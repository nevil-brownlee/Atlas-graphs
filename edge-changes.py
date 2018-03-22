# 1427, Tue 1 Aug 2017 (NZST)
#
# graph-changes.py: get info about ASNs (or nodes) over timebins
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own numpy (numpypy)

import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list, dendrogram
#from scipy.cluster.hierarchy import optimal_leaf_ordering
import matplotlib.pyplot as pplt

import math, sys

import config as c
c.set_pp(False, c.msm_id)  # Set prune parameters
 
# Extra command-line parameters (after those parsed by getparamas.py):
#
#   +a  plot edges-per-asn  (requires --full_graphs True)
#   +p    for percentage distributions
#   +e  plot edge presence for different kinds of 'interesting' edges
#                           (full_graphs may be True or False)

e_presence = e_per_asn = pc_graph = False
if c.rem_cpx != 0:
    e_presence  = '+e' in sys.argv  # Plot edge changes
    e_per_asn   = '+a' in sys.argv  # Plot inter- and same-ASN edge cum distribs
    pc_graph    = '+p' in sys.argv  # Use percentages in distributions
print("e_per_asn %s, e_presence %s, pc_graph %s" % (
    e_per_asn, e_presence, pc_graph))
if not (e_per_asn or e_presence or pc_graph):
    print("No options specified:")
    print("  +e  plot edge presence graphs for 'interesting' edges")
    print("  +a  plot inter- and same-ASN edge cumulative distribs")
    print("  +p    to use percentages for the distributions")
    exit()

n_bins = c.n_bins*c.n_days
node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}

asn_fn = c.asn_dests_fn(c.msm_id)  # Read ASN -> prefix mapping from file
print("asn file = %s <<<<<<" % asn_fn)
asnf = open(asn_fn, "r", encoding='utf-8')
for line in asnf:
    node, asn = line.strip().split()
    node_dir[node] = asn
#    print("node_dir key %s, val %s" % (node, node_dir[node]))

class NodeInfo:  # Get node information for BinGraphs
    tg       = 0;   tr = 1;    ts = 2;   tb = 3;  tf = 4;  tu = 5
    t_str = ['gone', 'root',' sub-root', 'branch', 'leaf', 'unknown <<<']

    def update(self, bn, icount, fails, roots, sna):  # Sets .kind for each bin
        #print("-- %s: %s" % (self.name, sna))
        self.icount[bn] = icount;  self.fails[bn] = fails
        self.present[bn] = 1
        
        if self.root:
            kind = self.tr  # Root
        elif icount == 0:
            kind = self.tf  # Leaf
        elif fails == -1:  # Version 1 graphs file, i.e. full_graphs
            if self.name in roots:
                kind = self.ts  # Sub-root
            else:
                kind = self.tb  # Branch
        else:  # Version 2 graphs file, i.e. ASN graphs
            if fails == 0:
                kind = self.tb  # Branch
            else:
                kind = self.ts  # Sub-root
        self.kind[bn] = kind
        ##self.counts[kind] += 1

    def __init__(self, bn, dest, name, icount, fails, roots, sna):
        #print("bin %d, roots = %s" % (bn, roots))
        self.name = name;  self.root = name == dest
        ##print(">> %s  %s  %s" % (name, dest, self.root))
        self.present = [0]*n_bins;  self.kind = [self.tg]*n_bins
        self.icount = [0]*n_bins;  self.fails = [0]*n_bins
        ##self.counts = [0]*len(self.t_str)
        self.update(bn, icount, fails, roots, sna)  # 6939
        
    def __str__(self):
        there = ''
        for bn in range(0, n_bins):  # Make string of 1s and 0s
            there += str(self.present[bn])
        return "%20s: %s" % (self.name, there)

    def save_info(self, msm_id, av_icount, pv,ps, zra):  # Present (binary) string
        # pv = 'present' vector, ps = string version of pv
        self.msm_id = msm_id;  self.av_icount = av_icount
        self.pv = pv;  self.ps = ps
        self.zra = zra

    def distance(self, n2):
        return np.sum(self.pv == n2.pv)

