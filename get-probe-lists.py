<<<<<<< HEAD
# 1552, Fri 13 Dec 2019 (NZDT)
=======
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385
# 1627, Fri  3 Nov 2017 (NZST)
#
# get-probe-lists.py:  Makes list of probes to use for a dataset
#    python3 get-probe-lists.py  (uses params.txt values to determine dataset)
#
<<<<<<< HEAD
# Copyright 2019, Nevil Brownlee,  U Auckland | RIPE NCC
=======
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385

# Documentation at https://github.com/RIPE-NCC/ripe-atlas-cousteau

from ripe.atlas.cousteau import ProbeRequest
import os, random
import config as c

# Areas  from  https://atlas.ripe.net/docs/udm/  "WW" = all 
#Areas = ["South-East", "North-East", "South-Central", "North-Central", "West"]

filters = {"area": "WW", "tags":"system-ipv4-works"}
probes = ProbeRequest(**filters)  # About 30k probes!

<<<<<<< HEAD
p_fa = c.probes_fn().split("/")  # Make sure the start_ymd dire ctory exists
pd = p_fa[1]
if not os.path.exists(pd):
    os.makedirs(pd)

=======
>>>>>>> 92c20d888b97d193e9f23a45066c314830055385
pn_dict = {}
for probe in probes:
    pid = probe["id"];  asn_v4 = probe["asn_v4"]
    #  asn_v4 is the _probe_'s ASN!

    if pid in pn_dict:
        print("%d appears twice in probes <<<" % pid)
    else:
        pn_dict[pid] = asn_v4
print("%d probes from Atlas" % len(pn_dict))

pf = open(c.probes_fn(), "w")
pn_list = list(pn_dict.keys())
for n in range(0,10):
    probe_nbrs = []
    for j in range(0, c.ppb):
        ri = random.randint(0, len(pn_list)-1)
        pn = pn_list[ri]
        probe_nbrs.append(pn)
        pn_list.pop(ri)
    pf.write("%s\n" % sorted(probe_nbrs))

pf.close()
