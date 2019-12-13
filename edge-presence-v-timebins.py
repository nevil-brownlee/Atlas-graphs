# 1802, Thu 1 Mar 2018 (NZDT)
# 1427, Tue 1 Aug 2017 (NZST)
#
# edge-presence-v-timebins.py: get info about ASNs (or nodes) over timebins
#
# Copyright 2018, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
import matplotlib.pyplot as pplt
from matplotlib import patches

import math, datetime

import config as c
c.set_pp(False, c.msm_id)  # Work on graphs-* file
 
#n_bins = 48  # 1 day
#n_bins = 48*3  # 3 days
n_bins = c.n_bins*c.n_days  # 1 week
print("$$$ n_bins = %d" % n_bins)

pc_graph = False  #True   # Convert edge counts to % of all edges
#dendro = False
inter_asn = True

what_to_do = 3  # was 4 for node-changes

if what_to_do == 1:  # Full-graph presence CDF for all msm_ids
    asn_graph = False;  inter_asn = False;  dendro = False
elif what_to_do == 2:  # ASN-graph presence CDF for all msm_ids
    asn_graph = True;  inter_asn = False;  dendro = False
elif what_to_do == 3:  # Inter- and Same- ASN presence CDFs for all msm_ids
    asn_graph = False;  inter_asn = True;  dendro = False
elif what_to_do == 4:  # Taxonomy of ASN edge presence
    asn_graph = False;  inter_asn = True;  dendro = True
elif what_to_do == 5:  # Taxonomy of all edge presence
    asn_graph = False;  inter_asn = False;  dendro = True
print("what_to_do %d, pc_graph %s, asn_graph %s, inter_asn %s" % (
    what_to_do, pc_graph, asn_graph, inter_asn))

node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}
##if not c.full_graphs:  # Read ASN -> prefix mapping from file
if c.full_graphs:  # Read prefix -> ASN mapping from file
    for msm_id in c.msm_nbrs:
        asn_fn = c.asn_dests_fn(msm_id)
        print("asn file = %s <<<<<<" % asn_fn)
        asnf = open(asn_fn, "r", encoding='utf-8')
        for line in asnf:
            node, asn = line.strip().split()
            node_dir[node] = asn
            #print("node_dir key %s, val %s" % (node, node_dir[node]))

class Edge:
    def __init__(self, src, dest, node_dir):
        self.node_dir = node_dir
        self.n_from = src;  self.n_to = dest  # Node names
        self.icount = [0]*n_bins;  self.av_icount = 0
        self.msm_id = self.pv = self.ps = self.zra = None
        if c.full_graphs:
            self.asn_from = self.node_asn(src)
            self.asn_to = self.node_asn(dest)
        else:
            self.asn_from = src;  self.asn_to = dest
        self.last_nb = 0
        self.inter_as = self.asn_from != self.asn_to
        #print("Edge.init(): asn_from = %s, asn_to = %s" % (self.asn_from, self.asn_to))

    def set_icount(self, nb, count):
        self.icount[nb] = count
        self.last_nb = nb
        
    def __str__(self):
        if asn_graph:
            return "%s --%.2f--> %s" % (self.n_from,
                self.av_icount, self.n_to)
        else:
            return "%s (%s) --%.2f--> %s (%s)" % (
                self.n_from, self.asn_from,
                self.av_icount,
                self.n_to, self.asn_to)

    def __eq__(self, e):
        return self.n_from == e.n_from and self.n_to == e.n_to

    #def save_info(self, msm_id, kind, n_ones, mx_zrun, av_icount, pv,ps, zra):  # Present (binary) string
    #    # pv = 'present' vector, ps = string version of pv
    #    self.msm_id = msm_id;  self.kind = kind;  
    #    self.n_ones = n_ones; self.mx_zrun = mx_zrun
    #    self.av_icount = av_icount
    #    self.pv = pv;  self.ps = ps
    #    self.zra = zra

    def distance(self, e2):
        return np.sum(self.pv == e2.pv)

    def node_asn(self, prefix):
        #print("edge.node_asn(%s), node_dir[] %s" % (prefix, self.node_dir[prefix]))
        if prefix in self.node_dir:
            return self.node_dir[prefix]
        else:
            if not prefix in no_asn_nodes:
                no_asn_nodes[prefix] = True
            return "unknown"
        
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

    def keep(self):  # Is important enough to keep?
        for e in self.edges:
            if e.count >= 250:
                return True
        return len(self.edges) > 1


