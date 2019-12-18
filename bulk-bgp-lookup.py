# 1823, Sun 12 Nov 2017 (SGT)
#
# Modified from Emile's bulk-ris-lookup.py
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import string, os

import sys, gzip, glob
from radix import Radix

from dgs_ld import find_usable_file

import config as c
c.set_pp(False, c.msm_id)  # Set prune parameters

bgp_fn = c.bgp_fn
print("bgp_fn = %s" % bgp_fn)
bfa = bgp_fn.split('.')
print("bfa = %s" % bfa)
bfa_files = glob.glob(bfa[0]+'*')
f_hours = 0
for fn in bfa_files:
    print("  %s" % fn)
    if fn.index(bfa[0]) == 0:
        print("    date matches")
        fna = fn.split('.')
        if bfa[1] == fna[1]:
            print("exact match - use it")
            break
        elif int(fna[1]) > int(bfa[1]):
            print("Longer number of hours, OK")
            bgp_fn = fn
print("   using file %s <<<" % bgp_fn)

reqd_date = b"20120222"  # "20120517" b"20120507"
rq_date_s = reqd_date.decode('utf-8')

rtree=Radix()

n = 0
with gzip.open(bgp_fn, 'rb') as zif:
    tb_n = 0;  tb = None
    for ln in zif:
        n += 1
        line = ln.decode("utf-8", "replace")
        la = line.strip().split()
        if len(la) != 2:  # BGP record had no Origin AS !
            print("line len != 2 >%s<" % la)
        else:
            pfx = str(la[0]);  origin = str(la[1])
        #print("pfx = %s, origin = %s" % (pfx, origin))
        #pfxa = pfx.split("'")
        #print("pfxa = %s" % pfxa)
        #if len(pfxa) != 3:
        #    print(">>> pfx = >%s<, pfxa = %s" % (pfx, pfxa))
        #    continue
        #pfx = pfxa[1]  # python3; now without b'and closing ' !!!

        try:
            rnode = rtree.search_exact( pfx )
            if rnode:
               rnode.data['origin'].add( origin )
            else:
                rnode = rtree.add( pfx )
                rnode.data['origin'] = set([ origin ])
        except:
            print("search_exact failed for pfx = %s" % pfx)

sys.stderr.write("finished loading BGP data\n")
sys.stderr.write("Loaded %d lines" % n)

enf, nntb = c.find_msm_files("nodes", reqd_date)
print("nodes files have %s timebins" % nntb)
print("existing nodes files = %s" % enf)
for msm_id in enf:
    print("msm_id = %s" % msm_id)
    asn_fn = c.asn_fn(int(msm_id))
    asn_f = open(asn_fn, "w")
    print("will write asn_fn: %s" % asn_fn)

    node_fn = c.nodes_fn(int(msm_id))  # Rebuild asn files for all msm_ids
                                       # That's a low-run-time operation!
    print("usable node_fn = %s" % node_fn)
    if node_fn != '':
        print("Will use node-file %s" % node_fn)
    else:
        print("No usable node file, run  pypy3 make-combined-svgs <<<")
        exit()
    #print("node_fn = %s" % node_fn)

    node_f = open(node_fn, "r")
    no_asn_nodes = {}
    for line in node_f:
        prefix = line.rstrip()  # Remove whitespace
        print("prefix = %s" % prefix)
        origin = '-'
        try:
            rnode = rtree.search_best( prefix )
            # print("rnode = %s" % rnode)  # <<<<<<<<<<<<<<<<<<<<<
            if rnode:
                # account for multi-origin:            
                origin = '|'.join( rnode.data['origin'] )
        except:
            #pass  #  Not in bgp table!
            no_asn_nodes[prefix] = True
        asn_f.write("%s %s\n" % (prefix, origin))

    asn_f.close();  node_f.close()
    no_asns = sorted(no_asn_nodes)
    for n in no_asns:
        print(n)
    print("len(no_asn_nodes) = %d" % len(no_asn_nodes))
