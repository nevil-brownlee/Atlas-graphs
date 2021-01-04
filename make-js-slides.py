# 1757, Fri  6 Nov 2020 (NZDT)
# 1950, Mon 13 Nov 2017 (SGT)
# 1700, Sun 14 Aug 2016 (NZST)
#
# make-js-slides.py:  Makes html slide show for atlas graphs
#                       args:    msm_id  full-graphs
#                       default: use values from config.py
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import sys, glob, re

import timebins
from datetime import timedelta

import config as c

reqd_ymds = [];  reqd_msms = []
pp_names = "m! y! a mxd= mntr= sd!"  # indeces 0 to 5
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default paremeters for drawing
mn_trpkts = c.draw_mn_trpkts
asn_graphs = not c.full_graphs
subdirs = []

for n,ix in enumerate(pp_ix):
    if ix == 0:    # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 2:  # a sets full_graphs F to use ASN graphs
        asn_graphs = True;  c.set_full_graphs(False)
    elif ix == 3:  # mxd  specify max depth
        mx_depth = pp_values[n]
    elif ix == 4:  # mntr  specify min trpkts
        mn_trpkts = pp_values[n]
    elif ix == 5:  # sd    specify sub_dir for drawing_dir
        subdirs = pp_values[n]
    else:
        exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
elif len(reqd_ymds) > 1:
    print("More than one ymd specified!");  exit()
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
if len(subdirs) != 1:
    print("Must specify a single subdir (sd)")
    exit()

print("asn_graphs = %s, reqd_ymds = %s, reqd_msms = %s" % (
    asn_graphs, reqd_ymds, reqd_msms))

c.set_ymd(reqd_ymds[0])
#print("subdirs >%s<" % subdirs)
c.set_sub_dir(subdirs[0])

start_dt = c.start_time.strftime("%Y-%m-%dT%H")
end_time = c.start_time + timedelta(c.n_days)
end_dt = end_time.strftime("%Y-%m-%dT%H")

tb = timebins.TimeBins(start_dt, end_dt)
n_bins = c.n_bins*c.n_days
#bn_lo = 0;  bn_hi = n_bins-1
    #>>> for bn in range(22,28):  # For 5017 test >>>#
    #bn_lo = 22;  bn_hi = 27


for msm_id in reqd_msms:
    full_graphs = c.full_graphs
    print("msm_id = %d, full_graphs = %s" % (msm_id, full_graphs))
    draw_dir = c.draw_dir(msm_id, mn_trpkts)

    set_id = c.slide_set_id(msm_id)
    cap_stem = set_id + "-"
    print("cap_stem = <%s>" % cap_stem)
    dd_dgs_stem = c.dd_dgs_stem(msm_id, mn_trpkts)
    print("dd_dgs_stem = %s" % dd_dgs_stem)
    dgs_stem = c.dgs_stem(msm_id)
    print("dgs_stem = %s" % dgs_stem)

    bn_lo = 9999;  bn_hi = -1
    bin_list =  glob.glob(dd_dgs_stem + "*.svg")
    print("bin_list = %s" % bin_list)
    for fn in bin_list:
        bn = int(fn[-7:-4])
        print("%s  bn=%d" % (fn, bn))
        if bn < bn_lo:
            bn_lo = bn
        if bn > bn_hi:
            bn_hi = bn
    print("   bin_hi %d, bn_lo %d" % (bn_lo, bn_hi))

    r = re.search(r'-(\d+)\.svg', bin_list[0])
    if r:
        dlen = len(r.group(1))
    print("dlen = %d" % dlen)

    slides_fn = c.slides_fn(msm_id, mn_trpkts)
    print("slides_fn = %s" % slides_fn)

    sf = open(slides_fn, "w")


    def make_captions(sf):
        for bn in range(bn_lo, bn_hi+1):
            bt = tb.bin_py_time(bn).strftime("%Y-%m-%dT%H:%M %Z")
            sf.write("    <div class=\"text\">%s, Bin %3d, %s</div>\n" % (
                cap_stem[0:], bn, bt))

    js_graph_fn = "js-graphs.html"
    jgf = open(js_graph_fn, "r")

    state = 0
    for line in jgf:
        sf.write(line)
        if state == 0:  # Copy head and css
            r = re.search(r'class="text"', line)
            if r:
               make_captions(sf)
               state = 1
        elif state == 1:
            r = re.search(r'var cap_stem', line)
            if r:
               sf.write("var cap_stem = \"%s\";\n" % cap_stem)  # Add trailing -
               sf.write("var dlen = %d;\n" % dlen)
                  # width of bin nbrs in svg filenames
               sf.write("var bn_offset = %d\n" % bn_lo)  # = bn 0
               state = 2

    sf.close()
    jgf.close()
