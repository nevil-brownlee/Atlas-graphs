# 1427, Tue 1 Aug 2017 (NZST)
#
# graph-changes.py: get info about ASNs (or nodes) over timebins
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own numpy (numpypy)

import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list, dendrogram
#from scipy.cluster.hierarchy import optimal_leaf_ordering
import matplotlib.pyplot as pplt

import math, sys, datetime, collections

import dgs_ld
import e_p_ni_gi

import getparams as gp  # reads -* params because this module is __main__
import config as c
c.set_pp(False, c.msm_id)  # Set prune parameters
 
# Extra command-line parameters (after those parsed by getparamas.py):
#
#   +e  check edge presence for different kinds of 'interesting' edges
#                           (-f full_graphs may be True or False)
#   +u  check sub_root presence
#   +p  plot bars for either edges or sub-roots
#   +i  to write file of asn name msm_ids 
#
#   +b  'bare', i.e. no ASN info available
#   +n  value for min_tr_pkts
#   reqd_msms may follow the + args

# Command-line arg pasing to handle ... +e 5005 +n 60
e_presence = check_sub_roots = plot_items = no_ASNs = \
    min_tr_pkts = write_sr_file = False
asn_graph = False
dendro = True
reqd_msms = []

#dir = "."  # Base directory for RIPE graph files

#print("c.rem_cpx = %d, len(argv) = %d >%s<" % (c.rem_cpx, len(sys.argv), sys.argv))
if c.rem_cpx > 0:
    x = c.rem_cpx
    while x < len(sys.argv):
        arg = sys.argv[x]
        #print("x=%d, arg=%s" % (x, arg))
        if arg == "+b":  # 'Bare' mode, no ASN info available
            no_ASNs = True;  x += 1
        elif arg == "+e":  # Check edge changes
            e_presence = True;  x += 1
        elif arg == "+n":  # Value for min_tr_pkts 
            min_tr_pkts = int(sys.argv[x+1]);  x += 2
        elif arg == "+p":  # Plot bars for edges or sub_roots
            plot_items = True;  x += 1
        elif arg == "+u":  # Check sUb_roots
            check_sub_roots = True;  x += 1
        elif arg == "+i":  # Write sub_roots Info file
            write_sr_file = True;  x += 1
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

if not (e_presence or check_sub_roots):
    print("No edges|sub-roots options specified:")
    print("  +e msm_ids  check edge presence behaviour")
    print("  +u msm_ids  check sub-root behaviour")
    print("  +p  Plot bars for edges or sub-root nodes\n")
    print("  +b 'bare',  i.e. don't use ASN info")
    print("  +n mtp  to set min_tr_pkts = mtp\n")
    exit()

print("check_sub_roots=%s, e_presence=%s, plot_items=%s, no_ASNs=%s, min_tr_pkts=%s; reqd_msms=%s)" % (
    check_sub_roots, e_presence, plot_items, no_ASNs, min_tr_pkts, reqd_msms))
if len(reqd_msms) == 0:
    reqd_msms.append(c.msm_id)
print("Starting: c.msm_id = %s, reqd_msms = %s" % (c.msm_id, reqd_msms))

n_bins = c.n_bins*c.n_days
node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}
asn_ids = {"unknown":0}  # Dictionary of ASN ids, indexed by ASN name

def plot_bars(group, msm_id, items, bar_colour, first_ix):
    n_items = len(items)
    w = 12;  h = 8;  stp = 8.5;  tkp = 8;  tp = 12
    if group == "Sub-root":
        w = 7
    if len(items) <= 40:
        n_items = len(items);  h = 1.0 + n_items*0.2  # h = n_items*0.43
    print("n_bins=%d, n_items=%d, group = %s;  w=%d, h=%d\n" % (
        n_bins, n_items, group, w, h))
#!    fig, xy = pplt.subplots(1,1, figsize=(w,h))  # Inches (?)
    b_bord_sz = 0.3;  t_bord_sz = 0.45 # Inches
    h = b_bord_sz + n_items*0.35 + t_bord_sz
    border_bot = b_bord_sz/h
    border_top = (b_bord_sz+n_items*0.35)/h
    fig, xy = pplt.subplots(1,1, figsize=(w,h))  # Inches
