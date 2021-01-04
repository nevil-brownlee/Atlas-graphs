# 1806, 15 Dec 2016 (NZDT)
#
# tr-pkts-v-edges-per-depth.py:  #  python3 (uses numpy)
#                  stats file -> nodes histograms, for all depths
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import numpy as np  # Operations on arrays
# http://wiki.scipy.org/Tentative_NumPy_Tutorial

import matplotlib as mpl
# http://matplotlib.org/api/pyplot_summary.html
from matplotlib import pyplot as pplt
from matplotlib import patches as plt_patches

import msm_file as mf
        
import math, datetime, os

import config as c

reqd_ymds = [];  reqd_msms = []
pp_names = "y! m!"  # indexes 0 to 1
pp_ix, pp_values = c.set_pp("")  # Set up config info  (no + parameters)
for n,ix in enumerate(pp_ix):
    if ix == 0:    # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 1:  # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("reqd_ymds = %s, reqd_msms = %s\n" % (reqd_ymds, reqd_msms))
if len(reqd_ymds) > 1:
    print("tr-pkts-v-edges-per-depth.py only handles one ymd <<<")
    exit()
c.start_ymd = reqd_ymds[0]

start_time = c.start_time
start_ymd = c.start_ymd

def tbs_filter(tbs, mn_depth,mx_depth, mn_tr_pkts,mx_tr_pkts):
    stop_row = mx_depth+1
    #print("tbs_filter: mn %d, mx %s stop_row %d" % (
    #    mn_depth,mx_depth, stop_row))
    tbs_ftr_pkts =  [ [] for j in range(mn_depth,mx_depth+1) ]  # Filtered array
    if len(tbs.tb_tr_pkts) < mx_depth:
        stop_row = len(tbs.tb_tr_pkts)
    total_edges = 0
    for d in range(mn_depth,stop_row):
        row =  np.array(tbs.tb_tr_pkts[d])
        tbs_ftr_pkts[d-mn_depth] = \
            row[(row >= mn_tr_pkts) & (row <= mx_tr_pkts)]
        #print("d=%d, keep=%s" % (d, tbs_ftr_pkts[d-mn_depth]))
        #print("d=%d, sum=%d" % (d, tbs_ftr_pkts[d-mn_depth].sum()))
        total_edges +=  len(tbs_ftr_pkts[d-mn_depth])
    print(">>> total_edges = %d" % total_edges)
    return tbs_ftr_pkts

def plot_stacked(msm_objs, msm_dests, inner, bn):  # Plots for timebin bn
    # msm_obj is an MsmStatsFile,
    #   msm_obj.tbsa is an array of TbStats objects

#   Resistor colour codes 0-9, repeating  ...
#                   1      2         3         4         5       6
    colours = ['brown', 'red', 'orange', 'yellow',  'green', 'blue',
#             7       8        9 white       10       11     12        13
        'violet', 'grey', 'navajowhite', 'black', 'brown', 'red', 'orange',
#            14       15      16        17      18             19
        'yellow', 'green', 'blue', 'violet', 'grey', 'navajowhite', 
#           20       21     22
        'black', 'brown', 'red']
    if inner:
        which = "Inner"
        depths = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "11", "12", "13", "14", "15", "16")
        colours = colours[:16]
    else:
        which = "Outer"
        depths = ("17", "18", "19", "20", "21", "22", "23", "24", "25", "26",
            "27", "28", "29", "30", "31", "32")
        colours = colours[6:]

