# G2-Mininet Sandbox

G2-Mininet is a mininet-based sandbox that has been developed to help empirically demonstrate the mathematical properties of bottleneck structures [1, 2, 3]. This software extends Mininet with a flexible and user-friendly way to create arbitrary (1) topologies, (2) routing schemes, and (3) flow configurations. G2-Mininet uses a configuration of Mininet with OpenFlow and POX to provide SDN capabilities and iPerf to generate traffic.

## Experiments to validate the Quantitative Theory of Bottleneck Structures (QTBS)

In this repository you will also find all the experiments (artifacts) presented in the various QTBS papers [1, 2, 3], allowing and encouraging anyone to reproduce them for further validation and discussion. Please see the instructions below to learn more on how to build this software and how to run the experiments. See also the `README` file under the `experiments` directory for a description of each of the experiments.

## Source Directory Structure

* Directory structure:
  * `experiments`: Example networks tested with G2-Mininet.
  * `devtools`: Development utilities, not for release.
  * `pox`: POX modules that implement the SDN controller.
  * `util`: Utility scripts that can be used with G2-Mininet tests.

## References

[1] J. Ros-Giralt, A. Bohara, S. Yellamraju, H. Langston, R. Lethin, Y. Jiang, L. Tassiulas, J. Li, Y. Lin, Y. Tan, M. Veeraraghavan, "On the Bottleneck Structure of Congestion-Controlled Networks," ACM SIGMETRICS, Boston, June 2020.

[2] Jordi Ros-Giralt, Noah Amsel, Sruthi Yellamraju, James Ezick, Richard Lethin, Yuang Jiang, Aosong Feng, Leandros Tassiulas,  Zhenguo Wu, Min Yeh Teh, Keren Bergman, "Designing Data Center Networks Using Bottleneck Structures," Accepted for publication at ACM SIGCOMM 2021.

[3] Jordi Ros-Giralt, Noah Amsel, Sruthi Yellamraju, James Ezick, Richard Lethin, Yuang Jiang, Aosong Feng, Leandros Tassiulas,  Zhenguo Wu, Min Yeh Teh, Keren Bergman, "A Quantitative Theory of Bottleneck Structures for Data Networks," Submitted to Transactions on Networking, 2021. (Under review).

## Getting Started

### Prerequisites

* Mininet
* Python 2.7
  * List of non-standard Python modules required: numpy, matplotlib, networkx, requests, psutil 
* sFlow-rt

### Installing

* Install Mininet by following the instructions from the [Mininet Website](http://mininet.org/download/). The following installation and execution steps should be run from a machine (or VM) running Mininet.

* Download `sFlow-rt`

  ```shell
  cd $HOME
  wget https://inmon.com/products/sFlow-RT/sflow-rt.tar.gz
  tar -xvzf sflow-rt.tar.gz
  ```
* Note: the following Macros are used in the steps below (please replace these with the paths specific to your installation):
  * `$MININET_SRC` represents the top of the Mininet installation directory, for example `/home/mininet/mininet/`
  * `$G2_MININET_SRC` represents the path to `g2-mininet` source code, for example `$MININET_SRC/g2-mininet`

* Clone the `g2-mininet` repo and deploy scripts:

  ```shell
  cd $MININET_SRC
  git clone $THIS_REPO_URL
  cp g2-mininet/pox/g2_static.py $MININET_SRC/pox/ext/
  ```

### Running the Tests   
1. Start `sFlow-rt`: 
   1. ```shell
      cd $HOME
      cd sflow-rt
      ./start.sh
      ```
   
   The above commands will start `sflow-rt`, listening on port 6343 (for sFlow) and 8008 (for HTTP). Keep it running for the entire experiment run.
   
2. Steps to simulate and test a new custom network topology named **`custom_net`**:

   1. Create the experiment directory:
      
      ```shell
      cd $G2_MININET_SRC
      mkdir experiments/custom_net/
      mkdir experiments/custom_net/input/
      ```

   2. Specify general configurations in `experiments/custom_net/input/g2.conf` file.

   3. Specify traffic flow configurations in `experiments/custom_net/input/traffic.conf` file.

   4. Launch G2-Mininet:
   
      ```shell
      sudo python g2Launcher.py -i experiments/custom_net/input/ -o experiments/custom_net/output/
      ```

   5. Open another terminal window and run the POX SDN controller:

      1. ```shell
         cd $MININET_SRC/pox
         ./pox.py --verbose openflow.of_01 --port=6633 g2_static --topo='$G2_MININET_SRC/experiments/custom_net/output/topo.json' --routing='$G2_MININET_SRC/experiments/custom_net/output/output_routing.conf'
         ```

   6. Output results and plots will be written to the directory `experiments/custom_net/output/`.

3. A large variety of network configuration examples can be found under `experiments/`, providing examples of `input/g2.conf` and `input/traffic.conf` configuration files. For example, use the following commands to run the network experiment `g2_network1`:

   1. ```shell
      cd $G2_MININET_SRC
      sudo python g2Launcher.py -i experiments/g2_network1/input/ -o experiments/g2_network1/output/
      cd $MININET_SRC/pox
      ./pox.py --verbose openflow.of_01 --port=6633 g2_static --topo='$G2_MININET_SRC/experiments/g2_network1/output/topo.json' --routing='$G2_MININET_SRC/experiments/g2_network1/output/output_routing.conf'
      ```

4. See the file `experiments/README` for a description of all the experiments available.
