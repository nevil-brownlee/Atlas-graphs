# 1924, Mon 13 Nov 2017 (SGT)
# 1912, Sat 25 Mar 2017 (CDT)
#
# asn-filter.py:  Get info about ASNs from graphs file
#                   i.e. makes asngraphs files
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import dgs_ld
import timebins
import sys, datetime, string, os.path
import codecs

import config as c

reqd_ymds = [];  reqd_msms = []
pp_names = "y! m! mxd= mntr="  # indexes 0 to 3
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default paremeters for drawing
mn_trpkts = c.draw_mn_trpkts
for n,ix in enumerate(pp_ix):
    if ix == 0:    # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 1:  # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 2:  # mxd  specify max depth
        mx_depth = pp_values[n]
    elif ix == 3:  # mntr  specify min trpkts
        mn_trpkts = pp_values[n]
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("reqd_ymds = %s, reqd_msms = %s, mxd = %d, mntr = %d\n" % (
    reqd_ymds, reqd_msms, mx_depth, mn_trpkts))
if not c.full_graphs:
    c.set_full_graphs()
if len(reqd_ymds) > 1:
    print("asn-filter.py only handles one ymd <<<")
    exit()
c.start_ymd = reqd_ymds[0]

class E_ASN:  # ASN where edges end
    types = ['normal', 'sub-root', 'root']

    def __init__(self, asnbr, depth):
        self.e_asn = asnbr
        self.s_asns = {}  # Key: s_ASN, value: incoming tr pkts
        self.type = -1    # 1 for root, 0 for sub-roots, else -1
        self.d_total = depth;  self.n_depths = 1
        self.depth = float(depth)  # Av depth while building E_ASN
        self.prefix = asnbr  # So dgs_ld can dump an E_ASN

    def update_depth(self, depth):  # Compute running average depth
        self.d_total += depth;  self.n_depths += 1
        self.depth = float(self.d_total)/self.n_depths
        
    def sources(self):
        return len(self.s_asns)

    def update(self, s_asn, count, type, src_prefix):
        # Builds the s_node dictionary with tr_pkts in to this E_ASN
        ##print("s_asn = %s, count = %d" % (s_asn, count))
        if type > self.type:
            self.type = type
        if s_asn != self.e_asn:
            if s_asn in self.s_asns:
                self.s_asns[s_asn] += count
                #print("   asn %s incremented, count %d, s_prefix %s" % (
                #    s_asn, self.s_asns[s_asn], src_prefix))
            else:  # New s_asn
                self.s_asns[s_asn] = count
                #print("   NEW asn %s, count = %d" % (s_asn, self.s_asns[s_asn]))
        ##print("--> s_ans = %s" % self.s_asns)

    def __str__(self):
        return "E_ASN: %s <= %s (%s) %d" % (self.asn,
            self.s_asns, self.types[self.type+1], self.depth)

    def dump(self, df):  # Derived from dgs_ld.PrunedNode
        in_count = 0
        for nk in self.s_asns:
            in_count += self.s_asns[nk]
        if in_count != 0:
            df.write("Node %s %d %d %d\n" % (
                    # Node so that dgs_ld can read the dumped ASN graph
                self.prefix, -1, in_count, self.depth))
            for nk in sorted(self.s_asns):
                df.write("  %s %d" % (nk, self.s_asns[nk]))
            df.write("  %d\n" % int(self.depth+1))

