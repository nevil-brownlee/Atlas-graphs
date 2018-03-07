# 1006, Fri 31 Mar 2017 (CST)
#
# gather-presence.py: get info about ASNs (or nodes) over timebins
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

# CAUTION: run using python3, pypy needs its own version (numpypy)

import numpy as np  # Operations on arrays
import numpy.ma as ma
#import scipy as sc  # Statistics functions for np arrays
import scipy.stats as scs
import matplotlib as mpl
import matplotlib.pyplot as pplt
#import math
import scipy.ndimage.filters as scf

import copy, os.path

import config as c
c.set_pp(False, c.msm_id)  # Work on graphs-* file

#n_bins = 48  # 1 day
#n_bins = 48*3  # 3 days
n_bins = c.n_bins*c.n_days  # 1 week

class NodeInfo:
    tg       = 0;   tr = 1;    ts = 2;   tb = 3;  tf = 4;  tu = 5
    t_str = ['gone', 'root',' sub-root', 'branch', 'leaf', 'unknown <<<']

    def update(self, bn, icount, fails, roots):  # Sets .kind for each bin
        self.icount[bn] = icount;  self.fails[bn] = fails
        self.present[bn] = 1
        if self.root:
            kind = self.tr  # Root
        elif icount == 0:
            kind = self.tf  # Leaf
        elif fails == -1:  # Version 1 graphs file, i.e. full_graphs
            if self.name in roots:
                kind = self.ts  # Sub-root
            else:
                kind = self.tb  # Branch
        else:  # Version 2 graphs file, i.e. ASN graphs
            if fails == 0:
                kind = self.tb  # Branch
            else:
                kind = self.ts  # Sub-root

        self.counts[kind] += 1
        self.kind[bn] = kind
            
    def __init__(self, bn, dest, name, icount, fails, roots):
        print("bin %d, roots = %s" % (bn, roots))
        self.name = name;  self.root = name == dest
        ##print(">> %s  %s  %s" % (name, dest, self.root))
        self.icount = [0]*n_bins;  self.fails = [0]*n_bins
        self.present = [0]*n_bins;  self.kind = [self.tg]*n_bins
        self.counts = [0]*len(self.t_str)
        self.update(bn, icount, fails, roots)  # 6939

    def __str__(self):
        there = ''
        for bn in range(0, n_bins):
            there += str(self.present[bn])
        return "%20s: %8.1f %8.1f %s" % (self.name, 
            self.ic_mean, self.ic_fails, there)

    def show_stats(self, name, msg, a):
        #min = np.ma.min(a)
        nz_len = len(a[a != 0])
        pc10 = np.percentile(a, 10.0)
        mean = np.ma.mean(a)
        mode, mva = scs.mode(a, axis=None)  # scipy.stats.mode
        mode = mode[0]  # Most popular value
        pc90 = np.percentile(a, 90.0)
        #max = np.ma.max(a)
        #std = np.ma.std(a)  # Standard deviation
        if mean > 5.0:
            print("%s, %s: len %d 10%% %.2f, mean %.2f, mode %.2f, 90%% %.2f" % (
                msg, name, nz_len, pc10, mean, mode, pc90))

    def compute_stats(self):
        present = np.array(self.present)
        self.seen = np.sum(self.present)
        icount = np.array(self.icount)
        nz_icount = icount[icount != 0]
        if len(nz_icount) == n_bins:
            av_icount = np.mean(icount)
            self.pc_icount = icount*100.0/np.mean(icount) - 100.0
            self.pc_range = np.max(self.pc_icount) - np.min(self.pc_icount)
            print(">> %s: pc_range = %.2f" % (self.name, self.pc_range))
            #?dev2 = np.max(self.pc_icount)-np.min(self.pc_icount)
            #?print("%s dev2 = %.2f" % (self.name, dev2))
        else:  # Not seen in every bin
            self.pc_icount = self.pc_range = False

        fails = np.array(self.fails)
        self.ic_mean = np.mean(icount[present])
        self.ic_fails = np.mean(fails[present])

        last_icount = copy.deepcopy(self.icount)  # Diffs between timebins
        last_icount.insert(0, 0);  last_icount.pop()
        last_icount = np.array(last_icount)
        last_icount[0] = icount[0]  # Zero change for bin 0
        diff = np.subtract(self.icount, last_icount)
        if len(nz_icount) != 0:
            mean_icount = np.mean(nz_icount)
            self.pc = diff*100.0/mean_icount
            self.show_stats("icount %", self. name, np.absolute(self.pc))

        #print("ASN %s (%s)" % (self.name, self.types[self.ntype+1]))
        #print("  masked mean(icount) = %d" %  self.m_mean
        #print()

