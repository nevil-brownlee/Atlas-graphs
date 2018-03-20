# 1117, Mon  9 Jan 2016 (NZDT)
#
# nodes+edges-v-min_tr_pkts.py: stats file -> n+e v prune  for all timebins
#
# Copyright 2016, Nevil Brownlee,  U Auckland | RIPE NCC

import numpy as np  # Operations on arrays
# http://wiki.scipy.org/Tentative_NumPy_Tutorial
import scipy as sp  # Science/mathematics/engineering functions
# http://matplotlib.org/api/pyplot_summary.html
#from scipy import stats

import matplotlib as mpl
# http://matplotlib.org/api/pyplot_summary.html
from matplotlib import pyplot as pplt

import datetime, math, os

import config as c
c.set_pp(True, c.msm_id)  #  Use stats_* prune parameters

tb_mx_depth = c.stats_mx_depth+1  # mx_depth = mx hops back from dest
start_ymd = c.start_ymd
msm_dests = c.msm_dests

import msm_file as mf

def plot_image(xy1, tp, tkp, lp, tbs_obj, title):
    msm_id = tbs_obj.msm_id
    if not title:
        dest = msm_dests[msm_id][0]
        title = "%d: %s" % (msm_id, dest)
    xy1.set_title("%s" % title, fontsize=tp)

    if msm_id == 5017:
        xy1.set_xticks([120, 160, 200, 240, 280])  # Others
        xy1.set_xlim([105, 310])
        xy1.set_ylim([0, 165])
        xy1.set_yticks(np.arange(20, 160, 20))
        pass
    elif msm_id == 5005:
        xy1.set_xticks([20, 70, 120, 170, 220, 270])  # Others
        xy1.set_xlim([5, 310])
        xy1.set_ylim([0, 800])
        xy1.set_yticks(np.arange(50, 850, 100))
    elif msm_id == 5016:
        xy1.set_xticks([60, 160, 260, 360, 460])
        xy1.set_xlim([55, 520])
        xy1.set_ylim([0, 125])
        xy1.set_yticks(np.arange(20, 140, 20))

    xy1.tick_params(axis='x', labelsize=tkp)
    xy1.set_xlabel("min traceroute packets", fontsize=8, labelpad=3)
    xy1.tick_params(axis='y', labelsize=tkp)

    xy1.plot(tbs_obj.prune_pkts, tbs_obj.pc_edges,
             "bo-", ms=1.5, lw=0.5, label="Edges")  # markersize, linewidth
    xy1.plot(tbs_obj.prune_pkts, tbs_obj.pc_nodes,
             "r^-", ms=2.0, lw=0.5, label="Nodes")

    xy1.legend(loc="upper right", fontsize=lp)
    xy1.grid()

def plot_timebins(tbsa):  # First len(tbsa) plots for a single msm_id
    w = 7;  h = 3.1;  stp = 13;  tkp = 7;  tp = 11;  lp = 6
    cols = 4;  rows = 6  # 24 timebins
    #fig, axes = pplt.subplots(rows, cols, figsize=(10, 8))  # Inches (?)
    fig, axes = pplt.subplots(rows, cols, figsize=(9, 9))
    msm_id = tbsa[0].msm_id
    dest = msm_dests[msm_id][0]
    fig.suptitle("Prune by min_tr_pkts:  %d (%s), %s UTC" % (
        msm_id, dest, c.start_time.strftime("%A %Y-%m-%d")),
        fontsize=stp, horizontalalignment='center')
    pplt.subplots_adjust(left=None, bottom=None, right=0.9, top=0.92,
                         wspace=0.6, hspace=1.3)

#    y1 = {5017: 600, 5005: 700, 5006: 800, 5015:950, 5004:950, 5016:650}  # Nodes
#    y2 = {5017: 190, 5005:  85, 5006: 120, 5015:115, 5004:115, 5016:75}  # tr kpkts

    for tbn, tbs_obj in enumerate(tbsa):
        bin_time = c.start_time + datetime.timedelta(0, 30*60) * tbn
        r = int(tbn/cols);  cl = tbn%cols
        xy1 = axes[r,cl]
        tbs_obj = tbsa[tbn]
        #print("tbn = %d, tbs_obj = %s" % (tbn, tbs_obj))
        title = "bin %02d, %s" % (tbn, bin_time.strftime("%H%M"))
        plot_image(xy1, tp, tkp, lp, tbs_obj, title)

    #pplt.show()
    plot_fn = "%s/%s-n+e-v-min_tr_pkts-24bins.svg" % (start_ymd, c.dgs_stem)
    pplt.savefig(plot_fn)


