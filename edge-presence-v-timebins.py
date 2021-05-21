# 1617, Wed 24 Feb 2021 (NZDT)
# 1658, Sun 30 Jun 2019(NZST)
# 1802, Thu  1 Mar 2018 (NZDT)
# 1427, Tue  1 Aug 2017 (NZST)
#
# edge-presence-v-timebins.py: plot cum_edge_presence
#
# Copyright 2021, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
import matplotlib.pyplot as pplt
from matplotlib import patches
from mpl_toolkits import mplot3d
import math, datetime, pickle

import graph_info  # Edge, Path, NodeInfo and GraphInfo classes
import dgs_ld

import config as c

reqd_ymds = [];  reqd_msms = []
pc_graph = cum_plots = False;  n_cols = 3;  suffix = ""
pp_names = "y! m! p a cum cols! sufx!"  # indexes 0 to 6
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default parameters for drawing
mn_trpkts = c.draw_mn_trpkts
asn_graphs = not c.full_graphs
for n,ix in enumerate(pp_ix):
    if ix == 0:    # y  (yyyymmdd) dates
        reqd_ymds = pp_values[n]
        ymd_pos = n
    elif ix == 1:  # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
        msm_pos = n
    elif ix == 2:  # p  Convert edge counts to % of all edges
        pc_graph = pp_values[n]
    elif ix == 3:  # a sets full_graphs F to use ASN graphs
        asn_graphs = True;  c.set_full_graphs(False)
    elif ix == 4:  # cum sets cum_plots to produce cummulative plots
        cum_plots = True
    elif ix == 5:  # cols  sets n_cols for sub_plots
        n_cols = int(pp_values[n][0])
    elif ix == 6:  # sufx  suffix for output file name
        suffix = "-%s" % pp_values[n][0]
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
ymd_first = ymd_pos < msm_pos
print("reqd_ymds %s, reqd_msms %s, ymd_first %s, n_cols %s, sufx %s" % (
    reqd_ymds, reqd_msms, ymd_first, n_cols, suffix))
        
#n_bins = 48  # 1 day
#n_bins = 48*3  # 3 days
n_bins = c.n_bins*c.n_days  # 1 week

sup_title = False

node_dir = {}  # Dictionary  IPprefix -> ASN
no_asn_nodes = {}

