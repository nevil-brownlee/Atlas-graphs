# 1633, Sat 22 Feb 2020 (NZDT)
# 1226, Thu  4 Jul 2019 (NZST)
#
# graphs-split-days.py  Splits -96 graphs files into 2x -48 graphs files
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import sys, datetime, string, os, glob

import config as c

pp_names = "m! y!"  # No + parameters
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
for n,ix in enumerate(pp_ix):
    if ix == 0:    # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) ymds
        reqd_ymds = c.check_ymds(pp_values[n])
    else:
        exit()
c.set_ymd(reqd_ymds[0])

print("pp_names >%s<, start_ymd %s, msm_id %d, n_bins %d" % (
    pp_names, c.start_ymd, c.msm_id, c.n_bins))

def find_file(keyword, ymd, msm_id):
    filenames, rq_ntb = c.find_msm_files("graphs", ymd)
    if len(filenames) == 0:
        print("No %s %d file found !!!" % (ymd, msm_id))
        exit()
    for fn in filenames:
        if fn.find(str(msm_id)) != -1:
            return fn
    return None

def split_graphs(in_graphs_fn):
    print("Reading from %s" % in_graphs_fn)
    ymd_dir, rest = in_graphs_fn.split('/')
    ftype, msm, ymd, hm, last = rest.split('-')
    n_bins, rest = last.split('.')
    if not os.path.exists(ymd):
        os.mkdir(ymd)
    old_nbins = int(n_bins)
    if old_nbins%48 != 0:
        print("Old nbins (%d) not a multiple of 48 <<<<<")
        exit()
    in_yymmdd = datetime.datetime.strptime(ymd, "%Y%m%d")
    day2_yymmdd = in_yymmdd+datetime.timedelta(seconds=24*3600)
    d2_ymd = day2_yymmdd.strftime("%Y%m%d")
    day3_yymmdd = in_yymmdd+datetime.timedelta(seconds=48*3600)
    #print("day2_yymmdd %s, day3_yymmdd %s" % (day2_yymmdd, day3_yymmdd))
    #print("+ + + + + + +") ; exit()
    if not os.path.exists(d2_ymd):
        os.mkdir(d2_ymd)
    d2_start_dt = day2_yymmdd.strftime("%Y-%m-%dT00")
    d2_end_dt = day3_yymmdd.strftime("%Y-%m-%dT00")

    new_fn1 = "%s/%s-%s-%s-%s-%d.txt" % (ymd_dir,
        ftype, msm, ymd, hm, 48)
    new_fn2 = "%s/%s-%s-%s-%s-%d.txt" % (d2_ymd,
        ftype, msm, d2_ymd, hm, 48)

    inf = open(in_graphs_fn, 'r')
    dg_hdr = inf.readline().rstrip()
    dg, h_msm, dest, n_traces, start_dt, end_dt  = dg_hdr.split()
    new_hdr1 = "DestGraphs %s %s %s  %s %s\n" % (
        h_msm, dest, n_traces, start_dt, d2_start_dt)
    #print(">>> new_hdr1 = %s" % new_hdr1)
    new_hdr2 = "DestGraphs %s %s %s  %s %s\n" % (
        h_msm, dest, n_traces,  d2_start_dt, d2_end_dt)
    #print(">>> new_hdr2 = %s" % new_hdr2)
    outf = open(new_fn1, "w")
    outf.write(new_hdr1)
    bn_offset = 0
    ln = 0
    print("inf state = %s" % inf)
    for line in inf:
        ln += 1
        #print("ln = %d, line = %s" % (ln, line))
        if line.find("BinGraph ") == 0:
            ba = line.rsplit(' ', 1)
            bn = int(ba[1][:-1])
            line = ba[0] + (" %d\n" % (bn-bn_offset))
            if bn == 48:  # Start of second day
                bn_offset = 48
                outf.close()
                new_f2 = open(new_fn2, "w")
                outf = new_f2
                outf.write(new_hdr2)
                line = ba[0] + (" %d\n" % (bn-bn_offset))
        outf.write(line)
    outf.close()

#gg = glob.glob("%s/graphs-*-%d*.txt" % (c.start_ymd, c.n_bins))
#print("gg = %s" % gg)
#for fn in gg:
for msm_id in reqd_msms:
    for ymd in reqd_ymds:
        fn = find_file("graphs", ymd, msm_id)
        print("\n--- fn = %s" % fn)
        split_graphs(fn)
