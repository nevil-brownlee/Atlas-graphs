# 1840, Mon 13 Nov 2017 (SGT)
# 1607, Fri 11 Mar 2016 (NZDT)
#
# dgs_ld.py: DestGraphs, PrunedNode and BinGraph classes, together
#                with load_graphs() to load a dumped DestGraphs file
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import graph
import ipp, natkit
from subprocess import call
import string, sys, glob  #, math

import config as c

#               0        1      2         3         4
colours = ['black', 'brown', 'red'
, 'orange', 'yellow',
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
               'dimgray']
asn_no_info_x = len(asn_colours)-1

class NodeChange:
    def __init__(self, kind, s_n, prefix, in_count_pc, root,
                 node_count, max_tr_pkts):
        self.kind = kind  # Back, Change, Gone
        self.s_n = s_n  # Change came from a s_nodes dict
        self.prefix = prefix
        self.pc = in_count_pc
        self.root = root
        self.node_count = node_count
        self.max_tr_pkts = max_tr_pkts

    def prefix(self):
        return natkit.ba_get_long(self.prefix.addr, 0)  # IPv4 as 32-bit unsigned
    def count(self):
        return self.node_count
    
    def tr_pkts(self):
        return self.max_tr_pkts
    
    def __str__(self):
        s_n = '  n,'
        if self.s_n:
            s_n = "s_n,"
        s_root = ''
        if self.root:
            s_root = ", root"
        return "%s, %s %-15s, %7.2f%s, %3d, %d" % (
            self.kind, s_n, self.prefix, self.pc, s_root,
            self.node_count, self.max_tr_pkts)