class ASN_Graph(dgs_ld.BinGraph):
    no_asn_nodes = {}  # Not in ASNs list
    
    def add_to_asns(self, n_prefix, subtree, depth):  # Build BinGraph's ASN keys list
        #print("ata.1: n_prefix %s, subtree %d" % (n_prefix, subtree))
        if subtree == -1:  # Dest treated like an ASN
            self.e_asns[n_prefix] = E_ASN(n_prefix, depth)
        if not n_prefix in node_dir:  # Doesn't map to ASN
                #  node_dir maps IPprefix -> ASN
            print("%s (%s) no ASN" % (n_prefix, type(n_prefix)))
            if not n_prefix in self.no_asn_nodes:
                self.no_asn_nodes[n_prefix] = True
                self.e_asns[n_prefix] = E_ASN(n_prefix, depth)
                # Treat it's prefix as an ASN (5015 has one, 198.97.190.53)
                print("Node %s has no ASN <<<" % n_prefix)
        else:  # Maps to ASN
            n_asn = node_dir[n_prefix]
            if n_asn not in self.e_asns:
                self.e_asns[n_asn] = E_ASN(n_asn, depth)
            else:
                self.e_asns[n_asn].update_depth(depth)

    def __init__(self, bg,  dest, node_dir, bin_nbr):
        self.n_traces = bg.n_traces  # Nbr of traces in timebin
        self.n_succ_traces = bg.n_succ_traces  # Reached dest node
        self.n_dup_traces = bg.n_dup_traces  # Traces with duplicated addresses
        self.t_addrs = bg.t_addrs  # Total pop addresses seen
        self.t_hops = bg.t_hops  # Total hops (after traces cleaned up)
        self.t_hops_deleted = bg.t_hops_deleted  # During cleanup()
        self.bin_nbr = bin_nbr  # This timebin's number
        self.mx_edges = bg.mx_edges  # Edges in to root (dest) node
        self.roots = []  # Root ASNs
        self.e_asns = {}  # Build dictionary of end (dst) ASNs

        dest_asn = node_dir.get(dest)  # Get ASN for dest
        if dest_asn:
            print("dest %s, dest_asn %s" % (dest, dest_asn))
            self.roots = [dest_asn]
        else:  # Dest not in node_dir, no trs reached dest
            print("dest not in node_dir <<<")
        for pk in bg.pops:  # pk is the pop's prefix
            dst_asn = node_dir.get(pk)
            if not dst_asn:
                print("No ASN for prefix %s !!!???" % pk);  exit()
            n = bg.pops[pk]  # n is a PrunedNode
            self.add_to_asns(str(pk), n.subtree, n.depth)  # Node's ASN
            for sk in n.s_nodes:  # Node's s_nodes
                src_asn = node_dir.get(sk)
                if src_asn != dst_asn:  # Ignore edges inside dst_asn
                    self.e_asns[dst_asn].update(src_asn, n.s_nodes[sk], 0, sk)
        print("len(no_asn_nodes) = %d" % len(self.no_asn_nodes))
        print("len(bg.pops) = %d" % len(bg.pops))
        no_nodes_fn = c.no_asn_nodes_fn(c.msm_id)
        anf = open(no_nodes_fn, "w")
        for n in sorted(self.no_asn_nodes):
            anf.write("%s\n" % n)
        anf.close()

        #print("bg.roots >%s<" % bg.roots)
        if len(bg.roots) < 1:
            print(">>> No roots left after load_graph() deletions !!!")
        else:
            print("bin %d, roots %s" % (bin_nbr, bg.roots))
            dest_asn = node_dir.get(dest)  # Dest address from DestGraphs header
            self.roots = [dest_asn]
            for rx,rk in enumerate(bg.roots):
                if not rk in bg.pops:
                    print("==> root %s deleted by load_graph !!!" % rk)
                else:
                    r_asn = node_dir.get(rk)
                    print("Root %2d, %15s, ASN %s, in_count %d" % (
                        rx, rk, r_asn, bg.pops[rk].in_count))
                    if r_asn not in self.roots:
                        self.roots.append(r_asn)
        print("asn-graphs roots: %s" % self.roots)

        for pk in bg.pops:  # Now build the ASN s_nodes and their counts
            n = bg.pops[pk]  # PN from pops
            pn_type = -1  # Not a root
            e_asn =  node_dir.get(n.prefix)
            if not e_asn:
                print("Node %s has no ASN ???" % n.prefix)
                continue
            if n.prefix in bg.roots:  # Was it a full_graphs sub-root?
                r_asn =  node_dir.get(n.prefix)
                pn_type = 0  # Sub-root
                if n.prefix == dest:
                    self.e_asns[r_asn].type = 1  # Root of tr tree
                if not e_asn in self.roots:
                    self.roots.append(e_asn)

            #if len(n.s_nodes) != 0:
            #    print("Node %s (%s) has no s_nodes <depth %s>" % (
            #        n.prefix, e_asn, n.depth))
            for sk in n.s_nodes:  # Update d_node s_nodes with in_counts
                s_asn = node_dir.get(sk)
                if not s_asn:
                    print("Node %s s_node %s (depth %d) has no ASN" % (
                        sk, n.prefix, n.depth))
                    continue
                s_count = n.s_nodes[sk]
                fails = 0
                if s_asn != e_asn or pn_type >= 0:  # tr pkts from another ASN
                    self.e_asns[e_asn].update(s_asn, s_count, pn_type, sk)
                #else:  # tr pkts from same ASN
                #    print("%s (%s): sk %s already in ASN" % (
                #        n.prefix, e_asn, sk))

        #  Add other info to complete the BinGraph
        #==#  self.add_to_asns(dest, -1, 0)  # Handle dest like an ASN
        #for root_node in bg.roots:
        #    root_asn = node_dir[root_node]
        #    self.root_asns.append(root_asn)
        #    print("root %s in ASN %s" % (root_node, root_asn))

        print("bin %3d, roots %s\n" % (self.bin_nbr, self.roots))
        
        self.tree = []
        for ask in self.e_asns:
            e_asn = self.e_asns[ask]
            if ask == dest_asn or ask == dest:
                if e_asn.sources() == 0:
                    continue   # Discard dest asn with no source trs
            self.tree.append(e_asn)
        self.as_nodes = None    
        return None  # i.e. return an ASN_Graph