class PresenceInfo:
    def __init__(self, msm_id):
        self.msm_id = msm_id
        self.ba = []  # List of array rows
        self.nodes = {}  # Dictionary, for all nodes seen in DestGraph
        self.tbx = np.array(list(range(0,n_bins)))
        self.type = None  # (Predominant) kind

        fn = c.msm_graphs_fn(msm_id)
        print(" >>> %d: %s" % (msm_id, fn))
        f = open(fn, 'r')
        gf_version = 1
        bn = 0
        for line in f:
            la = line.strip().split(' ',maxsplit=1)
            if la[0] == "BinGraph":
                bv = la[1].rsplit(' ',maxsplit=1)
                bn = int(bv[1])
                if bn == n_bins:
                    break
                #n_traces, n_succ_traces, n_dup_traces, \
                #    t_addrs, t_hops, t_hops_deleted, bin_nbr = la[1:]
                roots_line = f.readline()
                la2 = roots_line.strip().split()
                mx_edges = la2.pop(0)
                la.append(mx_edges)
                la = "%s %s %d" % (bv[0], mx_edges, len(la2))
            elif la[0] == "Node":
                nv = la[1].split(' ')
                name = nv[0];  subnet = int(nv[1]);  icount = int(nv[2])
                fails = -1  # Not in v1 graphs file
                if gf_version != 1:
                    fails = int(nv[3])
                if name in self.nodes:
                    self.nodes[name].update(bn, icount, fails, la2)
                else:
                    self.nodes[name] = \
                        NodeInfo(bn, dest, name, icount, fails, la2)
                s_nodes_line = f.readline()  # s_nodes line
            elif la[0] == "DestGraphs":
                nv = la[1].split()  # One or more white-space chars
                dest = nv[1]
                if len(nv) > 7:
                    gf_version = 2
        f.close()

        #for nk in self.nodes:
        #    print(self.nodes[nk])

    def plot(self, node_names):  # Plot pc-icount
        rows = len(node_names)  # *3
        plot_height = 1.0
        fig, axes = pplt.subplots(ncols=1, nrows=rows, sharex='col',
                                  figsize=(10, rows*plot_height))
        ##                          figsize=(rows, rows*plot_height))
        #top_mult = 0.0005
        pplt.subplots_adjust(left=0.27, bottom=None, right=None,
                             top=0.92, hspace=0.4)  # 0.5 0.6 0.7
        #                     top=0.93-rows*top_mult, hspace=0.4)
        where, mx_depth, prune_pc = c.msm_dests[self.msm_id]
        fig.suptitle("%d (%s, %d, %.1f%%): icount percent diffs from mean" % ( 
            self.msm_id, where, mx_depth, prune_pc),
            fontsize=14, horizontalalignment='center')
        for r,node_name in enumerate(node_names):
            node = self.nodes[node_name]
            #ax = axes[r*3]
            #ax.set_xlim(-2, n_bins+2)
            #ax.set_xticks(list(range(0,360,24)))
            #ax.set_ylim(-45.0,45.0)
            #ax.set_yticks(list(range(-30,45,15)))
            #ax.grid(which='major', axis='x', color='black', linewidth=0.3)
            #ax.text(-40, -7, node.name.rjust(18,' '),
            #    horizontalalignment='right')  # Axis units
            #ax.plot(self.tbx,www.easychair.com node.pc_icount)
            
            mf_pci = scf.median_filter(node.pc_icount, size=12) # 12
            #ax = axes[r*3+1]
            if len(node_names) == 1:
                ax = axes
            else:
                ax = axes[r]
            ax.set_xlim(-2, n_bins+2)
            ax.set_xticks(list(range(0,360,24)), minor=True)
            ax.grid(which='minor', axis='x', color='black',
                linewidth=0.5,  linestyle='--')
            ax.set_xticks(list(range(0,360,48)), minor=False)
            ax.grid(which='major', axis='x', color='black', linewidth=0.8)
            ax.set_ylim(-45.0,45.0)
            ax.set_yticks(list(range(-30,45,15)))
            nn = node.name + "\n%.1f%% of %d" % (
                np.median(node.pc_icount), np.median(node.icount))

            ##ax.text(-40, -7, node.name.rjust(18,' '),
            ax.text(-40, -7, nn.rjust(18,' '),
                horizontalalignment='right')  # Axis units
            ax.plot(self.tbx, mf_pci)
 
            #pci_slope = np.zeros(n_bins)
            #dx_reqd = 10.0  # percent 8
            #for x in range(1,n_bins):
            #    dx = mf_pci[x] - mf_pci[x-1]
            #    if dx > dx_reqd:
            #        pci_slope[x] = +1
            #    elif dx < -dx_reqd:
            #        pci_slope[x] = -1
            #    else:
            #        pci_slope[x] = 0
            #    if pci_slope[x] != 0:
            #        print("%s, %d, %.1f" % (node_name.rjust(20,' '), x, dx))

            ##print("==> %s" %  pci_slope)
            #pci_step = np.zeros(n_bins)
            #last_step_value = 0;  last_step_x = 0
            #for x in range(1,n_bins):
            #    step_value = pci_slope[x]
            #    if step_value != 0:  # Slope change
            #        print("   %d  step val change" % x)
            #        if step_value == last_step_value:
            #            # Two in same direction within 6: ignore first
            #            last_step_x = x
            #        else:  # Two in opp dirs
            #            gap = x-last_step_x
            #            print("   %d Opp step, gap = %d" % (x, gap))
            #            if gap > 30:  # 15h
            #                print("   %d >30 bins, ignore" % x)
            #                last_step_x = x###;  last_step_value = step_value
            #            else:
            #                print("   %d Opp step, gap %d", (x, gap))
            #                for gx in range(last_step_x, x+1):
            #                    pci_step[gx] = -step_value
            #                last_step_x = x
            #            last_step_value += step_value

            #ax = axes[r*3+2]
            #ax.set_xlim(-2, n_bins+2)
            #ax.set_xticks(list(range(0,360,24)))
            #ax.set_ylim(-1.2,1.2)
            #ax.set_yticks([-1, 0, +1])
            #ax.grid(which='major', axis='x', color='black', linewidth=0.3)
            #ax.plot(self.tbx, pci_step)

        plot_dir = "pc-icount-full"
        if not c.full_graphs:
            plot_dir = "pc-icount-asn"
        if not os.path.exists(plot_dir):
            os.makedirs(plot_dir)
        pfn = "%s/pc-icount-%4d.svg" % (plot_dir, msm_id)
        pplt.savefig(pfn)
        #pplt.show()
        
    def node_key(self, name):  # sorted passes the dictionary key!
        return self.nodes[name].ic_mean

    def stats(self):  # as 9304 not in bin 0
        for name in self.nodes:
            self.nodes[name].compute_stats()
        node_names = []
        for name in sorted(self.nodes, key=self.node_key, reverse=True):
            node = self.nodes[name]
            #if np.any(node.pc_icount) and (node.seen == n_bins):  # No changes seen
            if node.pc_range >= 20.0:  # Looks about right for 6005 (!)
                ##print("%s: pc_icount %s" % (name, node.pc_icount))
                node_names.append(node.name)
        if len(node_names) != 0:
            self.plot(node_names)        
