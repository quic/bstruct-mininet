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

Note: link capacities are capped at 1000 Mbit/s in Mininet

### References
[1] J. Ros-Giralt, A. Bohara, S. Yellamraju, H. Langston, R. Lethin, Y. Jiang, L. Tassiulas, J. Li, Y. Lin, Y. Tan, M. Veeraraghavan, "On the Bottleneck Structure of Congestion-Controlled Networks," accepted for publication at ACM SIGMETRICS, Boston, June 2020. 

[2] J. Ros-Giralt, S. Yellamraju, A. Bohara, R. Lethin, J. Li, Y. Lin, Y. Tan, M. Veeraraghavan, Y. Jiang, L. Tassiulas, "G2: A Network Optimization Framework for High-Precision Analysis of Bottleneck and Flow Performance," International Workshop on Innovating the Network for Data Intensive Science (INDIS), Supercomputing, Denver, Nov 2019.
