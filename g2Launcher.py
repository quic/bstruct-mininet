#!/usr/bin/python

"""
G2_RIGHTS.

This module creates a Mininet network based on the topology defined by G2Topo class.
It also performs configured tests on the network and does the post-processing of results.

"""

from mininet.net import Mininet
from mininet.util import quietRun
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info, debug
from mininet.util import waitListening, custom
from mininet.link import TCLink
from mininet.node import CPULimitedHost
from mininet.clean import cleanup

import ConfigParser
import argparse
import os
from time import time, sleep
from functools import partial
from multiprocessing import Process
from multiprocessing import Pool
from subprocess import Popen, PIPE, STDOUT
import re
import signal, sys
import socket
import fcntl
import array
import struct
from requests import put

from g2Topo import G2Topo
from util.topoGraphUtil import writeAdjList, generateShortestPaths, generateRoutingConf, readFromPathFile, getPathFeasibility, getG2Inputs
from util.traceParser import TraceParser
from util.resultsProcessing import ResultGenerator
from util.monitor import Monitor
from util.jainsFairnessIndex import calculateJainsIndex

# Controller IP and port constants.
REMOTE_CONTROLLER_IP = "127.0.0.1" # "localhost"
CONTROLLER_PORT = 6633

# Constants for file-names and paths.
G2_CONF = "g2.conf"
TRAFFIC_CONF = "traffic.conf"
SHORTEST_PATH_FILE = "shortest_paths.json"
BENCHMARK_PATH = "benchmarks"

def generateIPAddress(base, subnet, host, mask):
    """Generate IP address in CIDR format.

    Args:
        base (str): First two octets of the IP address.
        subnet (int): Subnet address (3rd octet).
        host (int): Host address (4th octet).
        mask (int): Bit length of subnet mask (/n).

    Returns:
        str: IP address string in dotted decimal notation.

    Examples:
        generateIPAddress('10.0',4,2,None) returns 10.0.4.2
        generateIPAddress('10.0',4,1,24) returns 10.0.4.1/24

    """

    addr = str(base)+'.'+str(subnet)+'.' + str(host)
    if mask != None:
        addr = addr + '/' + str(mask)
    return addr

def dpid_to_mac (dpid):
        """Generate hex MAC address from a given int ID.
        Args:
            dpid (int): Integer ID of a switch, e.g. 1,2,3, and so on.

        Returns:
            str: MAC address without any colon or comma sign (only hex numbers).

        """

        return "%012x" % (dpid & 0xffFFffFFffFF,)

def parseConfStr(confStr):
    """Parse a line of configuration file which is in format of semicolon-separated tuples.

    Args:
        confStr (str): String of tuples, each separated by semicolon, e.g., "(h1,s1);(h2,s1)".

    Returns:
        list: A list of tuples (key, value pairs).

    """
    pairList = []
    specs = confStr.split(';')
    for spec in specs:
        if not spec:
            continue
        spec = spec.strip()
        splits = spec.split(',')
        splits = [ss.strip("()") for ss in splits]
        splits = tuple(splits)
        pairList.append(splits)
    return pairList

