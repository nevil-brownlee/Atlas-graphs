# 1731, Sat 11 Jan 2020 (NZDT)
# 1823, Sun 12 Nov 2017 (SGT)
#
# Make asns- file(s) from nodes- files
#   Modified from Emile Aben's bulk-ris-lookup.py
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import string, os

import sys, gzip, glob
from radix import Radix

from dgs_ld import find_usable_file, asn_colours

import config as c

# Extra command-line parameters (after those parsed by getparamas.py):
#
#   +e  Make asns files for all existing nodes files
#   +   No other options
#
#   reqd_msms may follow the +

reqd_ymds = [];  reqd_msms = [];  use_enf = False
pp_names = "m! y! e rb="  # index 0 to 3
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
r_bins = c.n_bins*c.n_days
for n, ix in enumerate(pp_ix):
    if ix == 0:    # m  (50mm) reqd_msms
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 2:  # e  Make asns files for all existing nodes files
        use_enf = True
    elif ix == 3:  # rb Read nodes files with rb bins
        r_bins = pp_values[n]
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("use_enf= %s, reqd_msms = %s, reqd_ymds = %s, r_bins = %s" % (
    use_enf, reqd_msms, reqd_ymds, r_bins))
c.set_ymd(reqd_ymds[0])

def load_bgp_file(ymd):
    bgp_fn = c.bgp_fn(ymd)  # Find suitable BGP file
    print("bgp_fn = %s" % bgp_fn)
    bfa = bgp_fn.split('.')
    print("bfa = %s" % bfa)
    bfa_files = glob.glob(bfa[0]+'*')
    print("bfa_files %s" % bfa_files)

    f_hours = 0
    for fn in bfa_files:
        print("  %s" % fn)
        if fn.index(bfa[0]) == 0:
            print("    date matches")
            fna = fn.split('.')
            print("fna %s" % fna)
            if bfa[1] == fna[1]:
                print("    exact match - use it")
                break
            else:
                print("    Different number of hours, OK")
                bgp_fn = fn
    print("    using file %s <<<" % bgp_fn)
    rq_date_s = c.start_ymd
    n = 0
    rtree = Radix()  # Load the BGP file into rtree
    with gzip.open(bgp_fn, 'r') as zif:
        tb_n = 0;  tb = None
        for ln in zif:
            n += 1
            line = ln.decode("utf-8", "replace")
            la = line.strip().split()
            if len(la) != 2:  # BGP record had no Origin AS !
                print("line len != 2 >%s<" % la)
            else:
                pfx = str(la[0]);  origin = str(la[1])

            try:
                rnode = rtree.search_exact( pfx )
                if rnode:
                   rnode.data['origin'].add( origin )
                else:
                    rnode = rtree.add( pfx )
                    rnode.data['origin'] = set([ origin ])
            except:
                print("search_exact failed for pfx = %s" % pfx)
            if n % 20000 == 0:
                print(".", end='');  sys.stdout.flush()

    sys.stderr.write("finished loading BGP data\n")
    sys.stderr.write("Loaded %d BGP lines" % n)
    return rtree

class ASN_Info:
    mx_cx = len(asn_colours)-2  # [0:20], i.e. 21 colours

    def __init__(self, asn):
        self.asn = asn
        self.prefixes = [];  self.counts = []
        self.cx = self.mx_cx+1  # 21:'dimgrey'

    def __str__(self):
        #return "%s:\n  %s\n  %s" % (self.asn, self.prefixes, self.counts)
        c_tot = 0
        for ic in self.counts:
            c_tot += int(ic)
        return "%s: %d  %d" % (self.asn, len(self.prefixes), c_tot)
 
    def update(self, prefix, in_count):
        self.prefixes.append(prefix)
        self.counts.append(in_count)

    def set_cx(self, cx):
        if cx <= self.mx_cx:
            self.cx = cx
 
    def write(self, aof):
        for x in range(0, len(self.prefixes)):
            #print("%s %s %s %d" % (
            aof.write("%s %s %s %d\n" % (
                self.prefixes[x], self.asn, self.counts[x], self.cx))

def process_nodes_file(nfn, rtree, afn):
    print("Process node file %s:" % nfn)
    nf = open(nfn, 'r')
    asn_dict = {};  no_asn_nodes = {}
    for line in nf:
        prefix, in_count, depth = line.rstrip().split()
        n_asn = '-'
        try:
            rnode = rtree.search_best( prefix )
            # print("rnode = %s" % rnode)  # <<<<
            if rnode:
                # account for multi-origin:            
                n_asn = '|'.join( rnode.data['origin'] )
        except:
            #pass  #  Not in bgp table!
            no_asn_nodes[prefix] = True
            print("%s not in bgp file (hence no ASN for it)" % prefix)
        #asnf.write("%s %s %s\n" % (prefix, n_asn, in_count))
        if not n_asn in asn_dict:
            asn_dict[n_asn] = ASN_Info(n_asn)
        asn_dict[n_asn].update(prefix, in_count)
    nf.close()
    asnf = open(afn, 'w')
    def asns_key(ak):  # Increasing-depth order
        return len(asn_dict[ak].prefixes)

    cx = 0;  aof = open(afn, 'w')  # Rewrite asns file with colour indexes
    for n,ak in enumerate(sorted(asn_dict, key=asns_key, reverse=True)):
        aif = asn_dict[ak]
        #print("n %d, aif >%s<" % (n, aif))
        aif.set_cx(n)
        aif.write(aof)
    aof.close();
    no_asns = sorted(no_asn_nodes)
    for n in no_asns:
        print(n)
    print("len(no_asn_nodes) = %d" % len(no_asn_nodes))

if use_enf:
    enf, nntb = c.find_msm_files("nodes", c.start_ymd)
    print("nodes files have %s timebins" % nntb)
    #print("existing nodes files = %s" % enf)
    reqd_msms = []
    for fn in enf:
        msm_id = int(fn.split("-")[1])
        reqd_msms.append(str(msm_id))
    print("Will process nodes files for msms %s" % ", ".join(reqd_msms))

rtree = load_bgp_file(reqd_ymds[0])

anfn = c.all_nodes_fn()
if os.path.exists(anfn):
    print("file %s exists!" % anfn)
    process_nodes_file(anfn, rtree, c.all_asns_fn())

def fn_for_r_bins(fn, r_bins):
    if r_bins == c.n_bins*c.n_days:
        return fn  # r_bins not changed
    nfa = fn.rsplit("-", 1)
    nfb = nfa[1].split(".")
    if int(nfb[0]) != r_bins:
        return "%s-%d.txt" % (nfa[0], r_bins)
    else:
        return fn

for ymd in reqd_ymds:
    c.start_ymd = ymd
    for msm_id in reqd_msms:  # Make asns files for all the reqd_msms
        i_msm_id = int(msm_id)
        nfn = fn_for_r_bins(c.nodes_fn(i_msm_id), r_bins)
        print("nodes file %s:" % nfn)
        afn = c.asns_fn(msm_id)
        print("will write asns_fn: %s" % afn)
        process_nodes_file(nfn, rtree, afn)

