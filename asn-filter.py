# 1924, Mon 13 Nov 2017 (SGT)
# 1912, Sat 25 Mar 2017 (CDT)
#
# asn-filter.py:  Get info about ASNs from graphs file
#                   i.e. makes asngraphs files
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import dgs_ld
import timebins
###import ipp
import sys, datetime, string, os.path
import codecs

import config as c
c.set_pp(False, c.msm_id)  # Work on graphs-* file

# Read in graphs file (dgs)

dgs_stem = c.dgs_stem
    # full_graphs adds "-asn" to dgs_stem !
print("dgs_stem = >%s<" % dgs_stem)

in_graphs_fn = c.msm_graphs_fn(c.msm_id)
print("graph_fn = %s" % in_graphs_fn)
dgs = dgs_ld.load_graphs(in_graphs_fn)  # Load a DestGraphs file
    # dgs.ba is an array of BinGraphs
    # each BinGraph has a .pops dictionary, keys are IPprefixes

print("BinGraphs: %s %s %d  %d %s" % (
    dgs.msm_id, dgs.dest, dgs.n_traces, dgs.mx_depth, dgs.prune_s))

tb= timebins.TimeBins(dgs.start_dt, dgs.end_dt)
#print("$$$ len(bga) = %d" % len(dgs.bga))

no_asnf = no_whoisf = False
asn_fn = c.asn_fn(c.msm_id)
print("asn file >%s<" % asn_fn)
if not os.path.isfile(asn_fn):
    print("No asns file; run  pypy3 bulk-bgp-lookup.py <<<")
    no_asnf = True
#if not os.path.isfile(c.whois_fn(c.msm_id)):
#    print("No whois file; run  pypy get-whois-info.py <<<")
#    no_whoisf = True
if no_asnf:  ### or no_whoisf:
    exit()

# Make asn directories
node_dir = {}  # Dictionary  IPprefix -> ASN
asnf = open(asn_fn, "r", encoding='utf-8')
for line in asnf:
    la = line.strip().split()
    node_dir[la[0]] = la[1]
    #print("node_dir key %s, val %s" % (la[0], node_dir[la[0]]))

class E_ASN:  # ASN where edges end
    types = ['normal', 'sub-root', 'root']

    def __init__(self, asnbr):
        self.e_asn = asnbr
        self.s_asns = {}  # Key: s_ASN, value: incoming tr pkts
        self.type = -1    # 1 for root, 0 for sub-roots, else -1
        self.fails = 0    # Nbr of tr pkts that only reached a sub-root

        self.prefix = asnbr  # So dgs_ld can dump an E_ASN

    def sources(self):
        return len(self.s_asns)

    def update(self, s_asn, count, type):
        ##print("s_asn = %s, count = %d" % (s_asn, count))
        if type > self.type:
            self.type = type
        if type == 0:  # Sub-root
            self.fails += count
        if s_asn != self.e_asn:
            if s_asn in self.s_asns:
                self.s_asns[s_asn] += count
                ##print("   asn %s added, count = %d" % (s_asn, self.s_asns[s_asn]))
            else:  # New s_asn
                self.s_asns[s_asn] = count
                ##print("   NEW asn %s, count = %d" % (s_asn, self.s_asns[s_asn]))
        ##print("--> s_ans = %s" % self.s_asns)

    def __str__(self):
        failed = ''
        if self.fails > 0:
            failed = ", %d failed" % self.fails
        return "E_ASN: %s <= %s (%s%s)" % (
            self.e_asn, self.s_asns, self.types[self.type+1], failed)

    def dump(self, df):  # From dgs_ld.PrunedNode
        in_count = 0
        for nk in self.s_asns:
            in_count += self.s_asns[nk]
        df.write("Node %s %d %d %d\n" % (
            self.prefix, -1, in_count, self.fails))
        for nk in sorted(self.s_asns):
            df.write("  %s %d" % (nk, self.s_asns[nk]))
        df.write("\n")
                 

