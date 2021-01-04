# 1522, Sat 11 Jan 2020 (NZDT)
# 1629, Mon  8 Jul 2019 (NZST)
# 1840, Mon 13 Nov 2017 (SGT)
# 1607, Fri 11 Mar 2016 (NZDT)
#
# dgs_ld.py: DestGraphs, PrunedNode and BinGraph classes, together
#                with load_graphs() to load a dumped DestGraphs file
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import colorsys

import graph
from subprocess import call
import string, sys, glob, os  #, math
import datetime

import config as c

#               0        1      2         3         4
colours = ['black', 'brown', 'red', 'orange', 'yellow',
#                5       6         7       8        9
            'green', 'blue', 'violet', 'grey', 'olive']

#                   0      1          2         3            4 
asn_colours = ['black', 'red', 'crimson', 'salmon', 'orangered',
#                        5         6       7        8
               'darkorange', 'orange', 'gold', 'khaki',
#                   9           10       11               12
               'olive', 'olivedrab', 'green', 'lightseagreen',
#                  13         14       15          16
               'teal', 'steelblue', 'blue', 'slateblue',
#                         17            18        19        20
               'mediumorchid', 'darkviolet', 'purple', 'indigo',
#                   21  
               'dimgrey']
asn_no_info_x = len(asn_colours)-2

class EdgeColour:
    unchanging_colour = 'grey'
    bin0_colour = 'lightseagreen'

    # H: blue = 2/3, red = 0
    # S: 0 = white, 1 = colour specified by H
    # V; 0 = black, 1 = fully saturated
    # http://infohost.nmt.edu/tcc/help/pubs/colortheory/web/hsv.html

    # HSV Hue colours for graphviz:
    # We want change:  -1 -> blue, 0 -> lightgrey, 1 = red
    #   for            -max%                         +max%
    h_red = 1.0;  h_blue = 0.667  #  pink = 0.833
    h_orange = 0.067;  h_green = 0.333

    mn_pc = 5;  mx_pc = 40.0  # hsv_s() translates pc in [mn_pc,mx_pc]
    pc_range = mx_pc-mn_pc    #        to satruration in [mn_s,mx_s]
    mn_s = 0.2;  mx_s = 1.0
    x_range = mx_s-mn_s

    def hsv_colour(self, pc, incr_clr, decr_clr):  # HSV colours
        #print("hsv_s params pc=%s, incr_clr=%s, decr_clr=%s" % (
        #    pc, incr_clr, decr_clr))
        if pc < 0:
            h = decr_clr
        else:
            h = incr_clr
        apc = abs(pc)
        if apc > self.mx_pc:
            apc = self.mx_pc
        s = (apc-self.mn_pc)*self.x_range/self.pc_range + self.mn_s
        #return "%4.2f %4.2f 1.0" % (h, s)
        return h, s, 1.0  # value (brightness) = 1.0

    def bcp(self, this_ic, last_ic):  # Bin Change Percentage
        if last_ic == 0 or this_ic == 0:
            return 0
        av_ic = (this_ic+last_ic)/2.0  # Compute % change from average
        if av_ic == 0:
            return 0
        pc = 100.0*(this_ic-last_ic)/av_ic
        if abs(pc) < 5:
            return 0
        return pc

    def rgb_edge_colour(self, this_ic, last_ic):  # in_counts
        pc = self.bcp(this_ic, last_ic)
        if pc == 0:
            if last_ic == 0:  # last_ic may be 0!
                return self.bin0_colour
            elif this_ic == 0:
                return self.unchanging_colour
        r = self.hsv_colour(pc, self.h_blue, self.h_red)
        h,s,v = r
        return colorsys.hsv_to_rgb(h,s,v)

