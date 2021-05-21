# 1458, Wed 17 Feb 2021 (NZDT)
#
# Tweak <svg headers>:
#   height="280pt" -> height = "100%"
#   width="648pt"  -> width = "95%"
#
# Copyright 2021, Nevil Brownlee,  U Auckland | RIPE NCC

# From ~/ISE/Design_Team/check-svg/check-svg.py
#   ElementTree doesn't have nsmap
try:
    import xml.etree.cElementTree as ET
except ImportError:
    print("Exception, using etree.ElementTree")
    import xml.etree.ElementTree as ET

import config as c
import sys

if len(sys.argv) == 1:
    print("Expected input filename as first parameter!")
    exit()
in_fn = sys.argv[1]
ifa = in_fn.split(".")
if ifa[-1] != "svg":
    print("%s is not a .svg file!");  exit()

print("Will read file %s" % in_fn)
sf = open(in_fn, "r", encoding='utf-8')  # Fail if not present

o_fn = "tw-%s" % in_fn  # fw = full-width
print("will write to %s" % o_fn)

tree = ET.parse(in_fn)
root = tree.getroot()  # The <svg > element
#print("root.attrib = %s (%s)" % (root.attrib, type(root.attrib)))

root.attrib["width"] = "95%"  # Change svg's width attrib

if ifa[:6] == "table-":  # "-" in filename, e.g. table-6-4-msms.svg
    ifa = in_fn.split("-")
    n_d_cols = int(ifa[1])
    #print("ifa %s, ndc %d" % (ifa, n_d_cols))
    if n_d_cols == 6:
        lm_px = 10 # Left margin
        hv = '"95%"'
    elif n_d_cols == 4:
        lm_px = 40;  hv = '"95%"'
    else:
        print("Input file has %d cols, not 4 or 6 ???" % n_d_cols)
        exit()
else:  # Plot from matplotlib
    lm_px = 5;  hv = "96%"

vba = root.attrib["viewBox"].split(" ")
if len(vba) != 4:
    vba = root.attrib["viewBox"].split(",")
print("@@@ vba = %s" % vba)
vba[0] = str(int(vba[0])-lm_px)
vba[2] = str(int(vba[2])+lm_px)
root.attrib["viewBox"] =  ",".join(vba)

ha = root.attrib["height"].split(",")
ha[0] = hv
root.attrib["height"] =  ",".join(ha)

tree.write(o_fn)

def run_cmd(cmd):
    output, rc = c.run_bash_commands(cmd)
    if rc != 0:
        print(output)
    return rc

rt = run_cmd("mv %s RIPE-article/figs" % o_fn)
if rt != 0:
    print(">>>>> cp RIPE-article.figs run failed!");  exit()