#        self.plot(['44530'])        


    def presence_key(self, name):  # sorted passes the dictionary key!
        return self.nodes[name].ic_mean

    def find_run_length(self, n):
        mx_run_lengths = [0]*len(n.t_str);  start_bns = [0]*len(n.t_str)
        n_runs = [0]*len(n.t_str)
        mx_kind = last_kind = n.kind[n.tg];  start_bn = 0
        run_len = 1;  mx_run_len = 0
        kind_changes = 0
        for bn in range(1, n_bins):
            if n.kind[bn] == last_kind:
                run_len += 1
            else:
                kind_changes += 1
                if run_len > mx_run_lengths[last_kind]:
                    mx_kind = last_kind
                    mx_run_lengths[last_kind] = run_len
                    start_bns[last_kind] = start_bn
                    n_runs[last_kind] += 1
                last_kind = n.kind[bn];  start_bn = bn;  run_len = 1
        if run_len > mx_run_lengths[last_kind]:
            mx_run_lengths[last_kind] = run_len
            start_bns[last_kind] = start_bn
            n_runs[last_kind] += 1
        n.kind_changes = kind_changes
        #return mx_kind, mx_run_lengths, start_bns, n_runs
        return mx_kind, np.array(mx_run_lengths), start_bns, n_runs
        
    def get_xy(self, x, y, v):
        m = ma.masked_not_equal(y, v)
        xv = ma.array(x, mask = m.mask)
        yv = ma.array(y, mask = m.mask)
        return xv, yv

    def node_rl_key(self, name):  # sorted passes the dictionary key!
        n = self.nodes[name]
        return n.kind_changes
        #return n.n_runs[NodeInfo.ts]
        #return n.counts[NodeInfo.tb]/n.counts[NodeInfo.ts]
        #return n.runs[NodeInfo.tb]/n.runs[NodeInfo.ts]

    def plot_presence(self):  # 
        print("- - - - - - - -")
        varying_nodes = []
        for name in self.nodes:
            self.nodes[name].compute_stats()
            n = self.nodes[name]
            ##print("%s: counts = %s" % (name, n.counts))

            n_counts = np.array(n.counts)
            nz_counts = len(n_counts[n_counts > 1])
            n.n_kind = np.array(n.kind)
            if nz_counts > 1:  # 1:
                mx_kind, mx_run_lengths, start_bns, n_runs = \
                    self.find_run_length(n)
                self.nodes[name].n_runs = n_runs
                print("%s:  mx_kind %s, n_runs %s" % (
                    name, n.t_str[mx_kind], n_runs))
                print("       n_runs %s" % mx_run_lengths)
                print("       start_bns %s" % start_bns)
                n.mx_run_length = np.max(mx_run_lengths)
                if n.mx_run_length != 336:
                    varying_nodes.append(name)

        rows = len(varying_nodes)
        print("==== %4d: rows = %d" % (self.msm_id, rows))
        if rows == 0:
            return
        th  = 0.7  # suptitle height
        sph = 1.0  # subplot height
        fig, axes = pplt.subplots(ncols=1, nrows=rows, sharex='col',
                                  figsize=(9, th + rows*sph))
        pplt.subplots_adjust(left=None, bottom=None, right=None,
                             top=1-th/(th+rows*sph), hspace=0.55)
        #                     top=0.955, hspace=0.5)
        #                     top=1.0-2*title_height/tph, hspace=0.5)
        where, mx_depth, prune_pc = c.msm_dests[self.msm_id]
        fig.suptitle("%d (%s, %d, %.1f%%): Node kind for each bin" % ( 
            self.msm_id, where, mx_depth, prune_pc),
            fontsize=12, horizontalalignment='center')
        self.tbx = np.array(list(range(0,n_bins)))
        #y_tick_labels =  ['root','sub-root', 'branch', 'leaf', 'xxx']
        y_tick_labels =  ['sub-root', 'branch', 'leaf', 'xxx']
        #for r,node_name in enumerate(varying_nodes):
        for r,node_name in enumerate(sorted(varying_nodes, key=self.node_rl_key, reverse=True)):
            n = self.nodes[node_name]
            ax = axes[r]
            nn = "%s  (median %d, mean %d)" % (
                node_name, np.median(n.icount), np.mean(n.icount))
            ax.set_xlabel("Node %s" % nn)  ###node_name)
            ax.set_xlim(-2, n_bins+2)
            ax.set_xticks(list(range(0,360,24)), minor=True)
            ax.grid(which='minor', axis='x', color='black',
                linewidth=0.5,  linestyle='--')
            ax.set_xticks(list(range(0,360,48)), minor=False)
            ax.grid(which='major', axis='x', color='black', linewidth=0.8)
            #ax.set_ylim(0.5, 4.5)
            ax.set_ylim(1.5, 4.5)  # Don't show 'roots' !!
            #ax.set_yticks(list(range(n.tr, n.tu)))
            ax.set_yticks(list(range(n.ts, n.tu)))
            ax.set_yticklabels(y_tick_labels)
            
            #ok = ma.masked_outside(n.n_kind, n.tr, n.tf)
                # ok values are -- (invalid) for tr <= y <= tf
            #x_vals = ma.array(self.tbx, mask=ok.mask)
            #y_vals = ma.array(n.n_kind, mask=ok.mask)
            #ax.plot(x_vals, y_vals, drawstyle='steps')
            
            xf,yf = self.get_xy(self.tbx, n.n_kind, n.tf)  # Leaf
            xb,yb = self.get_xy(self.tbx, n.n_kind, n.tb)  # Branch
            xs,ys = self.get_xy(self.tbx, n.n_kind, n.ts)  # Sub-root
            xr,yr = self.get_xy(self.tbx, n.n_kind, n.tr)  # Root
            ax.plot(xf,yf,'green', xb,yb,'brown', xs,ys,'red',  xr,yr,'blue',
                    marker='.', markersize=2)

        plot_dir = "bin-kinds-full"
        if not c.full_graphs:
            plot_dir = "bin-kinds-asn"
        if not os.path.exists(plot_dir):
            os.makedirs(plot_dir)
        pfn = "%s/bin-kinds-%4d.svg" % (plot_dir, msm_id)
        pplt.savefig(pfn)

#for msm_id in c.msm_nbrs:
for msm_id in [c.msm_id]:
    gf = PresenceInfo(msm_id)
    gf.stats()  # pc-icount plot
    gf.plot_presence()  # bin-kind run lengths plot
    
    #print("%d, %-11s ..." % (msm_id, c.msm_dests[msm_id]))
    #pcf = gf.pc_fail()

    #break  # Only do one msm_id
