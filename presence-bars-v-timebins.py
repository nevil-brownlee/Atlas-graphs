# 1623, Thu 12 Nov 2020 (NZDT)
# 1745, Thu  3 Sep 2020 (NZST)
# 1636, Tue 31 Mar 2020 (NZDT)
# 1802, Thu  1 Mar 2018 (NZDT)
# 1427, Tue  1 Aug 2017 (NZST)
#
# presence-bars-v-timebins.py: 
#   plot bars for edges, ASNs or subroots over timebins
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
import scipy.stats
import matplotlib.pyplot as pplt
import matplotlib.cm as cm

#print("np.__version__ = %s" % np.__version__);  exit()
#import matplotlib.colors
#from matplotlib import cm
from matplotlib import patches

import math, datetime, sys, collections, os
import operator as op
from functools import reduce
import ipaddress
import colorsys

import dgs_ld
import graph_info as grin

import config as c

# Extra command-line parameters (after those parsed by getparamas.py):
#
#   n  check edge presence for different kinds of 'interesting' nodes
#                           (-f full_graphs may be True or False)
#   e  check edge presence for different kinds of 'interesting' edges
#   s  check sub_root presence
#
#   p  plot bars for either edges or sub-roots
#   mntr v  set mn_trpkts to v
#
#   b  'bare', i.e. no ASN info available
#
#   reqd_msms may follow the + args

asn_graphs = False
n_presence = dn_presence = e_presence = e_variance = sr_presence =\
    in_to_dest = plot_items = walk_graph = no_ASNs = False

pp_names = " m! y! a mxd= mntr= n d e v s i p w"  # indexes 0 to 13
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default paremeters for drawing
mn_trpkts = c.draw_mn_trpkts
reqd_ymds = reqd_msms = []
asn_graphs = not c.full_graphs
for n,ix in enumerate(pp_ix):
    if ix == 0:     # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:   # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 2:   # a sets full_graphs F to use ASN graphs
        asn_graphs = True;  c.set_full_graphs(False)
    elif ix == 3:   # mxd  specify max depth
        mx_depth = pp_values[n]
    elif ix == 4:   # mntr specify min trpkts
        mn_trpkts = pp_values[n]
    elif ix == 5:   # n  Check Node changes
        n_presence = True
    elif ix == 6:   # d  Check distal node changes
        dn_presence = True
    elif ix == 7:   # e  Check edge changes
        e_presence = True
    elif ix == 8:   # v  Check edge variance
        e_variance = True
    elif ix == 9:   # s  Check sub_roots
        s_presence = True
    elif ix == 10:  # i  Plot incount for dest node
        in_to_dest = True
    elif ix == 11:  # p  Plot bars for edges or sub_roots
        plot_items = True
    elif ix == 12:  # w  Walk graph
        walk_graph = True
    else:
        exit()
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_ymds) > 1:
    print("More than one ymd specified!");  exit()
print("reqd_ymds = %s, reqd_msms = %s" % (reqd_ymds, reqd_msms))

if not (n_presence or e_presence or dn_presence or e_variance or \
        sr_presence or in_to_dest or walk_graph):
    print("No edges|sub-roots options specified:")
    print("  n  check node presence behaviour")
    print("  d  check distal node presence behaviour")
    print("  e  check edge presence behaviour")
    print("  v  check edge in_count variation behaviour")
    print("  s  check sub-root behaviour")
    print("  p  plot bars for edges or sub-root nodes\n")
    print("  w  walk graph")
    print("  a  use ASN graphs (instead of node graphs)")
    print("  mntr v  Filter out n/e/r items with tr_pkts < v")
    print("  b  'bare',  i.e. don't use ASN info")
    exit()

print("asn_graphs=%s, e_presence=%s, dn_presence=%s, e_variance=%s, \
sr_presence=%s,\n    in_to_dest=%s, plot_items=%s, walk_graph=%s" % (
     asn_graphs, e_presence, dn_presence, e_variance,
     sr_presence, in_to_dest, plot_items, walk_graph))
print("Starting: c.msm_id = %s, reqd_msms = %s" % (c.msm_id, reqd_msms))

#n_bins = 48  # 1 day   ########### 
#n_bins = 48*3  # 3 days
n_bins = c.n_bins*c.n_days  # 1 week
#print("$$$ n_bins = %d" % n_bins)

pc_graph = False  #True   # Convert edge counts to % of all edges
inter_asn = True

node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}

