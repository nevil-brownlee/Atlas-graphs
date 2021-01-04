# 1544, Tue  7 Aug 2018 (NZST)
#
# read_yaml_gz.py: read ripe traceroute data from yaml file
#
# Copyright 2018, Nevil Brownlee,  U Auckland | RIPE NCC

import gzip, re, sys
import ipp

import traceroute as tr
import timebins
import graph
import read_atlas_gz
import config as c

class Yaml:
    def __init__(self, zif):
        self.zf = zif
        self.debug_traces = True  #False
        #self.read_gen = self.f_read()
            # generator, reads next line from self.zf
        self.ln = 0  # build-graphs.py reads the first two lines
        self.tb = None;  self.nt = 0
        self.t_empty = self.t_short = None
        self.bga = [];  self.dest = None

    class YamlEOF(Exception):
        pass

    def f_read(self):  # Generator of line info
        #for b_line in next(Yaml.read_gen):
        for b_line in self.zf:
            line = b_line.decode('ascii')
            self.ln += 1
            if self.ln % 100000 == 0:
                sys.stdout.write(".");  sys.stdout.flush()
            ls = line.rstrip()
            if len(ls) == 0:  # Blank line
                continue
            if line[0] == '#':  # Comment
                if re.match(r'^#Input header', ls):
                    lsa = ls.split()
                    start_dt = lsa[3]
                    edt = lsa[5];  end_dt = edt[:-1]
                    self.tb = timebins.TimeBins(start_dt, end_dt)
                    print("tb = %s" % self.tb)
                    self.t_empty = [0]*self.tb.nbins
                    self.t_short = [0]*self.tb.nbins
                continue
            nb = len(ls) - len(ls.lstrip())
            la = ls.split()
            #if self.ln == 5000:
            #    exit()
            #print("%6d: %2d >%s" % (self.ln, nb,ls))
            value = None
            if len(la) > 1:
                value = la[1]
            return nb, self.ln, la[0], value
        print("\n%8d: End of file" % self.ln)
        raise self.YamlEOF

    def get_rtts(self):
        rtts = []
        while True:
            #nb, ln, name, value = next(read_gen)
            nb, ln, name, value = self.f_read()
            if name == '-':
                if value:
                    rtts.append(float(value))
            else:  # Line doesn't start with '-'
                return nb, ln, name, value, rtts

    def get_responders(self, init_nb):
        prefix = None;  responders = []  # Ignore 'special'
        next_nb = None
        try:
            while True:
                if not next_nb:
                    #next_nb, ln, name, value = next(self.read_gen)
                    next_nb, ln, name, value = self.f_read()
                    # print("(%d, %d, %s, %s) responders !!" % (nb, ln, name, value))
                if next_nb <= init_nb:  # Smaller indent starts next object
                    return next_nb, ln, name, value, responders
                if name[-1] == ':':  # Expect !ruby/object:Responder
                    if name != '"":':  # addr's valus has : as last char
                        ip_address = ipp.from_s(name[0:-1])
                        if ip_address.version != 4:
                                print("\nIPv6 address @ ln %d  %s" % (ln, addr))
                    else:
                        ip_address = None
                    #try:
                    #    ip_address = ipp.from_s(name[0:-1])
                    #except ValueError:
                    #    print("*** ValueError: name = >%s<, ln = %d" % (name, ln))
                    #    exit()
                # print("%8d: value = >%s<" % (ln, value))
                va = value.split(':')
                o_name = va[1]
                if o_name != 'Responder':
                    print("%8d: responder name: without value <<<<" % ln)
                next_nb = None
                while True:
                    if not next_nb:
                        #next_nb, ln, name, value = next(self.read_gen)
                        next_nb, ln, name, value = self.f_read()
                        # print("(%d, %d, %s, %s) responders <-" % (
                        #     next_nb, ln, name, value))
                    a_name = name[0:-1]
                    if a_name == 'rtt':
                        next_nb, ln, name, value, rtts = self.get_rtts()
                        # print("(%d, %d, %s, %s) rtts = %s" % (
                        #     next_nb, ln, name, value, rtts))
                        if ip_address:
                            responders.append(tr.Responder(ip_address, rtts))
                        continue
                    if a_name == 'special':
                        next_nb = None
                        break  # special: last line for a responder
        except self.YamlEOF:
            print("   YamlEOF Exception caught in get_responders()")
            #sys.exc_clear()  # Not needed in python3
        return -1, ln, name, value, responders


    def get_hop(self):
        hop = loss = 0  #  responders = {}  #  Ignore 'map'
        next_nb = None
        while True:
            if not next_nb:
                next_nb = None
                #nb, ln, name, value = next(self.read_gen)  # Expect 'hop:' attri                
                nb, ln, name, value = self.f_read()  # Expect 'hop:' attribute
            # print("(%d, %d, %s, %s) Hop" % (nb, ln, name, value))
            if name[-1] == ':':
                a_name = name[0:-1]
                if a_name == 'hop':
                    hop = int(value)
                elif a_name == 'loss':
                    loss = int(value)
                elif a_name == 'map':
                    while True:
                        #next_nb, ln, name, value = next(self.read_gen)
                        next_nb, ln, name, value = self.f_read()
                        if next_nb == nb:  # Unindent = end of map
                            break
                elif a_name == 'responders':
                    value = []
                    if value == "{}":
                        continue
                    else:
                        next_nb, ln, name, value, responders = \
                            self.get_responders(next_nb)
                        if next_nb <= 0:  # Next object
                            break
        # print("Hop(hop=%d, loss=%d, responders=%s)" % (hop, loss, responders))
        return next_nb, ln, name, value, tr.Hop(hop, loss, responders)  # -1 = EOF

    def get_trace(self):
        msm_id = probe_id = ts = dest = complete = None
        hops = None;  empty_hops = 0
        next_nb = None
        while True:
            nb, ln, name, value = self.f_read()  # Expect trace: attributes
            #print("-1- (%d, %d, %s, %s) Trace" % (nb, ln, name, value))
            if name[-1] == ':':  # attrib: value
                a_name = name[0:-1]
                if a_name == 'msm_id':
                    msm_id = int(value)
                elif a_name == 'probe_id':
                    probe_id = int(value)
                elif a_name == 'ts':
                    ts = int(value)
                elif a_name == 'dest':
                    #print("??? dest: value = >%s<" % value)
                    dest = None
                    if value and value != '"?"':
                        dest = ipp.from_s(value)
                    if dest and self.dest:
                        if dest != self.dest:
                            print("!!! dest=%s but self.dest=%s, ln=%d" % (
                                dest, self.dest, ln))
                    else:
                        self.dest = dest
                elif a_name == 'complete':
                    continue  # Ignore 'complete'
                elif a_name == 'hops':
                    hops = []
                    if value == '[]':
                        continue  # Empty list
                    else:
                        while True:
                            next_nb, ln, name, value, hop = self.get_hop()
                            # print(".... back in get_trace(%d) ...." % next_nb)
                            # print("(name=%s, value=%s, hop=%s) get_trace" % (
                            #     name, value, hop))
                            if len(hop.responders) == 0:
                                empty_hops += 1
                            else:
                                hops.append(hop)
                                # hop.print_hop
                            if next_nb < 0:  # EOF
                                return tr.Trace(msm_id, probe_id, ts, dest, hops), empty_hops, "EOF"
                            if name == '---':
                                break
            #print("gt gt gt: msm_id=%s, probe_id=%s, ts=%s, dest=%s, hops=%s" % (
            #    msm_id, probe_id, ts, dest, hops))
            if name == '---':  # Start of next trace
                #print("Trace(msm_id=%d, probe_id=%d, ts=%d) ***" % (
                #    msm_id, probe_id, ts))
                return tr.Trace(msm_id, probe_id, ts, dest, hops), empty_hops, value


    def read_tr_file(self, mx_traces, sf):  # mx_traces zero -> read whole file
        while True:  # Read the yaml_tr.gz file
            more = True
            try:
                while more:
                #nb, ln, name, value = Yaml.read_gen()
                    nb, ln, name, value = self.f_read()
                    #print("-0- (%d, %d, %s, %s)" % (nb, ln, name, value))
                    if name[0] == '!':
                        print("%8d: %s >>> name starts with ! <<<" % (ln, name))
                        break
                    if name == '---':
                        va = value.split(':')
                        o_name = va[1]
                        #print("%8d: start of %s object" % (ln, o_name))
                        while True:
                            if o_name == 'Trace':
                                t, empty_hops, value = self.get_trace()
                                #print(">>> t %s, value %s" % (t, value))
                                #if t.dest == '?' or len(t.hops) == 0:
                                #    print("pid %d, empty trace" % t.probe_id)
                                #else:
                                self.nt += 1
                                #if t.hops:
                                    #last_hop = t.hops[len(t.hops)-1]
                                    #print("nt=%d, last_hop = %s" % (nt, last_hop))
                                    #for r in last_hop.responders:
                                    #    ip_pref = r.ip_addr.network(24)
                                this_bn = self.tb.bin_nbr(t.ts)
                                #print("+++ trace %d, ts %u, this_bin %d" % (
                                #    nt, t.ts, this_bn))
                                #print("*** trace %d: ts=%u, bn=%d, t=%s" % (nt, t.ts, bn, t))
                                #print("--> bn = >%s<, type(bn) = %s" % (bn, type(bn)))
                                self.tb.bins[this_bn].append(t)
                                if len(t.hops) == empty_hops:  # No valid hops
                                    self.t_empty[this_bn] += 1
                                elif len(t.hops)-empty_hops < 3:
                                    # cleanup_trace() needs 2 valid hops
                                    self.t_short[this_bn] += 1
                                ##?? tb.tindex.append( (bn, len(tb.bins[bn])-1) )
                                if self.nt == mx_traces:
                                    print("--- %d traces read" % nt)
                                    more = False;  break
                                elif value == "EOF":
                                    more = False;  break
                                va = value.split(':')
                                o_name = va[1]
                            else:
                                print("%8d: Expected 'Trace', got '%s'  <<<" % (
                                    ln, o_name))
                                break
                    elif name[-1] != ":":  # (name, value) pair
                        print("ln=%d name=%s, value=%s  <<< lone pair !?" % (
                            ln, name, value))
            except self.YamlEOF:
                print("   YamlEOF 111 in read_tr_file()")
                print("nt = %d traces" % self.nt)
                break

        for tb_n in range(0, self.tb.nbins):
            print("Timebin %d, %d Traces, %d empty, %d too short" % (
                tb_n, len(self.tb.bins[tb_n]),
                self.t_empty[tb_n], self.t_short[tb_n]))

            t_traces, t_addrs, t_hops, t_succ, t_addrs_deleted, \
                t_hops_deleted = read_atlas_gz.cleanup_bin(
                    self.tb, tb_n)  # , c.mx_depth) 20 Feb 2020
                # Remove rfc1918 and duplicate-responder address
            print("===  tb=%s, t_traces=%s" % (self.tb, t_traces))

            g = graph.build_graph(tb_n, self.tb.bins[tb_n], t.dest, \
                t_traces, t_addrs, t_hops, t_succ, t_addrs_deleted, \
                t_hops_deleted, c.msm_id, sf)
            self.bga.append(g)

        return self.bga, self.dest, self.tb, self.nt