class Edge:
    def node_asn(self, prefix):
        if prefix in node_dir:
            return node_dir[prefix]
        else:
            if not prefix in no_asn_nodes:
                no_asn_nodes[prefix] = True
            return "unknown"
        
    def __init__(self, src, dest):
        self.n_from = src;  self.n_to = dest  # Node names
        self.icount = [0]*n_bins;  self.av_icount = 0
        self.msm_id = self.pv = self.ps = self.zra = None
        if c.full_graphs:
            self.asn_from = self.node_asn(src)
            self.asn_to = self.node_asn(dest)
        else:  # ASN graphs
            self.asn_from = src;  self.asn_to = dest
        self.last_nb = 0
        self.inter_as = self.asn_from != self.asn_to

    def set_icount(self, nb, count):
        self.icount[nb] = count
        self.last_nb = nb
        
    def __str__(self):
        if not c.full_graphs:
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

class Path:  # list of Edges
    def __init__(self, edge, bn):
        self.edges = [edge]
        self.mx_icount = [0]*n_bins
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


class GraphInfo:
    def __init__(self, msm_id, all_edges):
        self.msm_id = msm_id
        self.all_edges = all_edges
        self.nodes = {}  # Dictionary, all nodes seen in DestGraph
        self.edges = {}  # Ditto for edges
        self.paths = {}  # Ditto for paths
        self.p_counts = np.zeros(n_bins+1)  # bins 1..336
        self.same_counts = np.zeros(n_bins+1)  # In same ASN
        self.inter_counts = np.zeros(n_bins+1)  # Between ASNs

        fn = c.msm_graphs_fn(msm_id)  # Full- or asn- filename
        print(" >>> %d: %s" % (msm_id, fn))
        f = open(fn, 'r')
        gf_version = 1
        bn = 0
        for line in f:
            la = line.strip().split(maxsplit=1)
            if la[0] == "BinGraph":  # Start of a timebin
                bv = la[1].rsplit(maxsplit=1)
                bn = int(bv[1])  # Bin nbr
                #n_traces, n_succ_traces, n_dup_traces, \
                #    t_addrs, t_hops, t_hops_deleted, bin_nbr = la[1:]
                roots_line = f.readline()
                rla = roots_line.strip().split()
                mx_edges = int(rla.pop(0))
            elif la[0] == "Node":
                nv = la[1].split()
                name = nv[0];  subtree = int(nv[1]);  icount = int(nv[2])
                # 'subtree' as found when building the graph
                fails = -1  # Not in v1 graphs file
                if gf_version != 1:
                    fails = int(nv[3])
                s_nodes_line = f.readline()  # s_nodes line
                sna = s_nodes_line.split()  # name, in_count pairs
                
                if name in self.nodes:  # Get info about nodes
                    self.nodes[name].update(bn, icount, fails, rla, sna)
                else:
                    self.nodes[name] = \
                        NodeInfo(bn, dest, name, icount, fails, rla, sna)

                for j in range(0, int(len(sna)), 2):  # Get info about edges
                    src = sna[j];  count = int(sna[j+1])
                    e_key = "%s %s" % (src, name)
                    if not e_key in self.edges:
                        self.edges[e_key] = Edge(src, name)
                    self.edges[e_key].set_icount(bn, count)
                if name in self.nodes:
                    self.nodes[name].update(bn, icount, fails, rla, sna)
                else:
                    self.nodes[name] = \
                        NodeInfo(bn, dest, name, icount, fails, rla, sna)
                
            elif la[0] == "DestGraphs":  # File header record
                nv = la[1].split()  # One or more white-space chars
                dest = nv[1]
                if len(nv) > 7:
                    gf_version = 2
        f.close()

        #for nk in self.nodes:
        #    print(self.nodes[nk])
        print("EOF reached")

    def zero_runs(self, a):
        # https://stackoverflow.com/questions/24885092/finding-the-consecutive-zeros-in-a-numpy-array
        iszero = np.concatenate(([0], np.equal(a, 0).view(np.int8), [0]))
        absdiff = np.abs(np.diff(iszero))  # 1 in element before change
        # Runs start and end where absdiff is 1.
        ranges = np.where(absdiff == 1)[0].reshape(-1, 2)  # Ranges of 0s
        return ranges

    def one_runs(self, a):
        w = np.logical_not(np.equal(a, 0))  # 1s for each 0 in a
        isone = np.concatenate(([0], w.view(np.int8), [0]))
        absdiff = np.abs(np.diff(isone))  # 1 in position before change
        return  np.where(absdiff == 1)[0].reshape(-1, 2)  # Ranges of 1s

    def asn_edges(self):  # Count Same- and Inter- ASN edges
        for ek in self.edges:
            e = self.edges[ek]
            present = np.not_equal(e.icount, 0).astype(int)
            n_ones = np.count_nonzero(present)  # Nbr of bins present
            if e.inter_as:
                self.inter_counts[n_ones] += 1
            else:
                self.same_counts[n_ones] += 1
        print("asn_edges(): same_counts = %d, inter_counts = %d + + +" %  (
            len(self.same_counts), len(self.inter_counts)))
        return (self.same_counts, self.inter_counts)
                       
    def acor(self, y):  # https://stackoverflow.com/questions/643699/how-can-i-use-numpy-correlate-to-do-autocorrelation
        yunbiased = y-np.mean(y)
        ynorm = np.sum(yunbiased**2)
        acor = np.correlate(yunbiased, yunbiased, "same")/ynorm
        return acor[len(acor)/2:]  # use only second half
        
    def examine_edges(self):
        n_stable = same_counts = inter_counts = 0
        for ek in self.edges:
            e = self.edges[ek]
            if not e.inter_as:  # Only interested in Inter-AS edges
                continue
            ec = np.array(e.icount)
            e.present = np.not_equal(e.icount, 0).astype(int)
            e.pv = e.present  # <link<<<<<<<<<<<< for linkage()
            e.n_ones = np.count_nonzero(e.present)  # Nbr of bins present
            self.p_counts[e.n_ones] += 1
            e.n_zeroes = n_bins-e.n_ones
            e.zra = self.zero_runs(ec)
            e.zra_len = e.zra[:,1]-e.zra[:,0]  # Run-of-zeroes lengths
            e.n_zruns = len(e.zra_len)
            e.mx_zrun = 0
            if len(e.zra_len) != 0:
                e.mx_zrun = e.zra_len.max()
            else:
                e.mx_zrun = np.zeros(1)
            ora = self.one_runs(ec)
            e.ora_len = ora[:,1]-ora[:,0]  # Run-of-ones lengths
            e.n_oruns = len(e.ora_len)
            if len(e.ora_len) != 0:
                e.mx_orun = e.ora_len.max()
            else:
                e.mx_zrun = np.zeros(1)

            if e.n_ones == n_bins:
                n_stable += 1
                continue  # Also not interesting                
            #e.kind = self.ekind(e.n_ones, e.n_zeroes, 
            #    len(ora), len(e.zra), e.mx_orun, e.mx_zrun)
            elif e.inter_as:
                inter_counts += 1
            else:
                same_counts += 1

            psl = np.apply_along_axis(  #  Apply along axis 0 of present
                lambda p: [str(i) for i in p], 0, e.present)
            e.ps = ''.join([''.join(s) for s in psl])
            #print("   ps = >%s<" % ps)
            #print("n_ones=%d, mx_zrun=%d" % (n_ones, mx_zrun))
            #print()

            e.av_icount = np.average(ec, axis=0, weights=ec.astype(bool))
                # For type bool, False = 0, True = 1
                # weights (above) treats bools as ints
            #print(">>> %s" % (ec.astype(bool)).astype(int))

            self.all_edges.append(e)  # Save the non-stable inter-AS edges

        print("examine_edges: n_stable = %d" % n_stable)
        return n_stable
                                       
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

