#!/usr/bin/python

"""
G2_RIGHTS.

Definition of a custom Mininet topology, which is created using a user-specified config file.
Google B4 would be a specific instance of this topology.
This module creates hosts and switches and wires them according to the link specifications provided by user.

"""

from mininet.topo import Topo
import json
from mininet.log import setLogLevel, info

class G2Topo(Topo):
    """Topology Definition.

    Args:
        topoDict (dict): Topology-related information that was parsed from config file.
        params: Used to pass Mininet-specific keyword arguments.

    """

    def __init__(self, topoDict, **params):
        setLogLevel('info')
        if not topoDict:
            info("**** [G2]: no topology was provided; exiting...\n")
            return

        # Initialize topology
        Topo.__init__(self, **params)
        hostNames = topoDict['hosts']
        switchNames = topoDict['switches']

        # Create hosts and switches.
        hosts = [self.addHost(h, ip=topoDict[h]['IP'], mac=topoDict[h]['MAC'])
                  for h in hostNames]
        switches = [self.addSwitch(s)
                   for s in switchNames]

        # Wire up hosts and switches.
        for ss1, ss2 in topoDict['links']:
            self.addLink(ss1, ss2)

        # Write the topology information to a JSON file for use by the controller.
        outfile = topoDict['topoJSON']
        if outfile:
            jsonDict = { hi: topoDict[hi] for hi in topoDict['hosts'] }
            with open(outfile, "w") as fw:
                json.dump(jsonDict, fw, indent=1, sort_keys=False)
            fw.close()
            info("**** [G2]: topology information written to %s\n" %outfile)

# Enable command line creation such as below:
# sudo mn --custom ./g2Topo.py --topo g2Topo
topos = { 'g2Topo': (lambda: G2Topo()) }
