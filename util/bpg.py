import numpy as np


class Network:
    def __init__(self, F, C, L=None, M=None, num_links=38):
        """
            F : Flow dictionary (key = flow ID, value = link IDs)
            C : Capacity dictionary (key = link ID, value = capacity)
            L : Link dictionary (key = link ID, value = flow IDs)
            M : Minimal rate dictionary (key = flow ID, value = minimal rate)
            num_links : number of links in the network, the default 38 accounts for Google's B4 network
        """
        self.F = F
        self.C = C
        self.num_links = num_links
        if L is None:
            self.L = self.L_from_F(F)
        else:
            self.L = L
        if M is None:
            self.M = {key: 0 for key in F.keys()}
        else:
            self.M = M

    def L_from_F(self, F):
        """
        In case only flow dictionary is given, this function obtains link dictionary from flow dictionary.
        Note that L depends on num_links
        """
        L = {i: [] for i in range(self.num_links)}
        for key, val in F.items():
            for link in val:
                L[link].append(key)
        return L

    def get_links(self, flow_idx):
        return self.F[flow_idx]

    def get_flows(self, link_idx):
        return self.L[link_idx]

    def get_capacity(self, link_idx):
        return self.C[link_idx]

    def get_min_rates(self, list_flow_idx):
        return np.array([self.M[i] for i in list_flow_idx])

    @staticmethod
    def get_advertised_rate(rates, min_rates, capacity):
        """
        Given a list of rates, minimal rates and the link's capacity, returns the advertised rate of this link
        """
        if not np.isclose(np.sum(rates), capacity):  # relative tolerance = 1e-08
            return np.inf
        elif np.all(rates == min_rates):
            return 0
        else:
            return np.max([rates[i] for i in range(len(rates)) if rates[i] > min_rates[i]])

    def get_all_links(self):
        """
        :return: links that are none-empty
        """
        return [link_idx for link_idx in self.L.keys() if len(self.L[link_idx]) > 0]

    def get_connected_links(self, link_idx):
        """
        :param link_idx: a link ID
        :return: a list of all link IDs that share at least one flow with link_idx (no duplications)
        """
        flows = self.get_flows(link_idx)
        connected_links = set()  # a set
        for flow_idx in flows:
            connected_links = connected_links.union(self.F[flow_idx])
        return list(connected_links)

    def solve_single_link_cmm(self, link_idx):
        """
        (See Fig. 3 in lexicographic paper)
        :param link_idx:
        :return: rates and advertised rates of link_idx
        """
        flows = self.get_flows(link_idx)  # list of flows passing link_idx
        num_flows = len(flows)  # num flows
        capacity = self.get_capacity(link_idx)  # link capacity
        min_rates = self.get_min_rates(flows)  # min rates

        rates = np.zeros(num_flows)
        is_constrained_flow = [False for _ in range(num_flows)]  # constrained flows indicator
        total_constrained_flow_rate = 0
        num_constrained_flows = 0
        ad_rate = 0

        while True:
            rl = float(capacity - total_constrained_flow_rate) / (num_flows - num_constrained_flows)
            for i in range(num_flows):
                if not is_constrained_flow[i]:
                    rates[i] = rl

            ad_rate = self.get_advertised_rate(rates, min_rates, capacity)

            is_end = True
            for i in range(num_flows):
                if not is_constrained_flow[i] and rates[i] != np.max([ad_rate, min_rates[i]]):
                    rates[i] = np.max([ad_rate, min_rates[i]])
                    num_constrained_flows += 1
                    total_constrained_flow_rate += rates[i]
                    is_constrained_flow[i] = True

                    is_end = False

            if is_end:
                break

        return rates, ad_rate

    def update_capacity(self, link_idx, inc):
        """
        :param link_idx: the index of link to be updated
        :param inc: the increment to be added to link_idx; usually negative
        :return:
        """
        self.C[link_idx] += inc

    def remove_link_and_flows(self, link_idx):
        """
        remove link_idx and the flows passing through it
        :param link_idx: the ID of link to be removed
        :return:
        """
        flows = self.get_flows(link_idx)
        del self.L[link_idx]
        del self.C[link_idx]
        for f in flows:
            for l in self.L.keys():
                if f in self.L[l]:
                    self.L[l].remove(f)
            del self.F[f]
            del self.M[f]

    def link_set_is_empty(self):
        """
        :return: bool value of whether all links are empty
        """
        return len(self.get_all_links()) == 0

    @staticmethod
    def num_intersection(list1, list2):
        """
        :return: the intersection of two lists
        """
        return len(set(list1).intersection(list2))

    def calc_delta(self, ad_rate_dict, removed_link_set):
        """
        See definition 25 in lexicographic paper
        """
        delta_l = {}
        remaining_links = set(self.get_all_links()) - set(removed_link_set)
        for link_i in remaining_links:
            delta_l[link_i] = set()
            for link_j in removed_link_set:
                if self.num_intersection(self.get_flows(link_i), self.get_flows(link_j)) > 0 and ad_rate_dict[link_j] < \
                        ad_rate_dict[link_i]:
                    delta_l[link_i].add(link_j)

        return delta_l

    def calc_i(self, ad_rate_dict, removed_link_set):  # link_idx:set
        """
        See definition 26 in lexicographic paper
        """
        i_l = {}
        remaining_links = set(self.get_all_links()) - set(removed_link_set)
        for link_i in remaining_links:
            i_l[link_i] = set()
            for link_j in removed_link_set:
                if self.num_intersection(self.get_flows(link_i), self.get_flows(link_j)) == 0:
                    for link_k in remaining_links:  # ensures link_k not moved in this round
                        if self.num_intersection(self.get_flows(link_i), self.get_flows(link_k)) > 0 \
                                and self.num_intersection(self.get_flows(link_j), self.get_flows(link_k)) > 0 \
                                and ad_rate_dict[link_k] < ad_rate_dict[link_i]: i_l[link_i].add(link_j)
        return i_l


