# 1521, Sat 11 Jan 2020 (NZDT)
# 1845, Mon 13 Nov 2017 (SGT)
# 1601, Wed 22 Jul 2016 (CEST)
#
# make-combined-svgs.py: read combined graph (plain .txt) file,
#            use nodeand edge positions to draw svgs for each bin
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import dgs_ld, timebins

import sys, datetime, string, os.path, glob
from subprocess import call
import codecs
import copy
from timeit import default_timer as timer

import config as c

# Extra command-line parameters (after those parsed by getparamas.py):
#   +b  'bare', i.e. no ASN info available

reqd_ymds = [];  reqd_msms = []
pp_names = "m! y! a mxd= mntr= b"  # indexes 0 to 5
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default parameters for drawing
mn_trpkts = -1;  noASNs = False
asn_graphs = not c.full_graphs
#write_mntr_nodes_f = False

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
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
elif len(reqd_ymds) > 1:
    print("More than one ymd specified!");  exit()
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("reqd_msms = %s" % reqd_msms)
if mn_trpkts < 0:
    print("No mntr! Must specify smallest in_count for nodes plotted <<<")
    exit()
print("asn_graphs %s, c.full_graphs %s, mntr %d, mxd %d" % (
    asn_graphs, c.full_graphs, mn_trpkts, mx_depth))

