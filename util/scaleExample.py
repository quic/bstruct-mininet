#!/usr/bin/python

"""
G2_RIGHTS.

This module generates a higher-scale example network given a base example network.
Specifically, it generates new traffic.conf by replicating existing network's traffic.conf by a specified factor.

"""
import argparse
import os
import shutil

def parse():
    """Parse command-line arguments.

    """

    parser = argparse.ArgumentParser(description='Scale a Mininet example test')
    parser.add_argument("-t", "--test", required=True, help="directory containing an example network")
    parser.add_argument("-f", "--factor", type=int, required=True, help="scaling factor")

    config_read = vars(parser.parse_args())
    return config_read

def main():
    CONFIG = parse()
    factor = CONFIG['factor']
    testDir = CONFIG['test']
    testDir = testDir.rstrip('/') # remove a trailing '/', if present
    testName = os.path.basename(testDir)
    # Prepare the name and path of new example network, e.g. examples/10x_g2_network1/.
    outName = str(factor) + 'x_' + testName
    testDir = os.path.abspath(testDir)
    print("Base example: {}".format(testDir))
    os.chdir(testDir)
    os.chdir("..")
    outPath = os.path.abspath(os.path.join(os.curdir, outName))
    if not os.path.isdir(outPath):
        os.mkdir(outPath)
        os.chdir(outPath)
        # Copy input/*.conf files.
        os.mkdir("input")
        shutil.copyfile(os.path.join(testDir, "input/traffic.conf"), os.path.join(os.curdir, "input/traffic.conf"))
        shutil.copyfile(os.path.join(testDir, "input/g2.conf"), os.path.join(os.curdir, "input/g2.conf"))

        # Replicate traffic flows 'factor' times.
        filename = os.path.join(os.path.abspath(os.curdir), "input/traffic.conf")
        with open(filename, 'r') as fr:
            fileContent = fr.readlines()
        writeLines = []
        maxID = 0
        if fileContent:
            for line in fileContent:
                line = line.strip()
                if line and not line.strip().startswith('#'):
                    ID = int(line.split(',')[0].strip())
                    if ID > maxID:
                        maxID = ID
                    writeLines.append(line)

        with open(filename, 'a') as fw:
            incr = 1
            for x in range(factor-1): # since we are appending
                for line in writeLines:
                    idx = line.find(",")
                    line = str(maxID + incr) + line[idx:]
                    fw.write("\n%s" % line)
                    incr += 1
        print("Successfully created example: {}".format(outPath))
        print("Change config in: {}".format(os.path.join(outPath, "input/g2.conf")))
    else:
        print("Desired example network already present: {}".format(outPath))

if __name__ == "__main__":
    main()
