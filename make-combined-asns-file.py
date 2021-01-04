# 1620, Sat 11 Jan 2020 (NZDT)
# 1520, Wed 10 Jul 2019 (NZST)
#
# make-combined-asns-file.py  # Makes single asns file for all msm_ids
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import sys, datetime, string, os, glob

import config as c

pp_ix, pp_values = c.set_pp("")  # Set up config info (no + params)

enf, nntb = c.find_msm_files("asns", c.start_ymd)
print("enf = %s" % enf)
for gfn in enf:
    fna = gfn.split("-")
    msm_id = int(fna[1]);  n_bins = int(fna[-1].split(".")[0])
    print("  msm_id = %d, n_bins = %s" % (msm_id, n_bins))
    if n_bins != c.n_bins:
        print("*** Inconsistent nbr of timebins (%d != %d)" % (
            n_bins, c.n_bins))

asn_dir = {}  # Dictionary  IPprefix -> ASN

for fn in enf:
    print(fn)
    asnsf = open(fn, 'r', encoding='utf-8')
    for line in asnsf:
        la = line.strip().split()
        ip_addr = la[0];  asn = la[1]
        if not ip_addr in asn_dir:
            asn_dir[ip_addr] = asn
    asnsf.close()

all_asns_fn = c.all_asns_fn()
aaf = open(all_asns_fn, 'w')
n_keys = sorted(asn_dir)
print("Writing %s, %d nodes" % (all_asns_fn, len(asn_dir)))
for ip_addr in asn_dir:
    aaf.write("%s %s\n" % (ip_addr, asn_dir[ip_addr]))
aaf.close()

