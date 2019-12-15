# 1658, Sun 30 Jun 2019 (NZST)
# 1802, Thu  1 Mar 2018 (NZDT)
# 1427, Tue  1 Aug 2017 (NZST)
#
#  e_p_ni_gi.py: Edge, Path, NodeInfo and GraphInfo classes
#                        (for edge-presence programs)
#                Graphinfo has the summary stats routines!
#
# Copyright 2019, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import numpy as np

import config as c

class Edge:
    def __init__(self, src, dest, node_dir, n_bins, asn_graph, no_asn_nodes):
        self.n_from = src;  self.n_to = dest  # Node names
        self.node_dir = node_dir;  self.n_bins = n_bins
        self.asn_graph = asn_graph;  self.no_asn_nodes = no_asn_nodes
        self.icount = [0]*self.n_bins;  self.av_icount = 0
        self.msm_id = self.pv = self.ps = self.zra = None
        if c.full_graphs:
            self.asn = self.asn_from = self.node_asn(src)
            self.asn_to = self.node_asn(dest)
        else:
            self.asn_from = src;  self.asn_to = dest
        self.last_nb = 0
        self.inter_as = self.asn_from != self.asn_to
        self.plot_label = '';  self.pv = False
            # label and presence array for plots
        #print("Edge.init(): asn_from = %s, asn_to = %s" % (self.asn_from, self.asn_to))

    def set_icount(self, nb, count):
        self.icount[nb] = count
        self.last_nb = nb
        
    def __str__(self):
        print("e.plot_label = >%s<" % self.plot_label)
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

    def node_asn(self, prefix):
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

    def __init__(self, bn, dest, name, icount, fails, roots, sna, n_bins):
        #print("bin %d, roots = %s" % (bn, roots))
        self.name = name;  self.root = name == dest;  self.n_bins = n_bins
        ##print(">> %s  %s  %s" % (name, dest, self.root))
        self.present = [0]*self.n_bins;  self.kind = [self.tg]*self.n_bins
        self.icount = [0]*self.n_bins;  self.fails = [0]*self.n_bins
        self.in_edges = [ {} ]*self.n_bins  # Empty dictionary for each bin
        ##self.counts = [0]*len(self.t_str)
        self.update(bn, icount, fails, roots, sna)  # 6939
        
    def __str__(self):
        there = ''
        for bn in range(0, self.n_bins):  # Make string of 1s and 0s
            there += str(self.present[bn])
        return "%20s: %s" % (self.name, there)

class SubRoot:            
    def one_runs(self, a):
        w = np.logical_not(np.equal(a, 0))  # 1s for each 0 in a
        isone = np.concatenate(([0], w.view(np.int8), [0]))
        absdiff = np.abs(np.diff(isone))  # 1 in position before change
        return  np.where(absdiff == 1)[0].reshape(-1, 2)  # Ranges of 1s

    def __init__(self, name, sub_roots, sub_root_counts):
        self.name = name  # Address (or ASN) of sub_root
        self.sub_roots = sub_roots  # List of subroot names
        self.sub_root_counts = sub_root_counts
        self.sr_for = np.count_nonzero(self.sub_roots)
        self.max_count = np.max(self.sub_root_counts)
        ec = np.array(self.sub_root_counts)
        self.av_count = np.average(ec, axis=0, weights=ec.astype(bool))
        self.nz_counts = np.count_nonzero(self.sub_roots)
        ora = self.one_runs(self.sub_root_counts)
        ora_len = ora[:,1]-ora[:,0]  # Run-of-ones lengths
        self.n_oruns = len(ora_len)
        self.mx_orun = 0
        if len(ora_len) != 0:
            self.mx_orun = ora_len.max()
        ora = self.one_runs(self.sub_roots)
        ora_len = ora[:,1]-ora[:,0]  # Run-of-ones lengths
        self.n_subruns = len(ora_len)
        self.mx_subrun = 0
        if len(ora_len) != 0:
            self.mx_subrun = ora_len.max()
        self.plot_label = '';  self.pv = False

        #print("SubRoots: name=%s, nz_counts=%s" % (self.name, self.nz_counts))


