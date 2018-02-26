# 1745, Thu 22 Feb 2018 (NZDT)
# 0858, Tue 14 Nov 2017 (SGT)
# 1117, Mon  9 Jan 2017 (NZDT)
#
# msm_file.py: Read stats file -> MsmFile, TbStats and Root classes
#
# Copyright 2018, Nevil Brownlee,  U Auckland | RIPE NCC

import numpy as np  # Operations on arrays
# http://wiki.scipy.org/Tentative_NumPy_Tutorial

import config as c
tb_mx_depth = c.stats_mx_depth+1  # mx_depth = mx hops back from dest

class Root:
    mx_trees = 20  # Constant in graph.py
    mx_depth = 0

    def __init__(self, r_nbr, prefix, mx_tr_pkts):
        self.r_nbr = r_nbr;  self.pref_s = prefix
        self.d_edges = [  # 2D: edges at each depth _for this root_
            {} for j in range(tb_mx_depth)]  # T/F
 
    def __str__(self):
        return ("Root %d, %tr_pkts" %  self.r_nbr, self.edge_count)

    def add_edge(self, depth, e_to, e_from, tr_pkts):
        et = (e_from, e_to)
        if et not in self.d_edges[depth]:
            self.d_edges[depth][et] = tr_pkts
        
    def root_stats(self, tbs):
        self.pd_edges = [ # 2D: Edges (after prunung) for each prune_pc
            {} for j in range(tbs.n_prune_pkts)]
        self.d_tr_pkts = [ # 2D: lists of tr_pkts (after pruning) at each depth
            [] for j in range(tb_mx_depth) ]
        self.pd_nodes = [  # Nodes (after prunung) for each prune_pc
            {} for j in range(tbs.n_prune_pkts)]
        self.pc_edges = np.zeros(len(tbs.prune_pkts))
        self.pc_nodes = np.zeros(len(tbs.prune_pkts))
        self.pc_tr_pkts = np.zeros(len(tbs.prune_pkts))
        #for x in range(tb_mx_depth):
        #    print("--- d=%d, len(d_edges[d])=%d" % (x, len(self.d_edges[x])))
        for pcx,pc in enumerate(tbs.prune_pkts):  # for each prune_pc
            #prune_tr_pcs = int(tbs.prune_pcs[pcx]*
            #    tbs.mx_root_tr_pkts/100.0)
            prune_tr_pkts = int(tbs.prune_pkts[pcx])
                # Use min_tr_pks instead of prune_pcs
  

            for d in range(tb_mx_depth):  # each depth (for this root)
                e_d = self.d_edges[d]  # Edges dict for this depth
                for e in e_d:  # 
                    tr_pkts = e_d[e]
                    to = e[0];  fr = e[1]; 
                    #print("e=%s, to %s from %s, %d tr_pkts" % (
                    #    e, to, fr, tr_pkts))
                    if tr_pkts >= prune_tr_pkts:
                        if not np.any(fr == self.pc_edges):
                                # fr in self.pc_edges
                            self.pd_edges[pcx][e] = True
                        if not np.any(fr == self.pc_nodes):
                                # fr in self.pc_nodes
                            self.pd_nodes[pcx][fr] = True

            self.pc_edges[pcx] = len(self.pd_edges[pcx])
            self.pc_nodes[pcx] = len(self.pd_nodes[pcx])
            #self.pc_tr_pkts[pcx] = len(self.d_tr_pkts[pcx])

        for d in range(tb_mx_depth):  # each depth (for this root)
            e_d = self.d_edges[d]  # Edges dict for this depth
            for e in e_d: 
                tr_pkts = e_d[e]
                self.d_tr_pkts[d].append(tr_pkts)
            if len(e_d) > 0 and len(e_d) > self.mx_depth:
                self.mx_depth = d
            #print("ddd depth %d, d_tr_pkts = %s" % (d, self.d_tr_pkts[d]))
            #print("mx_depth = %d\n" % self.mx_depth)

class TbStats:
    prune_pkts = []
    n_prune_pkts = 50
    prune_pc = 0;  mx_root_tr_pkts = 0
    
    def __init__(self, bn, msm_id):
        self.prune_pkts = []
        self.bn = bn;  self.msm_id = msm_id
        self.ra = []  # Roots in this timebin
        if len(self.prune_pkts) == 0:
            if msm_id == 5016:  # prune_pc values for pam-2014 paper <<<
                for n in range(self.n_prune_pkts):  # 0.2 to 4.0 for 5016 (j.root)
                    self.prune_pcs.append(0.2+n*0.2)
            else:
                ##for n in range(self.n_prune_pcs):  # 0.2 to 1.2 for others
                ##    self.prune_pcs.append(0.2+n*0.05)
                #for n in range(self.n_prune_pcs):  # 0.05 to 0.54 for others
                for n in range(self.n_prune_pkts):  # 0.05 to 0.54 for others
                    self.prune_pkts.append(8+n*6)  # [10,60]
                #print("prune_pkts = %s" % self.prune_pkts)

    def set_TbRoots(self, prune_pkts, mx_tr_pkts):
        TbStats.prune_pkts = float(prune_pkts)
        TbStats.mx_root_tr_pkts = int(mx_tr_pkts)

    def sum_roots(self, msm_id):  # Set TbStats pc_tr_pkts
        self.pc_nodes = np.zeros(self.n_prune_pkts)  # Nodes for each prune_pc
        self.pc_edges = np.zeros(self.n_prune_pkts)  # edges ditto
        self.pc_tr_pkts = np.zeros(self.n_prune_pkts)  # tr_pkts ditto
        for j in range(len(self.ra)):  # All the root objects
            self.pc_nodes = np.add(self.pc_nodes,self.ra[j].pc_nodes)
            self.pc_edges = np.add(self.pc_edges,self.ra[j].pc_edges)
            self.pc_tr_pkts = np.add(self.pc_tr_pkts,self.ra[j].pc_tr_pkts)
        #print("sum_roots(): pc_tr_pkts = %s" %  self.pc_tr_pkts)

        self.tb_tr_pkts = [  # Tr_Pkts for roots x depth (2D)
            [] for j in range(tb_mx_depth)]
        self.tn_tr_pkts = []  # Tr_Pkts for all roots at each depth (1D) 
        d_t_pkts = np.zeros(tb_mx_depth)
        for d in range(tb_mx_depth):
            for r in range(len(self.ra)):  # All the root objects
                self.tb_tr_pkts[d].extend(self.ra[r].d_tr_pkts[d]) # << plotted
            self.tn_tr_pkts.append(np.array(self.tb_tr_pkts[d]))
            #print("tb_tr_pkts[%d] = %s" % (d, self.tb_tr_pkts[d]))
            d_t_pkts[d] =  np.array(self.tb_tr_pkts[d]).sum()

        #print("d_t_pkts = %s" % d_t_pkts)
        tot_tr_pkts = d_t_pkts.sum()
        #print("tot_tr_pkts = %d" % tot_tr_pkts)
        pc_mult = 100.0/tot_tr_pkts
        cum_pc_tr_pkts = np.cumsum(d_t_pkts*pc_mult)
        #print("%d: cum_pc_tr_pkts =" % msm_id, end='')
        #for d in range(tb_mx_depth):
        #    print("  %.2f" % cum_pc_tr_pkts[d], end='')
        #print()

            
