# 1711, Wed  3 Jul 2019 (NZST)
# 1605, Wed  7 Sep 2016 (NZDT)
#
# get-whois-info.py:  Looks up whois info for ASNs
#
# Copyright 2016, Nevil Brownlee,  U Auckland | RIPE NCC

import traceroute as tr
import dgs_ld
import config as c

from ipwhois import IPWhois

import requests
import string, time, random, math, os

class ASN:
    def __init__(self, asn, address):
        self.asn = asn;  self.address = address
        self.cc = self.registry = self.name = self.descr = '-'
        self.r_printed = False
        self.count = 1

    def __str__(self):
        return "%s  %s" % (self.asn, self.address)

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
                print("  name = %s" % val.encode('utf-8', 'replace'))  # Print as a Bytes
            if not have_cc:
                r, val = self.get_field(netwk, 'country')
                if r and val:
                    self.cc = val.upper()
                    print("  cc = %s" % self.cc)
        return 0

    def get_http(self):
        url_base = 'https://ipinfo.io/AS'
        for asn in self.asn.split("|"):
            #print("trying get_http(%s)" % url_base+asn)
            r = requests.get(url_base + asn)
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
                        #    if not ignore:
                        #        print("%s" % line)
                if ok_count == 3:
                    break
        return 0

af = open(c.asn_fn(c.msm_id), "r")
print("Will read asns file %s" % af)

asn_d = {}  # Dictionary of ASN objects, key 

for line in af:  # Get dictionary of ASNs, with counts for each
    la = line.strip().split()
    addr = la[0];  asn = la[-1]
    if asn in asn_d:
        asn_d[asn].count += 1
    else:
        asn_d[asn] = ASN(asn, addr)
af.close()

kv_list = []
for k in asn_d:
    kv_list.append( (asn_d[k], asn_d[k].count) )

whoisfn = c.whois_fn(c.msm_id)
whoisf = open(whoisfn, "w", encoding='utf-8')
print("Will write whois info file %s" % whoisf)
n = 0
for kv in sorted(kv_list, reverse=True):
    n += 1
    asn_obj = kv[0]  # (count is kv[1])
    colour = 0
    print("%d %s - - -" % (n, asn_obj.asn))
    r = asn_obj.get_whois()
    if r != 0:
        r = asn_obj.get_http()
    if r != 0:
        print("%2d %s:  Failed" % (n, asn_obj.asn))

    colour = n  # asn_colours in dgs_ld.py
    if colour > 20:
        colour = 0  # black
    whoisf.write("%d %s %d %s %s %s\n" % (
        n, asn_obj.asn, colour, asn_obj.name, asn_obj.cc, asn_obj.registry))

    r = random.random()
    t = -1.0*math.log(r)
    time.sleep(t)
    #if n == 4:
    #    break

whoisf.close()
