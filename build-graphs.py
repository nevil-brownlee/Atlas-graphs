# 1630, Wed 19 Feb 2020 (NZDT)
# 1414, Tue  7 Nov 2017 (NZDT)
# 1250, Wed 10 Aug 2016 (NZST)
# 1539, Sun 12 Jun 2016 (NZST)
#
# build-graphs.py: read ripe traceroutes from atlas.gz file,
#     build graphs from it, write to DestGraphs (dgs) file.
#     Write stats file if -s True.
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import traceroute as tr
import timebins
import read_atlas_gz, read_yaml_gz
import graph
import dgs_ld

from pytz import timezone
from datetime import timedelta
import gzip, os, string, re, sys
from timeit import default_timer as timer

import config as c

reqd_ymds = [];  reqd_msms = []
pp_names = "m! y!"  # indeces 0 to 1
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
for n,ix in enumerate(pp_ix):
    if ix == 0:    # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
elif len(reqd_ymds) > 1:
    print("More than one ymd specified!");  exit()
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
    print("reqd_ymds %s, reqd_msms %s" % (reqd_ymds, reqd_msms))

def add_to_dict(ip_pref, dict):
    if ip_pref in dict:
        dict[ip_pref] += len(r.rtts)
    else:
        dict[ip_pref] = len(r.rtts)  # New ip_pref
    
def write_nodes_file(msm_id, bga):
    def add_to_nodes(n, nodes):
        in_count = 0
        for sk in n.s_nodes:  # Nodes don't have in_count (PrunedNodes do)
            in_count += n.s_nodes[sk]
        if n.prefix not in nodes:
            nodes[n.prefix] = n;  nodes[n.prefix].in_count = in_count
        else:
            old_in_count = nodes[n.prefix].in_count
            if in_count > old_in_count:  # Find max in_count over all bins
                nodes[n.prefix].in_count = in_count

    def accumulate_graph(bg, nodes):  # Build wg from array of BinGraphs
        for pp in bg.pops:  # pp is the pop's prefix
            n = bg.pops[pp]  # n is a Node
            add_to_nodes(n, nodes)
            # Actual node's s_nodes{} will differ from bg to bg
            for sk in n.s_nodes:
                sn = bg.pops.get(sk)
                if sn:
                     add_to_nodes(sn, nodes)

    def write_nodes_file(msm_id, nodes):
        nfn = c.nodes_fn(msm_id)
        print("nodes_fn = %s" % nfn)
        nodesf = open(nfn, "w")
        mx_in_count = mx_depth = 0
        for np in nodes:
            n = nodes[np]
            if n.in_count > mx_in_count:
                mx_in_count = n.in_count
            if n.depth > mx_depth:
                mx_depth = n.depth
            #in_count = 0
            #for snk in n.s_nodes:
            #    in_count += n.s_nodes[snk]
            #print("prefix %s, n %s (%s)" % (np, n, type(n)))
            nodesf.write("%s %d %d\n" % (n.prefix, n.in_count, n.depth))
        nodesf.close()
        print(">>> mx_in_count %d, mx_depth %d" % (mx_in_count, mx_depth))

    nodes = {}
    for n,bg in enumerate(bga):
        print("--- bn=%d" % n)
        accumulate_graph(bg, nodes)
    write_nodes_file(msm_id, nodes)

target_bn_lo = c.target_bn_lo;  target_bn_hi = c.target_bn_hi

#mx_traces = 10000
mx_traces = 0  # All traces

start_time = timezone('UTC').localize(c.start_time)  # Convert to UTC datetime
start_t = start_time
print("start_time = %s" % start_time.strftime('%X %x %Z'))

start_ymd = start_time.strftime("%Y%m%d")
bga = [];  n_traces  = 0  # Total number of traces!
start_dt = end_dt = None

