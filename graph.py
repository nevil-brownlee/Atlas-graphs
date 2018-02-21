# 1636, Sun 12 Nov 2017 (SGT)
# 1514, Wed 10 Jan 2016 (NZDT)
#
# graph.py: build graph from traceroute data
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import traceroute as tr
import dgs_ld
import ipp

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
        self.prefix = prefix;  self.depth = depth
        self.s_nodes = collections.OrderedDict()
            # key = prefix, value = incoming hops
        self.state = 0  # loop testing: 0 not tested, 1 testing, 2 Complete
        self.mx_edges = 0  # Max edges seen on path to dest
        self.keep = False  # Set True to keep this node
        self.subtree = 0  # 1 = dest is root
        self.depth = 0  # Recursion depth reached while building graph
        self.visited = False  # Only used by print_\node
        
    def __str__(self):
        sources = []
        for sk in self.s_nodes:
            ps = ''
            if self.prefix.is_rfc1918:
                ps = ' *'
            ks = '-'
            if self.pops[sk].keep:
                ks = 'K'
            sources.append("%s:%d%s %s" % (
                sk, self.s_nodes[sk], ps, ks))
        return("node: %s, %s %s" % (self.prefix, self.keep, sources))

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

    def dump(self, df):
        in_count = 0
        for nk in self.s_nodes:
            in_count += self.s_nodes[nk]
        df.write("Node %s %d %d\n" % (
            self.prefix, self.subtree, in_count))
        for nk in sorted(self.s_nodes):
            df.write("  %s %d" % (nk, self.s_nodes[nk]))
        df.write("\n")
                 
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

    def pruneable(self, mx_depth, min_tr_pkts, depth, mx_so_far):
        if debug_prune:
            print("--in %2d:%s s_nodes %d, %s" % (
                depth, Node.indent*depth, len(self.s_nodes),
                self.str_mne(min_tr_pkts/4)))

        self.depth = depth  # Remember recursion depth
        if depth > mx_depth:
            print("mx_depth reached at %s" % self.prefix)
            Node.n_too_deep += 1
            return mx_so_far, False

        if self.subtree != 0:  # Already walked this subtree
            #print("already walked subtree %d" % self.subtree)
            Node.n_already_walked += 1
            return mx_so_far, False  

        if self.state != 0:  # Been here before
            #print("loop detected at %s" % self.prefix)
            Node.n_loop_detected += 1
            return mx_so_far, False

        self.state = 1
        if len(self.s_nodes) == 0:  # Can't recurse deeper
            if debug_prune:
                print("--nr %2d:%s no s_nodes in %s" % (
                    depth, Node.indent*depth, self.str_mne(min_tr_pkts/4)))
            return mx_so_far, False  

        prune_keys = []
        for nk in self.s_nodes:
            tr_pkts = self.s_nodes[nk]  # Tr_Pkts (tr pkts) from node nk
            if tr_pkts >= min_tr_pkts:
                self.pops[nk].keep = True
            else:
                prune_keys.append(nk)
        for pk in prune_keys:
            self.s_nodes.pop(pk)

        if len(self.s_nodes) == 0:  # No s_nodes left 
            if debug_prune:
                print("--nn %2d:%s no s_nodes remain in %s" % (
                    depth, Node.indent*depth, self.str_mne(min_tr_pkts/4)))
            return mx_so_far, False  
            
        self.pops[self.prefix].keep = True  # Node has s_nodes left

        for nk in self.s_nodes:  # Examine next deeper nodes
            tr_pkts = self.s_nodes[nk]  # Tr_Pkts (tr pkts) from node nk
            if tr_pkts > mx_so_far:
                mx_so_far = tr_pkts

            n = self.pops[nk]
            if c.write_stats:
                #self.sf.write("N  %s  %d %d  %d\n" % (
                #    n.prefix, depth, tr_pkts, mx_so_far))
                self.sf.write("E  %d %s %s %d\n" % (
                    depth, self.prefix, nk, tr_pkts))
            path_mxe, mxe_reached = n.pruneable(  ### Check next deeper hop
                mx_depth, min_tr_pkts, depth+1, mx_so_far)

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

def incr_src_counts(dn, sa, n):  # incr dn counts for source responder sr
    self_ref = dn.prefix == sa
    #    dn, sa, n, self_ref)) #py3
    if not self_ref:
        if sa in dn.s_nodes:
            dn.s_nodes[sa] += n
        else:
            dn.s_nodes[sa] = n
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
    print("fmx: t_dest = %s, mx_tr_pkts = %d" % (t_dest, mx_tr_pkts))
    return t_dest, mx_tr_pkts

