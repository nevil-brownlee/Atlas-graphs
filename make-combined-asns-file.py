# 1520, Wed 10 Jul 2019 (NZST)
#
# make-combined-asns-file.py  # Makes single asns file for all msm_ids
#
# Copyright 2019, Nevil Brownlee,  U Auckland | RIPE NCC

import sys, datetime, string, os, glob

import config as c

c.set_pp(False, c.msm_id)  # Work on graphs-* file

asns_fn = c.asn_fn(5001)
print("asns_fn = %s" % asns_fn)

dir, fn = asns_fn.split("/", 1)
name, msm, ymd, hhmm, nbins, mx_depth, rest = fn.rsplit('-',6)
prune_s, ftype = rest.split(".")
g_fn = "%s/%s-*-%s-%s-%s-%s-%s.%s" % (dir, 
        name, ymd, hhmm, nbins, mx_depth, prune_s, ftype)
print("-1- g_fn = %s" % g_fn)

node_dir = {}  # Dictionary  IPprefix -> ASN
afa_files = glob.glob(g_fn)
for fn in afa_files:
    print(">>> %s" % fn)
    asnf = open(fn, 'r', encoding='utf-8')
    for line in asnf:
        ip_addr, asn = line.strip().split()
        if not ip_addr in node_dir:
            node_dir[ip_addr] = asn
    asnf.close()

all_asns_fn = g_fn = "%s/%s-all-%s-%s-%s-%s-%s.%s" % (dir, 
        name, ymd, hhmm, nbins, mx_depth, prune_s, ftype)
aaf = open(all_asns_fn, 'w')
n_keys = sorted(node_dir.keys())
for ip_addr in node_dir:
    aaf.write("%s %s\n" % (ip_addr, node_dir[ip_addr]))
aaf.close()

