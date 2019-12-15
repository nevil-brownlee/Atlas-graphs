# 1812, Sun  4 Mar 2018 (NZDT)
#
# config.py: configuration info for Nevil's Atlas graph programs
#            
# Copyright 2018, Nevil Brownlee,  U Auckland | RIPE NCC

import string, os
from datetime import datetime
import subprocess

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
# set_pp(stats_file, msm_id) picks up msm_id's prune parameters, then
# sets global (to module) variables/functions so that programs using this 
# module can see them.

dir = "."  # Base directory for RIPE graph files
agp = gp.AgParams(dir)  # Get -* parameters

start_ymd, start_hhmm, msm_id, n_bins, n_days, \
    full_graphs, write_stats, rem_cpx = agp.param_values()
print("ymd=%s, hhmm=%s, n_bins=%d, n_days=%d, msm_id=%d, full=%s, statf=%s (rem_cpx=%d)" % (
    start_ymd, start_hhmm, n_bins, n_days, msm_id,
    full_graphs, write_stats, rem_cpx))

#def reset_stats():
#    agp.raw_stats = agp.write_stats = False
#    agp.save_params()  

#start_time = datetime(2017, 2, 20, 0, 0)  # Monday, 20 Feb 2017 (UTC)
start_time = datetime(int(start_ymd[0:4]), int(start_ymd[4:6]),
    int(start_ymd[6:]),  int(start_hhmm[0:2]), int(start_hhmm[2:]))

ft_range = "%s-%02d" % (start_hhmm, n_bins*n_days)
ds_stem = "%d-%s-%s" % (msm_id, start_ymd, ft_range)

msm_nbrs = [5005, 5015, 5006, 5004, 5016, 5017]  # Decreasing nbr of edges

msm_dests = {5017: ("ronin.atlas",15,20),  # name, prune max, mx_depth
                                           # pp[2] of 80 is about 0.3%
             # Note: in 20191211 data, a few IP addrs reached mx_depth (15)!
             5005: ("i.root",15,20),   #  70  number of sites. Nov 2019
             5016: ("j.root",15,20),   # 104
             5006: ("m.root",15,20),   #   9
             5015: ("h.root",15,20),   #   2
             5004: ("f.root",15,20),   # 241

             5001: ("k.root",15,20),   #  70
             5002: ("tt01.ripe.net",15,20),
             5008: ("labs.ripe.net",15,20),
             5009: ("a.root",15,20),   #  28
             5010: ("b.root",15,20),   #   3
             5011: ("c.root",15,20),   #  10
             5012: ("d.root",15,20),   # 153
             5016: ("j.root",15,20),   # 164
             5017: ("ronin.atlas",15,20),
             5020: ("carson",15,20) }

msm_instances_2012 = {5017: 1, 5005: 50, 5006: 8, 5015: 2, 5004: 58, 5016: 127,
                 5001:70, 5002:1, 5008:1, 5009:8, 5010:1, 5011:8,
                 5012:1, 5016:70, 5017:1, 5020:1}  # Site counts for PAM 2014

msm_instances_2017 = {5017: 1, 5005: 70, 5006: 9, 5015: 2, 5004:241, 5016: 164,
                 5001:17, 5002:1, 5008:1, 5009:28, 5010:3, 5011:10,
                 5012:153, 5016:164, 5017:1, 5020:1}  # 28 Nov 2019 (NZDT)

def msm_pp(msm):  # Prune parameters
    pp = msm_dests[msm]
    p_pkts = isinstance(pp[2], int)  # True if pp[2] is an int
    if p_pkts:
        prune_s = "%d" % pp[2]
    else:
        prune_s = "%.2f" % pp[2]
    return (pp[0],  # dname
            pp[1],  # mx_depth
            pp[2],  # prune_pc (float) or prune_tr_pkts (int)
            p_pkts, # True if it's a max_tr_pkts
            prune_s)  # p_pkts as string

# Config for:   make-probes-list abd get-tr-gz.py (python3)

ppb = 1000  #  Probes per block

def probes_fn():
    return "%s/%s/probe-blocks.txt" % (dir, start_ymd)

