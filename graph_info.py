# 1556, Thu 22 Oct 2020 (NZDT)
# 1646, Tue 21 Apr 2020 (NZST)
# 1658, Sun 30 Jun 2019 (NZST)
# 1802, Thu  1 Mar 2018 (NZDT)
# 1427, Tue  1 Aug 2017 (NZST)
#
#  graphinfo.py: NodeInfo, Edge, Path, SubRoot and GraphInfo classes
#                GraphInfo has the summary stats routines!
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import math
import numpy as np
import scipy.stats
import sys, ipaddress
from matplotlib.colors import Normalize

import config as c

def one_runs(a):  # _runs functions used in the Classes below
    # https://stackoverflow.com/questions/24885092/finding-the-consecutive-zeros-in-a-numpy-array
    w = np.logical_not(np.equal(a, 0))  # 1s for each 0 in a
    isone = np.concatenate(([0], w.view(np.int8), [0]))
    absdiff = np.abs(np.diff(isone))  # 1 in position before change
    return np.where(absdiff == 1)[0].reshape(-1, 2)  # Ranges of 1s

def zero_runs(a):
    iszero = np.concatenate(([0], np.equal(a, 0).view(np.int8), [0]))
    absdiff = np.abs(np.diff(iszero))  # 1 in element before change
    # Runs start and end where absdiff is 1.
    return np.where(absdiff == 1)[0].reshape(-1, 2)  # Ranges of 0s

class OutObjects:
    def __init__(self, obj, kind, asn_graphs):
            # kind = n (node) or e (edge)
        self.obj = obj;  self.kind = kind;  self.asn_graphs = asn_graphs
        self.zeros = np.equal(obj.icounts, 0).astype(int)
        self.times_seen = self.trpkts = self.av_trpkts = 0
        self.sd_asns = {}
            # ASN (n) or src->dst ASNs (e) with same set of zeros

    def __str__(self):
        zra = one_runs(self.zeros)
        zs = ""
        for j,zrun in enumerate(zra):
            #print("?? j %d, zrun %s" % (j, zrun))
            if zrun[0] == zrun[1]-1:  # 0,1 pair in zrun
                zs += "%d, " % zrun[0]
            else:  # run of zeroes in zrun
                zs += "%d-%d, " % (zrun[0],zrun[1])
        ks = "edge"
        if self.kind == "n":
            ks = "node"
        n_trpkts = self.trpkts
        if self.times_seen > 1:
            ks += "s"
            n_trpkts /= self.times_seen
        return "%2d %s, %4d pkts (average), zero for bin(s) <%s>" % (
            self.times_seen, ks, n_trpkts, zs[:-2])

    def __eq__(self, oe):
        return np.array_equal(self.zeros, oe.zeros)
        # oe in oea  is true if  all it's zeros match

    def index(self, oea):  # oea = array of OutEdge objects
        for oe in oea:
            if np.array_equal(self.zeros, oe.zeros):
                return oe  # (pointer to) object
        return -1

    def update(self, trpkts, ok):  # ok = Object key
        self.times_seen += 1
        self.trpkts += trpkts
        if ok not in self.sd_asns:
            self.sd_asns[ok] = [trpkts]
        else:
            self.sd_asns[ok].append(trpkts)
        self.av_trpkts += trpkts

class NodeInfo:  # Called while graphs file is being read
    def update(self, bn, icount, fails, roots, sna):  # Sets info for bin bn
        #print("-- %s: %s" % (self.name, sna))
        self.icounts[bn] = icount;  self.sna_len[bn] = len(sna)
        self.fails[bn] = fails;  self.internal = True
        edict = {}  # Incoming edges
        for j in range(0, len(sna)-1, 2):
            edict[sna[j]] = int(sna[j+1])
        self.in_edges[bn] = edict
        
    def __init__(self, bn, dest, name, internal,
                 node_dir, icount, fails, roots, sna, n_bins, no_asn_nodes):
        #print("bin %d, roots = %s" % (bn, roots))
        self.name = name;  self.root = name == dest;  self.n_bins = n_bins
        self.node_dir = node_dir;  self.no_asn_nodes = no_asn_nodes
        self.internal = internal  # Appeared in a Node line
        self.present = np.zeros(self.n_bins)
        self.icounts = np.zeros(self.n_bins)
        self.sna_len = np.zeros(self.n_bins)
        self.fails = np.zeros(self.n_bins)
        self.in_edges = [ {} ]*self.n_bins  # Separate directory for each bin
        self.asn = self.node_asn(name)
        self.update(bn, icount, fails, roots, sna)  # Start from bin bn
        self.av_icount = 0
        
    def node_asn(self, prefix):
        #print("edge.node_asn(%s), node_dir[] %s" % (prefix, self.node_dir[prefix]))
        if prefix in self.node_dir:
            return self.node_dir[prefix]
        else:
            if not prefix in self.no_asn_nodes:
                self.no_asn_nodes[prefix] = True
            return "unknown"
        
    def __str__(self):
        there = '';  pstr = self.present
        for bn in range(0, len(pstr)):  # Make string of 1s and 0s
            there += str(pstr[bn])
        return "%17s %5d %s: %s" % (self.name, self.av_icount, self.internal,
            there)  #self.icounts.astype(int))  # there)