#    def edge_key(self, e):  # sorted passes the dict"%d %d %s %e" % (e.msm_id, e.kind, e,ps, e)ionary key!
#        #print("edge_key: %s" % str(e))
#        #return e.av_icount
#        ###print("%s %s %s %s %s %s" % (msm_id, e.kind, e.n_ones, e.mx_zrun, e.ps, e))      
#        return "%d %s %d %d %s" % (msm_id, e.ps, e.n_ones, e.mx_zrun, e)

    def classify_edges(self):
        seldom = [];   recurrent = [];   frequent = []
        mostly = [];   interest0 = [];   interest1 = [];      

        #t_p = {  # Parameters for classifying 336 bins
        #    'n_ones': 24, 'mx_orun': 12,
        #    'n_oruns': 2, 'n_zruns': 2,
        #    'n_ones_i1': 96, 'n_ones_seldom': 48, 'n_ones_mostly':240,
        #    }
        sf = n_bins/336.0
        print("n_bins = %d, sf = %.3f" % (n_bins, sf))
        t_p = {  # Parameters for type testing for 336 bins
            'n_ones': int(24*sf), 'mx_orun': int(12*sf),
            'n_oruns': 2, 'n_zruns': 2,
            'n_ones_i1': int(72*sf),
            'n_ones_seldom': int(48*sf), 'n_ones_mostly':int(240*sf),
            }
        print("ones: i1=%d, seldom=%d, mostly=%d" % (t_p['n_ones_i1'],
            t_p['n_ones_seldom'], t_p['n_ones_mostly']))
        ix = -1
        #for e in sorted(self.all_edges, key=self.edge_key, reverse=True):
    ## 1        print("%d %d %3d %3d %s %s" % (msm_id, e.kind, e.n_ones, e.mx_zrun,  e.ps, e))
        for e in self.all_edges:  # i.e. all those we could classify
            done = False
            if e.mx_orun <= t_p['mx_orun'] and \
                   e.n_ones >= t_p['n_ones']:
                ac = self.acor(e.present)
                if ac[1:24].max() >= 0.1:
                    recurrent.append(e)
                    done = True
            if not done:
                if e.n_oruns <= t_p['n_oruns'] and \
                        e.n_zruns <= t_p['n_zruns']:
                    if e.n_ones >= t_p['n_ones_i1']:  # 2*48
                        interest1.append(e)
                        done = True
                    else:
                        interest0.append(e)
                        done = True
            if not done:
                if e.n_ones <= t_p['n_ones_seldom']:
                    seldom.append(e)
                    done = True
            if not done:
                if e.n_ones > t_p['n_ones_mostly']:
                    mostly.append(e)
                    done = True
            if not done:
                frequent.append(e)

        n_seldom = len(seldom);        n_recurrent = len(recurrent)
        n_interest0 = len(interest0);  n_interest1 = len(interest1)
        n_frequent = len(frequent);    n_mostly = len(mostly)
        total = n_seldom+n_recurrent+n_interest0+n_interest1+n_frequent+n_mostly
        print("Counts: seldom=%d, recurrent=%d, interest0=%d, interest1=%d, frequent=%d, mostly=%d, total=%d" % (
            n_seldom, n_recurrent, n_interest0, n_interest1,
            n_frequent, n_mostly, total))
        return (interest1, recurrent, total)

    def add_to_paths(self, pl, bn, a_d):
        for p in pl:
            sp = p.key
            if sp in str(self.paths):
                self.paths[sp].append( (bn, a_d) )
            else:
                self.paths[sp] = [ (bn, a_d) ]

    def print_paths(self):
        for sp in self.paths:

            os = '';  p = self.paths[sp]
            for c in p:
                bn, ch = c
                os += "%d %s, " % (bn, ch)
            #print("   %s" % os[0:-2])
    

