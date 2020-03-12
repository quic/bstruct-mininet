#!/bin/bash
#
# G2_RIGHTS.
#
# Script that automates running G2 Mininet tests.
#
# Usage:
#   sudo g2MininetAutoTests.sh -e <ENVSETUP_FILE> -d <TESTS_DIR> [-t TESTS_LIST_TXTFILE] [-h]
#
# Please refer to README for further details.

# ####################################################################################

# --------------------------------------------
# Global variables
# --------------------------------------------
# Script basename
myName=$(basename -- "$0")

# Script name without extension
myNameNoExt=${myName%.sh}

gLockFile="/var/lock/myNameNoExt.lock"

# Enable debug logs
gVerbose=0

# Variable to hold environment setup script
gEnvFile=

# Variable to hold user specified test directory containing test samples
gTestDir=

# Variable to hold user specified test file. Used to specify subset of tests to run
# from a given test directory
gTestFile=

# Array to hold a list of tests to run
gTestList=()

# --------------------------------------------
# Functions
# --------------------------------------------

# Help function.
# Prints usage and exits
usage() {
  echo "${myName} -e <ENVSETUP_FILE> -d <TESTS_DIR> [-t TESTS_LIST_TXTFILE] [-l LOG_FILE ] [-h]"
  exit
}

# Process status function.
# Given a process name, returns PID if running, otherwise 0.
getProcessPID() {
  local ps_op=$(ps -o pid,args | grep -i "$1" | grep -v grep)
  local pid=$(echo $ps_op | awk '{print $1}')
  local cmd=$(echo $ps_op | awk '{print $2}')
  if [ -z "$pid" ]; then
    echo 0
  else
    echo $pid
  fi
}

# Util function to resolve a relative path to its absolute counterpart.
getAbsPath() {
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}

# Script input parser.
# Validates if we have all the mandatory parameters setup to proceed.
# On failure, prints usage and quits.
validateInputs() {
  # Mandatory inputs
  if [ -z $gEnvFile ] || [ -z $gTestDir ]; then
    echo "[ERROR] Missing mandatory arguments."
    usage
  fi

  if [ ! -f $gEnvFile ]; then
    echo "[ERROR] $gEnvFile not found. Please specify a valid environment paths file."
    usage
  fi

  if [ ! -d $gTestDir ]; then
    echo "[ERROR] $gTestDir not found. Please specify a valid test dir."
    usage
  elif [ ! "$(ls -a $gTestDir)" ]; then
    echo "[ERROR] $gTestDir empty. Please specify a valid test dir."
    usage
  fi

  if [ $gTestFile ] && [ ! -f $gTestFile ]; then
    echo "[ERROR] $gTestFile not found. Please specify a valid tests file."
    usage
  fi
}

# Command line argument parser.
# Parses command line arguments passed to this function.
parseCmdlineArgs() {
  # Atleast one valid argument?
  if [ $# -eq 0 ]; then
    usage
  fi

  # Parse input arguments
  while [ "$1" != "" ];
  do
    case $1 in
      -e | --env )            shift
                              gEnvFile=$(getAbsPath $1)
                              ;;
      -d | --testdir )        shift
                              gTestDir=$(getAbsPath $1)
                              ;;
      -t | --testfile )       shift
                              gTestFile=$(getAbsPath $1)
                              ;;
      -v | --gVerbose )       gVerbose=1
                              ;;
      -h | --help )           usage
                              exit
                              ;;
      * )                     usage
                              exit 1
    esac
    shift
  done

  # Do we have the inputs needed to proceed?
  validateInputs
}

# Test environment setup function.
# Calls the environment setup script passed with '-e' option to this script.
# Validates test setup. On failure, logs error and quits.
setupTestEnv() {
  # Run the environment setup script
  source $gEnvFile

  # Do we have all environment variables needed?
  if [ ! $MININET_SRC ] || [ ! $G2_MININET_SRC ] || [ ! $SFLOW_SRC ]; then
    echo "[ERROR] Please make sure $gEnvFile defines $MININET_SRC, $G2_MININET_SRC, $SFLOW_SRC variables"
    exit
  fi

  # Validate mininet environment
  if [ ! -f "${G2_MININET_SRC}/g2Launcher.py" ]; then
    echo "[ERROR] Failed to find G2 Mininet launcher ${G2_MININET_SRC}/g2Launcher.py"
    exit
  fi
  if [ ! -f "${MININET_SRC}/pox/ext/g2_static.py" ]; then
    echo "[ERROR] Failed to find POX controller ${MININET_SRC}/pox/ext/g2_static.py"
    exit
  fi

  # Put together list of tests to run. This can be loaded from either:
  #     ** user specified test list using -t option
  #     ** listing all directories from test directory specified using -d option
  if [ ! -z $gTestFile ] && [ -f $gTestFile ]; then
    # Read the list of tests into our array
    while read eachTestName; do
      gTestList+=($eachTestName)
    done <<< `grep -v '^#' $gTestFile`
  else
    # Validate and load test folder names
    for eachFile in `ls $gTestDir`; do
      if [ -d $gTestDir/$eachFile ] && \
        [ -f "$gTestDir/$eachFile/input/g2.conf" ] && \
        [ -f "$gTestDir/$eachFile/input/traffic.conf" ]; then
        # This is a valid test folder
        gTestList+=($eachFile)
      fi
    done
  fi

  # Success. We have basic test environment setup. Log and proceed.
  echo "[INFO] *******************************************"
  echo "[INFO] TEST CONFIGURATION"
  echo "[INFO] *******************************************"
  echo "[INFO] \$PYTHON_BIN=$PYTHON_BIN"
  echo "[INFO] \$SFLOW_SRC=$SFLOW_SRC"
  echo "[INFO] \$MININET_SRC=$MININET_SRC"
  echo "[INFO] \$G2_MININET_SRC=$G2_MININET_SRC"
  echo "[INFO] \$TEST_DIR=$gTestDir"
  echo "[INFO] \$TEST_FILE=$gTestFile"
  echo "[INFO] \$TEST_LIST=${gTestList[*]}"
}