def read_json_file(zif, start_dt, tb_n):
        # tb_n = starting bin nbr within whole dataset (i.e. set of days)
    n_bins = 0;  tot_bin_times = 0.0
    f_tb_n = 0  # starting bin nbr within output file
    n_traces = 0
    ln = -1
    tb = None  # Keep results of last read after end of zif!
    ta = nt = bin_nbr = dest = empty_traces = too_short_traces = 0
    while True:  # Step through bins in this file
        block_nbr = b_traces = b_empty_traces = b_too_short_traces = 0
        for b_line in zif:
            j_line = b_line.decode('ascii')
            ln += 1
            if j_line[0] == '#':  # Comment
                ls = j_line.rstrip()
                if re.match(r'^#Input header', ls):  # Get start and end times
                    lsa = ls.split()
                    ##print("lsa = >%s<" % lsa)
                    if not start_dt:
                        start_dt = lsa[3]
                    end_dt = lsa[5].rstrip(",");  zif_msm = lsa[:-1]
                    print("json file for %s: %s to %s" % (
                        zif_msm, start_dt, end_dt))
                    tb = timebins.TimeBins(lsa[3], end_dt)
                    print("tb = >%s<" % tb)
                continue

            ta, nt, bin_nbr, dest, empty_traces, too_short_traces = \
                read_atlas_gz.read_tr_file(tb, f_tb_n, j_line, mx_traces)
                # Read the Trees into tb.bins[f_tb_n]
                #  (timebin tb_n is in range of whole dataset)

            if bin_nbr == f_tb_n:
                tb.bins[bin_nbr].extend(ta)
                b_empty_traces += empty_traces
                b_too_short_traces += too_short_traces
                b_traces += nt
                continue
            else:  # Starting new bin, finish off bin f_tb_n
                if bin_nbr >= len(tb.bins):  # Ignore bins beyond tb.bins
                    print("\nDay %d, timebin %d IGNORED, %d Traces read" % (
                        day, bin_nbr, b_traces))
                    ##print("--> >%s<" % b_line)
                else:
                    print("\nDay %d, timebin %d, %d Traces read" % (
                        day, bin_nbr, b_traces))
                    print("  ==> empty_traces=%d, too_short_traces=%d" % (
                        b_empty_traces, b_too_short_traces))
                    t_traces, t_addrs, t_hops, t_succ, t_addrs_deleted, \
                        t_hops_deleted = read_atlas_gz.cleanup_bin(\
                            tb, f_tb_n)
                        # Remove rfc1918 and duplicate-responder address
                    print("===  tb=%s, t_traces=%s\n" % (tb, t_traces))

                    start_t = timer()
                    g = graph.build_graph(f_tb_n, tb.bins[f_tb_n], dest, \
                        t_traces, t_addrs, t_hops, t_succ, t_addrs_deleted, \
                        t_hops_deleted, c.msm_id, sf)
                    end_t = timer()
                    n_bins += 1;  tot_bin_times += (end_t-start_t)
                    bga.append(g)  # bga is global!

                    #??? tb.bins[f_tb_n] = None  # Finished with bin f_tb_n
                    # A trace early in bin may fall into the previous one!
                    n_traces += b_traces

                    tb.bins[bin_nbr] = ta
                    b_empty_traces = empty_traces
                    b_too_short_traces = too_short_traces
                    b_traces = nt
                    f_tb_n += 1

                #print("After gz.read_tr:  bin_nbr %d != f_tb_n %d" % (
                #    bin_nbr, f_tb_n))
                if bin_nbr != f_tb_n:
                    print("?? bin_nbr %d, f_tb_n %d" % (bin_nbr, f_tb_n))

            #break  # Testing: Only do one bin  (break inner loop)
            #if f_tb_n == 1:  # Only do 2 timebins (for each day)
            #    break
        print("Reached EOF on zip file, bin_nbr %d" % bin_nbr)
        tb.bins[bin_nbr].extend(ta)  # Save traces for last bin
        b_empty_traces += empty_traces
        b_too_short_traces += too_short_traces
        b_traces += nt
        bga.append(g)

        print("%d graphs produced, %.3f s per bin <<<" % (
            n_bins, tot_bin_times/n_bins))
        break  # EOF; Break the 'while True' loop

    return n_traces, dest, start_dt, end_dt, empty_traces, too_short_traces
        # We've built the graphs in bga[]

for msm_id in reqd_msms:
    for day in range(0,c.n_days):  #Read  RIPE Atlas for n_days days,
                            # make a complete list of BinGraphs in bga[]
        g_fn = c.msm_graphs_fn(msm_id)
        print("write graphs file %s,\n  and stats file %s" % (
            c.stats_fn(msm_id), g_fn))
        sf = open(c.stats_fn(msm_id), "w")
        
        #if day != 0:  # Only do first day
        #    break
        start_t = start_time + timedelta(seconds=1800)*day*c.n_bins
        start_ymd = start_t.strftime("%Y%m%d")
        fn_gzm_gz = c.gzm_gz_fn(start_ymd, msm_id)
        print("Read gzm file %s" % fn_gzm_gz)
        tb_n = day*c.n_bins  # Starting bin nbr in this day's file
        print("$$$ starting day %d, fn_gzm_txt %s, from bin %d" % (
            day, fn_gzm_gz, tb_n))

        print("Starting file for day %d (%s)" % (day, start_ymd))

        zif = gzip.open(fn_gzm_gz, 'rb')
        if not zif:
            print("Couldn't open zip file %s <<<" % fn_gzm_gz)
            exit()

        if c.start_ymd > '20130000':
            # Read graphs into bga[]
            nt, dest, start_dt, end_dt, empty_traces, too_short_traces = \
                read_json_file(zif, start_dt, tb_n)
            print("Returned from read_json_file(), day=%d" % day)
        else:
            yr = read_yaml_gz.Yaml(zif)  # Set up yaml reader
            bga, dest, tb, nt = yr.read_tr_file(mx_traces, sf)
            print("tb = %s, nt = %d traces" % (tb, nt))
            start_dt = tb.start_dt;  end_dt = tb.end_dt
            print("start_dt %s, end_dt %s (%d timebins)" % (
                start_dt, end_dt, len(bga)))

    if c.write_stats:
        sf.close()

    df = open(g_fn, "w")  # Write graphs- file
    print("??? end_dt = %s" % end_dt)
    dg = dgs_ld.DestGraphs(1, msm_id, dest, n_traces, \
        start_dt, end_dt,  bga)  # Version 1 = Nodes graph
    dg.dump(df)
    df.close()

    write_nodes_file(msm_id, bga)

    print("msm_id = %d, graphs_fn = %s" % (
        c.msm_id, g_fn))

    dg = None;  bga = []  # Deallocate memory for these between msm_ids!