class WholeGraph:
    node_f = None

    def __init__(self, msm_id, mntr):
        #print("WholeGraph: node_fn = %s" % node_fn)
        self.msm_id = msm_id;  self.mntr = mntr
        self.nodes = {};  self.edges = {}
        self.title = self.image_height = None
        self.nodes_too_deep = 0
        # When whole graph is read from dot plain ouput by
        #   read_whole_graph(), nodes[] and edges[] are replaced
        #     by the names (i.e. pos or node pair)

    def add_to_nodes(self, n):
        if n.prefix not in self.nodes:
            self.nodes[n.prefix] = n
            ##if n.in_count >= mn_trpkts:
            ##    self.nodes[n.prefix] = n
                #print("%s (%d) added to nodes" % (n.prefix, n.in_count))
        #else:
        #    print("--- %s already in nodes" % n.prefix)
        else:
            old_in_count = self.nodes[n.prefix].in_count
            if n.in_count > old_in_count:  # Find max in_count over all bins
                self.nodes[n.prefix].in_count = n.in_count

    def accumulate_graph(self, bn, bg):  # Build wg from bga entries
        # When wg is complete, read x,y from dot plain output,
        #   using read_whole_graph - that's where we set
        #   node and edge x,y names (i.e. positions)
        print("accumulate_graph, bn %d; %d pops" % (bn, len(bg.pops)))
        for pp in bg.pops:  # pp is the pop's prefix
            n = bg.pops[pp]
            #print("acg: n = %s (%s)" % (n, type(n)))
            ##??if dgs_ld.test_ok(n.depth,n.in_count, mx_depth,mn_trpkts):
            if True:
                self.add_to_nodes(n)  # Save the PrunedNode
                # Actual node's s_nodes{} will differ from bg to bg
                for sk in n.s_nodes:
                    sn = bg.pops.get(sk)
                    #print("   sk %s, sn %s" % (sk,sn))
                    if sn:
                        #if dgs_ld.test_ok(sn.depth,sn.in_count, 
                        #        mx_depth,mn_trpkts):
                        if True:
                            e_name = "%s-%s" % (sk, pp)
                            if e_name in self.edges:
                                self.edges[e_name] += 1
                            else:
                                self.edges[e_name] = 1
        print("bn %d, %d nodes, %d edges" % (
            bn, len(self.nodes), len(self.edges)))
        
    def write_s_node_info(self, si_fn):
        si_f = open(si_fn, "w")
        for nk in self.nodes:
            n = self.nodes[nk]
            if len(n.s_nodes) != 0:
                si_f.write(n.prefix)
                for sk in n.s_nodes:
                    si_f.write(" %s" %sk)
                si_f.write("\n")
        si_f.close()

    def draw_whole_graph(self, dt_dir, msm_id):
        dgs_stem = c.dgs_stem(msm_id)
        dot_fn = "%s/%s-whole.dot" % (dt_dir, dgs_stem)
        svg_fn = "%s/%s-whole.svg" % (dt_dir, dgs_stem)
        plain_fn = "%s/%s-whole.txt" % (dt_dir, dgs_stem)
        print("dot_fn = %s, plain_fn = %s" % (dot_fn, plain_fn))
        of = open(dot_fn, "w")
        of.write('digraph "Ts-%s-whole" {\n' % dgs_stem)
        #of.write("  size = \"11.7,8.27\";\n")  # A4 Landscape in inches
        of.write("  fontsize = 9;\n")
        dgs_ld.set_graph_attribs(of, self)

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
        call(["dot", "-Tplain", dot_fn, "-o", plain_fn])
            # neato makes a big mess of this (don't use it)!
        end_t = timer()
        print("draw whole graph (mxd %d, mntr %d) took %.2f seconds" % (
            mx_depth, mn_trpkts, end_t-start_t))
        
    def read_whole_graph(self, dt_dir):
    # dot 'plain' format:
    #   https://www.graphviz.org/doc/info/output.html#d:plain
    #   graph scalefactor width height
    #   node name x y width height label style shape color fillcolor
    #   edge tail head n x1 y1 x2 y2 ... xn yn [ label lx ly ] style color
    #   stop
        self.nodes = {}  # Clear nodes before reading the plain (txt) file
        plain_fn = "%s/%s-whole.txt" % (dt_dir, c.dgs_stem(msm_id))
        pf = open(plain_fn, "r")
        self.max_x = self.max_y = 0
        state = 0
        for line in pf:
            #print(line.strip())
            la = line.split()
            if la[0] == "graph":
                state = 1
            elif la[0] == "node":
                name = la[1].strip('"')
                #print("la = ", la)
                x = float(la[2]);  y = float(la[3])
                self.x = x;  self.y = y  # Save (x,y) for node
                if x > self.max_x:
                    self.max_x = x
                if y > self.max_y:
                    self.max_y = y
                self.nodes[name] = (x,y)
                    # overwritten by pos string for dot after scaling (below)
            else:
                break

        if asn_graphs:
            self.image_height = 1500.0  # pixels, mntr 500
            xf = 0.5;  yf = 0.8
        elif self.mntr == 5000:
            self.image_height = 600.0  # pixels, mntr 5000
            xf = 1.1;  yf = 1.4
        elif self.mntr == 500:
            self.image_height = 1500.0  # pixels, mntr 500
            xf = 1.1;  yf = 1.4
        elif self.mntr == 60:
            self.image_height = 2500.0  # pixels, mntr 60
            xf = 1.1;  yf = 1.4
        elif self.mntr == 30:
            self.image_height = 2250.0  # pixels, mntr 60
            xf = 1.1;  yf = 1.4
        else:
            self.image_height = 3000.0  # pixels, only OK for 2012
            xf = 0.8;  yf = 1.4
        print("Scale factors: xf %.2f, yf %.2f" % (xf, yf))
        yscale = self.image_height/self.max_y
        xscale = yscale*xf;  yscale *= yf
        print("max_y = %.3f, pscale = %.3f" % (self.max_y, yscale))
        self.max_x *= xscale;  self.max_y *= yscale  # Scaled
        self.tx_max = self.max_x;  self.ty_max = self.max_y  #+
        print("r_w_g: max x,y = %.3f, %.3f" % (self.tx_max, self.ty_max))  #+
        
        for nk in self.nodes:  # Save positions of each node
            #print("+++ nk = %s, type(nk) = %s" % (nk, type(nk)))
            #print("    self.nodes[nk] = %.3f,%.3f" % self.nodes[nk])
            (x,y) = self.nodes[nk]
            self.nodes[nk] = 'pos="%.3f,%.3f!"' % (x*xscale, y*yscale)
            #?print("-+- %s = %s" % (nk, self.nodes[nk]))


