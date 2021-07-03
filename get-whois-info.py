# 1659, Wed 29 Jan 2020 (NZDT)
# 1600, Wed 10 Jul 2019 (NZST)
# 1605, Wed  7 Sep 2016 (NZDT)
#
# get-whois-info.py:  Looks up whois info for ASNs in asns-all file
#
# Copyright 2020, Nevil Brownlee,  U Auckland | RIPE NCC

import traceroute as tr
import dgs_ld
import config as c

from ipwhois import IPWhois

import requests
import string, time, random, math, os

reqd_ymds = [];  reqd_msms = []
pp_names = "m! y! mntr="  # indeces 0 to 2
pp_ix, pp_values = c.set_pp(pp_names)  # Set up config info
mx_depth = c.draw_mx_depth  # Default parameters for drawing
mn_trpkts = c.draw_mn_trpkts
for n,ix in enumerate(pp_ix):
    if ix == 0:    # m  (50xx) msm_ids
        reqd_msms = c.check_msm_ids(pp_values[n])
    elif ix == 1:  # y  (yyyymmdd) dates
        reqd_ymds = c.check_ymds(pp_values[n])
    elif ix == 2:  # mntr specify min trpkts
        mn_trpkts = pp_values[n]
    else:
        exit()
if mn_trpkts < 0:
    print("No mntr! Must specify smallest in_count for nodes plotted <<<")
    print("Note: whois-all- file keeps whois info for all looked-up asns")
    exit()
if len(reqd_ymds) == 0:
    reqd_ymds = [c.start_ymd]
elif len(reqd_ymds) > 1:
    print("More than one ymd specified!");  exit()
if len(reqd_msms) == 0:
    reqd_msms = [c.msm_id]
print("mntr %d, reqd_ymds %s, reqd_msms = %s" % (mn_trpkts, reqd_ymds, reqd_msms))
c.set_ymd(reqd_ymds[0])