def plot_bars(group, msm_id, items, bar_colour, first_ix):
    # bar_colour = str to plot solid-colour bars, otherwise assume cmap
    n_items = len(items)
    #w = 12;  h = 8;  stp = 8.5;  tkp = 8;  tp = 12
    w = 8;  h = 11;  stp = 8.5;  tkp = 8;  tp = 12  # A4 210×297 mm 8.3×11.7"
    if group == "Sub-root":
        w = 7
    if n_items == 0:
        print("!!! No sub-roots to plot !!!")
        return
    if n_items <= 40:
        n_items = len(items);  h = 1.0 + n_items*0.2  # h = n_items*0.43
    #print("n_bins=%d, n_items=%d, group = %s;  w=%d, h=%d\n" % (
    #    n_bins, n_items, group, w, h))
#!    fig, xy = pplt.subplots(1,1, figsize=(w,h))  # Inches (?)
    b_bord_sz = 0.3;  t_bord_sz = 0.45 # Inches
    h = b_bord_sz + n_items*0.35 + t_bord_sz
    border_bot = b_bord_sz/h
    border_top = (b_bord_sz+n_items*0.35)/h
    print(">>> n_items = %d, = %.2f, top = %.2f, bot = %.2f" % (
        n_items, h, border_top, border_bot))
    fig, xy = pplt.subplots(1,1, figsize=(w,h))  # Inches
###    fig = pplt.figure(figsize=(w,h))
    msm_dest = c.msm_dests[msm_id]
    asn_s = ""
    if asn_graphs:
        asn_s = "ASN "
    print("asn_graphs %s, asn_s >%s<" % (asn_graphs, asn_s))
    title = "%s%s: %s, msm_id %d (%s), mntr %d " % (
        asn_s, group, c.start_time.strftime("%Y-%m-%d"), 
        msm_id, msm_dest[0], mn_trpkts)
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
        lwidth = 1.3
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

    variance_plot = not(isinstance(bar_colour, str))
    print("variance_plot = %s" % variance_plot)
    cmap = bar_colour
    for f in range(n_items):
        if first_ix+f >= n_items:
            break
        it = items[first_ix+f]
        pa = it.pv  # Presence array
        nn = it.plot_label
        offset = (n_items-1-f)*1.5  # Increasing difference order from top down
        b_width = 0.1
        ymin = np.ones(n_bins)*offset
        ymax = np.add(ymin, np.where(it.icounts!=0, 1, 0))
                    # 1 for non-zero icounts, 0 otherwise
        e = it  # edge to plot
        if variance_plot:
            ec = dgs_ld.EdgeColour()
            bin_colours = [ec.unchanging_colour]
            for bn in range(1,n_bins):
                h,s,v = ec.hsv_colour(e.bcps[bn], ec.h_blue, ec.h_red)
                bin_colours.append(colorsys.hsv_to_rgb(h,s,v))
            xy.vlines(xv, ymin, ymax, linewidth=lwidth, color=bin_colours)
        else:
            xy.vlines(xv, ymin, ymax, linewidth=lwidth, color=bar_colour)

        xy.text(-8, offset+0.3, nn, fontsize=stp,
                horizontalalignment='right')  # Axis units

    ns_group = group.replace(" ", "")
    if asn_graphs:
        pfn = "%s/%d-%d-%s%s-%d.pdf" % (
            c.start_ymd, msm_id, mn_trpkts, c.asn_prefix, ns_group, first_ix)
    else:  # asn_prefix is null
        pfn = "%s/%d-%d-%s-%d.pdf" % (
            c.start_ymd, msm_id, mn_trpkts, ns_group, first_ix)

    print("save to %s" % pfn)
    pplt.savefig(pfn)