class GraphInfo:
    def __init__(self, msm_id, node_dir, n_bins, asn_graph,
            n_asns, no_asn_nodes):
        self.msm_id = msm_id
        self.fn = None
        self.n_traces = self.n_succ_traces = self.n_dup_traces = \
            self.t_addrs = self.t_hops = self.t_hops_deleted = 0

        self.node_dir =  node_dir;  self.n_bins = n_bins
        self.n_asns = n_asns
        self.sub_roots = {}  # BG sub_root (for all bins)
        self.sub_root_counts = {}  # in_count (for all bins)

        self.stats = {}
        self.p_counts = np.zeros(self.n_bins+1)  # Edges in bins 0..335
        self.stats['edges_counts'] = self.p_counts
        self.same_counts = np.zeros(self.n_bins+1)  # Edges in same ASN
        self.stats['edges_same'] = self.same_counts
        self.inter_counts = np.zeros(self.n_bins+1)  # Edges between ASNs
        self.stats['edges_inter'] = self.inter_counts
        # +1 in above so we can compare pairs of array elements (!)
        self.all_edges = []

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

        self.name = c.msm_dests[self.msm_id][0]  # Other info (from graphs)
        self.dest = ""        # Dest IP address
        self.nodes_tot = np.zeros(self.n_bins)  # Nodes in graph
        self.stats["nodes_tot"] = self.nodes_tot
        self.nodes_outer = np.zeros(self.n_bins)  # 1st hop from probes
        self.stats["nodes_outer"] = self.nodes_outer
        self.nodes_1hop = np.zeros(self.n_bins)  # 1 hop before dest
        self.stats["nodes_1hop"] = self.nodes_1hop
        self.edges_tot = np.zeros(self.n_bins)
        self.stats["edges_tot"] =  self.edges_tot
        self.edges_same = np.zeros(self.n_bins)
        self.stats["edges_same"] =  self.edges_same
        self.edges_inter = np.zeros(self.n_bins)
        self.stats["edges_inter"] =  self.edges_inter
        self.trpkts_outer = np.zeros(self.n_bins)  # trs from probes
        self.stats["trpkts_tot"] = self.trpkts_outer
        self.trs_dest = np.zeros(self.n_bins)  # trs arriving at dest
        self.stats["trpkts_dest"] = self.trs_dest
        self.stats["asns_tot"] = self.n_asns
        self.n_subroots = np.zeros(self.n_bins)
        self.stats["subroots"] = self.n_subroots
        self.n_subroot_trs = np.zeros(self.n_bins)
        self.stats["trpkts_subroot"] = self.n_subroot_trs

        self.fn = c.msm_graphs_fn(self.msm_id)
        print(" >>> %d: %s" % (msm_id, self.fn))
        f = open(self.fn, "r")
        gf_version = 1
        bn = -1
        for line in f:  # Read in the graphs file
            la = line.strip().split(maxsplit=1)
            if la[0] == "BinGraph":
                if bn >= 0:
                    self.edges_tot[bn] = len(self.edges)
                    e_same = e_inter = 0
                    for e_key  in self.edges:
                        e = self.edges[e_key]
                        if e.asn_to == e.asn_from:
                            e_same += 1
                        else:
                            e_inter += 1
                    self.edges_same[bn] = e_same;  self.edges_inter[bn] = e_inter
                    self.n_subroots[bn] = n_subroots
                    self.n_subroot_trs[bn] = n_subroot_trpkts

                bn = int(la[1].split()[6])
                roots_line = f.readline()
                rla = roots_line.strip().split()
                self.nodes = {}  # Dictionary, all nodes seen in bin bn
                self.edges = {}  # Ditto for edges
                self.paths = {}  # Ditto for paths
                n_subroots = n_subroot_trpkts = 0

                for r in rla[2:]:  # rla[0] = mx_counts, rla[1] = dest
                    if not r in self.sub_roots:
                        self.sub_roots[r] = np.zeros(self.n_bins+1)
                        self.sub_root_counts[r] = np.zeros(self.n_bins+1)
                    self.sub_roots[r][bn] = 1
                    n_subroots += 1;  
                    #print("++ %3d  %s" % (bn, r))

            elif la[0] == "Node":
                self.nodes_tot[bn] += 1
                nv = la[1].split()
                name = nv[0];  subnet = int(nv[1]);  icount = int(nv[2])
                # 'subtree' as found when building the graph
                if name in self.sub_roots:
                    self.sub_root_counts[name][bn] = icount
                    n_subroot_trpkts += icount
                fails = -1  # Not in v1 graphs file
                if gf_version != 1:
                    fails = int(nv[3])
                s_nodes_line = f.readline()  # s_nodes line
                sna = s_nodes_line.split()  # name, in_count pairs
                
                if name in self.nodes:  # Get info about nodes
                    self.nodes[name].update(bn, icount, fails, rla, sna)
                else:
                    self.nodes_tot += 1
                    self.nodes[name] = NodeInfo(bn, self.dest, name, 
                        icount, fails, rla, sna, self.n_bins)

                if name == self.dest:
                    self.nodes_1hop[bn] = len(sna)/2
                    self.trs_dest[bn] = icount

                for j in range(0, int(len(sna)), 2):  # Get info about edges
                    src = sna[j];  count = int(sna[j+1])
                    e_key = "%s %s" % (src, name)
                    if not e_key in self.edges:
                        self.edges[e_key] = Edge( src, name,
                            node_dir, self.n_bins, asn_graph, no_asn_nodes)
                    self.edges[e_key].set_icount(bn, count)
 
            elif la[0] == "DestGraphs":
                nv = la[1].split()  # One or more white-space chars
                self.dest = nv[1]
                if len(nv) > 7:  # nv[7] = min_tr_pkts (last in v1 headers)
                    gf_version = 2

        self.edges_same[bn] = e_same;  self.edges_inter[bn] = e_inter
        self.n_subroots[bn] = n_subroots
        self.n_subroot_trs[bn] = n_subroot_trpkts
        print("----- EOF for pass 1")

        self.edges_tot[bn] = len(self.edges)
        e_same = e_inter = 0
        for e_key  in self.edges:
            e = self.edges[e_key]
            if e.asn_to == e.asn_from:
                e_same += 1
            else:
                e_inter += 1
        self.edges_same[bn] = e_same;  self.edges_inter[bn] = e_inter
        self.n_subroots[bn] = n_subroots
        self.n_subroot_trs[bn] = n_subroot_trpkts
        f.close()

        #for nk in self.nodes:
        #    print(self.nodes[nk])
        print("EOF reached")

    def count_outer_nodes(self):  # 2nd pass, we have all the edges
        # and nodes from Node lines.  Now we look at s_nodes line
        f = open(self.fn, 'r')
        bn = -1
        for line in f:  # Read in the graphs file
            la = line.strip().split(maxsplit=1)
            if la[0] == "BinGraph":
                if bn >= 0:
                    #print("bn %2d, n_leaves %d, n_trpkts_outer %d" % \
                    #    (bn, len(leaf_nodes), self.trpkts_outer))
                    self.nodes_outer[bn] = len(leaf_nodes)
                    self.trpkts_outer[bn] = trpkts_outer
                self.nodes = {}  # Dictionary, all nodes seen in bin bn
                self.edges = {}  # Ditto for edges
                self.paths = {}  # Ditto for paths
                trpkts_outer = 0;  leaf_nodes = {}
                    
                ila = list(map(int, la[1].split()))
                bn = ila[6]
                self.n_traces [bn] = ila[0]
                self.n_succ_traces [bn] = ila[1]
                self.n_dup_traces [bn] = ila[2]
                self.t_addrs [bn] = ila[3]
                self.t_hops [bn] = ila[4]
                self.t_hops_deleted [bn] = ila[5]
            elif la[0] == "Node":
                s_nodes_line = f.readline()  # s_nodes line
                sna = s_nodes_line.split()  # name, in_count pairs
                for j in range(0, int(len(sna)), 2):
                    src = sna[j];  count = int(sna[j+1])
                    if not src in self.nodes:  # Outer (probe) node
                        if not src in leaf_nodes:
                            leaf_nodes[src] = 0
                        #    print("==> leaf %s, trs %d" % (src, count))
                        #else:
                        #    print("++> leaf %s, trs %d" % (src, count))
                        trpkts_outer += count
            elif la[0] == "DestGraphs":
                pass
        f.close()
        self.nodes_outer[bn] = len(leaf_nodes)
        self.trpkts_outer[bn] = trpkts_outer
        print("----- EOF for pass 2")

        self.nodes_outer[bn] = len(leaf_nodes)
        self.trpkts_outer[bn] = trpkts_outer

    def gstat_val(self, reqd_stat):
        if not reqd_stat in self.stats:
            print("Statistic %s not know in GraphInfo" % reqd_stat)
            return False
        return self_stats[reqd_stat]

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
        if n_ones == self.n_bins:
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
        counts = np.zeros(self.n_bins+1)
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
        #z = np.zeros(self.n_bins)
        type_counts = np.zeros(len(self.ek_str))
        for nk in self.nodes:
            n = self.nodes[nk]
            ec = np.array(n.icount)
            self.present = np.not_equal(n.icount, 0).astype(int)  # pres vector
            n_ones = np.count_nonzero(self.present)  # Nbr of bins present
            self.p_counts[n_ones] += 1
            self.n_zeroes = self.n_bins-n_ones
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
            self.ps = ''.join([''.join(s) for s in psl])  # 'present' string

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
        howmany = int(len(acor)/2)
        return acor[howmany:]  # use only second half
        
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
            e.n_zeroes = self.n_bins-e.n_ones
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
            self.all_edges.append(e)
        print("examine_edges: n_stable = %d" % n_stable)
        return n_stable
                
        #print("\\\\------  %4d same -----" % msm_id)
        #self.print_counts(same_counts, msm_id)
        #print("\\\\------  %4d inter -----" % msm_id)
        #self.print_counts(inter_counts, msm_id)

        return self.p_counts
                       
    def classify_edges(self):
        seldom = [];   recurrent = [];   frequent = []
        mostly = [];   interest0 = [];   interest1 = [];      

        #t_p = {  # Parameters for classifying 336 bins
        #    'n_ones': 24, 'mx_orun': 12,
        #    'n_oruns': 2, 'n_zruns': 2,
        #    'n_ones_i1': 96, 'n_ones_seldom': 48, 'n_ones_mostly':240,
        #    }
        #sf = n_bins/336.0
        sf = 48/336.0  # Use paramaters for just one day of timebins
        print("n_bins = %d, sf = %.3f" % (self.n_bins, sf))
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
            #if e.mx_orun <= t_p['mx_orun'] and \
            #       e.n_ones >= t_p['n_ones']:
            #    ac = self.acor(e.present)
            #    if ac[1:24].max() >= 0.2:  ###0.1:
            #        recurrent.append(e)
            #        done = True
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
    