class NodeInfo:
    tg       = 0;   tr = 1;    ts = 2;   tb = 3;  tf = 4;  tu = 5
    t_str = ['gone', 'root',' sub-root', 'branch', 'leaf', 'unknown <<<']
    #  Aboce used in gather-presence.py

    def update(self, bn, icount, fails, roots, sna):  # Sets .kind for each bin
        #print("-- %s: %s" % (self.name, sna))
        self.icount[bn] = icount;  self.fails[bn] = fails
        self.present[bn] = 1
        edict = {}
        for j in range(0, int(len(sna)/2)):
            edict[sna[2*j]] = int(sna[2*j+1])
        self.in_edges[bn] = edict
        #print("$$ %s" % self.in_edges[bn])
        
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
        self.in_edges = [ {} ]*n_bins  # Empty dictionary for each bin
        ##self.counts = [0]*len(self.t_str)
        self.update(bn, icount, fails, roots, sna)  # 6939
        
    def __str__(self):
        there = ''
        for bn in range(0, n_bins):  # Make string of 1s and 0s
            there += str(self.present[bn])
        return "%20s: %s" % (self.name, there)


class GraphInfo:
    def __init__(self, msm_id, all_edges, node_dir):
        self.msm_id = msm_id
        self.all_edges = all_edges
        self.node_dir =  node_dir
        self.nodes = {}  # Dictionary, all nodes seen in DestGraph
        self.edges = {}  # Ditto for edges
        self.paths = {}  # Ditto for paths
        self.p_counts = np.zeros(n_bins+1)  # bins 1..336
        self.same_counts = np.zeros(n_bins+1)  # In same ASN
        self.inter_counts = np.zeros(n_bins+1)  # Between ASNs

        fn = c.msm_graphs_fn(self.msm_id)
        print(" >>> %d: %s" % (msm_id, fn))
        f = open(fn, 'r')
        gf_version = 1
        bn = 0
        for line in f:
            la = line.strip().split(maxsplit=1)
            if la[0] == "BinGraph":
                bv = la[1].rsplit(maxsplit=1)
                bn = int(bv[1])  # Bin nbr
                #if bn == 2:  #### n_bins:  # Never reached ???
                #    break
                #n_traces, n_succ_traces, n_dup_traces, \
                #    t_addrs, t_hops, t_hops_deleted, bin_nbr = la[1:]
                roots_line = f.readline()
                rla = roots_line.strip().split()
                mx_edges = int(rla.pop(0))
                #print("++ %3d  %d %s" % (bn, mx_edges, rla))
            elif la[0] == "Node":
                nv = la[1].split()
                name = nv[0];  subnet = int(nv[1]);  icount = int(nv[2])
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
                        self.edges[e_key] = Edge(src, name, node_dir)
                    self.edges[e_key].set_icount(bn, count)
                if name in self.nodes:
                    self.nodes[name].update(bn, icount, fails, rla, sna)
                else:
                    self.nodes[name] = \
                        NodeInfo(bn, dest, name, icount, fails, rla, sna)
                
            elif la[0] == "DestGraphs":
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

    stable = 0;  interesting = 1
    occ_gaps = 2;  intermittent = 3;  occ_seen = 4
    ek_str = ["Stable", "Interesting",
              "Occasional gaps", "Intermittent", "Seldom seen"]

    def ekind(self, n_ones, n_zeroes, one_runs, zero_runs, mx_orun, mx_zrun):
        r = -1
        if n_ones == n_bins:
            r = self.stable
        #elif mx_orun >= 12 and mx_zrun >= 4 and zero_runs < 4:
        #elif n_ones >= 240 and mx_zrun >= 5:
        elif n_ones >= 240 and mx_zrun >= 4:  # 5 days (out of 7)  WAS 2 RUNS
                #abs(one_runs-zero_runs) <= 1:
            r = self.interesting  # big runs of 1, with long breaks
        elif n_ones >= 192:  # Mostly ones (4 days)
            if mx_zrun < 3:
                r = self.occ_gaps
            else:
                r = self.intermittent
        else:  # Mostly zeroes
            if mx_zrun < 6:
                r = self.intermittent  # ~Repeating patterns
            else:
                r = self.occ_seen
        #if r == self.interesting_1:
        #if r != self.stable: # and r != self.occ_seen:
        #    print("n_ones = %d, n_zeroes = %d, 1_runs = %d, 0_runs = %d:  %s" % (
        #        n_ones, n_zeroes, one_runs, zero_runs,self.ek_str[r] ))
        return r

