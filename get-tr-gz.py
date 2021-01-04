# 1627, Wed 19 Feb 2020 (NZDT)
# 1510, Sat  4 Nov 2017 (NZST)
# 1021, Thu 23 Jun 2016 (NZST)
#
# get-tr-gz.py: gets atlas json data from RIPE, write to .gz file
#    pypy3 get-tr-gz.py -y 20171023 -n 48 -d 7 -m 5005
#                 msm_id 5005 for a week (Mon 20171023 thru Sun 1029)
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

# Documentation at https://github.com/RIPE-NCC/ripe-atlas-cousteau

import time
from datetime import datetime
from datetime import timedelta
import calendar
from pytz import timezone
from ripe.atlas.cousteau import AtlasResultsRequest
#from ripe.atlas.sagan import Result

import json, gzip, sys, os, resource

import config as c

print("probes_fn = %s" % c.probes_fn())
os.environ['TZ'] = 'UTC'

start_time = timezone('UTC').localize(c.start_time)  # Convert to UTC datetime
print("start_time = %s" % start_time.strftime('%X %x %Z'))

time_range = "%s-%02d" % (c.start_hhmm, c.n_bins)

kwargs = {  # start, stop and probe_ids set in inner loops below
    "msm_id": c.msm_id,
    "start": None,
    "stop": None,
    "probe_ids": None,
    "fields": "traceroute"
    }

print("c.gzm_dir = %s", c.gzm_dir)
if not os.path.exists(c.gzm_dir):
    os.makedirs(c.gzm_dir)

for day in range(0,c.n_days):  #Read  RIPE Atlas for n_days days
    # Write separate files into one-day directories
    start_t = start_time + timedelta(seconds=1800)*day*c.n_bins
    end_time = start_time + timedelta(seconds=1800)*(day+1)*c.n_bins

    start_ymd = start_t.strftime("%Y%m%d")
    print("starting at %s" % start_ymd)

    fn_gzm_txt = c.gzm_txt_fn(start_ymd, c.msm_id)
    print("$$$ starting day %d, fn_gzm_txt = %s" % (day, fn_gzm_txt))

    day_dir = "%s/%s" % (c.gzm_dir, start_ymd)
    if not os.path.exists(day_dir):
        os.makedirs(day_dir)

    of = open(fn_gzm_txt, "w")
    st = start_time.strftime("%Y-%m-%dT%H")  # For file header record
    et = end_time.strftime("%Y-%m-%dT%H")
    of.write("#Input header: %s: %s to %s, msm_id = %s\n" % (
        sys.argv[0], st, et, c.msm_id))

    def MB_in_use():
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000.0

    stop_time = start_t  # Start time for this day
    for b in range(0, c.n_bins):
        bin_start_time = stop_time  # From previous bin
        stop_time = bin_start_time + timedelta(seconds=1800)
        kwargs["start"] = bin_start_time
        kwargs["stop"] = stop_time           

        pf = open(c.probes_fn(), 'r')  # Takes about 40 s per block on nebbiolo
        pg = 0  # Probe numbers group
        for line in pf:
            pna = line[1:-2].strip().split(",")
            probes = []
            for ps in pna:
                probes.append(int(ps))

            kwargs["probe_ids"] = probes
            #print("time now = %s" % datetime.now())
            is_success, results = AtlasResultsRequest(**kwargs).create()
            #print("is_success=%s" % is_success)
            if not is_success:
                print("AtlasRequest failed for bin %d, pg %d <<<" % (b, pg))
            else:
                print("  %2d,%d start_ts = %s" % (b, pg, bin_start_time))
                #print(kwargs);  print()
                json.dump(results, of)
                of.write("\n")
                #for r in results:
                #    gr = Result.get(r, parse_all_hops=True)
                    #print("=== msm_id=%d, probe_id=%d, dest=start_ts=%d, dest=%s, %d hops" % (
                    #    gr.measurement_id, gr.probe_id, gr.created_timestamp,
                    #    gr.destination_address, len(gr.hops)))
                    #sys.stdout.flush()
                #    gr = None  # Don't hold gr in memory
                #break  # Break inner loop
            pg += 1
            results = None  # Don't keep last batch in memory!
        #else:
            #continue  # Continue outer loop if inner loop wasn't broken
        #break  # Only get one timebin
        print("end of timebin %d: %.2f MB" % (b,MB_in_use()))
        sys.stdout.flush()
        pf.close()

    of.close()
    print("time now = %s" % datetime.now())


    fn_gzm_gz = c.gzm_gz_fn(start_ymd, c.msm_id)
    print("zipping to %s" % fn_gzm_gz)
    of = gzip.open(fn_gzm_gz, "wb")
    inf = open(fn_gzm_txt, "rb")
    for line in inf:
        of.write(line)
    of.close()
    inf.close()

    os.remove(fn_gzm_txt)  # We have the .gz version, don't need the .txt
