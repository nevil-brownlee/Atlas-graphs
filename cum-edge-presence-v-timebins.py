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

import graph_info  # Edge, Path, NodeInfo and GraphInfo classes
import dgs_ld

import config as c

reqd_ymds = [];  reqd_msms = [];  pc_graph = False
pp_names = "y! m! p a"  # indexes 0 to 3
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default parameters for drawing
mn_trpkts = c.draw_mn_trpkts
asn_graphs = not c.full_graphs
for n,ix in enumerate(pp_ix):
    if ix == 0:    # y  (yyyymmdd) dates
        print("y parameter read")
        reqd_ymds = pp_values[n]
    elif ix == 1:  # m  (50xx) msm_ids
        reqd_ymds = c.check_msm_ids(pp_values[n])
    elif ix == 2:  # p  Convert edge counts to % of all edges
        pc_graph = pp_values[n]
    elif ix == 3:  # a sets full_graphs F to use ASN graphs
        asn_graphs = True;  c.set_full_graphs(False)
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("reqd_ymds %s, reqd_msms %s" % (reqd_ymds, reqd_msms))

#n_bins = 48  # 1 day
#n_bins = 48*3  # 3 days
n_bins = c.n_bins*c.n_days  # 1 week

sup_title = True

node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}

def plot_asn_counts(pca, inter_ca, ids, ymd):  # Plot counts (nbr of times pc[x] was seen)
    #  pca and inter_ca are np 1D arrays of counts, one for each msm_id
    #ymax = {5017:80, 5005:145, 5016:100, 5004:920, 5006:1270, 5015:1030}  # y axis upper limits
    xv = np.cumsum(np.ones(n_bins+1))  # x values
    #print("      xv = %s" % xv)
    print("      pc_graph = %s" % pc_graph)
    #print("pca = %s" % pca)
    #print("inter_ca = %s" % inter_ca)
    pcc = [];  inter_cc = []
    same_max = [];  inter_max = []
    for mx in range(0,len(pca)):
        cc = np.cumsum(pca[mx])  # Cumulative counts
        icc = np.cumsum(inter_ca[mx])
        same_max.append(cc[-1]);  inter_max.append(icc[-1])
        if pc_graph:
            ##print("cc = %s" % cc)
            ##print("icc = %s" % icc)
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
        pfn = "%s/inter-asn-full-%s.svg" % (ymd, which)
    else:
        dt = c.date_from_ymd(ymd, c.start_hhmm)
        title = "Cumulative Edge Presence:  %s" % \
                dt.strftime("%a %d %b %Y (UTC)")
        pfn = "%s/cum-edge-presence-%s.svg" % (ymd, which)
    print("pfn = %s" % pfn)

    if len(ids) <= 3:
        rows = 1;  cols = len(ids)
        w = 8;  h = 3.4;  stp = 12;  tkp = 7;  tp = 12
    else:
        rows = 2;  cols = int(len(ids)/2)
        w = 8;  h = 6;  stp = 12;  tkp = 7;  tp = 12
    #print("+1+ pc %s, len(ids) %d, rows %d, cols %d" % (pc_graph, len(ids), rows, cols))

    if sup_title:
        fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches
        if len(ids) <= 3:
            pplt.subplots_adjust(left=0.125, bottom=0.135, right=None, top=0.9,
                                 wspace=0.5, hspace=0.85)
        else:
            pplt.subplots_adjust(left=0.125, bottom=0.08, right=None, top=0.9,
                                 wspace=0.5, hspace=0.35)
        fig.suptitle(title, fontsize=14, horizontalalignment='center')
    else:
        fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches
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
            ymax = 80  #? 70
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

for ymd in reqd_ymds:
    c.start_ymd = ymd  # fn_ functions in config.py will use ymd <<<
    ids = [];  pca = [];  inter_ca = []
    for msm_id in reqd_msms:
        print("\n= = = = = = = = = =  %s  %d" % (ymd, msm_id))
        node_dir = {}  # Dictionary  IPprefix -> ASN
        no_asn_nodes = {}
        asn_ids = {"unknown":0}  # Dictionary of ASN ids, indexed by ASN name
        asns_fn = dgs_ld.find_usable_file(c.asns_fn(msm_id))
        if asns_fn != '':  # Read prefix->ASN from file
            asnf = open(asns_fn, "r", encoding='utf-8')
            n_nodes = 0
            for line in asnf:
                la = line.strip().split()
                name = la[0];  asn = la[1]
                node_dir[node] = asn;  n_nodes += 1
            #    print("node_dir key %s, val %s" % (node, node_dir[node]))
                if asn not in asn_ids:
                    asn_ids[asn] = len(asn_ids)
            print("asns file has %d nodes and %d asns" % (n_nodes, len(node_dir)))
        else:

            print("asn file = %s <<< Couldn't find an asns file" % asns_fn)
            exit()
        no_asn_nodes = {}
        msm_dest = c.msm_dests[msm_id][0]
        n_asns = len(asn_ids)-1  # Don't count "unknown"
        print(">>> n_asns = %d, n_nodes = %d" % (n_asns, len(node_dir)))

        gf = graph_info.GraphInfo(msm_id, node_dir, n_bins, asn_graphs,
            n_asns, no_asn_nodes, 0,0)  # No pruning
        print("%d has %d nodes with no asn <--" % (msm_id, len(no_asn_nodes)))
        ids.append(msm_id)

        same_counts, inter_counts = gf.asn_edges()
        print("msm_id = %s  <<<\n" % msm_id)
        #print("same_counts = %s\n" % same_counts)
        #print("inter_counts = %s\n" % inter_counts)
        pca.append(same_counts);  inter_ca.append(inter_counts)
        print("pca %s" % pca)
        print("inter-ca %s" % inter_ca)

    plot_asn_counts(pca, inter_ca, ids, ymd)  # Inter- Same-AS Edge comparisons

