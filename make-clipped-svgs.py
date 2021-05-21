# 1521, Sat 11 Jan 2020 (NZDT)
# 1845, Mon 13 Nov 2017 (SGT)
# 1601, Wed 22 Jul 2016 (CEST)
#
# make-combined-svgs.py: read combined graph (plain .txt) file,
#            use nodeand edge positions to draw svgs for each bin
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import dgs_ld, timebins
import graph_info as gi

import sys, datetime, string, os.path, glob, re
from subprocess import call
import codecs
import copy
from timeit import default_timer as timer

import config as c

# Extra command-line parameters (after those parsed by getparamas.py):
#   +b  'bare', i.e. no ASN info available

pp_names = "m! y! a mxd= mntr= b cs!"  # indexes 0 to 6
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default parameters for drawing
mn_trpkts = -1;  noASNs = False
asn_graphs = not c.full_graphs
#write_mntr_nodes_f = False
reqd_ymds = [];  reqd_msms = [];  clip_spec = []

for n,ix in enumerate(pp_ix):
    if ix == 0:    # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 2:  # a sets full_graphs F to use ASN graphs
        asn_graphs = True;  c.set_full_graphs(False)
    elif ix == 3:  # mxd  specify max depth
        mx_depth = pp_values[n]
    elif ix == 4:  # mntr specify min trpkts
        mn_trpkts = pp_values[n]
    elif ix == 5:  # b  'bare', i.e. no ASNs file available
        noASNs = True
    elif ix == 6:  # cs    specify  drawing_dir/clip_spec
        clip_spec = pp_values[n]
    else:
        exit()

if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
elif len(reqd_ymds) > 1:
    print("More than one ymd specified!");  exit()
if len(reqd_msms) > 1:
    print("More than one msm_id specified!");  exit()
elif len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("reqd_msms = %s" % reqd_msms)
if mn_trpkts < 0:
    print("No mntr! Must specify smallest in_count for nodes plotted <<<")
    exit()
if len(clip_spec) != 1:
    print("Must specify a single clipspec filename (cs)")
    exit()
print("asn_graphs %s, c.full_graphs %s, mntr %d, mxd %d" % (
    asn_graphs, c.full_graphs, mn_trpkts, mx_depth))

c.set_ymd(reqd_ymds[0])
c.set_sub_dir(clip_spec[0])
csdir = c.clip_spec_dir(reqd_msms[0], mn_trpkts)
print("csdir = %s" % csdir)
csf = open("%s/%s.txt" % (csdir, clip_spec[0]))
clip_name = "full";  xf = yf = 0
nodes_to_keep = [];  bn_lo = bn_hi = -1
cmd = "missing";  pb_type = "?"
sd = descr = scalef = pbtyp = margin = bins = nodes = errcnt = 0
for line in csf:  # Parse cilp-spec file - - - - - - - - - - - - -
    print("line >%s<" % line.strip())
    line = line.split("#", 1)[0]  # Remove # and chars after #
    if len(line) <= 1:  # Ignore blank lines
        print("blank line")
        continue
    la = line.split()
    if line[0] != " ":  # Continuation line
        cmd = la[0]
    # otherwise cmd is unchanged
    if cmd == "sd":  # sub-directory (clip name)
        clip_name = la[1]
        sd += 1
    elif cmd == "about":  # description (what's this clip about?)
        descr += 1
    elif cmd == "scale":  # scale factors for drawings
        scalef += 1
        xf = float(la[1]);  yf = float(la[2])
    elif cmd == "pbtype":  # presence-bars type(s)
        pbtyp += 1
        pb_type = " ".join(la[1:])
    elif cmd == "margin":  # left margin for drawings
        margin += 1
        bsx = float(la[1]);  bsy = float(la[2])
    elif cmd == "bins":  # bins (range of bins to use)
        clip_bn_lo = int(la[1]);  clip_bn_hi = int(la[2])
            # clip_bn_lo = first_bin_kept
            # clip_bn_hi = last_bin_kept  # ???? + 1 (python-style 'stop' value)
        bins += 1
    elif cmd == "nodes":
        for addr in la:
            if addr != "nodes":
                if asn_graphs:
                    ag = re.search(r'([0123456789\|]+)', addr)  # ASN
                else:
                    ag = re.search(r'([0123456789.]+)', addr)  # IPv4 address
                if ag:
                    nodes_to_keep.append(addr)
                else:
                    print("%s <<< invalid Node address" % addr);  errcnt += 1
        nodes += 1
    elif cmd == "eof":
        break
