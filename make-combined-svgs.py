# 1845, Mon 13 Nov 2017 (SGT)
# 1601, Wed 22 Jul 2016 (CEST)
#
# make-combined-svgs.py: read combined graph (plain .txt) file,
#            use node and edge positions to draw svgs for each bin
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import dgs_ld
import timebins
import sys, datetime, string, os.path, glob
from subprocess import call
import codecs
import copy
from timeit import default_timer as timer

import config as c
c.set_pp(False, c.msm_id)

graphs_fn = c.msm_graphs_fn(c.msm_id)
node_fn = c.node_fn
print("nodefn = %s" % node_fn)    

print("graphs_fn = %s, dgs_stem = %s" % (graphs_fn, c.dgs_stem))
dgs = dgs_ld.load_graphs(graphs_fn)  # Load a DestGraphs file
print("BinGraphs: %s %s %d  %d %s" % (
    dgs.msm_id, dgs.dest, dgs.n_traces, dgs.mx_depth, dgs.prune_s))

tb= timebins.TimeBins(dgs.start_dt, dgs.end_dt)
#print("  len(bga) = %d" % len(dgs.bga))

class Whole_Graph:
    node_f = None

    def __init__(self, node_fn):
        self.nodes = {};  self.edges = {}
        self.node_f = open(node_fn, "w")
        self.image_height = None
        # When whole graph is read from neato plain ouput
        #   by read_whole_graph(), nodes[] and edges[] are replaced
        #   by the names (i.e. pos or node pair)

    def add_to_nodes(self, pp):
        if pp in self.nodes:
            self.nodes[pp] += 1
        else:
            self.nodes[pp] = 1
            self.node_f.write("%s\n" % pp)

    def accumulate_graph(self, bg):  # Build wg from array of bgs
        # When wg is complete, read x,y from neato plain output,
        #   using read_whole_graph - that's where we set
        #   node and edge x,y names (i.e. positions)
        for pp in bg.pops:  # pp is the pop's prefix
            n = bg.pops[pp]
            self.add_to_nodes(pp)  # Only save node keys,
                # Actual node's s_nodes{} will differ from bg to bg
            for sk in n.s_nodes:
                #print("sk=%s, v=%s" % (sk, n.s_nodes[sk]))
                self.add_to_nodes(sk)
                e_name = "%s-%s" % (sk, pp)
                if e_name in self.edges:
                    self.edges[e_name] += 1
                else:
                    self.edges[e_name] = 1

    def close_whole(self):
        print("=== closing %s" % node_fn)
        self.node_f.close()

    def draw_whole_graph(self, dt_dir, dgs_info):
        dot_fn = "%s/%s-whole.dot" % (dt_dir, c.dgs_stem)
        svg_fn = "%s/%s-whole.svg" % (dt_dir, c.dgs_stem)
        plain_fn = "%s/%s-whole.txt" % (dt_dir, c.dgs_stem)
        of = open(dot_fn, "w")
        #of.write('digraph "Ts-%s-whole" { rankdir=LR;\n' % c.dgs_stem)
        of.write('digraph "Ts-%s-whole" {\n' % c.dgs_stem)
        of.write("  fontsize = 9\n")
        dgs_ld.set_graph_attribs(of)

        for nk in sorted(self.nodes):
            of.write('  "%s" [label="%s"];\n' %  (nk, nk))
        for e in sorted(self.edges):
            s_ps, d_ps = e.split("-")
            of.write('  "%s" -> "%s";\n' % (s_ps, d_ps))
                 
        of.write("  }\n")
        of.close()
        start_t = timer()
        call(["dot", "-Tplain", dot_fn, "-o", plain_fn])
            # neato makes a big mess of this (don't use it)!
        end_t = timer()
        print("draw whole graph took %.2f seconds" % (end_t-start_t))
        #exit()
        
    def read_whole_graph(self, dt_dir, dgs_info):
    # dot 'plain' format:
    #   graph scalefactor width height
    #   node name x y xsize ysize label style shape color fillcolor
    #   edge tail head n x1 y1 x2 y2 ... xn yn [ label lx ly ] style color
    #   stop
        self.nodes = {}  # Clear nodes before reading the plain (txt) file
        plain_fn = "%s/%s-whole.txt" % (dt_dir, c.dgs_stem)
        pf = open(plain_fn, "r")
        print("pf = %s" % pf)
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
                if x > self.max_x:
                    self.max_x = x
                if y > self.max_y:
                    self.max_y = y
                #print("  %s  (%f,%f)" % (name, x,y))
                self.nodes[name] = (x,y)
                    # pos string for dot
                #print("%s (%f,%f) = %s" % (name, x,y, self.nodes[name]))
            else:
                break

        self.image_height = 1200.0  # pixels
        yscale = self.image_height/self.max_y
        if c.full_graphs:
            xscale = yscale*0.9  #6
            yscale = yscale*1.4  #0.9
        else:  # For ASN plots
            xscale = yscale*0.5  # Make it (just a little) narrower
            yscale = yscale*0.8  # and a bit taller
        print("max_y = %.3f, pscale = %.3f" % (self.max_y, yscale))
        self.max_x *= xscale;  self.max_y *= yscale  # Scaled
        self.max_y += 30  #20  # Allow for size of node symbol as drawn
        
        for nk in self.nodes:  # Save positions of each node
            #print("+++ nk = %s, type(nk) = %s" % (nk, type(nk)))
            #print("    self.nodes[nk] = %.3f,%.3f" % self.nodes[nk])
            (x,y) = self.nodes[nk]
            self.nodes[nk] = 'pos="%.3f,%.3f!"' % (x*xscale, y*yscale)
            #print("-+- %s = %s" % (nk, self.nodes[nk]))