# 349 Stable
#  75 Interesting 1
#  49 Interesting 0
# 152 Occasional gaps zrun<5  133 <4 
#  69 Noisy
#  12 Intermittent
# 622 Occasionally seen

    def count_edges(self):  # Count all edges
        counts = np.zeros(n_bins+1)
        for ek in self.edges:
            e = self.edges[ek]
            ec = np.array(e.icount)
            present = np.not_equal(e.icount, 0).astype(int)
            n_ones = np.count_nonzero(present)  # Nbr of bins present
            self.p_counts[n_ones] += 1
        return self.p_counts
                       
    def asn_edges(self):  # Count Same- and Inter- ASN edges
        for ek in self.edges:
            e = self.edges[ek]
            #print("Edge e = %s" % e)
            present = np.not_equal(e.icount, 0).astype(int)
            n_ones = np.count_nonzero(present)  # Nbr of bins present
            if e.inter_as:
                self.inter_counts[n_ones] += 1
            else:
                self.same_counts[n_ones] += 1
        #print("asn_edges(): same_counts = %d, inter_counts = %d + + +" %  (
        #    len(self.same_counts), len(self.inter_counts)))
        return (self.same_counts, self.inter_counts)
                       
    def examine_nodes(self):
        print("+++ starting examine_nodes()")
        #z = np.zeros(n_bins)
        type_counts = np.zeros(len(self.ek_str))
        for nk in self.nodes:
            n = self.nodes[nk]
            ec = np.array(n.icount)
            self.present = np.not_equal(n.icount, 0).astype(int)  # pres vector
            n_ones = np.count_nonzero(self.present)  # Nbr of bins present
            self.p_counts[n_ones] += 1
            self.n_zeroes = n_bins-n_ones
            self.zra = self.zero_runs(ec)
            self.zra_len = self.zra[:,1]-self.zra[:,0]  # Run-of-zeroes lengths
            self.mx_zrun = 0
            if len(zra_len) != 0:
                self.mx_zrun = zra_len.max()
            self.ora = self.one_runs(ec)
            self.ora_len = self.ora[:,1]-self.ora[:,0]  # Run-of-ones lengths
            self.mx_orun = self.ora_len.max()
            self.kind = self.ekind(self.n_ones, self.n_zeroes, 
                len(self.ora), len(self.zra), self.mx_orun, self.mx_zrun)
            type_counts[self.kind] += 1
            if self.kind == self.stable:
                continue  # Not interesting                
            #if r != self.interesting_1:
            #    continue
            #print("zra_len %s" % zra_len)
            #print("ora_len %s" % ora_len)

            psl = np.apply_along_axis(  #  Apply along axis 0 of present
                lambda p: [str(i) for i in p], 0, present)
            self.ps = ''.join([''.join(s) for s in psl])  # pv string

            self.av_icount = np.average(ec, axis=0, weights=ec.astype(bool))
                # For type bool, False = 0, True = 1
                # weights (above) treats bools as ints
            #print(">>> %s" % (ec.astype(bool)).astype(int))

            #         5 days 
            #if n_ones >= 240 and mx_zrun >= 6:
            #if r == self.interesting:
            #    n.save_info(msm_id, n_ones, mx_zrun, av_icount, kind, present,ps, zra)
            #    print("%s: %.2f  %d %d %d %s" % (
            #        n.name, av_icount, n_ones, mx_zrun, len(zra), ps))
            self.all_nodes.append(n)

    def acor(self, y):  # https://stackoverflow.com/questions/643699/how-can-i-use-numpy-correlate-to-do-autocorrelation
        yunbiased = y-np.mean(y)
        ynorm = np.sum(yunbiased**2)
        acor = np.correlate(yunbiased, yunbiased, "same")/ynorm
        return acor[len(acor)/2:]  # use only second half
        
    def examine_edges(self):
        n_stable = 0
        same_counts = np.zeros(len(self.ek_str))
        inter_counts = np.zeros(len(self.ek_str))
        for ek in self.edges:
            e = self.edges[ek]
            if not e.inter_as:  # Only interested in Inter-AS edges
                continue
            ec = np.array(e.icount)
            e.present = np.not_equal(e.icount, 0).astype(int)
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
            e.kind = self.ekind(e.n_ones, e.n_zeroes, 
                len(ora), len(e.zra), e.mx_orun, e.mx_zrun)
            if e.inter_as:
                inter_counts[e.kind] += 1
            else:
                same_counts[e.kind] += 1
            if e.kind == self.stable:
                n_stable += 1
                continue  # Not interesting                
            #if kind != e.interesting_1:
            #    continue
            #print("zra_len %s" % zra_len)
            #print("ora_len %s" % ora_len)

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

            #         5 days 
            #if n_ones >= 240 and mx_zrun >= 6:
            #if r == e.interesting and e.inter_as:  # <<< ?
            if True:
                ##e.save_info(msm_id, kind,n_ones, mx_zrun, av_icount, present, ps, zra)
                #print("%s: %d  %d %d  %s" % (
                #    e, e.kind, e.n_ones, e.mx_zrun,  e.ps))            
                self.all_edges.append(e)
        print("examine_edges: n_stable = %d" % n_stable)
        return n_stable
                
        #print("\\\\------  %4d same -----" % msm_id)
        #self.print_counts(same_counts, msm_id)
        #print("\\\\------  %4d inter -----" % msm_id)
        #self.print_counts(inter_counts, msm_id)

        return self.p_counts
                       
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
    

