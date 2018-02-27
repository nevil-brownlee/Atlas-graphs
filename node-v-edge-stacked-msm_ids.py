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

import msm_file as mf
import config as c

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
               'red', 'orange', 'yellow', 'green', 'blue']
    nc = len(colours)  # Nbr of colours
    print("nc = %d" % nc)

    #depths = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")
    depths = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16")
    n_depths = len(depths)

    tpt = []; tlabels = [] # depths patch tuples and colours
    for t in range(n_depths-1):
        r = n_depths-2 - t
        print("  t=%d, r=%d" % (t, r))
        tpt.append(patches.Patch(color=colours[r]))  #   %nc]))
        tlabels.append(depths[r])
    if len(msm_objs) <= 3:
        rows = 1;  cols = len(msm_objs)
        w = 7*cols/3;  h = 3.4;  stp = 12;  tkp = 7;  tp = 9
    elif len(msm_objs) <= 6:
        rows = 2;  cols = 3
        w = 11.7;  h = 8.0;  stp = 18; tkp = 12;  tp = 12
    else:
        print("Can't plot more than 6 msm_ids <<<")
    fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches (?)
    print("type(axes)=%s, axes=%s" % (type(axes), axes))

    if len(msm_objs) < 6:  # ?? 
        pplt.subplots_adjust(left=0.155, bottom=None, right=None, top=0.9,
                             wspace=0.3, hspace=0.85)
    else:
        pplt.subplots_adjust(left=0.065, bottom=None, right=0.9, top=0.9,
                             wspace=0.3, hspace=0.3)
    
    #fig.suptitle("traceroute packet histograms: %s, timebin %d" % ( \
    #    start_time.strftime("%A %Y-%m-%d"), bn),
    #    fontsize=stp, horizontalalignment='center')

    print("lem(msm_objs) = %d" % len(msm_objs))
    if len(msm_objs) == 1:
        leg = fig.legend(tpt, tlabels, "center right",
            bbox_to_anchor=(0.88,0.6), prop={"size":5}, handlelength=1)
            # Legend inside plot at top right
        leg.set_title("Hops\n  to\nDest", prop={"size":6})  # Legend title size
    elif len(msm_objs) < 6:
        fig.legend(tpt, tlabels, "center right", title="Hops\n  to\nDest",
                   fontsize=7,
                   bbox_to_anchor=(0.99,0.50), prop={"size":7}, handlelength=1)
    else:
        fig.legend(tpt, tlabels, "center right", title="Hops\n to\nDest",
                   bbox_to_anchor=(0.98,0.5), prop={"size":7}, handlelength=1)
    #leg = fig.legend()
    
    elo = 17;  ehi = 2200
    xlo = math.log(elo)/math.log(10)
    xhi = math.log(ehi)/math.log(10)

    for f in range(rows*cols):
        print("--- f = %d" % f)
        r = f/cols;  c = f%cols        
        if rows == 1:
            if cols == 1:
                xy1 = axes
            else:
                xy1 = axes[c]
        else:
            xy1 = axes[r,c]
            
        msm_obj = msm_objs[f]
        tbs = msm_obj.tbsa[0]
        msm_id = msm_obj.msm_id;  dest = msm_dests[msm_id][0]
        title = "%d: %s" % (msm_id, dest)
        xy1.set_title("%s" % title, fontsize=tp)
 
        xy1.set_xlim([elo, ehi])
        xy1.set_xscale('log')
        xy1.tick_params(axis='x', labelsize=tkp)
        xy1.set_xticks([20, 80, 320, 1280])
        xy1.set_xticklabels(['20', '80', '320', '1280'])
        xy1.set_xlabel("tr packets", fontsize=tkp, labelpad=2)

        xy1.set_ylim([0.1, 92])
        xy1.tick_params(axis='y', labelsize=tkp)
        xy1.set_ylabel("Edges", fontsize=tkp, labelpad=2)
        #print("shape(tb_tr_pkts) = %s" % np.shape(tbs.tb_tr_pkts))
        n, bins, patches = xy1.hist(
            tbs.tb_tr_pkts, stacked=True,
            bins=np.logspace(xlo, xhi, 40),
            color=colours,
            alpha=0.8, linewidth=1, rwidth=0.8)

    #pplt.show()
    pdf_fn = "%s/n+e-stacked-msm_ids-%d.svg" % (start_ymd, len(msm_objs))
    pplt.savefig(pdf_fn)  # .svg gets % shown properly on OSX


msm_objs = []
for msm_id in [5005]:
#for msm_id in c.msm_nbrs:
    fn = c.stats_fn(msm_id)
    #print("msm_id = %d, fn = %s" % (msm_id, fn))
    if os.path.isfile(fn):
        print(" >>> %d: %s" % (msm_id, fn))
        msm_objs.append(mf.MsmFile(fn, msm_id))
print("--- msm_objs = %s" % msm_objs)
plot_stacked(msm_objs, c.msm_dests, 0)  # Plot timebin 0 only