wg = Whole_Graph(node_fn)
for bn in range(c.target_bn_lo, c.target_bn_hi):
    #print("--- bn=%d" % bn)
    bg = dgs.bga[bn]
    wg.accumulate_graph(bg)

changing_nodes = {}
def add_to_changing(n):
    if n.prefix not in changing_nodes:
        changing_nodes[n.prefix] = n

last_bg = dgs.bga[c.target_bn_lo]
##print("last_bg.pops: %s" % last_bg.pops)

# Find nodes that disappeared/reappeared or changed by > 5%
for bn in range(c.target_bn_lo+1, c.target_bn_hi):
    #print("--> bn=%d" % bn)
    this_bg = dgs.bga[bn]
    ##print("this_bg.pops: %s" % this_bg.pops)
    for nk in this_bg.pops:
        t_node = this_bg.pops[nk]
        #print("t_node = %s" % t_node)
        if nk not in last_bg.pops:  # Reappeared
            #print("%s reappeared" % t_node.prefix)
            add_to_changing(t_node)
        else:  # In this and last
            l_node = last_bg.pops[nk]
            if l_node.in_count != 0 and t_node.in_count != 0:
                change_ic = abs(t_node.in_count-l_node.in_count)
                mean_ic = (t_node.in_count+l_node.in_count)/2
                pc_change = 100.00*change_ic/mean_ic
                if pc_change > 5.0:
                    #print("  %s changed" % t_node.prefix)
                    t_node.pc_change = pc_change
                    add_to_changing(t_node)
    for lk in last_bg.pops:
        l_node = last_bg.pops[lk]
        if lk not in this_bg.pops:  # Disappeared
            #print("%s gone" % l_node.prefix)
            add_to_changing(l_node)
    #print("bn %2d, changing..." % bn)
    #for ck in changing_nodes:
    #    sys.stdout.write(" %s" % changing_nodes[ck].prefix)
    #print()

wg.close_whole()

wg.draw_whole_graph(c.start_ymd, c.dgs_info)  # Make plain.txt file

wg.read_whole_graph(c.start_ymd, c.dgs_info)  # Read x,y node co-ords from plain.txt