def reorder_list(items_list, dist_fn):
    pva = []
    if len(items_list) < 4:
        for it in items_list:
            pva.append(it)
        return pva

    def nCr(n, r):  # Compute binomial coefficient
        r = min(r, n-r)
        num = reduce(op.mul, range(n, n-r, -1), 1)
        denom = reduce(op.mul, range(1, r+1), 1)
        return num // denom  # Avoid div by zero

    def find_nc_size(sz):
        k = 200  # Find first k for which nCr(k,2) > sz
        while True:
            n = nCr(k,2)
            if n == sz:
                rq_sz = nCr(k,2);  break
            elif n < sz:
                rq_sz = nCr(k+1,2); break
            k -= 1
        #print("Found rq_sz = %d" % rq_sz)
        return rq_sz

    #class EdgePV:
    #    def __init__(self, s, d, pv):
    #        self.s = s;  self.d = d;  self.pv = pv 

    ## https://docs.scipy.org/doc/scipy/reference/cluster.hierarchy.html
    
    def linkage_order(items_list):
        pva = []  # Original order
        for it in items_list:
            pva.append(it.pv)  # general, i.e. ust use obj.pv
            #print(e)  ##############################
        rq_sz = find_nc_size(len(pva))
        print("%d items to order (rq_sz = %d)" % (len(items_list), rq_sz))
        epv = np.zeros(len(pva[0]))  # Empty presence vector
        while len(pva) <= rq_sz:
            pva.append(epv)
        print("len(pva) now = %d" % len(pva))

        Z = linkage(pva, method='single', metric=dist_fn)
            # pva must be a 1d condensed distance matrix

        # Z[i, 0] and Z[i, 1] are combined to form cluster n + i.
        # index less than n corresponds to one of the original observations.
        # distance between clusters Z[i, 0] and Z[i, 1] is given by Z[i, 2]. 
        # fourth value Z[i, 3] = nbr of original observatns in the new cluster.
        n = len(items_list)
        print("\nitems_list has %d edges, there were %d iterations" % (
            n, len(Z)))
        diff_order = []
        for j in range(len(Z)):
            it0 = int(Z[j,0]);   it1 = int(Z[j,1])
            if it0 < n and it0 not in diff_order:
                diff_order.append(it0)
            if it1 < n and not it1 in diff_order:
                diff_order.append(it1)
        print("len(diff_order)=%d\n" % len(diff_order))

        pvr = []  # Re-ordered
        #for j in range(0,len(diff_order)):
        ne = 35
        if len(diff_order) < ne:
            ne = len(diff_order)
        for j in range(0,ne-1):
            this_ix = diff_order[j]
            pvr.append(items_list[this_ix])
        #print("@@ pvr = %s" % pvr)
        return pvr

    svr_items = linkage_order(items_list)
    print("back from linkage_order(), len(svr_items) = %d" % len(svr_items))
    for n,svk in enumerate(svr_items):  
        print("%3d %s" % (n,svk))  ##### OK to here ######  <- Items
    return svr_items

    sublists = collections.OrderedDict();
    for item in svr_items:
        if item.asn in sublists:  # One sublist per ASN
            sublists[item.asn].append(item)
        else:
            sublists[item.asn] = [item]

    new_items_list = []
    for sk in sublists.keys():  # Find the single ASNs
        sl = sublists[sk]
        if len(sl) == 1:
            new_items_list = sl + new_items_list  # Prepend to new_items_list

    for sr in new_items_list:  # Pop the ASNs with only one edge
        sublists.pop(sr.asn)

    for key,value in sublists.items():
        new_items_list = value +  new_items_list  # Prepend to new_items_list
    return new_items_list

def read_asns_file(msm_id, asn_ids):
    asns_fn = dgs_ld.find_usable_file(c.asns_fn(msm_id))
    print("read_asns_file(%s), asns_fn = %s" % (msm_id, asns_fn))
    if os.path.isfile(asns_fn):
        no_asn_nodes = 0
        asnf = open(asns_fn, "r", encoding='utf-8')
        for line in asnf:
            la = line.strip().split()
            name = la[0];  asn = la[1]
            node_dir[name] = asn
            #print("node_dir key %s, val %s" % (name, node_dir[name]))
            if asn not in asn_ids:
                asn_ids[name] = asn
            else:
                asn_ids[name] = "Missing";  no_asn_nodes += 1
        print("%d nodes missing from asns file" % no_asn_nodes)
        return no_asn_nodes, asn_ids
    else:
        print("asn file = %s <<< Couldn't find an asns file" % asns_fn)
        return ''

print(" msm_ids >%s<" % reqd_msms)

yval_array = []  # y values for dest icounts

sf_offset = 3

n_min = mn_trpkts*2  # Min "interesting" av_icount for nodes,
d_min = mn_trpkts*5  # distal nodes
e_min = mn_trpkts*3  # and edges
n_lines = []  # Summary lines for nodes,
d_lines = []  # distal nodes
e_lines = []  # and edges

for msm_id in reqd_msms:
    ids = [];  pca = [];  inter_ca = []
    all_edges = []  # List of all 'interesting' edges for all msm_ids
    msm_dest = c.msm_dests[msm_id][0]
    if asn_graphs:
        n_asns = 0;  asn_ids = {}
    else:
        no_asn_ids, asn_ids = read_asns_file(msm_id, {})
            # Dictionary of ASN ids, indexed by ASN prefix (or name)
        if asn_ids == '':
            exit()  # No asn file for this msm_id
        if no_asn_ids != 0:
            a_unknown = {}
            no_asn_ids, unknown_asn_ids = read_asns_file('unknown', asn_ids)
            if unknown_asn_ids != '':  # Don't care of there's no asns_unknown file
                asn_ids = unknown_asn_ids  # Use it if we have one
                print("Unknown asns file loaded")
                no_asn_nodes = {}
        n_asns = len(asn_ids)-1  # Don't count "Missing"
        print(">>> n_asns = %d, n_nodes = %d" % (n_asns, len(node_dir)))
    
    gi = grin.GraphInfo(msm_id, asn_ids, n_bins, asn_graphs,
        n_asns, no_asn_nodes, mx_depth, mn_trpkts)
            # Pruning as for drawing svgs
                            
    #print("-a- %d sub_roots found" % len(gi.sub_roots))

