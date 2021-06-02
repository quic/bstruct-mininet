import numpy as np
from collections import OrderedDict
from copy import deepcopy
from warnings import warn


class Network:
    def __init__(self, F: dict, C: dict, L: dict = None, M: dict = None, num_links=None):
        """
            F : Flow dictionary (key = flow ID, value = link IDs)
            C : Capacity dictionary (key = link ID, value = capacity)
            L : Link dictionary (key = link ID, value = flow IDs)
            M : Minimal rate dictionary (key = flow ID, value = minimal rate)
            num_links : number of links in the network
        """
        self.F = F.copy()
        self.C = C.copy()
        self.num_links = num_links
        if L is None:
            self.L = self.l_from_f(F, num_links)
        else:
            self.L = L.copy()
        if M is None:
            self.M = {key: 0 for key in F.keys()}
        else:
            self.M = M.copy()

        self.input_F = deepcopy(self.F)
        self.input_C = deepcopy(self.C)
        self.input_L = deepcopy(self.L)
        self.input_M = deepcopy(self.M)

    def l_from_f(self, f: dict, num_links):
        L = dict() if num_links is None else {i: [] for i in range(self.num_links)}
        for key, links in f.items():
            for l in links:
                if l not in L.keys():
                    L[l] = [key]
                elif key not in L[l]:
                    L[l].append(key)
        return L

    def get_links(self, flow_idx, active=True):
        # use active to access current link pool, else access the original
        return self.F[flow_idx] if active else self.input_F[flow_idx]

    def get_flows(self, link_idx, active=True):
        # use active to access current link pool, else access the original
        return self.L[link_idx] if active else self.input_L[link_idx]

    def get_capacity(self, link_idx, active=True):
        # use active to access current link pool, else access the original
        return self.C[link_idx] if active else self.input_C[link_idx]

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

    def get_active_links(self):
        """
        :return: links that are none-empty
        """
        return [link_idx for link_idx in self.L.keys() if len(self.L[link_idx]) > 0]

    def get_connected_links(self, link_idx, L: dict = None, F: dict = None):
        """
        :param link_idx: a link ID
        :param flows: this function has an option for custom flows
        :param F: this function has an option for flow dict
        :return: a list of all link IDs that share at least one flow with link_idx (no duplications)
        """
        assert (L is None) == (F is None)
        if L is None:
            flows = self.get_flows(link_idx)
            F = self.F
        else:
            flows = L[link_idx]

        connected_links = set()  # a set
        for flow_idx in flows:
            connected_links = connected_links.union(F[flow_idx])
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

    def remove_link_flows_update_cap(self, link_idx, flow_rate_dict):
        """
        remove link_idx and the flows passing through it, then update capacities accordingly
        :param link_idx: the ID of link to be removed
        :param flow_rate_dict: a dict that has the rates of the flows to be removed
        :return:
        """
        flows = self.get_flows(link_idx)
        # update capacities
        for f in flows:
            for link in self.get_links(f):
                self.update_capacity(link, -flow_rate_dict[f])

        # remove links and flows
        del self.L[link_idx]
        del self.C[link_idx]
        for f in flows:
            for l in self.L.keys():
                if f in self.L[l]:
                    self.L[l].remove(f)
            del self.F[f]
            del self.M[f]

        # cleaning up
        links_to_remove = set()
        for l, cap in self.C.items():
            if np.isclose(cap, 0):
                links_to_remove.add(l)
            elif cap < 0:
                warn("Encountered negative capacity")

        for l, flows in self.L.items():
            if len(flows) == 0:
                links_to_remove.add(l)

        for l in links_to_remove:
            del self.C[l]
            del self.L[l]

    def link_set_is_empty(self):
        """
        :return: bool value of whether all links are empty
        """
        return len(self.get_active_links()) == 0

    @staticmethod
    def num_intersection(list1, list2):
        """
        :return: the intersection of two lists
        """
        return len(set(list1).intersection(list2))

    def has_shared_flows(self, link1, link2):
        return self.num_intersection(self.get_flows(link1, active=False),
                                     self.get_flows(link2, active=False)) > 0

    def calc_delta(self, ad_rate_dict, removed_link_set):
        """
        See definition 25 in lexicographic paper
        """
        delta_l = {}
        remaining_links = set(self.get_active_links()) - set(removed_link_set)
        for link_i in remaining_links:
            delta_l[link_i] = set()
            for link_j in removed_link_set:
                if self.has_shared_flows(link_i, link_j) and ad_rate_dict[link_j] < ad_rate_dict[link_i]:
                    delta_l[link_i].add(link_j)

        return delta_l

    def calc_i(self, ad_rate_dict, removed_link_set):  # link_idx:set
        """
        See definition 26 in lexicographic paper
        """
        i_l = {}
        remaining_links = set(self.get_active_links()) - set(removed_link_set)
        for link_i in remaining_links:
            i_l[link_i] = set()
            for link_j in removed_link_set:
                if self.has_shared_flows(link_i, link_j):
                    continue
                for link_k in remaining_links:  # ensures link_k not moved in this round
                    share_ind_flow = self.has_shared_flows(link_i, link_k) and self.has_shared_flows(link_j, link_k)
                    if share_ind_flow and ad_rate_dict[link_k] < ad_rate_dict[link_i]:
                        i_l[link_i].add(link_j)
        return i_l