def build_graph(tb_n, traces, g_dest, t_traces, t_addrs, t_hops, t_succ, \
        t_addrs_deleted, t_hops_deleted, msm_id, sf):
    d_name, mx_depth, prune_p, p_pkts, prune_s = c.msm_pp(msm_id)
    # Build pops{}, key = ip_adr, values = Node
    # Each Node has tr_pkts that reach it (in s_nodes{})
    msm_id = [];  dest_n = [];  Node.pops = collections.OrderedDict()
        # Clear these for each graph!
    tot_self_ref = 0
    nt = -1
    for t in traces:
        nt += 1
        #print(">>> Trace %d, t.dest=%s" % (nt, t.dest))
        if (not t.dest) or len(t.hops) < 2:
            continue  # Need at least two pops to get one edge

        # g_dest and t.dest are both ipp prefixes
        if not t.dest in Node.pops:  # Make sure dest is in pops
            Node.pops[t.dest] = Node(t.dest, 0)  # depth 0, i.e. root level
        if not t.dest in dest_n:  # Remeber trace's destination(s)
            dest_n.append(t.dest)  # Full addesses, not /24
        if not t.msm_id in msm_id:  # Ditto msm_id(s)
            msm_id.append(t.msm_id)
        # Don't really need this for t_dest and msm_id

        d = len(t.hops)+1
        for hx in range(len(t.hops)-2, -1, -1):  # Earlier hops
            depth = d - (hx+1)
                # Hop 0 has addresses of 1-st hop dests
            dra = t.hops[hx+1].responders  # Responders for this hop (hx+1)
            sra = t.hops[hx].responders  # Responders for previous hop (hx)
            st_rtts = 0
            for sr in sra:
                if not sr.ip_addr in Node.pops:  # Make sure responder in pops
                    Node.pops[sr.ip_addr] = Node(sr.ip_addr, depth)
                st_rtts += len(sr.rtts)
            for dr in dra:
                da = dr.ip_addr
                if not da in Node.pops:  # Make sure dest responder is in pops
                    #print("Add %s to Node.pops" % da)
                    if not da.is_rfc1918:
                        Node.pops[da] = Node(dr.ip_addr, depth)
                n_rtts = len(dr.rtts)
                for sr in sra:
                    self_ref = incr_src_counts(  # tr packets
                        Node.pops[da], sr.ip_addr, len(sr.rtts))
                    if self_ref:  # Self-reference to sra[]
                        tot_self_ref += 1
                        if debug_self_ref:
                            print("self_ref: trace %d, pop %s  <<<" % (
                                nt, Node.pops[da].prefix_s()))
    print("*** self_refs pruned = %d" % tot_self_ref)

    # Graph built (in pops{})
    #print_pops()

    for pk in Node.pops:
        Node.pops[pk].state = 0  # Not tested        
        total_loops_found = 0

    t_dest, mx_tr_pkts = find_mx_tr_pkts()  # Subnet 0 root has max incoming tr_pkts
    root_mx_tr_pkts = mx_tr_pkts
    if p_pkts:
        prune_tr_pkts = prune_p  ## For whole-network stats gathering
    else:
        prune_tr_pkts = int(prune_p*mx_tr_pkts/100.0)
    print("*** mx_tr_pkts=%d,  prune_pc=%s, prune_tr_pkts=%d, t_dest=%s" % (
        mx_tr_pkts, prune_s, prune_tr_pkts, t_dest))
    print("*** prune links with < %d tr_pkts" % prune_tr_pkts)

    if len(dest_n) > 1:
        print(">>> More than one dest_n <<<\n    "),
        for n in dest_n:
            print("   dest_n = %s" % n)

    if c.write_stats:
        sf.write("H %s %d  %d %s  %d  %3d\n" % (
            t_dest, len(traces), mx_tr_pkts, prune_s, prune_tr_pkts, tb_n)) 
        Node.sf = sf

    #for pk in Node.pops:  # Clear Node states (after loop testing)
    #    Node.pops[pk].state = 0  # No trees built yet

    print("dest_n[0] = %s" % dest_n[0])
    t_dest = dest_n[0]  # There should only be one destination!
    roots = []
    #print("roots = %s, t_dest = %s" % (roots, t_dest))
    Node.n_already_walked = Node.n_loop_detected = Node.n_too_deep = 0
    for st in range(1, 20):  # Up to 20 roots
        # Each root gets its subtree set to st
        #for r in roots:
        #    print("%s >%s<," % (r, Node.pops[r]))
        #print()
        if not t_dest:  # No more 'roots'
            break
        roots.append(t_dest)
        if c.write_stats:
            sf.write("R %d %s %d\n" % (st, roots[-1], mx_tr_pkts))
        for pk in Node.pops:
            n = Node.pops[pk]
            n.state = 0  # Not tested
        n = Node.pops[t_dest];  n.keep = True
        n.pruneable(mx_depth, prune_tr_pkts, 0, 0)  # Writes stats files !!
            # Prune to mx_depths + prune_tr_pkts from root
        n.mark_subtree(st, mx_depth)

        #print("--- t_dest = %s, subtree %d" % (t_dest, n.subtree))
        t_dest, mx_tr_pkts = find_mx_tr_pkts()
        #print("    t_dest = %s, mx_tr_pkts = %d" % (t_dest, mx_tr_pkts))
        if mx_tr_pkts < prune_tr_pkts:
            break

    used_roots = []
    for root in roots:
        if len(Node.pops[root].s_nodes) != 0:  # Has incoming s_nodes
            used_roots.append(root)
        else:
            Node.pops[root].keep = False
    roots = used_roots

    drawn_roots = []
    for j,root in enumerate(roots):  # Check root nodes
        root_s = str(root)
        rn = Node.pops.get(root_s)
        ordinary = False
        if rn:
            for nk in Node.pops:  # Do any s_nodes point to rn?
                n = Node.pops[nk]
                if root_s in n.s_nodes:  # Yes, it's not a sub-root
                    ordinary = True
        if ordinary:
            continue  # Don't draw it yet
        drawn_roots.append(root_s)
    found_roots = list(map(str, roots))
    print("roots:  %s\ndrawn:  %s\n" % (found_roots, drawn_roots))

    print()
    ##print_pops()

    if c.write_stats:
        sf.write("T %d %d %d\n" % (
            Node.n_already_walked, Node.n_loop_detected, Node.n_too_deep))
    
    tree = []
    znodes = 0
    root_full = dest_n[0]
    ##???root_24 = root_full.network(24)
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

    g = dgs_ld.BinGraph(t_traces, t_succ, t_addrs_deleted, \
        t_addrs, t_hops, t_hops_deleted, \
        root_mx_tr_pkts, drawn_roots, tree, 1)
        # graphs file version is 1 = node graphs (full_graphs True)
    return g

