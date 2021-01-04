# 1730, Wed  8 Jan 2020 (NZDT)  # Removed code for prunung graphs
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

#? tb_mx_depth = 0  # Max depth found in stats file
    
class Root:
    def __init__(self, r_nbr, prefix, mx_tr_pkts):
        self.r_nbr = r_nbr;  self.pref_s = prefix
        self.d_edges = [  # 2D: edges at each depth _for this root_
            {} ]  # Start with depth 0 only
#            {} for j in range(tb_mx_depth)]  # T/F
        self.mx_depth = 1

    def __str__(self):
        return ("Root %d, mx_depth %d" %  (self.r_nbr, self.mx_depth))

    def add_edge(self, depth, e_to, e_from, tr_pkts):
        et = (e_from, e_to)
        if depth > len(self.d_edges)-1:
            self.d_edges.append({})
            self.mx_depth += 1
        if et not in self.d_edges[depth]:
            self.d_edges[depth][et] = tr_pkts

    def root_stats(self, tbs):  
        # Made tables pf tr_pkts and nodes after prunung
        #   Pruning code deleted Feb 2020
        #print("==2== starting root_stats: tb_mx_depth=%d" % self.mx_depth)
        self.d_tr_pkts = [ # 2D: lists of tr_pkts at each depth
            [] for j in range(self.mx_depth) ]
        #print("==3== Root.d_tr_pkts = (%d)" % (len(self.d_tr_pkts)))
        for d in range(self.mx_depth):  # each depth (for this root)
            e_d = self.d_edges[d]  # Edges dict for this depth
            for e in e_d: 
                tr_pkts = e_d[e]
                self.d_tr_pkts[d].append(tr_pkts)

class TbStats:
    def __init__(self, bn, msm_id):  ###  bn)  ###, n_bins):
        self.msm_id = msm_id
        #self.distal_mx_depth = np.zeros(n_bins)
        #self.distal_min_ntrs = np.zeros(n_bins)
        self.tb_mx_depth = 1
        self.ra = []  # Roots in this timebin
        self.tb_tr_pkts = []
        self.d_t_pkts = None

    #def save_tb_stats(bn_mx_depth, bn_min_ntrs):
    #    print("== 4 == bn %d, mx_depth %d, min_trs %d" % (
    #        bn_mx_depth, bn_min_ntrs))
    #    self.distal_mx_depth[bn] = bn_mx_depth
    #    self.distal_min_ntrs[bn] = bn_min_ntrs
            
    def sum_roots(self, msm_id):  # Set TbStats tb_tr_pkts
        for root in self.ra:
            if root.mx_depth > self.tb_mx_depth:
                self.tb_mx_depth = root.mx_depth
        print("++> TbStats.tb_mx_depth = %d" % self.tb_mx_depth)
        self.tb_tr_pkts = [  # Tr_Pkts for roots x depth (2D)
            [] for j in range(self.tb_mx_depth)]

        for rn,root in enumerate(self.ra):  # Iterate over all roots
            tb_mx_d = len(root.d_edges)
            ##if tb_mx_d > tb_mx_depth:
            ##    tb_mx_depth = tb_mx_d
            self.tn_tr_pkts = []  # Tr_Pkts for all roots at each depth (1D) 
            for d in range(tb_mx_d):
                self.tb_tr_pkts[d].extend(root.d_tr_pkts[d]) # << plotted
                self.tn_tr_pkts.append(np.array(self.tb_tr_pkts[d]))
                #print("-- 1 -- rn=%d, d=%d, tb_tr_pkts[d] = %s" % (
                #    rn, d, self.tb_tr_pkts[d]))
        self.d_t_pkts = np.zeros(self.tb_mx_depth)
        for d in range(self.tb_mx_depth):
            self.d_t_pkts[d] =  np.array(self.tb_tr_pkts[d]).sum()
            #print("-- 2 -- d=%2d, d_t_pkts[d]=%s" % (d,d_t_pkts[d])) 

        #print("msm_id %d, mx_depth %d, tot_tr_pkts %s" % (
        #    self.msm_id, self.tb_mx_depth, d_t_pkts))
        #print("TbStats %d, mx_depth %d" % (
        #    self.msm_id, self.tb_mx_depth))