class PrunedNode:
    fill_colours = [0,                       # 0 none
        "whitesmoke", "ghostwhite",          # 1, 2 
        "powderblue", "lightpink", "wheat",  # 3, 4, 5
        ]
    notthere_v = 2; aggregated_v = 1
    gone_v = 3;  new_v = 4;  change_v = 5

    def __init__(self, prefix, subtree, in_count, fails):
        self.prefix = prefix  # Use strings for dictionary keys
        self.subtree = subtree  # Which subtree the node is part of
        self.in_count = in_count  # Total edges (after pruning)
        self.fails = fails  # tr pkts that reached _this_ root node
        self.s_nodes = {}
        self.type = None  # For asn-filter.py
        self.shape = None  # Set for 'root' nodes
        #self.fill = 0  # Fill colour when drawing nodes
        self.pos = ''
        self.drawn = False  # Used as 'counted' in chages.count_subtree()
        self.pc_change = 0

    def dump(self, df):
        in_count = 0
        for nk in self.s_nodes:
            in_count += self.s_nodes[nk]
        df.write("Node %s %d %d\n" % (
            self.prefix, self.subtree, in_count))
        for nk in sorted(self.s_nodes):
            df.write("  %s %d" % (nk, self.s_nodes[nk]))
        df.write("\n")
                 
    def __str__(self):
        sources = []
        for sk in self.s_nodes:
            sources.append("%s:%d " % (
                sk, self.s_nodes[sk]))
        name = self.prefix
        #ASNif self.asn:
        #ASN    name = self.asn
        return("PN: %s, %d. %d, %s" % (
            name, self.subtree, self.in_count, sources))

    def prefix_s(self, prefix):
        if isinstance(prefix, str):  #ASN !!
            return prefix
        if not prefix.length:
            return str(prefix)
        elif prefix.length == 24:
            return str(prefix)[0:-5]
        return str(prefix)
        #return "%s/%d" % (str(s_pref)[0:-5], s_pref.length)

    unchanging_colour = 'grey'  # 'darkgrey'  # 'lightgrey'
    bin0_colour = 'lightblue'  #'yellowgreen'
    # H: blue = 2/3, red = 0
    # S: 0 = white, 1 = colour specified by H
    # V; 0 = black, 1 = fully saturated
    # http://infohost.nmt.edu/tcc/help/pubs/colortheory/web/hsv.html

    # HSV Hue colours for graphviz:
    red = 1.0;  blue = 0.667  #  pink = 0.833
    orange = 0.067;  green = 0.333
    
    # We want change:  -1 -> blue, 0 -> lightgrey, 1 = red
    #   for           -max%                         +max%

    mn_pc = 5;  mx_pc = 40.0
    pc_range = mx_pc-mn_pc
    #b = 10;  logmax = math.log(mx_pc+1, b)
    mn_x = 0.2;  mx_x = 1.0
    x_range = mx_x-mn_x

    def hsv_s(self, pc, incr_clr, decr_clr):  # < 5% and > 100% colours
                                              # pc < 0 means a decrease
        if abs(pc) < 5:
            return self.unchanging_colour
        #x = (b ** (logmax*(abs(pc)-mn_pc)/pc_range) - 1)/mx_pc  # (0,1] log
        #x = (abs(pc)-self.mn_pc)*self.x_range/self.pc_range + \
        #    self.mn_x  # (0,1] linear
        #if abs(pc) < self.mn_pc:  # Near 0 %
        #    x = 0.0
        #elif pc < -self.mn_pc:
        #    x = -x
        #c = (x-self.mn_x)*(decr_clr-incr_clr)/self.x_range + incr_clr
        #return "%5.3f 1.0 1.0" % c  # H S V
        if pc < 0:
            h = decr_clr
        else:
            h = incr_clr
        apc = abs(pc)
        if apc > self.mx_pc:
            apc = self.mx_pc
        s = (apc-self.mn_pc)*self.x_range/self.pc_range + self.mn_x
        return "%4.2f %4.2f 1.0" % (h, s)

    def ipc_colour(self, this_ic, last_ic):
        if not last_ic:  # last_ic may be 0!
            last_ic = 0
        av_ic = (this_ic+last_ic)/2.0
        if av_ic == 0:
            pc = 0
        else:
            pc = 100.0*(this_ic-last_ic)/av_ic
        #print("hsv(%d) -> %s" % (pc, self.hsv_s(pc, self.blue, self.red)))
        return self.hsv_s(pc, self.blue, self.red)
        
    def edge_colour(self, s_ps, changing, last_bg):  # Edge s->d
        if not last_bg:
            return self.bin0_colour
        if not self.prefix in changing:  # Always ~ the same
            colour = self.unchanging_colour
        else:
            this_ic = self.s_nodes[s_ps]  # Incoming trs from s_ps
            last_ic = 0
            if self.prefix in last_bg.pops:
                last_dn = last_bg.pops[self.prefix]
                if s_ps in last_dn.s_nodes:
                    last_ic = last_dn.s_nodes[s_ps]
                if last_ic == 0:
                    last_ic == -1
            if last_ic == 0:
                colour = 'lightseagreen'
            elif this_ic == 0:
                colour = self.unchanging_colour
            else:
                colour = self.ipc_colour(this_ic, last_ic)
        return colour


    def node_colour(self, changing, last_bg):
        if not last_bg:
            return self.bin0_colour
        if not self.prefix in changing:  # Always ~ the same
            colour = self.unchanging_colour
        else:
            this_ic = self.in_count  # Total incoming trs
            last_ic = -1
            if self.prefix in last_bg.pops:
                last_ic = last_bg.pops[self.prefix].in_count
                if last_ic == 0:
                    last_ic == -1
            if last_ic < 0:
                colour = 'lightseagreen'
            elif this_ic == 0:
                colour = self.unchanging_colour
            else:
                colour = self.ipc_colour(this_ic, last_ic)
        return colour

    def draw_node(self, of, pops, wg, node_dir, asn_dir, version,
            changing, last_bg):
        d_ps = self.prefix_s(self.prefix)  # Node name

        if self.in_count == 0:
            label = ''  # Default, use node name
        else:
            fails_s= ''
            if self.fails != 0:
                fails_s = " <%d>" % self.fails
            label = ", label=\"%s\\n%d%s\"" % (d_ps, self.in_count, fails_s)

        if self.shape:  # Root or sub-root
            shape = ", shape=%s" % self.shape
        else:
            shape = ''
        #if self.fill != 0:
        #    fill = ', style=filled, fillcolor="%s"' % \
        #        self.fill_colours[self.fill]
        #else:
        #    fill = ''
        pos = wg.nodes[self.prefix]

        if self.prefix in node_dir:  # Actual node
            asn = node_dir[self.prefix]
        else:
            asn = self.prefix

        if asn in asn_dir:
            cx_tuple = asn_dir[asn]
            cx = int(cx_tuple[0])
            t_text = cx_tuple[1]  # for tooltip
        else:  # Node graph
            cx = asn_no_info_x
            t_text = "%s  no whois info" % asn
            print("No whois info for %s (asn %s) <<<" % (self.prefix, asn))

        if c.full_graphs:
            colour = "%s" % asn_colours[cx]  # Colour shows which ASN it is
        else:  # ASN graph
            colour = self.node_colour(changing, last_bg)
        n_colour = ", color=\"%s\"" % colour

        t_str = ", tooltip=\"%s\"" % t_text
        #print("   t_str = >%s<" % t_str)
        #np_width = 1.7;  nf_size = 15;  # For ASN??  plots
        np_width = 2.0;  nf_size = 16;  # For ASN??  plots
        if not self.drawn:
            #of.write('  "%s" [%s%s%s%s%s%s];\n' % (  # Draw node
            #    d_ps, "fontsize=8, ",
            #    pos, shape, fill, n_colour, t_str))
            of.write('  "%s" [%s%s, %s%s%s%s, penwidth=%.1f, fontsize=%d];\n' % (  # Draw node
                d_ps, "fontsize=8", label, pos, shape, n_colour, t_str, np_width, nf_size))
            self.drawn = True

    def e_width(self, count):
        if count < 1000:
            return 1.5  #1.0
        elif count < 4000:
            return 1.7  #1.4
        elif count < 10000:
            return 2.0  #1.7
        return 2.0
            
    def draw_edges(self, of, changing, last_bg):  # Draw edges from s_nodes to self
        d_ps = self.prefix_s(self.prefix)  # Node name
        np_width = 16
        for nk in self.s_nodes:  # Draw with arrows in trace direction
                                 # The diagrams are less confusing that way!
            s_ps = self.prefix_s(nk)
            fcolour = colour = self.edge_colour(s_ps, changing, last_bg)
            if not self.drawn:
                print("draw_edges(%s <- %s) source node not drawn" % (
                    d_ps, s_ps))
            #if self.s_nodes[nk] >= 20:  # Don't draw seldom-used edges
            #    of.write('  "%s" -> "%s" [label=%d, fontcolor="blue", color="%s"];\n' % (
            #        s_ps, d_ps, self.s_nodes[nk], colour))
            of.write('  "%s" -> "%s" [label=%d, fontcolor="%s", color="%s", penwidth=%.1f, fontsize=%d];\n' % (
                s_ps, d_ps, self.s_nodes[nk], fcolour, colour, self.e_width(self.s_nodes[nk]), np_width))

    def compare(self, o_sn, this_bg, last_bg, sig_edges):
        # Compare new_n (self) with o_sn (old_node)
        #    o_roots,n_roots let compare() say node was not the destination
        o_roots = last_bg.roots;  n_roots = this_bg.roots
        change = [];  gone = [];  back = []
        np_width = 2.0;  nf_size = 16;  # For ASN??  plots
        for nk in o_sn.s_nodes:
            if nk in self.s_nodes:  # There in both
                new_count = self.s_nodes[nk];  old_count = o_sn.s_nodes[nk]
                if new_count > old_count:
                    diff = new_count-old_count
                    pc = (new_count-old_count)*100.0/old_count
                else:
                    diff = old_count-new_count
                    pc = (old_count-new_count)*100.0/old_count
                
                #e_change = self.s_nodes[nk] - o_sn.s_nodes[nk]
                #    # Increase of incoming edges from this node
                #if e_change >= sig_edges:
                if diff >= sig_edges:
                    n = this_bg.pops[nk]
                    change.append(NodeChange("C", True, nk, pc,
                        nk in n_roots, n.node_count, n.in_count))
            else:  # Gone
                if o_sn.s_nodes[nk] > sig_edges:
                    old_n = last_bg.pops[nk]
                    gone.append(NodeChange("G", True, nk, -100.00,
                        nk in o_roots, old_n.node_count, old_n.in_count))
        for sk in self.s_nodes:
            if not (sk in o_sn.s_nodes):  # Not in old node
                ###bg.new_nodes.append(sk)  # Make sure it's in 
                if self.s_nodes[sk]  >= sig_edges:
                    # Incoming edges from this node
                    o_snd = ''
                    if sk in n_roots:
                        o_snd = ',o-nd'
                    this_n = this_bg.pops[sk]
                    try:
                        x =  this_n.node_count
                    except:
                        print("!! No node_count, sk = %s" % sk)
                        print("!! this_n = %s" % this_n)
                        exit()

                    back.append(NodeChange("B", True, sk, +100.00,
                        sk in n_roots, this_n.node_count, this_n.in_count))
        return back + change + gone
        