def plot_single_bin(tbin, msm_a):  # Graphs for a list of msm_ids
    if len(msm_objs) <= 3:
        rows = 1;  cols = len(msm_a)
        w = 7*cols/3;  h = 3.4;  stp = 12;  tkp = 7;  tp = 9;  lp = 7
    elif len(msm_a) <= 6:
        rows = 2;  cols = 3
        w = 11.7;  h = 8.0;  stp = 18; tkp = 12;  tp = 12;  lp = 12
    else:
        print("Can't plot more than 6 msm_ids <<<")
    fig, axes = pplt.subplots(rows, cols, figsize=(w, h))  # Inches (?)

    if len(msm_a) < 6:  # ??
        pplt.subplots_adjust(left=0.13, bottom=0.135, right=None, top=0.9,
                             wspace=0.5, hspace=1.5)
    else:
        pplt.subplots_adjust(left=None, bottom=None, right=0.9, top=0.9,
                             wspace=0.8, hspace=1.0),

    for j, msm_obj in enumerate(msm_a):
        print("j = %d" % j)
        bin_time = c.start_time + datetime.timedelta(0, 30*60) * tbin
        r = j/cols;  cl = j%cols
        if rows == 1:
            if cols == 1:
                xy1 = axes
            else:
                xy1 = axes[cl]
        else:
            xy1 = axes[r,cl]
        tbs_obj = msm_obj.tbsa[tbin]
        plot_image(xy1, tp, tkp, lp, tbs_obj, None)

    #pplt.show()
    plot_fn = "%s/%s-n+e-v-min_tr_pkts.svg" % (start_ymd, c.dgs_stem)
    print("writing %s" % plot_fn)
    pplt.savefig(plot_fn)  # .svg gets % shown properly on OSX

#for b in range(c.n_bins):
#    bin_start = start_time + datetime.timedelta(0, 30*60) * b
#    print("bin %02d, %s" % (b, bin_start))
#    print("bin %02d, %s" % (b, bin_start.strftime("%H%M")))
#    print("bin %02d, %s" % (b, bin_start.strftime("%Y-%m-%d")))

#reqd_msm_ids = [5005];  n_bins = 24  # 4x6 array of plots for timebins 0-23
#reqd_msm_ids = c.msm_ids;  n_bins = 6  # Six msm_ids in config.c
reqd_msm_ids = [5017, 5005, 5016];  n_bins = 1  # msm_ids for paper diagram

msm_objs = []
if reqd_msm_ids:
    for msm_id in reqd_msm_ids:
        fn = c.stats_fn(msm_id)
        print("reqd stats_fn = %s" % fn)
        if os.path.isfile(fn):
            sa = fn.split("-");  mx_depth = int(sa[5])
            print("Stats report for file %s, mx_depth = %d" % (fn, mx_depth))
            mf_obj = mf.MsmFile(fn, n_bins)
            msm_objs.append(mf_obj)
    print("msm_objs = %s" % msm_objs)

    #for msm_obj in msm_objs:
    #    #plot_timebins(msm_obj.tbsa)  # Plot 4x6 array of timebins
    #    plot_single_bin(0, msm_objs)  # Plot only bin  0
    plot_single_bin(0, msm_objs)  # Plot only bin  0
else:
    for msm_id in c.msm_nbrs:
        fn = c.stats_fn(msm_id)
        print("reqd fn = %s" % fn)
        if os.path.isfile(fn):
            print("stats_fn = %s" % fn)
            sa = fn.split("-");  mx_depth = int(sa[5])
            print("Stats report for file %s, mx_depth = %d" % (fn, mx_depth))
            mf_obj = mf.MsmFile(fn, n_bins)
            msm_objs.append(mf_obj)
    plot_single_bin(0, msm_objs)  # Plot only bin  0