class ASN_Graph(dgs_ld.BinGraph):
    no_asn_nodes = {}  # Not in ASNs list
    
    def add_to_asns(self, n_prefix, subtree):  # Build BinGraph's ASN keys list
        if subtree == -1:  # Dest treated like an ASN
            self.e_asns[n_prefix] = E_ASN(n_prefix)
        if not n_prefix in node_dir:  # Doesn't map to ASN
            #print("%s (%s) no ASN" % (n_prefix, type(n_prefix)))
            if not n_prefix in self.no_asn_nodes:
                self.no_asn_nodes[n_prefix] = True
                self.e_asns[n_prefix] = E_ASN(n_prefix)
                # Treat it's prefix as an ASN (5015 has one, 198.97.190.53)
                print("Node %s has no ASN <<<" % n_prefix)
        else:  # Maps to ASN
            n_asn = node_dir[n_prefix]
            if n_asn not in self.e_asns:
                self.e_asns[n_asn] = E_ASN(n_asn)
            
    def __init__(self, bg,  dest, node_dir, bin_nbr):
        self.n_traces = bg.n_traces  # Nbr of traces in timebin
        self.n_succ_traces = bg.n_succ_traces  # Reached dest node
        self.n_dup_traces = bg.n_dup_traces  # Traces with duplicated addresses
        self.t_addrs = bg.t_addrs  # Total pop addresses seen
        self.t_hops = bg.t_hops  # Total hops (after traces cleaned up)
        self.t_hops_deleted = bg.t_hops_deleted  # During cleanup()
        self.bin_nbr = bin_nbr  # This timebin's number
        self.mx_edges = bg.mx_edges  # Edges in to root (dest) node

        # dgs_ld.PrunedNode(prefix, subtree, in_count) has
        #  prefix  IPprefix of node
        #  subtree 0  (used by build_graphs)
        #  in_count = sum of edges in from s_nodes
        #  s_nodes = dictionary of nodes sending to this one
        
        self.e_asns = {}  # Build dictionary of end ASNs
        self.add_to_asns(dest, -1)  # Handle dest like an ASN
        dest_asn = node_dir.get(dest)
        if dest_asn:
            print("dest_asn = %s" % dest_asn)
        else:  # Dest not in node_dir, no trs reached dest
            print("dest not in node_dir <<<")
        n_nodes_in_asns = 0
        for pk in bg.pops:  # pk is the pop's prefix
            n = bg.pops[pk]
            self.add_to_asns(str(pk), n.subtree)  # Node itself
            for sk in n.s_nodes:  # Node's s_nodes
                self.add_to_asns(str(sk), 0)
        print("len(no_asn_nodes) = %d" % len(self.no_asn_nodes))
        print("len(bg.pops) = %d" % len(bg.pops))
        no_nodes_fn = c.no_asn_nodes_fn(c.msm_id)
        anf = open(no_nodes_fn, "w")
        for n in sorted(self.no_asn_nodes):
            anf.write("%s\n" % n)
        anf.close()

        for rx,rk in enumerate(bg.roots):
            print("Root %2d, %15s, ASN %s" % (rx, rk, node_dir[rk]))
        print()

        sub_roots = []
        for pk in bg.pops:  # Now build the ASN s_nodes and their counts
            n = bg.pops[pk]  # PN from pops
            type = -1  # Not a root
            e_asn =  node_dir[n.prefix]
            if n.prefix in bg.roots:  # Was it a full_graphs sub-root?
                type = 0  # Sub-root
                if n.prefix == dest:
                    type = 1  # Root
                    e_asn = dest
                elif not e_asn in sub_roots:
                    sub_roots.append(e_asn)
            
            for sk in n.s_nodes:  # Update d_node s_nodes with in_counts
                s_asn = node_dir[sk]
                s_count = n.s_nodes[sk]
                fails = 0
                if e_asn != s_asn or type >= 0:  # tr pkts from another ASN
                    self.e_asns[e_asn].update(s_asn, s_count, type)

        #for ask in self.e_asns:
        #    print("as_node: %s" % self.e_asns[ask])

        #  Add other info to complete the BinGraph
        self.roots = [dest]  # Dest address str from DestGraphs header
        for j,root in enumerate(sub_roots):  # Check the ASN sub-roots
            root_s = str(root)
            rn = self.e_asns.get(root_s)
            ordinary = False
            if rn:
                for nk in self.e_asns:  # Do any s_nodes point to rn?
                    n = self.e_asns[nk]
                    if root_s in n.s_asns:  # Yes, it's not a sub-root
                        ordinary = True
            if ordinary:
                continue  # It's a branch or leaf
            if not root_s in self.roots:
                self.roots.append(root_s)
        print("%3d: %s\n     %s\n" % (self.bin_nbr, sub_roots, self.roots))
        
        self.tree = []
        for ask in self.e_asns:
            e_asn = self.e_asns[ask]
            if ask == dest_asn or ask == dest:
                if e_asn.sources() == 0:
                    continue   # Discard dest asn with no source trs
            self.tree.append(e_asn)
        self.as_nodes = None    

        return None  # i.e. return an ASN_Graph

bga = []
for bn,bg in enumerate(dgs.bga):
    print("--- bn=%d" % bn)
    asn_bg = ASN_Graph(bg, dgs.dest, node_dir, bn)
    bga.append(asn_bg)
    #if bn == 3:
    #    break  # Only do first few bins

# Write asngraphs file    
out_dgs_fn = c.msm_asn_graphs_fn(c.msm_id)
print("out_dgs_filename = %s" % out_dgs_fn)
asnf = open(out_dgs_fn, "w")
dg = dgs_ld.DestGraphs(2, dgs.msm_id, dgs.dest, dgs.n_traces, \
        dgs.start_dt, dgs.end_dt, bga)
dg.dump(asnf)
asnf.close()