class PrunedNode:
    ec = EdgeColour()
    fill_colours = [0,                       # 0 none
        "whitesmoke", "ghostwhite",          # 1, 2 
        "powderblue", "lightpink", "wheat",  # 3, 4, 5
        ]
    notthere_v = 2; aggregated_v = 1
    gone_v = 3;  new_v = 4;  change_v = 5

    def __init__(self, prefix, subtree, in_count, depth):
        self.node_seen = False
        self.depth = depth  # nbr of hops from subroot
        self.prefix = prefix  # Use strings for dictionary keys
        self.subtree = subtree  # Which subtree the node is part of
        self.in_count = in_count  # Total edges (after pruning)
        self.s_nodes = {}  # in_count of trpkts from next-most-distal nodes
        self.type = None  # For asn-filter.py
        self.shape = None  # Will be set for 'root' and 'subroot' nodes
        #self.fill = 0  # Fill colour when drawing nodes
        self.pos = ''
        self.x = self.y = None
        self.drawn = False  # Used as 'counted' in chages.count_subtree()
        self.fsize = 16  # fontsize for nodes and edges

    def dump(self, df):  # Dump a PrundeNode
        in_count = 0
        for nk in self.s_nodes:
            in_count += self.s_nodes[nk]
        df.write("Node %s %d %d %d\n" % (
            self.prefix, self.subtree, in_count, self.depth))
        for nk in sorted(self.s_nodes):
            df.write("  %s %d" % (nk, self.s_nodes[nk]))
        df.write(" %d\n" % self.depth+1)
        print("wrote s_nodes for %s, depth %d "  % (self.prefix, self.depth+1))

    def __str__(self):
        sources = []
        for sk in self.s_nodes:
            sources.append("%s:%d " % (
                sk, self.s_nodes[sk]))
        name = self.prefix
        #ASNif self.asn:
        #ASN    name = self.asn
        return("PN: %s, <%d>, %d, %d, %s" % (
            name, self.depth, self.subtree, self.in_count, sources))

    def prefix_s(self, prefix):
        if isinstance(prefix, str):  #ASN !!
            return prefix
        if not prefix.length:
            return str(prefix)
        elif prefix.length == 24:
            return str(prefix)[0:-5]
        return str(prefix)

    def node_colour(self, last_bg):
        if not last_bg:
            return self.ec.bin0_colour
        if self.shape == "box":  # Root node
            return "darkgrey"
        this_ic = self.in_count  # Total incoming trs
        last_ic = -1
        if self.prefix in last_bg.pops:
            last_ic = last_bg.pops[self.prefix].in_count
            if last_ic == 0:
                last_ic == -1
        pc = self.ec.bcp(this_ic, last_ic)
        if pc == 0:
            if last_ic == 0:  # last_ic may be 0!
                return self.bin0_colour
            elif this_ic == 0:
                return self.unchanging_colour
        r = self.ec.hsv_colour(pc, self.ec.h_blue, self.ec.h_red)
        h,s,v = r
        return "%4.2f %4.2f %4.2f" % (h, s, v)
        
    def edge_colour(self, s_ps, last_bg):  # For edge s_node -> dest
        if not last_bg:
            return self.ec.bin0_colour  # No previous bg
        this_ic = self.s_nodes[s_ps]  # Incoming trs from s_ps
        last_ic = 0
        if self.prefix in last_bg.pops:
            last_dn = last_bg.pops[self.prefix]
            if s_ps in last_dn.s_nodes:
                last_ic = last_dn.s_nodes[s_ps]
            if last_ic == 0:
                last_ic == -1
        pc = self.ec.bcp(this_ic, last_ic)
        #print("pc %s: this_ic %d, last_ic %d, %s -> %s" % (
        #    pc, this_ic, last_ic, s_ps, self.prefix))
        if pc == 0:
            if last_ic == 0:  # last_ic may be 0!
                return self.ec.bin0_colour
            #elif this_ic == 0:
            #return "orange"
            return self.ec.unchanging_colour
        r = self.ec.hsv_colour(pc, self.ec.h_blue, self.ec.h_red)
        h,s,v = r
        return "%4.2f %4.2f %4.2f" % (h, s, v)

    def draw_node(self, noASNs, of, pops, wg, node_dir, asn_dir, version,
            last_bg):
        d_ps = self.prefix_s(self.prefix)  # Node name

        label = ''  # Default, just use node name
        if self.shape:  # Show in_count for non-ellipse nodes
            label = "label=\"%s\\n%d\"" % (d_ps, self.in_count)
            #print("label: %s" % label)

        if self.shape:  # Root or sub-root
            shape = ", shape=%s" % self.shape
        else:
            shape = ''
            if len(self.s_nodes) == 0:  # No s_nodes -> distal node
                                    #   -> no info from further out <-
            #    label = ", label=\"%s\"" % d_ps
            #else:
            #    label = ", label=\"%s\\n%d\"" % (d_ps, self.in_count)
                label = "label=\"%s\"" % d_ps
            else:
                label = "label=\"%s\\n%d\"" % (d_ps, self.in_count)
                
        if self.prefix not in wg.nodes:  # ??-??
            return

        #                      pos = '"pos=%.3f,%.3f!' % (x, y)
        pos = wg.nodes[self.prefix]  # pos string for x,y! (for neato)

        if self.prefix in node_dir:  # Actual node
            #asn = node_dir[self.prefix]
            n_info = node_dir[self.prefix]
            asn = n_info.asn
        else:
            print("prefix %s not in node_dir <<<" % self.prefix)
            asn = self.prefix

        if noASNs:
            cx_tuple = (self.x, self.y)
            t_text = None  # No whois info
        elif asn in asn_dir:
            cx_tuple = asn_dir[asn]
            cx = int(cx_tuple[0])
            t_text = cx_tuple[1]  # for tooltip
        else:  # Node graph
            cx = asn_no_info_x
            t_text = "%s  no whois info" % asn
            print("No whois info for %s (asn %s) <<<" % (self.prefix, asn))

        if noASNs:
            colour = "black"
        else:  # ASN or full graph
            #colour = self.node_colour(last_bg)
            colour = asn_colours[n_info.cx]
        n_colour = ", color=\"%s\"" % colour

        t_str = ", tooltip=\"%s\"" % t_text
        #print("   t_str = >%s<" % t_str)
        np_width = 2.0  # For ASN??  plots
        if not self.drawn:
            of.write('  "%s" [%s, %s%s%s%s, penwidth=%.1f, fontsize=%d];\n' % (  # Draw node
                d_ps, label, pos, shape, n_colour, t_str, np_width, self.fsize))
            self.drawn = True

    def e_width(self, count):
        if count < 1000:
            return 1.5  #1.0
        elif count < 4000:
            return 1.7  #1.4
        elif count < 10000:
            return 2.0  #1.7
        return 2.0
            
    def draw_edges(self, of, last_bg):  # Draw edges from s_nodes to self
        d_ps = self.prefix_s(self.prefix)  # Node name
        for nk in self.s_nodes:  # Draw with arrows in trace direction
                                 # The diagrams are less confusing that way!
            s_ps = self.prefix_s(nk)
            fcolour = colour = self.edge_colour(s_ps, last_bg)
            if not self.drawn:
                print("draw_edges(%s <- %s) source node not drawn" % (
                    d_ps, s_ps))
            if self.s_nodes[nk] >= 20:  # Don't draw seldom-used edges
                of.write('  "%s" -> "%s" [label=%d, fontcolor="blue", fontsize=%s, color="%s"];\n' % (
                    s_ps, d_ps, self.s_nodes[nk], self.fsize, colour))

