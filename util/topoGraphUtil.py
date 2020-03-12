#!/usr/bin/python

"""
G2_RIGHTS.

This module defines utility functions to generate graph properties for a Mininet network.

"""

from collections import defaultdict
import networkx as nx
import json
import os
from itertools import combinations
import operator

def writeAdjList(mnet, outfile):
    """Generate adjacency list for a graph given by a Mininet topology and write it to an output file.

    Args:
        mnet (mininet.net.Mininet): Mininet network object.
        outfile (str): Output file path.

    """

    allLinks = mnet.topo.iterLinks() # list of (src,dst) tuples
    G = nx.Graph(allLinks)
    nx.write_adjlist(G, outfile)

def generateShortestPaths(adjfile, outfile, trafficEndPoints, configuredLinks):
    """Generate shortest path between each pair of nodes of a graph represented by its adjacency list.

    Args:
        adjfile (str): Path to a file containing adjacency list of a graph.
        outfile (str): Output file path.
        trafficEndPoints (list): List of traffic flow end points (src_host, dst_host).
        configuredLinks (list): List of tuples, each representing a user-specified non-default link.

    Returns:
        dict: With (key, value) = (each node as src, dictionary containing dst-path as key-value)

    """

    G = nx.read_adjlist(adjfile)
    paths = (nx.shortest_path(G))

    # If there are multiple paths of same (shortest) length between a pair of nodes,
    # nx.shortest_path() can pick any one. Therefore, we make sure that
    # each reverse path is literally the reverse of the forward path.
    for n1, n2 in combinations(paths.keys(), 2):
        fwd = paths[n1][n2]
        dwf = fwd[::-1]
        rev = paths[n2][n1]
        if dwf != rev:
            paths[n2][n1] = dwf

    # Enforce to choose shortest paths which traverse the configured links, wherever applicable.
    # ['src']['dst'][idx] -> number_of_configured_links
    pathDict = {}
    for tSrc,tDst in trafficEndPoints:
        if tSrc not in pathDict:
            pathDict[tSrc] = dict()
        pathDict[tSrc][tDst] = defaultdict(int)
        srcDstPaths = [p for p in nx.all_shortest_paths(G, tSrc, tDst)]
        for idx, pth in enumerate(srcDstPaths):
            for bSrc, bDst in configuredLinks:
                try:
                    if abs(pth.index(bSrc) - pth.index(bDst)) == 1: # configured link (bSrc,bDst) is present on path 'pth'
                        pathDict[tSrc][tDst][idx] += 1
                except ValueError:
                    # ValueError occurs when configured link is not part of any of the shortest paths.
                    continue
        # Get the path having max configured link on it.
        # Which means -- get key with max value in dictionary pathDict[tSrc][tDst].
        maxIdx = max(pathDict[tSrc][tDst].iteritems(), key=operator.itemgetter(1))[0]
        pth = srcDstPaths[maxIdx]
        paths[tSrc][tDst] = pth
        # Again, set the reverse path.
        paths[tDst][tSrc] = pth[::-1]

    with open(outfile, "w") as write_file:
        json.dump(paths, write_file, indent=1, sort_keys=False)
    write_file.close()
    return paths

def readFromPathFile(infile):
    """Read path information from a file.

    Args:
        infile (str): Path to input file.

    """

    with open(infile, "r") as read_file:
        data = json.load(read_file)
    read_file.close()
    return data

def generateRoutingConf(mnet, paths, outfile):
    """For a given Mininet network and given paths (flows), generate routing config file.

    Args:
        mnet (mininet.net.Mininet): Mininet network object.
        paths (dict): Dictionary containing paths.
        outfile (str): Output file path.

    """

    topo = mnet.topo
    links = topo.iterLinks()
    srcs = paths.keys()
    routingInfo = defaultdict(list)
    for src in srcs:
        if not topo.isSwitch(src):
            dsts = paths[src].keys()
            for dst in dsts:
                if not topo.isSwitch(dst):
                    if src != dst:
                        hoplist = paths[src][dst]
                        for idx in range(len(hoplist) - 2):
                            firsthop = hoplist[idx]
                            secondhop = hoplist[idx+1]
                            thirdhop = hoplist[idx+2]
                            rcvPort = topo.port(firsthop, secondhop)[1] # dst switch side port
                            sendPort = topo.port(secondhop,thirdhop)[0] # source switch side port towards nexthop
                            routingInfo[secondhop].append(src + '-' + dst + ': ' + str(rcvPort) + '-' + str(sendPort))

    with open(outfile, 'w') as wf:
        sections = routingInfo.keys()
        for sc in sections:
            wf.write('[%s]\n' %sc)
            for entry in routingInfo[sc]:
                wf.write(entry+'\n')
            wf.write('\n')
    wf.close()