class MsmFile:
    sf = None    # Stats filename for this msm_id
    tbsa = None  # TbStats array for this msm_id

    def getline(self):
        line = self.sf.readline()
        if line == "":  # EOF
            return 'X', None
        flag = line[0]
        la = line[1:].strip().split()
        return flag, la

    def read_roots(self, tbs, ln):
        r_nbr = 0;  r_obj = None
        while True:
            flag, la = self.getline();  ln += 1
            #print "r_roots %d %s" % (ln, flag)
            if flag == "R":  #   Header for next root
                if r_obj:  # Handle info for previous root
                    r_obj.root_stats(tbs)
                    #if r_nbr == 1:  # Only do one root
                    #    return flag, la, ln
                r_prefix = la.pop(1)  # string
                r_nbr, r_mx_tr_pkts = map(int, la)
                #print("RRR %d, %s, %d" % (r_nbr, r_prefix, r_mx_tr_pkts))
                r_obj = Root(r_nbr, r_prefix, r_mx_tr_pkts)
                tbs.ra.append(r_obj)
                ###print("flag 'R': r_obj.pc_edges = %s" % r_obj.pc_edges)
            elif flag == "N":
                n_prefix = la.pop(0)  # string
                n_depth, n_tr_pkts, n_mx_so_far = map(int, la)
                print("NNN %s, %d, %d, %d" % (
                    n_prefix, n_depth, n_tr_pkts, n_mx_so_far))
                r_obj.add_node(n_depth, n_prefix, n_tr_pkts)
            elif flag == "E":
                e_depth = int(la[0])
                e_tr_pkts = int(la[3])
                #print("EEE %d, (%s, %s)" % (e_depth, la[1], la[2]))
                r_obj.add_edge(e_depth, la[1], la[2], e_tr_pkts)  # e_to, e_from
            elif flag == "T":  # Trailer for this timebin
                if r_obj:  # Handle info for previous root
                    r_obj.root_stats(tbs)
                    #print "r_obj.n_tr_pkts = %s" % r_obj.n_tr_pkts
                tbs.sum_roots(self.msm_id)  #  Sum for all roots
                already_walked, loop_detected, n_too_deep = map(int, la)
                #print("TTT %d %d %d  bin %02d" % (
                #    already_walked, loop_detected, n_too_deep, tbs.bn))
                return flag, la, ln
            elif flag == "X":  # EOF
                print(">>>> Unexpected EOF")
                return flag, la, ln

    def __init__(self, stats_fn, n_bins):
        print("MsmFile: n_bins = %d" % n_bins)
        sa = stats_fn.split("-")
        self.msm_id = int(sa[1]);  self.mx_depth = int(sa[5])
        #print("msm_file: sa = %s" % sa)
        #print("Stats report for file %s" % c.msm_stats_fn(self.msm_id))
        self.sf = open(stats_fn, "r")
        self.tbsa = []

        bn = 0;  ln = 0;  r_obj = None
        while True:
            flag, la = self.getline();  ln += 1
            #print "line %d %s" % (ln, flag)
            if flag == "X":  # EOF
                break
            if flag == "H":  # Header for timebin bn
                t_dest, n_traces, mx_tr_pkts, prune_pc, prune_tr_pkts, f_bn = la
                #print(">>> bn %d: msm_id %s, mx_depth %d, mx_tr_pkts %s," % (
                #    bn, self.msm_id, self.mx_depth, mx_tr_pkts))
                #print("prune_pc %s, prune_tr_pkts %s, n_traces %s" % (
                #    prune_pc, prune_tr_pkts, n_traces))
                tbs = TbStats(bn, self.msm_id)
                tbs.set_TbRoots(prune_pc, mx_tr_pkts)
                flag, la, ln = self.read_roots(tbs, ln)
                #tbs.plot_roots()
                #tbs.plot_stacked()
                self.tbsa.append(tbs)

                #break  # Only do one timebin
                #print("  f_bn=%d, bn=%d" % (int(f_bn), bn))
                bn += 1
                if bn == n_bins:  # Stop after n_bins bins
                    break
                
        self.sf.close()
