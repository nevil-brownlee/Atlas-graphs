# 1555, Sat 29 Aug 2020 (NZST)
#
# depth-distribution.py: Plot node depth distribution
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import numpy as np
import scipy.stats
from matplotlib import pyplot as pplt

import config as c

reqd_ymds = [];  reqd_msms = []
pp_names = "m! y!"  # indeces 0 to 1
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
for n,ix in enumerate(pp_ix):
    if ix == 0:    # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
elif len(reqd_ymds) > 1:
    print("More than one ymd specified!");  exit()
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
    print("reqd_ymds %s, reqd_msms %s" % (reqd_ymds, reqd_msms))

def counts_array(msm_id):
    nfn = c.nodes_fn(msm_id)
    print("nodes_fn = %s" % nfn)
    mx_depth = 0
    counts = np.zeros(61)
    nf = open(nfn, "r")
    for line in nf:
        la = line.split()
        depth = int(la[2])
        if depth > mx_depth:
            mx_depth = depth
        counts[depth] += 1
    print("%s: mx_depth = %d" % (msm_id, mx_depth))

    tot_depths = np.sum(counts)
    yp = 100*counts/tot_depths  # Convert to percentages
    #print(yp.astype(float))  #print(yp.astype(int))

    xa = np.ones(mx_depth+1);  xa[0] = 0
    x = np.cumsum(xa)  # x values

    return x[:mx_depth+1], np.cumsum(yp)[:mx_depth+1]

'''
def h_subplot(ax0,ax1, x,y, msm_id, pc_97):
    ax0.set_xlabel("in_count", fontsize=10)
    ax0.set_ylabel("% Nodes", fontsize=10)
    ax0.set_xlim([-1.5,32])
    ax0.set_xticks([1,3,6,9,12,15,18,21,24,27,30])
    ax1.set_ylim([22,105])
    ax0.set_yticks([30,50,70,90],minor=True)
    ax0.grid(True, which='both')
    ax0.text(21,42, "msm_id %d" % msm_id, fontsize=12)
    ax0.text(13,32, "97%% with in_count <= %2d" % pc_97, fontsize=12)
    ax0.plot(x[:31],y[:31])

    ax1.set_xlabel("in_count", fontsize=10)
    ax1.set_ylabel("% Nodes", fontsize=10)
    ax1.set_xscale('log')
    ax1.set_yscale('linear')  # But both axes drawn log-scaled !!
    ax1.set_xlim([21,38000])
    ax1.set_xticks([30, 100, 300, 1000, 3000, 10000, 30000])
    ax1.set_xticklabels(['30', '100', '300', '1000', '3000', '10k', '30k'])
    ax1.set_ylim([96.65,100.2])
    ax1.set_yticks([97.5,98.5,99.5],minor=True)
    ax1.grid(True, which='both')
    ax1.text(4300, 97.05, "msm_id %d\n%5d Nodes" \
             % (msm_id, len(y)-1), fontsize=12)
    ax1.plot(x[26:],y[26:])
    #ax1.semilogy(x[26:],y[26:])  # This doesn't work!!
'''
def d_subplot(ax, x,y, msm_id):
    ax.set_xlabel("depth", fontsize=10)
    ax.set_ylabel("% Nodes", fontsize=10)
    #ax.set_yscale('log')
    ax.set_xlim([-1,42])  #len(x)+1])
    ax.set_xticks(np.arange(0,45,5))
    ax.set_ylim([-5,105])
    ax.set_yticks([0,30,60,90])
    ax.grid(True, which='both')
    ax.text(30,15, "msm_id %d" % msm_id, fontsize=12)
    #ax.text(13,32, "97%% with in_count <= %2d" % pc_97, fontsize=12)
    ax.plot(x,y)

n_msms = len(reqd_msms)
'''
# W 2,1 horizontal  (adjust settings are fractions of window!)
fig, axes = pplt.subplots(n_msms,2, figsize=(11,2.5*n_msms), squeeze=False)
#print("axes >%s< %s" % (axes, np.shape(axes)))
pplt.subplots_adjust(left=0.08, bottom=0.06, right=0.95, top=0.93,
                     wspace=0.24, hspace=0.66)  # 0.67
'''

fig, axes = pplt.subplots(n_msms,1, figsize=(8,1+3*n_msms), squeeze=False)
pplt.subplots_adjust(left=0.12, bottom=0.11, right=0.95, top=0.94,
                     wspace=0.20, hspace=0.80)  # 0.67
print("axes >%s< %s" % (axes, np.shape(axes)))

dt = c.date_from_ymd(reqd_ymds[0], c.start_hhmm)
fig.suptitle("Node depth cumulative %% distributions: %s" % \
    dt.strftime("%a %d %b %Y (UTC)"), \
    fontsize=14,horizontalalignment='center')

p_xlim = 41
for n,msm_id in enumerate(reqd_msms):
    x,y = counts_array(msm_id)
    #print("len(x)=%d, len(y)=%d, x %s, y %s" % (len(x), len(y), x, y))
    d_subplot(axes[n,0], x[:p_xlim],y[:p_xlim], msm_id)

#pplt.show()
pplt.savefig("depth_pc.svg")
 