class Edge:  # Called while graphs file is being read
    def __init__(self, src, dest, node_dir, n_bins, asn_graph, no_asn_nodes):
        self.n_from = src;  self.n_to = dest  # Node names
        self.node_dir = node_dir;  self.n_bins = n_bins
        self.asn_graph = asn_graph;  self.no_asn_nodes = no_asn_nodes
        self.icounts = np.zeros(self.n_bins);  self.av_icount = 0
        self.msm_id = self.pv = self.ps = self.zra = None
        if c.full_graphs:
            self.asn = self.asn_from = self.node_asn(src)
            self.asn_to = self.node_asn(dest)
        else:
            self.asn_from = src;  self.asn_to = dest
        self.last_nb = 0
        #  Set by GraphInfo.examine_edges() (for ek in self.edges:)
        self.present = self.n_ones = self.n_zeroes = \
            self.zra_len = self.n_zruns = self.mx_zrun = \
            self.ora_len = self.o_runs = self.mx_orun = 0
        # self.p_counts is a gi attribute for Edges
        
        if c.full_graphs:
            self.asn = self.asn_from = self.node_asn(src)
            self.asn_to = self.node_asn(dest)
        else:
            self.asn_from = src;  self.asn_to = dest
        self.inter_as = self.asn_from != self.asn_to
        self.plot_label = '';  self.pv = False
            # label and presence array for plots
        #print("Edge.init(): asn_from = %s, asn_to = %s" % (self.asn_from, self.asn_to))

    def set_icount(self, nb, count):
        self.icounts[nb] = count

    def __str__(self):
        #print("e.plot_label = >%s<" % self.plot_label)
        if self.asn_graph:
            return "%s --%.2f--> %s" % (self.n_from,
                self.av_icount, self.n_to)
        else:
            return "%s (%s) --%.2f--> %s (%s)" % (
                self.n_from, self.asn_from,
                self.av_icount,
                self.n_to, self.asn_to)

    def __eq__(self, e):
        return self.n_from == e.n_from and self.n_to == e.n_to

    def distance(self, e2):
        return np.sum(self.pv == e2.pv)

    def node_asn(self, prefix):  # Used for src,dst nodes !
        #print("edge.node_asn(%s), node_dir[] %s" % (prefix, self.node_dir[prefix]))
        if prefix in self.node_dir:
            return self.node_dir[prefix]
        else:
            if not prefix in self.no_asn_nodes:
                self.no_asn_nodes[prefix] = True
            return "unknown"

class Path:  # list of Edges
    def __init__(self, edge, bn):
        self.edges = [edge]
        self.mx_icount = [0]*self.n_bins
        ##self.mx_icount[bn] = edge.count
        self.key = ""
        
    def __str__(self):
        e_str = ''
        for e in self.edges:
            e_str += ", %s" % str(e)
        return "[%s]" % e_str[2:]

    def __eq__(self, p):
        if len(self.edges) != len(p.edges):
            return False
        for j in range(0, len(self.edges)):
            if not self.edges[j] == p.edges[j]:
                return False
        return True

    def set_mx_count(self, bn):
        mx = 0
        for e in self.edges:
            if e.count > mx:
                mx = e.count
        self.mx_icount[bn] = mx

    def add_edge(self, e, bn):  # Return True if edge e added into Path
        if e in self.edges:
            self.set_mx_count(bn)
            return True  # Already there
        if e.n_to == self.edges[0].n_from:
            self.edges.insert(0,e);  self.key = e.key + ", " + self.key
            self.set_mx_count(bn)
            return True
        elif e.n_from == self.edges[-1].n_to:
            self.edges.append(e);  self.key += ", " + e.key
            self.set_mx_count(bn)
            return True
        return False

    def keep(self):  # Is important enough to keep?
        for e in self.edges:
            if e.count >= 250:
                return True
        return len(self.edges) > 1

class SubRoot:            
    def __init__(self, name, sub_root_icounts):  # Called after graphs file read
        self.name = name  # Address (or ASN) of sub_root
        self.sub_root_icounts = sub_root_icounts  # List of trpkts per bin
        ec = np.array(self.sub_root_icounts)
        self.present = np.greater_equal(ec, c.draw_mn_trpkts).astype(bool)
        self.max_icount = np.max(ec)
        self.av_icount = np.average(ec, axis=0, weights=ec.astype(bool))
        self.nz_counts = np.count_nonzero(self.sub_root_icounts)
        ora = one_runs(self.sub_root_icounts)
        ora_len = ora[:,1]-ora[:,0]  # Run-of-ones lengths
        self.n_oruns = len(ora_len)
        ##print("   self.n_oruns = %d" % self.n_oruns)
        self.mx_orun = 0
        if self.n_oruns != 0:
            self.mx_orun = ora_len.max()
            icount = self.sub_root_icounts
            self.sub_root_icounts = icount[icount >= c.draw_mn_trpkts]
        self.plot_label = '';  self.pv = False

        #print("SubRoot: name=%s, nz_counts=%s" % (self.name, self.nz_counts))

    def __str__(self):
        rs = "subroot %s\n   counts %s" % (self.name, self.sub_root_icounts)
        return rs