def plot_asn_counts(pca, inter_ca, ids):  # Plot counts (nbr of times pc[x] was seen)
    #ymax = {5017:80, 5005:145, 5016:100, 5004:920, 5006:1270, 5015:1030}  # y axis upper limits for PAM paper
    pcc = [];  inter_cc = []
    for pc in pca:  # Same ASN
        cc = np.cumsum(pc)  # Cumulative counts
        if pc_graph:
            cc = cc*(100.0/cc[-1])
        pcc.append(cc)
        ymax = cc.max()
        print("cc = %s, cc_max = %d" % (cc, ymax))
    for ic in inter_ca:  # Between ASNs
        icc = np.cumsum(ic)  # Cumulative counhts
        if pc_graph:
            icc = icc*(100.0/icc[-1])
        inter_cc.append(icc)
        iccmax = icc.max()
        print("icc = %s, icc_max = %d" % (icc, iccmax))
        if iccmax > ymax:
            ymax = iccmax
    if pc_graph:
        ymax += 2
    else:
        ymax += 20

    which = "counts"
    if pc_graph:
        which = "percent"
    if not c.full_graphs:
        title = "ASN graph: edge presence (%s)" % which
        pfn = "%/inter-asn-%s.svg" % (c.start_ymd, which)
    else:
        title = "Full graph: edge presence (%s)" % which
        pfn = "%s/inter-asn-full-%s.svg" % (c.start_ymd, which)

    if len(ids) == 1:
        rows = cols = 1;  lw = 0.2
        w = 3;  h = 3.4;  stp = 12;  tkp = 7;  tp = 12
    elif len(ids) <= 3:
        rows = 1;  cols = len(ids);  lw = 0.125
        w = 8;  h = 3.4;  stp = 12;  tkp = 7;  tp = 12
    else:
        rows = 2;  cols = int(len(ids)/2);  lw = 0.125
        w = 8;  h = 6;  stp = 12;  tkp = 7;  tp = 12
    fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches (?)
    if len(ids) <= 3:
        pplt.subplots_adjust(left=lw, bottom=0.135, right=None, top=0.9,
                             wspace=0.5, hspace=0.85)
    else:
        pplt.subplots_adjust(left=lw, bottom=0.07, right=None, top=0.95,
                             wspace=0.5, hspace=0.35)
    ##fig.suptitle(title, fontsize=18, horizontalalignment='center')
    #print("axes = %s, shape(axes) = %s" % (axes, np.shape(axes)))
    for f in range(rows*cols):
        msm_id = ids[f]
        msm_dest = c.msm_dests[msm_id]
        ls = "%d (%s)" % (msm_id, msm_dest[0])
        r = f/cols;  nc = f%cols
        print("%d: len(ids) = %d, f = %d, r=%d, nc=%d" % (
            msm_id, len(ids), f, r, nc))
        if len(ids) == 1:
            xy = axes
        elif len(ids) == 3:
            xy = axes[nc]
        else:
            xy = axes[r,nc]
        if n_bins == 336:  # 1 week
            xy.set_xlim(-5,340)  # x axis limits
            xy.set_xticks(range(0,8*48, 48))
            #for x in range(48, 336, 48):
            #    gx.append(x)
            lwidth = 0.4
        elif n_bins == 48:  # 1 day
            xy.set_xlim(-1,49)  # x axis limits
            xy.set_xticks(range(0,9*6, 6))
            #for x in range(6, 54, 6):
            #    gx.append(x)
            lwidth = 1.5
        xy.set_title(ls, fontsize=12)
        xy.set_ylabel("edges")
        xy.set_xlabel("timebins present")
        xy.tick_params(axis='x', labelsize=tkp)
        xy.tick_params(axis='y', labelsize=tkp)
        print("ymax = %s" % ymax)
        xy.set_ylim(-2,ymax)  # y axis limits
        if len(ids) != 1:
            x_vals = np.linspace(0,48,49)
            xy.plot(x_vals, pcc[f], label="Same ASN")  # <<<<<<<<<<<<
            print("  same AS: %s" % pcc[f])
            xy.plot(x_vals, inter_cc[f], label="Inter-ASN")
            print("  inter-AS: %s" % inter_cc[f])
        else:
            xy.plot(pcc[0], label="Same ASN")
            xy.plot(inter_cc[0], label="Inter-ASN")
            
        xy.legend(loc="upper left", title="Edge type", fontsize=5,
                  bbox_to_anchor=(0.03,0.99), prop={"size":7}, handlelength=1)
            # fontsize for labels, "size" for heading
        xy.grid()
    pplt.savefig(pfn)

