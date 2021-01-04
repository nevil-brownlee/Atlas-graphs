# 1259, Thu  9 Jan 2020 (NZDT)
# 1625, Wed 18 Dec 2019 (NZDT)
# 1812, Sun  4 Mar 2018 (NZDT)
#
# config.py: configuration info for Nevil's Atlas graph programs
#            
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import string, os, sys
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT

import getparams as gp

# Config variables - written to file, reused if not reset
#
# -y start_ymd      20170220  Start time of dataset
# -h start_hhmm     0000
# -n n_bins         48        Nbr of bins per day
# -d n_days         7         Nbr of days in dataset
# -m msm_id         5005      Measurement ID to use
# -f full_graphs    True      Work on/with full graphs (id = IP address)
#                   False     Produce ASN-based graphs (id = ASN)
# -s write_stats    False     

# Python note:
# This is a module; importing it (essentially) creates a single class instance.
# set_pp() sets global (to module) variables/functions so that programs
#   using this module can see them.

dir = "."  # Base directory for RIPE graph files
agp = gp.AgParams(dir)  # Get -* parameters

mx_depth = asn_prefix = asn_suffix = ""  # Variables used in config functions

start_ymd, start_hhmm, msm_id, n_bins, n_days, \
    full_graphs, write_stats, rem_cpx = agp.param_values()
print("ymd=%s, hhmm=%s, n_bins=%d, n_days=%d, msm_id=%d, full=%s, statf=%s (rem_cpx=%d)" % (
    start_ymd, start_hhmm, n_bins, n_days, msm_id,
    full_graphs, write_stats, rem_cpx))

def set_ymd(ymd):  # Set ymd to use
    global start_ymd
    start_ymd = ymd

def set_asn_prefs():
    global asn_prefix, asn_suffix
    if full_graphs:
       asn_prefix = asn_suffix = ""
    else:  # ASN graphs
        asn_prefix = "asn-";  asn_suffix = "-asn"

def set_full_graphs(v):
    global full_graphs
    full_graphs = v
    set_asn_prefs()

def date_from_ymd(ymd, hhmm):
    return datetime(int(ymd[0:4]), int(ymd[4:6]),
        int(ymd[6:]),  int(hhmm[0:2]), int(hhmm[2:]))

#start_time = datetime(2017, 2, 20, 0, 0)  # Monday, 20 Feb 2017 (UTC)
start_time = date_from_ymd(start_ymd, start_hhmm)
#start_time = datetime(int(start_ymd[0:4]), int(start_ymd[4:6]),
#    int(start_ymd[6:]),  int(start_hhmm[0:2]), int(start_hhmm[2:]))

#ds_id = "%s-%02d" % (start_hhmm, n_bins*n_days)
ds_id = "%s-%d" % (start_hhmm, n_bins*n_days)

def dgs_stem(msm_id):
    return "%d-%s-%s" % (msm_id, start_ymd, ds_id)

def node_stem(msm_id):
    return "%s/nodes-%d-%s-%s" % (start_ymd, msm_id, start_ymd, ds_id)

###msm_nbrs = [5005, 5015, 5006, 5004, 5016, 5017]  # Decreasing nbr of edges
### was used in -v-timebins programs !!!!

mx_depth = 79  # mx_depth 54 found in graphs (as of 20191211)
draw_mx_depth = 0  # Allow any mx_depth for drawing graph images
draw_mn_trpkts = 27  # min_trpkts for drawing graph images

msm_dests = {5017: ("ronin.atlas"," 78.46.48.134"),
             5005: ("i.root","192.36.148.17"),
             5016: ("j.root","192.58.128.30"),
             5004: ("f.root","192.5.5.241"),
             5006: ("m.root","202.12.27.33"),
             5015: ("h.root","198.97.190.53"),

             5001: ("k.root","193.0.14.129"),
             5002: ("tt01.ripe.net",""),
             5008: ("labs.ripe.net",""),
             5009: ("a.root","198.41.0.4"),
             5010: ("b.root","199.9.14.201"),
             5011: ("c.root","192.33.4.12"),
             5012: ("d.root","199.7.91.13"),
             5016: ("j.root","192.58.128.30"),
             5020: ("carson","") }

# Instances data from www.root-servers.org
msm_instances_2012 = {5017: 1, 5005: 50, 5006: 8, 5015: 2, 5004: 58, 5016: 127,
                 5001:70, 5002:1, 5008:1, 5009:8, 5010:1, 5011:8,
                 5012:1, 5016:70, 5017:1, 5020:1}  # Site instances for PAM 2014

msm_instances_2017 = {5017: 1, 5005: 70, 5006: 9, 5015: 2, 5004:241, 5016: 164,
                 5001:72, 5002:1, 5008:1, 5009:28, 5010:3, 5011:10,
                 5012:153, 5016:164, 5017:1, 5020:1}  # 20 Feb Nov 2017 (NZDT)