class ConfigHandler:
    """Configuration parser.

    Args:
        inputPath (str): Path to directory containing configuration files, e.g., g2.conf, traffic.conf.
        outPath (str): Path to directory used to write output config and results.

    Attributes:
        All fields from configuration file.

    """

    def __init__(self, inputPath, outPath):
        self.config = ConfigParser.ConfigParser()
        try:
            self.config.read(os.path.join(inputPath, G2_CONF))
        except ConfigParser.ParsingError, err:
            info("**** [G2]: could not parse config; exiting....\n", err, "\n")
            self.config = None
            return

        self.outPath = outPath

        # Topology-related configurations: details on hosts, switches, and connections.
        self.topoData = self.getTopoConf()
        if not self.topoData:
            self.config = None
            return

        # General configurations.
        generalDict = self.configSectionMap('General')
        self.isDebug = int(generalDict['debug'])
        self.isCLI = int(generalDict['start_cli'])
        self.ccAlgo = generalDict['tcp_congestion_control']
        self.adjacencyFile = os.path.join(outPath, generalDict['adjacency_list_outfile'])
        self.routingConf = os.path.join(outPath, generalDict['routing_conf_outfile'])

        # Benchmarking-related configurations.
        monitorDict = self.configSectionMap('Monitoring')
        self.isPingAll = int(monitorDict['test_pingall'])
        self.isIperf = int(monitorDict['test_iperf'])
        self.trafficConf = os.path.join(inputPath, TRAFFIC_CONF)
        self.trace = TraceParser(self.trafficConf)
        self.isSwStat = int(monitorDict['monitor_switch_stats'])
        self.linksToMonitor = monitorDict['links_to_monitor']
        self.frequency = float(monitorDict['collection_frequency'])
        self.utilizationInterval = float(monitorDict['utilization_monitor_interval'])
        self.prefix = monitorDict['result_prefix']
        self.onlyResults = int(monitorDict['only_results_processing'])
        # Save all results to outPath/benchmarks directory.
        self.benchPath = os.path.join(outPath, BENCHMARK_PATH)
        if not os.path.exists(self.benchPath):
                os.makedirs(self.benchPath)
        self.convTimeType = monitorDict['convergence_time_method']
        self.convWindow = monitorDict['window_size']
        self.convThresh = monitorDict['threshold']
        self.convNumSamples = monitorDict['num_samples']
        self.plotEachFlow = int(monitorDict['plot_each_flow'])

    def getTopoConf(self):
        """Create a dictionary of topology-related information obtained from configuration file.

        Returns:
            dict: topology-related information a dictionary.

        """

        topoDict = {}
        topoDict['hosts'] = set()
        topoDict['switches'] = set()
        topoDict['links'] = list()
        # linkID -> [linkStr]
        # Example: L = {'l1': 's1-s2'}
        topoDict['L'] = {}

        confDict = self.configSectionMap("Topology")
        if not confDict:
            return {}

        linkStr = confDict['links']
        pairs = parseConfStr(linkStr)
        # 'pairs' would be a list of tuples (linkID, switch1, switch2).
        for pair in pairs:
            nodes = (pair[1], pair[2])
            topoDict['links'].append(nodes)
            if nodes[0].startswith('s') and nodes[1].startswith('s'):
                topoDict['L']['l' + pair[0]] = nodes[0] + '-' + nodes[1]
            for node in nodes:
                if node.startswith('h') and node not in topoDict:
                    topoDict[node] = {}
                    topoDict['hosts'].add(node)
                if node.startswith('s'):
                    topoDict['switches'].add(node)

        # Obtain IP address information from the config file.
        # Set MAC addresses automatically and sequentially.
        baseAddr = confDict['base_addr'].strip()
        subnetAddr = confDict['subnet_addr'].strip()
        if subnetAddr == 'x':
            subnetAddr = None
        hostAddr = confDict['host_addr'].strip()
        if hostAddr == 'x':
            hostAddr = None

        # Check that one of the subnetAddr and hostAddr was 'x'.
        if subnetAddr and hostAddr:
            info("**** [G2]: invalid config for subnet or host address; please make sure that either subnet or host address is 'x'; exiting...\n")
            return {}

        netmaskLen = int(confDict['netmask_length'].strip())
        if netmaskLen == 0:
            netmaskLen = None

        assignedIPs = set()
        for hn in topoDict['hosts']:
            num = hn[1:]
            if not subnetAddr:
                currIP = generateIPAddress(baseAddr,num,hostAddr,netmaskLen)
                topoDict[hn]['IP'] = currIP
                assignedIPs.add(currIP)
            if not hostAddr:
                currIP = generateIPAddress(baseAddr,subnetAddr,num,netmaskLen)
                topoDict[hn]['IP'] = currIP
                assignedIPs.add(currIP)

            topoDict[hn]['MAC'] = dpid_to_mac(int(num))

        # IF 'override_ip' configuration was set, we read the IP addresses that are specified under 'ip_info' config parameter.
        # For the hosts present in the 'ip_info' config, we set the IP to user-specified value.
        overrideIP = confDict['override_ip'].strip()
        if overrideIP == 'yes':
            overrideIPStr = confDict['ip_info'].strip()
            pairs = parseConfStr(overrideIPStr)
            for (hName, hIP) in pairs:
                if hIP in assignedIPs:
                    info("**** [G2]: override IPs conflict with auto-assigned IPs; exiting....\n")
                    return {}
                topoDict[hName]['IP'] = hIP

        topoDict['flowSpec'] = confDict['flow_paths_file'].strip()
        topoDict['defaultLinkInfo'] = self.parseDefaultLinkInfo(confDict['default_link_info'])
        topoDict['linkInfos'] = self.parseLinkInfoData(confDict['link_info'])
        topoDict['topoJSON'] = os.path.join(self.outPath, confDict['topology_json_outfile'])

        return topoDict

    def configSectionMap(self, sectionName):
        """Create a dictionary of all config parameters in a section.

        Args:
            sectionName (str): Name of a section (as in the config file).

        Returns:
            dict: With (key, value) = (parameter name , parameter value)

        """

        dict1 = {}
        configObj = self.config
        try:
            options = configObj.options(sectionName)
        except Exception as e:
            info("**** [G2]: ConfigParser exception; exiting....\n", e, "\n")
            return {}

        for option in options:
            try:
                dict1[option] = configObj.get(sectionName, option)
                if dict1[option] == -1:
                    info("**** [G2]: skip: %s" % option, "\n")
            except:
                info("**** [G2]: exception on %s!" % option, "\n")
                dict1[option] = None
        return dict1

    def parseDefaultLinkInfo(self, confStr):
        """Parse a string of default link info that is specified in config file.

        Args:
            confStr (str): Link info specification obtained from config file.

        Returns:
            dict: Containing link info parameters.

        """

        linkInfo = {}
        if confStr != 'None':
            splits = confStr.strip().split(',')
            splits = [s.strip() for s in splits]
            linkInfo['bw'] = splits[0]
            linkInfo['delay'] = splits[1]
            linkInfo['loss'] = splits[2]
            linkInfo['max_queue_size'] = splits[3]
            linkInfo['use_htb'] = splits[4]
        return linkInfo

    def parseLinkInfoData(self, confStr):
        """Parse a string of link info that is specified in config file.

        Args:
            confStr (str): Link info specification obtained from config file.

        Returns:
            list: List of dictionaries, each containing link info parameters.

        """

        data = []
        if not confStr:
            return data

        specs = confStr.split(';')
        for spec in specs:
            if not spec:
                continue
            splits = spec.split(',')
            splits = [s.strip() for s in splits]
            ls = {}
            ls['src'] = splits[0]
            ls['dst'] = splits[1]
            ls['bw'] = splits[2]
            ls['delay'] = splits[3]
            ls['loss'] = splits[4]
            ls['max_queue_size'] = splits[5]
            ls['use_htb'] = splits[6]
            data.append(ls)
        return data


