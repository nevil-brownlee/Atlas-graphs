# 1658, Sun 30 Jun 2019 (NZST)
# 1802, Thu 1 Mar 2018 (NZDT)
# 1427, Tue 1 Aug 2017 (NZST)
#
# cum-trpkts-distribution.py plot cum_trpkts
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import numpy as np
#from scipy.cluster.hierarchy import dendrogram, linkage
import matplotlib.pyplot as pplt
from matplotlib import patches
import math, datetime

import graph_info  # Edge, Path, NodeInfo and GraphInfo classes
import dgs_ld

import config as c

reqd_ymds = [];  reqd_msms = [];  pc_graph = False
pp_names = "y! m! p a"  # indexes 0 to 3
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
asn_graphs = not c.full_graphs
for n,ix in enumerate(pp_ix):
    if ix == 0:    # y  (yyyymmdd) dates
        print("y parameter read")
        reqd_ymds = pp_values[n]
    elif ix == 1:  # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 2:  # p  Convert edge counts to % of all edges
        pc_graph = pp_values[n]
    elif ix == 3:  # a sets full_graphs F to use ASN graphs
        asn_graphs = True;  c.set_full_graphs(False)
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("asn_garphs %s, reqd_ymds %s, reqd_msms %s" % (
    asn_graphs, reqd_ymds, reqd_msms))

#n_bins = 48  # 1 day
#n_bins = 48*3  # 3 days
n_bins = c.n_bins*c.n_days  # 1 week

sup_title = True

node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}

def plot_counts(pca, ids, ymd):  # Plot n_trpkts counts
    #  pca is an np 1D arrays of counts, one for each msm_id


    print("      pc_graph = %s" % pc_graph)
    #print("pca = %s" % pca)
    #print("inter_ca = %s" % inter_ca)
    pcc = []
    same_max = []
    for mx in range(0,len(pca)):
        cc = np.cumsum(pca[mx])  # Cumulative counts
        same_max.append(cc[-1])
        if pc_graph:
            ##print("cc = %s" % cc)
            ##print("icc = %s" % icc)
            tcounts = cc[-1]  # Total counts
            cc = cc*(100.0/tcounts)
        pcc.append(cc)
    which = "counts"
    if pc_graph:
        which = "percent"
    if not c.full_graphs:
        title = "ASN graph: Cumulative Node in_trpkts (%s)" % which
        pfn = "%s/inter-asn-n_trpkt-%s.svg" % (ymd, which)
    else:
        dt = c.date_from_ymd(ymd, c.start_hhmm)
        title = "Cumulative n_trpkts:  %s" % \
                dt.strftime("%a %d %b %Y (UTC)")
        pfn = "%s/cum-n_trpkts-%s.svg" % (ymd, which)
    print("pfn = %s" % pfn)

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
        xy.set_xlabel("Node n_trpkts")
        if pc_graph:
            xy.set_ylabel("% n_trpkts")
        else:
            xy.set_ylabel("n_trpkts")
        xy.tick_params(axis='x', labelsize=tkp)
        ntb = len(pcc[0])
        #print("ntb = %d, n_bins = %d" % (ntb, n_bins))
        xtick_incr = int(n_bins/8)
        xy.set_xticks(range(0,9*xtick_incr, xtick_incr))
        xy.set_xlim(-int(0.25*xtick_incr), int(8.45*xtick_incr))  # x axis lims
        xy.tick_params(axis='y', labelsize=tkp)
        if pc_graph:
            ymax = 100
        else:
            cc_max = np.max(pcc[f])
            ymax = cc_max+15
        xy.set_ylim(-2, ymax)  # y axis limits
        xy.plot(xv, pcc[f], label="%4d same ASN" % same_max[f])
        xy.legend(loc="upper left", title="Node n_trpkts", fontsize=5,
                  bbox_to_anchor=(0.03,0.99), prop={"size":7}, handlelength=1)
            # fontsize for labels, "size" for heading
        xy.grid()
    pplt.savefig(pfn)

trlo = 30000;  trhi = 1;  n_counters = 60
xlo = math.log(trlo)/math.log(10)  # For logspace() bins
xhi = math.log(trhi)/math.log(10)
bin_values = np.logspace(xlo, xhi, n_counters).astype(int)
    # trpkts values: descending order, log spacing
#print("bin_values = %s" % bin_values)

for ymd in reqd_ymds:
    c.start_ymd = ymd  # fn_ functions in config.py will use ymd <<<
    ids = [];  pca = [];  inter_ca = []
    for msm_id in reqd_msms:
        print("\n= = = = = = = = = =  %s  %d" % (ymd, msm_id))
        node_dir = {}  # Dnp.where(bin_values <= xv)[0][0]ictionary  IPprefix -> ASN
        no_asn_nodes = {};  n_asns = 0
        msm_dest = c.msm_dests[msm_id][0]

        gf = graph_info.GraphInfo(msm_id, node_dir, n_bins, asn_graphs,
            n_asns, no_asn_nodes, 0,0)  # No pruning
        print("%d has %d nodes with no asn <--" % (msm_id, len(no_asn_nodes)))
        ids.append(msm_id)

        #same_counts, inter_counts = gf.asn_edges()
        print("msm_id = %s  <<<\n" % msm_id)
        trpkt_counters = np.zeros(n_counters)

        nc = 0
        for name in gf.all_nodes:  #gf.all_nodes[] has nodes for all the bins
            n = gf.all_nodes[name]
            ta = np.average(n.icounts, None, n.icounts!=0)
            #print("%s, ta %s, in_count %s" % (name, ta, n.icounts))
            lx = np.where(bin_values <= ta)[0][0]
            #print("  lx = %3f"% lx)
            trpkt_counters[lx] += 1
            #nc += 1;  if nc == 20:
            #    print("trpkt_counters  = %s" % trpkt_counters)
            #    exit()

        cum_counts = np.cumsum(trpkt_counters)
        tot_counts = cum_counts[n_counters-1]
        for j in range(n_counters-2, 0, -1):
            if cum_counts[j] != tot_counts:
                nz_counts = j+1;  break
        print("trpkt_counters:")
        for j in range(0,nz_counts+1):
            print("%6d %6d %6d %8d" % (
                j, bin_values[j], trpkt_counters[j], cum_counts[j]))
        exit()

        pca.append(trpkt_counters[0:nz_counts+1])
        print("pca %s" % pca)
        print("inter-ca %s" % inter_ca)

    plot_asn_counts(pca, ids, ymd)  # Node n_trpkt counts
