# example running script: python util/config_gen.py --tapering_num 1 --network_type clos_pods --k 4 --config_folder ./examples/pods1 --num_bytes 64000000 --result_prefix 1 --collection_frequency 1 --c 1 --skewness 1
import json
import os
from itertools import permutations,product
import networkx as nx
from bpg import calc_bpg, Network

def link_info_gen(C: dict, mapping: dict, link_delay, link_loss):   
    """Generate the specified link information 
    Args:
        C (dict): Capacity dictionary (key, value) = (link ID, capacity of the link).
        mapping (dict): Link dictionary (key, value) = (link ID, source and destination pair of the link).
        link_delay (float): Specified delay for the link.
        link_loss (float): Specified loss for the link.
    Returns:
        str: Link infomation for all specified links, seperated by ;.
    Examples:
        The return can be "link_info: s1, s17, 5, 5ms, 0, N/A, N/A; s2, s17, 5, 5ms, 0, N/A, N/A; ..."
    """
    
    link_info = "link_info: "
    for link_id, cap in C.items():
        link_info += "{}, {}, {}, {}ms, {}, N/A, N/A; ".format(*mapping[link_id], cap, link_delay, link_loss)
    return link_info[:-2]


def default_link_info_gen(default_link_delay, default_link_loss, default_link_bw):  
    """Generate the default link information
    Args:
        default_link_delay (float): Default delay for the link.
        default_link_loss (float): Default loss for the link.
        default_link_bw (float): Default bandwidth for the link.
    Returns:
        str: Default link infomation.
    Examples:
        The return can be "default_link_info: 1000, 5ms, 0, N/A, N/A"
    """

    return "default_link_info: {}, {}ms, {}, N/A, N/A".format(default_link_bw, default_link_delay, default_link_loss)


def traffic_gen(flows: dict, flow_rates, num_bytes, K, skewness):
    """Generate the traffic configurations.
    Args:
        flows (dict): Dictionary of flows information (key, value) = (flowID, (flowID, (src, dst))).
        flow_rates (dict): Dictionary of flow rate information (key, value) = (flowID, flow rate).
        num_bytes (int): Number of bytes to send for all the flows.
        K (int): number of pods.
        skewness (float): num_bytes skewness between intrapod and interpod traffic, inter = intra*skewness
    Returns:
        str: Generated traffic configurations.
    Examples:
        The return can be
        "
        	# Format: int job id, source host, destination host, number of bytes to transfer, time in seconds to start the transfer, expected fair share of the flow in Mbits/sec
			1, h1, h2, 80000000, 0, 1.4583333333333346, h1 s1 s17 s2 h2 
			2, h1, h3, 80000000, 0, 1.4583333333333346, h1 s1 s17 s3 h3 
			3, h1, h4, 80000000, 0, 1.4583333333333346, h1 s1 s17 s4 h4
			...
		"
    """ 

    traffic_conf = "# Format: int job id, source host, destination host, number of bytes to transfer, " \
                   "time in seconds to start the transfer, expected fair share of the flow in Mbits/sec, specified path\n"
    for flow_id, (src,dst) in flows.items():
        if (int(src[1:])-1) // K != (int(dst[1:])-1) // K:
            traffic_conf += "{}, {}, {}, {}, 0, {}, N/A\n".format(flow_id, src, dst, int(num_bytes*skewness), flow_rates[flow_id])
        else:
            traffic_conf += "{}, {}, {}, {}, 0, {}, N/A\n".format(flow_id, src, dst, num_bytes, flow_rates[flow_id])
    return traffic_conf