class GraphInfo:
    #dta_size = 43  # 0:42 tr pkts (tr tries three pkts at each depth)
    trpkt_sizes = np.arange(0,42)  # Counted in linear array 0:42
    trpart_sizes = np.array([38, 39, 48, 63, 81, 102, 132, 168,  # log array
        213, 273, 348, 447, 570, 726, 927, 1182, 1509, 1926, 2457,
        3135, 4000, 5103, 6513, 8313, 10608, 13536, 17271, 23097, 28977])
        # 38 counts all the sizes below 39 !!!

    def nz_len(self, a):  # Find highest non-zero value
        for j in range(0, len(a)):
            k = len(a)-1-j
            if a[k] != 0:
                return k

    def pc_depths(self, bn, depth_counts):
        mx_depth = self.nz_len(depth_counts)
        depth_v = [16, 19, 25, 32];  pc_covered = []
        cum_depths = np.cumsum(depth_counts)  # Cumulative counts
        #print("cum_depths = %s" % cum_depths)
        tot_counts = cum_depths[-1]
        for depth in depth_v:
            pc_covered.append(cum_depths[depth]*100.0/tot_counts)
        self.depth_16[bn] = pc_covered[0]
        self.depth_19[bn] = pc_covered[1]
        self.depth_25[bn] = pc_covered[2]
        self.depth_32[bn] = pc_covered[3]
        self.mx_depth[bn] = mx_depth
        #print("depths %s covers %s %% of the graph, max depth = %d" % (
        #    depth_v, pc_covered, mx_depth))
        #print("pc_depths: depth_16 = %s" % self.depth_16)
        return

    def pc_trpkts(self, bn, trpkt_counts, trpkt_sizes,
            trpart_counts, trpart_sizes):
        trpkt_prod = trpkt_counts * trpkt_sizes
        trpkts_sum = np.sum(trpkt_prod)
        #print("trpkts_sum = %d" % trpkts_sum)
        trparts_sum = np.sum(trpart_counts*trpart_sizes)
        #print("tr_parts_sum = %d" % trparts_sum)

        all_sizes = np.concatenate( (trpkt_sizes, trpart_sizes) )
        all_counts = np.concatenate( (trpkt_counts, trpart_counts) )
        all_trpkts = all_counts*all_sizes
        cum_trpkts = np.cumsum(all_trpkts)  # Cumulative counts
        #print("sum(parts*size) = %s" % cum_trpkts)
        tot_trpkts = int(cum_trpkts[-1])
        min_trpkts = [3, 9, 27, 81];  pc_covered = []
        for trp in min_trpkts:
            sz_index = (np.abs(all_sizes-trp)).argmin() 
            pc_covered.append(100.0 - cum_trpkts[sz_index]*100.0/tot_trpkts)
        self.trpkts_3[bn]  = pc_covered[0]
        self.trpkts_9[bn]  = pc_covered[1]
        self.trpkts_27[bn] = pc_covered[2]
        self.trpkts_81[bn] = pc_covered[3]
        #print("min_trpkts %s covers %s %% of the graph" % (
        #    min_trpkts, pc_covered))
        #print("pc_trpkts: trpkts_3 = %s" % self.trpkts_3)
        return

