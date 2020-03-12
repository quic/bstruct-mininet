#!/usr/bin/python

"""
G2_RIGHTS

Script to create a linear BPG network with 'n' links.

Usage:
./createNLinksExample.py -t <base_example_folder> -l <number_of_links> -cc <tcp_congestion_control> -f <scale_factor>

Given the above inputs, the script does the following:
    * Uses the network topology and default configuration from base example folder specified using '-t'
    * Sets up flows using the links specified with '-l' such that it produces a linear BPG graph
    * Sets up the congestion control algorithm for the example as specified using '-cc'
    * Replicates the flows by 'f' times (optional argument). If 'f' is not specified,
      flows are replicated by a factor of 1, 10, 100 by default.
    * By default all the examples generated are saved to 'g2_example_nlevel' folder in the current directory
    * Please note that this script has been tested with 'examples/g2_network10'
"""
import argparse
import os
import shutil

# Valid TCP congestion control algorithms to use for test with Mininet
VALID_CONGESTION_CONTROL_PROTOS = ["bbr", "cubic", "reno"]

# Default folder name to which the thus generated examples will be saved to
EXAMPLE_BASEDIR = "g2_example_nlevel"

# Path to mininet traffic flow configuration file
TRAFFIC_CONF_FILE = "input/traffic.conf"

# Path to mininet configuration file
G2_CONF_FILE = "input/g2.conf"

# If no scale factor specified using '-f', use the following scale factors instead
DEFAULT_SCALE_FACTOR = [1, 10, 100]

def is_valid_cc(ccAlgo):
    """
    Validates congestion control algorithm input.
    Returns:
        Valid string on success and None on error
    """
    if ccAlgo in VALID_CONGESTION_CONTROL_PROTOS:
        return ccAlgo
    else:
        return None

def parse_cmdline_args():
    """
    Command line parser.
    Returns:
        None on error and valid configuration on success
    """
    parser = argparse.ArgumentParser(description='Linear BPG network generator')
    parser.add_argument("-t", "--test", required=True, help="directory containing base topology configuration")
    parser.add_argument("-l", "--links", type=int, required=True, help="number of links")
    parser.add_argument("-cc", "--cc_algo", type=lambda x: is_valid_cc(x), required=True, help="Congestion control algorithm to use: bbr/cubic/reno")
    parser.add_argument("-f", "--factor", type=int, required=False, help="max scaling factor")

    config_read = vars(parser.parse_args())
    if config_read['links'] > 8 and os.path.basename(config_read['test'].rstrip('/')) == 'g2_network10':
        print "ERROR: Cannot support more than 8 links with this base configuration. "\
              "Exceeding 8 links could violate Mininet's 1Gbps maximum link capacity limit."
        exit(1)
    return config_read

def create_g2conf_file(baseG2ConfFile, destG2ConfFile, ccAlgo):
    """
    Creates a G2 configuration file for Mininet, based on base
    configuration file 'baseG2ConfFile', and by modifying it for
    the TCP congestion control algorithm 'ccAlgo'. Rest of the
    parameters are copied as-is from the base configuration file.
    Args:
        baseG2ConfFile(string): Base G2 configuration file to use
        destG2ConfFile(string): Destination G2 configuration file to write to
        ccAlgo(string): TCP congestion control algorithm to use
    """
    baseG2ConfFile = open(baseG2ConfFile, 'r')
    g2_conf_string = str()
    for line in baseG2ConfFile:
        # Replace the TCP CC algorithm with one passed
        if line.find('tcp_congestion_control') >= 0:
            line = "tcp_congestion_control: " + ccAlgo + "\n"
        g2_conf_string += line

    # Construct the final G2 configuration file.
    f_write = open(destG2ConfFile, 'w')
    f_write.write(g2_conf_string)
    f_write.close()
    baseG2ConfFile.close()

