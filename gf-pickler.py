# 1617, Wed 24 Feb 2021 (NZDT)
# 1658, Sun 30 Jun 2019 (NZST)
# 1802, Thu  1 Mar 2018 (NZDT)
# 1427, Tue  1 Aug 2017 (NZST)
#
# cum_edge-presence-v-timebins.py: plot cum_edge_presence
#
# Copyright 2021, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
import matplotlib.pyplot as pplt
from matplotlib import patches
from mpl_toolkits import mplot3d
import math, datetime, pickle

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
print("reqd_ymds %s, reqd_msms %s" % (reqd_ymds, reqd_msms))

#n_bins = 48  # 1 day
#n_bins = 48*3  # 3 days
n_bins = c.n_bins*c.n_days  # 1 week

sup_title = False

node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}

for ymd in reqd_ymds:
    c.start_ymd = ymd  # fn_ functions in config.py will use ymd <<<
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
                node_dir[name] = asn;  n_nodes += 1
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

        pfn = c.pickle_fn(ymd, msm_id)
        print("will write %s" % pfn)
        pf = open(pfn, "wb")
        pickle.dump(gf, pf)
        pf.close()