def g2_conf_gen(input_path, exp_name, mapping, C, batch_proc_path, link_delay, default_link_delay,
                link_loss, default_link_loss, default_link_bw, tcp_congestion_control, collection_frequency,
                result_prefix):
    """Generate the traffic configurations.
    Args:
        input_path (str): The relative path for the input folder.
        exp_name (str): The name of the experiment which is the folder name for the experiment.
        num_bytes (int): Number of bytes to send for all the flows.
        mapping (dict): Link dictionary (key, value) = (link ID, source and destination pair of the link).
        C (dict): Capacity dictionary (key, value) = (link ID, capacity of the link).
        batch_proc_path (str): The relative path for the folder containing all the examples.
        link_delay (float): Specified delay for the link.
        default_link_delay (float): Default delay for the link.        
        link_loss (float): Specified loss for the link.        
        default_link_loss (float): Default loss for the link.
        default_link_bw (float): Default bandwidth for the link.
        tcp_congestion_control (str): congestion control method.
        collection_frequency (float): The (a) iperf interval and (b) switch statistics polling interval.
        result_prefix (str): The prefix of the result files.
    Returns:
        str: The genertaed text of the "g2.conf".

    """     

    g2_conf_input = open(os.path.join(input_path, "g2.conf"), 'r')
    list_lines = g2_conf_input.readlines()

    links_str = "links: "
    links_tuple = []
    link_id = 0
    for key, val in mapping.items():
        if (val[1], val[0]) not in links_tuple:
            link_id += 1
            links_tuple.append(val)
            links_str += "({},{},{});".format(key, *val)

    linkinfo_str = link_info_gen(C, mapping, link_delay, link_loss)
    default_linkinfo_str = default_link_info_gen(default_link_delay, default_link_loss, default_link_bw)
    path_str = "flow_paths_file: /home/mininet/mininet/" \
               "g2-mininet/{}/{}/output/input_routing.json".format(batch_proc_path, exp_name)

    g2_conf = ""
    for line in list_lines:
        if line.startswith("links:"):
            new_line = links_str + '\n'
        elif line.startswith("flow_paths_file:"):
            new_line = path_str + '\n'
        elif line.startswith("link_info:"):
            new_line = linkinfo_str + '\n'
        elif line.startswith("default_link_info:"):
            new_line = default_linkinfo_str + '\n'
        elif line.startswith("tcp_congestion_control:"):
            new_line = "tcp_congestion_control: {}\n".format(tcp_congestion_control)
        elif line.startswith("collection_frequency:"):
            new_line = "collection_frequency: {}\n".format(collection_frequency)
        elif line.startswith("result_prefix:"):
            new_line = "result_prefix: {}\n".format(result_prefix)
        else:
            new_line = line
        g2_conf += new_line

    g2_conf_input.close()

    return g2_conf