class NetworkSimulator:
    """Create and start a Mininet network using parsed configuration.

    Args:
        config (ConfigHandler): Object containing parsed configurations.

    Attributes:
        config (ConfigHandler): Object containing parsed configurations.
        net (mininet.net.Mininet): Mininet net object.
        paths (dict): Path information on the created network, as specified by user in config file.

    """

    def __init__(self, config):
        self.config = config
        self.net = self.createNet()
        self.paths = self.getPaths()

    def createNet(self):
        """Create an instance of a Mininet network.

        Returns:
            mininet.net.Mininet: Reference to the created Mininet network.

        """

        sw = OVSKernelSwitch
        topo = G2Topo(self.config.topoData)
        ctrl = RemoteController('c', ip=REMOTE_CONTROLLER_IP, port=CONTROLLER_PORT)

        # Default link parameters.
        # HTB: Hierarchical Token Bucket rate limiter.
        spec = self.config.topoData['defaultLinkInfo']
        if spec:
            mybw = float(spec['bw'])
            mydelay = spec['delay']
            myloss = float(spec['loss'])
            link = partial(TCLink, delay=mydelay, bw=mybw, loss=myloss)
            if spec['max_queue_size'] != 'N/A' and spec['use_htb'] == 'N/A':
                myqueue = int(spec['max_queue_size'])
                link = partial(TCLink, delay=mydelay, bw=mybw, loss=myloss, max_queue_size=myqueue)
            if spec['max_queue_size'] == 'N/A' and spec['use_htb'] != 'N/A':
                myhtb = bool(spec['use_htb'])
                link = partial(TCLink, delay=mydelay, bw=mybw, loss=myloss, use_htb=myhtb)
            if spec['max_queue_size'] != 'N/A' and spec['use_htb'] != 'N/A':
                myqueue = int(spec['max_queue_size'])
                myhtb = bool(spec['use_htb'])
                link = partial(TCLink, delay=mydelay, bw=mybw, loss=myloss, max_queue_size=myqueue, use_htb=myhtb)
        else:
            # No spec for default parameters, using Mininet defaults.
            info("**** [G2]: using Mininet default parameters for links other than those configured in link_info \n")
            link = TCLink

        # Configure bw, delay, loss, etc. for some links that are specified in config file.
        for spec in self.config.topoData['linkInfos']:
            src = spec['src']
            dst = spec['dst']
            try:
                linkInfo = topo.linkInfo(src, dst)
                if spec['bw'] != 'N/A':
                    linkInfo['bw'] = float(spec['bw']) # Mbit
                if spec['delay'] != 'N/A':
                    linkInfo['delay'] = spec['delay'] # ms
                if spec['loss'] != 'N/A':
                    linkInfo['loss'] = float(spec['loss']) # Percentage
                if spec['max_queue_size'] != 'N/A':
                    linkInfo['max_queue_size'] = int(spec['max_queue_size'])
                if spec['use_htb'] != 'N/A':
                    linkInfo['use_htb'] = bool(spec['use_htb'])

                topo.setlinkInfo(src,dst,linkInfo)
            except KeyError:
                info("**** [G2]: no link exists between switch pair (%s, %s) \n" %(src, dst))

        # Assign a fraction of overall CPU time to Mininet hosts.
        nHosts = float(len(self.config.topoData['hosts']))
        cpuHostFrac = 0.50/nHosts
        # 'cpu' is the fraction of CPU that each host would get.
        # Indirectly, it sets 'cpu.cfs_quota_us': the total available run-time within a period (in microseconds).
        # Mininet uses the following scheme: cfs_quota_us = (cpuHostFrac * nCPU * period_us) microseconds.
        # 'period_us' sets cpu.cfs_period_us.
        # Larger period would allow for increased burst capacity.
        host = custom(CPULimitedHost, cpu=cpuHostFrac, period_us=100000)

        net = Mininet(topo=topo,
            host=host,
            switch=sw,
            controller=ctrl,
            waitConnected=True,
            autoStaticArp=True,
            link=link)

        # Create a default route for each host.
        # Turn on tcpdump on each host if debug mode is on.
        for hs in topo.hosts():
            net.getNodeByName(hs).setDefaultRoute(intf='%s-eth0' %hs) # 1st interface on hosts is hi-eth0
            if self.config.isDebug:
                net.getNodeByName(hs).cmd('tcpdump -w %s.pcap -i %s-eth0 &' %(hs,hs))
        return net

    def getPaths(self):
        """Read from file (if created and specified by the user) or generate (if selected for shortest paths) path information.

        Returns:
            dict: With (key, value) = (each node as src, dictionary containing dst-path as key-value).

        """

        trafficEndPoints = []
        # A job denotes a traffic flow, which corresponds to an iperf task.
        for job in self.config.trace.jobs:
            trafficEndPoints.append((job['src'], job['dst']))

        # Obtain details about user-specified non-default links.
        configuredLinks = []
        for linkInfo in self.config.topoData['linkInfos']:
            configuredLinks.append((linkInfo['src'], linkInfo['dst']))

        paths = None
        spec = self.config.topoData['flowSpec']
        if spec == 'shortest_path':
            # export paths info and create routing conf using shortest paths
            adjFile = self.config.adjacencyFile
            writeAdjList(self.net, adjFile)
            info("**** [G2]: adjacency list written to file", adjFile, "\n")

            outfile = os.path.join(self.config.outPath, SHORTEST_PATH_FILE)
            paths = generateShortestPaths(adjFile, outfile, trafficEndPoints, configuredLinks)
            info("**** [G2]: shortest paths written to file", outfile, "\n")
            # Note: Since there can be multiple shortest paths between two endpoints, solution could vary.
        elif ".json" in spec:
            info("**** [G2]: reading path info from", spec, "\n")
            paths = readFromPathFile(spec)
        else:
            paths = None
        return paths

    def generateRouting(self, adjFile, outFile):
        """For the given network, generate routing config and write to a file.

        Args:
            adjFile (str): Path to file containing adjacency list of the network (in a format feasible for Python networkx)
            outFile (str): Output file path.

        """

        if self.paths:
            feasible = getPathFeasibility(self.net, adjFile, self.paths)
            if feasible:
                routingConf = generateRoutingConf(self.net, self.paths, outFile)
                info("**** [G2]: path specs are FEASIBLE; generated routing conf file", outFile, "\n")
            else:
                if os.path.exists(outFile):
                    os.remove(outFile)
                info("**** [G2]: INFEASIBLE path sepcs; deleted any old routing conf files present; controller will receive NO routing conf\n")
        else:
            info("**** [G2]: NO path sepcs found; controller will receive NO routing conf\n")

    def start(self):
        """Start Mininet net.

        """

        self.net.start()