#    def index(self, x):
#        return (np.abs(self.np_trpart_sizes - x)).argmin()
#            # Find closest value to x

    def start_bin(self, bn):
        print("Starting bin %d" % bn)
        #info_f.write("Bin %d\n" % bn)
        self.node_depths = np.zeros(c.mx_depth+1)
        dta_size = 43  # 0:42 tr pkts (tr tries three pkts at each depth)
        self.node_trpkts = np.zeros(dta_size)
        self.trparts_bin =  np.zeros(len(self.trpart_sizes))
            # trpkt_parts for this bin
        
    def end_bin(self, msm_id, bn):
        self.pc_depths(bn, self.node_depths)
        self.pc_trpkts(bn, self.node_trpkts[0:39], self.trpkt_sizes[0:39],
            self.trparts_bin[1:], self.trpart_sizes[1:])
        return
        
    def start_msm_id(self):
        self.depth_16 = np.zeros(self.n_bins)  # Counts for each bin
        self.depth_19 = np.zeros(self.n_bins)
        self.depth_25 = np.zeros(self.n_bins)
        self.depth_32 = np.zeros(self.n_bins)
        self.mx_depth = np.zeros(self.n_bins)
        self.trpkts_3  = np.zeros(self.n_bins)
        self.trpkts_9  = np.zeros(self.n_bins)
        self.trpkts_27 = np.zeros(self.n_bins)
        self.trpkts_81 = np.zeros(self.n_bins)
        return

    def variable(self, v_name, v):
        mean = np.mean(v);  iqr = scipy.stats.iqr(v)
        #print("%s  mean = %7.2f, iqr = %7.2f" % (v_name, mean, iqr))

    def end_msm_id(self):
        print("End of msm_id %d\n" % self.msm_id)
        return  # Don't print anything here!
        '''
        self.variable("depth_16: ", self.depth_16)
        self.variable("depth_19: ", self.depth_19)
        self.variable("depth_25: ", self.depth_25)
        self.variable("depth_32: ", self.depth_32)
        print()
        self.variable("mx_depth: ", self.mx_depth)
        print()
        self.variable("trpkts_3: ", self.trpkts_3)
        self.variable("trpkts_9: ", self.trpkts_9)
        self.variable("trpkts_27:", self.trpkts_27)
        self.variable("trpkts_81:", self.trpkts_81)
        return
        '''

    def __init__(self, msm_id, node_dir, n_bins, asn_graph,
            n_asns, no_asn_nodes, mx_allowed_depth, mn_allowed_trpkts):
        self.msm_id = msm_id
        self.mn_allowed_trpkts = mn_allowed_trpkts
        self.fn = None  # graphs- filename
        self.n_traces = self.n_succ_traces = self.n_dup_traces = \
            self.t_addrs = self.t_hops = self.t_hops_deleted = 0

        self.node_dir = node_dir;  self.n_bins = n_bins
        print("  GraphInfo node_dir len = %d" % len(self.node_dir))
        self.asn_graph = asn_graph;  self.no_asn_nodes = no_asn_nodes
        self.n_asns = n_asns
        self.sub_root_icounts = {}  # in_count (for all bins)

        self.stats = {}
        self.p_counts = np.zeros(self.n_bins+1)  # Edges in bins 0..(c.n_bins)
        self.stats['edges_counts'] = self.p_counts
        self.all_edges = {}  # All edges seen in whole GraphInfo

        self.n_traces = np.zeros(self.n_bins)  # Totals from BinGraph lines
        self.stats["n_traces"] = self.n_traces
        self.n_succ_traces = np.zeros(self.n_bins)
        self.stats["trs_success"] = self.n_succ_traces
        self.n_dup_traces = np.zeros(self.n_bins)
        self.stats["n_dup_traces"] = self.n_dup_traces
        self.t_addrs = np.zeros(self.n_bins)
        self.stats["t_addrs"] = self.t_addrs
        self.t_hops = np.zeros(self.n_bins)
        self.stats["t_hops"] = self.t_hops
        self.t_hops_deleted = np.zeros(self.n_bins)
        self.stats["t_hops_deleted"] = self.t_hops_deleted

        self.dest = ""        # Dest IP address for traces
        self.all_nodes = {}  # Nodes in graphs file
        self.distal_nodes = {}  # Nodes from s_nodes lines
        self.nodes_tot = np.zeros(self.n_bins)
            # All nodes in graph (from s_node_nodes)
        self.stats["nodes_tot"] = self.nodes_tot
        self.outer_nodes = np.zeros(self.n_bins)  # Nodes in s_nodes lines
        self.stats["outer_nodes"] = self.outer_nodes
        self.nodes_1hop = np.zeros(self.n_bins)  # 1 hop before dest
        self.stats["nodes_1hop"] = self.nodes_1hop
        self.trpkts_tot = np.zeros(self.n_bins)  # trs from probes
        self.stats["trpkts_tot"] = self.trpkts_tot
        #lsp_trpkts = [39, 60, 93, 141, 213, 327, 501, 768, 1176]

        self.trpkts_part = []
        for k in range(0,len(self.trpart_sizes)):
            self.trpkts_part.append(np.zeros(self.n_bins))  # trs in each part

        self.start_msm_id()  # Initialise depth and tr variables
        self.stats["depth_16 (%)"] = self.depth_16
        self.stats["depth_19 (%)"] = self.depth_19
        self.stats["depth_25 (%)"] = self.depth_25
        self.stats["depth_32 (%)"] = self.depth_32
        self.stats["depth_max"] = self.mx_depth
        self.stats["trpkts_3 (%)"] = self.trpkts_3
        self.stats["trpkts_9 (%)"] = self.trpkts_9
        self.stats["trpkts_27 (%)"] = self.trpkts_27
        self.stats["trpkts_38 (%)"] = self.trpkts_81

        self.trs_dest = np.zeros(self.n_bins)  # trs arriving at dest
        self.stats["trpkts_dest"] = self.trs_dest
        self.stats["asns_tot"] = self.n_asns
        self.n_subroots = np.zeros(self.n_bins)  # subroots for each bn
        self.stats["subroots"] = self.n_subroots
        self.n_subroot_trs = np.zeros(self.n_bins)
        self.stats["trpkts_subroot"] = self.n_subroot_trs

        self.tot_edges = np.zeros(self.n_bins)  # Nbr of edges
        self.stats['edges_tot'] = self.tot_edges
        self.bin_same_edges = np.zeros(self.n_bins)
        self.bin_inter_edges = np.zeros(self.n_bins)
        self.stats['edges_same'] = self.bin_same_edges
        self.stats['edges_inter'] = self.bin_inter_edges

        self.same_counts = np.zeros(self.n_bins+1)
        self.inter_counts = np.zeros(self.n_bins+1)
        # same_counts[] and inter_counts[] are np arrays
        #   indicating the number of bins their edges were actaully present.
        #   Computed by the asn_edges() function (below)
        # Used by cum-edge-presence-v-timebins.py

        self.distal_mx_depth = np.zeros(self.n_bins)
        self.stats['distal_mx_depth'] = self.distal_mx_depth
        self.distal_min_ntrs = np.zeros(self.n_bins)
        self.stats['distal_min_trs'] = self.distal_min_ntrs

        self.same_asn_edges = np.zeros(self.n_bins)  # Edges in same ASN
        self.stats['edges_same'] = self.same_asn_edges
        self.inter_asn_edges = np.zeros(self.n_bins)  # Edges between ASNs
        self.stats['edges_inter'] = self.inter_asn_edges
        self.stats_fn = c.stats_fn(c.msm_id)
        #?sf = open(self.stats_fn, "r")
        #?for line in sf:
        ###self.last_bn = 0#; self.ne = 3  #################################

        #info_f.write("msm_id %d\n" % msm_id)

        self.fn = c.msm_graphs_fn(self.msm_id)
        print(" >>> %s / %d: %s" % (c.start_ymd, msm_id, self.fn))
        f = open(self.fn, "r")
        gf_version = 1
        bn = -1
        mxa_depth = mna_trpkts = 0
        if mx_allowed_depth:
            mxa_depth = mx_allowed_depth  # True
        if mn_allowed_trpkts:
            mna_trpkts = mn_allowed_trpkts  # True
        print("   mxa_depth %d, mna_trpkts %d" % (mxa_depth, mna_trpkts))

        nodes_this_bin = {}  #  Nodes found in Node lines
        s_nodes = {}  # Nodes found in s_nodes lines
        trpkts_tot = 0 
        mx_depth_seen = 0;  mx_n_depth_seen = 0
        for line in f:  # Read in the graphs file
            la = line.strip().split(maxsplit=1)
            if la[0] == "BinGraph":
                if bn >= 0:
                    self.trpkts_tot[bn] = trpkts_tot
                    self.n_subroots[bn] = n_subroots
                    self.n_subroot_trs[bn] = n_subroot_trpkts
                    self.tot_edges[bn] = len(self.edges)
                    self.same_asn_edges[bn] = bin_same_edges
                    self.inter_asn_edges[bn] = bin_inter_edges
                    self.end_bin(msm_id, bn)
                    self.nodes_tot[bn] = len(s_nodes)
                    ext_nodes = 0
                    for nn in s_nodes:
                        if nn not in nodes_this_bin:
                            ext_nodes += 1
                    self.outer_nodes[bn] = ext_nodes

                ila = list(map(int, la[1].split()))
                bn = ila[6]
                #if bn == 5:  # Testing, testing . . .
                #    break
                self.n_traces[bn] = ila[0]
                self.n_succ_traces[bn] = ila[1]
                self.n_dup_traces[bn] = ila[2]
                self.t_addrs[bn] = ila[3]
                self.t_hops[bn] = ila[4]
                self.t_hops_deleted[bn] = ila[5]

                self.start_bin(int(bn))
                            
                roots_line = f.readline()
                rla = roots_line.strip().split()
                self.dest = rla[1]  # Save the dest

                self.nodes = {}  # Dictionary, all nodes seen >> in bin bn <<
                self.edges = {}  # Ditto for edges (use np arrays for the bins)
                self.paths = {}  # Ditto for paths
                trpkts_tot = 0;  s_nodes = {};  nodes_this_bin = {}
                node_lines = n_subroots = n_subroot_trpkts = 0
                bin_same_edges = bin_inter_edges = 0
                for r in rla[2:]:  # rla[0] = mx_counts, rla[1] = dest
                    if not r in self.sub_root_icounts:  # r = subroot name
                        self.sub_root_icounts[r] = np.zeros(self.n_bins+1)
                    n_subroots += 1
            elif la[0] == "Node":
                nv = la[1].split()
                name = nv[0];  subnet = int(nv[1])
                # 'subtree' as found when building the graph
                icount = int(nv[2]);  depth = int(nv[3])
                if depth >  mx_depth_seen:
                    mx_depth_seen = depth
                #print("NO: depth %d, la %s\n    rla %s" % (
                #    depth, la, rla))

                if depth >= len(self.node_depths):
                    self.node_depths = np.append(self.node_depths,
                        np.zeros(depth+10-len(self.node_depths)))
                self.node_depths[depth] += 1
                if icount < len(self.node_trpkts):
                    self.node_trpkts[icount] += 1
                trpkts_tot += icount
                self.trparts_bin[
                    (np.abs(self.trpart_sizes-icount)).argmin()] += 1

                if name in self.sub_root_icounts and \
                        icount >= self.mn_allowed_trpkts:
                    self.sub_root_icounts[name][bn] = icount
                    n_subroot_trpkts += icount
                fails = -1  # Not in v1 graphs file
                if gf_version != 1:
                    fails = int(nv[3])
                s_nodes_line = f.readline()  # s_nodes line
                sna = s_nodes_line.split()  # name, in_count pairs
                for j in range(0, len(sna)-1, 2):  # name.count pairs, + depth
                    src_name = sna[j];  in_pkts = int(sna[j+1])
                    if src_name not in self.distal_nodes:
                        self.distal_nodes[src_name] = NodeInfo(
                            bn, self.dest, src_name, False,
                            self.node_dir, in_pkts, fails, [], [],
                            self.n_bins, no_asn_nodes)
                        #print("bn %2d src_name %s, icounts %s <<< new" % (
                        #    bn, src_name,
                        #    self.distal_nodes[src_name].icounts.astype(int)))
                    else:
                        self.distal_nodes[src_name].icounts[bn] = in_pkts
                        #print("bn %2d src_name %s, in_pkts %s" % (
                        #    bn, src_name, 
                        #    self.distal_nodes[src_name].icounts.astype(int)))
                
                if name not in nodes_this_bin:
                    nodes_this_bin[name] = True
                if name not in self.all_nodes:  # Get info about nodes
                    self.all_nodes[name] = NodeInfo(bn, self.dest, name, 
                        True, self.node_dir, icount, fails, rla, sna,
                        self.n_bins, no_asn_nodes)
                else:
                    self.all_nodes[name].update(
                        bn, icount, fails, rla, sna)
                #print("-2- %s" % (self.all_nodes[name]))

                if name == self.dest:
                    n_1hop = 0
                    for j in range(0, len(sna)-1, 2):
                        count = int(sna[j+1])
                        if count >= mn_allowed_trpkts:
                            n_1hop += 1  # Edges to be drawn on graphs
                            # There are also _lots_ of edges with count < 27 !!!
                    self.nodes_1hop[bn] = n_1hop
                    self.trs_dest[bn] = icount

                #print("s_nodes: >%s<" % sna)
                n_depth = int(sna.pop())  # Depth of s_node edges
                #print("     depth %d" % n_depth)
                for j in range(0, len(sna), 2):  # Get info about edges
                    src = sna[j];  count = int(sna[j+1])
                        # "distal" (probe) nodes only appear in s_nodes lines!
                        # "internal" nodes are sources for nodes nearer to dest
                    if not src in s_nodes:
                        s_nodes[src] = True                    
                    e_key = "%s %s" % (src, name)
                    in_all_edges = False
                    if not e_key in self.all_edges:  # Edges in all bins
                        e = self.all_edges[e_key] = Edge( src, name,
                            self.node_dir, self.n_bins, asn_graph, no_asn_nodes)
                    else:
                        e = self.all_edges[e_key]
                        in_all_edges = True
                    e.set_icount(bn, count)
                    if e_key not in self.edges:  # Edges in this bin
                        self.edges[e_key] = e
                    if e.inter_as:
                        bin_inter_edges += 1
                    else:
                        bin_same_edges += 1
           
            elif la[0] == "DestGraphs":
                nv = la[1].split()  # One or more white-space chars
                self.dest = nv[1]
                if len(nv) > 7:  # nv[7] = min_tr_pkts (last in v1 headers)
                    gf_version = 2

        self.end_msm_id()  # EOF reached

        self.n_subroots[bn] = n_subroots
        self.n_subroot_trs[bn] = n_subroot_trpkts
        self.tot_edges[bn] = len(self.edges)
        self.same_asn_edges[bn] = bin_same_edges
        self.inter_asn_edges[bn] = bin_inter_edges
        self.outer_nodes[bn] = len(s_nodes)
        self.trpkts_tot[bn] = trpkts_tot
        print("<<< bn %d, %d edges. %d in all_edges" % (
            bn, len(self.edges), len(self.all_edges)))
        print("mx_depth_seen = %d" % mx_depth_seen)
        self.end_bin(msm_id, bn)  # For last bin

        # Delete subroots with max_icount < mn_allowed_trpkts
        if self.mn_allowed_trpkts != 0:
            subrs_to_delete = []
            for sr_key in self.sub_root_icounts.keys():
                sr_icounts = np.array(self.sub_root_icounts[sr_key])
                mx_icount = np.max(sr_icounts)
                if mx_icount < self.mn_allowed_trpkts:
                    subrs_to_delete.append(sr_key)
            print("About to delete %d subroots with max_icount < %d" % (
                len(subrs_to_delete), self.mn_allowed_trpkts))
            for sr_key in subrs_to_delete:
                self.sub_root_icounts.pop(sr_key)

        f.close()
        #info_f.write("End (MxDepth %d)\n" % mx_depth_seen)
        print("EOF reached")

        #for n,sr_key in enumerate(self.sub_roots):
        #    sr = self.sub_roots[sr_key]
        #    print("%d: %s" % str(sr))

    def print_nparray(self, f, hdr, npa):
        f.write(hdr+"\n")
        n_lines = (len(npa)+9) // 10
        for n in range(0,n_lines):
            fn = n*10;  ln = n*10 + 10
            if ln > len(npa):
                ln = len(npa)
            for n in range(fn,ln):
                f.write("%8d" % n)
            f.write("\n")
            for n in range(fn,ln):
                f.write("%8d" % int(npa[n]))
            f.write("\n\n")
            f.flush()

    def asn_edges(self):  # Count numbers of Same- and Inter- ASN edges
                          #   for cum-edge-presence-v timebins.py  <<<<
        #print("len(all_edges_ = %d" % len(self.all_edges))
        for ek in self.all_edges:
            e = self.all_edges[ek]
            present = np.not_equal(e.icounts, 0).astype(int)
            n_ones = np.count_nonzero(present)  # Nbr of bins present
            if e.inter_as:
                self.inter_counts[n_ones] += 1
            else:
                self.same_counts[n_ones] += 1
        #tot_inter = np.sum(self.inter_counts)
        #tot_same = np.sum(self.same_counts)
        #print("tot_same=%d, tot_inter=%d, total=%d" % (
        #    tot_same, tot_inter, tot_same+tot_inter))
        return self.same_counts, self.inter_counts
                       
    def count_edges(self):  # Count edges in all_bins
        for ek in self.all_edges:
            e = self.all_edges[ek]
            ec = np.array(e.icounts)
            present = np.not_equal(e.icounts, 0).astype(int)
            n_ones = np.count_nonzero(present)  # Nbr of bins present
            self.p_counts[n_ones] += 1
        return self.p_counts
                       
    def gstat_val(self, reqd_stat):
        if not reqd_stat in self.stats:
            print("Statistic %s not known in GraphInfo" % reqd_stat)
            return False
        return self_stats[reqd_stat]

    def acor(self, y):  # https://stackoverflow.com/questions/643699/how-can-i-use-numpy-correlate-to-do-autocorrelation
        yunbiased = y-np.mean(y)
        ynorm = np.sum(yunbiased**2)
        acor = np.correlate(yunbiased, yunbiased, "same")/ynorm
        howmany = int(len(acor)/2)
        return acor[howmany:]  # use only second half

    def check_icounts(self, n):
        # look for big changes in icount between bins
        av_icount = np.mean(n.icounts)
        if av_icount >= 27:
            diff_a = np.insert(np.diff(n.icounts), 0, 0)
            ada = np.absolute(diff_a)
            big_diff = np.where(ada >= 0.1*av_icount, n.icounts, 0)
            if np.count_nonzero(big_diff) != 0:                
                print("node %s: av %.2f\ndiff %s" % (
                    n.name, av_icount, diff_a))
                print("icounts %s" % n.icounts)
                print("diff_a %s" % diff_a)

    def check_sna_len(self, n):
        # Look for big changes in len(sna)
        av_sna_len = np.mean(n.sna_len)
        if av_sna_len >= 5:
            diff_a = np.insert(np.diff(n.sna_len), 0, 0)
            ada = np.absolute(diff_a)
            big_diff = np.where(ada >= 0.1*av_sna_len, n.sna_len, 0)
            if np.count_nonzero(big_diff) != 0:                
                print("node %s: av %.2f\ndiff %s" % (
                    n.name, av_sna_len, diff_a))
                print("sna_len %s" % n.sna_len)
                print("diff_a %s" % diff_a)

    def compute_node_stats(self, nodes, mn_trpkts):
        # Returns array of NodeInfo objects <<<
        keep_nodes = [];  n_stable = 0  # stable = present in all bins
        for nk in nodes:
            n = nodes[nk]
            #print("@@@ nk %s, %s (%s)" % (nk, n, type(n)))
            n.icounts = np.where(n.icounts < mn_trpkts, 0, n.icounts)
            n.present = np.not_equal(n.icounts, 0).astype(int)
            n.n_ones = np.count_nonzero(n.icounts)
            if n.n_ones == 0:
                continue  #  All icounts < mn_trpkts
            if n.n_ones == n.n_bins:
                n_stable += 1
                continue  # Not interested in stable nodes
            self.p_counts[n.n_ones] += 1  # GI attribute for Edges
            n.n_zeroes = n.n_bins-n.n_ones
            zra = zero_runs(n.icounts)
            zra_len = zra[:,1]-zra[:,0]  # Run-of-zeroes lengths
            n.n_zruns = 0;  n.mx_zrun = 0
            if len(zra_len) != 0:
                n.n_zruns = len(zra_len)
                n.mx_zrun = zra_len.max()
            ora = one_runs(n.icounts)
            ora_len = ora[:,1]-ora[:,0]  # Run-of-ones lengths
            n.n_oruns = 0;  n.mx_orun = 0
            if len(ora_len) != 0:
                n.n_oruns = len(ora_len)
                n.mx_orun = ora_len.max()
            n.av_icount = 0
            if n.n_ones != 0:
                n.av_icount = np.average(
                    n.icounts, axis=0, weights=n.icounts.astype(bool))
            n.pv = n.present
            keep_nodes.append(n)
        return keep_nodes, n_stable

    def examine_nodes(self, mn_trpkts):
        nodes, n_stable = self.compute_node_stats(self.all_nodes, mn_trpkts)
        self.all_nodes = nodes
        print("$exn %d nodes in self.all_nodes, %d were stable" % (
            len(nodes), n_stable))
        d_nodes, d_stable = self.compute_node_stats(
            self.distal_nodes, mn_trpkts)
        print("$exd %d d_nodes in self.all_nodes, %d were stable" % (
            len(d_nodes), d_stable))
        distals = []
        for n in d_nodes:
            if n.n_zeroes >= 2 and n.n_ones > 8:
                distals.append(n)
        print("$exd: %d distals with >=2 zeroes and >8 ones" % len(distals))
        self.distal_nodes = distals
        return n_stable

    def examine_edges(self, mn_trpkts):
        n_stable = 0
        for ek in self.all_edges:
            e = self.all_edges[ek]
            #if not e.inter_as:  # Only interested in Inter-AS edges
            #    continue
            e.icounts = np.where(e.icounts < mn_trpkts, 0, e.icounts) 
            self.n_ones = np.count_nonzero(e.icounts)  # Nbr of bins present
            e.present = np.not_equal(e.icounts, 0).astype(int)
            e.n_ones = np.count_nonzero(e.present)  # Nbr of bins present
            self.p_counts[e.n_ones] += 1
            e.n_zeroes = self.n_bins-e.n_ones
            e.zra = zero_runs(e.icounts)
            e.zra_len = e.zra[:,1]-e.zra[:,0]  # Run-of-zeroes lengths
            e.n_zruns = len(e.zra_len)
            e.mx_zrun = 0
            if len(e.zra_len) != 0:
                e.mx_zrun = e.zra_len.max()
            ora = one_runs(e.icounts)
            ora_len = ora[:,1]-ora[:,0]  # Run-of-ones lengths
            e.n_oruns = len(ora_len)
            e.mx_orun = 0
            if len(ora_len) != 0:
                e.mx_orun = ora_len.max()
            if e.n_ones == e.n_bins:
                n_stable += 1
            if e.n_ones != 0:
                e.av_icount = np.average(
                    e.icounts, axis=0, weights=e.icounts.astype(bool))
                    # For type bool, False = 0, True = non-zero
                    # weights (above) treats bools as ints

            if not ek in self.all_edges:
                self.all_edges[ek] = e

            e.pv = e.present  # For diff()
            #s = int(ipaddress.IPv4Address(e.n_from))  # For diff2 and 3
            #d = int(ipaddress.IPv4Address(e.n_to))
            #na = np.array( [s,d] )
            #e.pv = np.hstack( [e.present, na] )  # Keep presence vector first

        print("examine_edges: n_stable = %d" % n_stable)
        return n_stable
        
    def examine_subroots(self):  # For presence-bars-v-timebins.py
        self.sub_roots = []
        for sr_key in self.sub_root_icounts.keys():
            #print("subroot %s\n counts %s\npresence %s" % (sr_key,
            #    self.sub_root_presence[sr_key], self.sub_root_icounts[sr_key]))
            self.sub_roots.append( 
                SubRoot(sr_key, self.sub_root_icounts[sr_key]) )
                # All sub_root stats are computed by SubRoot()

    def classify_nodes(self):
        interest0 = []
        print("classify_nodes: %d distal nodes" % len(self.distal_nodes))
        #for j,n in enumerate(self.distal_nodes):
        #    print("%3d %s  (%s)" % (j, n, type(n)))

        for n in self.all_nodes:  # i.e. all those we can classify
            print("&&& n = %s (%s)" % (n, type(n)))
            #print("n.name %s, n_zruns %d, av_icount %d: %s" % (
            #    n.name, n.n_zruns, n.av_icount, n.icounts))
            #if n.n_ones >= c.n_bins/4:
            if n.n_ones >= c.n_bins/4 and n.n_zruns <= 5:
                nzr = np.array( [n.n_zruns] )
                n.pv = np.hstack( [n.present, nzr] )  
                    # Keep presence vector first
                interest0.append(n)
        return interest0

    def classify_edges(self):
        interest0 = []
        n_seldom = n_lower = n_interesting = n_upper = n_mostly = 0
        n_inter_AS = 0
        for e_key in self.all_edges:  # i.e. all those we could classify
            e = self.all_edges[e_key]
            if e.inter_as:
                n_inter_AS += 1
            #    continue
            ones_c = e.n_ones
            if ones_c < 6:
                n_seldom += 1;  continue  # Not interesting
            elif ones_c < 22:
                n_lower += 1
            elif ones_c < 26:
                n_interesting += 1
            elif ones_c < 42:
                n_upper += 1
            else:
                n_mostly += 1

            # Filter 1: same-ASN switches, uses edge_dest()
            #if e.mx_zrun > 10 and e.mx_orun > 10 and not e.inter_as:
            #     interest0.append(e)

            # Filter 2: ditto, but allow inter-as edges
            #if e.mx_zrun > 10 and e.mx_orun > 10:
            #     interest0.append(e)

            # Filter 3: allow 1 or 2 oruns or zruns
            #if e.mx_zrun > 8 and e.mx_orun > 8 and \
            #        e.n_zruns == 1 and e.n_oruns <= 2:
            #    interest0.append(e)

            if e.n_zruns >= 1:
                interest0.append(e)

        n_tot = n_seldom+n_lower+n_interesting+n_upper+n_mostly 
        print("%d edges classified" % n_tot)
        print("  %d seldom, %d lower, %d interesting, %d upper, %d mostly" % (
            n_seldom, n_lower, n_interesting, n_upper, n_mostly))
        return interest0

    def classify_variances(self):
        v_edges = []
        n = 0
        for e_key in self.all_edges:  # i.e. all those we could classify
            e = self.all_edges[e_key]
            nzeros = np.count_nonzero(e.icounts)
            nz_counts = e.icounts[e.icounts != 0]
            if len(nz_counts) == 0:
                continue  # Ignore completely unused edge
            mean = np.divide(  # Mean of non-zero elements
                np.sum(nz_counts),len(nz_counts))
            #print("len(nz_counts) %d" % len(nz_counts))
            #print("inf check mean: %s" % np.isfinite(mean).all())
            iqr = scipy.stats.iqr(nz_counts)
            ratio = iqr/mean
            #if nzeros >= 40 and mean >= 100.0 and ratio >= 0.2:
            if nzeros >= 30 and mean >= 50.0 and ratio >= 0.1:
                e.av_icount = np.average(e.icounts,
                    axis=0, weights=e.icounts.astype(bool))
                #np.set_printoptions(precision=3)  # .3f in %s format :-)
                #print("e.av_count = %s" % e.av_icount)
 
                # this_ic = e.icounts()
                last_ic = np.insert(e.icounts, 0, 0)
                pair_avs = np.add(e.icounts, last_ic[:-1])/2
                diffs = np.subtract(e.icounts, last_ic[:-1])
                r_bcps = np.divide(diffs, pair_avs)*100  # May contain nan's !!
                e.bcps = np.nan_to_num(r_bcps)  # np v 1.16 has no nan=0.0 !!!!
                #print("bcps     %s" % e.bcps)

                #normal = Normalize(np.min(e.diff), np.max(e.diff))
                #e.pv = normal(e.dif)
                e.pv = e.bcps
                #print("e.pv = %s" % e.pv)
                v_edges.append(e)
                n += 1
                print("%3d:  mean %.3f, iqr %.3f: ratio %.3f" % (
                    n, mean, iqr, ratio))
        return v_edges
 
    def classify_subroots(self, mn_trpkts):
        interesting_subroots = []
        for n,sr in enumerate(self.sub_roots):
            #sr = self.sub_roots[sr_key]
            #print("%d: max_icount %d, %s" % (n, sr.max_icount, sr))
            if sr.nz_counts >= c.n_bins/4 and \
                    (sr.av_icount >= mn_trpkts or \
                     sr.max_icount >= mn_trpkts):
                #print("Keep subroot %d: %s" % (n, str(sr)))
                interesting_subroots.append(sr)
        return interesting_subroots


    def print_plist(self, msg, p_l):
        print("   %s" % msg)
        for p in p_l:
            print("      %s" % p)

    def build_paths(self, e_list, bn):
        #self.print_plist("e_list", e_list)
        if len(e_list) == 0:
            return False
        p_list = [Path(e_list[0], bn)]
        ##self.print_plist("P:", p_list)
        if len(e_list) == 1:
            return p_list
        for e in range(1,len(e_list)):
            edge = e_list[e]
            ##print("e=%d, edge %s" % (e, edge))
            added = False
            for p in range(0,len(p_list)):
                if p_list[p].add_edge(edge, bn):
                    added = True
                    #print("p=%d, edge %s added" % (p, edge))
                    ##self.print_plist("Q:", p_list)
                    break
            if not added:
                p_list.append(Path(edge, bn))
        #self.print_plist("p_list", p_list)
        return p_list

    def filter_paths(self, p_list):
        return p_list
        #pk_list = []
        #for p in p_list:
        #    if p.keep():
        #        pk_list.append(p)
        #return pk_list

    def add_to_paths(self, pl, bn, a_d):
        for p in pl:
            sp = p.key
            if sp in str(self.paths):
                self.paths[sp].append( (bn, a_d) )
            else:
                self.paths[sp] = [ (bn, a_d) ]

    def print_paths(self):
        for sp in self.paths:
            #print("%s:" % sp.replace(' ', ' -> '))
            os = '';  p = self.paths[sp]
            for c in p:
                bn, ch = c
                os += "%d %s, " % (bn, ch)
            #print("   %s" % os[0:-2])