def plot_edge_presence(pv_eca, group, first_ix, e_labels):  # List of edges to plot presence
    #n_edges = 40; w = 10;  h = 16;  stp = 9;  tkp = 8;  tp = 12
    n_edges = len(pv_eca); w = 10;  h = 16;  stp = 9;  tkp = 8;  tp = 12
    if len(pv_eca) <= 22:
        n_edges = len(pv_eca);  h = n_edges*0.43
    #n_edges = 6; w = 10;  h = 2.5;  stp = 9;  tkp = 8;  tp = 12
    print("n_bins=%d, n_edges=%d, group = %s\n" % (n_bins, n_edges, group))
    fig, xy = pplt.subplots(1,1, figsize=(w,h))  # Inches (?)
    msm_dest = c.msm_dests[c.msm_id]
    title = "'%s'  edges for %d (%s)" % (group, c.msm_id, msm_dest[0])
    fig.suptitle(title, fontsize=18, horizontalalignment='center')
    print("axes = %s, shape(axes) = %s" % (xy, np.shape(xy)))
    xv = np.concatenate(([0], np.cumsum(np.ones(n_bins-1))))
    xy.tick_params(axis='x', labelsize=tkp)
    gx = []
    if n_bins == 336:  # 1 week
        pplt.subplots_adjust(left=0.23, bottom=0.12, right=None, top=None,
                                 wspace=None, hspace=None)
        xy.set_xlim(-5,340)  # x axis limits
        xy.set_xticks(range(0,8*48, 48))
        for x in range(48, 336, 48):
            gx.append(x)
        lwidth = 0.4
    elif n_bins == 48:  # 1 day
        pplt.subplots_adjust(left=0.6, bottom=0.12, right=None, top=None,
                                 wspace=None, hspace=None)
        xy.set_xlim(-1,49)  # x axis limits
        xy.set_xticks(range(0,9*6, 6))
        for x in range(6, 54, 6):
            gx.append(x)
        lwidth = 1.5

    gy_min = np.ones(len(gx))*(-0.5)
    gy_max = np.ones(len(gx))*(n_edges*1.5)
    xy.set_ylim(-0.5,n_edges*1.5)  # y axis limits
    pplt.setp(xy.get_yticklabels(), visible=False)  # Hide tick labels
    xy.yaxis.set_tick_params(size=0) # Hide y ticks
    hy = []
    for f in range(n_edges):
        hy.append(f*1.5 + 0.5)
    hx_min = np.ones(len(hy))*(-5.0)
    hx_max = np.ones(len(hy))*340.0
    xy.hlines(hy, hx_min, hx_max, linewidth=0.2, color='black')
    xy.vlines(gx, gy_min, gy_max, linewidth=0.2, color='black')

    for f in range(n_edges):
        if first_ix+f >= len(pv_eca):
            break
        e = pv_eca[first_ix+f]
        offset = f*1.5
        ymin = np.ones(336)*offset
        ymax = np.add(e.present, offset)
        if not e_labels:            
            #nn = "%s -> %s  %5d pkts  %3d" % (
            #    e.asn_from, e.asn_to, e.av_icount, f)
            nn = "%s->%s   (%s->%s)  %5d pkts" % (
                e.asn_from, e.asn_to, e.n_from, e.n_to, e.av_icount)
        else:
            nn = e_labels[f]
        print("%s, %s->%s, first 0 at %d to %d" % (
            nn, e.n_from, e.n_to, e.zra[0,0], e.zra[0,1]))
        b_width = 0.1
        xy.vlines(xv, ymin, ymax, linewidth=lwidth, color='blue')
        xy.text(-12, offset+0.3, nn, fontsize=stp,
                horizontalalignment='right')  # Axis units

        #xy.legend(loc="upper left", title="Edge type", fontsize=5,
        #          bbox_to_anchor=(0.03,0.99), prop={"size":7}, handlelength=1)
        #    # fontsize for labels, "size" for heading
        #xy.grid()
    pfn = "%s/%d-%s-presence-%d.svg" % (
        c.start_ymd, c.msm_id, group, first_ix)
    pplt.savefig(pfn)
   
