#!/usr/bin/python

"""
G2_RIGHTS.

This module processes output from traffic generation module (iperf results).
It stores the results into a .json file and generates graphs.

"""

import numpy as np
import re
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend.
import matplotlib.pyplot as plt
from collections import defaultdict, OrderedDict
import json
from os import listdir
from os.path import isfile, join
import time

# Globals
# Regular expression to parse iperf output.
ipRegex = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
timeRegex = re.compile(r"\d+\.\d+-\s?\d+\.\d+\ssec")

# Multiplication factors for converting data units.
# Todo: Future work- (low priority): check for other possible units.
factorToMB = {
    'Bytes': (1.) / (1000*1000),
    'KBytes': (1.) / (1000),
    'MBytes': 1.,
    'GBytes': 1000.,
    'TBytes': 1000. * 1000
    }
factorToMbps = {
    'bits/sec': (1.) / (1000*1000),
    'Kbits/sec': (1.) / (1000),
    'Mbits/sec': 1.,
    'Gbits/sec': 1000.,
    'Tbits/sec': 1000. * 1000,
    }

# Colors to use while plotting lines.
# To plot lines more than the number of colors below, we will use black by default.
plotColors = ['crimson', 'olive', 'green', 'teal', 'purple', 'red',
    'brown', 'grey', 'cyan', 'magenta', 'yellow']

# Number of unique flow plots.
MAXUNIQUEFLOWPLOTS = 5

