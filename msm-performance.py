# 1718, Sun 17 Jan 2021 (NZDT)
# 1626, Wed 18 Dec 2019 (NZDT)
#
# msm-performance.py:  Gather performance stats per msm
#
# Copyright 2021, Nevil Brownlee,  U Auckland | RIPE NCC

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

e_presence = check_sub_roots = plot_items = no_ASNs = \
    min_tr_pkts = write_info_file = full_stats = False

c.set_full_graphs(c.full_graphs)

pp_names = "y! m! f a mntr= cols= sufx!"  # indexes 0 to 6
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
asn_graphs = not c.full_graphs
cols = 0;  mn_trpkts = 0;  suffix = ""
ymd_pos = msm_pos = 99
for n,ix in enumerate(pp_ix):
    if ix == 0:    # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
        ymd_pos = n
    elif ix == 1:  # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
        msm_pos = n
    elif ix == 2:  # f  Print full stats
        full_stats = True
    elif ix == 3:  # a sets full_graphs F to use ASN graphs
        asn_graphs = True;  c.set_full_graphs(False)
    elif ix == 4:  # mntr  specify min trpkts
        mn_trpkts = pp_values[n]
    elif ix == 5:  # cols  specify cols displayed
        cols = int(pp_values[n])
    elif ix == 6:  # sufx  suffix for output file name
        suffix = "-%s" % pp_values[n][0]
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
tot_cols = len(reqd_ymds)*len(reqd_msms)
if cols == 0:  # cols not specified
    if tot_cols > 6:
        print("len(msms)*len(ymds) > 6 (can only print 6 cols of stats) <<<")
        exit()
    cols = 6  # Default 6 cols
elif cols > 6:
    print("cols > 6 (can only print 6 cols of stats) <<<")
    exit()
elif tot_cols % cols != 0:
    print("Total columns requested (%d) is not a multipe of cols (%d) <<<" % (
        tot_cols, cols))
ymd_first = ymd_pos < msm_pos
print("ymd %d, msm %d: ymd_first = %s" % (ymd_pos, msm_pos, ymd_first))

original_ymds = reqd_ymds.copy()
#if len(reqd_ymds) == 1:
#    reqd_ymds = [reqd_ymds[0]] * len(reqd_msms)
print("reqd_ymds=%s, reqd_msms=%s, full_stats=%s, asn_graphs=%s, cols=%d, suffix=>%s<\n" % (
    reqd_ymds, reqd_msms, full_stats, asn_graphs, cols, suffix))

v_spaced = False  # No blank lines between measures
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

msmida = [];  ymda = []  # Arrays for data columns
desta = [];  instancesa = []
if ymd_first:
    for ymd in reqd_ymds:
        for msm_id in reqd_msms:
            msmida.append(msm_id);  ymda.append(ymd)
            desta.append(c.msm_dests[msm_id][0])
            instancesa.append(c.ymd_instances(ymd)[msm_id])
else:
    for msm_id in reqd_msms:
        for ymd in reqd_ymds:
            msmida.append(msm_id);  ymda.append(ymd)
            desta.append(c.msm_dests[msm_id][0])
            instancesa.append(c.ymd_instances(ymd)[msm_id])

print("msmida %s" % msmida)
print("instancesa %s" % instancesa)