no_asnf = no_whoisf = False
print("c.asn_fn = %s\nc.whois_fn = %s" % (c.asn_fn, c.whois_fn))

asn_fn = dgs_ld.find_usable_file(c.asn_fn())
if asn_fn != '':
    print("Will use asn-file %s" % asn_fn)
else:
    print("No asns file; run  pypy3 bulk-bgp-lookup.py <<<")
    no_asnf = True

whois_fn = dgs_ld.find_usable_file(c.whois_fn())
if whois_fn != '':
    print("Will use whois-file %s" % whois_fn)
else:
    print("No whois file; run  pypy3 get-whois-info.py <<<")
    no_whoisf = True
if no_asnf or no_whoisf:
    exit()

asn_dir = {}  # Make asn and whois directories
whoisf = open(whois_fn, 'r', encoding='utf-8')
for n,line in enumerate(whoisf):
    #print("%4d: %s" % (n, line.strip()))
    asn, colour, name, cc, rr = line.strip().split()  # All strs
    t_text = "%s: %s  (%s, %s)" % (asn, name, cc.lower(), rr)
    asn_dir[asn] = (int(colour), t_text)  # t_text is a str

node_dir = {}
asnf = open(asn_fn, "r", encoding='utf-8')
for line in asnf:
    la = line.strip().split()
    node_dir[la[0]] = la[1]

#for k in node_dir:
#    print("%s = %s" % (k, node_dir[k]))
    
#mcs_draw_dir = "%s/%s-%sdrawings" % (c.start_ymd, c.msm_id, c.asn_prefix)
mcs_draw_dir = c.draw_dir(c.msm_id)
if not os.path.exists(mcs_draw_dir):
    os.makedirs(mcs_draw_dir)
print("mcs_draw_dir = %s" % mcs_draw_dir)

tb_dgs_stem = c.dd_dgs_stem()
print("tb_dgs_stem = %s" % tb_dgs_stem)

start_t = timer()
for bn in range(c.target_bn_lo, c.target_bn_hi):
    #print("--- bn = %d" % bn)
    bg = dgs.bga[bn];  dest = dgs.dest
    
    if bn == c.target_bn_lo:  # First bin
        last_bg = None
    else:
        last_bg = dgs.bga[bn-1]

    print("--- drawing bin %d ---" % bn)
    dot_fn = "%s-%03d.dot" % (tb_dgs_stem, bn)
    svg_fn = "%s-%03d.svg" % (tb_dgs_stem, bn)
    bg.draw_graph(dot_fn, svg_fn, mcs_draw_dir, tb_dgs_stem, # in dgs_ld.py
        bn, wg, dest, node_dir, asn_dir, changing_nodes, last_bg)

    #na = ["neato", "-n2", "-Gsplines", "-Tsvg", dot_fn, "-o", svg_fn]
    #                        sets spline=true, that's too slow !!
    na = ["neato", "-n2", "-Tsvg", dot_fn, "-o", svg_fn]
    print("==== na = >%s<" % na)
    b_st = timer()
    call(na)
    b_et = timer()
    print("Bin %3d drawn, %.2f seconds" % (bn, b_et-b_st))
    os.remove(dot_fn)
    #if bn == 3:  # Only draw first 4 bins
    #    break
end_t = timer()
n_bins = c.target_bn_hi-c.target_bn_lo
print("%d bins drawn, %.2f seconds/bin" % (n_bins, (end_t-start_t)/n_bins))

    
#for bn,bg in enumerate(dgs.bga): # Avoid neato warnings (!)
#    dot_fn = "%s/%s-%02d.dot" % (c.start_ymd, tb_dgs_stem, bn)
#    svg_fn = "%s/%s-%02d.svg" % (c.start_ymd, tb_dgs_stem, bn)
#    na = ["neato", "-n2", "-Gsplines", "-Tsvg", dot_fn, "-o", svg_fn]
#    #na = ["dot", "-Tsvg", dot_fn, "-o", svg_fn]
#    #print("==== na = >%s<" % na)
#    call(na)