class NetworkMonitor:
    """Run benchmarking test on a Mininet network including pingAll, iperf, and switch monitoring.
    Launch post-processing of results to generate CSV files and plots.

    Args:
        network (NetworkSimulator): Object containing Mininet and ConfigHandler objects.

    Attributes:
        net (mininet.net.Mininet): Mininet object.
        config (ConfigHandler): ConfigHandler object.
        interfaceList (list): list of switch interfaces obtained from config descriptions of links to monitor.

    """

    def __init__(self, network):
        self.net = network.net
        self.config = network.config
        self.interfaceList = self.monitoredInterfaceList()

    def getIfInfo(self, dst):
        """Get name and IP address of the interface that is used by sFlow agent to send traffic.

        Args:
            dst (str): IP address of the sFlow collector in standard dotted-quad string representation.

        Returns:
            (str, str): name and IP address of the interface (in standard dotted-quad string representation e.g., 123.45.67.89)

        """

        # Identify the size of each interface entry as returned by ioctl system operation for get iface list.
        # For platforms with pointer size greater than 2**32, the size of each interface entry is 40 bytes.
        is_64bits = sys.maxsize > 2**32
        struct_size = 40 if is_64bits else 32

        # Create a datagram socket to use as the file descriptor to operate on.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        max_possible = 8 # initial value
        while True:
            bytes = max_possible * struct_size
            names = array.array('B')
            for i in range(0, bytes):
                names.append(0)
            # First, using pack(), get the address of 'names' array and create a mutable byte buffer.
            # Next, using ioctl(), store results of get iface list operation at the 'names' array.
            outbytes = struct.unpack('iL', fcntl.ioctl(
                s.fileno(),
                0x8912, # SIOCGIFCONF: command defined in ioctl.h for the system operation to get iface list.
                struct.pack('iL', bytes, names.buffer_info()[0])
            ))[0]
            if outbytes == bytes:
                max_possible *= 2
            else:
                break
        namestr = names.tostring()
        s.connect((dst, 0))
        ip = s.getsockname()[0]
        s.close()
        for i in range(0, outbytes, struct_size):
            # In each 40 bytes long entry, the first 16 bytes are the name string, the 20th-24th bytes are IP address octet strings in byte form - one for each byte.
            name = namestr[i:i+16].split('\0', 1)[0]
            addr = socket.inet_ntoa(namestr[i+20:i+24])
            if addr == ip:
                return (name, addr)
        # Return None if no matching interface was found.
        return (None, None)

    def configSFlow(self, ifname, collector, sampling, polling):
        """Create sFlow configuration and attach it to each switch in the network.

        ifname (str): Name of interface whose IP address is used by the sFlow agent to send traffic from, e.g., 'eth0'.
        collector (str): IP address of the sFlow collector in standard dotted-quad string representation.
        sampling (str): Packet sampling frequency of sFlow.
        polling (str): Polling interval of sFlow.

        """

        net = self.net
        info("**** [G2]: enabling sFlow:\n")
        sflow = 'ovs-vsctl -- --id=@sflow create sflow agent=%s target=%s sampling=%s polling=%s --' % (ifname, collector, sampling, polling)
        for s in net.switches:
            sflow += ' -- set bridge %s sflow=@sflow' % s
        info("**** [G2]: " + ' '.join([s.name for s in net.switches]) + "\n")
        quietRun(sflow)

    def sendTopology(self, agent, collector):
        """Create a dictionary of topology information and send it to sFlow collector as a JSON object.

        Args:
            agent (str): IP address of the interface used by the sFlow agent to send traffic.
            collector (str):  IP address of the server running sFlow software that can receive and analyze sFlow datagrams sent by agents.

        """

        info("**** [G2]: sending topology\n")
        net = self.net
        topo = {'nodes':{}, 'links':{}}
        for s in net.switches:
            topo['nodes'][s.name] = {'agent':agent, 'ports':{}}
        path = '/sys/devices/virtual/net/'
        for child in os.listdir(path):
            parts = re.match('(^.+)-(.+)', child)
            if parts == None: continue
            if parts.group(1) in topo['nodes']:
                ifindex = open(path+child+'/ifindex').read().split('\n',1)[0]
                topo['nodes'][parts.group(1)]['ports'][child] = {'ifindex': ifindex}
        i = 0
        for s1 in net.switches:
            j = 0
            for s2 in net.switches:
                if j > i:
                    intfs = s1.connectionsTo(s2)
                    for intf in intfs:
                        s1ifIdx = topo['nodes'][s1.name]['ports'][intf[0].name]['ifindex']
                        s2ifIdx = topo['nodes'][s2.name]['ports'][intf[1].name]['ifindex']
                        linkName = '%s-%s' % (s1.name, s2.name)
                        topo['links'][linkName] = {'node1': s1.name, 'port1': intf[0].name, 'node2': s2.name, 'port2': intf[1].name}
                j += 1
            i += 1
        put('http://%s:8008/topology/json' % collector, json=topo)

    def testPing(self):
        """Run pingAll test.

        """

        if self.config.isPingAll:
            info("**** [G2]: testing basic connectivity using ping\n")
            self.net.pingAll()

    def testBandwidth(self):
        """Run bandwidth test using iperf and monitor switch interfaces.
        Results are written to files with prefix specified in config file.

        """

        if self.config.isIperf:
            info("**** [G2]: running bandwidth test using iperf\n")
            p1 = Process(target=self.iperfDriver)
            p1.start()

            if self.config.isSwStat:
                info("**** [G2]: collecting switch stats\n")
                ifList = self.interfaceList
                pfx = self.config.prefix
                freq = self.config.frequency

                procs = []
                for iface in ifList:
                    p = Process(target=self.monitorInterface, args=(iface, pfx, freq))
                    procs.append(p)
                    p.start()

            p1.join()
            # Once the iperf is done, we will terminate all the switch monitoring processes.
            if self.config.isSwStat:
                for p in procs:
                    p.terminate()

    def iperfDriver(self):
        """Wrapper function for launching iperf.
        Gets traffic information from user-specified traffic conf file.

        """

        # A job denotes a traffic flow, which corresponds to an iperf task.
        jobs = self.config.trace.jobs
        if jobs:
            now = time()
            info("**** [G2]: iperf test started at:", now, "\n") # Prints Unix epoch of 'now'.

            procs = []
            for j in jobs:
                p = Process(target=self.launchIperf, args=(j,))
                procs.append(p)
                p.start()

            for p in procs:
                p.join()

            end = time()
            simTime = end-now
            info("**** [G2]: iperf test done successfully in %.2f" %simTime, "sec\n")
            with open(os.path.join(self.config.benchPath, "%s_experiment_duration.csv" %self.config.prefix), "w") as fd:
                fd.write("simulation duration, slowest flow duration\n")
                fd.write("%.2f," %simTime)
        else:
            info("**** [G2]: no flow found, iperf test unsuccessful \n")

    def launchIperf(self, job):
        """Prepare arguments and launch 'iperf' to measure bandwidth using iperf along a traffic flow.
        Per flow, results are written to two files in ./benchmarks directory:
        <perfix>_iperf_server_<job id>.txt and <prefix>_iperf_client_<job id>.txt.

        Args:
            job (dict): Dictionary specification of each flow (as defined in TraceParser.jobs).

        """

        sleep(job['time'])
        jobID = job['id']
        client = self.net.getNodeByName(job['src'])
        server = self.net.getNodeByName(job['dst'])
        size = job['size']
        # Since there could be multiple flows destined to the same server at the same time, we make sure same port is not used multiple times.
        serverPort = 5001 + jobID

        # 'iperf' supports minimum interval 0.5. Smaller values would default to 0.5.
        # Also, for values greater than 0.5, only one digit after decimal point is supported.
        # Such values will be rounded to nearest supported value, e.g. 1.67 -> 1.7
        intervalSec = self.config.frequency
        pfx = self.config.prefix
        ccAlgo = self.config.ccAlgo

        fsSrv = open(os.path.join(self.config.benchPath, "%s_iperf_server_%d.txt" %(pfx, jobID)), "w")
        popenSrv = server.popen('iperf -s -p %d -i %f' %(serverPort, intervalSec), stdout=fsSrv, stderr=STDOUT) # Or, sys.stdout
        # Wait until server port is listening.
        cmdOut = server.cmd("sudo lsof -i -P -n | grep LISTEN | grep %d" %serverPort)
        while (not cmdOut) or ('iperf' not in cmdOut):
            debug("**** [G2]: traffic-flow %d waiting for iperf server to start on host %s\n" %(jobID, job['dst']))
            cmdOut = server.cmd("sudo lsof -i -P -n | grep LISTEN | grep %d" %serverPort)

        fsClnt = open(os.path.join(self.config.benchPath, "%s_iperf_client_%d.txt" %(pfx, jobID)), "w")
        popenClnt = client.popen('iperf -c %s -p %d -i %f -n %f -Z %s' % (server.IP(), serverPort, intervalSec, size, ccAlgo), stdout=fsClnt, stderr=STDOUT) # Or, sys.stdout
        retCode = popenClnt.wait()

        # Once client popen returns, wait for a small duration to allow the server receive all the traffic, and forcefully terminate server.
        sleep(.100) # 100 milliseconds
        popenSrv.kill()
        fsSrv.close()
        fsClnt.close()
        debug("**** [G2]: iperf done; flow ID:%d, src:%s, dst:%s; client iperf return code:%s\n" %(jobID, job['src'], job['dst'], retCode))

    def monitoredInterfaceList(self):
        """Parse list of switch links (specified in config file) and generate a list of interfaces to be monitored.

        Returns:
            list: A list of interface names.

        Example:
            For a config (s6, s8), the output would contain ['s8-eth2'] if s6-s8 link is on eth2 on s8.

        """

        ifs = []
        confStr = self.config.linksToMonitor
        specLinks = parseConfStr(confStr)
        topo = self.net.topo
        topoLinks = topo.iterLinks()
        for s,d in specLinks:
            if (s,d) in topoLinks and topo.isSwitch(s) and topo.isSwitch(d):
                ifs.append('%s-eth%d' %(d, topo.port(s,d)[1]))
            else:
                info("**** [G2]:(%s,%s) is not a valid switch link in the topology; cannot be monitored\n" %(s,d))
        return ifs

    def monitorInterface(self, interface, prefix, freq):
        """Monitor a switch interface to collect queue size and number of dropped packets.
        Uses Linux 'tc' command.
        Writes results (with header row) to a csv file in ./benchmarks directory.

        Args:
            interface (str): A switch interface in Mininet, e.g., 's8-eth2'
            prefix (str): Output file prefix.
            freq (float): Interval time between consecutive measurement in seconds.

        """

        queuedRegex = re.compile(r'backlog\s[^\s]+\s([\d]+)p')
        droppedRegex = re.compile(r'dropped\s([\d]+),')
        intervalSec = freq
        cmd = "tc -s qdisc show dev %s" % (interface)
        fname = os.path.join(self.config.benchPath, '%s_switch_stats_%s.csv' %(prefix, interface))
        open(fname, 'w').write('timestamp,queued_packets,cumulative_dropped_packets\n')
        info("**** [G2]: monitoring stats for", interface, "; will save results to", fname, "\n")
        while 1:
            p = Popen(cmd, shell=True, stdout=PIPE)
            output = p.stdout.read()
            matches1 = queuedRegex.findall(output)
            matches2 = droppedRegex.findall(output)
            if matches1 and matches2 and len(matches1) > 1 and len(matches2) > 1:
                t = "%f" %time()
                open(fname, 'a').write(t + ',' + matches1[1] + ',' + matches2[1] + '\n')
            p.terminate()
            sleep(intervalSec)
        return

