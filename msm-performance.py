# 1551, Tue 13 Aug 2019 (NZST)
#
# msm-performance.py:  Gather performance stats per msm
#
# Copyright 2019, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own numpy (numpypy)

import numpy as np
import scipy.stats
import matplotlib.pyplot as pplt

import math, sys, datetime, collections

import dgs_ld, e_p_ni_gi

import getparams as gp  # reads -* params because this module is __main__
import config as c
c.set_pp(False, c.msm_id)  # Set prune parameters
 
# Extra command-line parameters (after those parsed by getparamas.py):
#
#   +e  check edge presence for different kinds of 'interesting' edges
#                           (-f full_graphs may be True or False)
#   +u  check sub_root presence
#   +p  plot bars for either edges or sub-roots
#   +i  to write info file of statistics for msm_ids
#
#   +b  'bare', i.e. no ASN info available
#   +n  value for min_tr_pkts
#   reqd_msms may follow the + args

# Command-line arg pasing to handle ... +e +n 60 5005
e_presence = check_sub_roots = plot_items = no_ASNs = \
    min_tr_pkts = write_info_file = False
asn_graph = c.full_graphs
reqd_msms = []


print("c.rem_cpx = %d, len(argv) = %d >%s<" % (c.rem_cpx, len(sys.argv), sys.argv))
if c.rem_cpx > 0:
    x = c.rem_cpx
    while x < len(sys.argv):
        arg = sys.argv[x]
        #print("x=%d, arg=%s" % (x, arg))
#        if arg == "+b":  # 'Bare' mode, no ASN info available
#            no_ASNs = True;  x += 1
#        elif arg == "+e":  # Check edge changes
#            e_presence = True;  x += 1
#        elif arg == "+n":  # Value for min_tr_pkts 
#            min_tr_pkts = int(sys.argv[x+1]);  x += 2
#        elif arg == "+p":  # Plot bars for edges or sub_roots
#            plot_items = True;  x += 1
#        elif arg == "+u":  # Check sUb_roots
#            check_sub_roots = True;  x += 1
        if arg == "+i":  # Write Info file
            write_info_file = True;  x += 1
        elif sys.argv[x].isdigit():
            while sys.argv[x].isdigit():
                reqd_msms.append(int(sys.argv[x]))
                x += 1
                if x == len(sys.argv):
                    break
        else:
            print("Unknown +x option (%s) !!!", arg);  exit()
if len(reqd_msms) == 0:
    reqd_msms.append(c.msm_id)
print("   reqd_msms = %s" % reqd_msms)

#if not (e_presence or check_sub_roots):
#    print("No edges|sub-roots options specified:")
#    print("  +e msm_ids  check edge presence behaviour")
#    print("  +u msm_ids  check sub-root behaviour")
#    print("  +p  Plot bars for edges or sub-root nodes\n")
#    print("  +b 'bare',  i.e. don't use ASN info")
#    print("  +n mtp  to set min_tr_pkts = mtp\n")
#    exit()

print("check_sub_roots=%s, e_presence=%s, plot_items=%s, no_ASNs=%s, min_tr_pkts=%s; reqd_msms=%s)" % (
    check_sub_roots, e_presence, plot_items, no_ASNs, min_tr_pkts, reqd_msms))
if len(reqd_msms) == 0:
    reqd_msms.append(c.msm_id)
print("Starting: c.msm_id = %s, reqd_msms = %s" % (c.msm_id, reqd_msms))

n_bins = c.n_bins*c.n_days

<<<<<<< HEAD
#def plot_stat(plt_title, stat1_data, stat2_data, stat1_name, stat2_name):
#    n_bins = len(stat1_data)
#    fig, ax1 = pplt.subplots()
#
#    ax1.set(xlabel='timebin', ylabel=stat1_name, title = plt_title)
#    xv = np.concatenate(([0], np.cumsum(np.ones(n_bins-1))))
#    ax1.grid()
#
#    colour = 'tab:red'
#    ax1.set_ylim(9100, 10000)
#    ax1.set_ylabel(stat1_name, color=colour)
#    ax1.plot(xv, stat1_data, color=colour)
#
#    ax2 = ax1.twinx()  # Share same x axis
#    colour = 'tab:blue'
#    ax2.set_ylabel(stat2_name, color=colour)
#    #ax2.set_ylim(12200, 12600)  # n_dup_traces
#    #ax2.set_ylim(1280000, 1320000)  # t_hops
#    ax2.set_ylim(128500, 132000)  # t_addrs
#    ax2.plot(xv, stat2_data, color=colour)
#
#    fig.tight_layout()
#    fig.savefig("test.svg")
#    #pplt.show()
=======
def plot_stat(plt_title, stat1_data, stat2_data, stat1_name, stat2_name):
    n_bins = len(stat1_data)
    fig, ax1 = pplt.subplots()

    ax1.set(xlabel='timebin', ylabel=stat1_name, title = plt_title)
    xv = np.concatenate(([0], np.cumsum(np.ones(n_bins-1))))
    ax1.grid()

    colour = 'tab:red'
    ax1.set_ylim(9100, 10000)
    ax1.set_ylabel(stat1_name, color=colour)
    ax1.plot(xv, stat1_data, color=colour)

    ax2 = ax1.twinx()  # Share same x axis
    colour = 'tab:blue'
    ax2.set_ylabel(stat2_name, color=colour)
    #ax2.set_ylim(12200, 12600)  # n_dup_traces
    #ax2.set_ylim(1280000, 1320000)  # t_hops
    ax2.set_ylim(128500, 132000)  # t_addrs
    ax2.plot(xv, stat2_data, color=colour)

    fig.tight_layout()
    fig.savefig("test.svg")
    #pplt.show()
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385

msm_gis = []