# sFlow launcher
# Checks if sFlow-RT is already running. If not, starts sFlow-RT agent for collecting
# sFlow records from mininet OVs switches.
launchSflow() {
  # Launch sFlow-RT engine if not already running.
  if [ $(getProcessPID sflow) != 0 ]; then
    echo "[INFO] sFlow-RT engine already running ..."
  else
    # sFlow-RT not running. Lets start it.
    if [ ! -f "${SFLOW_SRC}/start.sh" ]; then
      echo "[ERROR] Failed to launch sFlow startup script $(SFLOW_SRC)\start.sh"
      exit
    fi
    cd ${SFLOW_SRC} && ./start.sh&
  fi
}

# Test launcher using Mininet, POX controller.
# Given a test folder:
#    ** does basic test input validation
#    ** launches Mininet with configuration files from <test_folder>/input/
#    ** launches POX with configuration files from Mininet output <test_folder>/output/
# On test completion, cleans up lingering processes for next test run.
runOneTest() {
  local currTestDir="$1"
  if [ -d $currTestDir ] && \
    [ -f "$currTestDir/input/g2.conf" ] && \
    [ -f "$currTestDir/input/traffic.conf" ]; then
    echo "[INFO] *******************************************"
    echo "[INFO] Starting test $currTestDir ..."

    # Launch Mininet to create topology, routing info.
    cd ${G2_MININET_SRC} && \
      ${PYTHON_BIN} g2Launcher.py -i $currTestDir/input/ -o $currTestDir/output/&

    # Wait for a bit to make sure mininet actually is up
    sleep 20

    # Is mininet up and running?
    mininetPID=$(getProcessPID g2Launcher)
    if [ $mininetPID == 0 ]; then
      echo "[ERROR] Failed to start g2Launcher.py ..."
      exit
    fi
    echo "[INFO] Started g2Launcher, PID: $mininetPID"

    # Launch POX controller
    cd ${MININET_SRC}/pox && \
      ./pox.py --verbose openflow.of_01 --port=6633 g2_static \
               --topo=$currTestDir/output/topo.json --routing=$currTestDir/output/routing.conf&

    # Is POX up?
    poxPID=$(getProcessPID pox)
    if [ $poxPID == 0 ]; then
      echo "[ERROR] Failed to start pox.py ..."
      kill -n 9 $mininetPID
      exit
    fi

    # Wait until mininet test run is complete.
    while [ $(getProcessPID g2Launcher) != 0 ]; do
      sleep 10
    done

    # Mininet when done, cleans itself up.
    # POX not so much, since its a daemon. Lets kill it once mininet tests are done.
    kill -n 9 $poxPID

    # Done running this test. Log and return.
    echo "[INFO] Completed test $currTestDir ..."
    echo "[INFO] *******************************************"
  else
    # Missing input files needed to proceed. Quit.
    echo "[ERROR] Bad test setup at $currTestDir. Ignoring this ..."
  fi
}

# Acquires lockfile. Blocks another instance of this script from
# running at the same time.
getLock() {
  # Check for lock file.
  if [ -f $gLockFile ]; then
    echo "g2MininetAutoTests.sh already running..."
    exit
  else
    touch $gLockFile
  fi
}

# Releases lockfile. Allows another instance of this script to run
releaseLock() {
  if [ -f $gLockFile ]; then
    rm $gLockFile
  fi
}

# Exit handler.
doCleanup() {
  releaseLock
}


# --------------------------------------------
# Script MAIN logic starts below.
# --------------------------------------------
# Make sure we can run. Get a lock.
getLock

# Install an exception handler to cleanup lingering lock files
trap doCleanup EXIT INT TERM

parseCmdlineArgs "$@"

# Setup environment variables for test using env script passed.
setupTestEnv

# Start sFlow-RT
launchSflow

# Iterate over all the test folders and run them sequentially.
# Waits for each test to complete before launches the next one.
for eachTestDirName in "${gTestList[@]}"; do
  # Individual test directory. Must contain input/ folder with required configuration to proceed.
  eachTestDir=$gTestDir/$eachTestDirName

  runOneTest $eachTestDir
done

# Wait for a bit to make sure all processing is done. Cleanup and exit
sleep 20
doCleanup

echo "[INFO] *******************************************"
echo "[INFO] DONE RUNNING ALL TESTS."
echo "[INFO] *******************************************"