#                   0        1      2               3       4
    colours = ['black', 'brown', 'red',   'darkorange', 'gold',
#                   5       6         7       8            9       10
               'green', 'blue', 'violet', 'grey', 'lightblue', 'black']

    if n_presence or dn_presence:  # Check node presence (for bar plots)
        ids = [];  pca = []
        msm_dest = c.msm_dests[msm_id][0]

        def print_stats(n, ix, ac):
            av_orun = np.average(n.ora_len)
            av_zrun = np.average(n.zra_len)
            av_ms = av_orun/av_zrun
            print("%d: %d  ones=%d, n_oruns=%d, n_zruns=%d, mx_orun=%d, mx_zrun=%d, av_orun=%.2f, av_zrun=%.2f, av_ms=%.2f\n%s" % (
                ix, msm_id, n.n_ones, n.n_oruns, n.n_zruns, n.mx_orun, n.mx_zrun, av_orun, av_zrun, av_ms,
                    n.ps))
            #if ac:
            #    print("ac = %s" % gi.acor(n.present))

        def node_dist(pv1, pv2):  # Distance metric for clustering Egdes
            dist = np.sum(pv1 != pv2)  # Different, in [0:n_bins]
            #dist2 = np.sum(pv1 != np.logical_not(pv2))  # Present in gaps
            #if dist2 < dist:
            #    return dist2
            return dist

        #def shift(a, num):
        #    arr = np.roll(a, num)
        #    arr[:num] = 0
        #    return arr

        def node_dist2(pv1, pv2):  # Distance metric for clustering Egdes
            dist = np.sum(pv1[:n_bins] != pv2[:n_bins])
                # Strip src/dst ASNs
            return dist

        xv = np.cumsum(np.ones(n_bins))  # [1,48] interval vector
        def node_dist3(pv1, pv2):  # Distance metric for distal nodes
            # Behaves same as dist2()
            pp1 =  np.multiply(pv1[:n_bins], xv)
            pp2 =  np.multiply(pv2[:n_bins], xv)
            dist = np.sum((pp1 != pp2).astype(int))  # Difference in [0:n_bins]
            return dist

        def get_n_runs(pv):  # Get node stats from pv
            zra = grin.zero_runs(pv)
            zra_len = zra[:,1]-zra[:,0]  # Run-of-zeroes lengths
            n_zruns = len(zra_len)
            ora = grin.one_runs(pv)
            ora_len = ora[:,1]-ora[:,0]  # Run-of-ones lengths
            n_oruns = len(ora_len)
            #mx_orun = 0
            #if len(ora_len) != 0:
            #    mx_orun = ora_len.max()
            return n_zruns, n_oruns  #, mx_orun

        def node_dist4(pv1, pv2):  # Distance metric for distal nodes
            nzr1,nor1 = get_n_runs(pv1)
            nzr2,nor2 = get_n_runs(pv2)
            #dist = abs((mxor1-mxor2))*50 \
            #    + np.sum((pv1 != pv2).astype(int))*100
            dist = (abs((nor1-nor2))+abs(nzr1-nzr2))*50 \
                + np.sum((pv1 != pv2).astype(int))*100
            return dist

        def make_node_plot_labels(msm_id, nodes):
            print("msm_id %d has %d nodes" % (
                msm_id, len(nodes)))
            #if len(nodes) <= 2:
            #    print("  >>> not enough to plot")
            #    return
            for j,n in enumerate(nodes):
                #print("plot node n: (%s) %s" % (type(n), n))
                if no_ASNs:
                    nn = "%s->%s %4d pkts " % (n.n_from, n.n_to, n.av_icount)
                elif c.full_graphs:
                    nn = "%s   %s %5d pkts " % (
                        n.asn, n.name, n.av_icount)
                else:
                    nn = "%s %5d pkts " % (
                        n.name, n.av_icount)
                n.plot_label = nn

        def summarise_nodes(nodes, obj_type, diff_fn,  colour, i_min):
            a_unknown = []  # Names of nodes with no ASN
            #for j,n in enumerate(nodes):
            #    print("summarise_nodes %2d, (%s), %s)" % (j, type(n), n))
            make_node_plot_labels(msm_id, nodes)
            print("Abougt to call reorder_list of %s nodes" % obj_type)
            nodes = reorder_list(nodes, diff_fn)
            for n in nodes:  # Check for unknown nodes
                n.pv = n.pv[:n_bins]
                if n.asn == "unknown":
                    a_unknown.append(n.name)
            print("%d unknown asns found <<<" %len(a_unknown))
            plot_bars("%s Presence" % obj_type, 
                #???msm_id, nodes[0:34], colour, 0)
                msm_id, nodes, colour, 0)

            n_lines.append("\n%s%s %s presence: zero-runs . . .\n" % (
                ' '*(sf_offset), msm_id, obj_type))
            #i_min = n_min  # Min "interesting" av_icount
            oepa = []  # nodes for each ASN
            for j,n in enumerate(nodes):  # Look for "interesting" nodes
                if n.av_icount >= i_min and \
                       n.n_zruns != 0 and n.n_zruns <= 3:
                    oe = grin.OutObjects(n, "n", asn_graphs)
                    if oe not in oepa:
                        oepa.append(oe)
                    oep = oe.index(oepa)  # pointer to eo in oea
                    ok = "%s, %s" % (n.node_asn(n.name), n.name)  # Object Key
                    oep.update(n.av_icount, ok)

            #sni_f = open(c.s_n_info_fn(msm_id), "r")
            #for line in sni_f:
            #    print(line.strip())
            #exit()

            for oe in oepa:
                n_lines.append("%s%s\n" % (
                    ' '*(sf_offset+3), oe))
                for ok in oe.sd_asns:
                    ocounts = np.array(oe.sd_asns[ok]).astype(int)
                    name = str(ok)
                    if name[0:7] == "unknown":
                        name = ok[9:]
                    n_lines.append("%s%5d for %s\n" % (
                        ' '*(sf_offset+6), np.sum(ocounts), name))
            #for j,line in enumerate(n_lines):
            #    print("%3d  %s" % (j, line), end='')

            if len(a_unknown) != 0:
                ua_unknown_f = open(c.all_unknown_nodes_fn(), 'a')
                for an in a_unknown:
                    ua_unknown_f.write(an+"\n")
                ua_unknown_f.close()

        print("-d- about to examine %d nodes()" % len(gi.all_nodes))
        n_stable = gi.examine_nodes(mn_trpkts)  # Compute Node stats values
        #        # Also makes list of 'interesting' nodes in gi.all_nodes
        print("%d stable nodes" % n_stable)

        print("-e- %d distal nodes found" % len(gi.distal_nodes))
        #nnn = 0
        #for n in gi.distal_nodes:
        #    print("n %s\n   n_zruns %d, mx_zrun %d" % (
        #          n, n.n_zruns, n.mx_zrun))
        #    if nnn == 5:
        #        break

        if n_presence:
            if len(gi.all_nodes) < 5:
                print("\nOnly %d all_nodes were 'interesting' !!!" % \
                    len(gi.all_nodes))
            nodes = gi.classify_nodes()
            print("classify_nodes() found %d interesting nodes" % len(nodes))

            if nodes and plot_items:
                summarise_nodes(nodes, "Node", node_dist3, "green", n_min)

        if dn_presence:  # Distal Node presence
            dn_nodes = []
            for j,n in enumerate(gi.distal_nodes):
                dn_nodes.append(n)
            if dn_nodes and plot_items:
                #summarise_nodes(dn_nodes, "Distal Node", node_dist3,
                summarise_nodes(dn_nodes, "Distal Node", node_dist4,
                    "magenta", d_min)

    def make_edge_plot_labels(msm_id, edges):
        print("msm_id %d has %d edges" % (
            msm_id, len(edges)))
        for j,e in enumerate(edges):  # Assume we always have asn info :-)
            if asn_graphs:  # Nodes names are ASNs
                e.plot_label = "%s->%s  %5d pkts" % (
                    e.n_from, e.n_to, e.av_icount)
            else:
                e.plot_label = "%s->%s, %s->%s %5d pkts" % (
                    e.asn_from, e.asn_to, e.n_from, e.n_to, e.av_icount)

    if e_presence:  # Check Edge presence
        pca = []
        msm_dest = c.msm_dests[msm_id][0]

        def print_stats(e, ix, ac):
            av_orun = np.average(e.ora_len)
            av_zrun = np.average(e.zra_len)
            av_ms = av_orun/av_zrun
            print("%d: %d  ones=%d, n_oruns=%d, n_zruns=%d, mx_orun=%d, mx_zrun=%d, av_orun=%.2f, av_zrun=%.2f, av_ms=%.2f\n%s" % (
                ix, msm_id, e.n_ones, e.n_oruns, e.n_zruns, e.mx_orun, e.mx_zrun, av_orun, av_zrun, av_ms,
                    e.ps))
            #if ac:
            #    print("ac = %s" % gi.acor(e.present))

        def edge_dist(pv1, pv2):  # Distance metric for clustering Egdes
            dist = np.sum(pv1 != pv2)  # Different, in [0:n_bins]
            #dist2 = np.sum(pv1 != np.logical_not(pv2))  # Present in gaps
            #if dist2 < dist:
            #    return dist2
            return dist

        def edge_dist2(epv1, epv2):  # Distance metric for clustering Egdes
            dist = edge_dist(epv1[:-2], epv2[:-2])
            sd = dd = 0  # src, dest distances
            if epv1[-2] != epv2[-2]:  # High if different srcs
                sd = c.n_days
            if epv1[-1] == epv2[-1]:  # High if same dests
                dd = c.n_days
            return 2*dist + sd+dd

        def edge_dist3(epv1, epv2):  # Distance metric for clustering Egdes
            dist = edge_dist(epv1[:-2], epv2[:-2])
            sd = dd = 0  # src, dest distances
            if epv1[-2] != epv2[-2]:  # High if different srcs
                sd = c.n_days
            if epv1[-1] == epv2[-1]:  # High if same dests
                dd = c.n_days
            pd = c.n_days
            if epv1[-1] == epv2[-2] or epv2[-2] == epv1[-1]:
                # s1 == d2, i.e. ongoing path
                pd = 0
            return dist + pd + ss+dd


        same_counts, inter_counts = gi.asn_edges()
        pca.append(same_counts);  inter_ca.append(inter_counts)

        print("-d- about to examine_edges()")
        n_stable = gi.examine_edges(mn_trpkts)  # Compute stats values for each Edge
        #        # Also makes list of 'interesting' edges in gi.all_edges
        print("-y- n_stable = %d" % n_stable)

        if len(gi.all_edges) < 5:
            print("\nOnly %d edges were 'interesting' !!!" % len(all_edges))
        edges  = gi.classify_edges()
        print("classify_edges() found %d interesting edges" % len(edges))

        if plot_items:
            edges = reorder_list(edges, edge_dist)
            a_unknown = {}
            n2 = 0
            for e in edges:  # Strip src, dest from pv
                e.pv = e.pv[:n_bins]
                if e.asn_from == "unknown" and e.n_from not in a_unknown:
                    a_unknown[e.n_from] = 2;  n2 += 1
                if e.asn_to == "unknown" and e.n_to not in a_unknown:
                    a_unknown[e.n_to] = 2;  n2 += 1
            print("%d unknown asns found <<<" % n2)
            make_edge_plot_labels(msm_id, edges)
            plot_bars("Edge Presence", msm_id, edges[0:34], 'blue', 0)

            if no_ASNs:
                print("  no ASNs, can't print 'interesting' edges")
            else:
                i_min = e_min  # min "interesting" av_icount
                e_lines.append("\n%s%s Edge presence: zero-runs . . .\n" % (
                    ' '*(sf_offset), msm_id))
                oepa = []  # Edges for each ASN|prefix pair
                for j,e in enumerate(edges):  # Look for "interesting" edges
                    if e.av_icount >= i_min and \
                           e.n_zruns != 0 and e.n_zruns <= 3:
                        #e_lines.append("%2d  %s -> %s  %d pkts" % (
                        #    j, e.asn_from, e.asn_to, e.av_icount))
                        #print("e.icounts = %s" % e.icounts)

                        oe = grin.OutObjects(e, "e", asn_graphs)
                        if oe not in oepa:
                            oepa.append(oe)
                        oep = oe.index(oepa)  # pointer to eo in oea
                        if asn_graphs:
                            ek = "%s->%s" % (  # Node names are ASNs
                                e.n_from, e.n_to)
                        else:
                            ek = "%s->%s, %s->%s" % (
                                e.asn_from, e.asn_to, e.n_from, e.n_to)
                        oep.update(e.av_icount, ek)
                for oe in oepa:
                    e_lines.append("%s%s\n" % (
                        ' '*(sf_offset+3), oe))
                    for ek in oe.sd_asns:
                        ecounts = np.array(oe.sd_asns[ek]).astype(int)
                        e_lines.append("%s%5d for %s\n" % (
                            ' '*(sf_offset+6), np.sum(ecounts), ek))

            if len(a_unknown) != 0:
                ua_unknown_f = open(c.all_unknown_nodes_fn(), 'a')
                for nk in a_unknown:
                    if a_unknown[nk] == 2:
                        ua_unknown_f.write(nk+"\n")
                ua_unknown_f.close()

    if e_variance:  # Check Edge variance (for colour-bar plots)
        edges = gi.classify_variances()
        print("%d edges have iteresting variance" % len(edges))
        msm_dest = c.msm_dests[msm_id][0]

        def var_dist(pv1, pv2):  # Clustering metric for Edge tr_pkts variance
            #diff_v = pv1 - pv2
            diff_v = np.absolute(pv1 - pv2)
            #print("pv1 = %s" % pv1)
            #print("pv2 = %s" % pv2)
            #print("diif_v = %s" % diff_v)
            #print("var_dist returns %s" % np.sum(diff_v))
            return np.sum(diff_v)

        if plot_items:
            edges = reorder_list(edges, var_dist)
            a_unknown = {}
            n2 = 0
            for e in edges:  # Strip src, dest from pv
                e.pv = e.pv[:n_bins]
                if e.asn_from == "unknown" and e.n_from not in a_unknown:
                    a_unknown[e.n_from] = 2;  n2 += 1
                if e.asn_to == "unknown" and e.n_to not in a_unknown:
                    a_unknown[e.n_to] = 2;  n2 += 1
            print("%d unknown asns found <<<" % n2)
            make_edge_plot_labels(msm_id, edges)
            plot_bars("Edge Variance", msm_id, edges[0:34], 
                pplt.get_cmap('RdBu'), 0)

            if len(a_unknown) != 0:
                ua_unknown_f = open(c.all_unknown_nodes_fn(), 'a')
                for nk in a_unknown:
                    if a_unknown[nk] == 2:
                        ua_unknown_f.write(nk+"\n")
                ua_unknown_f.close()

    if sr_presence:  # Check SubRoot presence (for bar plots)
        def ev_dist(pv1, pv2):  # Clustering distance metric
            dist = np.sum(pv1 != pv2)  # Different
            #dist2 = np.sum(pv1 != np.logical_not(pv2))  # Present in gaps
            #if dist2 < dist:
            #    return dist2
            return dist

        gi.examine_subroots()  # Get list of all subroots
        sr_il = gi.classify_subroots(mntr)  # Find 'interesting' subroots
        sr_list = []
        for sr in sr_il:
            if sr.name in node_dir:
                sr.asn =  node_dir[sr.name]  # node_dir only contains ASNs
            else:
                print("------ sr %s Missing" % sr.name)
                sr.asn = "Missing?"
            sr_label = "%s    %s  %4d pkts " % (
                sr.asn, sr.name, sr.av_icount)
            sr.pv = sr.present;  sr.plot_label = sr_label
            sr_list.append(sr)

        if plot_items:
            plot_bars("SubRoot Presence", msm_id, sr_list, "red", 0)

    elif in_to_dest:
        yval_array.append(gi.trs_dest)
        if plot_items and msm_id == reqd_msms[-1]:
            fig, ax = pplt.subplots(1, figsize=(6, 3))
            fig.suptitle("%s: traceroute pkts reaching dest" % c.start_ymd, 
                fontsize=12)
            ax.set_xticks(np.arange(0,n_bins+1,6))
            pplt.grid(which="major", color="lightgrey")
            pplt.xlim(-1,n_bins)
            for n,yv in enumerate(yval_array):
                cn = int(str(reqd_msms[n])[-1])
                lbl = str(reqd_msms[n])
                ax.step(np.arange(0,n_bins), yv, where="mid",
                    color=colours[cn], label=str(reqd_msms[n]))
            ax.legend(loc="lower right", title="msm_id", frameon=False)
            pfn = "%s/dest-incounts.pdf" % c.start_ymd
            print("save to %s" % pfn)
            pplt.savefig(pfn)

    elif walk_graph:
        print("Walking the graph for %s ..." % msm_id)
        nodes = gi.all_nodes

        def top_n_nodes(dest, n_reqd):  # dest = target for trpkts
            hop1_nodes = []
            dest_node = nodes[dest]

            in_dict = dest_node.in_edges[0]  # Look at bin 0
            for pnk in in_dict:
                #print(">>> pn %s : %d" % (pnk, in_dict[pnk]))
                #exit()
                icount = in_dict[pnk]
                if icount >= mn_trpkts:
                    #print("pn >%s< (%s)" % (pn, type(pn)))
                    hop1_nodes.append( (icount, pnk) )
            print("%d nodes with icount >= %d" % (len(hop1_nodes), mn_trpkts))

            yval_array = [];  node_names = []
            for n,tuple in enumerate(sorted(hop1_nodes, reverse=True)):
                print("%4d  %s : %d" % (n, tuple[1], tuple[0]))
                node_names.append(tuple[1])
                yval_array.append(nodes[tuple[1]].icounts)
                if n == n_reqd:
                    break
            return yval_array, node_names

        def plot_hop_n_incounts(yval_array, node_names, dest, depth):
            fig, ax = pplt.subplots(1, figsize=(8, 5))
            fig.subplots_adjust(left=None, bottom=None, right=0.7, top=None)
            fig.suptitle("%s, %d: tr_pkts to %s at depth %d" % (
                c.start_ymd, msm_id, dest, depth), fontsize=12)
            ax.set_xticks(np.arange(0,n_bins+1,6))
            pplt.grid(which="major", color="lightgrey")
            pplt.xlim(-1,n_bins)
            for n,yv in enumerate(yval_array):
                lbl = str(msm_id)
                ax.step(np.arange(0,n_bins), yv, where="mid",
                        color=colours[n], label=str(node_names[n]))
            #ax.legend(loc="lower right", title="Node Name", 
            ax.legend(title="Node Name",  loc="center left",
                bbox_to_anchor=(1.05,0.5), prop={"size":10}, frameon=False)
            pfn = "%s/hop-%d-%s-incounts-%s.pdf" % (
                c.start_ymd, depth, dest, msm_id)
            print("save to %s" % pfn)
            pplt.savefig(pfn)

        d1_dest = gi.dest
        d1_yval_array, d1_node_names = top_n_nodes(d1_dest, 10)
        #if plot_items:
        #    plot_hop_n_incounts(d1_yval_array, d1_node_names, "dest", 1)

        d2_dest = d1_node_names[0]
        d2_yval_array, d2_node_names = top_n_nodes(d2_dest, 10)
        if plot_items:
            plot_hop_n_incounts(d2_yval_array, d2_node_names, d2_dest, 2)

        d2_dest = d1_node_names[1]
        #d2_yval_array, d2_node_names = top_n_nodes(d2_dest, 10)
        #if plot_items:
        #    plot_hop_n_incounts(d2_yval_array, d2_node_names, d2_dest, 2)