def getPathFeasibility(mnet, adjfile, paths):
    """Check the dictionary 'paths' on the graph represented by Mininet network.
    The paths dictionary is in specific format, that matches with the outputs of networkx.shortest_path(G) and our generateShortestPaths(adjfile, outfile) functions.

    Args:
        mnet (mininet.net.Mininet): Mininet network object.
        paths (dict): Dictionary containing paths
        adjfile (str): Path to file containing adjacency list of the network (in a format feasible for Python networkx)

    Returns:
        bool: Returns True if every path in 'paths' is feasible on the graph. False otherwise.

    """

    # If adjacency list file is not present, create it and then create a graph out of it.
    if not os.path.exists(adjfile):
        writeAdjList(mnet, adjfile)
    G = nx.read_adjlist(adjfile)

    for src in paths.keys():
        for dst in paths[src].keys():
            path = paths[src][dst] # list of nodes on the path, including src and dst.
            pair_list = zip(path[:-1], path[1:])
            # For single node path (i.e., src == dst), pair_list will be [], so below check is bypassed.
            for n1, n2 in pair_list:
                if not G.has_edge(n1, n2):
                    print("Routing conf not feasible. Non-existent edge (%s,%s) as specified in conf, path %s.\n"
                          %(n1, n2, "-".join(path)))
                    return False
    return True

def getG2Inputs(conf, mnet):
    """Get dictionaries C, F, and flow info (RTT and path) for each traffic flow.
    Write these dictionaries to JSON files.

    Args:
        conf (ConfigHandler): ConfigHandler object containing user-specified configurations.
        mnet (NetworkSimulator): The NetworkSimulator object.

    Returns:
        C (dict)    [linkID] -> linkCapacity
        F (dict)    [flowID] -> [linkIDs]
        flowInfo (dict) [flowID] -> {linkStr, links, rtt}

    Note:
        -- All IDs are integers starting at 1, prefixed with 'l' or 'f'' (for link or flow respectively).
        -- C, F, and L are written to c_dict.json, f_dict.json, and l_dict.json files in the output directory (as specified in config).

    """

    flows = conf.trace.jobs
    topoConf = conf.topoData
    paths = mnet.paths
    topo = mnet.net.topo
    # The capacity dictionary.
    C = {}
    # The flow dictionary.
    # A flow is the list of links traversed by it.
    F = {}
    # linkID -> [linkStr]. Example, {'l1': 's1-s2'}.
    L = conf.topoData['L']
    # [linkStr] -> linkID. Example, {'s1-s2': 'l1'}.
    reverseL = dict((v,k) for k,v in L.iteritems())
    # Dictionary to hold flow information and RTT.
    flowInfo = {}

    # Link specifications are provided by the user under either 'link_info' or 'default_link_info' parameters.
    linkInfos = topoConf['linkInfos']
    defaultBW = float(topoConf['defaultLinkInfo']['bw'].strip())
    links = topo.iterLinks()
    for n1, n2 in links:
        # For C, consider only switch-switch links.
        if topo.isSwitch(n1) and topo.isSwitch(n2):
            linkStr = n1 + '-' + n2
            linkBW = defaultBW
            for lif in linkInfos:
                if (n1 == lif['src'] and n2 == lif['dst']) or (n2 == lif['src'] and n1 == lif['dst']):
                    linkBW = float(lif['bw'].strip())
                    break
            C[reverseL[linkStr]] = linkBW

    # At this point, C and L dictionaries will have data for all the relevant links.
    # Now prepare F and flowInfo
    defaultDelay = float(topoConf['defaultLinkInfo']['delay'].strip('ms')) # remove 'ms' from end
    for flow in flows:
        flowID = 'f' + str(flow['id'])
        flowInfo[flowID] = {}
        src = flow['src']
        dst = flow['dst']
        flowStr = src + '-' + dst
        flowInfo[flowID]['flowStr'] = flowStr
        # Generate pairs of consecutive nodes on the path - we consider complete end-to-end path.
        pathList = paths[src][dst]
        flowLinks = [(x,y) for x,y in zip(pathList, pathList[1:])]
        flowInfo[flowID]['links'] = flowLinks # all links, both host-switch and switch-switch.

        # Add to F, the details for this flow, consider only switch-switch links for that.
        F[flowID] = []
        for (x,y) in flowLinks:
            if topo.isSwitch(x) and topo.isSwitch(y):
                if x+'-'+y in reverseL:
                    F[flowID].append(reverseL[x+'-'+y])
                elif y+'-'+x in reverseL:
                    F[flowID].append(reverseL[y+'-'+x])
                else:
                    # This would happen only when 'paths' do not correspond to the same network, e.g., due to (un)intentional data corruption.
                    F[flowID] = []
                    break
        if not F[flowID]:
            # Again, the extreme case of data corruption, as above.
            F = {}
            break
        # RTT computation.
        rtt = 0.0
        for n1, n2 in flowLinks:
            linkDelay = defaultDelay
            for lif in linkInfos:
                if (n1 == lif['src'] and n2 == lif['dst']) or (n2 == lif['src'] and n1 == lif['dst']):
                    linkDelay = float(lif['delay'].strip('ms'))
                    break
            rtt += linkDelay
        rtt *= 2.0
        flowInfo[flowID]['rtt'] = rtt

    # Write C, F, and L to files in output directory.
    cfile = os.path.join(conf.outPath, "c_dict.json")
    ffile = os.path.join(conf.outPath, "f_dict.json")
    lfile = os.path.join(conf.outPath, "l_dict.json")
    with open(cfile, "w") as write_file:
        json.dump(C, write_file, indent=1)
    with open(ffile, "w") as write_file:
        json.dump(F, write_file, indent=1)
    with open(lfile, "w") as write_file:
        json.dump(L, write_file, indent=1)

    return (C, F, flowInfo)
