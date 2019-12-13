# 1658, Sun 30 Jun 2019 (NZST)
# 1802, Thu 1 Mar 2018 (NZDT)
# 1427, Tue 1 Aug 2017 (NZST)
#
# cum_edge-presence-v-timebins.py: plot cum_edge_presence
#
# Copyright 2018, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
import matplotlib.pyplot as pplt
from matplotlib import patches
import math, datetime

import e_p_ni_gi  # Edge, Path, NodeInfo and GraphInfo classes
import dgs_ld

import config as c
c.set_pp(False, c.msm_id)  # Work on graphs-* file
 
#n_bins = 48  # 1 day
#n_bins = 48*3  # 3 days
n_bins = c.n_bins*c.n_days  # 1 week

pc_graph = True   # Convert edge counts to % of all edges
inter_asn = True
sup_title = True

#asn_fn = c.asn_dests_fn(c.msm_id)
#print("asn_fn = %s" % asn_fn)
#r = dgs_ld.find_usable_file(asn_fn)
#print("r = >%s<" % r)
#exit()

node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}
##if not c.full_graphs:  # Read ASN -> prefix mapping from file
if c.full_graphs:  # Read prefix -> ASN mapping from file
    for msm_id in c.msm_nbrs:
        asn_fn = c.asn_dests_fn(msm_id)
        print("asn file = %s <<<<<<" % asn_fn)
        af = dgs_ld.find_usable_file(asn_fn)
        print("      af = %s" % af)
        asnf = open(af, "r", encoding='utf-8')
        for line in asnf:
            node, asn = line.strip().split()
            node_dir[node] = asn
            #print("node_dir key %s, val %s" % (node, node_dir[node]))

def plot_asn_counts(pca, inter_ca, ids):  # Plot counts (nbr of times pc[x] was seen)
    #  pca and inter_ca are np 1D arrays of counts, one for each msm_id
    #ymax = {5017:80, 5005:145, 5016:100, 5004:920, 5006:1270, 5015:1030}  # y axis upper limits
    xv = np.cumsum(np.ones(n_bins+1))  # x values
    #print("      xv = %s" % xv)
    #print("      pc_graph = %s" % pc_graph)
    pcc = [];  inter_cc = []
    same_max = [];  inter_max = []
    for mx in range(0,len(pca)):
        cc = np.cumsum(pca[mx])  # Cumulative counts
        icc = np.cumsum(inter_ca[mx])
        same_max.append(cc[-1]);  inter_max.append(icc[-1])
        if pc_graph:
            tcounts = cc[-1]+icc[-1]  # Total counts
            cc = cc*(100.0/tcounts)
            icc = icc*(100.0/tcounts)
        pcc.append(cc)
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
                c.start_time.strftime("%a %d %b %Y (UTC)")
        pfn = "inter-asn-%s.svg" % which

    if len(ids) <= 3:
        rows = 1;  cols = len(ids)
        w = 8;  h = 3.4;  stp = 12;  tkp = 7;  tp = 12
    else:
        rows = 2;  cols = int(len(ids)/2)
        w = 8;  h = 6;  stp = 12;  tkp = 7;  tp = 12
    #print("+1+ pc %s, len(ids) %d, rows %d, cols %d" % (pc_graph, len(ids), rows, cols))

    if sup_title:
        fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches (?)
        if len(ids) <= 3:
            pplt.subplots_adjust(left=0.125, bottom=0.135, right=None, top=0.9,
                                 wspace=0.5, hspace=0.85)
        else:
            pplt.subplots_adjust(left=0.125, bottom=0.08, right=None, top=0.9,
                                 wspace=0.5, hspace=0.35)
        fig.suptitle(title, fontsize=14, horizontalalignment='center')
    else:
        fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches (?)
        if len(ids) <= 3:
            pplt.subplots_adjust(left=0.125, bottom=0.135, right=None, top=0.9,
                                 wspace=0.5, hspace=0.85)
        else:
            pplt.subplots_adjust(left=0.125, bottom=0.07, right=None, top=0.8,
                                 wspace=0.5, hspace=0.35)

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
            ymax = 70
        else:
            cc_max = np.max(pcc[f])
            icc_max = np.max(inter_cc[f])
            if icc_max > cc_max:
                cc_max = icc_max
            ymax = cc_max+15
        ##xy.set_ylim(-2,ymax[msm_id])  # x axis limits
        xy.set_ylim(-2, ymax)  # y axis limits
        xy.plot(xv, pcc[f], label="%4d same ASN" % same_max[f])
        xy.plot(xv, inter_cc[f], label="%4d inter-ASN" % inter_max[f])
        xy.legend(loc="upper left", title="Edge type", fontsize=5,
                  bbox_to_anchor=(0.03,0.99), prop={"size":7}, handlelength=1)
            # fontsize for labels, "size" for heading
        xy.grid()
    pplt.savefig(pfn)


ids = [];  pca = [];  inter_ca = []
#for msm_id in c.msm_nbrs:
#for msm_id in [5005]:  # 5004]:
#for msm_id in [5017, 5005, 5016]:
for msm_id in [5017, 5005, 5016, 5004, 5006, 5015]:
    print("= = = = = = = = = =")
    all_edges = []  # List of all 'interesting' edges for all msm_ids
    msm_dest = c.msm_dests[msm_id][0]
    
    gf = e_p_ni_gi.GraphInfo(msm_id, all_edges, node_dir, n_bins)
    print("%d has %d nodes with no asn <--" % (msm_id, len(no_asn_nodes)))
    #if len(no_asn_nodes) != 0:
    #    print("   %s <==" % no_asn_nodes)
    ids.append(msm_id)
    if inter_asn:
        same_counts, inter_counts = gf.asn_edges()
        pca.append(same_counts);  inter_ca.append(inter_counts)
    else:
        p_counts = gf.count_edges()
        pca.append(p_counts)
    ##print("msm_id %s, inter_ca %s" % (msm_id, inter_ca))

plot_asn_counts(pca, inter_ca, ids)  # Inter- Same-AS Edge comparisons
