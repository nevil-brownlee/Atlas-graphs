# 1129, Wed  8 Jan 2020 (NZDT)
# 1636, Sun 12 Nov 2017 (SGT)
# 1514, Wed 10 Jan 2016 (NZDT)
#
# graph.py: build BinGraph from traceroute data
#
# Copyright 2019, Nevil Brownlee,  U Auckland | RIPE NCC

import traceroute as tr
import dgs_ld
##import ipp

import sys, collections

import config as c

debug_self_ref = False
debug_test_loop = False
debug_prune = False

class Node:
    pops = collections.OrderedDict()  # Dictionary of nodes
    indent = ' . '
    sf = None  # Stats file
    n_already_walked = n_loop_detected = n_too_deep = 0
    of = None  # draw_node output file
    
    def __init__(self, prefix, depth):
        self.prefix = prefix
        self.d_total = depth;  self.n_depths = 1
        self.depth = float(depth)  # Average depth reached while building graph
        self.s_nodes = collections.OrderedDict()
            # key = prefix, value = incoming hops
        self.state = 0  # loop testing: 0 not tested, 1 testing, 2 Complete
        self.mx_edges = 0  # Max edges seen on path to dest
        self.keep = False  # Set True to keep this node
        self.subtree = 0  # 1 = dest is root
        #self.n_distal_trs = 0  # Traceroute packets reaching (depth-1)th node
        self.visited = False  # Only used by print_node
        ###self.in_count = 0  # nbr of tr_pkts received from s_nodes
        self.es_count = 0  # nbr of tr_pkts sent from this node

    def update_depth(self, depth):  # Compute running average depth
        self.d_total += depth;  self.n_depths += 1
        self.depth = float(self.d_total)/self.n_depths
        
    def __str__(self):
        sources = []
        for sk in self.s_nodes:
            ps = ''
            if self.prefix.is_rfc1918:
                ps = ' *'
            ks = '-'
            s_n =  self.pops.get(sk)
            if not s_n:
                print(">>> s_node key %s is not in Node.pops" % sk)
            elif self.pops[sk].keep:
                ks = 'K'
            sources.append("%s:%d%s %s" % (
                sk, self.s_nodes[sk], ps, ks))
        return("Node: %s, %s %s ->%d" % (
            self.prefix, self.keep, sources, self.es_count))

    def str_mne(self, min_edges):
        sources = []
        if len(self.s_nodes) > 0:
            for sk in self.s_nodes:
                ks = '-'
                if self.pops[sk].keep:
                    ks = 'K'
                if self.s_nodes[sk] >= min_edges:
                    sources.append("%s:%d %s" % (
                        sk, self.s_nodes[sk], ks))
                else:
                    sources.append('<%s' % ks)
        return("node: %s, %s %s" % (self.prefix, self.keep, sources))

    def dump(self, df):  # dgs_ld uses this to dump pops Nodes in a BinGraph
        # depth added to Node and s_nodes records    13 Jan 2020
        # use count as max of in_count and es_count  22 Aug 2020
        in_count = 0
        for nk in self.s_nodes:
            in_count += self.s_nodes[nk]
        count = in_count
        if in_count < self.es_count:
            count = self.es_count
        depth = self.depth  #  Node depth
        df.write("Node %s %d %d %d\n" % (
            self.prefix, self.subtree, count, self.depth))
        for nk in sorted(self.s_nodes):
            df.write("  %s %d" % (nk, self.s_nodes[nk]))
        depth = self.depth+1  # Depth of s_nodes (= node depth -1)
        df.write(" %d\n" % depth)
                 
    def prefix_s(self):
        return '"%s"' % str(self.prefix)[0:-5]  # Trim '.0/24'

    def print_node(self, level):
        # print("-- %d -- %s" % (level, self))

        i_visited = self.visited
        self.visited = True  # Avoid recursive loops!
        if i_visited:  # Already printed
            return
        if level >= 33:  # Check for recursive loop
            print("@@@@@ level = %d, breaking loop" % level)
            exit()
        if len(self.s_nodes) == 0:  # No incoming responders
            return
        in_count = 0
        for nk in self.s_nodes:
            in_count += self.s_nodes[nk]
        if in_count == 0:  # No incoming edges (hop 0)
            print("%2d:%18s%s  %s" % (
                level, self.prefix, node.indent*level, "<-"))
            return
        for nk in self.s_nodes:
            ps = ' '
            if nk.is_rfc1918:
                ps = '*'
            self.pops[nk].print_node(level+1)
            print("%2d:%18s%s%s %d %s" % (level, self.prefix,
                node.indent*level, nk, self.s_nodes[nk], ps))

    def pruneable(self, min_tr_pkts, depth, mx_so_far):
        if debug_prune:
            print("--in %2d:%s s_nodes %d, %s" % (
                depth, Node.indent*depth, len(self.s_nodes),
                self.str_mne(min_tr_pkts/4)))

        self.depth = depth  # Remember recursion depth

        if self.subtree != 0:  # Already walked this subtree
            #print("already walked subtree %d" % self.subtree)
            Node.n_already_walked += 1
            return mx_so_far, False  

        if self.state != 0:  # Been here before
            Node.n_loop_detected += 1
            return mx_so_far, False

        self.state = 1
        if len(self.s_nodes) == 0:  # Can't recurse deeper
            if debug_prune:
                print("--nr %2d:%s no s_nodes in %s" % (
                    depth, Node.indent*depth, self.str_mne(min_tr_pkts/4)))
            return mx_so_far, False  

        for nk in self.s_nodes:
            tr_pkts = self.s_nodes[nk]  # Tr_Pkts (tr pkts) from node nk
            self.pops[nk].keep = True

        if len(self.s_nodes) == 0:  # No s_nodes left 
            if debug_prune:
                print("--nn %2d:%s no s_nodes remain in %s" % (
                    depth, Node.indent*depth, self.str_mne(min_tr_pkts/4)))
            return mx_so_far, False  
            
        self.pops[self.prefix].keep = True  # Node has s_nodes left

        #self.n_distal_trs = 0
        for nk in self.s_nodes:  # Examine next deeper nodes
            tr_pkts = self.s_nodes[nk]  # Tr_Pkts (tr pkts) from node nk
            #self.n_distal_trs += tr_pkts

            if tr_pkts > mx_so_far:
                mx_so_far = tr_pkts

            n = self.pops[nk]
            if c.write_stats:
                self.sf.write("E  %d %s %s %d\n" % (
                    depth, self.prefix, nk, tr_pkts))
            path_mxe, mxe_reached = n.pruneable(  ### Check next deeper hop
                min_tr_pkts, depth+1, mx_so_far)

        if debug_prune:
            print("--rt %2d:%s %s" % (
                depth, Node.indent*depth, self.str_mne(min_tr_pkts/4)))
            print("--   %2d:%s %s" % (
                depth, '   '*depth, self))

        return mx_so_far, mxe_reached

    def mark_subtree(self, st_nbr, mx_depth):
        #print("+++ mark_subtree(%s): self = %s" % (st_nbr, self))
        if len(self.s_nodes) == 0 or self.subtree != 0:
            return
        self.subtree = st_nbr
        if self.depth < mx_depth:
            for nk in self.s_nodes:  # Prefixes for incoming tr_pkts
                sn = self.pops[nk]
                sn.mark_subtree(st_nbr, mx_depth)
        return

    def mark_unvisited(self):
        self.state = 0
        if len(self.s_nodes) == 0:
            return
        for nk in self.s_nodes:  # Prefixes for incoming tr_pkts
            sn = self.pops[nk]
            sn.state = 0
        return