def set_graph_attribs(of, wg):
    #of.write("  graph [splines=false, nodesep=0.75, ranksep=1.0];\n")
    #of.write("  graph [overlap=false, splines=true, sep=0.8];\n")
    splines = "false"
    if wg.title:
        splines = "true"
    of.write("  graph [overlap=false, splines=%s, " \
             "sep=0.8, fontsize=18];\n" % splines)
             # "sep=0.8, fontsize=18, margin=\"0.0,0.0\"];\n")
        # node and edge fontsizes are set to PrunedNode.fsize
            # graphviz default fontsize is set above for the title!
        # for dot (WholeGraph) and neato (bin graphs)
            # splines=true draws curved lines, 
            #   but takes far too long for full graphs.
            # It's OK for (small) clipped graphs though, and seems
            #   to be the only way to avoid edges ovelapping nodes!
            # edges may overlap, nodes may not overlap
        # node position set from whole-graph,
        # neato uses pos=x,y! for 'pinned' node position i11n points
        #   (dot doesn't use pos!)

class BinGraph:    
    def __init__(self, n_traces, n_succ_traces, n_dup_traces, \
            t_addrs, t_hops, t_hops_deleted, mx_edges, roots, \
            tree, version, pops):
        self.n_traces = n_traces
        self.n_succ_traces = n_succ_traces  # Reached dest node
        self.n_dup_traces = n_dup_traces  # Traces with duplicated addresses
        self.t_addrs = t_addrs  # Total pop addresses seen
        self.t_hops = t_hops  # Total hops (after traces cleaned up)
        self.t_hops_deleted = t_hops_deleted  # During cleanup()
        self.mx_edges = mx_edges  # Edges in to root (dest) node
        self.roots = roots  # Root (destination) node keys
        self.tree = tree  # Node list for 'reached dest' paths
            # skel.py dumps this as an array
        self.version = version
        self.pops = pops  # Current PNs; load_bingraph() loads tree as pops
        print("About to make BinGraph:")
        #for pk in pops:
        #    print("%s" % self.pops[pk])

    def draw_graph(self, noASNs, dot_fn, svg_fn,  draw_dir, dgs_stem, \
                   bin_nbr, wg, dest, node_dir, asn_dir, last_bg):
        # wg is the WholeGraph with all the node positions
        print("draw_graphs: roots = %s" % self.roots)

        #dot_fn = "%s-%02d.dot" % (dgs_stem, bin_nbr)
        #svg_fn = "%s-%02d.svg" % (dgs_stem, bin_nbr)
        of = open(dot_fn, "w", encoding='utf-8')
        of.write("digraph \"Ts-%s-%02d\" { rankdir=LR;\n" % (dgs_stem, bin_nbr))
        set_graph_attribs(of, wg)

        #of.write('  size="%.3f,%.3f";\n' % (wg.tx_max, wg.ty_max))  # translated x,y
            # neato doesn't seem to use size= ???
        # bottom of displayed graph set by browser window size!

        of.write(  # point at top left of image
            " TL  [pos=\"0,%f!\", shape=\"point\", height=0.02];\n" % \
            wg.ty_max)  # Top left  (. at top left of image)
        of.write(  # point at bottom right of image
            " BR  [pos=\"%f,0!\", shape=\"point\", height=0.02];\n" % \
            wg.tx_max)  # Top left  (. at top left of image)

        root_shape = "box"
        if self.version == 1:
            sub_root_shape = "hexagon"
        else:
            sub_root_shape = "octagon"

        if self.roots[0] != dest: # Never reached dest
            print("roots[0] = %s <- No root (dest) node !!!!"  % self.roots[0])
            root_shape = sub_root_shape

        for root in self.roots:  # Draw root nodes
            if root in self.pops:
                rn = self.pops[root]
                rn.shape = root_shape
                rn.draw_node(noASNs, of, self.pops, wg, node_dir, asn_dir, 
                    self.version, last_bg)
            #else:
            #    print("msm dest (%s) not in pops" % root)
            root_shape = sub_root_shape

        for pk in self.pops:  # Draw all nodes except the roots
            if pk not in self.roots:
                self.pops[pk].draw_node(noASNs, of, self.pops, wg,
                    node_dir, asn_dir, self.version, last_bg)
                
        #check_pops_cs_nodes(self.pops, self.cs_nodes)

        for nk in sorted(self.pops):  # Draw edges for all pops
            n = self.pops[nk]
            if n.drawn:
                n.draw_edges(of, last_bg)

        if wg.title:
            of.write("labelloc=\"b\";\n")  # Bottom (t for top)
            of.write("label=\"%s\n\n\"" % wg.title)

        of.write("  }\n")
        of.close()

    def __str__(self):
        res = "BinGraph: \n"
        for pk in sorted(self.pops):
            res += "%s\n" % self.pops[pk]
        return res


    def node_key(self, node):
        return node.prefix

    def dump(self, df, bin_nbr):  # Dumps BinGraph from node tree
        rs = ""
        for nk in self.roots:
            rs += " %s" % nk
        df.write("BinGraph %d %d %d %d %d %d  %d\n" % (
            self.n_traces, self.n_succ_traces, self.n_dup_traces, \
            self.t_addrs, self.t_hops, self.t_hops_deleted, bin_nbr))
        df.write("  %d %s\n" % (self.mx_edges, rs))
        #for n in self.tree:
        #    print("$$$ n = %s, type(n) = %s" % (n, type(n)))
        for n in sorted(self.tree, key=self.node_key):
            #print("%s" % n)
            n.dump(df)