gzm_dir = "%s/%s" % (dir, start_ymd)  # start_ymd from params.txt
#  traces stored as single-day .gz files for each msm_id
#  success files for each msm_id (written by build-graphs.py)

def gzm_txt_fn(st_ymd, msm_id):  # fn for gzm.txt file
    return "%s/%s/%s-%s-%s-%02d.txt" % (
        gzm_dir, st_ymd, msm_id, st_ymd, start_hhmm, n_bins)

def gzm_gz_fn(st_ymd, msm_id):  # fn for gzm.gz file
    return "%s/%s/%s-%s-%s-%02d.gz" % (
        gzm_dir, st_ymd, msm_id, st_ymd, start_hhmm, n_bins)


# build-graphs.py  config

stats_mx_depth = 15;  stats_min_tr_pkts = 10  # Prune parameters

def set_pp(stats_file, msm_id):  # True to use stats file instead of graphs file
    global dname, mx_depth, prune_pc, p_pkts, prune_s, \
        dgs_info, dgs_stem, node_fn, graphs_fn, asn_prefix, asn_suffix
        # Globals needed by functions (within config module)
    dname, mx_depth, prune_pc, p_pkts, prune_s = msm_pp(msm_id)
    if stats_file:  # For graph-stats.py analysis
        mx_depth = stats_mx_depth
        #prune_p = stats_min_tr_pkts;  p_pkts = True
        prune_p = msm_dests[msm_id][2];  p_pkts = True  # 1 Dec 2019 !!
        prune_s = "%s" % prune_p
    dgs_info = "%d-%s" % (mx_depth, prune_s)

    node_stem = "%s/nodes-%d-%s-%s-%d-%s" % (
    start_ymd, msm_id, start_ymd, ft_range, mx_depth, prune_s)
    # Must call set_pp to set mx_depth <<<<<<<<<<<<<<<<<

    dgs_stem = "%d-%s-%s-%s" % (msm_id, start_ymd, ft_range, dgs_info)
    if full_graphs:
        graphs_fn = msm_graphs_fn(msm_id)  # graphs file (from traces file)
        node_fn = node_stem + ".txt"
        asn_prefix = asn_suffix = ""
    else:  # ASN graphs
        graphs_fn = msm_asn_graphs_fn(msm_id)  # asngraphs file (asn-filter.py)
        dgs_stem += "-asn"
        node_fn = node_stem + "-asn.txt"
        asn_prefix = "asn-";  asn_suffix = "-asn"

def msm_graphs_fn(msm_id):  # Depends on full_graphs !
    asn_s = "asn"
    if full_graphs:
        asn_s = ''
    return "%s/%sgraphs-%d-%s-%s-%d-%s.txt" % (start_ymd, asn_s,
        msm_id, start_ymd, ft_range, mx_depth, prune_s)

def stats_fn(msm_id):
##    print("mx_depth=%d, prune_pc=%.2f <<< stats_fn" % (mx_depth, prune_pc))
    print("config.py: msm_id = %s" % msm_id)
    return "%s/stats-%d-%s-%s-%d-%s.txt" % (start_ymd,
        msm_id, start_ymd, ft_range, mx_depth, prune_s)

def success_fn(msm_id):
    return "%s/success-stats-%d-%s-%s-%d-%s.txt" % (start_ymd,
        msm_id, start_ymd, ft_range, mx_depth, prune_s)

#target_bn_lo = 0;  target_bn_hi = 1 # Bin 0 only
#target_bn_lo = 0;  target_bn_hi = 2 # Bin 1 and bin 2
#target_bn_lo = 0;  target_bn_hi = 4 # Bin 0-3 only
#target_bn_lo = 0;  target_bn_hi = 24  # First 12 hours only

target_bn_lo = 0;  target_bn_hi = n_days*n_bins  # All bins
#  Target bin range used by build_graphs.py and make-combined-svgs.py

ft_range = "%s-%02d" % (start_hhmm, n_bins*n_days)

def graph_gather_fn(msm_id):
    start_ymd = start_time.strftime("%Y%m%d")
    start_hhmm = start_time.strftime("%H%M")
    return "%s/graphs-%d-%s-%s-%d-%s.txt" % (
        start_ymd, msm_id, start_ymd, ft_range, mx_depth, prune_s)