if sd != 1 or bins != 1:
    print("May only have onde 'sd' or 'bins' line!");  errcnt += 1
if sd == 0 or descr == 0 or pbtyp == 0 or scalef == 0 or \
   bins == 0 or nodes == 0:
    #  or margin == 0  margin doesn't work since we started using label
    print("Missing statement!");  errcnt += 1
    print("sd %d, descr %d, pbtyp %d, scalef %d, bins %d, nodes %d" % (
        sd, descr, pbtyp, scalef, bins, nodes))
if errcnt != 0:
    print("%d errors in %s.txt file" % (errcnt, clip_spec[0]));  exit()

print("clip name: %s, scale factors %f, %f" % (clip_name, xf, yf))
print("clip_bins: lo %d, hi %d" % (clip_bn_lo, clip_bn_hi))
print("nodes_to_keep: %s" % nodes_to_keep)

c.set_sub_dir(clip_name)
#print("draw_dir = %s" % c.draw_dir(msm_id, mn_trpkts))

class WholeGraph:
    node_f = None

    def __init__(self, msm_id, mntr, asn_dir):
        #print("WholeGraph: node_fn = %s" % node_fn)
        self.msm_id = msm_id;  self.mntr = mntr
        self.nodes = {};  self.edges = {}
        self.image_height = None
        self.nodes_too_deep = 0
        self.bsy = bsy  # top margin (graphviz units)
        self.bsx = bsx  # left margin
        # When whole graph is read from dot plain ouput by read_whole_graph(),
        #   nodes[] and edges[] are replaced by the names 
        #   (i.e. pos or node pair)

    def add_to_nodes(self, n):
        if n.prefix not in self.nodes:
            self.nodes[n.prefix] = n
        else:
            old_in_count = self.nodes[n.prefix].in_count
            if n.in_count > old_in_count:  # Find max in_count over all bins
                self.nodes[n.prefix].in_count = n.in_count

    def accumulate_graph(self, bn, bg):  # Build wg from bga entries
        # When wg is complete, read x,y from dot plain output,
        #   using read_whole_graph - that's where we set
        #   node and edge x,y names (i.e. positions)
        print("accumulate_graph, bn %d; %d pops" % (bn, len(bg.pops)))
        nb = c.n_bins*c.n_days
        for pp in bg.pops:  # pp is the pop's prefix
            if not pp in nodes_to_keep: # +++
                continue  # Only interested in nodes_to_keep
            n = bg.pops[pp]  # n is a PrunedNode
            self.add_to_nodes(n)  # Save the PrunedNode
            # n's s_nodes{} will differ from bg to bg
            for sk in n.s_nodes:
                if not sk in nodes_to_keep: # +++
                    continue
                sn = bg.pops.get(sk)
                sna = [sk, mn_trpkts]  # Dummy s_nodes line
                if sk in nodes_to_keep:
                    self.add_to_nodes(dgs_ld.PrunedNode(
                        sk, -1, n.s_nodes[sk], 99))
                if sn:
                    e_name = "%s-%s" % (sk, pp)
                    if e_name in self.edges:
                        self.edges[e_name] += 1
                    else:
                        self.edges[e_name] = 1
        print("bn %d, %d nodes, %d edges" % (
            bn, len(self.nodes), len(self.edges)))
        #for sk in self.nodes:
        #    dn = self.nodes[sk]
        #    print("ddd %s" % dn)
        
    def draw_whole_graph(self, dt_dir, msm_id):
        dgs_stem = c.dgs_stem(msm_id)
        dot_fn = "%s/%s-whole.dot" % (dt_dir, dgs_stem)
        svg_fn = "%s/%s-whole.svg" % (dt_dir, dgs_stem)
        plain_fn = "%s/%s-whole.txt" % (dt_dir, dgs_stem)
        print("dot_fn = %s, plain_fn = %s" % (dot_fn, plain_fn))
        of = open(dot_fn, "w")
        of.write('digraph "Ts-%s-whole" {\n' % dgs_stem)
        #of.write("  size = \"11.7,8.27\";\n")  # A4 Landscape in inches
        #of.write("  fontsize = 8;\n")  # Ignored by dot and neato!

        self.title = "      %s/%sgraphs-%d-%d  %s  %s" % (
            reqd_msms[0], c.asn_prefix, msm_id, mn_trpkts,
            clip_spec[0], pb_type)
        #self.blx = 120  # x value for bottom left corner
        #of.write(  #  Title at bottom left of image
        #    " BL [shape=plaintext,label=\".  %s\"," \
        #    "fontsize=12];\n" % self.title)
        #    #"pos=\"0,%f!\",fontsize=12];\n"  % (title, wg.ty_max))

        dgs_ld.set_graph_attribs(of, wg)

        def nodes_key(nk):  # Increasing-depth order
            return self.nodes[nk].depth
        for nk in sorted(self.nodes, key=nodes_key, reverse=True):
            of.write('  "%s" [label="%s"];\n' %  (nk, nk))

        def edges_key(e):  # Increasing-depth + decreasing-in_count order
            s_ps, d_ps = e.split("-")
            return self.nodes[d_ps].depth*50000 + \
                49000-self.nodes[d_ps].in_count
        for e in sorted(self.edges, key=edges_key, reverse=True):
            s_ps, d_ps = e.split("-")
            of.write('  "%s" -> "%s";\n' % (s_ps, d_ps))
        of.write("  }\n")
        of.close()
        start_t = timer()
        call(["dot", "-Tplain", "-Goverlap=scale", dot_fn, "-o", plain_fn])
            # neato makes a big mess of this (don't use it)!
        end_t = timer()
        print("draw whole graph (mxd %d, mntr %d) took %.2f seconds" % (
            mx_depth, mn_trpkts, end_t-start_t))
        
    def translate(self, x,y):
        tx = x - self.x_min + self.bsx
        ty = y - self.y_min + self.bsy
        return tx,ty

    def read_whole_graph(self, dt_dir):
    # dot 'plain' format:
    #   https://www.graphviz.org/doc/info/output.html#d:plain
    #   graph scalefactor width height
    #   node name x y width height label style shape color fillcolor
    #   edge tail head n x1 y1 x2 y2 ... xn yn [ label lx ly ] style color
    #   stop
        self.nodes = {}  # Clear nodes before reading the plain (txt) file
        ###self.edges = {}
        plain_fn = "%s/%s-whole.txt" % (dt_dir, c.dgs_stem(msm_id))
        pf = open(plain_fn, "r")
        x_min = y_min = 50000;  x_max = y_max = 0
        state = 0
        for line in pf:
            #print(line.strip())
            la = line.split()
            if la[0] == "graph":
                g_width = float(la[2]);  g_height = float(la[3])
                print(la)
                state = 1
            elif la[0] == "node":
                name = la[1].strip('"')
                if name in nodes_to_keep:
                    #print("la = ", la)
                    x = float(la[2]);  # Find clip window boundaries
                    y = float(la[3])
                    width = float(la[4]);  height = float(la[5])
                    if x < x_min:
                        x_min = x
                    if x > x_max:
                        x_max = x
                    if y < y_min:
                        y_min = y
                    if y > y_max:
                        y_max = y
                    self.nodes[name] = (x, y)
                        # overwritten by pos string for dot after scaling (below)
                    #print("%s (%f,%f) = %s" % (name, x,y, self.nodes[name]))
            else:
                break

        print("RWG: x in [%f, %f], y in [%f, %f]" % (
            x_min, x_max, y_min, y_max))
        self.x_min = x_min;  self.y_min = y_min
        self.x_max = x_max;  self.y_max = y_max
        
        print("=== after translate, brefore scaling ===")
        for nk in self.nodes:
            n = self.nodes[nk]
            x, y = self.translate(float(n[0]), float(n[1]))
            self.nodes[nk] = (x, y) 
                # overwritten by pos string for dot after scaling (below)
            print("Node %s -> %f, %f" % (n, x,y))
        self.x_max, self.y_max = self.translate(float(x_max), float(y_max))
        self.x_min, self.y_min = self.translate(float(x_min), float(y_max))
        print("--- x_max,y_max -> %f, %f" % (x_max, y_max+self.bsy))
        print("--- x_min,y_min -> %f, %f" % (x_min, y_min+self.bsy))

        # Drawing size for svg clips
        self.image_height = 1500.0  # pixels

        print("Scale factors: xf %.2f, yf %.2f" % (xf, yf))
        yscale = self.image_height/self.y_max
        xscale = yscale*xf;  yscale *= yf
        print("self.y_max = %.3f, yscale = %.3f" % (self.y_max, yscale))
        
        xscale /= 4.0;  yscale /= 5.0  ##################

        self.x_min *= xscale;  self.y_min *= yscale  # Scaled
        self.tx_min = self.x_min
        self.ty_min = self.y_min + self.bsy*yscale
        self.x_max *= xscale;  self.y_max *= yscale  # Scaled
        self.tx_max = self.x_max
        self.ty_max = self.y_max + self.bsy*yscale
        print("r_w_g: min x,y = %.3f, %.3f" % (self.tx_min, self.ty_min))  #+
        print("r_w_g: max x,y = %.3f, %.3f" % (self.tx_max, self.ty_max))  #+

        for nk in self.nodes:  # Save positions of each node
            #print("+++ nk = %s, type(nk) = %s" % (nk, type(nk)))
            #print("    self.nodes[nk] = %.3f,%.3f" % self.nodes[nk])
            (x,y) = self.nodes[nk]
            self.nodes[nk] = 'pos="%.3f,%.3f!"' % (x*xscale, y*yscale)

        print("=== after scaling ===")
        for nk in self.nodes:
            n = self.nodes[nk]
            print("Node %s -> %s" % (nk, n))
        print("--- tx_max,ty_max -> %f, %f" % (self.tx_max, self.ty_max))

        print("tx_max %f, ty_max %f (scaled for svg)" % (
            self.tx_max, self.ty_max))

