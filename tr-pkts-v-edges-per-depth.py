# 1806, 15 Dec 2016 (NZDT)
#
# node-v-edge-stacked-msm_ids.py:  #  python3 (uses numpy)
#                  stats file -> nodes histograms, for all depths
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import numpy as np  # Operations on arrays
# http://wiki.scipy.org/Tentative_NumPy_Tutorial

import matplotlib as mpl
# http://matplotlib.org/api/pyplot_summary.html
from matplotlib import pyplot as pplt
from matplotlib import patches

import math, datetime, os

import config as c
c.set_pp(True, c.msm_id)  #  Use stats_* prune parameters
print(">>> %s" % c.dgs_stem)

import msm_file as mf

start_time = c.start_time
start_ymd = c.start_ymd

#for b in range(c.n_bins):
#    bin_start = start_time + datetime.timedelta(0, 30*60) * b
#    print "bin %02d, %s" % (b, bin_start)
#    print "bin %02d, %s" % (b, bin_start.strftime("%H%M"))
#    print "bin %02d, %s" % (b, bin_start.strftime("%Y-%m-%d"))

tb_mx_depth = c.stats_mx_depth+1  # mx_depth = mx hops back from dest

def plot_stacked(msm_objs, msm_dests, bn):
    global patches

#               1        2      3         4  # Resistor colour codes
    colours = ['brown', 'red', 'orange', 'yellow',
#        5        6       7         8       9 white        10       11
    'green', 'blue', 'violet', 'grey', 'navajowhite', 'black', 'brown', #'magenta',
#                 12        13        14       15      16
               'red', 'orange', 'yellow', 'green', 'blue']
    nc = len(colours)  # Nbr of colours
    print("nc = %d" % nc)

    #depths = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")
    depths = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16")
    n_depths = len(depths)

    tpt = []; tlabels = [] # depths patch tuples and colours
    for t in range(n_depths):
        r = n_depths-1 - t
        print("  t=%d, r=%d" % (t, r))
        tpt.append(patches.Patch(color=colours[r]))  #   %nc]))
        tlabels.append(depths[r])
    if len(msm_objs) <= 3:
        rows = 1;  cols = len(msm_objs)
        w = 7*cols/3;  h = 3.4;  stp = 12;  tkp = 7;  tp = 9
    elif len(msm_objs) <= 6:
        rows = 2;  cols = 3
#        w = 11.7;  h = 8.0;  stp = 18; tkp = 12;  tp = 12
        w = 11.5;  h = 9.0;  stp = 18; tkp = 12;  tp = 12
    else:
        print("Can't plot more than 6 msm_ids <<<")
    fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches (?)

    if len(msm_objs) < 6:  # ?? 
        pplt.subplots_adjust(left=0.155, bottom=None, right=None, top=0.9,
                             wspace=0.3, hspace=0.85)
    else:
        #pplt.subplots_adjust(left=0.065, bottom=None, right=0.9, top=0.95,
        #pplt.subplots_adjust(left=0.065, bottom=None, right=None, top=0.9,
        pplt.subplots_adjust(left=0.065, bottom=None, right=None, top=0.91,
                             wspace=0.4, hspace=0.3)
    
    fig.suptitle("traceroute packet histograms: %s, timebin %d" % ( \
        start_time.strftime("%A %Y-%m-%d"), bn),
        fontsize=stp, horizontalalignment='center')
    fig.legend(tpt, tlabels, "center right", title="Hops\n to\nDest",
         bbox_to_anchor=(0.98,0.5), prop={"size":10}, handlelength=1)

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
        #print("f = %i, msm_obj = %s" % (f, msm_obj))
        tbs = msm_obj.tbsa[0]
        msm_id = msm_obj.msm_id;  dest = msm_dests[msm_id][0]
        title = "%d: %s" % (msm_id, dest)
        xy1.set_title("%s" % title, fontsize=14)  #? tp)
 
        xy1.set_yscale('log')  #x
        xy1.tick_params(axis='y', labelsize=tkp)  #x