class DestGraphs:
    def __init__(self, version, msm_id, dest, n_traces,
            start_dt, end_dt, bga):
        self.version = version
        self.msm_id = msm_id;  self.dest = dest  # Traces info
        self.n_traces = n_traces
        self.start_dt = start_dt;  self.end_dt = end_dt
        self.graph_start_dt = self.start_dt  # Save original start_dt
        #print("DestGraphs.__init__(): start_dt=%s, end_dt=%s" % (start_dt, end_dt))
        self.bga = bga  # List of BinGraphs, one for each timebin

    def change_bin_range(self, first_bin, n_bins, new_bga):
        dt_obj = datetime.datetime.strptime(self.graph_start_dt, "%Y-%m-%dT00")
        self.start_dt = dt_obj+datetime.timedelta(seconds=first_bin*3600)
        self.bga = new_bga

    def dump(self, df):
        version_s = ''  # Version 1
        if self.version == 2:
            version_s = '2'
        df.write("DestGraphs %d %s %d  %s %s  %s\n" % (
            self.msm_id, self.dest, self.n_traces,
            self.start_dt, self.end_dt, version_s))
        for bn,bg in enumerate(self.bga):
            bg.dump(df, bn)
        df.close()

def print_pops(marker, pops):
    print("%5s, len(pops) %d" % (marker, len(pops)))
    for pn in pops:
        print("  %s" % pops[pn])
    exit()

