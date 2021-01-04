# 1626, Wed 18 DEC 2019 (NZDT)
#
# msm-performance.py:  Gather performance stats per msm
#
# Copyright 2019, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own numpy (numpypy)

import numpy as np
import scipy.stats
import matplotlib.pyplot as pplt

import math, sys, datetime, collections

import dgs_ld, graph_info

import config as c
 
# Extra command-line parameters (after those parsed by getparamas.py):
#
#   +f  Print Full set of statistics
#   +y  List of required ymds, terminated by !
#
#   reqd_msms may follow the + args

# Command-line arg pasing to handle ... +e +n 60 5005
e_presence = check_sub_roots = plot_items = no_ASNs = \
    min_tr_pkts = write_info_file = full_stats = False

c.set_full_graphs(c.full_graphs)
reqd_ymds = [];  reqd_msms = [];  full_stats = False

pp_names = "y! m! f a mntr="  # indexes 0 to 3
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
asn_graphs = not c.full_graphs
mn_trpkts = 0
for n,ix in enumerate(pp_ix):
    if ix == 0:    # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 1:  # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 2:  # f  Print full stats
        full_stats = True
    elif ix == 3:  # a sets full_graphs F to use ASN graphs
        asn_graphs = True;  c.set_full_graphs(False)
    elif ix == 4:  # mntr  specify min trpkts
        mn_trpkts = pp_values[n]
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
if len(reqd_ymds)*len(reqd_msms) > 6:
    print("len(msms)*len(ymds) > 6 (we only print 6 cols of stats) <<<")
    exit()

original_ymds = reqd_ymds.copy()
#if len(reqd_ymds) == 1:
#    reqd_ymds = [reqd_ymds[0]] * len(reqd_msms)
print("reqd_ymds=%s, reqd_msms=%s, full_stats=%s, asn_graphs=%s\n" % (
    reqd_ymds, reqd_msms, full_stats, asn_graphs))
reqd_msms = map(int, reqd_msms)

n_bins = c.n_bins*c.n_days

def find_file(keyword, ymd, msm_id):
    filenames, rq_ntb = c.find_msm_files("asns", ymd)
    if len(filenames) == 0:
        print("No %s %d file found !!!" % (ymd, msm_id))
        exit()
    for fn in filenames:
        if fn.find(str(msm_id)) != -1:
            return fn
    return None

def get_gi(ymd, msm_id):
    print("===> ymd %s, msm_id %d" % (ymd, msm_id))
    asnf = None
    node_dir = {}  # Dictionary  IPprefix -> ASN
    no_asn_nodes = {}
    asn_ids = {"unknown":0}
    if not no_ASNs:
        #asns_fn = dgs_ld.find_usable_file(c.asns_fn(msm_id))  # Read prefix->ASN from file
        asns_fn = find_file("asns", ymd, msm_id)
        print("msm_id %d, asns_fn %s" % (msm_id, asns_fn))
        if asns_fn:
            asnf = open(asns_fn, "r", encoding='utf-8')
            for line in asnf:
                la = line.strip().split()
                node = la[0];  asn = la[1]  # Ignore la[2] (in_count)
                node_dir[node] = asn
                if asn not in asn_ids:
                    asn_ids[asn] = len(asn_ids)
            print("%d nodes, %d asns" % (len(node_dir), len(asn_ids)-1))
        else:
            print("asn file = %s <<< Couldn't find asn file" % asns_fn)
            exit()
    n_asns = len(asn_ids)-1  # Don't count "unknown"
    print("n_asns = %d" % n_asns)

    c.set_ymd(ymd)
    print("start_ymd = %s" % c.start_ymd)

    gi = graph_info.GraphInfo(  # The msm_id's Graphinfo for all bins
        msm_id, node_dir, n_bins, asn_graphs, n_asns, no_asn_nodes,
        0, mn_trpkts)  #  All depths and all trpkts
    #print("gi.depth_16 = %s" % gi.depth_16)
    #print("msm_id %s, len(asn_ids <===) %d" % (msm_id, len(asn_ids)))
    #print("len(gi.edges) = %d" % len(gi.edges))
    return gi