def set_graph_attribs(of):
    of.write("  graph [splines=false, overlap=false];\n")
                 # edges may overlap, nodes may not overlap
                 # node position set from whole-graph,
                 # neato uses pos=x,y! to indicate 'pinned' node position
                 
class BinGraph:
    def __init__(self, n_traces, n_succ_traces, n_dup_traces, \
            t_addrs, t_hops, t_hops_deleted, mx_edges, roots, tree, version):
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
        self.pops = {}  # load_bingraph() loads tree as pops
        #?self.gone_nodes = []
        #?self.new_nodes = []
        #?self.change_nodes = []

    def draw_graph(self, dot_fn, svg_fn,  draw_dir, dgs_stem, \
            bin_nbr, wg, dest, node_dir, asn_dir, changing_nodes, last_bg):
        # wg is the WholeGraph with all the node positions
                
        #dot_fn = "%s-%02d.dot" % (dgs_stem, bin_nbr)
        #svg_fn = "%s-%02d.svg" % (dgs_stem, bin_nbr)
        of = open(dot_fn, "w", encoding='utf-8')
        of.write("digraph \"Ts-%s-%02d\" { rankdir=LR;\n" % (dgs_stem, bin_nbr))
        of.write("  fontsize = 8\n")
        set_graph_attribs(of)

        of.write('  size="%.3f,%.3f";\n' % (wg.max_x, wg.max_y))
        of.write("  \".\" [pos=\"1,%f!\", shape=\"point\", height=0.1];\n" % wg.max_y)
        #of.write("  \"..\" [pos=\"1,0!\", shape=\"point\", width=0.1];\n")  # Bottom left
            # bottom of displayed graph set by browser window size!
        
        root_shape = "box"
        if self.version == 1:
            sub_root_shape = "hexagon"
        else:
            sub_root_shape = "octagon"

        if str(self.roots[0]) != dest:  # Never reached dest
            root_shape = sub_root_shape

        for j,root in enumerate(self.roots):  # Draw root nodes
            root_s = str(root)
            rn = self.pops.get(root_s)
            if rn:
                rn.shape = root_shape
                rn.draw_node(of, self.pops, wg, node_dir, asn_dir, 
                    self.version, changing_nodes, last_bg)
            root_shape = sub_root_shape

        for pk in self.pops:  # Draw all nodes except the roots
        #    if pk not in drawn_roots:
            self.pops[pk].draw_node(of, self.pops, wg,  node_dir, asn_dir,
                self.version, changing_nodes, last_bg)
                
        for nk in sorted(self.pops):  # Draw edges for all pops
            n = self.pops[nk]
            if n.drawn:
                n.draw_edges(of, changing_nodes, last_bg)

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
            n.dump(df)