def plot_p_counts(pca, ids):  # Plot counts (nbr of times pc[x] was seen)
    print("@@@ plot_p_counts()")
    pcc = []
    for pc in pca:
        print("p_counts = %s" % pc)
        cc = np.cumsum(pc)  # Cumulative counhts
        if pc_graph:
            cc = cc*(100.0/cc[-1])
        pcc.append(cc)
    pplt.figure(figsize=(8,10))
    xv = np.cumsum(np.ones(n_bins+1))
    #pplt.title("Full graph: Edge presence")
    which = "counts"
    if pc_graph:
        which = "percent"
    if asn_graph:
        pplt.title("ASN graph: Edge presence (%s)" % which)
        pfn = "counts-asn-%s.pdf" % which
    else:
        pplt.title("Full graph: Edge presence (%s)" % which)
        pfn = "counts-full-%s.pdf" % which
    pplt.ylabel("Number of edges")
    pplt.xlabel("Present for x timebins")
    for j in range(0, len(pca)):
        msm_id = ids[j]
        msm_dest = c.msm_dests[msm_id]
        ls = "%d (%s)" % (ids[j], msm_dest[0])
        pplt.plot(xv, pcc[j], label=ls)
    pplt.xlim(-4,340)  # x axis limits
    pplt.xticks(range(0,15*24, 24))
    pplt.legend(loc="upper left", title="Destination",
    bbox_to_anchor=(0.06,0.96), prop={"size":11}, handlelength=1)

    pplt.savefig(pfn)
        
def plot_asn_counts(pca, inter_ca, ids):  # Plot counts (nbr of times pc[x] was seen)
    #ymax = {5017:80, 5005:145, 5016:100, 5004:920, 5006:1270, 5015:1030}  # y axis upper limits
    xv = np.cumsum(np.ones(n_bins+1))  # x values
    #print("      xv = %s" % xv)
    #print("      pc_graph = %s" % pc_graph)
    pcc = [];  inter_cc = []
    for pc in pca:  # Same ASN
        cc = np.cumsum(pc)  # Cumulative counts
        if pc_graph:
            cc = cc*(100.0/cc[-1])
        pcc.append(cc)
    for ic in inter_ca:  # Between ASNs
        icc = np.cumsum(ic)  # Cumulative counhts
        if pc_graph:
            icc = icc*(100.0/cc[-1])
        inter_cc.append(icc)
    which = "counts"
    if pc_graph:
        which = "percent"
    if not c.full_graphs:
        title = "Full graph: edge presence (%s)" % which
        pfn = "inter-asn-full-%s.svg" % which
    else:
        #title = "ASN graph: edge presence (%s)" % which
        title = "Cumulative Edge Presence:  %s" % \
                c.start_time.strftime("%A, %d %b %Y")
        pfn = "inter-asn-%s.pdf" % which

    if len(ids) <= 3:
        rows = 1;  cols = len(ids)
        w = 8;  h = 3.4;  stp = 12;  tkp = 7;  tp = 12
    else:
        rows = 2;  cols = int(len(ids)/2)
        w = 8;  h = 6;  stp = 12;  tkp = 7;  tp = 12
    #print("+1+ pc %s, len(ids) %d, rows %d, cols %d" % (pc_graph, len(ids), rows, cols))

    #fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches (?)
    #if len(ids) <= 3:
    #    pplt.subplots_adjust(left=0.125, bottom=0.135, right=None, top=0.9,
    #                         wspace=0.5, hspace=0.85)
    #else:
    #    pplt.subplots_adjust(left=0.125, bottom=0.07, right=None, top=0.95,
    #                         wspace=0.5, hspace=0.35)
    fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches (?)
    if len(ids) <= 3:
        pplt.subplots_adjust(left=0.125, bottom=0.135, right=None, top=0.9,
                             wspace=0.5, hspace=0.85)
    else:
        pplt.subplots_adjust(left=0.125, bottom=0.08, right=None, top=0.9,
                             wspace=0.5, hspace=0.35)
    fig.suptitle(title, fontsize=14, horizontalalignment='center')
    
    for f in range(rows*cols):
        msm_id = ids[f]
        msm_dest = c.msm_dests[msm_id]
        ls = "%d (%s)" % (msm_id, msm_dest[0])
        r = int(f/cols);  nc = f%cols
        #print("%d: len(ids) = %d, f = %d, r=%d, nc=%d" % (
        #    msm_id, len(ids), f, r, nc))
        if len(ids) <= 3:
            xy = axes[nc]
        else:
            xy = axes[r,nc]
        xy.set_title(ls, fontsize=12)
        xy.set_xlabel("timebins present")
        if pc_graph:
            xy.set_ylabel("% edges")
        else:
            xy.set_ylabel("edges present")
        xy.tick_params(axis='x', labelsize=tkp)
        ntb = len(pcc[0])
        #print("ntb = %d, n_bins = %d" % (ntb, n_bins))
        xtick_incr = int(n_bins/8)
        xy.set_xticks(range(0,9*xtick_incr, xtick_incr))
        xy.set_xlim(-int(0.25*xtick_incr), int(8.45*xtick_incr))  # x axis lims
        xy.tick_params(axis='y', labelsize=tkp)
        if pc_graph:
            ymax = 105
        else:
            cc_max = np.max(pcc[f])
            icc_max = np.max(inter_cc[f])
            if icc_max > cc_max:
                cc_max = icc_max
            ymax = cc_max+15
        ##xy.set_ylim(-2,ymax[msm_id])  # x axis limits
        xy.set_ylim(-2, ymax)  # y axis limits
        xy.plot(xv, pcc[f], label="Same ASN")
        #print("  same AS: %s" % pcc[f])
        xy.plot(xv, inter_cc[f], label="Inter-ASN")
        #print("  inter-AS: %s" % inter_cc[f])
        xy.legend(loc="upper left", title="Edge type", fontsize=5,
                  bbox_to_anchor=(0.03,0.99), prop={"size":7}, handlelength=1)
            # fontsize for labels, "size" for heading
        xy.grid()
    pplt.savefig(pfn)