t_addr = "81.174.0.21"  #  Testing, testing
def in_pops(msg, in_pops, bn):
    #return  # Don't print anything
    print("%s: in pops %s, bn %d\n" % (msg, in_pops, bn))

def load_bingraph(df, line, version, mx_depth, mn_trpkts, dest):
    print("load_bingraph(): Initial  load, d=%d, p=%d" % (
        mx_depth, mn_trpkts))
    la = line.split()
    if la[0] != "BinGraph":
        print(">>> Expected 'BinGraph'")
        print("    %s" % line)
    n_traces = int(la[1]);  n_succ_traces = int(la[2])
    n_dup_traces = int(la[3]);  t_addrs = int(la[4])
    t_hops = int(la[5]);  t_hops_deleted = int(la[6])
    bn = int(la[7])
    print("Start bin %d -------------------------------------" % bn)
##    version = 1  # For v1 graphs files
##    if len(la) > 8:  # la[8] is the bin number
##        version = int(la[8])
##    print("load_bingraph: version = %d" % version)
    line = df.readline()
    la = line.split()
    roots = []
    mx_edges = int(la[0])
    for j in range(1,len(la)):
        roots.append(la[j])
    subroots = {};  pops = {};  edges = {}  # Initial versions of these
#r    on_trpkts_in = {}  # trpkts in to other nodes
    tree = None;  eof = False;  ln = 0
    #  Pass 1  Read in graphs- file, i.e. build pops entries for all nodes
    while True:
        line = df.readline()
        if not line:  # EOF
            eof = True
            break
        else:
            ln += 1
            la = line.split()
            #print("+2+ Node line %s" % la)
            if la[0] != "Node":
                break
            prefix = la[1]  # Node IP address
            subnet = int(la[2])  # i.e. sub-tree
            tot_trpkts_in = int(la[3])  # total in_count
            depth = int(la[4])
            node_line = df.readline();  ln += 1
            if not node_line:  # EOF
                eof = True
                break
            pn = PrunedNode(prefix, subnet, tot_trpkts_in, depth)
                # addr, subnet, in_count for pn
            if test_ok(depth,tot_trpkts_in, mx_depth,mn_trpkts):
                # OK for depth and trpkts, save it in pops
                la = node_line.split()  # List of addr+in_count pairs + depth
                #print("+3+ s_nodes line %s" % la)
                s_n_depth = int(la.pop())
                if s_n_depth != depth+1:
                    print("%s : depth != Node depth +1" % node_line)
                ok = False
                if len(la) == 0:
                    print("empty node_line ?????");  exit()
                s_nodes = {};  tic = 0  # total in_count
                for j in range(0, len(la), 2):  # Build s_nodes for pn
                    sn_prefix = la[j];  sn_count = int(la[j+1])
                    if sn_count >= mn_trpkts:
                        tic += sn_count
                        s_nodes[sn_prefix] = sn_count
                        edge_name = "%s %s" % (sn_prefix, prefix)
                        if not edge_name in edges:
                            edges[edge_name] = sn_count
                        else:
                            edges[edge_name] += sn_count
                pn.s_nodes = s_nodes  # Don't delete this line!
                if tic >= mn_trpkts:
                    pn.in_count = tic
                    if prefix in pops:
                        print("prefix %s already in pops !!!!" % prefix)
                    else:
                        pops[prefix] = pn
            #else:  # test_ok failed
            #    print("test_ok() Node %s not enough trpkts" % prefix)

    print("Pass 1 after load_bingraph(%d, %d): %d pops, %d edges" % (
        mx_depth, mn_trpkts, len(pops), len(edges)))
    #in_pops("end Pass 1", t_addr in pops, bn)
    #if bn == 0:
    #    for pk in pops:
    #        pn = pops[pk]
    #        print("%s\n" % pn)

    # Pass 1.5: tests whether s_node counts agree with Node in_counts
    nip = {};  no_diff = small_diff = diff_gt_10 = 0
    for prefix in pops:  
        d_pn = pops[prefix]  # dst node
        for s_p in d_pn.s_nodes:  # look at sources
            if s_p not in pops and s_p not in nip:
                nip[s_p] = True
            else:
                sp_in = d_pn.s_nodes[s_p]  # trpkts in to d_pn
                diff = abs(sp_in - d_pn.in_count)
                if diff == 0:
                    no_diff += 1
                elif diff <= 10:
                    small_diff += 1
                else:
                    diff_gt_10 += 1
    #in_pops("end Pass 1.5", t_addr in pops, bn)
    print("Pass 1.5: len(pops) %d, len(nip) %d\n  same %d, small_diff %d, gt_10 %d" % (
        len(pops), len(nip), no_diff, small_diff, diff_gt_10))
    #if bn == 0:
    #    for pk in pops:
    #        pn = pops[pk]
    #        #print("%s\n" % pn)

    # Pass 2  Remove edges with in_count < mntr
    no_sources_nodes = {};  nodes_not_in_pops = {}
    for prefix in pops:  # Check source node in_counts are OK
        d_pn = pops[prefix]  # dst node
        #d_edges_ok = d_pn.in_count >= mn_trpkts  # End point OK
        #if prefix == trace_p:
        #    print(";;; %s, deok %s" % (d_pn, d_edges_ok))
            
        new_s_nodes = {}
        for s_p in d_pn.s_nodes:  # look at sources
            dp_in = d_pn.s_nodes[s_p]  # trpkts in to d_pn from s_p
            if s_p in pops:
                sn = pops[s_p]  # Keep this s_node
                sic = sn.in_count
                if sic >= mn_trpkts:  # This s_node's in_count is OK
                    #if dp_in > sic:
                    #    sic = dp_in
                    new_s_nodes[s_p] = dp_in
                #if sn_in_count < dp_in:
                #    print("dst %s: s_p %s (%d) > src %s (%d) <<<" % (
                #        prefix, s_p,dp_in,  s_p,sn.in_count))
            elif dp_in > mn_trpkts:  # s_p not in pops
                #print("%s (%d) -> %s (%d); src not in pops" % (
                #    s_p, dp_in,  prefix,d_pn.in_count))
                new_s_nodes[s_p] = dp_in  # Use instead of sn.in_count
                if s_p not in pops:
                    nodes_not_in_pops[s_p] = PrunedNode(
                        s_p, 0, dp_in, d_pn.depth+1)
                    # Save source node in pops (with no s_nodes)
        d_pn.s_nodes = new_s_nodes
        #>> d_pn.tot_count left at total before stripping too-low s_nodes
        if len(new_s_nodes) == 0:
            no_sources_nodes[prefix] = d_pn.in_count
    for sk in nodes_not_in_pops:
        pops[sk] = nodes_not_in_pops[sk]

    print("Pass 2: %d no_sources nodes" % len(no_sources_nodes))
    print("    %d pops, %d edges" % (len(pops), len(edges)))
    #in_pops("end Pass 2", t_addr in pops, bn)
    #if bn == 0:
    #    for pk in pops:
    #        pn = pops[pk]
    #        print("%s\n" % pn)

    # Pass 3  Count no_source nodes
    zero_in_nodes = [];  edges = {}  # Make new edges dictionary
    s3_nodes = {}  # Make list of s_node prefixes after pass 3
    for prefix in pops:
        pn = pops[prefix];  s_nodes = pn.s_nodes
        new_s_nodes = {};  new_in_count = 0
        for sn_prefix in s_nodes:
            sn_count = s_nodes[sn_prefix]
            if sn_count >= mn_trpkts:
                s3_nodes[sn_prefix] = True  # Will be the source of an edge
                new_in_count += sn_count
                new_s_nodes[sn_prefix] = sn_count
                edge_name = "%s %s" % (sn_prefix, prefix)
                if not edge_name in edges:
                    edges[edge_name] = sn_count
                else:
                    edges[edge_name] += sn_count
            #print("  new_s_nodes %s" % new_s_nodes)
        if len(new_s_nodes) != 0:
            pn.s_nodes = new_s_nodes;  pn.in_count = new_in_count
        else:
            zero_in_nodes.append(prefix)

    dest_pn = pops.get(dest)
    if dest_pn:
        print("dest %s, depth %d" % (dest, pops[dest].depth))
        pops[dest].depth = 0  # depth was treated above like any other node
    else:
        print("dest not in pops, i.e. traceroutes never reached dest !!!")

    print("Pass 3 count too-small s_nodes: %d pops, %d edges, %d s3_nodes" % (
        len(pops), len(edges), len(s3_nodes)))
    in_pops("end Pass 3", t_addr in pops, bn)
    #if bn == 0:
    #    for pk in pops:
    #        pn = pops[pk]
    #        print("%s\n" % pn)
    #    #print("contents of zero_in_nodes: %s" % zero_in_nodes)
    #    exit()
    
    print("graph roots found with d,p = (%d,%d)" % (mx_depth,mn_trpkts))
    for n,prefix in enumerate(roots):
        if prefix in pops:
            pn = pops[prefix]
            print("%3d %15s %3d %d" % (n, prefix, pn.depth, pn.in_count))
    ##in_pops("enumerate roots", t_addr in pops, bn)

    bg = BinGraph(n_traces, n_succ_traces, n_dup_traces, \
        t_addrs, t_hops, t_hops_deleted,  mx_edges, roots, 
        tree, version, pops)
    in_pops("returning bg", t_addr in pops, bn)
    return bg, eof, line

