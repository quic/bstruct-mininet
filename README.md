# BStruct-Mininet Sandbox

BStruct-Mininet is a Mininet-based sandbox that extends Mininet with:
- (1) Pre-processing scripts that help the user create arbitrary topologies, routing schemes, and flow configurations in a flexible and user-friendly way; 
- (2) Post-processing scripts to measure and plot the performance metrics obtained from your experiments, including health metrics like the Jain's fairness index, CPU and memory utilization that will allow you to assess whether your experiment's quality is high or was otherwise distorted by the HW limitations of the system you are running on. 

Although originally BStruct-Mininet was developed to help empirically demonstrate the mathematical properties of bottleneck structures [1, 2, 3] in congestion-controlled networks, it can be generically used for any kind of Mininet experiments that you may want to run. 

## Experiments to validate the Quantitative Theory of Bottleneck Structures (QTBS)

In this repository you will also find all the experiments (artifacts) presented in the various QTBS papers [1, 2, 3], allowing and encouraging anyone to reproduce them for further validation and discussion. Please see the instructions below to learn more on how to build this software and how to run the experiments. See also the `README` file under the `experiments` directory for a description of each of the experiments.

## Source Directory Structure

* Directory structure:
  * `experiments`: Example networks tested with BStruct-Mininet.
  * `devtools`: Development utilities, not for release.
  * `pox`: POX modules that implement the SDN controller.
  * `util`: Utility scripts that can be used with BStruct-Mininet tests.

## References

[1] J. Ros-Giralt, A. Bohara, S. Yellamraju, H. Langston, R. Lethin, Y. Jiang, L. Tassiulas, J. Li, Y. Lin, Y. Tan, M. Veeraraghavan, "On the Bottleneck Structure of Congestion-Controlled Networks," ACM SIGMETRICS, Boston, June 2020.

[2] Jordi Ros-Giralt, Noah Amsel, Sruthi Yellamraju, James Ezick, Richard Lethin, Yuang Jiang, Aosong Feng, Leandros Tassiulas,  Zhenguo Wu, Min Yeh Teh, Keren Bergman, "Designing Data Center Networks Using Bottleneck Structures," Accepted for publication at ACM SIGCOMM 2021.

[3] Jordi Ros-Giralt, Noah Amsel, Sruthi Yellamraju, James Ezick, Richard Lethin, Yuang Jiang, Aosong Feng, Leandros Tassiulas,  Zhenguo Wu, Min Yeh Teh, Keren Bergman, "A Quantitative Theory of Bottleneck Structures for Data Networks," Oct 2022, https://arxiv.org/abs/2210.03534.

## Getting Started

### Prerequisites

* Mininet
* Python 2.7 or above
  * List of non-standard Python modules required: numpy, matplotlib, networkx, requests, psutil 
* sFlow-rt

### Installing

* Note: the following Macros are used in the steps below:
  * `$ROOT` represents a root directory of your choice where you want to install the various software components
  * `$MININET_SRC` represents the top of the Mininet installation directory, for example `$ROOT/mininet/`
  * `$BSTRUCT_MININET_SRC` represents the path to `bstruct-mininet` source code, for example `$MININET_SRC/bstruct-mininet`

* Start by installing Mininet in the $MININET_SRC directory by following the instructions from the [Mininet Website](http://mininet.org/download/). We recommend using the "Native Installation from Source" procedure. The steps below have been tested to work on Mininet 2.3.1b1.

* Make sure you also have these packages installed: numpy, matplotlib, networkx, requests, psutil

* Download `sFlow-rt`

  ```shell
  cd $ROOT
  wget https://inmon.com/products/sFlow-RT/sflow-rt.tar.gz
  tar -xvzf sflow-rt.tar.gz
  ```

* Clone the `bstruct-mininet` repo and deploy scripts:

  ```shell
  cd $MININET_SRC
  git clone https://github.com/quic/bstruct-mininet
  cp bstruct-mininet/pox/g2_static.py $MININET_SRC/pox/ext/
  ```

### Running the Tests   
1. Start `sFlow-rt`: 
   ```shell
   cd $ROOT/sflow-rt
   ./start.sh
   ```
   
   The above commands will start `sflow-rt`, listening on port 6343 (for sFlow) and 8008 (for HTTP). Keep it running for the entire experiment run.
   
2. Steps to simulate and test a new custom network topology named **`custom_net`**:

   1. Create the experiment directory:
      
      ```shell
      cd $BSTRUCT_MININET_SRC
      mkdir experiments/custom_net/
      mkdir experiments/custom_net/input/
      ```

   2. Specify general configurations in `experiments/custom_net/input/g2.conf` file. (You will find examples of g2.conf files in the `experiments/` folder.)

   3. Specify traffic flow configurations in `experiments/custom_net/input/traffic.conf` file. (You will find examples of g2.conf files in the `experiments/` folder.)

   4. Launch BStruct-Mininet:
   
      ```shell
      sudo python g2Launcher.py -i experiments/custom_net/input/ -o experiments/custom_net/output/
      ```

   5. Open another terminal window and run the POX SDN controller:

      ```shell
      cd $MININET_SRC/pox
      ./pox.py --verbose openflow.of_01 --port=6633 g2_static --topo='$BSTRUCT_MININET_SRC/experiments/custom_net/output/topo.json' --routing='$BSTRUCT_MININET_SRC/experiments/custom_net/output/output_routing.conf'
      ```

   6. Output results and plots will be written to the directory `experiments/custom_net/output/`.

3. A large variety of network configuration examples can be found under `experiments/`, providing examples of `input/g2.conf` and `input/traffic.conf` configuration files. For example, use the following commands to run the network experiment `g2_network1`:

   ```shell
   cd $BSTRUCT_MININET_SRC
   sudo python g2Launcher.py -i experiments/g2_network1/input/ -o experiments/g2_network1/output/
   cd $MININET_SRC/pox
   ./pox.py --verbose openflow.of_01 --port=6633 g2_static --topo='$BSTRUCT_MININET_SRC/experiments/g2_network1/output/topo.json' --routing='$BSTRUCT_MININET_SRC/experiments/g2_network1/output/output_routing.conf'
   ```

4. See the file `experiments/README` for a description of all the experiments available.