def plot_edge_presence(pv_eca, group, first_ix, e_labels):  # List 0f edges to plot presence
    # plot the first 10 edges for now
    n_edges = 40; w = 10;  h = 16;  stp = 9;  tkp = 8;  tp = 12
    #n_edges = 6; w = 10;  h = 2.5;  stp = 9;  tkp = 8;  tp = 12
    fig, xy = pplt.subplots(1,1, figsize=(w,h))  # Inches (?)
    pplt.subplots_adjust(left=0.23, bottom=0.12, right=None, top=None, #0.95,
                             wspace=None, hspace=None)
    ##fig.suptitle(title, fontsize=18, horizontalalignment='center')
    print("axes = %s, shape(axes) = %s" % (xy, np.shape(xy)))
    xv = np.concatenate(([0], np.cumsum(np.ones(335))))
    #print("xv = %s" % xv)
    #for f in range(rows*cols):
    #    r = f/cols;  nc = f%cols
    #    print("%d: len(ids) = %d, f = %d, r=%d, nc=%d" % (
    #        msm_id, len(ids), f, r, nc))
    #    xy = axes[nc]
    #xy.set_title(ls, fontsize=12)
    xy.set_xlim(-5,340)  # x axis limits
    xy.tick_params(axis='x', labelsize=tkp)
    xy.set_xticks(range(0,8*48, 48))
    xy.set_ylim(-0.5,n_edges*1.5)  # y axis limits
    pplt.setp(xy.get_yticklabels(), visible=False)  # Hide tick labels
    xy.yaxis.set_tick_params(size=0) # Hide y ticks
    hy = []
    for f in range(n_edges):
        hy.append(f*1.5 + 0.5)
    hx_min = np.ones(len(hy))*(-5.0)
    hx_max = np.ones(len(hy))*340.0
    xy.hlines(hy, hx_min, hx_max, linewidth=0.2, color='black')

    gx = []
    for x in range(48, 336, 48):
        gx.append(x)
    gy_min = np.ones(len(gx))*(-0.5)
    gy_max = np.ones(len(gx))*(n_edges*1.5)
    xy.vlines(gx, gy_min, gy_max, linewidth=0.2, color='black')

    for f in range(n_edges):
        if first_ix+f >= len(pv_eca):
            break
        e = pv_eca[first_ix+f]
        offset = f*1.5
        ymin = np.ones(336)*offset
        ymax = np.add(e.present, offset)
        if not e_labels:
            nn = "%s -> %s" % (e.asn_from, e.asn_to)
        else:
            nn = e_labels[f]
        print("%s, %s->%s, first 0 at %d to %d" % (
            nn, e.n_from, e.n_to, e.zra[0,0], e.zra[0,1]))
        b_width = 0.1
        #xy.bar(xv, y, b_width, color='green')    #'o', s=0.2, label=str(pv_eca[f]))
        #xy.vlines(xv, ymin, ymax, linewidth=0.8, color='blue')
        xy.vlines(xv, ymin, ymax, linewidth=0.4, color='blue')
        xy.text(-12, offset+0.3, nn, fontsize=stp,
                horizontalalignment='right')  # Axis units

        #xy.legend(loc="upper left", title="Edge type", fontsize=5,
        #          bbox_to_anchor=(0.03,0.99), prop={"size":7}, handlelength=1)
        #    # fontsize for labels, "size" for heading
        xy.grid()
    pfn = "%s-presence--%d.pdf" % (group, first_ix)
    pplt.savefig(pfn)
   
