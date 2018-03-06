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
c.set_pp(False, c.msm_id)  # Set prune parameters

start_dt = c.start_time.strftime("%Y-%m-%dT%H")
end_time = c.start_time + timedelta(c.n_days)
end_dt = end_time.strftime("%Y-%m-%dT%H")

tb = timebins.TimeBins(start_dt, end_dt)
n_bins = c.n_bins*c.n_days
bn_lo = 0;  bn_hi = n_bins-1

msm_id = c.msm_id;  full_graphs = c.full_graphs
print("msm_id = %d, full_graphs = %s" % (msm_id, full_graphs))
draw_dir = c.draw_dir(msm_id)

set_id = c.slide_set_id()
cap_stem = set_id
dgs_stem = c.dd_dgs_stem()

bin_list = glob.glob(dgs_stem + "-*.svg")
r = re.search(r'-(\d+)\.svg', bin_list[0])
if r:
    dlen = len(r.group(1))
print("dlen = %d" % dlen)

slides_fn = c.slides_fn()
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
           sf.write("var cap_stem = \"%s-\";\n" % cap_stem)  # Add trailing -
           sf.write("var dlen = %d;\n" % dlen) # width of bin nbrs in svg filenames
           state = 2

sf.close()
jgf.close()