class DestGraphs:
    def __init__(self, version, msm_id, dest, n_traces,
            start_dt, end_dt, bga):
        self.version = version
        self.msm_id = msm_id;  self.dest = dest  # Traces info
        self.n_traces = n_traces
        self.start_dt = start_dt;  self.end_dt = end_dt
        dname, self.mx_depth, self.prune_p, self.p_pkts, \
            self.prune_s = c.msm_pp(msm_id)  # Graph pruning info
        self.bga = bga  # List of BinGraphs, one for each timebin

    def dump(self, df):
        version_s = ''  # Version 1
        if self.version == 2:
            version_s = '2'
        df.write("DestGraphs %d %s %d  %s %s  %d %s  %s\n" % (
            self.msm_id, self.dest, self.n_traces,
            self.start_dt, self.end_dt,
            self.mx_depth, self.prune_s, version_s))
        for bn,bg in enumerate(self.bga):
            bg.dump(df, bn)
        df.close()

def load_bingraph(df, line, version):
    la = line.split()
    if la[0] != "BinGraph":
        print(">>> Expected 'BinGraph'")
        print("    %s" % line)
    n_traces = int(la[1]);  n_succ_traces = int(la[2])
    n_dup_traces = int(la[3]);  t_addrs = int(la[4])
    t_hops = int(la[5]);  t_hops_deleted = int(la[6])
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
#ASN        roots.append(ipp.from_s(la[j]))
    tree = None;  pops = {};  eof = False
    while True:
        line = df.readline()
        if not line:  # EOF
            eof = True
            break
        else:
            la = line.split()
            if la[0] != "Node":
                break
            subnet = int(la[2])
            # la[3] = total in_count
            fails = 0
            if len(la) > 4:
                fails = int(la[4])
            pn = PrunedNode(la[1], subnet, int(la[3]), fails)
                # addr, subnet, in_count for pn
            pn.node_count = 1  # changes.count_subtree() may update
            node_line = df.readline()
            if not node_line:  # EOF
                eof = True
                break
            if len(node_line) != 0:
                la = node_line.split()  # List of addr+in_count pairs
                for j in range(0, len(la), 2):  # Build s_nodes for pn
                    prefix_str = la[j];  sn_count =  int(la[j+1])
                    #ASNprefix = ipp.from_s(prefix_str)
                    prefix = prefix_str
                    pn.s_nodes[prefix] = sn_count
                    if not prefix in pops:  # Add it to pops
                        sn = PrunedNode(
                            prefix_str, subnet, sn_count, fails)
                        sn.node_count = 1  # changes.count_subtree() may update
                        pops[prefix] = sn
                pops[pn.prefix] = pn
                
    bg = BinGraph(n_traces, n_succ_traces, n_dup_traces, \
            t_addrs, t_hops, t_hops_deleted,  mx_edges, roots, tree,  version)
    bg.pops = pops
    return bg, eof, line

