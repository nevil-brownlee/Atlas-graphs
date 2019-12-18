# 1949, Sun 12 Nov 2017 (SGT)
#
# get-bgp-table.py:  python get-bgp-table.py
#                    Modified from Emile's bulk-ris-lookup.py
#    python get-bgp-table  # Install failed for python3 on nebbiolo
#                    installing bgpstream is _tricky_!
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import config as c

from datetime import datetime, timedelta
import sys, string, time, gzip

import arrow  # "Better times and dates for Python"
import pybgpstream

#def e_print(s, **kwargs): 
#   #https://stackoverflow.com/questions/5574702/how-to-print-to-stderr-in-python
#   #print(*args, file=sys.stderr, **kwargs)  # python3
#   print >>sys.stderr, s

from_day = datetime.strptime(c.start_ymd, "%Y%m%d")
hhmm = int(c.start_hhmm[0:2])*60 + int(c.start_hhmm[2:])
from_time = from_day + timedelta(seconds=hhmm)
print("from_time = %s (%s)" % ( from_time, type(from_time)))

until_time = from_time + timedelta(minutes=30*c.n_bins*c.n_days)  # duration
print("until_time = %s" % until_time)


stream = pybgpstream.BGPStream(
    from_time = "%s" % from_time,
    until_time = "%s UTC" % until_time,
    collectors=["route-views.sg", "route-views.eqix"],
    record_type="ribs",
    )
### stream.add_filter('routeviews')

ofn = c.bgp_fn
print("fn = %s" % ofn)

print("====================================")

timestamp = arrow.get(from_time).timestamp

# fudge by 12 minutes to allow for creating of ribs
now = time.time()
fudge_secs = 12*60
if now - timestamp < fudge_secs:
   old_timestamp = timestamp
   timestamp = now - fudge_secs
   print >>sys.stderr, "timestamp to close to realtime, adjusted by %s" % (
      timestamp - old_timestamp)

# processing RIS only because of 8hrs dumps (rv is different)
stream.add_interval_filter(timestamp, timestamp+12*3600)  # AMSIX 12 hours

sys.stderr.write("start loading BGP data\n")

of = gzip.open(ofn, "wb")

t1=time.time()

n = 0;  last_pfx = ""
for elem in stream:
   path = elem.fields['as-path']  # AS path
   pfx = elem.fields['prefix']   # AS list
   ases = path.split(" ")
   origin = ases[-1]

   if pfx != last_pfx:
      s = "%s %s\n" % (pfx, origin)
      of.write(s.encode('utf-8'))      
      n += 1;  last_pfx = pfx

t2=time.time()

sys.stderr.write("finished loading BGP data (in %s s)\n" % ( t2 - t1 ))
sys.stderr.write("%s recores written\n" % n)
of.close()