#    nc = len(colours)  # Nbr of colours
#    print("nc = %d" % nc)
    tpt = []; tlabels = [] # depths patch tuples and colours
    n_depths = len(depths)
    for t in range(n_depths):
        r = n_depths-1 - t
        tpt.append(plt_patches.Patch(color=colours[r]))
        tlabels.append(depths[r])

    print("@@@ Starting plot_stacked, which = %s . . ." % which)
    if len(msm_objs) <= 3:
        rows = 1;  cols = len(msm_objs)
        w = 7*cols/3;  h = 3.4;  stp = 11;  tkp = 7;  tp = 9
    elif len(msm_objs) <= 6:
        rows = 2;  cols = 3
        w = 11.5;  h = 9.0;  stp = 16; tkp = 12;  tp = 12
    else:
        print("Can't plot more than 6 msm_ids <<<")
    fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches (?)
    fig.legend(tpt, tlabels, "center right", title="Hops\n   to\nDest",
        bbox_to_anchor=(0.98,0.5), prop={"size":10}, handlelength=1)

    if len(msm_objs) < 6:  # ?? 
        pplt.subplots_adjust(left=0.155, bottom=None, right=None, top=0.9,
                             wspace=0.3, hspace=0.85)
    else:
        #pplt.subplots_adjust(left=0.065, bottom=None, right=0.9, top=0.95,
        #pplt.subplots_adjust(left=0.065, bottom=None, right=None, top=0.9,
        pplt.subplots_adjust(left=0.065, bottom=None, right=None, top=0.91,
                             wspace=0.4, hspace=0.3)
    
    fig.suptitle("%s traceroute packet histograms: %s, timebin %d" % ( \
        which, start_time.strftime("%A %Y-%m-%d"), bn),
        fontsize=stp, horizontalalignment='center')

    for f in range(rows*cols):
        print("--- f = %d" % f)
        r = int(f/cols);  cl = f%cols        
        if rows == 1:
            if cols == 1:
                xy1 = axes
            else:
                xy1 = axes[cl]
        else:
            xy1 = axes[r,cl]
            
        msm_obj = msm_objs[f]
        print("f = %i, msm = %d, bn = %d" % (f, msm_obj.msm_id, bn))
        print("   >>> len(tbas) = %d" % len(msm_obj.tbsa))
        tbs = msm_obj.tbsa[bn]
        tb_mn_depth = msm_obj.tb_mn_depth

        msm_id = msm_obj.msm_id;  dest = msm_dests[msm_id][0]
        title = "%d: %s" % (msm_id, dest)
        xy1.set_title("%s" % title, fontsize=14)  #? tp)
 
        xy1.set_yscale('log')
        xy1.tick_params(axis='y', labelsize=tkp)  #x
        xy1.set_ylabel("tr packets", fontsize=14, labelpad=-4)
        xy1.tick_params(axis='x', labelsize=tkp)
        xy1.set_xlabel("Edges", fontsize=tkp, labelpad=1)  #y

        if inner:
            tpa = tbs_filter(tbs, 0,15, 32,20000)
            trlo = 32;  trhi = 1750
            xy1.set_ylim([trlo, trhi])
            xy1.set_yticks([20, 60, 180, 540, 1620])
            xy1.set_yticklabels(['20', '60', '180', '540', '1620'])
            ylo = math.log(trlo)/math.log(10)  # For logspace() bins
            yhi = math.log(trhi)/math.log(10)

            edlo = 0.1;  edhi = 100
            xy1.set_xticks([10, 30, 50, 70, 90])
            xy1.set_xlim([edlo, edhi])

            n, bins, patches = xy1.hist(
                #first_depths, stacked=True, orientation=u'horizontal',
                tpa, stacked=True, orientation=u'horizontal',
                bins=np.logspace(ylo, yhi, 40),
                color=colours,  # linear scale
                alpha=0.8, linewidth=1, rwidth=0.8)

        else:  # outer
            tpa = tbs_filter(tbs, 16,31, 1,120)
            trlo = 1;  trhi = 90
            xy1.set_ylim([trlo, trhi])
            xy1.set_yticks([3, 9, 27, 81])
            xy1.set_yticklabels(['3', '9', '27', '81'])
            ylo = math.log(trlo)/math.log(10)  # For logspace() bins
            yhi = math.log(trhi)/math.log(10)

            edlo = 10;  edhi = 14000  ##10000  ##7000  ##6000  ##5400
            xy1.set_xlim([edlo, edhi])
            xy1.set_xscale('log')
            #xy1.set_xticks([20, 60, 180, 540, 1620])
            #xy1.set_xticklabels(['20', '60', '180', '540', '1620'])
            xy1.set_xticks([15, 60, 240, 1200, 7000])
            xy1.set_xticklabels(['15', '60', '240', '1200', '7000'])

            n, bins, patches = xy1.hist(
                tpa, stacked=True, orientation=u'horizontal',
                bins=np.logspace(ylo, yhi, 30),
                color=colours, # log=False
                alpha=0.8, linewidth=1, rwidth=0.8)

    #pplt.show()
    plot_fn = "%s/%s-tr-pkts-v-edges-per-depth.svg" % (start_ymd, which)
    pplt.savefig(plot_fn)


msm_objs = []
bins_to_read = 1  # Only read stats for first bin
#for msm_id in c.msm_nbrs:
#print("--- msm_objs = %s <<<" % msm_objs)
#for msm_id in [5017]:
#for msm_id in [5017, 5005, 5016]:
for msm_id in [5017, 5005, 5016, 5004, 5006, 5015]:
    fn = "./" + c.stats_fn(msm_id)  # isfile expects full filename!
    print("msm_id = %d, fn = %s" % (msm_id, fn))
    if os.path.isfile(fn):
        print(" >>> %d: %s" % (msm_id, fn))
        msm_objs.append(mf.MsmStatsFile(fn, 0, 0))  # Read bins 0 only
        #msm_objs.append(mf.MsmStatsFile(fn, 0, 2))  # Read bins 0,1,2
    else:
        print("No file %s" % fn)
    print("len(msm_objs) = %i" % len(msm_objs))

if len(msm_objs) == 0:
    print("No stats files found <<<")
    exit()
print("--- msm_objs = %s" % msm_objs)

plot_stacked(msm_objs, c.msm_dests, True, 0)  # Inner plot for timebin 0
plot_stacked(msm_objs, c.msm_dests, False, 0)  # Outer plot for timebin 0
#plot_stacked(msm_objs, c.msm_dests, 10)  # Plot timebin 10 only
