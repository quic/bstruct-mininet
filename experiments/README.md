This directory includes artifacts and experiments published in various papers. They are made available so that anyone can reproduce them and verify the results. For instructions on how to install G2-Mininet and run experiments in this directory, please see the README file located in the root directory.

## G2 Network Examples
1. `g2_network1`: Google's B4 network consisting 12 nodes (data centers)
2. `g2_network2`: A small network consisting of six flows and four links, to demonstrate small flows can be elephants
   1. Section 2.6 and Fig. 7 [1]
   2. Section II C and Fig. 4 [2]
3. `g2_network3`: Google's B4 network consisting of 12 nodes and five flows
   1. Section 2.4 and Fig. 5 [1]
   2. Section II B and Fig. 2 [2]
4. `g2_network4`: A two-level bottleneck structure network containing 12 nodes, two flows
   1. Section 3.1 and Fig. 8-a [1]
   2. Section V and Fig. 10-a [2]
5. `g2_network5`: A three-level bottleneck structure network containing 12 nodes, three flows
   1. Section 3.1 and Fig. 8-b [1]
   2. Section V and Fig. 10-b [2]
6. `g2_network6`: A four-level bottleneck structure network containing 12 nodes, six flows
   1. Section 3.1 and Fig. 8-c [1]
7. `g2_network7`: A two-level bottleneck structure network containing 12 nodes, two flows, RTT = 0 ms
   1. Section 3.1 and Fig. 8-a [1]
8. `g2_network8`: A three-level bottleneck structure network containing 12 nodes, three flows, RTT = 0 ms
   1. Section 3.1 and Fig. 8-b [1]
9. `g2_network9`: A four-level bottleneck structure network containing 12 nodes, six flows, RTT = 0 ms
   1. Section 3.1 and Fig. 8-c [1]
10. `g2_network10`: A nine-node linear bottleneck structure network with capacities modeled using '10 + 20(n-1)^2))'
    1. Section 3.4 and Fig. 14 [1]
11. `g2_network11, 12, 13, 14, 15`: Time-bound constrained data transfers experiments on Google's B4 network for 1) no traffic shaping, 2) traffic shaping flow 4, 3) traffic shaping flow 4 and flow 8, 4) traffic shaping flow 1, and 5) traffic shaping flow 3, flow 4 and flow 8, respectively. [4]
    1. Section 3.3; Fig. 7, 8, A4 [4]
12. `g2_network16, 17, 18, 19`: Bandwidth tapering on fat tree networks experiments on Google's B4 network for link 6's capacity equal to 1) 5, 2) 13.333, 3) 20, and 4) 10, respectively.
    1. Section 3.2; Fig. 4, 5, A5 [4]
13. `g2_network20, 21`: Identification of optimal throughput routes experiments on Google's B4 network for 1) flow 25 traversing link 15 and link 10 and 2) flow 25 traversing link 19, link 8 and link 16, respectively [4].
    1. Section 3.1; Fig. 3 [4]
14. `g2_network22`: A twelve-node canonical Dragonfly(3,4,1) network containing 132 (uniform) flows with BBR.
    1. Section E.3, Fig. A8-a and Fig. A9 [3]
15. `g2_network23`: A twelve-node canonical Dragonfly(3,4,1) network containing 132 (uniform) flows with Cubic.
    1. Section E.3, Fig. A8-b and Fig. A9 [3] 
16. `g2_network24`: A twelve-node canonical Dragonfly(3,4,1) network containing 132 (uniform) flows with Reno.
    1. Section E.3, Fig. A8-c and Fig. A9 [3]
17. `g2_network25`: A twelve-node canonical Dragonfly(3,4,1) network containing 132 (skewed,sigma=2) flows.
    1. Section E.3 and Fig. A11-a [3]
18. `g2_network26`: A twelve-node canonical Dragonfly(3,4,1) network containing 132 (skewed,sigma=4) flows.
    1. Section E.3 and Fig. A11-b [3]
19. `g2_network27`: A twelve-node canonical Dragonfly(3,4,1) network containing 132 (skewed,sigma=10) flows.
    1. Section E.3 and Fig. A11-c [3]
20. `g2_network28`: A 4-children Fat-Tree network containing 12 flows (uniform traffic).
    1. Fig. A12 [3]
21. `g2_network29`: A 9-children Fat-Tree network containing 72 flows (uniform traffic).
    1. Fig. 8, 9, 10 [3]
22. `g2_network30, 31, 32`: A 4-children Fat-Tree network containing 12 flows (traffic skewness = 2, 4, 10, respectively).
    1. Fig. A13 , A14, A15 , A18 [3]
23. `g2_network33, 34, 35`: A 9-children Fat-Tree network containing 72 flows (traffic skewness = 2, 4, 10, respectively).
    1. Fig. 12, A16, A17. A19 [3]
24. `g2_network36`: A four-pod folded-clos network with tapering 0.5 and 20 skewness values.
25. `g2_network37`: A four-pod folded-clos network with tapering 1 and 20 skewness values.

### References
[1] J. Ros-Giralt, A. Bohara, S. Yellamraju, H. Langston, R. Lethin, Y. Jiang, L. Tassiulas, J. Li, Y. Lin, Y. Tan, M. Veeraraghavan, "On the Bottleneck Structure of Congestion-Controlled Networks," accepted for publication at ACM SIGMETRICS, Boston, June 2020.

[2] J. Ros-Giralt, S. Yellamraju, A. Bohara, R. Lethin, J. Li, Y. Lin, Y. Tan, M. Veeraraghavan, Y. Jiang, L. Tassiulas, "G2: A Network Optimization Framework for High-Precision Analysis of Bottleneck and Flow Performance," International Workshop on Innovating the Network for Data Intensive Science (INDIS), Supercomputing, Denver, Nov 2019.

[3] Reservoir Labs, Yale University, Columbia University, "Designing Data Center Networks Using Bottleneck Structures," Accepted for publication at ACM SIGCOMM 2021.

[4] Jordi Ros-Giralt, Noah Amsel, Sruthi Yellamraju, James Ezick, Richard Lethin, Yuang Jiang, Aosong Feng, Leandros Tassiulas,  Zhenguo Wu, Min Yeh Teh, Keren Bergman, "A Quantitative Theory of Bottleneck Structures for Data Networks," Submitted to Transactions on Networking, 2021. (Under review).

[5] Noah Amsel, Jordi Ros-Giralt, Sruthi Yellamraju, Brendan von Hofe, Richard Lethin,  "Computing Bottleneck Structures at Scale for High-Precision Network Performance Analysis," International Workshop on Innovating the Network for Data Intensive Science (INDIS), Supercomputing, Denver, Nov 2020.
