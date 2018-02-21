# 1414, Tue  7 Nov 2017 (NZDT)
# 1250, Wed 10 Aug 2016 (NZST)
# 1539, Sun 12 Jun 2016 (NZST)
#
# build-graphs.py: read ripe traceroutes from atlas.gz file,
#                  build graphs from it, write to dgs file
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import traceroute as tr
import timebins
import read_atlas_gz
import graph
import dgs_ld

from pytz import timezone
from datetime import timedelta
import gzip, os, string, re

import config as c

#print("%d traces read" % len(traces))
#for n,t in enumerate(traces):
#    print("--- %2d ---" % n)
#    t.print_trace()

#def addr_list(resps):
#    addrs = []
#    for r in resps:
#        addrs.append(str(r.ip_addr))
#    return addrs

def add_to_dict(ip_pref, dict):
    if ip_pref in dict:
        dict[ip_pref] += len(r.rtts)
    else:
        dict[ip_pref] = len(r.rtts)  # New ip_pref
    
addresses4 = {};  addresses6 = {}

target_bn_lo = c.target_bn_lo;  target_bn_hi = c.target_bn_hi

#mx_traces = 10000
mx_traces = 0  # All traces
print("write_stats=%s, raw_stats=%s, stats_fn=%s" % (
    c.write_stats, c.raw_stats, c.stats_fn(c.msm_id)))

g_fn = c.msm_graphs_fn(c.msm_id)

if c.write_stats:
    sf = open(c.stats_fn(c.msm_id), "w")
else:
    sf = None

start_time = timezone('UTC').localize(c.start_time)  # Convert to UTC datetime
start_t = start_time
print("start_time = %s" % start_time.strftime('%X %x %Z'))

start_ymd = start_time.strftime("%Y%m%d")
succa = [];  bga = [];  n_traces  = 0  # Total number of traces!
start_dt = end_dt = None
for day in range(0,c.n_days):  #Read  RIPE Atlas for n_days days,
                        # make a complete list of BinGraphs in bga[]
    #if day != 0:  # Only do first day
    #    break
    start_t = start_time + timedelta(seconds=1800)*day*c.n_bins
    start_ymd = start_t.strftime("%Y%m%d")
    fn_gzm_gz = c.gzm_gz_fn(start_ymd, c.msm_id)
    tb_n = day*c.n_bins  # Starting bin nbr for this day's file
    print("$$$ starting day %d, fn_gzm_txt %s, from bin %d" % (
        day, fn_gzm_gz, tb_n))
    
    f_tb_n = 0  # tb within this file
    print("Starting file for day %d (%s)" % (day, start_ymd))
    with gzip.open(fn_gzm_gz, 'rb') as zif:  # Step through bins in this file
        tb = None
        block_nbr = b_traces = b_empty_traces = b_too_short_traces = 0
        for b_line in zif:
            line = b_line.decode('ascii')
            #print("*** %s" % line)
            if line[0] == '#':  # Comment
                ls = line.rstrip()
                if re.match(r'^#Input header', ls):  # Get start and end times
                    lsa = ls.split()
                    if not start_dt:
                        start_dt = lsa[3]
                    edt = lsa[5];  end_dt = edt[:-1]
                    tb = timebins.TimeBins(lsa[3], end_dt)
                    print("tb = %s, end_dt = %s" % (tb, end_dt))
                continue

            if (tb_n >= target_bn_lo) and (tb_n <= target_bn_hi):
                #  timebin tb is in range (of whole dataset)
                nt, dest, empty_traces, too_short_traces = \
                    read_atlas_gz.read_tr_file(tb, f_tb_n, line, mx_traces)
                    # Read the Trees into tb.bins[f_tb_n]
                b_empty_traces += empty_traces
                b_too_short_traces += too_short_traces
                b_traces += nt

            block_nbr += 1
            if block_nbr < 10:  # 10 blocks of probes for each timebin
                continue
            else:  # End of this bin
                print("Day %d, timebin %d, %d Traces read" % (
                    day, f_tb_n, b_traces))
                print("  ==> empty_traces=%d, too_short_traces=%d" % (
                    b_empty_traces, b_too_short_traces))
                t_traces, t_addrs, t_hops, t_succ, t_addrs_deleted, \
                    t_hops_deleted = read_atlas_gz.cleanup_bin(
                        tb, f_tb_n, c.mx_depth)
                    # Remove rfc1918 and duplicate-responder address
                print("===  tb=%s, t_traces=%s" % (tb, t_traces))

                g = graph.build_graph(f_tb_n, tb.bins[f_tb_n], dest, \
                    t_traces, t_addrs, t_hops, t_succ, t_addrs_deleted, \
                    t_hops_deleted, c.msm_id, sf)

                bga.append(g)
                succa.append("%2d: %.2f (%d of %d)" % (
                    tb_n, t_succ*100.0/t_traces, t_succ, t_traces))
                tb.bins[f_tb_n] = None  # Finished with bin f_tb_n
                n_traces += b_traces
                b_traces = block_nbr = b_empty_traces = b_too_short_traces =0
                tb_n += 1;  f_tb_n += 1

                #break  # Only do one bin  (break inner loop)
                #if f_tb_n > 1:  # Only do 2 timebins (for each day)
                #    break
        else:
            continue  # Executed if the bline in zif executed normally
        break
    
if c.write_stats or c.raw_stats:
    sf.close()
    c.reset_stats()

df = open(g_fn, "w")
print("??? end_dt = %s" % end_dt)
dg = dgs_ld.DestGraphs(1, c.msm_id, dest, n_traces, \
    start_dt, end_dt,  bga)  # Version 1 = Nodes graph
dg.dump(df)
df.close()

sf = open(c.success_fn(c.msm_id), "w")
sf.write("msm_id %d success stats:\n" % c.msm_id)
for sline in succa:
    sf.write(sline+"\n")
sf.close()

print("msm_id = %d, mx_depth = %d, prune_s = %s, graphs_fn = %s" % (
    c.msm_id, c.mx_depth, c.prune_s, g_fn))