def parse():
    """Parse command-line arguments.

    """

    global args
    global parser

    parser = argparse.ArgumentParser(description='Mininet topology launcher and monitoring module')
    parser.add_argument("-l", "--log-level", default="info", help="log level info|debug|warning|error")
    parser.add_argument("-i", "--input", required=True, help="directory containing input config files")
    parser.add_argument("-o", "--output", required=True, help="directory that receives output files and benchmarks")

    args = parser.parse_args()

def main():

    # Parse command-line arguments.
    parse()
    logLevels = ['debug', 'info', 'warning', 'error']
    if args.log_level in logLevels:
        setLogLevel(args.log_level)
    else:
        setLogLevel('info')

    info("**** [G2]: reading conf files from ", args.input, "\n")
    ch = ConfigHandler(args.input, args.output)

    # If there is an exception in config parsing, ch.config will be None.
    if not ch.config:
        info("**** [G2]: error while reading config; exiting...\n")
        return

    # Create and start the network.
    network = NetworkSimulator(ch)
    adjFile = ch.adjacencyFile # 'adj_list.txt'
    outfile = ch.routingConf # 'routing.conf'
    network.generateRouting(adjFile, outfile)

    if not ch.onlyResults:
        network.start()
        # Benchmarking.
        monitor = NetworkMonitor(network)

        # Configure and start sFlow.
        # 'collector': IP address of the server running sFlow software that can receive and analyze sFlow datagrams sent by agents.
        # 'sampling': an average 1 out of n packets is randomly sampled.
        # 'polling': how often (in seconds) the network device sends interface counters.
        collector = os.environ.get('COLLECTOR', '127.0.0.1')
        sampling = os.environ.get('SAMPLING', '10')
        polling = os.environ.get('POLLING', '10')
        (ifname, agent) = monitor.getIfInfo(collector)
        if not ifname or not agent:
            info("**** [G2]: error in getting sFlow agent interface details; exiting...\n")
            info("**** [G2]: cleaning Mininet\n\n")
            cleanup()
            return
        monitor.configSFlow(ifname, collector, sampling, polling)
        monitor.sendTopology(agent, collector)
        monitor.testPing()

        # Monitor CPU and memory during bandwidth tests.
        systemMonitor = Monitor(ch.utilizationInterval)
        systemMonitor.start()
        info("**** [G2]: started monitoring CPU and memory usage\n")
        systemMonitor.monitor()

        monitor.testBandwidth()

        systemMonitor.stop()
        info("**** [G2]: finished monitoring CPU and memory usage\n")
        cpuMemFile = os.path.join(ch.benchPath, "%s_cpu_memory_usage.csv" %(ch.prefix))
        systemMonitor.writeReadings(cpuMemFile)

        # CLI and stopping the network.
        if network.config.isCLI:
            CLI(network.net)
        else:
            info("**** [G2]: not starting CLI; exiting...\n")
        network.net.stop()

    info("**** [G2]: post-processing the output of monitoring and generating results\n")
    # Obtain details on flows, links, and RTT.
    (C, F, flowInfo) = getG2Inputs(ch, network)
    if not C:
        info("**** [G2]: error in input configurations caused an empty C dictionary; exiting...\n")
        return
    if not F:
        info("**** [G2]: error in input configurations caused an empty F dictionary; exiting...\n")
        return
    # Process iperf output and generate results.
    rg = ResultGenerator(ch, C, F, flowInfo)
    results = rg.parseIperfOutput()
    slowestTime = rg.getMaxCompletionTime(results)
    with open(os.path.join(ch.benchPath, "%s_experiment_duration.csv" %ch.prefix), "a") as fd:
        fd.write("%.2f\n" %slowestTime)
    rg.writeToJson(results)
    rg.writeToCsv(results)
    rg.plotResults(results)
    if ch.isSwStat:
        rg.plotSwitchStats()
    rg.plotUtilization()
    # Jain's fairness index.
    experimentRates = []
    expectedRates = []
    for flowID in range(1,len(ch.trace.jobs) + 1):
        experimentRates.append(results[flowID]['receiverAvgMbps'])
        for flow in ch.trace.jobs:
            if flow['id'] == flowID:
                expectedRates.append(flow['share'])
    jainsIndex = calculateJainsIndex(experimentRates, expectedRates)
    with open(os.path.join(ch.benchPath, "%s_fairness_index.csv" %ch.prefix), "w") as fd:
        fd.write("%f\n" %jainsIndex)

    info("**** [G2]: plots and results written to %s with prefix %s\n" %(ch.benchPath, ch.prefix))

    # Clean up Mininet junk which might be left over from old runs.
    info("**** [G2]: cleaning Mininet\n\n")
    cleanup()

# Clean up Mininet junk if the program was killed using ctrl-c.
def sigint_handler(signum, frame):
    info("**** [G2]: cleaning Mininet\n")
    cleanup()
    sys.exit(1)

signal.signal(signal.SIGINT, sigint_handler)

if __name__ == "__main__":
    main()