def plot_asn_counts(ymda, msma, gfa):  # Plot counts (nbr of times pc[x] was seen)
    pca = [];  inter_ca = []
    for g in range(0,len(gfa)):
        gf = gfa[g]
        same_counts, inter_counts = gf.asn_edges()
        print("msm_id = %s  <<<\n" % msma[n])
        pca.append(same_counts);  inter_ca.append(inter_counts)

    #  pca and inter_ca are np 1D arrays of counts, one for each ymd/msm_id
    iv = np.cumsum(np.ones(n_bins))  # integers 1:48
    xv = np.insert(iv, 0, 0)  # integers 0:49, i.e. [0,48]
    print("      pc_graph = %s" % pc_graph)
    pcc = [];  inter_cc = []
    same_max = [];  inter_max = []
    for mx in range(0,len(pca)):
        if cum_plots:
            cc = np.cumsum(pca[mx])  # Cumulative counts
            icc = np.cumsum(inter_ca[mx])
        else:
            cc = pca[mx];  icc = inter_ca[mx]
        same_max.append(cc[-1]);  inter_max.append(icc[-1])
        if pc_graph:
            tcounts = cc[-1]+icc[-1]  # Total counts
            cc = cc*(100.0/tcounts)
            icc = icc*(100.0/tcounts)
        pcc.append(cc)
        inter_cc.append(icc)

    if cum_plots:
        cum = "Cummulative "
        which = "cum-counts"
        if pc_graph:
            which = "cum-pc"
    else:
        cum = ""
        which = "counts"
        if pc_graph:
            which = "percent"

    if c.full_graphs:
        title = "Full graph: edge presence (%s)" % which
        pfn = "edge-presence-full-%s%s.svg" % (which, suffix)
    else:
        title = "ASN graph: edge presence (%s)" % which
        pfn = "inter-asn-%s%s.svg" % ( which, suffix)

        dt = c.date_from_ymd(ymd, c.start_hhmm)
        title = "%sEdge Presence:  %s" % \
            (cum, dt.strftime("%a %d %b %Y (UTC)"))
    print("pfn = %s" % pfn)

    if len(msma) <= 4:
        rows = 1;  cols = len(msma)
        #w = 8;  h = 3.4;  stp = 12;  tkp = 7;  tp = 12
        w = 10;  h = 3.0;  stp = 12;  tkp = 7;  tp = 12
    else:
        rows = 2;  cols = int(len(msma)/2)
        w = 10;  h = 7;  stp = 12;  tkp = 7;  tp = 12
    #print("+1+ pc %s, len(ids) %d, rows %d, cols %d" % (pc_graph, len(ids), rows, cols))

    if sup_title:
        fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches
        if len(reqd_msms) <= 4:
            pplt.subplots_adjust(left=0.125, bottom=0.135,
                #right=None, top=0.9, wspace=0.5, hspace=0.85)
                right=None, top=0.85, wspace=0.5, hspace=0.85)
        else:
            pplt.subplots_adjust(left=0.125, bottom=0.08,
                right=None, top=0.9, wspace=0.5, hspace=0.35)
        fig.suptitle(title, fontsize=14, horizontalalignment='center')
    else:
        fig, axes = pplt.subplots(rows, cols, figsize=(w,h))  # Inches
        if len(msma) < 4:
            pplt.subplots_adjust(left=0.125, bottom=0.1,
                #right=None, top=0.9, wspace=0.5, hspace=0.85)
                right=None, top=0.95, wspace=0.5, hspace=0.85)
        else:
            pplt.subplots_adjust(left=0.125, bottom=0.07,
                #right=None, top=0.95, wspace=0.55, hspace=0.28)
                right=None, top=0.97, wspace=0.5, hspace=0.3)

    for f in range(rows*cols):
        ymd = ymda[f];  msm_id = msma[f]
        msm_dest = c.msm_dests[msm_id]
        ls = "%s/%s, %s" % (ymd[0:4], msm_id, msm_dest[0])
        r = int(f/cols);  nc = f%cols
        if rows == 1:
            xy = axes[nc]  # axes from pplt.sublots()
        else:
            xy = axes[r,nc]        
        #xy.set_title(ls, fontsize=12)
        xy.set_title(ls, fontsize=10)
        xy.set_xlabel("timebins present")
        if pc_graph:
            xy.set_ylabel("% edges")
        else:
            xy.set_ylabel("edges present")
        xy.tick_params(axis='x', labelsize=tkp)
        ntb = len(pcc[0])
        #print("ntb = %d, n_bins = %d" % (ntb, n_bins))
        xtick_incr = int(n_bins/8)
        xy.set_xticks(range(0,9*xtick_incr, xtick_incr))
        xy.set_xlim(-int(0.25*xtick_incr), int(8.45*xtick_incr))  # x axis lims
        xy.tick_params(axis='y', labelsize=tkp)
        if pc_graph:
            ymax = 80  #? 70
        else:
            cc_max = np.max(pcc[f])
            icc_max = np.max(inter_cc[f])
            if icc_max > cc_max:
                cc_max = icc_max
            ymax = int(cc_max*1.05)
        xy.set_ylim(-2, ymax)  # y axis limits
        xy.plot(xv, pcc[f], label="%4d same ASN" % same_max[f])
        xy.plot(xv, inter_cc[f], label="%4d inter-ASN" % inter_max[f])
        xy.legend(loc="upper left", title="Edge type", fontsize=5,
                  bbox_to_anchor=(0.03,0.99), prop={"size":7}, handlelength=1)
            # fontsize for labels, "size" for heading
        xy.grid()
    pplt.savefig(pfn)

#               0        1      2               3       4
colours = ['black', 'brown', 'red',   'darkorange', 'gold',
#               5       6         7       8            9       10
           'green', 'blue', 'violet', 'grey', 'lightblue', 'black']