msm_instances_2019 = {5017: 1, 5005: 70, 5006: 9, 5015: 4, 5004:252, 5016: 162,
                 5001:72, 5002:1, 5008:1, 5009:28, 5010:3, 5011:10,
                 5012:153, 5016:162, 5017:1, 5020:1}  # 28 Nov 2019 (NZDT)

def instances():
    if start_ymd[0:4] == "2012":
        return msm_instances_2012
    elif start_ymd[0:4] <= "2017":
        return msm_instances_2017
    elif start_ymd[0:4] <= "2019":
        return msm_instances_2019

# Config for:   make-probes-list abd get-tr-gz.py (python3)

ppb = 1000  #  Probes per block

def probes_fn():  # probes file has 10 records, each with 1000 probe nbrs
    return "%s/%s/probe-blocks.txt" % (dir, start_ymd)

gzm_dir = "%s/%s" % (dir, start_ymd)  # start_ymd from params.txt
#  traces stored as single-day .gz files for each msm_id
#  success files for each msm_id (written by build-graphs.py)

def gzm_txt_fn(st_ymd, msm_id):  # fn for gzm.txt file
    return "%s/%s/%s-%s-%s-%02d.txt" % (
        gzm_dir, st_ymd, msm_id, st_ymd, start_hhmm, n_bins)

def gzm_gz_fn(st_ymd, msm_id):  # fn for gzm.gz file
    return "%s/%s/%s-%s-%s-%02d.gz" % (
        gzm_dir, st_ymd, msm_id, st_ymd, start_hhmm, n_bins*n_days)


# build-graphs.py  config

def check_msm_ids(strs):
    msms = []
    for id in strs:
        if not id.isdigit(): 
            print("msm_id >%s< contains non-digit(s)" % id);  exit()
        if id[0:2] != "50":
            print("msm_id >%s< does not start with '50'" % id);  exit()
        msms.append(int(id))
    return msms  # Array of ints

def check_ymds(strs):
    for id in strs:
        if not id.isdigit(): 
            print("ymd >%s< contains non-digit(s)", id);  exit()
        if id[0:2] != "20":
            print("ymd >%s< does not start with '20'" % id);  exit()
        if id[4:6] < "01" or id[4:6] > "12" :
            print("ymd >%s< has an invalid month" % id);  exit()
        if id[6:8] < "01" or id[6:8] > "31" :
            print("ymd >%s< has an invalid day" % id);  exit()
    return strs  # Array of strings

def set_pp(pnames):
    #print("config: pnames >%s<" % pnames)
    gpp_result, pp_values = agp.get_plus_params(pnames)
#    print("CONFIG gpp_result = >%s<" % get_plus_params_result)
    return gpp_result, pp_values  # Result from set_pp

def msm_graphs_fn(msm_id):  # Depends on full_graphs !
    return "%s/%sgraphs-%d-%s-%s.txt" % (
        start_ymd, asn_prefix,  msm_id, start_ymd, ds_id)

def s_n_info_fn(msm_id):  # s_nodes info file name
        #  Written by make-combined-svgs.py
    graphs_fn = msm_graphs_fn(msm_id)
    gx = graphs_fn.find("graphs")
    return graphs_fn[0:gx+5] + "-snodes" + graphs_fn[gx+6:]

def stats_fn(msm_id):
    # H (header), R (roots), E (edges) and T (build-info) records
    # stats files are written by graph.build-graphs.py
    #   E records have depth, node <- s_node, trpkts_in 
    return "%s/stats-%d-%s-%s.txt" % (
        start_ymd, msm_id, start_ymd, ds_id)

#target_bn_lo = 0;  target_bn_hi = 1 # Bin 0 only
#target_bn_lo = 0;  target_bn_hi = 2 # Bin 1 and bin 2
#target_bn_lo = 0;  target_bn_hi = 4 # Bin 0-3 only
#target_bn_lo = 0;  target_bn_hi = 24  # First 12 hours only
target_bn_lo = 0;  target_bn_hi = n_days*n_bins  # All bins
    # Bins read from graphs file by make-combined-svgs.py

# asn-filter.py

def no_asn_nodes_fn(msm_id):
    return "%s/no-asn-nodes-%d.txt" % (start_ymd, msm_id)

def msm_asn_graphs_fn(msm_id):
    return "%s/asn-graphs-%d-%s-%s.txt" % (
        start_ymd, msm_id, start_ymd, ds_id)

# make-combined-svgs.py

draw_sub_dir = "full"

def set_sub_dir(sdir):
    global draw_sub_dir
    draw_sub_dir = sdir

def draw_dir(msm_id, mn_trpkts):
    return "%s/%d-%s%d-drawings/%s" % (
        start_ymd, msm_id, asn_prefix, mn_trpkts, draw_sub_dir)

