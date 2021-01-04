# 1740, SU 20 Dec 2020 (NZDT)
#
# print-clip-info.py:  find all the clip files, print their descriptions

import re, string, glob, os, sys
from datetime import datetime

import config as c

pp_names = "m! y! mxd= mntr= b"  # indexes 0 to 5
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default parameters for drawing
mn_trpkts = -1;  noASNs = False
asn_graphs = not c.full_graphs
reqd_ymds = [];  reqd_msms = []

for n,ix in enumerate(pp_ix):
    if ix == 0:    # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    #elif ix == 2:  # a sets full_graphs F to use ASN graphs
    #    asn_graphs = True;  c.set_full_graphs(False)
    elif ix == 2:  # mxd  specify max depth
        mx_depth = pp_values[n]
    elif ix == 3:  # mntr specify min trpkts
        mn_trpkts = pp_values[n]
    elif ix == 4:  # b  'bare', i.e. no ASNs file available
        noASNs = True
    else:
        exit()

if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("reqd_msms = %s" % reqd_msms)
if mn_trpkts < 0:
    print("No mntr! Must specify smallest in_count for nodes plotted <<<")
    exit()
print("asn_graphs %s, c.full_graphs %s, mntr %d, mxd %d" % (
    asn_graphs, c.full_graphs, mn_trpkts, mx_depth))

#print("msm_ids: %s, ymds: %s" % (reqd_msms, reqd_ymds))

def parse_clip_file(fn):
    csf = open(fn)
    about_lines = []
    clip_name = "full";  xf = yf = 0
    nodes_to_keep = [];  bn_lo = bn_hi = -1
    cmd = "missing";  pb_type = "?"
    sd = descr = scalef = pbtyp = margin = bins = nodes = errcnt = 0
    for line in csf:  # Parse cilp-spec file - - - - - - - - - - - - -
        #print("line >%s<" % line.strip())
        line = line.split("#", 1)[0]  # Remove # and chars after #
        if len(line) <= 1:  # Ignore blank lines
            print("blank line")
            continue
        la = line.split()
        if line[0] != " ":  # Continuation line
            cmd = la[0].strip()
        # otherwise cmd is unchanged
        if cmd == "sd":  # sub-directory (clip name)
            clip_name = la[1]
            sd += 1
        elif cmd == "about":  # description (what's this clip about?)
            about_text = line.split(" ",1)[1]
            offset = ""
            if line[0] == " ":  # Continuation line
                offset = "    "
            about_lines.append("%s%s" % (offset, about_text.strip()))
            descr += 1
        elif cmd == "scale":  # scale factors for drawings
            scalef += 1
            xf = float(la[1]);  yf = float(la[2])
        elif cmd == "pbtype":  # presence-bars type(s)
            pbtyp += 1
            pb_type = " ".join(la[1:])
        elif cmd == "margin":  # left margin for drawings
            margin += 1
            bsx = float(la[1]);  bsy = float(la[2])
        elif cmd == "bins":  # bins (range of bins to use)
            clip_bn_lo = int(la[1]);  clip_bn_hi = int(la[2])
                # clip_bn_lo = first_bin_kept
                # clip_bn_hi = last_bin_kept + 1 (python-style 'stop' value)
            bins += 1
        elif cmd == "nodes":
            for addr in la:
                if addr != "nodes":
                    if asn_graphs:
                        ag = re.search(r'([0123456789\|]+)', addr)  # ASN
                    else:
                        ag = re.search(r'([0123456789.]+)', addr)  # IPv4 address
                    if ag:
                        nodes_to_keep.append(addr)
                    else:
                        print("%s <<< invalid Node address" % addr);  errcnt += 1
            nodes += 1
        elif cmd == "eof":
            break
    csf.close()
    if sd != 1 or bins != 1:
        print("May only have onde 'sd' or 'bins' line!");  errcnt += 1
    if sd == 0 or cmd == 0 or scalef == 0 or bins == 0 or nodes == 0:
        #  or margin == 0  margin doesn't work since we started using label
        print("Missing statement!");  errcnt += 1
    if errcnt != 0:
        print("%d errors in %s.txt file" % (errcnt, clip_spec[0]));  exit()

    #print("clip name: %s, scale factors %f, %f" % (clip_name, xf, yf))
    #print("clip_bins: lo %d, hi %d" % (clip_bn_lo, clip_bn_hi))
    #print("nodes_to_keep: %s" % nodes_to_keep)

    return pb_type, about_lines

def print_clip_info(clip_files):
    for fn in sorted(clip_files):
        print("\n%s" % fn)
        pbtype, about_lines = parse_clip_file(fn)
        print("  pbtype: %s" % pbtype)
        print("  about: %s" % "\n".join(about_lines))

for msm_id in reqd_msms:
    for ymd in reqd_ymds:
        c.set_ymd(ymd)

        asn_graphs = True;  c.set_full_graphs(False)  # full graphs
        clip_dir = c.clip_spec_dir(msm_id, mn_trpkts)
        clip_files = glob.glob("%s/*.txt" % clip_dir)
        print_clip_info(clip_files)

        asn_graphs = False;  c.set_full_graphs(True)  # ASN graphs
        clip_dir = c.clip_spec_dir(msm_id, mn_trpkts)
        clip_files = glob.glob("%s/*.txt" % clip_dir)
        print_clip_info(clip_files)