class ASN:
    def __init__(self, asn, address, in_count):
        self.asn = asn;  self.address = address;  self.in_count = in_count
        self.cc = self.registry = self.name = self.descr = '-'
        self.r_printed = False
        self.count = 1

    def set_ASN_info(self, name, cc, registry):
        self.name = name;  self.cc = cc;  self.registry = registry

    def __str__(self):
        return "%s  %s  %d" % (self.asn, self.address, self.count)

    def __lt__(self, other):
        return self.asn < other.asn
        
    def __eq__(self, other):
        return self.asn == other.asn

    def print_results(self, results):
        if not self.r_printed:
            for rk in results:
                if rk == 'network':
                    for nk in results[rk]:
                        if nk:
                            try:
                                rk_val = results[rk].encode('utf-8', 'default') # Convert to bytes
                            except:
                                rk_val = rk_val.encode('cp437', 'default')
                                #  437 encoding = IBM PC 8-bit characters
                            print("++ netwk.%s = %s" % (nk, rk_val))
                else:
                    print("++ rk %s = %s" % (rk, results[rk].encode('cp437')))
        self.r_printed = True

    def get_field(self, results, fname):
        try:
            if fname in results:
                val = results[fname]
                if val:  # Not None
                    try:
                        return True, val.replace(' ','_')  # String
                    except:
                        print("!!! utf-8 encode() failed")
                        return True, os.fsencode(val)
                else:
                    return True, None
            else:
                self.print_results(results)
                return False, False
        except:
            print("get_field(%s) failed <<<" % fname)
            print("   address = %s" % self.address)
            self.print_results(results)
            return False, False

    def get_whois(self):
        try:
            obj = IPWhois(self.address)
            results = obj.lookup_rdap(depth=1)
        except:
            print("whois lookup failed <---")
            return 1

        have_cc = False  # Now unpack whois result
        r, val = self.get_field(results, 'asn_registry')
        if r and val:
            self.registry = val
            print("  registry = %s" % self.registry)
        r, val = self.get_field(results, 'asn_country_code')
        if r and val:
            self.cc = val.lower()
            have_cc = True
            print("  cc = %s" % self.cc)
        if 'network' in results:
            netwk = results['network']
            r, val = self.get_field(netwk, 'name')
            if r and val:
                self.name = val
                print("  name = %s" % val.encode('utf-8', 'replace'))
                    # Print as Bytes
            if not have_cc:
                r, val = self.get_field(netwk, 'country')
                if r and val:
                    self.cc = val.upper()
                    print("  cc = %s" % self.cc)
        return 0

    def get_http(self):
        url_base = 'https://ipinfo.io/AS'
        for asn in self.asn.split("|"):
            r = False
            print("trying get_http(%s)" % url_base+asn)
            try:
                r = requests.get(url_base + asn)
            except:
                print("Couldn't get_http(%s) !!!" % url_base+asn)
                print("  Is your wifi connection up?")
                continue  # Try for others . . . . ?
            r.encoding = "utf-8"
            lines = r.content.splitlines()
            self.cc = self.registry = self.name = self.descr = '-'
            
            state = 0;  ok_count = 0
            for line in lines:
                #print("   %s" % line)
                if state == 0:
                    if line.decode('utf-8').find("aut-num") >= 0:
                        la = line.split()
                        print("asn = %s" % la[-1][2:])
                        state = 1
                elif state == 1:
                    ln = line.strip().decode('utf-8')
                    if ln.find("</pre>") >= 0:
                        break
                    else:
                        la = ln.split(':')
                        if len(la) <= 1:
                            continue  # Ignore empty lines
                        key =la[0].encode('utf-8');  val = la[1].strip()
                        if key == b"as-name":
                            self.name = val
                            print("as-name = %s" % self.name)
                            ok_count += 1
                        if key == b"descr":
                            self.descr = val
                            print("descr = %s" % self.descr)
                            ok_count += 1
                        elif key == b"country":
                            self.cc = val.upper()
                            print("cc = %s" % self.cc)
                            ok_count += 1
                        #elif la[0] == "source":
                        #    self.registry = la[1].lower()
                        #    print("source = %s" % self.source)
                        #else:
                        #    ignore = la[0] in ["import:", "mp-import:", "export:",
                        #        "mp-export:", "remarks:", "status:", "mnt-by:",
                        #        "created:", "last-modified:"]
                        #    if not ignore:whois-all-20191211-0000-48.txt
                        #        print("%s" % line)
                if ok_count == 3:
                    break
        return 0

all_whois_d = {}  # Dictionary of ASN objects, key asn
all_whois_fn = g_fn = c.all_whois_fn()  # All whois info known so far for c.msm_id
if os.path.exists(all_whois_fn):
    print("Will read all-whois file %s" % all_whois_fn)
    whois_info_f = open(all_whois_fn, 'r')
    for line in whois_info_f:  # Get dictionary of ASNs
        n, asn, colour, name, cc, registry = line.strip().split()
        if asn == "15895":
            print("%s  %s %s <1<" % (n, asn, name))
        all_whois_d[asn] = name + ' ' + cc + ' ' + registry
    whois_info_f.close()
n_whois_known = len(all_whois_d)
print("%d ASNS known in whois-all" % n_whois_known)