###    fig = pplt.figure(figsize=(w,h))
    msm_dest = c.msm_dests[msm_id]
    title = "%s presence: msm_id %d (%s), starting at %s " % (
        group, msm_id, msm_dest[0], c.start_time.strftime("%Y-%m-%d"))
    fig.suptitle(title, fontsize=13, horizontalalignment='center')
    print("axes = %s, shape(axes) = %s" % (xy, np.shape(xy)))
    xv = np.concatenate(([0], np.cumsum(np.ones(n_bins-1))))
    xy.tick_params(axis='x', labelsize=tkp)
    gx = []        
    if n_bins == 48:  # 1 day
        pplt.subplots_adjust(bottom=border_bot, top=border_top,
                             left=0.6, right=0.87)
        xy.set_xlim(-1,49)  # x axis limits
        xy.set_xticks(range(0,9*6, 6))
        for x in range(6, 54, 6):
            gx.append(x)
        lwidth = 1.2
    elif n_bins == 96:  # 2 days
        pplt.subplots_adjust(bottom=border_bot, top=border_top,
                             left=0.5,  right=0.93)
        xy.set_xlim(-1,95)  # x axis limits
        xy.set_xticks(range(0,18*6, 12))
        for x in range(6, 108, 6):
            gx.append(x)
        lwidth = 0.8
    elif n_bins == 336:  # 1 week
        pplt.subplots_adjust(bottom=border_bot, top=border_top,
            left=0.48, right=0.97)
        xy.set_xlim(-5,340)  # x axis limits
        xy.set_xticks(range(0,8*48, 48))
        for x in range(48, 336, 48):
            gx.append(x)
        lwidth = 0.4  # Presence line width

    gy_min = np.ones(len(gx))*(-0.5)
    gy_max = np.ones(len(gx))*(n_items*1.5)
    xy.set_ylim(-0.5,n_items*1.5)  # y axis limits
    print("ylim = %.2f : %.2f" % (-0.5,n_items*1.5))
    pplt.setp(xy.get_yticklabels(), visible=False)  # Hide tick labels
    xy.yaxis.set_tick_params(size=0) # Hide y ticks
    hy = []  # Draw horizontal and vertical lines for grid
    for f in range(n_items+1):
        hy.append(f*1.5 + 0.5)
    print("n_items=%d, hy=%s" % (n_items, hy))
    hx_min = np.ones(len(hy))*(-5.0)
    hx_max = np.ones(len(hy))*340.0  # Box is 340 wide (for all n_bins)
    xy.hlines(hy, hx_min, hx_max, linewidth=0.2, color='black')
    xy.vlines(gx, gy_min, gy_max, linewidth=0.2, color='black')

    for f in range(n_items):
        if first_ix+f >= n_items:
            break
        pa = items[first_ix+f].pv  # Presence array
        nn = items[first_ix+f].plot_label
        ##print("plot(): e=%s" % e)
        offset = f*1.5
        b_width = 0.1
        ymin = np.ones(336)*offset
        ymax = np.add(pa, offset)
        xy.vlines(xv, ymin, ymax, linewidth=lwidth, color=bar_colour)
        xy.text(-8, offset+0.3, nn, fontsize=stp,
#        xy.text(-12, offset+0.3, nn, fontsize=stp,
                horizontalalignment='right')  # Axis units

    pfn = "%s/%d-%s-presence-%d.pdf" % (
        c.start_ymd, msm_id, group, first_ix)
    print("save to %s" % pfn)
    pplt.savefig(pfn)