def get_asn_counts_arrays(ymda, msma, gf):
    e_dict = gf.all_edges
    same_counts = np.zeros(shape=(49,49))  # presence x depth
    inter_counts = np.zeros(shape=(49,49))  # 49 rows x cols
    for ek in e_dict:
        e = e_dict[ek]
        #print("%4d: %s depth %d" % (n, e, d))
        d = e.n_depth
        p = np.count_nonzero(e.icounts)
        if d >= 49 or p >= 49:
            continue
        if e.asn_from == e.asn_to:
            same_counts[p,d] += 1
        else:
            inter_counts[p,d] += 1
    return same_counts, inter_counts

def plot_3d_asn_edges(ymda, msma, gfa):  # Scatter plots of asn counts
    for g in range(0, len(gfa)):
        same_counts, inter_counts = get_asn_counts_arrays(ymda, msma, gfa[g])
        # 3D plot ranges
        xmn = 1;  xmx = 48  # presence
        ymn = 2;  ymx = 10  # depth
        xr = xmx+1 - xmn
        yr = ymx+1 - ymn
        s_sz = xr*yr

        x_s = np.zeros(s_sz)  # presence
        y_s = np.zeros(s_sz)  # depth
        z_s = np.zeros(s_sz)  # z_same
        x_i = np.zeros(s_sz)  # presence
        y_i = np.zeros(s_sz)  # depth
        z_i = np.zeros(s_sz)  # z_inter

        n_same = n_inter = 0  # index of each sample in x,y,z arrays
        for p in range(xmn,xmx+1):
            for d in range(ymn,ymx+1):
                z = same_counts[p,d]
                if z > 0:
                    x_s[n_same] = p;  y_s[n_same] = d
                    z_s[n_same] = z
                    n_same += 1
                z = inter_counts[p,d]
                if z > 0:
                    x_i[n_inter] = p;  y_i[n_inter] = d
                    z_i[n_inter] = z
                    n_inter += 1

        fig1 = pplt.figure(num=1, figsize=(10,7))
        ax1 = pplt.axes(projection="3d")
        ax1.set_xlabel("Presence")
        ax1.set_ylabel("Depth")
        ax1.set_zlabel("Same-ASNs")
        ax1.view_init(elev=38, azim=149)  # Degrees
        ax1.scatter(x_s[:n_same], y_s[:n_same], z_s[:n_same],
            c='g', marker='o')
        fn = "%s/%s-3d-Same-ASNs.svg" % (ymd, msm_id)
        pplt.suptitle(fn)
        pplt.savefig(fn)

        fig2 = pplt.figure(num=2, figsize=(10,7))
        ax2 = pplt.axes(projection="3d")
        ax2.set_xlabel("Presence")
        ax2.set_ylabel("Depth")
        ax2.set_zlabel("Inter-ASNs")
        ax2.view_init(elev=38, azim=149)  # Degrees
        ax2.scatter(x_i[:n_inter], y_i[:n_inter], z_i[:n_inter], 
            c='r', marker='o')
        fn = "%s/%s-3d-Inter-ASNs.svg" % (ymd, msm_id)
        pplt.suptitle(fn)
        pplt.savefig(fn)
        #pplt.show()

