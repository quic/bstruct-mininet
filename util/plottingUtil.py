#!/usr/bin/python

"""
G2_RIGHTS.

This module post-processes Mininet experiment results to generate custom plots.
Currently, it supports customizing axes range for 'unique pairs' plots and 'average throughput' plots.

Usage: sudo plottingUtil.py [-h] -i INPUT -o OUTPUT [-n NUM_UNIQUE_PLOTS] [-xmin XMIN] [-xmax XMAX] [-ymin YMIN] [-ymax YMAX]

"""
import argparse
import sys
from mininet.clean import cleanup

sys.path.append("../")
from .topoGraphUtil import getG2Inputs
from .resultsProcessing import ResultGenerator
from g2Launcher import ConfigHandler, NetworkSimulator

def parse():
    """Parse command-line arguments.

    """

    global args
    global parser

    parser = argparse.ArgumentParser(description='Module to generate custom plots')
    parser.add_argument("-i", "--input", required=True, help="directory containing input config files")
    parser.add_argument("-o", "--output", required=True, help="directory that receives output files and benchmarks")
    parser.add_argument("-n", "--num-unique-plots", type=int, default=1, help="number of unique pairs plots to generate with custom axis limits")
    parser.add_argument("-xmin", "--xmin", type=int, default=-1, help="xaxis left value, must be an integer greater than or equal to -1, where -1 means the axis is set to it's default value")
    parser.add_argument("-xmax", "--xmax", type=int, default=-1, help="xaxis right value, must be an integer greater than or equal to -1, where -1 means the axis is set to it's default value")
    parser.add_argument("-ymin", "--ymin", type=int, default=-1, help="yaxis bottom value, must be an integer greater than or equal to -1, where -1 means the axis is set to it's default value")
    parser.add_argument("-ymax", "--ymax", type=int, default=-1, help="yaxis top value, must be an integer greater than or equal to -1, where -1 means the axis is set to it's default value")
    parser.add_argument("--no-legend", action="store_false", help="Whether to remove legend")
    parser.add_argument("--sample", type=int, default=1, help="Interval for sampling the collected data")
    args = parser.parse_args()

def main():
    cleanup()

    # Parse command-line arguments.
    parse()

    # Validate xaxis and yaxis input values.
    if args.xmin < -1 or args.xmax < -1 or args.ymin < -1 or args.ymax < -1:
        print("Invalid values entered for axis limits. View help using -h.")
        return
    xlimits = (args.xmin, args.xmax)
    ylimits = (args.ymin, args.ymax)

    ch = ConfigHandler(args.input, args.output)
    # If there is an exception in config parsing, ch.config will be None.
    if not ch.config:
        print("Error while reading config; exiting...\n")
        return

    # Simulate network.
    # We simulate the network only to access the required configurations such as nodes, links, and paths from underlying Mininet object.
    # However, we don't start the network or run tests on it.
    network = NetworkSimulator(ch)
    # Obtain details on flows, links, and RTT.
    (C, F, flowInfo) = getG2Inputs(ch, network)
    # Process iperf output and generate results.
    rg = ResultGenerator(ch, C, F, flowInfo)
    iperfResults = rg.parseIperfOutput()

    # Generate throughput plots using specified axis range.
    # Plot throughput of unique flows with custom axis range.
    numPlots = args.num_unique_plots
    # rg.plotUniqueInstances(iperfResults, numPlots, xlimits, ylimits)
    # Plot average throughput of unique flows with custom axis range.
    # rg.plotAvgFlows(iperfResults, xlimits, ylimits)
    rg.plotResults(iperfResults, use_legend=args.no_legend, sample_data_n = args.sample)
    # Clean Mininet.
    cleanup()

if __name__ == "__main__":
    main()