for msm_id in reqd_msms:
    #n_bins_to_read = 1  #  Testing, testing
    n_bins_to_read = c.n_bins*c.n_days

    graphs_fn = c.msm_graphs_fn(msm_id)
    print("graphs_fn = %s, dgs_stem = %s" % (graphs_fn, c.dgs_stem))
    dg = dgs_ld.load_graphs(graphs_fn, mx_depth, mn_trpkts, n_bins_to_read)

    #print("l-l-l-l-l-l back from load_graphs()")
    #bg = dg.bga[0]
    #for pk in bg.pops:
    #    print("%s" % bg.pops[pk])
    ##exit()
    

    #t_addr = "105.233.31.2"  # Debugging
    #dgs_ld.in_pops("back fromj load_graphs", t_addr)
    #dg = dgs_ld.load_graphs(graphs_fn, c.draw_mx_depth, 21)
    # 12)  8 s for whole graph, overall OK
    #  9)  30 s, 3 s for Firefox to render the graph
    #  6)  gave up waiting !!
    print("BinGraphs: %s %s %d" % (dg.msm_id, dg.dest, dg.n_traces))
    #  Each bingraph has it's own pops{}

    print("@1@ dg.start_dt=%s, dg.end_dt=%s" % (dg.start_dt, dg.end_dt))
    tb= timebins.TimeBins(dg.start_dt, dg.end_dt)
    #print("  len(bga) = %d" % len(dg.bga))

    wg = WholeGraph(msm_id, mn_trpkts)
    #print("@2@ c.target_bn_lo=%s, c.target_bn_hi=%s" % (
    #    c.target_bn_lo, c.target_bn_hi))
    #for bn in range(c.target_bn_lo, c.target_bn_hi):

    for bn in range(0,n_bins_to_read):
        print("--- bn=%d" % bn)
        bg = dg.bga[bn]
        wg.accumulate_graph(bn, bg)

    #gx = graphs_fn.find("graphs")
    #sni_fn = graphs_fn[0:gx+5] + "-snodes" + graphs_fn[gx+6:] 
    sni_fn = c.s_n_info_fn(msm_id)
    print("sni_fn = %s" % sni_fn)
    wg.write_s_node_info(sni_fn)

    last_bg = dg.bga[c.target_bn_lo]
    wg.draw_whole_graph(c.start_ymd, msm_id)  # Make plain.txt file
    print("---WholeGraph drawn ---")
    #input_var = input("Enter something: ")
    #print ("you entered " + input_var) 

    wg.read_whole_graph(c.start_ymd)  # Read x,y node co-ords from plain.txt
    #print("wg.nodes{} = %s" % wg.nodes)  # Now have (x,y) for each node[name]

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
    #else:  # no_ASNs True, node_dir has been read from whole-nodes file
    #print("node_dir = %s" % node_dir)
    #print("asn_dir = %s" % asn_dir)

    mcs_draw_dir = c.draw_dir(msm_id, mn_trpkts)
    if not os.path.exists(mcs_draw_dir):
        os.makedirs(mcs_draw_dir)
    print("mcs_draw_dir = %s" % mcs_draw_dir)

    tb_dgs_stem = c.dd_dgs_stem(msm_id, mn_trpkts)
    print("tb_dgs_stem = %s" % tb_dgs_stem)

    start_t = timer()
    print("bbb c.target_bn_lo=%s, c.target_bn_hi=%s" % (c.target_bn_lo, c.target_bn_hi))
    #for bn in range(c.target_bn_lo, c.target_bn_hi):
    for bn in range(0,n_bins_to_read):  # Only draw first few bins
        bg = dg.bga[bn];  dest = dg.dest

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

        #na = ["neato", "-n2", "-Gsplines", "-Tsvg", dot_fn, "-o", svg_fn]
        #                        sets spline=true, that's too slow !!ule) variables/functions so that programs
#   using this module can see 
        na = ["neato", "-n2", "-Tsvg", dot_fn, "-o", svg_fn]
          # -n2 means "use the x,y positions without change
        print("==== na = >%s<" % na)
        b_st = timer()
        call(na)
        b_et = timer()
        print("Bin %3d drawn, %.2f seconds" % (bn, b_et-b_st))
        #?? os.remove(dot_fn)
        #if bn == 3:  # Only draw first 4 bins
        #    break
    end_t = timer()
    n_bins = c.target_bn_hi-c.target_bn_lo
    print("%d bins drawn, %.2f seconds/bin" % (n_bins, (end_t-start_t)/n_bins))

    asn_s = ""
    if asn_graphs:
        asn_s = " a"
    cmd = "python make-js-slides.py + m %s ! y %s ! %s mntr %d mxd %d sd %s" % (
        msm_id, c.start_ymd, asn_s, mn_trpkts, mx_depth, "full")
    print("About to run cmd: %s" % cmd)
    output, returncode = c.run_bash_commands(cmd)
    print(">>>>>>>>>>>>>>> output")
    print(output)
    print("<<<<<<<<<<<<<  returncode = %s" % returncode)

    
#for bn,bg in enumerate(dgs.bga): # Avoid neato warnings (!)
#    dot_fn = "%s/%s-%02d.dot" % (c.start_ymd, tb_dgs_stem, bn)
#    svg_fn = "%s/%s-%02d.svg" % (c.start_ymd, tb_dgs_stem, bn)
#    na = ["neato", "-n2", "-Gsplines", "-Tsvg", dot_fn, "-o", svg_fn]
#    #na = ["dot", "-Tsvg", dot_fn, "-o", svg_fn]
#    #print("==== na = >%s<" % na)
#    call(na)