def plot_asn_edges_v_depth(ymda, msma, gfa, pl):
    # pl is a list of depths to use
    fig, axes = pplt.subplots(2,1, figsize=(10,7), squeeze=False)
    pplt.subplots_adjust(left=0.12, bottom=0.1,
        right=0.87, top=0.97, wspace=0.5, hspace=0.27)

    def p_vals(pl):
        pv = pl[0]
        ps = str(pv)
        if len(pl) != 1:
            for j,p in enumerate(pl[1:]):
                if p != pv+1:
                    ps += "-%s" % p
                pv = p

            ps += "-%s" % pv
        return ps
    #print(">%s<" % p_vals(pl))
    pv_s = p_vals(pl)

    dx = {}
    for n,p in enumerate(pl):
        dx[p] = n
    #print("dx = %s" % dx)
    if ymd_first:
        pfn = "Edges-v-Depth-msm-presence-%s%s.svg" % (pv_s, suffix)
    else:
        pfn = "Edges-v-Depth-ymd-presence-%s%s.svg" % (pv_s, suffix)

    ds = "Dataset ID"
    if len(reqd_ymds) == 1:
        ds = "%s Datasets" % ymda[0][:4]

    mx_d = 40
    x = np.arange(0,mx_d+1)

    tot_ya_s = np.zeros(mx_d+1);  tot_ya_i = np.zeros(mx_d+1)
    for gg in range(0, len(gfa)):
        gf = gfa[gg];  e_dict = gf.all_edges
        ya_s = np.zeros(shape=(len(pl),mx_d+1))  # One row per depth {0:mx_d-1]
        ya_i = np.zeros(shape=(len(pl),mx_d+1))  # Inter-ASNs
        e_dict = gf.all_edges
        for ek in e_dict:
            e = e_dict[ek]
            p = np.count_nonzero(e.icounts)
            if p in pl:
                d = e.n_depth
                if d <= mx_d:
                    if e.asn_from == e.asn_to:
                        #ya_s[dx[p],d] += 1
                        tot_ya_s[d] += 1  # Sums for all presences in list
                    else:
                        #ya_i[dx[p],d] += 1
                        tot_ya_i[d] += 1  # Sums


        if len(reqd_ymds) == 1:  # Only one year requested
            ts = "%s" % msma[gg]
        else:
            ts = "%s/%s" % (ymda[gg],msma[gg])

        ax = axes[0,0]
        ax.set_ylabel("Edges", fontsize=12)
        ax.set_xlabel("Depth for Same-ASN edges with presence %s" % pv_s,
            fontsize=12)
        ax.set_xlim([38,-1])
        ax.grid(True, which='both')
        #ax.plot(x,ya_s[0], label=ts,
        ax.plot(x,tot_ya_s, label=ts,
            color=colours[gg], marker='s', markersize=3)
        leg = ax.legend(loc="center right", # prop size for lines in legend
            bbox_to_anchor=(0.342,0.63), prop={"size":12}, frameon=True)
        leg.set_title(title=ds, prop={'size':14})  # For legend title

        ax = axes[1,0]
        ax.set_ylabel("Edges", fontsize=12)
        ax.set_xlabel("Depth for Inter-ASN edges with presence %s" % pv_s,
            fontsize=12)
        ax.set_xlim([38,-1])
        ax.grid(True, which='both')
        #ax.plot(x,ya_i[0], label=ts,
        ax.plot(x,tot_ya_i, label=ts,
            color=colours[gg], marker='D', markersize=3)
        leg = ax.legend(loc="center right", # prop size for lines in legend
            bbox_to_anchor=(0.342,0.63), prop={"size":12}, frameon=True)
        leg.set_title(title=ds, prop={'size':14})  # For legend title

    pplt.savefig(pfn)  # Must come before show !!!
    #pplt.show()


ymda = [];  msma = [];  gfa = []
if ymd_first:
    for ymd in reqd_ymds:
        c.start_ymd = ymd  # fn_ functions in config.py use ymd !!!
        for msm_id in reqd_msms:        
            pfn = c.pickle_fn(ymd, msm_id)
            print("will read %s" % pfn)
            pf = open(pfn, "rb")
            gf = pickle.load(pf)
            pf.close()
            ymda.append(ymd);  msma.append(msm_id);  gfa.append(gf)
else:
    for msm_id in reqd_msms:
        for ymd in reqd_ymds:
            pfn = c.pickle_fn(ymd, msm_id)
            print("will read %s" % pfn)
            pf = open(pfn, "rb")
            gf = pickle.load(pf)
            pf.close()
            ymda.append(ymd);  msma.append(msm_id);  gfa.append(gf)

#plot_asn_counts(ymda, msma, gfa)  # Fig 5 4, years x 5017 and 5005 ASN edges

#plot_3d_asn_edges(ymda, msma, gfa)

plot_asn_edges_v_depth(ymda, msma, gfa, [47,48])  # Fig 4,depth for ASN edges
#plot_asn_edges_v_depth(ymda, msma, gfa, [1,2,3,4,5,6])
#plot_asn_edges_v_depth(ymda, msma, gfa, [23,24,25])