#  The code that looks for 'interesting' groups uses all_edges;
#    that's global above, and built by the NodeInfo class.

ids = [];  pca = [];  inter_ca = [];  all_edges = []
#for msm_id in [c.msm_id]:  #!! Kludge so we don't change indenting below!
#for msm_id in [5017, 5005, 5016, 5004, 5006, 5015]:

if e_per_asn:
    for msm_id in [5017, 5005, 5016]:
        msm_dest = c.msm_dests[msm_id][0]
        gf = GraphInfo(msm_id, all_edges)
    
        print("%d has %d nodes with no asn <--" % (msm_id, len(no_asn_nodes)))
        ids.append(msm_id)
        same_counts, inter_counts = gf.asn_edges()
        pca.append(same_counts);  inter_ca.append(inter_counts)
    plot_asn_counts(pca, inter_ca, ids)  # Inter- Same-AS Edge comparisons
    exit()

for msm_id in [5017, 5005, 5016]:
    msm_dest = c.msm_dests[msm_id][0]
    gf = GraphInfo(msm_id, all_edges)
    
    print("%d has %d nodes with no asn <--" % (msm_id, len(no_asn_nodes)))
    ids.append(msm_id)
    if e_per_asn:
        same_counts, inter_counts = gf.asn_edges()
        pca.append(same_counts);  inter_ca.append(inter_counts)
        plot_asn_counts(pca, inter_ca, ids)  # Inter- Same-AS Edge comparisons
        exit()
        
    def print_stats(e, ix, ac):
        av_orun = np.average(e.ora_len)
        av_zrun = np.average(e.zra_len)
        av_ms = av_orun/av_zrun
        print("%d: %d %d ones=%d, n_oruns=%d, n_zruns=%d, mx_orun=%d, mx_zrun=%d, av_orun=%.2f, av_zrun=%.2f, av_ms=%.2f\n%s" % (
            ix, msm_id, e.kind, e.n_ones, e.n_oruns, e.n_zruns, e.mx_orun, e.mx_zrun, av_orun, av_zrun, av_ms,
                e.ps))
        if ac:
            print("ac = %s" % gf.acor(e.present))

    n_stable = gf.examine_edges()  # Compute stats values for each Edge

    interest1, recurrent, total = gf.classify_edges()
        # Lists of edges
    n_unclassified = len(all_edges)-total
    if n_unclassified != 0:
        print("!!!!!! %d unclassified !!!!!!" % n_unclassified)            

    if len(all_edges) < 5:
        print("\nOnly %d edges were 'interesting' !!!" % len(all_edges))
        continue

    print("= = = = =")
    
    def plot_dendrogram(Z, eva_labels, group):
        pplt.figure(figsize=(6, 8))
        which = "%d (%s)" % (msm_id, c.msm_dests[msm_id][0])
        t = "RIPE Atlas Edges, single-link dendrogram for %s" % which
        pplt.title(t, fontsize=10)
        pplt.xlabel('distance')  #'log10(distance)')
        dn = dendrogram(
            Z,
            orientation='right',  # Root at the right
            #leaf_rotation=90.0,  # rotates the x axis labels
            labels=eva_labels,
            leaf_font_size=5.0,   # font size for the x axis labels
            distance_sort='ascending')
        ax = pplt.gca()
        pplt.tight_layout(w_pad=5.0)  # Width padding 5x font size
            # Only one plot, so h_pad (height padding) isn't used
        pfn = "%s/%d-dendro-%s.svg" % (c.start_ymd, msm_id, group)
        #pplt.show()
        pplt.savefig(pfn)

    def e_name(x):
        ix = int(x)
        return "<%d>" % ix