#        xy1.set_ylabel("tr packets", fontsize=tkp, labelpad=1)  #x  3
        xy1.set_ylabel("tr packets", fontsize=14, labelpad=-4)  #x  3
        if start_ymd == '20120222':
            if msm_id == 5017 or msm_id == 5005:
                xy1.set_xlim([0.1, 21])
                xy1.set_xticks([4, 8, 12, 16, 20])
            elif msm_id == 5016:
                xy1.set_xlim([0.1, 15])
                xy1.set_xticks([2, 4, 6, 8, 10, 12, 14])
            elif msm_id == 5004:
                xy1.set_xlim([0.1, 14])
                xy1.set_xticks([2, 4, 6, 8, 10, 12])
            elif msm_id == 5006:
                xy1.set_xlim([0.1, 39])
                xy1.set_xticks([5, 10, 15, 20, 25, 30, 35])
            elif msm_id == 5015:
                xy1.set_xlim([0.1, 59])
                xy1.set_xticks([10, 20, 30, 40, 50])
        elif start_ymd == '20170220':
            if msm_id == 5017 or msm_id == 5005 or msm_id == 5004:
                xy1.set_xlim([0.1, 99])
                xy1.set_xticks([10, 30, 50, 70, 90])
            elif msm_id == 5016:
                xy1.set_xlim([0.1, 49])
                xy1.set_xticks([5, 15, 25, 35, 45])
            elif msm_id == 5006:
                xy1.set_xlim([0.1, 123])
                xy1.set_xticks([10, 30, 50, 70, 90, 110])
            elif msm_id == 5015:
                xy1.set_xlim([0.1, 109])
                xy1.set_xticks([15, 35, 55, 75, 95])
        else:
            if msm_id == 5016:
                xy1.set_xlim([0.1, 49])
                xy1.set_xticks([5, 15, 25, 35, 45])
            else:
                xy1.set_xlim([0.1, 123])
                xy1.set_xticks([10, 30, 50, 70, 90, 110])
        elo = 18;  ehi = 1800
        ylo = math.log(elo)/math.log(10)
        yhi = math.log(ehi)/math.log(10)
        xy1.set_yticks([20, 60, 180, 540, 1620])
        xy1.set_yticklabels(['20', '60', '180', '540', '1620'])
        #xy1.set_yticks([20, 40, 80, 160, 320, 640])
        #xy1.set_yticklabels(['20', '40', '80', '160', '320', '640'])
        xy1.set_ylim([elo, ehi]) #x
        xy1.tick_params(axis='x', labelsize=tkp)  #y
#        xy1.set_ylabel("Edges", fontsize=tkp, labelpad=2)
        xy1.set_xlabel("Edges", fontsize=tkp, labelpad=0)  #y
        #print("shape(tb_tr_pkts) = %s" % np.shape(tbs.tb_tr_pkts))
        n, bins, patches = xy1.hist(
            tbs.tb_tr_pkts, stacked=True, orientation=u'horizontal',
            bins=np.logspace(ylo, yhi, 40),
            color=colours,
            alpha=0.8, linewidth=1, rwidth=0.8)

    #pplt.show()
    plot_fn = "%s/tr-pkts-v-edges-per-depth.svg" % start_ymd
    pplt.savefig(plot_fn)


msm_objs = []
bins_to_read = 1  # Only read stats for first bin
#for msm_id in c.msm_nbrs:
#print("--- msm_objs = %s <<<" % msm_objs)
#for msm_id in [5017, 5005, 5016]:
for msm_id in [5017, 5005, 5016, 5004, 5006, 5015]:
    fn = "./" + c.stats_fn(msm_id)  # isfile expects full filename!
    print("msm_id = %d, fn = %s" % (msm_id, fn))
    if os.path.isfile(fn):
        print(" >>> %d: %s" % (msm_id, fn))
        msm_objs.append(mf.MsmFile(fn, bins_to_read))  # Read msm's stats file
    else:
        print("No file %s" % fn)
    print("len(msm_objs) = %i" % len(msm_objs))
if len(msm_objs) == 0:
    print("No stats files found <<<")
    exit()
print("--- msm_objs = %s" % msm_objs)
plot_stacked(msm_objs, c.msm_dests, 0)  # Plot timebin 0 only
#plot_stacked(msm_objs, c.msm_dests, 10)  # Plot timebin 10 only

'''
        if msm_id == 5005:
            elo = 17;  ehi = 2200
            xlo = math.log(elo)/math.log(10)
            xhi = math.log(ehi)/math.log(10)
            xy1.set_xlim([elo, ehi])
            xy1.set_xticks([20, 80, 320, 1280])
            xy1.set_xticklabels(['20', '80', '320', '1280'])
            xy1.set_ylim([0.1, 99])
        else:
            elo = 75;  ehi = 2200
            xlo = math.log(elo)/math.log(10)
            xhi = math.log(ehi)/math.log(10)
            xy1.set_xlim([elo, ehi])
            xy1.set_xticks([80, 320, 1280])
            xy1.set_xticklabels(['80', '320', '1280'])
            xy1.set_ylim([0.1, 12.25])
'''