for msm_id in reqd_msms:
    print("===> msm_id = %d" % msm_id)
    asnf = None
    node_dir = {}  # Dictionary  IPprefix -> ASN
    no_asn_nodes = {}
    asn_ids = {"unknown":0}
    if not no_ASNs:
        asn_fn = dgs_ld.find_usable_file(c.asn_fn(msm_id))  # Read prefix->ASN from file
        if asn_fn != '':
            asnf = open(asn_fn, "r", encoding='utf-8')
            for line in asnf:
                node, asn = line.strip().split()
                node_dir[node] = asn
            #    print("node_dir key %s, val %s" % (node, node_dir[node]))
                if asn not in asn_ids:
                    asn_ids[asn] = len(asn_ids)
        else:
            print("asn file = %s <<< Couldn't find asn file" % asn_fn)
            exit()
    n_asns = len(asn_ids)-1  # Don't count "unknown"

    gi = e_p_ni_gi.GraphInfo(  # The msm_id's Graphinfo for all bins
        msm_id, node_dir, n_bins, asn_graph, n_asns, no_asn_nodes)
    #print("??? sub_roots = %s" % gi[msm_id].sub_roots)
    print("msm_id %s, len(asn_ids <===) %d" % (msm_id, len(asn_ids)))
    gi.count_edges()
    gi.count_outer_nodes()
    gi.examine_edges()
    #print("len(gi.edges) = %d" % len(gi.edges))
    msm_gis.append(gi)

s_title = "stats-%s.txt" % c.start_ymd
sf = open(s_title, "w", encoding='utf-8')
<<<<<<< HEAD
sf.write("python3 msm-performance.py -y %s -n %s -d 1 +i %s\n\n" % (
    c.start_ymd, c.n_bins, reqd_msms))
=======
sf.write("python3 msm-performance.py -y %s -n %s -d 1 +i 5017 5005 5016 5004 5006 5015\n\n" % (c.start_ymd, c.n_bins))
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385

def gi_stats(gi, a_name):
    return gi.stats[a_name]

#def print_stat(a_name, stat_fn):
#    sf.write("%14s" % a_name)  #, end="")
#    for gi in msm_gis:
#        v = stat_fn(gi, a_name)
#        mean = np.mean(v);  sd = np.std(v)
#        sf.write("%7d|%-4d " % (mean, sd))  #, end="")
#    sf.write("\n")
def print_stat(a_name, stat_fn):
    # write mean()|stddev() of statistic vector for stat_fn
    sf.write("{:>15}".format(a_name))
    for gi in msm_gis:
        v = stat_fn(gi, a_name)
        mean = np.mean(v);  iqr = scipy.stats.iqr(v)
<<<<<<< HEAD
        print("gi = %s, mean = %s, iqr = %s" % (gi.msm_id, mean, iqr))
=======
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385
        sf.write("{0:>8d}|{1:<4d}".format(int(mean), int(iqr)))
    sf.write("\n")

sf.write(' '*12)
for msm_id in reqd_msms:
    sf.write("{:>13}".format(msm_id))
sf.write("\n\n")

sf.write("{:>17}".format('destination  '))
for msm_id in reqd_msms:
    sf.write("{:^13}".format(c.msm_dests[msm_id][0]))
sf.write("\n")

sf.write("{:>17}".format('instances  '))
<<<<<<< HEAD
if c.start_ymd[0:4] == "2012":
    instances = c.msm_instances_2012
elif c.start_ymd[0:4] == "2017":
    instances = c.msm_instances_2017
elif c.start_ymd[0:4] == "2019":
    instances = c.msm_instances_2017
=======
if c.start_ymd[0:4] == "2017":
    instances = c.msm_instances_2017
elif c.start_ymd[0:4] == "2012":
    instances = c.msm_instances_2012
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385
for msm_id in reqd_msms:
    sf.write("{:^13}".format(instances[msm_id]))
sf.write("\n\n")

def n_traces_pc(gi, a_name):
<<<<<<< HEAD
    print("n_traces_pc %s:" % a_name)
    print("  n_succ_traces = %s" % gi.n_succ_traces)
    print("  n_traces = %s" % gi.n_traces)
    #return np.divide(gi.n_succ_traces*100.0, gi.n_traces)
    print(np.divide(gi.n_succ_traces, gi.n_traces))
    return np.divide(gi.n_succ_traces, gi.n_traces)
=======
    return np.divide(gi.n_succ_traces*100.0, gi.n_traces)
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385

print_stat("n_traces", gi_stats)
print_stat("trs_success", gi_stats)
print_stat("succ_traces (%)", n_traces_pc)
sf.write("\n")
print_stat("trpkts_tot", gi_stats)
print_stat("trpkts_dest", gi_stats)
sf.write("\n")
print_stat("subroots", gi_stats)
print_stat("trpkts_subroot", gi_stats)

def subroot_pc(gi, a_name):
    #print("r = %s" % np.divide(gi.n_subroot_trs*100.0, gi.trpkts_outer))
    return np.divide(gi.n_subroot_trs*100.0, gi.trpkts_outer)

print_stat("subroot_tr (%)", subroot_pc)
sf.write("\n")
print_stat("asns_tot", gi_stats)
sf.write("\n")
print_stat("edges_tot", gi_stats)
print_stat("edges_same", gi_stats)
print_stat("edges_inter", gi_stats)

def inter_as_pc(gi, a_name):
    return np.divide(gi.edges_inter*100.0, gi.edges_tot)

print_stat("edges_inter (%)", inter_as_pc) 
sf.write("\n")
print_stat("nodes_tot", gi_stats)
print_stat("nodes_1hop", gi_stats)
print_stat("nodes_outer", gi_stats)
sf.write("\n\n")
 