def print_pops():
    print("pops ...")
    for pk in Node.pops:
        print("   %s" % Node.pops[pk])

def test_loop(n, level):  # test for loop through node n
    if n.state == 2:  # Testing complete
        return None, 0
    elif n.state == 1:  # Testing
        return 2, 0  # Tell caller we've been here before!
    if len(n.s_nodes) == 0:
        n.state = 2  # Testing complete
        return None, 0
    #print("tl:start %d  %s%s" % (level, '   '*level, n.prefix_s()))
    n.state = 1  # Testing
    sk_delete = []
    loops_found = 0
    for sk in n.s_nodes:
        #print("tl:sk %d  %s%s" % (level, '   '*level, sk);  sys.stdout.flush())
        r, lf = test_loop(Node.pops[sk], level+1)
        loops_found += lf
        if r == 2:
            loops_found += 1
            if debug_test_loop:
                #print("loop found, sk=%s to %s" % (sk, n.prefix_s()))
                print("loop found, sk=%s to %s" % (sk, n.prefix))
            sk_delete.append(sk)  # Can't delete entry while iterating
    for sk in sk_delete:  # Delete the backward pointers
        n.s_nodes.pop(sk)
    n.state = 2  # Testing complete
    return None, loops_found

t_addr = "81.23.23.77"
def incr_src_counts(dn, sa, n):  # incr dn counts for source responder sr
    self_ref = dn.prefix == sa
    if not self_ref:
        if sa in dn.s_nodes:
            dn.s_nodes[sa] += n
        else:
            dn.s_nodes[sa] = n
    #if str(sa) == t_addr:
    #    print("i_c_s %s -> %s (%d)" % (sa,dn.prefix, dn.s_nodes[sa]))
    return self_ref