class MsmStatsFile:
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
        last_dest = "";  last_depth = last_tr_pkts = -1
        mx_depth_seen = 0;  min_distal_tr = 9999999
        while True:
            flag, la = self.getline();  ln += 1
            #print("^^ flag %s, la = %s" % (flag,la))
            if flag == "R":  #   Header for next root
                #print("++ flag %s, la = %s" % (flag,la))
                if r_obj:
                    r_obj.root_stats(tbs)
                    #print("&& 4 && last r_obj: mx_depth %d" % (
                    #    tbs.ra[-1].mx_depth))
                    #print("   d_edges = %s" % tbs.ra[-1].d_edges)
                r_prefix = la.pop(1)  # string
                r_nbr, r_mx_tr_pkts = map(int, la)
                #print("R %d, %s, %d" % (r_nbr, r_prefix, r_mx_tr_pkts))
                r_obj = Root(r_nbr, r_prefix, r_mx_tr_pkts)
                tbs.ra.append(r_obj)
            elif flag == "N":
                n_prefix = la.pop(0)  # string
                n_depth, n_tr_pkts, n_mx_so_far = map(int, la)
                print("Unexpected:  N %s, %d, %d, %d" % (
                    n_prefix, n_depth, n_tr_pkts, n_mx_so_far))
                r_obj.add_node(n_depth, n_prefix, n_tr_pkts)
            elif flag == "E":
                e_depth, dest, src, in_trs = la[0:4]
                e_depth = int(e_depth);  e_tr_pkts = int(in_trs)
                #print("E %d, %s, %s, %d" % (e_depth, dest, src, e_tr_pkts))
                r_obj.add_edge(e_depth, dest, src, e_tr_pkts)  # e_to, e_from
                if last_flag != "R":  # First edge for new root
                    if e_depth <= last_depth:  # Recursed back to lower depth
                        #print(">!>!> %s %d %d" % (
                        #    last_dest, last_depth, last_tr_pkts))
                        if last_depth > mx_depth_seen:
                            mx_depth_seen = last_depth
                        if last_tr_pkts < min_distal_tr:
                            min_distal_tr = last_tr_pkts
                last_depth = e_depth;  last_tr_pkts = e_tr_pkts
            elif flag == "T":  # Trailer for this timebin
                already_walked, loop_detected, n_too_deep = map(int, la)
                #print(">->-> %s %d %d" % (last_dest, last_depth, last_tr_pkts))
                #print("T %d %d %d  bin %02d" % (
                #    already_walked, loop_detected, n_too_deep, tbs.bn))
                if r_obj:  # Handle info for previous root
                    r_obj.root_stats(tbs)
                    #print "r_obj.n_tr_pkts = %s" % r_obj.n_tr_pkts
                tbs.sum_roots(self.msm_id)  #  Sum for all roots

                if last_depth > mx_depth_seen:
                    mx_depth_seen = last_depth
                if last_tr_pkts < min_distal_tr:
                    min_distal_tr = last_tr_pkts
                #print("?? mx_depth_seen = %d, min_distal_trpkts = %d" % (
                #    mx_depth_seen, min_distal_tr))
                return flag, la, ln
            elif flag == "X":  # EOF
                return flag, la, ln
            last_flag = flag
        print(">X>X> %s %d %d" % (last_dest, last_depth, last_tr_pkts))
        tbs.save_tb_stats(mx_depth_seen, min_distal_ntr)

    def __init__(self, stats_fn, first_bin, last_bin):
        sa = stats_fn.split("-")
        print("sa = %s" % sa)
        self.msm_id = int(sa[1])
        print("MsmStatsFile: %d, bins = %d-%d" % (
            self.msm_id, first_bin, last_bin))
        #print("msm_file: sa = %s" % sa)
        #print("Stats report for file %s" % c.msm_stats_fn(self.msm_id))
        self.sf = open(stats_fn, "r")
        self.tbsa = []
        self.tb_mn_depth = 999  # min(mx_depth) over all bins

        bn = ln = mx_tr_pkts = 00;  r_obj = None
        while True:
            flag, la = self.getline();  ln += 1
            #print("line %d %s" % (ln, flag))
            if flag == "X":  # EOF
                print("EOF REACHED")
                break
            if flag == "H":  # Header for timebin bn
                t_dest, n_traces, mx_tr_pkts = la[0:3]
                bn = int(la[-1])
                #print(">>> bn %d: msm_id %s, mx_tr_pkts %s, n_traces %s" % (
                #    bn, self.msm_id, mx_tr_pkts, n_traces))
                #if bn < first_bin or bn > last_bin:
                #    pass  #self.tbsa.append(0)
                #else:
                if bn >= first_bin and bn <= last_bin:
                    tbs = TbStats(bn, self.msm_id) ###, first_last_bin)
                    print("$$ bn=%d, making TbStats" % bn)
                    flag, la, ln = self.read_roots(tbs, ln)
                    self.tbsa.append(tbs)

                #break  # Only do one timebin
                #print("  f_bn=%d, bn=%d" % (int(f_bn), bn))
                #bn += 1
                #if bn == n_bins:  # Stop after n_bins bins
                #    print(">>> Stopping after bin %d" % bn)
                #    break
        if flag == "X":
            print("Stats file EOF reached after bin %d" % bn)                
        self.sf.close()
        print("tbsa = %s" % self.tbsa)
        for tbs_obj in self.tbsa:
            if tbs_obj.tb_mx_depth < self.tb_mn_depth:
                self.tb_mn_depth = tbs_obj.tb_mx_depth
        print("    tb_mn_depth = %d <<<<<" % self.tb_mn_depth)

if __name__ == "__main__":  # Running as main()
    sfn = c.stats_fn(c.msm_id)
    msf = MsmStatsFile(sfn, 1)