def present(pops, prefix, msg):
    if prefix in pops:
        result = " present, in_count=%d" % pops[prefix].in_count
    else:
        result = " missing"
    print("M %s: %s %s" % (msg, prefix, result))

def check_ok(pops, cs_nodes, mxa_depth, mna_trpkts):
    # Check s_nodes in_counts, remove any that are too small from pops
    for prefix in pops:
        pn = pops[prefix]
        new_in_count = 0;  new_s_nodes = {}
        for s_prefix in pn.s_nodes:  # Delete s_nodes with low in_counts
            sn_in_count = pn.s_nodes[s_prefix]  # trpkts in from s_prefix
            sn_count = 0
            n_spx = pops.get(s_prefix)
            if n_spx:  # In pops, check it
                sn_in_count = n_spx.in_count  # Current value for PN s_prefix
                if sn_in_count < mna_trpkts:  # in_count too small
                    #print("delete sn %s -> %d" % (s_prefix, sn_in_count))
                    pn.in_count -= sn_in_count
                    cs_nodes[s_prefix] -= sn_count
                else:  # keep
                    new_s_nodes[s_prefix] = sn_in_count
                    new_in_count += sn_in_count
            if len(new_s_nodes) != 0 or new_in_count != 0:
                pn.s_nodes = new_s_nodes
                pn.in_count = new_in_count
            else:  # No s_nodes remain, in_count == 0
                pn.s_nodes = {}  # Now has no s_nodes
                pn.in_count == 0
                #print("def deleting %s <%d> from pops" % (prefix, pn.in_count))

    csn_to_delete = []
    for prefix in cs_nodes:
        n = pops.get(prefix)
        if prefix == "105.233.31.25":
            print("csp: n = %s" % n)
        if n and (n.in_count == 0 or len(n.s_nodes) == 0):  # No trpkts in to n
            csn_to_delete.append(prefix)
    print("csn_to_delete: %s" % csn_to_delete)
    for prefix in csn_to_delete:
        cs_nodes.pop(prefix)
        pops.pop(prefix)
    return len(csn_to_delete)