if plot_items and (n_presence or e_presence):
    asn_prefix = ""
    if asn_graphs:
        asn_prefix = "ASN-"
    option_str = ''
    if n_presence:
        option_str += "_n"
    if dn_presence:
        option_str += "_d"
    if e_presence:
        option_str += "_e"
    summary_file = open("%s/%sgraphs%s-summary.txt" % (
        reqd_ymds[0], asn_prefix, option_str), "w")
    summary_file.write("Presence summary for %sgraphs on %s\n\n" % (
        asn_prefix, reqd_ymds[0]))
    if n_presence:
        summary_file.write(
            "Nodes (min 'interesting' count = %d)\n" % n_min)
        for line in n_lines:
            summary_file.write(line)
    if e_presence:
        if n_presence:
            summary_file.write("\n")
        summary_file.write(
            "Edges (min 'interesting' count = %d)\n" % e_min)
        for line in e_lines:
            summary_file.write(line)
    summary_file.write("\n")
    summary_file.close()


'''
            icount = 0
            for pn in in_edges:
                icount += in_edges[pn]
            counts_at_depths[depth] += icount
            if depth != 15:
                for pn in in_edges:
                    #print(">>> pn = %s (%s)" % (pn, type(pn)))
                    if pn in nodes:  # May have been pruned
                        prev_hop(depth+1, nodes[pn], bn)
            return
        

    ng = True;  ea = []
    for r in range(0, len(Z)):  # Print linkage matrix
        #print("%3d:  %3d %3d  %6.3f  %3d (%3d)  <%s + %d = %d>" % (r,
        #    Z[r,0],Z[r,1], Z[r,2], n+r, Z[r,3], n, r, n+r-1))
        if ng:
            if Z[r,2] >= 0.1:
                break  # NoZ[r,3] more low-dist groups
            ea.append(int(Z[r,0]));  ea.append(int(Z[r,1]))
            ng = False
            #print("New group: %s" % ea)
        elif Z[r,2] < 0.1 and Z[r,2] == Z[r-1,2] and Z[r,1] == n+r-1:
            # Same v.small dist && Z[r,2] adds to prev cluster -> end of group
            ea.append(int(Z[r,0]))
            #print("End of group: %s" % ea)
            #?p = check_path(ea)
            #?if p:
            #?    print("path = %s" % p)
            ng = True;  ea = []
'''
