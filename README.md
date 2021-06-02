# G2-Mininet Sandbox

G2-Mininet provides a flexible way to create arbitrary (1) topologies, (2) routing schemes, and (3) flow configurations to analyze general network architectures with a focus on (although not limited to) understanding the bottleneck structure of high-speed communication networks (See [1, 2, 3, 4, 5]). G2-Mininet uses Mininet with OpenFlow and POX to provide SDN capabilities and iPerf to generate traffic.

In this repository you will also find all the experiments (artifacts) presented in the papers. This allows anyone to reproduce the experiments. Please see the instructions below to learn how to build this software and how to run the experiments. See also the README file under the experiments directory for a description of each of the experiments.

## References

[1] J. Ros-Giralt, A. Bohara, S. Yellamraju, H. Langston, R. Lethin, Y. Jiang, L. Tassiulas, J. Li, Y. Lin, Y. Tan, M. Veeraraghavan, "On the Bottleneck Structure of Congestion-Controlled Networks," ACM SIGMETRICS, Boston, June 2020.

[2] Reservoir Labs, Yale University, Columbia University, "Designing Data Center Networks Using Bottleneck Structures," Accepted for publication at ACM SIGCOMM 2021.

[3] Jordi Ros-Giralt, Noah Amsel, Sruthi Yellamraju, James Ezick, Richard Lethin, Yuang Jiang, Aosong Feng, Leandros Tassiulas,  Zhenguo Wu, Min Yeh Teh, Keren Bergman, "A Quantitative Theory of Bottleneck Structures for Data Networks," Submitted to Transactions on Networking, 2021. (Under review).

For any questions, please contact Reservoir Labs at https://www.reservoir.com/company/contact/

## Getting Started

### Prerequisites

* Mininet
* Python 2.7
  * List of non-standard Python modules required: numpy, matplotlib, networkx, requests, psutil 
* sFlow-rt

Note: We have verified G2-Mininet works on Ubuntu 16.04 LTS, although it should work on any distribution that supports Mininet.

### Installing

* Install Mininet by following the instructions at [Mininet Website](http://mininet.org/download/). The following installation and execution steps should be run from a machine (or VM) running Mininet.

* Download `sFlow-rt`

  ```shell
  cd $HOME
  wget https://inmon.com/products/sFlow-RT/sflow-rt.tar.gz
  tar -xvzf sflow-rt.tar.gz
  ```
* Note: following Macros are used in the steps below (please replace these with the paths specific to your installation):
  * `$MININET_SRC` represents the top of the Mininet installation directory, for example `/home/mininet/mininet/`
  * `$G2_MININET_SRC` represents the path to `g2-mininet` source code, for example `$MININET_SRC/g2-mininet`

* Clone `g2-mininet` repo and deploy scripts:

  ```shell
  cd $MININET_SRC
  git clone https://github.com/reservoirlabs/g2-mininet.git
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

   1. ```shell
      cd $G2_MININET_SRC
      mkdir experiments/custom_net/
      mkdir experiments/custom_net/input/
      ```

   2. Specify configurations in `experiments/custom_net/input/g2.conf` file.

   3. Specify traffic flow configurations in `experiments/custom_net/input/traffic.conf` file.

   4. ```shell
      sudo python g2Launcher.py -i experiments/custom_net/input/ -o experiments/custom_net/output/
      ```

   5. Open another terminal window and run:

      1. ```shell
         cd $MININET_SRC/pox
         ./pox.py --verbose openflow.of_01 --port=6633 g2_static --topo='$G2_MININET_SRC/experiments/custom_net/output/topo.json' --routing='$G2_MININET_SRC/experiments/custom_net/output/output_routing.conf'
         ```

   6. Output results and plots will be written to directory `experiments/custom_net/output/`.

3. An existing network example simulation can be run using that network's directory under `experiments/` and modifying  its`input/g2.conf` and `input/traffic.conf` as needed. For example, use the following commands to run `g2_network1`:

   1. ```shell
      cd $G2_MININET_SRC
      sudo python g2Launcher.py -i experiments/g2_network1/input/ -o experiments/g2_network1/output/
      cd $MININET_SRC/pox
      ./pox.py --verbose openflow.of_01 --port=6633 g2_static --topo='$G2_MININET_SRC/experiments/g2_network1/output/topo.json' --routing='$G2_MININET_SRC/experiments/g2_network1/output/output_routing.conf'
      ```

4. See `experiments/README` for details on existing example network configurations and results.

### Source Directory Structure

* Source hosted at: https://github.com/reservoirlabs/g2-mininet
* Directory structure:
  * `experiments`: Example networks tested with G2-Mininet.
  * `devtools`: Development utilities, not for release.
  * `pox`: POX modules that implement the SDN controller.
  * `util`: Utility scripts that can be used with G2-Mininet tests.
