#!/bin/bash
# #########################################################################
#
# G2 Mininet emulation test environment setup script.
#
# Please make sure to customize all the variables defined in this script 
# prior to running tests.Also, please use absolute path and not relative
# paths to keep things simple :)
#
# #########################################################################

# PYTHON bin path (Needs 2.7)
export PYTHON_BIN='/home/mininet/env2/bin/python2.7'

# Directory where mininet sources are present
export MININET_SRC='/home/mininet/mininet'

# Directory where 'g2-mininet' repo is present
export G2_MININET_SRC='/home/mininet/mininet/g2-mininet'

# Directory where sflow-rt is present
export SFLOW_SRC='/home/mininet/git/sflow/sflow-rt'
