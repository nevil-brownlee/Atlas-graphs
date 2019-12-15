# 1949, Sun 12 Nov 2017 (SGT)
#
# get-bgp-table.py:  python get-bgp-table.py
#                    Modified from Emile's bulk-ris-lookup.py
#    python get-bgp-table  # Install failed for python3 on nebbiolo
#                    installing bgpstream is _tricky_!
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

<<<<<<< HEAD
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
=======
'''
Prototype tool for bulk IP->AS lookups for a specific date
Downloads RIS data locally (using CAIDA BGPSTREAM)
expects IP addresses/prefixes on STDIN (IPv4 and IPv6)
takes a single command-line argument which is the DATE for which to download the table (any format convertable by arrow will do)
example use:
cat file_with_maaaaany_ips | ./bulk-ris-lookup.py 2009-03-22
'''

import config as c

import sys
import arrow
import time
import sys, string, gzip
from _pybgpstream import BGPStream, BGPRecord, BGPElem

def e_print(s, **kwargs): 
   #https://stackoverflow.com/questions/5574702/how-to-print-to-stderr-in-python
   #print(*args, file=sys.stderr, **kwargs)  # python3
   print >>sys.stderr, s

stream = BGPStream()
rec = BGPRecord()
print("-------------- imports done")

input_time = c.bgp_time
dt_dir = c.gzm_dir
duration = c.duration
print("input_time = %s, dt_dir = %s, duration = %d" % (input_time, dt_dir, duration))
print("====================================")

#fn_time = string.replace(input_time, ":", "-")  # OSX doesn't like :
ofn = c.bgp_fn
print("fn = %s" % ofn)

timestamp = arrow.get( input_time ).timestamp
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385

# fudge by 12 minutes to allow for creating of ribs
now = time.time()
fudge_secs = 12*60
if now - timestamp < fudge_secs:
   old_timestamp = timestamp
   timestamp = now - fudge_secs
<<<<<<< HEAD
   print >>sys.stderr, "timestamp to close to realtime, adjusted by %s" % (
      timestamp - old_timestamp)

# processing RIS only because of 8hrs dumps (rv is different)
stream.add_interval_filter(timestamp, timestamp+12*3600)  # AMSIX 12 hours

sys.stderr.write("start loading BGP data\n")
=======
   print >>sys.stderr, "timestamp to close to realtime, adjusted by %s" % ( timestamp - old_timestamp )

# processing RIS only because of 8hrs dumps (rv is different)
stream.add_filter('project', 'ris')
stream.add_filter('record-type', 'ribs')
# test#stream.add_filter('collector','rrc11')
stream.add_interval_filter(timestamp, timestamp+12*3600)  # AMSIX 12 hours

# start the stream
stream.start()
e_print("start loading BGP data")
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385

of = gzip.open(ofn, "wb")

t1=time.time()

<<<<<<< HEAD
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
=======
n = 0
last_pfx = ""
while(stream.get_next_record(rec)):
   elem = rec.get_next_elem()
   while(elem):

      # as path
      path = elem.fields['as-path']
      pfx = elem.fields['prefix']
      # as list
      ases = path.split(" ")
      ases.reverse()
      origin = ases[0]

      if pfx != last_pfx:
         of.write("%s %s\n" % (pfx, origin))
         last_pfx = pfx
         n += 1

      elem = rec.get_next_elem()

t2=time.time()

e_print("finished loading BGP data (in %s s)" % ( t2 - t1 ))

of.close()

'''

      rnode = rtree.search_exact( pfx )
      if rnode:
         rnode.data['origin'].add( origin )
      else:
         rnode = rtree.add( pfx )
         rnode.data['origin'] = set([ origin ])
      
'''
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385