#  The code that looks for 'interesting' groups uses all_edges, that's
#  global above, and built by the NodeInfo class.
#  The code after that has problems with all_edges -
#    it needs a careful re-work, alas!

ids = [];  pca = [];  inter_ca = []
#for msm_id in [5005]:  # 5004]:
#for msm_id in c.msm_nbrs:
#for msm_id in [5017, 5006, 5005, 5004, 5016, 5015]:
#for msm_id in [5017, 5005, 5016]:
for msm_id in [5017, 5005, 5016, 5004, 5006, 5015]:
#for msm_id in [5017]:  ###  <<<<<<<<<<<<<
    all_edges = []  # List of all 'interesting' edges for all msm_ids
    msm_dest = c.msm_dests[msm_id][0]
    
    gf = GraphInfo(msm_id, all_edges, node_dir)
    print("%d has %d nodes with no asn <--" % (msm_id, len(no_asn_nodes)))
    #if len(no_asn_nodes) != 0:
    #    print("   %s" % no_asn_nodes)
    ids.append(msm_id)
    if not dendro:
        if inter_asn:
            same_counts, inter_counts = gf.asn_edges()
            pca.append(same_counts);  inter_ca.append(inter_counts)
        else:
            p_counts = gf.count_edges()
            pca.append(p_counts)
    else:
        if inter_asn:
            same_counts, inter_counts = gf.asn_edges()
            pca.append(same_counts);  inter_ca.append(inter_counts)
        else:
            p_counts = gf.count_edges()
            pca.append(p_counts)
    ##print("msm_id %s, inter_ca %s" % (msm_id, inter_ca))

    #continue  # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< ekinds for all msm_ids

    #if inter_asn:
    #    plot_asn_counts(pca, inter_ca, ids)  # Inter- Same-AS Edge comparisons
    #elif not dendro:
    #    plot_p_counts(pca, ids)  # Edge Presence CDF plots
    #else:
    #    pass

    continue  # Only plot the graphs
    
    def edge_key(e):  # sorted passes the dict"%d %d %s %e" % (e.msm_id, e.kind, e,ps, e)ionary key!
        #print("edge_key: %s" % str(e))
        #return e.av_icount
        ###print("%s %s %s %s %s %s" % (msm_id, e.kind, e.n_ones, e.mx_zrun, e.ps, e))      
        return "%d %d %s %d %d %s" % (msm_id, e.kind, e.ps, e.n_ones, e.mx_zrun, e)

    def print_counts(counts, msm_dest, msm_id):
        #print("Dest Name & Dest ID & Total & Interest0 & Seldom & Frequent & Mostly & Recurring & Interrupted &Stable \\\\")
        print("Dest Name & Dest ID & Total & Other & Correlated & Interrupted &Stable \\\\")
        tot = counts[0];  pc = []
        print("counts = %s" % counts)
        pc_m = 100.0/tot
        for j in range(1,8):
            pc.append(counts[j]*pc_m)
        other_pc = pc[0] + pc[1] + pc[2] + pc[3]
        print("%11s & %d & %4d & %5.1f\\%% & %5.1f\\%% & %5.1f\\%% & %5.1f\\%% \\\\" % (
            msm_dest, msm_id, tot, other_pc, pc[4], pc[5], pc[6]))

    def print_stats(e, ix, ac):
        av_orun = np.average(e.ora_len)
        av_zrun = np.average(e.zra_len)
        av_ms = av_orun/av_zrun
        print("%d: %d %d ones=%d, n_oruns=%d, n_zruns=%d, mx_orun=%d, mx_zrun=%d, av_orun=%.2f, av_zrun=%.2f, av_ms=%.2f\n%s" % (
            ix, msm_id, e.kind, e.n_ones, e.n_oruns, e.n_zruns, e.mx_orun, e.mx_zrun, av_orun, av_zrun, av_ms,
                e.ps))
        if ac:
            print("ac = %s" % gf.acor(e.present))

    print("= = = = =")
    n_stable = gf.examine_edges()
            
    if len(all_edges) < 5:
        print("\nOnly %d edges were 'interesting' !!!" % len(all_edges))
        continue

    pv_seldom = [];   pv_recurrent = [];   pv_frequent = []
    pv_mostly = [];   pv_interest0 = [];   pv_interest1 = [];      
    n_seldom = n_recurrent = n_frequent = n_mostly = n_interest0 = n_interest1 = 0
    n_unclassified = 0

    ix = -1
    for e in sorted(all_edges, key=edge_key, reverse=True):