def create_traffic_file(destFlowFile, numLinks, scaleFactor):
    """
    Creates a traffic configuration file for Mininet. Based on
    the number of links to use 'numLinks', builds a base traffic
    flow profile for the experiment. Further based on scaling factor 'scaleFactor',
    repplicates each flow from base traffic flow profiles 'scaleFactor' times.
    Args:
        destFlowFile(string): Destination G2 configuration file to write to
        numLinks(int): Maximum number of links in the network
        scaleFactor(int): Number of times to replicate each flow
    """
    # For each link, we need two hosts. Given 'n' links, we need n+1 hosts.
    # Track source, destination hosts for each link. Assume hosts, links are
    # 1 based.
    # Format: hosts = {1: (h1, h2), 2: (h2, h3), ..., n: (hn, hn+1)}
    hosts = {}
    for link in range(1, numLinks + 1):
        hosts[link] = ('h' + str(link), 'h' + str(link + 1))

    # For each flow, we track list of links it traverses. Flows are 1 based.
    # If we define a flow to be between two consecutive links, given 'n' links,
    # we can have 'n-1' flows.
    # Format: flow_links = {1: [1, 2], 2: [2, 3], ..., n-1: [n-1, n]}
    flow = 1
    flow_links = {}
    for link in range(1, numLinks + 1):
        if link == numLinks:
            # Handles nth flow case.
            flow_links[flow] = [link]
            flow += 1
        else:
            # Create 'n-1' flows.
            flow_links[flow] = [link, link + 1]
            flow += 1

    # Finally, get the flow definitions in terms of source, destination hosts
    # based on the set of links they traverse.
    # Format: flows = {1: (h1, h3), 2: (h2, h4), ..., n-1: (hn-1, hn+1)}
    # For a given scaling factor 'x', replicate each flow 'x' times.
    flows = ""
    flowCtr = 1
    for scale in range(1, scaleFactor + 1):
        for flowIdx in range(1, flow):
            src_link = flow_links[flowIdx][0]
            dst_link = flow_links[flowIdx][-1]
            src_host = hosts[src_link][0]
            dst_host = hosts[dst_link][1]
            flows += str(flowCtr) + ", " + str(src_host) + ", " + str(dst_host) + ", 256000000, 0, 0.0\n"
            flowCtr += 1

    # Put together traffic configuration file.
    header = "# Format: int job id, source host, destination host, number of bytes to transfer, time in seconds to start the transfer, expected fair share of the flow in Mbits/sec\n"
    traffic_conf_string = header
    traffic_conf_string += flows
    #print traffic_conf_string
    f_write = open(destFlowFile, 'w')
    f_write.write(traffic_conf_string)
    f_write.close()

def main():
    """
    Entry point of script.
    """
    CONFIG = parse_cmdline_args()
    maxLinks = CONFIG['links']
    ccAlgo = CONFIG['cc_algo']
    testDir = CONFIG['test']
    testDir = testDir.rstrip('/') # remove a trailing '/', if present

    # Use scale if specified, otherwise resort to defaults [1x, 10x, 100x]
    if CONFIG['factor']:
        scale_factors = [f for f in range(1, CONFIG['factor'] + 1)]
    else:
        scale_factors = DEFAULT_SCALE_FACTOR

    # Create a fresh directory to hold all the examples, 'g2_example_nlevel' by default.
    outDir = os.path.join(os.curdir, EXAMPLE_BASEDIR)
    if not os.path.isdir(outDir):
        print "%s directory not present. Creating it..."%(os.path.abspath(outDir))
        os.makedirs(outDir)
    print "Creating configuration for: %d links, with scaling of %s."%(maxLinks, scale_factors)

    # Prepare the name and path of new example network, e.g. g2_example_nlevel/10x_3links_bbr/.
    for scale in scale_factors:
        for links in range(1, maxLinks + 1):
            testName = str(scale) + 'x' + str(links) + 'links' + ccAlgo
            destDir = os.path.join(outDir, testName)
            if not os.path.isdir(destDir):
                os.makedirs(destDir)
                os.makedirs(os.path.join(destDir, 'input'))
                os.makedirs(os.path.join(destDir, 'output'))
            create_g2conf_file(os.path.abspath(os.path.join(testDir, G2_CONF_FILE)),
                            os.path.abspath(os.path.join(destDir, G2_CONF_FILE)),
                            ccAlgo)
            create_traffic_file(os.path.abspath(os.path.join(destDir, TRAFFIC_CONF_FILE)), links, scale)

if __name__ == "__main__":
    main()