def load_graphs(fn):
    df = open(fn, "r")
    line = df.readline()
    if not line:  # EOF
        print(">>> No lines in dumped file!")
        return
    la = line.split()
    if la[0] != "DestGraphs":
        print(">>> Expected 'DestGraphs'")
        print("    %s" % line)
#ASN    msm_id = int(la[1]);  dest = ipp.from_s(la[2]);  n_traces = int(la[3])
    msm_id = int(la[1]);  dest = la[2];  n_traces = int(la[3])
    start_dt = la[4];  end_dt = la[5]
    mx_depth = int(la[6]);  prune_s = la[7]
    version = 1
    if len(la) > 8:
        version = int(la[8])
    bga = []
    line = df.readline()  # First BinGraph
    j = 0
    while True:  # Load BinGraphs
        j += 1
        bg, eof, line = load_bingraph(df, line, version)
        bga.append(bg)
        if eof:
            df.close()
            break
    return DestGraphs(version, msm_id, dest, n_traces, 
                      start_dt, end_dt, bga)


def find_usable_file(a_fn):  # For filenames that end with pruning parameters
    # These are:
    #   graphs_fn, node_fn,  (msm_graphs_fn, msm_asn_graphs_fn_
    #   stats_fn, success_fn,
    afa = a_fn.rsplit('-', 3)
    a_ppc = afa[-1][0:-4]
    afa_files = glob.glob(afa[0]+'*')
    for fn in afa_files:
        if fn == a_fn:
            return a_fn
        if fn.index(afa[0]) == 0:
            fna = fn.rsplit('-',3)
            if afa[1] >= fna[1]:
                if afa[2] >= fna[2]:
                    f_ppc = fna[-1][0:-4]
                    a_int = a_ppc.find('.') < 0
                    f_int = f_ppc.find('.') < 0
                    if a_int and f_int:
                        if int(f_ppc) <= int(a_ppc):
                            return fn
    return ''

if __name__ == "__main__":  # Running as main()
    print("argv = %s" % sys.argv)
    dgs = load_graphs(sys.argv[1])  # arg[0] is name of program
    print("BinGraphs: %s %s %d  %s %s  %d %.2f" % (
        dgs.msm_id, dgs.dest, dgs.n_traces, dgs.start_dt, dgs.end_dt,
        dgs.mx_depth, dgs.prune_pc))
 