def calc_bpg(network):
    """
    See figure 10 in lexicographic paper
    :param network: it accepts a Network object as defined above
    :return: 5 values:
        1) the bpg level of the network
        2) bpg vertices, see below for format
        3) bpg direct links, see below for format
        4) bpg indirect links, see below for format
        5) expected flow rates, format = [{'flows': {f1...fn}, 'rate': r}, ...] which means f1...fn have expected rate
           of r
    """
    level = 1
    bpg_v = {}  # bpg vertices, format = {level: [{link_idx: R}]}
    bpg_e_dir = {}  # direct precedent links, format = {upper level: [(link_src,link_dst)]}
    bpg_e_indir = {}  # indirect precedent links, format = {upper level: [(link_src,link_dst)]}
    flow_rates = []
    # initialize DELTA, I
    all_links = network.get_all_links()
    delta_all = {
        0: {link_idx: set() for link_idx in all_links}}  # {level: {link_idx: Potential Direct Precedent Links}}
    i_all = {0: {link_idx: set() for link_idx in all_links}}  # {level: {link_idx: Potential Indirect Precedent Links}}

    while True:
        all_links = network.get_all_links()

        rate_dict = {}
        advertised_rates_dict = {}
        for link_idx in all_links:
            r, ad_rate = network.solve_single_link_cmm(link_idx)
            rate_dict[link_idx] = {flow: rate for flow, rate in zip(network.get_flows(link_idx), r)}
            advertised_rates_dict[link_idx] = ad_rate

        removed_link_set = set()
        flow_set_to_skip = set()

        for link_idx in all_links:
            connected_links = network.get_connected_links(link_idx)
            if advertised_rates_dict[link_idx] == np.min([advertised_rates_dict[l] for l in connected_links]):  # TODO
                for l in connected_links:  # 3.1 update cap
                    for shared_flow in set(network.get_flows(link_idx)).intersection(network.get_flows(l)):
                        if shared_flow not in flow_set_to_skip:
                            for link in network.get_links(shared_flow):
                                network.update_capacity(link, -rate_dict[link_idx][shared_flow])
                            flow_set_to_skip.add(shared_flow)

                removed_link_set.add(link_idx)

                if level not in bpg_v.keys():  # 3.3 add to record
                    bpg_v[level] = []
                bpg_v[level].append({link_idx: advertised_rates_dict[link_idx]})
                for shared_link in delta_all[level - 1][link_idx]:
                    if level - 1 not in bpg_e_dir.keys():
                        bpg_e_dir[level - 1] = []
                    bpg_e_dir[level - 1].append((shared_link, link_idx))
                for shared_link in i_all[level - 1][link_idx]:
                    if level - 1 not in bpg_e_indir.keys():
                        bpg_e_indir[level - 1] = []
                    bpg_e_indir[level - 1].append((shared_link, link_idx))

        delta_l = network.calc_delta(advertised_rates_dict, removed_link_set)  # 4 calc delta and i
        i_l = network.calc_i(advertised_rates_dict, removed_link_set)

        delta_all[level] = delta_l
        i_all[level] = i_l

        flows_removed_at_level = set()
        flow_rate_at_level = 0
        for link_idx in removed_link_set:
            flows_removed_at_level = flows_removed_at_level.union(network.get_flows(link_idx))
            flow_rate_at_level = advertised_rates_dict[link_idx]
            network.remove_link_and_flows(link_idx)  # 3.2 remove
        flow_rates.append({"flows": flows_removed_at_level, "rate": flow_rate_at_level})

        if network.link_set_is_empty():
            break

        level += 1

    return level, bpg_v, bpg_e_dir, bpg_e_indir, flow_rates
