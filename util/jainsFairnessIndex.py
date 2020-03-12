#!/usr/bin/python
"""
G2_RIGHTS.

Compute Jain's fairness index.
Jain's index is a metric that reflects the fairness of a set of values.
The index value ranges from 1/n (worst case) to 1 (best case), where n is the number of values in the set.

This module is imported in g2Launcher.py to compute the fairness index automatically as part of a Mininet experiment.
Additionally, this module can also be invoked separately (as shown in the usage and example below).

Usage: python jainsFairnessIndex.py [-h] -r RESULTS_JSON_FILE -t TRAFFIC_CONF_FILE
Example: python jainsFairnessIndex.py -r ../examples/g2_network1/output/benchmarks/20190624_bbr_iperf_all.json -t ../examples/g2_network1/input/traffic.conf

"""

import numpy as np
import argparse
import json
from traceParser import TraceParser

def calculateJainsIndex(rates, expectedRates):
    """Compute Jain's fairness index.

    Args:
        rates (list): list of observed flow rates (throughputs).
        expectedRates (list): list of theoretical optimal transmission rates.

    Returns:
        float: the Jain's fairness index.

    """

    normalizedRates = np.array(rates) / np.array(expectedRates)
    index = np.power(np.mean(normalizedRates), 2) / np.mean(np.power(normalizedRates, 2))
    return index if index <= 1 else 1  # to avoid overflow

def parse():
    """Parse command-line arguments.

    """

    parser = argparse.ArgumentParser(description="Compute Jain's fairness index")
    parser.add_argument("-r", "--results-json-file", required=True, help="JSON file containing experiment results")
    parser.add_argument("-t", "--traffic-conf-file", required=True, help="traffic.conf file that contains theoretical optimal transmission rates")

    config_read = vars(parser.parse_args())
    return config_read

def main():
    CONFIG = parse()
    results_file = CONFIG['results_json_file']
    with open(results_file, "r") as fr:
        results = json.load(fr)
    traffic_conf_file = CONFIG['traffic_conf_file']
    trace = TraceParser(traffic_conf_file)
    flows = trace.jobs

    if not results:
        print "Error in reading experiment results."
        return
    if not flows:
        print "Error in reading traffic conf."
        return

    experimentRates = []
    expectedRates = []
    for flowID in range(1,len(flows) + 1):
        experimentRates.append(results[str(flowID)]['receiverAvgMbps'])
        for flow in flows:
            if flow['id'] == flowID:
                expectedRates.append(flow['share'])

    print("Jain's fairness index: %f" %calculateJainsIndex(experimentRates, expectedRates))

if __name__ == "__main__":
    main()