#        if ix > len(eva)-1:
#            return "<%d>" % ix
#        return eva_labels[ix]

#    def e_asns(x):
#        ix = int(x)
#        if ix > len(eva)-1:
#            return "<%d>" % ix
#        return eva_asns[ix]

#    def check_path(ea):
#        print("\n%d Group Edges:" % msm_id)
#        for j in range(len(ea)):
#            e = all_edges[ea[j]]
#            print("  %s  av icount %.2f" % (e, e.av_icount))

#    print("Starting linkage")
            
    e_info = []
    def ev_dist(pv1, pv2):  # Distance metric for clustering
        dist = np.sum(pv1 != pv2)  # Different
        return dist
        dist2 = np.sum(pv1 != np.logical_not(pv2))  # Present in gaps
        if dist2 < dist:
            return dist2
        return dist
        # Number of overlapping zrun/orun pairs
        #   This didn't work as well as above, sigh!
        #print("edges %d and %d:" % (int(pv1[0]), int(pv2[0])))
        e1 = e_info[int(pv1[0])];  e2 = e_info[int(pv2[0])]
        #print("  e1=%s, nzruns=%d\n  e2=%s, nzruns=%d" % (e1, e1.n_zruns, e2, e2.n_zruns))
        #print("  e1.zra=%s, e2.zra=%s" % (e1.zra, e2.zra))
        mx_olap = 0  # Olap zrun
        for r1 in range(0, e1.n_zruns):
            st1 = e1.zra[r1,0];  en1 = e1.zra[r1,1]
            for r2 in range(0, e2.n_zruns): 
                st2 = e2.zra[r2,0];  en2 = e2.zra[r2,1]
                olap = min(en1,en2)-max(st1,st2)
                if olap > mx_olap:
                    mx_olap = olap
        print("mx_olap: rows %d & %d = %d" % (int(pv1[0]),int(pv2[0]), mx_olap))
        return (n_bins-mx_olap) + dist*20

    def make_edges_list(edges, group):
        eva = []  # 2d array of observation vectors