def calc_bpg(network):
    """
    See figure 10 in lexicographic paper
    :param network: it accepts a Network object as defined above
    :return: 5 values:
        1) the bpg level of the network
        2) bpg vertices, format = {level: {link_idx: R}}
        3) bpg direct links, format = {upper level: [(link_src,link_dst)]}
        4) bpg indirect links, format = {upper level: [(link_src,link_dst)]}
        5) expected flow rates, format = {flow_id (sorted): flow_rate}
    """
    level = 1
    bpg_v = {}  # bpg vertexes, format = {level: {link_idx: R}}
    bpg_edge_dir = {}  # direct precedent links, format = {upper level: [(link_src,link_dst)]}
    bpg_edge_indir = {}  # indirect precedent links, format = {upper level: [(link_src,link_dst)]}
    flow_rates = {}
    # initialize DELTA, I
    all_links = network.get_active_links()
    # Format: {level: {link_idx: Potential Direct Precedent Links}}
    delta_all = {0: {link_idx: set() for link_idx in all_links}}

    # Format: {level: {link_idx: Potential Indirect Precedent Links}}
    i_all = {0: {link_idx: set() for link_idx in all_links}}

    while True:
        all_links = network.get_active_links()

        rate_dict = {}
        advertised_rates_dict = {}
        for link_idx in all_links:
            r, ad_rate = network.solve_single_link_cmm(link_idx)
            rate_dict[link_idx] = {flow: rate for flow, rate in zip(network.get_flows(link_idx), r)}
            advertised_rates_dict[link_idx] = ad_rate

        # Removing links and flows
        removed_link_set = set()
        # excluded_link_set = set()
        L_copy = deepcopy(network.L)
        F_copy = deepcopy(network.F)
        while True:
            remaining_link_set = network.get_active_links()
            if len(remaining_link_set) == 0:
                break

            for link_idx in remaining_link_set:
                # connected_links = network.get_connected_links(link_idx)
                connected_links = network.get_connected_links(link_idx, L=L_copy, F=F_copy)
                min_ad_rate = np.min([advertised_rates_dict[l] for l in connected_links])
                if np.isclose(advertised_rates_dict[link_idx], min_ad_rate):
                    # Adding flow rate information
                    flow_rates.update(rate_dict[link_idx])
                    removed_link_set.add(link_idx)

                    # 3.1 remove links/flows; update cap; update excluded link set
                    network.remove_link_flows_update_cap(link_idx, rate_dict[link_idx])

                    if level not in bpg_v.keys():  # 3.3 add to record
                        bpg_v[level] = {}
                    bpg_v[level][link_idx] = advertised_rates_dict[link_idx]
                    for shared_link in delta_all[level - 1][link_idx]:
                        if level - 1 not in bpg_edge_dir.keys():
                            bpg_edge_dir[level - 1] = []
                        bpg_edge_dir[level - 1].append((shared_link, link_idx))
                    for shared_link in i_all[level - 1][link_idx]:
                        if level - 1 not in bpg_edge_indir.keys():
                            bpg_edge_indir[level - 1] = []
                        bpg_edge_indir[level - 1].append((shared_link, link_idx))

                    break  # find the first link that has min ad rate, update remaining set, then continue
            else:
                break

        delta_l = network.calc_delta(advertised_rates_dict, removed_link_set)  # 4 calc delta and i
        i_l = network.calc_i(advertised_rates_dict, removed_link_set)

        delta_all[level] = delta_l
        i_all[level] = i_l

        if network.link_set_is_empty():
            break
        level += 1

    return level, bpg_v, bpg_edge_dir, bpg_edge_indir, OrderedDict(sorted(flow_rates.items(), key=lambda x: int(x[0])))
