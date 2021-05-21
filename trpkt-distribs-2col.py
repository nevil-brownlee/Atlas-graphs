# 1635, Tue 25 Aug 2020 (NZST)
#
# trpkt-distribs.2col.py: Plot node trpkts distribution
#    2 cols, [0,30] on left and [3,30k] on right
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

    nf = open(nfn, "r")
    mx_trp = 0
    for line in nf:
        la = line.split()
        in_count = int(la[1])
        if in_count > mx_trp:
            mx_trp = in_count
    nf.close()
    counts = np.zeros(mx_trp+1)
    nf = open(nfn, "r")
    for line in nf:
        la = line.split()
        in_count = int(la[1])
        counts[int(in_count)] += 1
    print("%s: mx_trp = %d" % (msm_id, mx_trp))

    tot_trpkts = np.sum(counts)
    yp = 100*counts/tot_trpkts  # Convert to percentages
    #print(y[0:60].astype(int))

    xa = np.ones(mx_trp+1);  xa[0] = 0
    x = np.cumsum(xa)  # x values

    return x, np.cumsum(yp)

def h_subplot(ax0,ax1, x,y, msm_id, pc_97):
    ax0.set_xlabel("in_count", fontsize=10)
    ax0.set_ylabel("% Nodes", fontsize=10)
    ax0.set_xlim([-1.5,32])
    ax0.set_xticks([1,3,6,9,12,15,18,21,24,27,30])
    ax0.set_ylim([15,105])
    #ax0.set_yticks(np.arange(10,110,20))
    ax0.set_yticks(np.arange(5,130,25))
    ax0.grid(True, which='both')
    ax0.text(21,33, "msm_id %d" % msm_id, fontsize=12)
    ax0.text(13,19, "97%% with in_count <= %2d" % pc_97, fontsize=12)
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

# W 2,1 horizontal  (adjust settings are fractions of window!)
n_msms = len(reqd_msms)
fig, axes = pplt.subplots(n_msms,2, figsize=(11,2.5*n_msms), squeeze=False)
#print("axes >%s< %s" % (axes, np.shape(axes)))
pplt.subplots_adjust(left=0.08, bottom=0.06, right=0.95, top=0.93,
                     wspace=0.24, hspace=0.66)  # 0.67

dt = c.date_from_ymd(reqd_ymds[0], c.start_hhmm)
fig.suptitle("Node in_count cumulative %% distributions: %s" % \
    dt.strftime("%a %d %b %Y (UTC)"), \
    fontsize=14,horizontalalignment='center')

for n,msm_id in enumerate(reqd_msms):
    x,y = counts_array(msm_id)
    print("msm_id %d, y[1:5] = %d %d %d %d" % (
        msm_id, y[1],y[2],y[3],y[4]))
    h_subplot(axes[n,0],axes[n,1], x,y, msm_id, np.argmax(y>=97))

#pplt.show()
pplt.savefig("in_size_pc.svg")
 