#        eva_labels = []  # Labels for each edge
        eva_asns = []  # ASNs for each edge
        for j,e in enumerate(edges):
            #eva.append(e.present)  # Unsorted
            #da = np.concatenate(([e.n_zruns], e.present))
            da = np.concatenate(([j], e.present))
            e_info.append(e)
            #print("da   %s" % da)
            #print("j=%d, z_runs=%s" % (j, e.zra))
            

            eva.append(da)
#            eva_labels.append("%s -> %s" % (e.n_from, e.n_to))
            eva_asns.append("%s -> %s" % (e.asn_from, e.asn_to))
        Z = linkage(eva, method='single', metric=ev_dist)  #'euclidean')
        print("\neva has %d edges, there were %d iterations" % (
            len(eva), len(Z)))
#        for r in range(0, len(Z)):
#            print("r=%d, <%d,%d> %s + %s ==> %s,  dist %.3f, (row %d in Z matrix)" % (r, Z[r,0], Z[r,1],
#                    e_name(Z[r,0]), e_name(Z[r,1]), e_name(n+r), Z[r,2], Z[r,3]))
#            print("   ASNs  %s --> %s" % (e_asns(Z[r,0]), e_asns(Z[r,1])))

# Z[i, 0] and Z[i, 1] are combined to form cluster n + i.
# index less than n corresponds to one of the original observations.
# distance between clusters Z[i, 0] and Z[i, 1] is given by Z[i, 2]. 
# fourth value Z[i, 3] = number of original observations in the new cluster.
        n = len(eva)
        #for r in range(0, len(Z)):
        #    original = ''
        #    if r > n:
        #        original = '*'
        #    print("r=%d, <%d,%d>   dist %.3f, (%d original observations) %s" % (
        #        r, Z[r,0], Z[r,1],
        #        Z[r,2], Z[r,3], original))
        #dendro_order = leaves_list(Z)
        #print("DO = %s" % dendro_order)
        diff_order = []
        for j in range(len(eva)-1):
            e0 = int(Z[j,0]);   e1 = int(Z[j,1])
            if e0 < n and e0 not in diff_order:
                diff_order.append(e0)
            if e1 < n and not e1 in diff_order:
                diff_order.append(e1)
        print("diff_order=%s, len(diff_order)=%d" % (
            diff_order, len(diff_order)))
        pv_rec_d = []
        for j in range(0,len(diff_order)):
            this_ix = diff_order[j]
            pv_rec_d.append(edges[this_ix])
        return pv_rec_d

    if e_presence:
        edges = make_edges_list(interest1, "interest1")
        plot_edge_presence(edges, "interest1", 0, None)
        edges = make_edges_list(recurrent, "recurrent")
        plot_edge_presence(edges, "recurrent", 0, None)
    
    ## https://docs.scipy.org/doc/scipy/reference/cluster.hierarchy.html
    
exit()  #  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

if inter_asn:
    pass
     #plot_asn_counts(pca, inter_ca, ids)  # Inter- Same-AS Edge comparisons
elif not dendro:
    plot_p_counts(pca, ids)  # Edge Presence CDF plots