## 1        print("%d %d %3d %3d %s %s" % (msm_id, e.kind, e.n_ones, e.mx_zrun,  e.ps, e))
        done = False
        #if e.mx_orun <= 8 and e.n_ones >= 24:  # and e.n_ones <= 48:
        if e.mx_orun <= 12 and e.n_ones >= 24:  # and e.n_ones <= 48:
            ac = gf.acor(e.present)
            if ac[1:24].max() >= 0.1:
            #    print_stats(e, ix, False);  ix += 1
                pv_recurrent.append(e)
            #    print(">Recurrent<")  # "acor = %s" % ac)
                n_recurrent += 1;  done = True
        if not done:
            #if e.n_ones >= 240 and e.mx_zrun >= 4 and \
            #    e.n_oruns <= 2 and e.n_zruns <= 2:
            if e.n_oruns <= 2 and e.n_zruns <= 2:
                if e.n_ones >= 96:  # 2*48
                    #print_stats(e, ix, False)
                    #print(">Interest1<")
                    pv_interest1.append(e)
                    n_interest1 += 1;  done = True
                else:
                    #print_stats(e, ix, False)
                    #print(">Interest0<")
                    pv_interest0.append(e)
                    n_interest0 += 1;  done = True
        if not done:
            if e.n_ones <= 48:
                #print_stats(e, ix, False)
                #print(">Seldom<")
                pv_seldom.append(e)
                n_seldom += 1;  done = True
        if not done:
            if e.n_ones > 240:
                #print_stats(e, ix, False)
                #print(">mostly<")
                pv_mostly.append(e)
                n_mostly += 1;  done = True
        if not done:
            #print_stats(e, ix, False)
            #print(">Frequent<")  # Doesn't quite look `interesting'!
            pv_frequent.append(e)
            n_frequent += 1
              
        #print("   zra = %s" % e.zra)
        #pv_eca.append(e)
    print("interest0=%d, seldom=%d, frequent=%d, mostly=%d, recurrent=%d, interest1=%d, total=%d" % (
               n_interest0, n_seldom, n_frequent, n_mostly, n_recurrent, n_interest1, len(all_edges)))
    if n_unclassified != 0:
        print("!!!!!! %d unclassified !!!!!!" % n_unclassifed)
    tot =  n_interest0 + n_seldom + n_frequent + n_mostly + n_recurrent + n_interest1 + n_stable
    print("$$$$$ n_stable = %d, len(all_edges) = %d, tot = %d" % (n_stable, len(all_edges), tot))
    cc = [tot, n_interest0, n_seldom, n_frequent, n_mostly, n_recurrent, n_interest1, n_stable]
    #print_counts(cc, msm_dest, msm_id)
    #print()
    #continue  ## <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    group_s = []
    #plot_edge_presence(pv_interest0, "interest0",  0, None)
    #plot_edge_presence(pv_interest0, "interest0", 40, None)
    #plot_edge_presence(pv_interest0, "interest0", 60, None)
    ##group_s.append(pv_interest0[75])  # Group 0, top line

    #plot_edge_presence(pv_seldom, "seldom",  0)
    ##group_s.append(pv_seldom[39])  # Group 1

    #plot_edge_presence(pv_frequent, "frequent",  0)
    ##group_s.append(pv_frequent[24])  # Group 2

    #plot_edge_presence(pv_mostly, "mostly",  0)
    ##group_s.append(pv_mostly[34])  # Group 3

    #plot_edge_presence(pv_recurrent, "recurring", 0)
    #plot_edge_presence(pv_recurrent, "recurring", 40)
    #plot_edge_presence(pv_recurrent, "recurring", 80)
    #recurr_ix = [8, 47, 54, 61, 71, 84]
    #pv_rec_s = []
    #for ix in recurr_ix:
    #    pv_rec_s.append(pv_recurrent[ix])
    #plot_edge_presence(pv_rec_s, "recur-sample", 0, None)
    #group_s.append(pv_recurrent[61])

    print("len() = %d <<<" % len(pv_interest0))
    plot_edge_presence(pv_interest1, "interest1",  0, None)
    plot_edge_presence(pv_interest1, "interest1", 40, None)
    #recurr_ix = [2,13, 31,32, 34,35]
    #pv_int1_s = []
    #for ix in recurr_ix:
    #    pv_int1_s.append(pv_interest1[ix])
    #plot_edge_presence(pv_interest1, "int1-sample", 0, None)
    #group_s.append(pv_interest1[21])

    group_names = ["Group 0", "Group 1", "Group 2", "Group 3", 
                   "Correlated", "Interrupted"];
    #plot_edge_presence(group_s, "group-samples", 0, group_names)
    exit()
    
    continue  # <<<<<<<<<<<<<<

    def ev_dist(pv1, pv2):  # Distance metric for clustering
        dist = np.sum(pv1 != pv2)
        #return dist
        if dist <= 1:  # log10(1) = 0, log10(0) = math domain error!
            return 0.05
        #return math.log10(dist)
        return math.log10(dist )

    eva = []  # 2d array of observation vectors
    eva_labels = []  # Labels for each edge
    eva_asns = []  # ASNs for each edge
    
    def e_name(x):
        ix = int(x)
        if ix > len(eva)-1:
            return "<%d>" % ix
        return eva_labels[ix]

    def e_asns(x):
        ix = int(x)
        if ix > len(eva)-1:
            return "<%d>" % ix
        return eva_asns[ix]

    def check_path(ea):
        print("\n%d Group Edges:" % msm_id)
        for j in range(len(ea)):
            e = all_edges[ea[j]]
            print("  %s  av icount %.2f" % (e, e.av_icount))


    continue  # <<<<<<<<<<<<<<
    
    print()  # "Starting dendro, all_edges = %s" % all_edges)
    for e in all_edges:
        eva.append(e.pv)  # Unsorted
        eva_labels.append("%s -> %s" % (e.n_from, e.n_to))
        eva_asns.append("%s -> %s" % (e.asn_from, e.asn_to))

    Z = linkage(eva, method='single', metric=ev_dist)  #'euclidean')

    n = len(eva)  # Number of edges
    print("\neva has %d edges, there were %d iterations" % (
        n, len(Z)))
    for r in range(0, len(Z)):
        #if Z[r,2] > 10:  # 0.6:
        if Z[r,0] > n and Z[r,1] > n:
            break
        print("r=%d, %s + %s ==> %s,  dist %.3f, (row %d in Z matrix)" % (r,
            e_name(Z[r,0]), e_name(Z[r,1]), e_name(n+r), Z[r,2], Z[r,3]))
        print("   ASNs  %s --> %s" % (e_asns(Z[r,0]), e_asns(Z[r,1])))
        if Z[r,2] > 0.05:
            break
    #continue  # <<<<<<<<<<<<<<
              
    ng = True;  ea = []
    for r in range(0, len(Z)):  # Print linkage matrix
        #print("%3d:  %3d %3d  %6.3f  %3d (%3d)  <%s + %d = %d>" % (r,
        #    Z[r,0],Z[r,1], Z[r,2], n+r, Z[r,3], n, r, n+r-1))
        if ng:
            if Z[r,2] >= 0.1:
                break  # NoZ[r,3] more low-dist groups
            ea.append(int(Z[r,0]));  ea.append(int(Z[r,1]))
            ng = False
            #print("New group: %s" % ea)
        elif Z[r,2] < 0.1 and Z[r,2] == Z[r-1,2] and Z[r,1] == n+r-1:
            # Same v.small dist && Z[r,2] adds to prev cluster -> end of group
            ea.append(int(Z[r,0]))
            #print("End of group: %s" % ea)
            #?p = check_path(ea)
            #?if p:
            #?    print("path = %s" % p)
            ng = True;  ea = []

    if dendro:
        pplt.figure(figsize=(6, 8))
        which = "%d (%s)" % (msm_id, c.msm_dests[msm_id][0])
        t = "RIPE Atlas Edges, single-Link dendrogram for %s" % which
        pplt.title(t, fontsize=10)
        pplt.xlabel('distance')  #'log10(distance)')
        dn = dendrogram(
            Z,
            orientation='right',  # Root at the right
            #leaf_rotation=90.0,  # rotates the x axis labels
            labels=eva_labels,
            leaf_font_size=5.0  # font size for the x axis labels
        )
        #print("dn = %s" % dn)
        ax = pplt.gca()
        #ax.set_xlim(-0.05, 2.1)
        #ax.set_xticks([float(x)/100.0 for x in range(0, 220, 20)])
        pplt.tight_layout(w_pad=5.0)  # Width padding 5x font size
            # Only one plot, so h_pad (height padding) isn't used
        #ASNpfn = "dendro-asn.pdf"
        pfn = "dendro-%d.pdf" % msm_id
        #pplt.show()
        pplt.savefig(pfn)

    print()

    ## https://docs.scipy.org/doc/scipy/reference/cluster.hierarchy.html
    
#exit()  #  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
print(">>> About to plot asn_counts")
plot_asn_counts(pca, inter_ca, ids)  # Inter- Same-AS Edge comparisons

if inter_asn:
    pass
     #plot_asn_counts(pca, inter_ca, ids)  # Inter- Same-AS Edge comparisons
elif not dendro:
    plot_p_counts(pca, ids)  # Edge Presence CDF plots