def test_ok(d,p, mxa_depth, mna_trpkts):
    ok = False
    if mna_trpkts != 0:
        if mxa_depth == 0:  # Test only trpkts
            if p >= mna_trpkts:  # Test only trpkts
                ok = True
        elif p >= mna_trpkts and d <= mxa_depth:
            ok = True
    elif mxa_depth != 0:
        if d <= mxa_depth:  # Test only depth
            ok = True
    else:
        ok = True
    return ok

def add_to_pops(pops,cs_nodes, pn, d,p, mxa_depth, mna_trpkts):
    #print("start add_to, len(pops) %d" % len(pops))
    #print("%d %d, %d %d,  %s" % (d,p, mxa_depth,mna_trpkts, pn.prefix))
    ok = test_ok(d,p, mxa_depth, mna_trpkts)
    if ok:
        pops[pn.prefix] = pn
        #print(" POK  %3d  %6d  %s" % (d, p, pn.prefix))
        if pn.prefix not in cs_nodes:
            cs_nodes[pn.prefix] = pn.in_count
        else:
            cs_nodes[pn.prefix] += pn.in_count
    return ok

def load_graphs(fn, mx_depth, mn_trpkts, n_bins_to_read):
    # Load DestGraphs object from a graphs- file
    print("=== Starting load_graphs(%s) mxd %d, mntr %d" % (
        fn, mx_depth, mn_trpkts))
    df = open(fn, "r")
    line = df.readline()
    if not line:  # EOF
        print(">>> No lines in dumped file!")
        return
    la = line.split()
    if la[0] != "DestGraphs":
        print(">>> Expected 'DestGraphs'")
        print("    %s" % line)
    msm_id = int(la[1]);  dest = la[2];  n_traces = int(la[3])
    start_dt = la[4];  end_dt = la[5]
    #print("@2@ load_graphs: start_dt=%s, end_dt=%s" % (start_dt, end_dt))
    version = 1
    if len(la) > 8:
        version = int(la[8])
    bga = []
    line = df.readline()  # First BinGraph
    j = 0
    while True:  # Load BinGraphs
        j += 1
        bg, eof, line = load_bingraph(df, line, version,  # In load_graphs(fn)
            mx_depth, mn_trpkts, dest)

        bga.append(bg)
        if eof:
            df.close()
            break

        if j == n_bins_to_read:
            break

    return DestGraphs(version, msm_id, dest, n_traces, 
                      start_dt, end_dt, bga)