def find_mx_tr_pkts():  # Find node with max incoming tr_pkts
    mx_tr_pkts = 0;  t_dest = None  # It will be used as next 'root'
    for pk in Node.pops:
        n = Node.pops[pk]
        if n.subtree == 0:
            tr_pkts = 0
            for nk in n.s_nodes:
                sn = Node.pops[nk]
                if n.subtree == 0:
                    tr_pkts += n.s_nodes[nk]
            if tr_pkts > mx_tr_pkts:
                mx_tr_pkts = tr_pkts;  t_dest = pk
    #print("fmx: t_dest = %s, mx_tr_pkts = %d" % (t_dest, mx_tr_pkts))
    return t_dest, mx_tr_pkts

def build_graph(tb_n, traces, g_dest, t_traces, t_addrs, t_hops, t_succ, \
        t_addrs_deleted, t_hops_deleted, msm_id, sf):
    # Build pops{}, key = ip_adr, values = Node
    # Each Node has tr_pkts that reach it (from s_nodes{})
    msm_id = [];  dest_n = [];  Node.pops = collections.OrderedDict()
        # Clear these for each graph!
    tot_self_ref = 0
    nt = -1
    for t in traces:
        nt += 1
        if (not t.dest) or len(t.hops) < 2:
            continue  # Need at least two pops to get one edge
        #print(">>> Trace %d, t.dest=%s" % (nt, t.dest))

        # g_dest and t.dest are both ipp prefixes
        if not t.dest in Node.pops:  # Make sure dest is in pops
            Node.pops[t.dest] = Node(t.dest, 0)  # depth 0, i.e. root level
        if not t.dest in dest_n:  # Remeber trace's destination(s)
            dest_n.append(t.dest)  # Full addesses, not /24
        if not t.msm_id in msm_id:  # Ditto msm_id(s)
            msm_id.append(t.msm_id)
        # Don't really need this for t_dest and msm_id

        d = len(t.hops)+1
        for hx in range(len(t.hops)-1, -1, -1):  # Check all nodes are in pops
            depth = d - (hx+2)
            for r in t.hops[hx].responders:  # Responders at this depth
                #print("depth %d, r %s" % (depth, r.ip_addr))
                if not r.ip_addr.is_rfc1918:
                    if not r.ip_addr in Node.pops:
                        Node.pops[r.ip_addr] = Node(r.ip_addr, depth)
                    else:  # Compute running average depth
                        Node.pops[r.ip_addr].update_depth(depth)

        for hx in range(len(t.hops)-2, -1, -1):  # Earlier (more distal) hops
            depth = d - (hx+1)
                # Hop 0 has addresses of 1-st hop dests
            dra = t.hops[hx+1].responders  # Responders for this hop (hx+1)
            sra = t.hops[hx].responders  # Responders for previous hop (hx)
            st_rtts = 0
            for sr in sra:
                #if not sr.ip_addr in Node.pops:  # Check src responder in pops
                #    Node.pops[sr.ip_addr] = Node(sr.ip_addr, depth)
                sa = str(sr.ip_addr)
                st_rtts += len(sr.rtts)
                for dr in sra:
                    Node.pops[sr.ip_addr].es_count += st_rtts
                Node.pops[sr.ip_addr] 
            for dr in dra:
                da = dr.ip_addr
                #if not da in Node.pops:  # Check dest responder is in pops
                #    #print("Add %s to Node.pops" % da)
                #    if not da.is_rfc1918:
                #        Node.pops[da] = Node(dr.ip_addr, depth)
                n_rtts = len(dr.rtts)  # Nbr of responses revceived by probe
                if not da.is_rfc1918:
                    for sr in sra:
                        self_ref = incr_src_counts(  # tr packets
                            Node.pops[da], sr.ip_addr, len(sr.rtts))
                        if self_ref:  # Self-reference to sra[]
                            tot_self_ref += 1
                            if debug_self_ref:
                                print("self_ref: trace %d, pop %s  <<<" % (
                                    nt, Node.pops[da].prefix_s()))
        #if len(hxa) > 1:
        #    print("--> hxa %s, d %d" % (hxa, d))

    print("*** self_refs pruned = %d" % tot_self_ref)

    # Graph built (in pops{})
    # print_pops()

    for pk in Node.pops:
        Node.pops[pk].state = 0  # Not tested        
        total_loops_found = 0

    t_dest, mx_tr_pkts = find_mx_tr_pkts()  # Subnet 0 root has max incoming tr_pkts
    root_mx_tr_pkts = mx_tr_pkts

    if len(dest_n) > 1:
        print(">>> More than one dest_n <<<\n    "),
        for n in dest_n:
            print("   dest_n = %s" % n)

    if c.write_stats:
        sf.write("H %s %d  %3d\n" % (
            t_dest, len(traces), tb_n)) 
        Node.sf = sf

    #for pk in Node.pops:  # Clear Node states (after loop testing)
    #    Node.pops[pk].state = 0  # No trees built yet

    t_dest = dest_n[0]  # There should only be one destination!
    roots = []
    #print("roots = %s, t_dest = %s" % (roots, t_dest))
    Node.n_already_walked = Node.n_loop_detected = Node.n_too_deep = 0
    mx_roots = 100;  min_tr_pkts = 9999999
    for st in range(1, 19):  # Up to 19 more "roots"
        # Each root gets its subtree set to st
        #for r in roots:
        #    print("%s >%s<," % (r, Node.pops[r]))
        #print()
        if not t_dest:  # No more 'roots' found by find_mx_tr_pkts()
            break
        roots.append(t_dest)
        if c.write_stats:
            sf.write("R %d %s %d\n" % (st, roots[-1], mx_tr_pkts))
        for pk in Node.pops:
            n = Node.pops[pk]
            n.state = 0  # Not tested
        n = Node.pops[t_dest];  n.keep = True
        n.pruneable(min_tr_pkts, 0, 0)  # Writes stats files !!workon py-git;  cd py-yaml/Atlas-graphs
            # Prune to mx_depths + prune_tr_pkts from root
        n.mark_subtree(st, c.mx_depth)

        #print("--- t_dest = %s, subtree %d" % (t_dest, n.subtree))
        t_dest, mx_tr_pkts = find_mx_tr_pkts()
        #print("    st = %s, t_dest = %s, mx_tr_pkts = %d <<<<<<<<<<<" % (
        #    st, t_dest, mx_tr_pkts))

    used_roots = [str(roots[0])]  # Make sure we keep root[0], it's the actual dest!
    for root in roots[1:]:
        if len(Node.pops[root].s_nodes) != 0:  # Has incoming trpkts
            used_roots.append(root)
        else:
            Node.pops[root].keep = False
    roots = used_roots;  drawn_roots = [roots[0]]
 
    for j,root in enumerate(roots[1:]):  # Check root nodes
        root_s = str(root)
        rn = Node.pops.get(root_s)
        ordinary = False
        if rn:
            for nk in Node.pops:  # Do any s_nodes point to rn?
                n = Node.pops[nk]
                if root_s in n.s_nodes:  # Yes, it's not a sub-root
                    ordinary = True
        if not ordinary:
            drawn_roots.append(root_s)
    print("roots:  %s" % drawn_roots)
    print()

    if c.write_stats:
        sf.write("T %d %d %d\n" % (
            Node.n_already_walked, Node.n_loop_detected, Node.n_too_deep))
    
    tree = []
    znodes = 0
    root_full = dest_n[0]
    root_24 = root_full
    for pk in Node.pops:  # Visited nodes have been pruned
        n = Node.pops[pk]
        if not n.keep:  # Node was pruned (i.e. not kept)
            continue
        if n.subtree != 0:
            if n.prefix == root_24:  # dest node
                n.prefix = root_full
            tree.append(n)
        else:
            znodes += 1
    print("*** len(tree)=%d, znodes=%d" % (len(tree), znodes))

    '''
    cs_nodes = {}
    for pk in Node.pops:
        n = Node.pops[pk]
        for s_prefix in n.s_nodes:
            if s_prefix not in cs_nodes:
                cs_nodes[s_prefix] = n.s_nodes[s_prefix]
            else:
                cs_nodes[s_prefix] += n.s_nodes[s_prefix]
    '''
    g = dgs_ld.BinGraph(t_traces, t_succ, t_addrs_deleted, \
        t_addrs, t_hops, t_hops_deleted, \
        root_mx_tr_pkts, drawn_roots, tree, 1, \
        Node.pops)
##        Node.pops, cs_nodes)
            # graphs file version is 1 = node graphs (full_graphs True)
    return g