def reorder_list(items_list):
    if len(items_list) < 4:
        for e in items_list:
            pva.append(e.pv)
        return pva

    def linkage_order(items_list):
        pva = []  # Original order
        for e in items_list:
            pva.append(e.pv)

        def ev_dist(pv1, pv2):  # Distance metric for clustering
            dist = np.sum(pv1 != pv2)  # Different
            #return dist
            dist2 = np.sum(pv1 != np.logical_not(pv2))  # Present in gaps
            if dist2 < dist:
                return dist2
            return dist

        Z = linkage(pva, method='single', metric=ev_dist)  #'euclidean')
            # pva must be a 1d condensed distance matrix
        # Z[i, 0] and Z[i, 1] are combined to form cluster n + i.
        # index less than n corresponds to one of the original observations.
        # distance between clusters Z[i, 0] and Z[i, 1] is given by Z[i, 2]. 
        # fourth value Z[i, 3] = nbr of original observatns in the new cluster.
        n = len(items_list)
        print("\nitems_list has %d edges, there were %d iterations" % (
            n, len(Z)))
        diff_order = []
        for j in range(n-1):
            e0 = int(Z[j,0]);   e1 = int(Z[j,1])
            if e0 < n and e0 not in diff_order:
                diff_order.append(e0)
            if e1 < n and not e1 in diff_order:
                diff_order.append(e1)
        print("diff_order=%s, len(diff_order)=%d\n" % (
            diff_order, len(diff_order)))

        pvr = [];  pvr_items = []  # Re-ordered
        for j in range(0,len(diff_order)):
            this_ix = diff_order[j]
            pvr.append(items_list[this_ix])
        return pvr

    svr_items = linkage_order(items_list)
        
    sublists = collections.OrderedDict();
    for item in svr_items:
        if item.asn in sublists:
            sublists[item.asn].append(item)
        else:
            sublists[item.asn] = [item]

    new_items_list = []
    for sk in sublists.keys():  # Find the single ASNs
        sl = sublists[sk]
        if len(sl) == 1:
            new_items_list = sl + new_items_list  # Prepend to new_items_list

    for sr in new_items_list:  # Pop the singles
        sublists.pop(sr.asn)

    for key,value in sublists.items():
        new_items_list = value +  new_items_list  # Prepend to new_items_list
    return new_items_list

item_info = {}  # Directory of "item asn" strings

for msm_id in reqd_msms:
    print("===> msm_id = %d" % msm_id)
    asnf = None
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

    msm_dest = c.msm_dests[msm_id][0]
    n_asns = len(asn_ids)-1  # Don't count "unknown"
    gi = e_p_ni_gi.GraphInfo(  # The msm_id's Graphinfo for all bins
        msm_id, node_dir, n_bins, asn_graph, n_asns, no_asn_nodes)
    #print("??? sub_roots = %s" % gi.sub_roots)

    if check_sub_roots:
        srs = {}  # SubRoots for this msm_id
        for k in gi.sub_roots.keys():
            sr = e_p_ni_gi.SubRoot(k, gi.sub_roots[k], gi.sub_root_counts[k])
            #print("sr name=%s, sr_nz_counts=%s" % (sr.name, sr.nz_counts))
            key = "%5d %s" % (sr.nz_counts, sr.name)
            srs[key] = sr  # Key (for sorting) saved here

        n_kept = 0
        sr_list = []
        for k in sorted(srs.keys(), reverse=True):
            sr = srs[k];
            name = sr.name
            sub_roots = sr.sub_roots;  sub_root_counts = sr.sub_root_counts
            nz_counts = sr.nz_counts;  max_count = sr.max_count
            n_oruns = sr.n_oruns;  mx_orun = sr.mx_orun
            n_subruns = sr.n_subruns;  mx_subrun = sr.mx_subrun
            if (nz_counts >= n_bins*0.5 and max_count >= 30) or \
               (n_subruns < n_bins*0.5 and mx_subrun >= n_bins*0.15):
                sr.asn =  node_dir[sr.name]
                sr_label = "%s    %s  %4d pkts " % (
                    node_dir[sr.name], sr.name, sr.av_count)
                sr.pv = sr.sub_roots###;  sr.plot_label = sr_label
                sr.plot_label = sr_label
                sr_list.append(sr)
                print("name %s: nz_counts %d, max_count %d, n_oruns %d, mx_orun %d,  n_subruns %d, mx_subrun %d, av_count %d" % ( 
                    name, nz_counts, max_count, n_oruns, mx_orun, n_subruns, mx_subrun, sr.av_count))
                print("=== counts %s" % sub_root_counts)
                print("--- sub_roots %s" % sr.sub_roots)
                
        print("%d sr nodes kept" % len(sr_list))
        sr = reorder_list(sr_list)
        if write_sr_file:
            for item in sr:
                item_key = "%22s %15s" % (item.asn, item.name)
                if item_key not in item_info:
                    item_info[item_key] = []
                item_info[item_key].append(str(msm_id))

        if plot_items:
            plot_bars("Sub-root", msm_id, sr, "red", 0)