def find_usable_file(a_fn):  # For filenames similar to a_fn
    # These are:
    #   graphs_fn, node_fn (and
    #    msm_graphs_fn, msm_asn_graphs_fn, stats_fn
    # Used by make-combined-svgs.py for asns and whois files

    dir, fn = a_fn.split("/", 1)
    print("--- dir %s, fn %s" % (dir, fn))
    name, msm, ymd, hhmm, rest = fn.split('-')
    nbins, ftype = rest.split(".")
    g_fn = "%s/%s-%s-%s*.%s" % (dir, name, msm, ymd, ftype)
    print("fuf-1 g_fn = %s" % g_fn)
    afa_files = glob.glob(g_fn)
    r_fn = ''
    if len(afa_files) != 0:
        for fn in afa_files:
            print("--- fn = %s" % fn)
            dir, aafn = fn.split("/", 1)
            fname, fmsm, fymd, fhhmm, rest = aafn.rsplit('-')
            fnbins, ftype = rest.split(".")
            print("fuf-2 fn %s, fnbins %s, nbins %s" % (fn, fnbins, nbins))
            #if int(fnbins) >= int(nbins):  # We don't really care about nbins
            #    print("  a fnbins = %s" % fnbins)
            r_fn = "%s/%s-%s-%s-%s-%s.%s" % (dir, 
                fname, fmsm, fymd, fhhmm, fnbins, ftype)
            print("-3- r_fn = %s" % r_fn)
            return r_fn
    print(">>>> Couldn't find %s file(s) for msm_id %s" % (name, msm))
        
if __name__ == "__main__":  # Running as main()
    print("argv = %s" % sys.argv)
    #dgs = load_graphs(sys.argv[1])  # arg[0] is name of program
    #print("BinGraphs: %s %s %d  %s %s  %d %.2f" % (
    #    dgs.msm_id, dgs.dest, dgs.n_traces, dgs.start_dt, dgs.end_dt,
    #    dgs.mx_depth, dgs.prune_pc))
