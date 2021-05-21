# 1204, Fri 22 Jan 2021 (NZDT)
#
# node-depth-distribs.py: Plot node depths distribution
#    2 plots [0,30] at top and [3,30k] below
#    one line per msm_id, with key at right
#
# Copyright 2021, Nevil Brownlee,  U Auckland | RIPE NCC

import numpy as np
import scipy.stats
from matplotlib import pyplot as pplt

import config as c

plot_pc = False  # Actual counts are more interesting than percentages
reqd_ymds = [];  reqd_msms = [];  plot_cum = False
pp_names = "m! y! cum"  # indeces 0 to 2
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
for n,ix in enumerate(pp_ix):
    if ix == 0:    # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 2:  # cum  plot cummulative distribs
        plot_cum = True
    else:
        exit()
if len(reqd_ymds) == 0:    reqd_ymds = [c.start_ymd]
elif len(reqd_ymds) > 1:
    print("More than one ymd specified!");  exit()
c.set_ymd(reqd_ymds[0])
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("reqd_ymds %s, reqd_msms %s" % (reqd_ymds, reqd_msms))

pcs = ""
if plot_pc:
    pcs = "% "
dist_type = "";  plot_fn = "depths.svg"
if plot_cum:
    dist_type = "cummulative ";  plot_fn = "cum-depths.svg"

def counts_array(msm_id):
    nfn = c.nodes_fn(msm_id)
    print("msm_id %s, nodes_fn = %s" % (msm_id, nfn))

    mx_depth = 80  # 5015 in 20120222 reached 75
    xa = np.ones(mx_depth+1);  xa[0] = 0
    x = np.flip(np.cumsum(xa))  # x values (mx_depth down to 0)
    print("x = %s" % x)

    depths = np.zeros(mx_depth+1)
    nf = open(nfn, "r")
    for line in nf:
        la = line.split()
        depth = int(la[2])
        depths[depth] += 1
    if plot_cum:
        csd = np.cumsum(np.flip(depths))
    else:
        csd = np.flip(depths)
    #for d in range(0,mx_depth):
    #    print("%8d  %6d" % (d, depths[d]))
    print("%s: mx_depth %d, total nodes %d" % (msm_id, mx_depth, csd[-1]))
    if not plot_pc:
        return x, csd  # Return depths

    tot_depths = np.sum(depths)
    yp = 100*depths/tot_depths  # Convert to percentages
    ##print(y[0:60].astype(int))
    return x, np.cumsum(yp)  # Return percentages

def draw_axes(ax):  # Set axes
    #print("draw_axes(%d)" % n)
    ax.set_ylabel("%sNodes" % pcs, fontsize=12)  # 10
    ax.set_xlabel("Depth", fontsize=12)  # 10
    ax.set_xlim([38,-1])
    #ax.set_xlim([-1.5,32])
    #ax.set_xticks([1,3,6,9,12,15,18,21,24,27,30])
    #ax.set_ylim([15,105])
    #ax.set_yticks(np.arange(5,130,25))
    ax.grid(True, which='both')


# W 1,1 horizontal  (adjust settings are fractions of window!)

#               0        1      2               3       4
colours = ['black', 'brown', 'red',   'darkorange', 'gold',
#               5       6         7       8            9       10
           'green', 'blue', 'violet', 'grey', 'lightblue', 'black']

dt = c.date_from_ymd(reqd_ymds[0], c.start_hhmm)

fig, axes = pplt.subplots(1,1, figsize=(10,4.5), squeeze=False)
pplt.subplots_adjust(left=0.12, bottom=0.1, right=0.87, top=0.95)
#pplt.subplots_adjust(left=0.12, bottom=0.14, right=0.87, top=0.87)
#                     wspace=0.24, hspace=0.66)
ax = axes[0,0]

#fig.suptitle("Node depth %s%sdistributions: %s" % \
#    (pcs, dist_type, dt.strftime("%a %d %b %Y (UTC)")), \
#    fontsize=12, horizontalalignment='center')

draw_axes(ax)

for n,msm_id in enumerate(reqd_msms):
    x,y = counts_array(msm_id)
    ax.plot(x,y, label=str(msm_id),
        color=colours[n], marker='o', markersize=3)
leg = ax.legend(loc="center right", # prop size for lines in legend
    bbox_to_anchor=(0.342,0.63), prop={"size":12}, frameon=True)
leg.set_title(title="msm_id", prop={'size':14})  # For legend title


#pplt.show()
pplt.savefig(plot_fn)