for msm_id in reqd_msms:
    print("\n>>> Starting msm_id %s\n" % msm_id)
    msm_id_asns = {}  # All ASNs (with in_counts) from asns-50xx file
    asnf = open(c.asns_fn(msm_id), 'r')
    n_nodes = mn_nodes = 0
    for line in asnf:
        n_nodes += 1
        la = line.strip().split()
        addr = la[0];  asn = la[1];  in_count = int(la[2])
        in_count = int(in_count)
        if in_count >= mn_trpkts:
            mn_nodes += 1
            if asn not in msm_id_asns:
                msm_id_asns[asn] = ASN(asn, addr, in_count)
            else:
                msm_id_asns[asn].count += 1  # Nbr of times the ASN appears
                msm_id_asns[asn].in_count += in_count  # Total in_count seen for ASN
    print("File %s read, %d nodes, %d with in_count >= %d, %d ASNs required" % (
        c.asns_fn(msm_id), n_nodes, mn_nodes, mn_trpkts, len(msm_id_asns)))

    asns_needed = {}  # Dictionary of ASNs to be looked up for msm_id
    for ak in msm_id_asns:
        ak_asn = msm_id_asns[ak]
        #print("??? ak_asn (%s) = %s" % (type(ak_asn), ak_asn))
        if ak not in all_whois_d and ak_asn.in_count >= mn_trpkts:
                    # all_whois_d read from asns-all-
            if ak not in asns_needed:
                asns_needed[ak] = ak_asn.in_count
    asnf.close()
    print("==> %d asns for msm_id %d" % (len(msm_id_asns), msm_id))
    print("  %d whois already known, %d to be looked up for %d" % (
        n_whois_known, len(asns_needed), msm_id))

    kv_list = [];
    for n,ak in enumerate(msm_id_asns):  # Make kv list
        if msm_id_asns[ak].asn == "15895":
            print("15895 in msm_id_asns")
        asn_obj = msm_id_asns[ak]
        kv_list.append( (asn_obj, asn_obj.count) )
            # (asn, nbr of prefixes counted)
    print("%d ASNs in msm_id_asns, %d in kv_list" % (
        len(msm_id_asns), len(kv_list)))

    whois_msm_fn = c.whois_fn(msm_id)
    print("Will write %s" % whois_msm_fn)
    whois_msm_f = open(whois_msm_fn, 'w')
    print("  and append to %s" % all_whois_fn)
    whois_info_f = open(all_whois_fn, "a", encoding='utf-8')

    def times_seen(item):  # For kv_list sort
        return item[1]
        
    n = 0;  n_to_go = len(kv_list);  n_written = 0
    print("n_to_go = %d" % n_to_go)
    for kve in sorted(kv_list, key=times_seen, reverse=True):
        n += 1
        asn_obj = kve[0]

        colour = n  # asn_colours in dgs_ld.py
        if colour > 20:
            colour = 0  # black

        r = 0
        if asn_obj.asn in all_whois_d:  # Use info from asns-all- file
            #if asn_obj.asn 
            whois_msm_f.write("%d %s %d %s\n" % (
                n, asn_obj.asn, colour, all_whois_d[asn_obj.asn]))
            n_written += 1
            #print("%s in all_whois_d, %d written, %d n_to_go" % (
            #    asn_obj.asn, n_written, n_to_go))
            n_to_go -= 1
        else:  # Have to look up whois info
            print("%d ASNs still needed" % n_to_go)
            #if n_to_go == 0:
            #    break
            #print("n_to_go == 0 !!!!!!!!!");  exit()
            r = asn_obj.get_whois()
            if r != 0:
                r = asn_obj.get_http()
            if r != 0:
                print("%2d %s:  Failed" % (n, asn_obj.asn))
            whois_msm_f.write("%s %s %d %s %s %s\n" % (
                n, asn_obj.asn, colour, asn_obj.name, asn_obj.cc, asn_obj.registry))

            if asn_obj.asn not in all_whois_d:  # Append to whois-all file
                n_whois_known += 1
                whois_info_f.write("%d %s %d %s %s %s\n" % (
                    n_whois_known, asn_obj.asn, 
                    colour, asn_obj.name, asn_obj.cc, asn_obj.registry))

            r = random.random()  # [0.0, 1.0)
            t = -1.0*math.log(r)
            n_to_go -= 1
            if t > 2.0:
                t = 2.0
                time.sleep(t)
            #if n == 4:
            #    break

    whois_info_f.close()  # whois-all
    whois_msm_f.close()  # 