def generateClosPodsPaths(links, K, tapering_num = 0):
    """Generate the shortest path routing with balanced link loads for the clos-pods structure.
       The routing algorithm is compatiable with the algorithm described in http://ccr.sigcomm.org/online/files/p63-alfares.pdf
    Args:
        links (dict): Dictionary of the link information (key, value) = (linkID, (src, dst)).
        K (int): The number of pods in the clos-pods structure.
    Returns:
        list: The routing list Paths[src][dst] = [all transversed nodes].
    Examples:
        paths = generateClosPodsPaths(links, 4)
    """

    numCoreSwitches = K**2 / 4
    numHosts = K**3 / 4
    numSwitchesPerPod = K
    numHostsPerPod = K**2 / 4
    numSwitchPorts = K

    assert (numCoreSwitches.is_integer() and numHosts.is_integer()),"K is not appropriate!"
    numCoreSwitches = int(numCoreSwitches)
    numHosts = int(numHosts)
    numHostsPerPod = int(numHostsPerPod)

    G = nx.Graph()
    G.add_edges_from(links.values())
    paths = (nx.shortest_path(G))

    # Intra-Pod inter-EdgeSwitch routing
    # If source is the ith host in mth edge switch and destination is the jth host in nth edge switch,
    # the routing will transverse ath aggregation switch, a = (j + m) mod (k/2).
    # The remaining transversed nodes are then deterministic.
    for podID in range(K):
        for esrc, edst in permutations(range(1, numSwitchesPerPod // 2 + 1),2):
            for hsrc, hdst in product(range(1, numSwitchPorts // 2+1),range(1, numSwitchPorts // 2 + 1)):
                eOutPort = (hdst - 1 + esrc - 1) % (numSwitchesPerPod // 2) + 1
                hSrcID = podID * numHostsPerPod + (esrc - 1)*numSwitchPorts // 2 + hsrc
                hDstID = podID * numHostsPerPod + (edst - 1)*numSwitchPorts // 2 + hdst
                eSrcID = podID * numSwitchesPerPod + esrc
                eDstID = podID * numSwitchesPerPod + edst
                aID    = podID * numSwitchesPerPod + numSwitchesPerPod // 2 + eOutPort
                paths["h" + str(hSrcID)]["h" + str(hDstID)] = ['h' + str(hSrcID),'s' + str(eSrcID),'s' + str(aID),'s' + str(eDstID),'h' + str(hDstID)]
    # Inter-Pod routing
    # If source is the ith host in mth edge switch within pod k1, and destination is the jth host in nth edge switch within pod k2,
    # the routing will transverse ath aggregation switch in pod k1, a = (j + m) mod (k/2),
    # and transverse the kth core switch, k = (a + m) mod (k/2).
    # The remaining transversed nodes are then deterministic.

    for psrc, pdst in permutations(range(K),2):
        for esrc, edst in product(range(1, numSwitchesPerPod // 2 + 1), range(1, numSwitchesPerPod // 2 + 1)):
            for hsrc, hdst in product(range(1, numSwitchPorts // 2 + 1),range(1, numSwitchPorts // 2 + 1)):
                eOutPort = (hdst - 1 + esrc -1) % (numSwitchesPerPod // 2) + 1
                hSrcID = psrc * numHostsPerPod + (esrc - 1) * numSwitchPorts // 2 + hsrc
                hDstID = pdst * numHostsPerPod + (edst - 1)*numSwitchPorts // 2 + hdst
                eSrcID = psrc * numSwitchesPerPod + esrc
                eDstID = pdst * numSwitchesPerPod + edst
                aSrcID = psrc * numSwitchesPerPod + numSwitchesPerPod // 2 + eOutPort
                aDstID = pdst *numSwitchesPerPod + numSwitchesPerPod // 2 + eOutPort
                aOutPort = (hdst - 1 + eOutPort - 1) % (numSwitchesPerPod // 2 - tapering_num) + 1
                coreID = numSwitchesPerPod * K + (eOutPort - 1) * numSwitchPorts // 2 + aOutPort

                paths["h" + str(hSrcID)]["h" + str(hDstID)] = ['h' + str(hSrcID),'s' + str(eSrcID),'s' + str(aSrcID),'s' + str(coreID),'s' + str(aDstID),'s' + str(eDstID),'h' + str(hDstID)]        

    return paths


def generateClosPaths(links):
    """Generate the shortest path routing for the clos structure.
    Args:
        links (dict): Dictionary of the link information (key, value) = (linkID, (src, dst)).
    Returns:
        list: The routing list Paths[src][dst] = [all transversed nodes].
    Examples:
        paths = generateClosPaths(links)
    """

    G = nx.Graph()
    G.add_edges_from(links.values())
    paths = (nx.shortest_path(G))
    return paths

def generate_config(path_to_exp, links: dict, hosts, C, network_type = 'clos', batch_proc_path="examples",
                    num_bytes: int = 640000000, skewness = 1, K = 1, link_delay=5, default_link_delay=5, link_loss=0, default_link_loss=0,
                    default_link_bw=1000, tcp_congestion_control="bbr", collection_frequency=1.0,tapering_num = 0,
                    result_prefix="2020"):
    """Generate the configuration files "g2.conf", "traffic.conf", "input_routing.json".
    Args:
        path_to_exp (str): The relative path for the experiment folder.
        links (dict): Dictionary of the link information (key, value) = (linkID, (src, dst)).
        hosts (list): List of all the hosts.
        C (dict): Capacity dictionary (key, value) = (link ID, capacity of the link).
        network_type (str): The type of the network to be configured.
        batch_proc_path (str): The relative path for the folder containing all the examples.
        num_bytes (int): Number of bytes to send for all the flows.
        link_delay (float): Specified delay for the link.
        default_link_delay (float): Default delay for the link.
        link_loss (float): Specified loss for the link.        
        default_link_loss (float): Default loss for the link.
        default_link_bw (float): Default bandwidth for the link.
        tcp_congestion_control (str): congestion control method.
        collection_frequency (float): The (a) iperf interval and (b) switch statistics polling interval.
        result_prefix (str): The prefix of the result files.
    Returns:
        None  
    Examples:
        generate_config(args.config_folder, links, hosts, C, network_type='clos', num_bytes = args.num_bytes, 
                        link_delay=args.link_delay, default_link_delay=args.default_link_delay, link_loss=args.link_loss, 
                        default_link_loss=args.default_link_loss, default_link_bw=args.default_link_bw, tcp_congestion_control="bbr", 
                        collection_frequency=args.collection_frequency,result_prefix=args.result_prefix)

    """ 

    assert os.path.isdir(path_to_exp), "Please enter the path to the experiment folder"

    exp_name = os.path.basename(os.path.normpath(path_to_exp))
    input_path = os.path.join(path_to_exp, "input")
    output_path = os.path.join(path_to_exp, "output")
    if not os.path.exists(os.path.join(input_path, "g2.conf")):
        raise FileExistsError("File g2.conf does not exit.")
    os.makedirs(output_path, exist_ok=True)

    print("Generating g2.conf ...")
    g2_config = g2_conf_gen(input_path, exp_name, links, C, batch_proc_path, link_delay, default_link_delay,
                            link_loss, default_link_loss, default_link_bw, tcp_congestion_control, collection_frequency,
                            result_prefix)
    with open(os.path.join(input_path, "g2.conf"), 'w') as gc:
        gc.write(g2_config)
    gc.close()

    print("Generating input_routing.json ...")
    with open(os.path.join(output_path, "input_routing.json"), 'w') as sp:
        if network_type == 'clos_pods':
            paths = generateClosPodsPaths(links, K, tapering_num = tapering_num)
        else:
            paths = generateClosPaths(links)
        sp.write(json.dumps(paths, indent=2))    
    sp.close()

    flows = {}
    flowID = 0
    for ha, hb in permutations(hosts,2):
        flowID += 1
        flows[flowID] = (ha,hb)
    
    flow_transversedLinks = {}
    for flow in flows.keys():
        src, dst = flows[flow][0], flows[flow][1]
        transversedNodes = paths[src][dst]
        transversedLinks = []
        for i in range(len(transversedNodes)-1):
            for linkID, linkSrcDst in links.items():
                if linkSrcDst == (transversedNodes[i],transversedNodes[i+1]):
                    transversedLinks.append(linkID)
        flow_transversedLinks[flow] = transversedLinks  

    print("Generating traffic.conf ...")
    network = Network(F=flow_transversedLinks.copy(), C=C.copy())
    level, bpg_v, bpg_e_dir, bpg_e_indir, flow_rates = calc_bpg(network)
    traffic_conf = traffic_gen(flows, flow_rates, num_bytes, K, args.skewness)
    with open(os.path.join(input_path, "traffic.conf"), 'w') as tc:
        tc.write(traffic_conf)
    tc.close()

    print("Completed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--network_type', type=str, default='clos', help='the type of the networks', required=False)
    parser.add_argument('--result_prefix', type=str, default='exp', help='the type of the networks', required=False)
    parser.add_argument('--config_folder', type=str, default='exp', help='config folder name', required=False)

    parser.add_argument("--c", type=float, default=1, help="constant capacity for links", required=False)
    parser.add_argument("--num_bytes", type=int, default=1000000, help="number of bytes", required=False)
    parser.add_argument("--skewness", type=float, default=1, help="link delay", required=False)
    parser.add_argument("--link_delay", type=float, default=5, help="link delay", required=False)
    parser.add_argument("--default_link_delay", type=float, default=5, help="default link delay", required=False)
    parser.add_argument("--default_link_bw", type=float, default=5, help="default link bandwidth", required=False)
    parser.add_argument("--link_loss", type=float, default=0, help="link loss", required=False)
    parser.add_argument("--default_link_loss", type=float, default=0, help="default link loss", required=False)
    parser.add_argument("--collection_frequency", type=float, default=1, help="collection frequency", required=False)
    parser.add_argument("--k", type=int, default=4, help="K for pod structure", required=False)
    parser.add_argument("--tapering_num", type=int, default=0, help="K for pod structure", required=False)    
    args = parser.parse_args()
    if args.network_type == 'clos':
        exp = 1
        exp_name = "exp{}_bbr".format(exp)
        hosts = ['h'+str(i) for i in range(1, 17)]
        linkID = 1
        links = {}
        for i in range(1, 17):
            links[linkID] = ('h'+str(i), 's' + str(i))
            linkID += 1
        for i in range(17, 21):
            for j in range(1, 5):
                links[linkID] = ('s' + str((i - 17) * 4+j),'s' + str(i))
                linkID += 1
        for i in range(21, 22):
            for j in range(17, 21):
                links[linkID] = ('s' + str(j),'s' + str(i))
                linkID += 1
        for i in range(37, 36 * 2 + 1):
            links[i] = (links[i - 36][1], links[i - 36][0])

        const_cap = args.c
        if exp == 1:  # All equal c
            C = {i: 1 * const_cap for i in range(1, len(links) + 1)}
        elif exp == 2:  # higher c for spines
            C = {i: 1 * const_cap for i in range(17, 33)}
            for i in range(33, 37):
                C[i] = 48 / 15 * const_cap 
            for i in range(37, 36 * 2 + 1):
                C[i] = C[i - 20]
        else:
            raise RuntimeError("not supported")
        generate_config(args.config_folder, links, hosts, C, network_type='clos', num_bytes = args.num_bytes, skewness = args.skewness, 
                        K = args.k, link_delay=args.link_delay, default_link_delay=args.default_link_delay, link_loss=args.link_loss, 
                        default_link_loss=args.default_link_loss, default_link_bw=args.default_link_bw, tcp_congestion_control="bbr", 
                        collection_frequency=args.collection_frequency,tapering_num = args.tapering_num,result_prefix=args.result_prefix)

    elif args.network_type == 'clos_pods':
        K = args.k
        numCoreSwitches = K**2 / 4
        numHosts = K**3 / 4
        numSwitchesPerPod = K
        numHostsPerPod = K**2 / 4
        numSwitchPorts = K
        
        assert (numCoreSwitches.is_integer() and numHosts.is_integer()),"K is not appropriate!"
        numCoreSwitches = int(numCoreSwitches)
        numHosts = int(numHosts)
        numHostsPerPod = int(numHostsPerPod)
        
        links = {}
        hosts = ['h'+str(i) for i in range(1,K**3//4+1)]
        linkID = 1
        for pod in range(K):
            hostIDStart = pod * numHostsPerPod + 1
            coreSwitchStart = numSwitchesPerPod * K + 1
            EdgeSwitchStart =  pod*numSwitchesPerPod + 1
            EdgeSwitchEnd = int((pod + 1/2) * numSwitchesPerPod)
            aggSwitchStart = EdgeSwitchEnd + 1
            aggSwitchEnd = EdgeSwitchEnd + numSwitchesPerPod // 2

            for eS in range(EdgeSwitchStart,EdgeSwitchEnd + 1):
                for h in range(numSwitchPorts // 2):         
                    links[linkID] = ('h'+str(hostIDStart + h), 's'+str(eS))
                    linkID += 1
                hostIDStart += numSwitchPorts // 2
            for aS in range(aggSwitchStart,aggSwitchEnd + 1):
                for eS in range(EdgeSwitchStart,EdgeSwitchEnd + 1):
                    links[linkID] = ('s'+str(aS), 's'+str(eS))
                    linkID += 1
                for cS in range(numSwitchPorts//2):
                    links[linkID] = ('s'+str(coreSwitchStart + cS), 's'+str(aS))
                    linkID += 1
                coreSwitchStart += numSwitchPorts//2
        # links are directed
        for i in range(linkID - 1):
            links[i + linkID] = (links[i + 1][1], links[i + 1][0])

        C = {i:args.c for i in range(1, 2 * linkID - 1)}
 
        generate_config(args.config_folder, links, hosts, C, network_type='clos_pods', num_bytes = args.num_bytes, skewness = args.skewness,
                        K = args.k, link_delay=args.link_delay, default_link_delay=args.default_link_delay, link_loss=args.link_loss, 
                        default_link_loss=args.default_link_loss, default_link_bw=args.default_link_bw, tcp_congestion_control="bbr", 
                        collection_frequency=args.collection_frequency,tapering_num = args.tapering_num, result_prefix=args.result_prefix)
    else:
        raise RuntimeError("network type not supported")
