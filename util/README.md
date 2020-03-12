# G2 Mininet utilities
This folder contains various utility modules, scripts that can be used
with g2 mininet tests.

## g2MininetAutoTests.sh:
  * Utility to automate mininet testing. 
      * Given a bash script to setup the test environment, a directory containing configuration files for various tests, this script sets up all needed components (POX, sFlow-RT, mininet) to run tests and saves their output to individual test's 'output' directory. 
      * Optionally only a subset of tests in a given test directory could be run by specifying '-t' 
        option with a txt file containing the list of tests to run (one test name per line).
      * Please refer to the sample 'setupEnv.sh' and 'sampleG2AutoTestList.txt' for examples.
  * Usage: sudo g2MininetAutoTests.sh -e <ENVSETUP_FILE> -d <TESTS_DIR> [-t [TESTS_LIST_TXTFILE]] [-v] [-h]
  

      Note:
      Please note that the bash script MUST be run as root or with 'sudo' access to enable mininet to be
      able to create switches, interfaces etc on Linux stack.

  * Example:
    cd $G2_MININET_SRC
    sudo ./util/g2MininetAutoTests.sh -e util/setupEnv.sh -d examples/ -t util/sampleG2AutoTestList.txt
    
  * Please review the sample 'setupenv.sh' provided and ensure all variables are defined correctly.

## jains_fairness_index.py
  * Returns Jain's fairness index according to rates and expected rates. See https://www.cse.wustl.edu/~jain/atmf/ftp/af_fair.pdf slide 4

## bpg.py
  * A *Network* class and a *calc_bpg* function is defined here.
    * *Network*: accepts F, C, L (optional, can be derived from C), M (optional, default is all 0) and num_links (optional, default = 38) as inputs, where F is flow dictionary, C is capacity dictionary, L is link dictionary, M is minimal rates dictionary. All attributes are implemented according to the *Lexicographic* paper.
    * *calc_bpg*: accepts a *Network* class and run algorithm in *Lexicographic* paper. It returns 5 values:
      * level: total bpg levels
      * bpg_v: bpg vertices, format = {level: [{link_idx: R}]}
      * bpg_e_dir: direct precedent links, format = {upper level: [(link_src,link_dst)]}
      * bpg_e_indi: indirect precedent links, format = {upper level: [(link_src,link_dst)]}
      * flow_rates: grouped flow rates, format = [{"flows": [flow_ids], "rate": shared_flow_rate}]

## create_level_10_experiments.py
  * Generates level 1 - level 10 networks (See Sigmetrics paper). It takes g2.conf from *files* directory as input. You can specify tcp congestion control, level and number of duplicated flows.
  * The following example creates level 1-10, 1-5 flow duplications for both bbr and cubic congestion controls:
  ```python
      for tcp_cc in ["bbr", "cubic"]:
        for level in range(1, 11):
          for n_dup in range(1, 6):
            make_dir(tcp_cc=tcp_cc, level=level, n_dup=n_dup)
  ```

## createNLinksExample.py
  * Generates a linear BPG network configuration with 'l' links. Accepts number of links 'l', base network topology 
    using '-t', TCP congestion control algorithm to use 'cc', scaling factor 'f' as inputs and creates configuration 
    appropriately. Can be used with Mininet to run simulations.
  * Usage: python2.7 util/createNLinksExample.py -t examples/g2_network10 -l 8 -f 5 -cc bbr
    Creates a folder called 'g2_example_nlevel' in the current directory with 40 experiments, containing 8 links, using
    BBR and flows scaled upto 5 times.
