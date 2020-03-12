"""
G2_RIGHTS.

This module defines Monitor class to monitor CPU and memory utilization.

Pre-requisite non-standard Python module(s):
    psutil

"""

import time
import threading
import psutil

class Monitor():
    def __init__(self, interval=1):
        """ Monitor constructor.

        Args:
            interval (int): the polling interval.

        Attributes:
            interval (int): The polling interval.
            readings (list): Observations.
            _running (bool): State of monitor.
         """

        self.interval = interval
        self.readings = []
        self._running = False

    def start(self):
        """Start the monitor.
        """

        self._running = True

    def monitor(self):
        """Monitor CPU and memory usage.
        """

        if self._running:
            # Current time
            ctime = time.time()
            # A float representing the current system-wide CPU utilization as a percentage.
            cpu = psutil.cpu_percent()
            # System memory usage percent = (total - available) * 100.0 / total
            memData = dict(psutil.virtual_memory()._asdict())
            vmem = memData['percent']
            self.readings.append((ctime, cpu, vmem))
            t = threading.Timer(self.interval, self.monitor)
            t.start()

    def stop(self):
        """Stop a monitor.
        """

        self._running = False

    def writeReadings(self, filepath):
        """Write CPU and memory usage to a CSV file; header row is also written..

        Args:
            filepath (str): Path to output file.

        """

        with open(filepath, "w") as fs:
            header = "timestamp,cpuPercent,memoryPercent"
            fs.write(header + '\n')
            for t, c, m in self.readings:
                line = str(t)+','+str(c)+','+str(m)
                fs.write(line + '\n')