for msm_id in reqd_msms:
    no_asnf = no_whoisf = False
    asns_fn = c.asns_fn(msm_id)
    print("asns file >%s<" % asns_fn)
    if not os.path.isfile(asns_fn):
        print("No asns file; run pypy3 bulk-bgp-lookup.py <<<")
        exit()
    dgs_stem = c.dgs_stem
        # full_graphs adds "-asn" to dgs_stem !
    print("dgs_stem = >%s<" % dgs_stem)

    in_graphs_fn = c.msm_graphs_fn(msm_id)
    print("graph_fn = %s" % in_graphs_fn)
    n_bins_to_read = c.n_bins  # 3  ########################  c.n_bins

    dgs = dgs_ld.load_graphs(in_graphs_fn,  # Load a DestGraphs file (dgs)
                             mx_depth, mn_trpkts, n_bins_to_read)
        # dgs.ba is an array of BinGraphs
        # each BinGraph has a .pops dictionary, keys are IPprefixes

    print("BinGraphs: %s %s %d traces, %d,%d" % (
        dgs.msm_id, dgs.dest, dgs.n_traces, mx_depth, mn_trpkts))

    tb= timebins.TimeBins(dgs.start_dt, dgs.end_dt)

    # Make asn directory
    node_dir = {}  # Dictionary  IPprefix -> ASN
    asnf = open(asns_fn, "r", encoding='utf-8')
    for line in asnf:
        la = line.strip().split()
        node_dir[la[0]] = la[1]
        #print("node_dir key %s, val %s" % (la[0], node_dir[la[0]]))
    asnf.close()

    bga = []  # For the asn BinGraphs
    for bn,bg in enumerate(dgs.bga):
        print("--> bn=%d" % bn)
        asn_bg = ASN_Graph(bg, dgs.dest, node_dir, bn)
        bga.append(asn_bg)
        #if bn == 3:  # Testing, testing
        #    break  # Only do first few bins

    # Write asngraphs file
    print("= = = = =")
    out_dgs_fn = c.msm_asn_graphs_fn(msm_id)
    print("out_dgs_filename = %s" % out_dgs_fn)
    asnf = open(out_dgs_fn, "w")
    dest_asn = node_dir[dgs.dest]
    dg = dgs_ld.DestGraphs(2, dgs.msm_id, dest_asn, dgs.n_traces, \
            dgs.start_dt, dgs.end_dt, bga)
    dg.dump(asnf)
    asnf.close()