def clip_spec_dir(msm_id, mn_trpkts):  # for make-clipped-svgs.py
    return "%s/%d-%s%d-drawings" % (
        start_ymd, msm_id, asn_prefix, mn_trpkts)

# make-js-slides.py

def dd_dgs_stem(msm_id, mn_trpkts):
    return "%s/%s" % (draw_dir(msm_id, mn_trpkts),
        dgs_stem(msm_id))  # For every timebin!

def slide_set_id(msm_id):
    return "%d-%s-%s" % (msm_id, start_ymd, ds_id)


def slides_fn(msm_id, mn_trpkts):
    as_s = ""
    if not full_graphs:
        as_s = "-asn"
    return "%s/%s%s-%s-%s-slides.html" % (
        draw_dir(msm_id, mn_trpkts), msm_id, as_s, start_ymd, ds_id)

# bgp-bulk-lookup.py

def bgp_fn(start_ymd):
    start_time = date_from_ymd(start_ymd, start_hhmm)
    bgp_time = start_time.strftime("%Y-%m-%dT%H:%M")  # arow's time format!
    duration = n_bins*n_days/2  # Hours
    return "%s/bgp-%s.%02d.gz" % (start_ymd, bgp_time, duration)

def nodes_fn(msm_id):
    return "%s/%snodes-%d-%s-%s.txt" % (
        start_ymd, asn_prefix,  msm_id, start_ymd, ds_id)
#    return "%s/nodes-%d-%s-%s.txt" % (
#        start_ymd, msm_id, start_ymd, ds_id)

def mntr_nodes_fn(msm_id, mntr):
    return "%s/%snodes-%d-%d-%s-%s.txt" % (
        start_ymd, asn_prefix,  msm_id, mntr, start_ymd, ds_id)
#    return "%s/nodes-%d-%s-%s.txt" % (
#        start_ymd, msm_id, start_ymd, ds_id)

def asns_fn(msm_id):
    return  "%s/asns-%s-%s-%s.txt" % (
        start_ymd, msm_id, start_ymd, ds_id)

def all_nodes_fn():
    return "%s/nodes-all-%s-%s.txt" % (
        start_ymd, start_ymd, ds_id)

def all_asns_fn():
    return "%s/asns-all-%s-%s.txt" % (
        start_ymd, start_ymd, ds_id)

def all_unknown_nodes_fn():
    return "%s/nodes-unknown-%s-%s.txt" % (
        start_ymd, start_ymd, ds_id)

def all_unknown_asns_fn():
    return "%s/asns-unknown-%s-%s.txt" % (
        start_ymd, start_ymd, ds_id)

def whois_fn(msm_id):
    return "%s/whois-%d-%s-%s.txt" % (
        start_ymd, msm_id, start_ymd, ds_id)

def all_whois_fn():
    return "%s/whois-all-%s-%s.txt" % (
        start_ymd, start_ymd, ds_id)

def run_bash_commands(cmds):  # Execute bash commands (separated by ;)
    p1 = Popen(cmds, stdout=PIPE, stderr=STDOUT, bufsize=1,
               universal_newlines=True, shell=True)
    output = ""
    while True:  # Watch p1, can print any output while it's running
        nextline = p1.stdout.readline()
        #sys.stdout.write(nextline);  sys.stdout.flush()
        if nextline == '' and p1.poll() is not None:
            break
        if nextline != '':
            output += nextline
    return output, p1.returncode


def find_msm_files(keyword, reqd_date):
    existing_files = [];  ntb_a = []
    #print("find_msm_files >>> %s (%s), %s (%s)" % ( keyword, type(keyword), reqd_date, type(reqd_date)))
    cmd = b"ls " + reqd_date.encode('utf-8') + b"/" + keyword.encode('utf-8') + b"-50*.txt" 
    output, err = run_bash_commands(cmd)
    lines = output[:-1].split('\n')  # Drop the trailing \n
    rq_ntb = str(n_bins)  # Only want files with c.n_bins timebins
    for ln in lines:
        line = ln.split('-')
        if len(line) != 0:
            nbtxt = line.pop()
            nb = nbtxt.split(".")[0]
            if len(ln) > 1:
                if nb != rq_ntb:
                    continue
            #print(line)
            existing_files.append(ln)
    if len(existing_files) == 0:
        print("*** No %s files found with %s timebins" % (keyword, rq_ntb))
        return [], str(n_bins)
    #print("existing_files = %s, rq_ntb = %s" % (existing_files, rq_ntb))
    return existing_files, rq_ntb

def find_gz_files(keyword):
    existing_files = []
    cmd = b"ls " + keyword.encode('utf-8')
    output, err = run_bash_commands(cmd)
    lines = output.decode('utf-8').split('\n')
    for ln in lines:
        line = ln.split('-')
        print(line)
        if len(line) > 1:
            existing_files.append(line[0])  # filename up to first '-'
    return existing_files