#        #print("%d has %d nodes with no asn <--" % (msm_id, len(no_asn_nodes)))

    elif e_presence:  # Check edge presence (for bar plots)
        ids = [];  pca = []
        msm_dest = c.msm_dests[msm_id][0]

        def print_stats(e, ix, ac):
            av_orun = np.average(e.ora_len)
            av_zrun = np.average(e.zra_len)
            av_ms = av_orun/av_zrun
            print("%d: %d  ones=%d, n_oruns=%d, n_zruns=%d, mx_orun=%d, mx_zrun=%d, av_orun=%.2f, av_zrun=%.2f, av_ms=%.2f\n%s" % (
                ix, msm_id, e.n_ones, e.n_oruns, e.n_zruns, e.mx_orun, e.mx_zrun, av_orun, av_zrun, av_ms,
                    e.ps))
            if ac:
                print("ac = %s" % gi.acor(e.present))

        def print_counts(counts, msm_dest, msm_id):
            print("Dest Name & Dest ID & Total & Other & Correlated & Interrupted &Stable \\\\")
            tot = counts[0];  pc = []
            print("counts = %s" % counts)
            pc_m = 100.0/tot
            for j in range(1,8):
                pc.append(counts[j]*pc_m)
            other_pc = pc[0] + pc[1] + pc[2] + pc[3]
            print("%11s & %d & %4d & %5.1f\\%% & %5.1f\\%% & %5.1f\\%% & %5.1f\\%% \\\\" % (
                msm_dest, msm_id, tot, other_pc, pc[4], pc[5], pc[6]))

        n_stable = gi.examine_edges()  # Compute stats values for each Edge
                # Also makes list of 'interesting' edges in gi.all_edges
        interest1, recurrent, total = gi.classify_edges()
            # Returns lists of edges showinf 'interesting' and 'recurrent'
            # total = number of all classified edges (not just above two kinds)
        n_unclassified = len(gi.all_edges)-total
        if n_unclassified != 0:
            print("!!!!!! %d unclassified !!!!!!" % n_unclassified)            

        if len(gi.all_edges) < 5:
            print("\nOnly %d edges were 'interesting' !!!" % len(all_edges))
            

        def make_items_list(msm_id, edges):
            print("msm_id %d has %d edges" % (
                msm_id, len(edges)))
            if len(edges) <= 2:
                print("  >>> not enough to plot")
                return
            eva = []  # 2d array of observation vectors
            for j,e in enumerate(edges):
                da = np.concatenate(([j], e.present))
                if no_ASNs:
                    nn = "%s->%s %4d pkts " % (e.n_from, e.n_to, e.av_icount)
                elif c.full_graphs:
                    nn = "%s->%s   (%s->%s) %5d pkts " % (
                        e.asn_from, e.asn_to, e.n_from, e.n_to, e.av_icount)
                else:
                    nn = "%s->%s %5d pkts " % (
                        e.n_from, e.n_to, e.av_icount)
                e.plot_label = nn;  e.pv = e.present
                eva.append(e)
            return eva
        
        edges = make_items_list(msm_id, interest1)

        if edges and plot_items:
            re, re_labels = reorder_list(edges)
            plot_bars("Edge", msm_id, re, re_labels, "blue", 0)
    
    ## https://docs.scipy.org/doc/scipy/reference/cluster.hierarchy.html
    
if write_sr_file:
    info_f = open("%s/sr-info.txt" % c.start_ymd, "w")
    for item in sorted(item_info):
        info_f.write("%s  %s\n" % (item, " ".join(item_info[item])))
    info_f.close()
