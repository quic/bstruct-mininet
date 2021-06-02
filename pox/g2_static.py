"""
G2_RIGHTS.

An L3 switch based on static routing.

This module creates a POX controller which reads static routing configuration from a file.
Accordingly, each switch that connects to this controller will receive both IP and ARP flows table entries.
Therefore, no routing request comes to the controller for known paths.
If a flow needs to be transmitted on an unknown path, requests will come to the controller only to get ignored and hence those requests would not succeed.

"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.arp import arp
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.revent import *

import configparser
from collections import defaultdict
import json

log = core.getLogger()

class TopoStructure():
    """Topology structure related constants.

    Args:
        topoFile (str): Path to file that contains topology information.

    Attributes:
        hostAddrDict (dict): Mapping from host ID to IP address and MAC address.

    Examples:
        hostAddrDict['h1']['IP'] = 10.0.1.10
        hostAddrDict['h1']['MAC'] = 000000000001

  """

    def __init__(self, topoFile):
        self.hostAddrDict = {}
        with open(topoFile, "r") as read_file:
            self.hostAddrDict = json.load(read_file)
        read_file.close()

class StaticRouter():
    """Definition of a router that reads flow rules from a config file and prepares data required to create flow rules for switches.

    Args:
        config_file (str): Path of file that contains routing configuration.

    Attributes:
        config (str): Path of file that contains routing configuration.

    """

    def __init__(self, config_file):
        self.config = config_file

    def getRoutes(self):
        """Create a dictionary of flow rules.

        Returns:
            dict: With (key, value) = (switch dpid, list of flow rules)

        Example:
            rulesDict['1'] = [(h1,h2,3,2)] can be interpreted as follows:
            On switch s1, a flow rule should be inserted to forward any packets to port 2 which match source host h1, source port 3,
            and destination host h2

        """

        rulesDict = defaultdict(list)
        Config = configparser.ConfigParser()
        if Config.read(self.config):
            switches = Config.sections() # ['s1', 's2', 's3', ...]
            if switches:
                for switch in switches:
                    options = Config.options(switch)
                    for pair in options:
                        ks = pair.split('-')
                        sh, dh = ks[0], ks[1] # sh: source host, dh: destination host
                        vs = Config.get(switch, pair).split('-')
                        sp, dp = vs[0], vs[1] # sp: source port, dp: destination port
                        rulesDict[int(switch[1:])].append((sh,dh,sp,dp)) # dict key is just int dpid
            else:
                log.debug("no switches found in routing conf. No rules will be inserted.")
        return rulesDict

class G2Switch (EventMixin):
    """An L3 switch class.

    Args:
        topoFile (str): Path to file that contains topology information.
        routingFile (str): Path to file that contains routing configuration.


    Attributes:
        routingConfig (str): Path of file that contains routing configuration.
        topoStruct (TopoStructure): Instance of TopoStructure class that contains topology-related constants.


    """

    def __init__ (self, topoFile, routingFile):
        self.topoStruct = TopoStructure(topoFile)
        self.routingConfig = routingFile
        core.addListeners(self)

    def _handle_GoingUpEvent (self, event):
        core.openflow.addListeners(self)
        log.debug("Up...")

    def _handle_ConnectionUp (self, event):
        dpid = event.connection.dpid
        log.debug("switch %i has come up.", dpid)
        router = StaticRouter(self.routingConfig)
        flowRules = router.getRoutes()
        if flowRules:
            rules = flowRules[dpid] # list of tuples
            for rule in rules:
                sh, dh, inp, outp = rule

                # IP
                fm = of.ofp_flow_mod()
                fm.match.in_port = None
                fm.priority = 42
                fm.match.dl_type = 0x0800

                fullIP = self.topoStruct.hostAddrDict[sh]["IP"]
                splits = fullIP.split('/')
                (addr, netmask) = (splits[0].strip(), int(splits[1].strip()))
                fm.match.nw_src = (IPAddr(addr), netmask)

                fullIP = self.topoStruct.hostAddrDict[dh]["IP"]
                splits = fullIP.split('/')
                (addr, netmask) = (splits[0].strip(), int(splits[1].strip()))
                fm.match.nw_dst = (IPAddr(addr), netmask)

                fm.actions.append(of.ofp_action_output(port = int(outp)))
                event.connection.send(fm)

                # ARP
                fm = of.ofp_flow_mod()
                fm.match.in_port = None
                fm.priority = 42
                fm.match.dl_type = 0x0806
                fm.match.dl_src = EthAddr(self.topoStruct.hostAddrDict[sh]["MAC"])

                fullIP = self.topoStruct.hostAddrDict[dh]["IP"]
                splits = fullIP.split('/')
                (addr, netmask) = (splits[0].strip(), int(splits[1].strip()))
                fm.match.nw_dst = (IPAddr(addr), netmask)

                fm.actions.append(of.ofp_action_output(port = int(outp)))
                event.connection.send(fm)
            log.debug("inserted flow rules in switch %i.", dpid)
        else:
            log.debug("routing conf was not found. No rules added to switch %i.", dpid)

    def _handle_PacketIn (self, event):
        dpid = event.connection.dpid
        inport = event.port
        packet = event.parsed

        if not packet.parsed:
            log.warning("switch %i port %i ignoring unparsed packet", dpid, inport)
            return

        if packet.type == ethernet.LLDP_TYPE:
            # Ignore LLDP packets
            return

        if isinstance(packet.next, ipv4):
            log.debug("IPv4 packet")
            log.debug("switch %i port %i IP %s => %s", dpid,inport,
                    packet.next.srcip,packet.next.dstip)
            log.debug("ignoring packet")
            # Do nothing
            return
        elif isinstance(packet.next, arp):
            log.debug("ARP packet")
            a = packet.next
            log.debug("switch %i port %i ARP %s srcIP %s => dstIP %s", dpid, inport,
            {arp.REQUEST:"request",arp.REPLY:"reply"}.get(a.opcode,
                'op:%i' % (a.opcode,)), str(a.protosrc), str(a.protodst))

            if a.prototype == arp.PROTO_TYPE_IP:
                if a.hwtype == arp.HW_TYPE_ETHERNET:
                    if a.protosrc != 0:
                        log.debug("ignoring packet")
                        # Do nothing
                        return

        # Todo: Future work- (1) handle other protocol types
        # (2) suppress warnings: ipv6 packet data incomplete and dns incomplete name.


def launch (topo, routing):
    """POX controller's launch() function. The function that POX calls to tell the component to initialize itself.

    Args:
        topo (str): Path to JSON file that contains topology information.
        routing (str): Path to file that contains routing configuration.

    Example:
        The command line arguments are passed as follows:
        ./pox.py --verbose openflow.of_01 --port=6633 g2_static --topo='path/to/topo.json --routing='path/to/routing.conf '

    """

    # POX core will handle the case when 'topo' and 'routing' were not specified.
    core.registerNew(G2Switch, topo, routing)