def print_perf_stats(msm_gis, ymds, msms):
    s_title = "msm-performance.txt"
    print("Will write file %s" % s_title)
    sf = open(s_title, "w", encoding='utf-8')
    asng_s = ''
    if asn_graphs:
        asng_s = "a "
    mntr_s = ''
    if mn_trpkts != 0:
        mntr_s = " mntr %d" % mn_trpkts
    sf.write("msm-performance.py  -n %s -d 1 + %s%s y %s ! m %s  (no pruning)\n\n" % (
        c.n_bins, asng_s, mntr_s,
        " ".join(map(str,original_ymds)), " ".join(map(str, msms))))
    
    def gi_stats(gi, a_name):
        x =  gi.stats[a_name]
        #print("gi_stats: a_name = >%s<, x = %s (%s)" % (a_name, x, type(x)))
        return gi.stats[a_name]

    def print_stat(a_name, stat_fn):
        # write mean()|stddev() of statistic vector for stat_fn
        #print("STAT: %s" % a_name)
        sf.write("{:>15}".format(a_name))
        for gi in msm_gis:
            v = stat_fn(gi, a_name)
            #print("STAT: v = %s" % v)
            mean = np.mean(v);  iqr = scipy.stats.iqr(v)
            #print("gi = %s, mean = %s, iqr = %s" % (gi.msm_id, mean, iqr))
            if iqr < 1.0:
                sf.write("{0:>9d}|{1:<5.2f}".format(int(mean), iqr))
            else:
                sf.write("{0:>9d}|{1:<5d}".format(int(mean), int(iqr)))
        sf.write("\n")

    sf.write(' '*17)
    for ymd in ymds:
        sf.write("{:^15}".format(int(ymd)))
    sf.write("\n")

    sf.write(' '*17)
    for msm_id in msms:
        sf.write("{:^15}".format(msm_id))
    sf.write("\n\n")
#    exit()
    sf.write("{:>17}".format('destination  '))
    for msm_id in msms:
        sf.write("{:^15}".format(c.msm_dests[msm_id][0]))
    sf.write("\n")
    sf.write("{:>16}".format('IPv4 address '))
    for msm_id in msms:
        sf.write("{:^15}".format(c.msm_dests[msm_id][1]))
    sf.write("\n")

    sf.write("{:>17}".format('instances  '))
    for msm_id in msms:
        sf.write("{:^15}".format(c.instances()[msm_id]))
    sf.write("\n\n")

    def n_traces_pc(gi, a_name):
        #print("gi.n_succ_traces %s" % gi.n_succ_traces)
        #print("gi.traces %s" % gi.n_traces)
        return np.divide(gi.n_succ_traces*100.0, gi.n_traces)

    print_stat("n_traces", gi_stats)
    if full_stats:
        print_stat("trs_success", gi_stats)
    print_stat("trs success (%)", n_traces_pc)
    sf.write("\n")

    print_stat("trpkts_tot", gi_stats)
    print_stat("trpkts_dest", gi_stats)
    if full_stats:
        print_stat("trpkts_38 (%)", gi_stats)
    print_stat("trpkts_27 (%)", gi_stats)
    if full_stats:
        print_stat("trpkts_9 (%)", gi_stats)
        print_stat("trpkts_3 (%)", gi_stats)
    sf.write("\n")

    print_stat("nodes_tot", gi_stats)
    print_stat("nodes_external", gi_stats)
    print_stat("nodes_internal", gi_stats)
    print_stat("nodes_1hop", gi_stats)
    sf.write("\n")

    print_stat("depth_max", gi_stats)
    if full_stats:
        print_stat("depth_16 (%)", gi_stats)
        print_stat("depth_19 (%)", gi_stats)
        print_stat("depth_25 (%)", gi_stats)
    print_stat("depth_32 (%)", gi_stats)
    sf.write("\n")

    print_stat("asns_tot", gi_stats)
    sf.write("\n")
    print_stat("edges_tot", gi_stats)
    print_stat("edges_same", gi_stats)
    if full_stats:
        print_stat("edges_inter", gi_stats)

    def inter_as_pc(gi, a_name):
        #print("gi.edges_inter %s\ngi.edges_tot %s" % (
        #    gi.bin_inter_edges, gi.tot_edges))
        return np.divide(gi.inter_asn_edges*100.0, gi.tot_edges)

    print_stat("edges_inter (%)", inter_as_pc) 
    sf.write("\n")

    print_stat("subroots", gi_stats)
    if full_stats:
        print_stat("trpkts_subroot", gi_stats)

    def subroot_pc(gi, a_name):
        #print("r = %s" % np.divide(gi.n_subroot_trs*100.0, gi.trpkts_outer))
        return np.divide(gi.n_subroot_trs*100.0, gi.trpkts_tot)

    print_stat("subroot_tr (%)", subroot_pc)
    sf.write("\n")


msm_gis = []  # GraphInfo objects for the required stats
rq_ymds = [];  rq_msms = []
for msm_id in reqd_msms:
    for ymd in reqd_ymds:
        rq_msms.append(msm_id);  rq_ymds.append(ymd)
        #print("msm_id %s ymd %s" % (msm_id, ymd))
        msm_gis.append(get_gi(ymd, msm_id))

print_perf_stats(msm_gis, rq_ymds, rq_msms)