for msm_id in reqd_msms:
    #n_bins_to_read = 1  #  Testing, testing
    n_bins_to_read = c.n_bins*c.n_days

    graphs_fn = c.msm_graphs_fn(msm_id)
    print("graphs_fn = %s, dgs_stem = %s" % (graphs_fn, c.dgs_stem))
    dg = dgs_ld.load_graphs(graphs_fn, mx_depth, mn_trpkts, n_bins_to_read)

    print("BinGraphs: %s %s %d" % (dg.msm_id, dg.dest, dg.n_traces))
    #  Each bingraph has it's own pops{}

    print("@1@ dg.start_dt=%s, dg.end_dt=%s" % (dg.start_dt, dg.end_dt))
    tb= timebins.TimeBins(dg.start_dt, dg.end_dt)
    #print("  len(bga) = %d" % len(dg.bga))

    asn_dir = {}  # Make asn and whois directories
    no_asnf = no_whoisf = False
    asns_fn = dgs_ld.find_usable_file(c.asns_fn(msm_id))
    if asns_fn != '':
        print("Will use asns file %s" % asns_fn)
    else:
        print("No asns file; run  bulk-bgp-lookup.py <<<")
        no_asnf = True

    whois_fn = c.all_whois_fn()
    if os.path.exists(whois_fn):
        print("Will use whois-all-file %s" % whois_fn)
    else:
        whois_fn = dgs_ld.find_usable_file(c.whois_fn(msm_id))
        if whois_fn != '':
            print("Will use whois-file %s" % whois_fn)
        else:
            print("No whois file; run  get-whois-info.py <<<")
            no_whoisf = True
            print("? ? ? ?");  exit()
    
    if not no_whoisf:
        whoisf = open(whois_fn, 'r', encoding='utf-8')
        for n,line in enumerate(whoisf):
            #print("%4d: %s" % (n, line.strip()))
            nif, asn, colour, name, cc, rr = line.strip().split()  # All strs
            #??t_text = "%s %s: %s  (%s, %s)" % (nif, asn, name, cc.lower(), rr)
            t_text = "%s: %s  (%s, %s)" % (asn, name, cc.lower(), rr)
            asn_dir[asn] = (int(colour), t_text)  # t_text is a str

    wg = WholeGraph(msm_id, mn_trpkts, asn_dir)
    #print("@2@ c.target_bn_lo=%s, c.target_bn_hi=%s" % (
    #    c.target_bn_lo, c.target_bn_hi))
    #for bn in range(c.target_bn_lo, c.target_bn_hi):
    for bn in range(0,n_bins_to_read):
        print("--- bn=%d" % bn)
        bg = dg.bga[bn]
        wg.accumulate_graph(bn, bg)

    last_bg = dg.bga[c.target_bn_lo]
    wg.draw_whole_graph(c.start_ymd, msm_id)  # Make plain.txt file
    print("---WholeGraph drawn ---")
    #input_var = input("Enter something: ")
    #print ("you entered " + input_var) 

    wg.read_whole_graph(c.start_ymd)  # Read x,y node co-ords from plain.txt
    #print("wg.nodes{} = %s" % wg.nodes)  # Now have (x,y) for each node[name]

    class NodeInfo:
        def __init__(self, asn, asn_cx):
            self.asn = asn;  self.cx = asn_cx

        def __str__(self):
            return "NodeInfo: asn %s, cx %d" % (self.asn, self.cx)

    asnf = open(asns_fn, "r", encoding='utf-8')
    node_dir = {}
    for line in asnf:
        la = line.strip().split()
        if asn_graphs:  # node names are ASNS, not prefixes
            node_dir[la[1]] = NodeInfo(la[1], int(la[3]))  # prefix-> ASN, cx
        else:
            node_dir[la[0]] = NodeInfo(la[1], int(la[3]))  # prefix-> ASN, cx
        #print( node_dir[la[0]])

    mcs_draw_dir = c.draw_dir(msm_id, mn_trpkts)
    if not os.path.exists(mcs_draw_dir):
        os.makedirs(mcs_draw_dir)
    print("mcs_draw_dir = %s" % mcs_draw_dir)

    tb_dgs_stem = c.dd_dgs_stem(msm_id, mn_trpkts)
    print("tb_dgs_stem = %s" % tb_dgs_stem)

    start_t = timer()
    #print("bbb c.target_bn_lo=%s, c.target_bn_hi=%s" % (
    #    c.target_bn_lo, c.target_bn_hi))
    #for bn in range(c.target_bn_lo, c.target_bn_hi):
    #for bn in range(0,n_bins_to_read):  # Only draw first few bins

    def strip_unwanted_nodes(pops):
        feed_in_nodes = {}  # Nodes external to clip
        clipped_pops = {}
        for nk in pops:
            if nk in nodes_to_keep:
                #print("-1- keeping node %s (%s)" % (nk, node_dir[nk].asn))
                cp = pops[nk]
                new_s_nodes = {}
                for sk in cp.s_nodes:
                    if sk in nodes_to_keep:
                        new_s_nodes[sk] = cp.s_nodes[sk]
                    else:
                        feed_in_nodes[sk] = cp.s_nodes[sk]
                        #print("-2-  feed in %d from %s (%s)" % (
                        #    cp.s_nodes[sk], sk, node_dir[sk].asn))
                cp.s_nodes = new_s_nodes
                clipped_pops[nk] = cp
            else:
                cp = pops[nk]
                for sk in cp.s_nodes:
                    if sk in nodes_to_keep:
                        pass  # Not interested in s_nodes of unwanted nodes!
                        #print("-3-  feed out %d from %s (%s) to %s (%s) " % (
                        #    cp.s_nodes[sk], sk, node_dir[sk].asn,
                        #    nk, pops[nk]))
        return clipped_pops

    for bn in range(clip_bn_lo,clip_bn_hi+1):
        bg = dg.bga[bn];  dest = dg.dest

        bg.pops = strip_unwanted_nodes(bg.pops)
        #print("============ bin %d, bg.pops = %s" % (bn, bg.pops))

        if bn == c.target_bn_lo:  # First bin
            last_bg = None
        else:
            last_bg = dg.bga[bn-1]

        print("--- drawing bin %d ---" % bn)
        dot_fn = "%s-%03d.dot" % (tb_dgs_stem, bn)
        svg_fn = "%s-%03d.svg" % (tb_dgs_stem, bn)
        bg.draw_graph(noASNs, dot_fn, svg_fn, mcs_draw_dir,
            tb_dgs_stem, # in dgs_ld.py
            bn, wg, dest, node_dir, asn_dir, last_bg)

        na = ["neato", "-n2", "-Gsplines", "-Tsvg", dot_fn, "-o", svg_fn]
            # sets spline=true; slow, but that's OK for small clip images
            # -n2 means "use the x,y positions without change"
        print("==== na = >%s<" % na)
        b_st = timer()
        call(na)
        b_et = timer()
        print("Bin %3d drawn, %.2f seconds" % (bn, b_et-b_st))
        #?? os.remove(dot_fn)
        #if bn == 3:  # Only draw first 4 bins
        #    break
    end_t = timer()
    n_bins = clip_bn_hi-clip_bn_lo
    print("%d bins drawn, %.2f seconds/bin" % (n_bins, (end_t-start_t)/n_bins))

    asn_s = ""
    if asn_graphs:
        asn_s = " a"
    cmd = "python make-js-slides.py + m %s ! y %s ! %s mntr %d mxd %d sd %s" % (
        msm_id, c.start_ymd, asn_s, mn_trpkts, mx_depth, clip_name)
    print("About to run cmd: %s" % cmd)
    output, returncode = c.run_bash_commands(cmd)
    print("---- output")
    print(output)
    if returncode != 0:
        print("<<<< returncode = %s !!!!" % returncode)