# graph-stats.py

# asn-filter.py

def no_asn_nodes_fn(msm_id):
    return "%s/no-asn-nodes-%d.txt" % (start_ymd, msm_id)

def msm_asn_graphs_fn(msm_id):
    return "%s/asngraphs-%d-%s-%s-%d-%s.txt" % (
        start_ymd, msm_id, start_ymd, ft_range, mx_depth, prune_s)

# make-combined-svgs.py

def draw_dir(msm_id):
    return "%s/%s-%sdrawings" % (start_ymd, msm_id, asn_prefix)

# make-js-slides.py

def dd_dgs_stem():
    return "%s/%s" % (draw_dir(msm_id), dgs_stem)  # For every timebin!

def slide_set_id():
    return "%d-%s-%s-%s%s" % (
        msm_id, start_ymd, ft_range, dgs_info, asn_suffix)


def slides_fn():
    as_s = ""
    if not full_graphs:
        as_s = "-asn"
    return "%s/%s%s-%s-slides.html" % (draw_dir(msm_id), msm_id, as_s, dgs_info)

# bgp-bulk-lookup.py

bgp_time = start_time.strftime("%Y-%m-%dT%H:%M")  # arow's time format!
duration = n_bins*n_days/2  # Hours

bgp_fn = "%s/bgp-%s.%02d.gz" % (start_ymd, bgp_time, duration)

def nodes_fn(msm_id):
    return "%s/nodes-%d-%s-%s-%d-%s.txt" % (
        start_ymd, msm_id, start_ymd, ft_range, mx_depth, prune_s)

def asn_fn(msm_id):
    return  "%s/asns-%d-%s-%s-%d-%s.txt" % (
        start_ymd, msm_id, start_ymd, ft_range, mx_depth, prune_s)

def asn_dests_fn(msm_id):
    dname, mx_depth, prune_pc = msm_dests[msm_id]
    return "%s/asns-%d-%s-%s-%d-%s.txt" % (
        start_ymd, msm_id, start_ymd, ft_range, mx_depth, prune_s)

# asn-stats.py

def whois_fn(msm_id):
    return "%s/whois-%d-%s-%s-%d-%s.txt" % (
        start_ymd, msm_id, start_ymd, ft_range, mx_depth, prune_s)


def run_bash_commands(cmds):  # Execute bash commands, separated by \0a
    p1 = subprocess.Popen(['bash'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    output, err = p1.communicate(cmds)  #, timeout=5)
    #p1.wait()  #  Wait here for command to complete
    #if err:
    #    print("cmds %s;  stderr %s" % (cmds, err))
    return output, err

#msms_2012 = [b"5001",b"5002",b"5004",b"5005",b"5006",b"5008",b"5009",
#             b"5010",b"5011",b"5012",b"5015",b"5016",b"5017",b"5020"]

def find_msm_files(keyword, reqd_date):
    existing_files = [];  ntb_a = []
    cmd = b"ls " + reqd_date.encode('utf-8') + b"/" + keyword.encode('utf-8') + b"-50*.txt" 
    print("--cmd = %s" % cmd)
    output, err = run_bash_commands(cmd)
    lines = output.decode('utf-8').split('\n')
    rq_ntb = str(n_bins)
    for ln in lines:
        line = ln.split('-')
        if len(line) > 1:
            if line[4] != rq_ntb:
                continue
            print(line)
            existing_files.append(line[1])
            ntb_a.append(line[4])
    if len(ntb_a) == 0:
        print("*** No %s files found" % keyword)
        return [], str(n_bins)
    return existing_files, rq_ntb

def find_gz_files(keyword):
    existing_files = []
    cmd = b"ls " + keyword.encode('utf-8')
    print("--cmd = %s" % cmd)
    output, err = run_bash_commands(cmd)
    lines = output.decode('utf-8').split('\n')
    for ln in lines:
        line = ln.split('-')
        print(line)
        if len(line) > 1:
            existing_files.append(line[0])  # filename up to first '-'
    return existing_files
