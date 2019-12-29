# 1633, Wed 18 Dec 2019 (NZDT)
# 1709, Tue 23 Oct 2018 (NZDT)
#
# Make graphs- files for a spcified date
#
# Copyright 2018, Nevil Brownlee, U Auckland

#import string, os, datetime
import subprocess

import config as c
c.set_pp(False, c.msm_id)  # Set prune parameters

reqd_date = c.start_ymd

egf, gntb = c.find_msm_files("graphs", reqd_date)
print("egf = %s" % egf)
enf, nntb = c.find_msm_files("nodes", reqd_date)
print("enf = %s" % enf)
if gntb != nntb:
    print("*** Inconsistent nbr of timebins (%s != %s)" % (gntb, nntb))
print("gntb = %s, nntb = %s" % (gntb, nntb))

for msm_id in egf:
    if msm_id in enf:
        continue  # Already have its nodes file  ??? 14 Jun 2019 ???
    msm_id_b = msm_id.encode('utf-8')
    ntb = gntb.encode('utf-8')
    print("msm_id = %s, gntb = %s" % (msm_id_b, gntb))
    cmd = b"python3 make-combined-svgs.py -y " + reqd_date.encode('utf-8') + \
        b" -n " + ntb + b" -m " + msm_id_b
    print("cmd = >%s<" % cmd)

    output, err = c.run_bash_commands(cmd)
    lines = output.decode('utf-8').split('\n')
    for ln in lines:
        print(ln)