def print_block(msmida, ymda, desta, instancesa):
    print("print_block, msmida %s, ymda %s" % (msmida,ymda))

    msm_gia = []  # Get the gis here ti minimise the memory we use!
    for x in range(0,len(msmida)):
        msm_gia.append(get_gi(ymda[x], msmida[x]))

    def gi_stats(gi, a_name):
        #x =  gi.stats[a_name]
        #print("gi_stats: a_name = >%s<, x = %s (%s)" % (a_name, x, type(x)))
        return gi.stats[a_name]

    def print_stat(a_name, stat_fn):
        # write mean()|stddev() of statistic vector for stat_fn
        #print("STAT: %s" % a_name)
        sf.write("{:>15}".format(a_name))
        sf.write("    ")
        for gi in msm_gia:
            v = stat_fn(gi, a_name)
            #print("STAT: v = %s" % v)
            mean = np.mean(v);  iqr = scipy.stats.iqr(v)
            #print("gi = %s, mean = %s, iqr = %s" % (gi.msm_id, mean, iqr))
            if iqr < 1.0:
                sf.write("{0:>9d}:{1:<5.2f}".format(int(mean), iqr))
            else:
                sf.write("{0:>9d}:{1:<5d}".format(int(mean), int(iqr)))
        sf.write("\n")

    if ymd_first:
        sf.write(' '*17)
        for ymd in ymda:
            sf.write("{:^15}".format(int(ymd)))
        sf.write("\n")
        sf.write(' '*17)
        for msm_id in msmida:
            sf.write("{:^15}".format(msm_id))
        sf.write("\n")
    else:
        sf.write(' '*17)
        for msm_id in msmida:
            sf.write("{:^15}".format(msm_id))
        sf.write("\n")
        sf.write(' '*17)
        for ymd in ymda:
            sf.write("{:^15}".format(int(ymd)))
        sf.write("\n")
    if v_spaced:
        sf.write("\n")
    sf.write("{:>17}".format('destination  '))
    for dest in desta:
        sf.write("{:^15}".format(dest))
    sf.write("\n")
    sf.write("{:>17}".format('instances  '))
    for inst in instancesa:
        sf.write("{:^15}".format(inst))
    if v_spaced:
        sf.write("\n")
    sf.write("\n")

    def n_traces_pc(gi, a_name):
        #print("gi.n_succ_traces %s" % gi.n_succ_traces)
        #print("gi.traces %s" % gi.n_traces)
        return np.divide(gi.n_succ_traces*100.0, gi.n_traces)

    print_stat("n_traces", gi_stats)
    if full_stats:
        print_stat("trs_success", gi_stats)
    print_stat("trs success (%)", n_traces_pc)
    if v_spaced:
        sf.write("\n")

    if full_stats:
        print_stat("trpkts_tot", gi_stats)
        print_stat("trpkts_dest", gi_stats)
        print_stat("trpkts_38 (%)", gi_stats)
        print_stat("trpkts_27 (%)", gi_stats)
        print_stat("trpkts_9 (%)", gi_stats)
        print_stat("trpkts_3 (%)", gi_stats)
    if v_spaced:
        sf.write("\n")

    print_stat("nodes_tot", gi_stats)
    if full_stats:
        print_stat("nodes_distal", gi_stats)
        print_stat("nodes_internal", gi_stats)
        print_stat("nodes_1hop", gi_stats)
    if v_spaced:
        sf.write("\n")

    if full_stats:
        print_stat("depth_max", gi_stats)
        print_stat("depth_16 (%)", gi_stats)
        print_stat("depth_19 (%)", gi_stats)
        print_stat("depth_25 (%)", gi_stats)
        print_stat("depth_32 (%)", gi_stats)
    if v_spaced:
        sf.write("\n")

    print_stat("asns_tot", gi_stats)
    if v_spaced:
        sf.write("\n")
    print_stat("edges_tot", gi_stats)
    if full_stats:
        print_stat("edges_same", gi_stats)
        print_stat("edges_inter", gi_stats)

    def inter_as_pc(gi, a_name):
        #print("gi.edges_inter %s\ngi.edges_tot %s" % (
        #    gi.bin_inter_edges, gi.tot_edges))
        return np.divide(gi.inter_asn_edges*100.0, gi.tot_edges)
 
    print_stat("edges_inter (%)", inter_as_pc) 

    if full_stats:
        print_stat("subroots", gi_stats)
        print_stat("trpkts_subroot", gi_stats)

        def subroot_pc(gi, a_name):
            #print("r = %s" % np.divide(gi.n_subroot_trs*100.0, gi.trpkts_outer))
            return np.divide(gi.n_subroot_trs*100.0, gi.trpkts_tot)

        print_stat("subroot_tr (%)", subroot_pc)
    if v_spaced:
        sf.write("\n")
    sf.write("\n")

s_title = "msm-performance%s.txt" % suffix
print("Will write file %s" % s_title)
sf = open(s_title, "w", encoding='utf-8')
asng_s = ''
if asn_graphs:
    asng_s = "a "
mntr_s = "mntr %d" % mn_trpkts
sufx = ""
if suffix != "":
    sufx = "sufx %s " % suffix
if ymd_first:
    sf.write("msm-performance.py  -n %s -d 1 + %s%s y %s ! m %s %s\n\n" % (
        c.n_bins, asng_s, mntr_s,
        " ".join(map(str,original_ymds)), " ".join(map(str, reqd_msms)),
        sufx))
else:
    sf.write("msm-performance.py  -n %s -d 1 + %s%s y %s ! m %s sufx %s\n\n" % (
        c.n_bins, asng_s, mntr_s,
        " ".join(map(str, reqd_msms)),  " ".join(map(str,original_ymds)),
        suffix))

for cx in range(0,len(msmida),cols):
    print("cx loop, cx=%d" % cx)
    print_block(msmida[cx:cx+cols], ymda[cx:cx+cols], 
        desta[cx:cx+cols], instancesa[cx:cx+cols])
        #desta[cx:cx+cols], ipv4addra[cx:cx+cols], instancesa[cx:cx+cols])