class ResultGenerator:
    """Post-process monitoring output and generate results and plots.

    Args:
        config (ConfigHandler): A ConfigHandler object encapsulating the network configurations.
        C (dict): The capacity dictionary [linkID] -> linkCapacity.
        F (dict): The flow dictionary [flowID] -> [linkIDs].
        flowInfo (dict): Mapping of flow ID to flow info including RTT and links traversed.
    Attributes:
        config (ConfigHandler): A ConfigHandler object encapsulating the network configurations.
        jobs (list): List of traffic flows (each a Python dict), as obtained from TraceParser.
        prefix (str): Prefix to use for result files.
        outPath (str): Path to store results and plots.
        C (dict): The capacity dictionary [linkID] -> linkCapacity.
        F (dict): The flow dictionary [flowID] -> [linkIDs].
        L (dict): [linkID] -> linkStr.
        flowInfo (dict): Mapping of flow ID to flow info including RTT and links traversed.

    """

    def __init__(self, config, C, F, flowInfo):
        self.config = config
        self.jobs = config.trace.jobs
        self.prefix = config.prefix
        self.outPath = config.benchPath
        self.C = C
        self.F = F
        self.L = config.topoData['L']
        self.flowInfo = flowInfo

    def parseIperfOutput(self):
        """For a list of flows, parses iperf output from 'outPath' directory.
        Parsing logic is highly based on the output format of iperf.
        Generates a dictionary that can be easily processed to compute statistics and plot graphs.

        Returns:
            dict: That contains, for each flow, its RTT, links traversed, and the useful statistics parsed from iperf output.

        """

        iperfResults = defaultdict(dict)
        pfx = join(self.outPath, "%s_iperf_" %(self.prefix))

        for flow in self.jobs:
            fid = flow['id']
            iperfResults[fid]['sender'] = flow['src']
            iperfResults[fid]['receiver'] = flow['dst']
            iperfResults[fid]['flowStr'] = self.flowInfo['f'+str(fid)]['flowStr']
            iperfResults[fid]['links'] = self.flowInfo['f'+str(fid)]['links']
            iperfResults[fid]['rtt'] = self.flowInfo['f'+str(fid)]['rtt']
            iperfResults[fid]['senderTs'] = []
            iperfResults[fid]['senderMbps'] = []
            iperfResults[fid]['senderAvgMbps'] = 0.0
            iperfResults[fid]['receiverTs'] = []
            iperfResults[fid]['receiverMbps'] = []
            iperfResults[fid]['receiverAvgMbps'] = 0.0
            iperfResults[fid]['receiverMBytes'] = []
            iperfResults[fid]['receiverTotalMBytes'] = 0.0
            iperfResults[fid]['completionTime'] = 0.0
            iperfFiles = ["%sclient_%d.txt" %(pfx, fid), "%sserver_%d.txt" %(pfx, fid)]

            for fname in iperfFiles:
                isClient = False
                isServer = False
                timeReadings = []
                sizeReadings = []
                bwReadings = []
                with open(fname) as fs:
                    fileContent = fs.readlines()
                isFirstLine = False
                for line in fileContent:
                    if "Client connecting to" in line:
                        isClient = True
                    elif "Server listening on TCP port" in line:
                        isServer = True

                    if timeRegex.search(line):
                        ts = timeRegex.findall(line)[0] # '0.0- 1.0 sec' OR '9.0-10.0 sec'
                        startSec = float(ts.split('-')[0].strip())
                        endSec = ts.split('-')[1].strip()
                        endSec = float(endSec[:-3].strip()) # Remove substring 'sec' from end.

                        # Detect if the last line in the file is reporting cumulative stats of iperf run.
                        # If so, we exclude the cumulative stats from the timeseries.
                        # 'first line' has pattern "0.0- 'interval' sec"
                        # 'last line' has pattern "0.0- 'max' sec", if it reports cumulative stats.
                        if startSec == 0.0 and endSec > 0.0:
                            if not isFirstLine:
                                isFirstLine = True
                            else: # 'last line'
                                continue
                        splits = line.strip().split() # Splits at one or more spaces.
                        # The last four splits are size unit bw unit
                        bwUnit = splits[-1]
                        MbitsPerSec = float(splits[-2])
                        MbitsPerSec = MbitsPerSec * factorToMbps[bwUnit]

                        sizeUnit = splits[-3]
                        MBytes = float(splits[-4])
                        MBytes = MBytes * factorToMB[sizeUnit]

                        if endSec != 0.0 or MBytes != 0.0 or MbitsPerSec != 0.0:
                            timeReadings.append(endSec)
                            sizeReadings.append(MBytes)
                            bwReadings.append(MbitsPerSec)
                # Store statistics to results.
                if not timeReadings:
                    continue
                if isClient:
                    iperfResults[fid]['senderTs'] = [t + flow['time'] for t in timeReadings]
                    iperfResults[fid]['senderMbps'] = bwReadings
                    iperfResults[fid]['senderAvgMbps'] = np.mean(bwReadings)
                elif isServer:
                    iperfResults[fid]['receiverTs'] = [t + flow['time'] for t in timeReadings]
                    iperfResults[fid]['receiverMbps'] = bwReadings
                    iperfResults[fid]['receiverAvgMbps'] = np.mean(bwReadings)
                    iperfResults[fid]['receiverMBytes'] = sizeReadings
                    iperfResults[fid]['receiverTotalMBytes'] = np.sum(sizeReadings)
                    iperfResults[fid]['completionTime'] = timeReadings[-1]

        # Convergence time computation.
        # Todo: Future work- better way of selecting window and threshold.
        # Sliding window size, could be set to 10% of the time points, for example.

        # Read parameters from config.
        convTimeType = self.config.convTimeType
        window = int(self.config.convWindow)
        threshold = float(self.config.convThresh)
        numSamples = int(self.config.convNumSamples)
        if convTimeType == 'FS':
            fairShares = [f['share'] for f in self.jobs]
            convTimes = self.getFSConvergenceTime(iperfResults, fairShares, window, threshold)
        elif convTimeType == 'No-FS':
            convTimes = self.getConvergenceTime(iperfResults, window, numSamples, threshold)

        for ID, t in convTimes:
            iperfResults[ID]['convergenceTime'] = t

        return iperfResults

    def getConvergenceTime(self, iperfDict, win, numSamples, thresh):
        """Compute convergence time for given iperf results without using expected max-min fair shares.
        A flow is considered converged at time t if, t is the earliest time when,
        ( (A(t) - A(t-1)) / A(t-1) ) <= thresh, is true for numSamples number of consecutive windows,
        where A(t) is the average throughput of 'win' number of observations starting at time t.

        Args:
            iperfDict (dict): Results of iperf.
            win (int): size of sliding window, e.g., 5.
            numSamples (int): number of consecutive windows to compare.
            thresh (float): threshold to determine two average throughput values are close, e.g., 0.05.


        Returns:
            list: List of tuples in form (flow ID, convergence time). Convergence time is set to -1 if the flow never converged.

        """

        res = []
        for flowID, iperfResult in iperfDict.items():
            converged = False
            times = np.array(iperfResult['receiverTs'])
            bws = np.array(iperfResult['receiverMbps'])
            # We now loop over the throughput observations.
            # In each iteration, we extract a window of size 'win' and compare 'numSamples' of subsequent windows.
            # Therefore, after index (len(times) - (win + numSamples -2) - 1), this process will hit the end of the list.
            maxIdx = len(times) - (win + numSamples -2)
            for t in range(maxIdx):
                nMatch = 0
                for z in range(t, t + numSamples):
                    Avg_t1 = np.mean(bws[z : z+win])
                    Avg_t2 = np.mean(bws[z+1 : z+1+win])
                    # Avoid divide by zero error.
                    # Avg_t1 can be 0.0 if the receiver did not receive any data for a sequence of 'win' number of time points.
                    if not Avg_t1:
                        continue
                    # Check if the average values of the two windows are close.
                    ratio = abs((Avg_t1 - Avg_t2) / Avg_t1)
                    if ratio > thresh:
                        break
                    nMatch += 1
                if nMatch == numSamples:
                    res.append((flowID, times[t]))
                    converged = True
                    break # Report the first time when the flow converged.
            if not converged:
                res.append((flowID, -1))
        return res

    def getFSConvergenceTime(self, iperfDict, shares, win, thresh):
        """Compute convergence time for given iperf results and expected max-min fair shares.
        A flow is considered converged at time t if,
        t is the earliest time when the RMSD of 'window' number of throughput values
        with respect to 'share' was within  ('share'+-'thresh').

        Args:
            iperfDict (dict): Results of iperf.
            shares (list): List of float values depicting fair-share of each flow.
            win (int): size of sliding window.
            thresh (float): size of boundary on either side of fair-share.

        Returns:
            list: List of tuples in form (flow ID, convergence time). Convergence time is set to -1 if the flow never converged.

        """

        res = []
        for flowID, iperfResult in iperfDict.items():
            converged = False
            times = np.array(iperfResult['receiverTs'])
            bws = np.array(iperfResult['receiverMbps'])
            maxIdx = len(times) - win
            for i in range(maxIdx):
                sample = bws[i:i+win]
                # Root mean square deviation of the window
                windowRmsd = np.sqrt(np.sum(np.square(sample - shares[flowID-1])) / (len(sample) - 1))
                if windowRmsd < thresh:
                    res.append((flowID, times[i]))
                    converged = True
                    break # Report the first time when the flow converged.
            if not converged:
                res.append((flowID, -1))
        return res

    def writeToJson(self, results):
        """Dump results to a json file.

        Args:
            results defaultdict(dict): Parsed results obtained from iperf output.

        """

        resFile = join(self.outPath, "%s_iperf_all.json" %(self.prefix))
        with open(resFile, "w") as fs:
            json.dump(results, fs, indent=2, sort_keys=True)
        fs.close()

    def writeToCsv(self, results):
        """Write results to a CSV files; header row is also written in each file.

        Args:
            results defaultdict(dict): Parsed results obtained from iperf output.

        """

        # CSV file for average and cumulative stats.
        csvFile = join(self.outPath, "%s_avg_results.csv" %(self.prefix))
        with open(csvFile, "w") as fs:
            header = "flowID,senderAvgMbps,receiverTotalMBytes,receiverAvgMbps,completionTime,convergenceTime,RTT(ms)"
            fs.write(header + '\n')
            for k, v in results.items():
                line = str(k)+','+str(v['senderAvgMbps'])+','+str(v['receiverTotalMBytes'])+','+str(v['receiverAvgMbps'])+','+str(v['completionTime'])+','+str(v['convergenceTime'])+','+str(v['rtt'])
                fs.write(line + '\n')
        fs.close()

        # One file per flow containing timeseries of send and receive throughput.
        for k,v in results.items():
            csvFile = join(self.outPath, "%s_bw_flow%d.csv" %(self.prefix, k))
            with open(csvFile, "w") as fs:
                header = "senderTs,senderMbps,receiverTs,receiverMbps"
                fs.write(header + '\n')
                zipped = zip(v['senderTs'], v['senderMbps'], v['receiverTs'], v['receiverMbps'])
                for st, sm, rt, rm in zipped:
                    line = str(st)+','+str(sm)+','+str(rt)+','+str(rm)
                    fs.write(line + '\n')
            fs.close()

    def getMaxCompletionTime(self, results):
        """Output completion time of the slowest flow

        Args:
            results defaultdict(dict): Parsed results obtained from iperf output.

        """
        times = []
        for k, v in results.items():
                times.append(v['completionTime'])
        return max(times)

    def getUniqueEndPointPairs(self, results):
        """
        Obtain a list of unique end point pairs from traffic flows.

        Args:
            results defaultdict(dict): Parsed results obtained from iperf output.

        Returns:
            list: A list of unique end point tuples: (flow_id, src, dst).

        """

        pairs = []
        keyAndPairs = []
        for k,v in results.items():
            src = v["sender"]
            dst = v["receiver"]
            if (src, dst) in pairs:
                continue
            else:
                pairs.append((src, dst))
                keyAndPairs.append((k, src, dst))
        return keyAndPairs

    def plotSingleFlow(self, flowID, flow):
        """Plot a line graph of throughput timeseries for a given flow; separate lines for client and server.
        Generates the graph in outPath/prefix_bw_flow<flowID>.pdf file.

        Args:
            flowID (int): Flow ID.
            flow (dict): Represents statistics for the flow as parsed from iperf outputs.

        """

        fileLabel = self.prefix
        fig = plt.figure()

        # Client side data.
        ts = flow["senderTs"]
        mbps = flow["senderMbps"]
        plt.plot(ts, mbps, label='Transmission', color='orangered', linestyle=':', marker='+', linewidth=0.75)
        if len(ts) > 1:
            plt.plot(ts, [flow["senderAvgMbps"]]*len(ts), label='Avg. Transmission', color='black', linestyle=':')

        # Server side data.
        ts = flow["receiverTs"]
        mbps = flow["receiverMbps"]
        plt.plot(ts, mbps, label='Receive', color='blue', linestyle='--', marker='x', linewidth=0.75)
        if len(ts) > 1:
            plt.plot(ts, [flow["receiverAvgMbps"]]*len(ts), label='Avg. Receive', color='black', linestyle='--')

        plt.xlim(xmin=0)
        plt.xlabel('Time (sec)')
        plt.ylabel('Throughput (Mbits/sec)')
        plt.title("Throughput results for transfer from '%s' to '%s'" %(flow["sender"], flow["receiver"]))
        plt.legend()

        outFile = join(self.outPath, "%s_bw_flow%d.pdf" %(fileLabel, flowID))
        fig.savefig(outFile)
        plt.close(fig)

    def plotAllFlows(self, res, title, outFile, xlimits=None, ylimits=None):
        """Plot server throughput timeseries for all flows in single graph, similar to Figure 6 of BBR paper.
        Generates the graph in outPath/prefix_bw_all.pdf file.

        Args:
            res (dict): A dictionary containing statistics for all flows, as parsed from iperf outputs.
            title (str): Plot title.
            outFile (str): Path to save the plot PDF.
            xlimits (tuple): Range of x-axis (left, right).
            ylimits (tuple): Range of y-axis (top, bottom).

        """

        fig = plt.figure()
        labels = []
        data = []
        for flow in res.values():
            data.append((flow['receiverTs'], flow['receiverMbps']))
            labels.append(flow['flowStr']+ ', RTT=' + str(flow['rtt']) + 'ms')

        la = len(data)
        lb = len(plotColors)
        if la > lb:
            colors = plotColors[:]
            for i in range(lb, la):
                colors.append('black')
        else:
            colors = plotColors[:la]

        for (x,y), cl, lab in zip(data, colors, labels):
            plt.plot(x, y, color=cl, label=lab, linewidth=0.85)

        # Set axes range.
        plt.xlim(left=0)
        plt.ylim(bottom=0)
        if xlimits:
            if xlimits[0] > 0:
                plt.xlim(left=xlimits[0])
            if xlimits[1] > 0:
                plt.xlim(right=xlimits[1])
        if ylimits:
            if ylimits[0] > 0:
                plt.ylim(bottom=ylimits[0])
            if ylimits[1] > 0:
                plt.ylim(top=ylimits[1])

        plt.xlabel('Time (sec)')
        plt.ylabel('Throughput (Mbits/sec)')
        plt.title(title)
        plt.legend()
        # plt.grid(True)
        fig.savefig(outFile)
        plt.close(fig)

    def plotUniqueInstances(self, results, numPlots, xlimits=None, ylimits=None):
        """ Plot N instances of unique-flows-plots: throughput timeseries of each unique set of flows.
        While scaling a network example, the traffic flows are replicated n times (n = 10 or 100, for example).

        Args:
            results defaultdict(dict): Parsed results obtained from iperf output.
            numPlots (int): Maximum number of unique-flow-plots to generate.
            xlimits (tuple): Range of x-axis (left, right).
            ylimits (tuple): Range of y-axis (top, bottom).

        """

        uniqPairs = self.getUniqueEndPointPairs(results)
        numUniqFlows = len(uniqPairs)
        flowIDs = sorted([int(x) for x in results.keys()])
        maxPlots = numPlots
        # Let the network configuration consists of m traffic flows, which could be replicated n times.
        # First, we extract each of the n sets (outer for loop).
        # Next, we extract each of the m traffic flows within each set (inner for loop).
        # Finally, we copy the results to 'uniqPairsRes', sort them on flow ID, and call plotAllFlows.
        for i in xrange(0, len(flowIDs), numUniqFlows):
            if not maxPlots:
                break
            uniqPairsRes = {}
            for j in range(numUniqFlows):
                uniqPairsRes[flowIDs[i+j]] = results[flowIDs[i+j]]
            # Sort the results on flow_id.
            uniqPairsRes = OrderedDict(sorted(uniqPairsRes.items()))
            title = "Throughput results"
            outFile = join(self.outPath, "%s_bw_all_unique_pairs_%d.pdf" %(self.prefix,i+1))
            if xlimits or ylimits:
                outFile = join(self.outPath, "%s_bw_all_unique_pairs_%d_custom_%s.pdf" %(self.prefix,i+1,time.time()))
            self.plotAllFlows(uniqPairsRes, title, outFile, xlimits, ylimits)
            maxPlots -= 1

    def plotAvgFlows(self, results, xlimits=None, ylimits=None):
        """ Plot average flow throughput; for each flow, average is computed over all it's replicas.

        Args:
            results defaultdict(dict): Parsed results obtained from iperf output.
            xlimits (tuple): Range of x-axis (left, right).
            ylimits (tuple): Range of y-axis (top, bottom).

        """

        uniqPairs = self.getUniqueEndPointPairs(results)
        numUniqFlows = len(uniqPairs)
        flowIDs = sorted([int(x) for x in results.keys()])
        # Create a mapping of a flow ID to it's replicas.
        # group_id is the ID of first flow of the group.
        # flow_id -> [duplicate_flow_id]
        flowGroups = defaultdict(list)
        for i in range(1, numUniqFlows+1):
            flowGroups[i] = [j for j in xrange(i, len(flowIDs)+1, numUniqFlows)]

        # Create a dictionary {group_id : group_avg_throughput_timeseries}
        avgResults = {}
        for g in flowGroups:
            IDList = flowGroups[g]
            currGrp = {}
            maxLen = 0
            for ID in IDList:
                tsList = results[ID]['receiverTs']
                if len(tsList) > maxLen:
                    maxLen = len(tsList)
                    currGrp['receiverTs'] = tsList
                    currGrp['flowStr'] = results[ID]['flowStr']
                    currGrp['rtt'] = results[ID]['rtt']
            currGrp['receiverMbps'] = np.zeros(maxLen, dtype='float')
            for ID in IDList:
                mbps = np.array(results[ID]['receiverMbps'], dtype='float')
                currGrp['receiverMbps'][:len(mbps)] += mbps
            currGrp['receiverMbps'] = np.divide(currGrp['receiverMbps'], len(IDList))
            avgResults[g] = currGrp
        # Sort the results on group_id (i.e., flow_id).
        avgResults = OrderedDict(sorted(avgResults.items()))

        # Write each flow group's avg. throughput to a csv file.
        csvFile = join(self.outPath, "%s_avg_flow_throughput.csv" %(self.prefix))
        with open(csvFile, "w") as fs:
            header = "flowID,receiverAvgMbps"
            fs.write(header + '\n')
            for k, v in avgResults.items():
                line = str(k)+','+str(np.mean(v['receiverMbps']))
                fs.write(line + '\n')

        title = "Throughput results"
        outFile = join(self.outPath, "%s_bw_all_unique_pairs_avg.pdf" %self.prefix)
        if xlimits or ylimits:
            outFile = join(self.outPath, "%s_bw_all_unique_pairs_avg_custom_%s.pdf" %(self.prefix, time.time()))
        self.plotAllFlows(avgResults, title, outFile, xlimits, ylimits)

    def plotResults(self, results):
        """Plotting parsed results.

        Args:
            results defaultdict(dict): Parsed results obtained from iperf output.

        """

        # Plotting all flows (receiver side) in one graph.
        title = "Throughput results"
        outFile = join(self.outPath, "%s_bw_all.pdf" %self.prefix)
        self.plotAllFlows(results, title, outFile)

        # Plotting each flow in a separate graph.
        plotEachFlow = self.config.plotEachFlow
        if plotEachFlow:
            for k, v in results.items():
                self.plotSingleFlow(k, v)
        else:
            uniqPairsRes = {}
            uniqPairs = self.getUniqueEndPointPairs(results)
            for (k,_, _) in uniqPairs:
                uniqPairsRes[k] = results[k]
            # Sort the results on flow_id.
            uniqPairsRes = OrderedDict(sorted(uniqPairsRes.items()))
            for k,v in uniqPairsRes.items():
                self.plotSingleFlow(k, v)
        # Plot n instances of unique-flow-plots (receiver side).
        self.plotUniqueInstances(results, MAXUNIQUEFLOWPLOTS)
        # Plot average unique flows (receiver side) in one graph.
        self.plotAvgFlows(results)

    def plotSwitchStats(self):
        """Plot timeseries of queued packets and dropped packets.
        Output is written to files prefixed with 'prefix' and interface name.

        Args:
            ifList (list): List of switch interfaces.

        """

        pfx = self.prefix
        # list of all files that start with 'prefix_switch_stats'
        mypath = self.outPath
        switchFiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
        switchFiles = [join(mypath, f) for f in switchFiles if (f.startswith('%s_switch_stats' %pfx)) and ('.csv' in f)]

        for filename in switchFiles:
            outPrefix = filename[:-4] # Remove '.csv' from end.
            splits = outPrefix.split('_')
            outPrefix = '_'.join(splits[-1:]) # e.g., 's8-eth2'

            with open(filename) as fr:
                content = fr.readlines()
            if len(content) > 2:
                # Means that we have some data for this interface.
                # Discard header row
                content = content[1:]
                tsStart = float(content[0].split(',')[0])
                # Discard first row as it will always have 0 for both stats.
                content = content[1:]

                ts = []
                queued = []
                dropped = []
                for line in content:
                    splits = line.split(',')
                    ts.append(float(splits[0].strip()) - tsStart)
                    queued.append(int(splits[1].strip()))
                    dropped.append(int(splits[2].strip()))

                # Plot queued packets (instantaneous measure)
                fig = plt.figure()
                plt.plot(ts, queued, label='Queued packets', color='blue', marker='.', linewidth=0.85)
                plt.xlim(xmin=0)
                plt.ylim(ymin=0)
                plt.xlabel('Time (sec)')
                plt.ylabel('Queue size (packets)')
                plt.title("Queue size timeseries for interface %s" %outPrefix)
                plt.legend()
                outFile = join(self.outPath, "%s_%s_queue_size.pdf" %(pfx, outPrefix))
                fig.savefig(outFile)

                # Plot dropped packets (cumulative measure)
                fig = plt.figure()
                plt.plot(ts, dropped, label='Dropped packets', color='blue', marker='.', linewidth=0.85)
                plt.xlim(xmin=0)
                plt.ylim(ymin=0)
                plt.xlabel('Time (sec)')
                plt.ylabel('Dropped packets')
                plt.title("Cumulative dropped packets for interface %s" %outPrefix)
                plt.legend()
                outFile = join(self.outPath, "%s_%s_dropped_packets.pdf" %(pfx, outPrefix))
                fig.savefig(outFile)

    def plotUtilization(self):
        """Plot CPU and memory utilization.

        """

        csvFile = join(self.outPath, "%s_cpu_memory_usage.csv" %(self.prefix))
        outFile = join(self.outPath, "%s_cpu_memory_usage.pdf" %(self.prefix))
        with open(csvFile) as fr:
            content = fr.readlines()
            if len(content) > 2:
                # Means that we have some data for this interface.
                # Discard header row.
                content = content[1:]
                tsStart = float(content[0].split(',')[0])

                ts = []
                cpu = []
                mem = []
                for line in content:
                    splits = line.split(',')
                    ts.append(float(splits[0].strip()) - tsStart)
                    cpu.append(float(splits[1].strip()))
                    mem.append(float(splits[2].strip()))
                fig, ax = plt.subplots(nrows=2, ncols=1)
                # Plot CPU timeseries.
                ax[0].plot(ts, cpu, label='CPU utilization', color='red', marker=None, linewidth=0.9) #row=0
                cpu_median = np.median(cpu)
                ax[0].hlines(cpu_median, min(ts), max(ts), colors='red', linestyles='--', label='Median')

                # Plot memory timeseries
                ax[1].plot(ts, mem, label='Memory utilization', color='blue', marker=None, linewidth=0.9) #row=1
                mem_median = np.median(mem)
                ax[1].hlines(mem_median, min(ts), max(ts), colors='blue', linestyles='--', label='Median')
                ax[1].set_xlabel('Elapsed time (sec)')

                for row in ax:
                    row.set_ylim([0, 100])
                    row.set_ylabel('Utilization (%)')
                    row.legend()

                fig.savefig(outFile)
