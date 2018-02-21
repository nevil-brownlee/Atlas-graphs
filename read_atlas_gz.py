# 1349, Tue 17 Jun 2016 (NZST)
#
# rea_atlas_gz.py: reads atlas json data from .gz file
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import json, string, sys, copy

import ipp  # So that we can test for RFC1918 addresses!
import traceroute as tr
import timebins

debug_traces = False

def read_tr_file(tb, f_tb_n, line, mx_traces):
        # mx_traces zero -> read whole file
        # Reads Traces into tb.bins[f_tb_n]
    empty_traces = too_short_traces = nt = 0
    results = json.loads(line)  # Reads all traces for tb
    for pr in results:  # Probe
        #if nt % 1000 == 0:
        #    sys.stdout.write(". ");  sys.stdout.flush()
        msm_id = int( pr['msm_id'])
        prb_id = int( pr['prb_id'])
        ts = int( pr['timestamp'])
        dest = ipp.from_s(pr['dst_addr'])
        #print("=== nt=%d, f_tb_n=%d, msm_id=%d, probe_id=%d, src=%s, ts=%d, dest=%s, proto=%s" %(
        #    nt, f_tb_n, msm_id, prb_id, pr['src_addr'], ts, dest,  pr['proto']))

        hops = [];  empty_hops = 0
        result = pr['result']
        for h in result:  # Hops in prb_id result
            hn = h['hop']
            #sys.stdout.write("%6d " % hn)
            if not 'result' in h:
                if 'error' in h:
                    if h['error'].find("Network is unreachable") != -1:
                        continue  # No traceroute for this probe
                    print("   Error: prb_id=%d, %s" % (prb_id, h['error']))
                else:
                    print(">>> prb_id=%d, No 'result' and no 'error'" % prb_id)
                continue
            resp_d = {};  loss = 0
            res = h['result'];  rx = 0
            while rx < len(res):  # Packets in Hop
                p = res[rx]
                #print("p = %s" % p)
                addr = rtt = None
                if 'from' in p:  # From address?
                    addr = ipp.from_s(p['from'])
                    if 'late' in p and rx < len(res)-1:
                        np = res[rx+1]
                        if 'x' in np:  # 'from' followed by 'x'
                            rtt = np['x'].encode('ascii','replace')
                            rx += 1
                        else:
                            rtt = 'L'
                        loss += 1
                    else:
                        if 'rtt' in p:  # Get an rtt
                            rtt = p['rtt']
                        else:
                            rtt = '?'
                            loss += 1
                else:  # No 'from'
                    #if 'x' in p:  # lone 'x'
                    #    rtt = p['x'].encode('ascii','replace')
                    loss += 1
                if addr:
                    if addr in resp_d:  # IPprefixes _are_ hashable ## now strings
                        resp_d[addr].rtts.append(rtt)
                    else:
                        resp_d[addr] = tr.Responder(addr, [rtt])
                rx += 1
            resp_a = list(resp_d.values())  # List of responders
            if len(resp_a) == 0: 
                empty_hops += 1
            hops.append(tr.Hop(hn, loss, resp_a))

        if len(hops) == empty_hops:  # No valid hops
            empty_traces += 1
        elif len(hops)-empty_hops < 3:  # cleanup_trace() needs 2 valid hops
            too_short_traces += 1
        else:
            t = tr.Trace(msm_id, prb_id, ts, dest, hops)
            #bn = tb.bin_nbr(t.ts)
            # ts from sample in a half-hour json record may be outside
            #   the bin by +/- 1 second!
            #if f_tb_n >= len(tb.bins):
            #    print("+++ f_tb_n = %d, len(tb.bins) = %d" % (f_tb_n, len(tb.bins)))
            tb.bins[f_tb_n].append(t)
        nt += 1  # Next Trace

    return nt, dest, empty_traces, too_short_traces

def cleanup_trace(t, tn, mx_hops):  # tn = index in bin
    # Remove rfc1918 addresses, and duplicate responder address
    bad = False  # Has rfc1918 address or recurring addresses
    if len(t.hops) == 0:
        return 0, 0, 0, 0,0, 0
    
    n_1918_deleted = addrs_deleted = hops_deleted = 0
    total_addrs = total_hops = 0
    if debug_traces:  # Before
        print("Before")
        print("Trace %d: ts=%d, dest=%s" % (tn, t.ts, t.dest))
        for j,h in enumerate(t.hops):
            h.print_hop(j)
        print()
        
    cycle = 0
    while True:  # Repeat until all duplicates are removed
        cycle += 1
        #print("cycle %d" % cycle)
        if len(t.hops) > 0:
            d_empties = []  # Remove empty hops
            for hx,h in enumerate(t.hops):
                if len(h.responders) == 0:
                    d_empties.append(hx)
            for hx in range(len(d_empties)-1, -1, -1):
                t.hops.pop(d_empties[hx])

        bad = False
        # Remove rfc_1918 responders in last hop
        d_dups = [];  d_addrs = []
        if len(t.hops) > 0:
            #sys.stdout.write("--1: ")  #py3
            #t.print_trace()
            for n,dr in enumerate(t.hops[-1].responders):
                if dr.ip_addr.is_rfc1918:
                    d_dups.append(-1);  d_addrs.append(str(dr.ip_addr))
                    n_1918_deleted += 1
            for j in range(len(d_dups)):
                t.hops[-1].responders.pop(d_dups[j])
                bad = True
        for hx in range(len(t.hops)-2, -1, -1):  # Keep last occurrence
            # Remove duplicate and rfc_1918 responders in earlier hops
            sra = t.hops[hx].responders  # Responders for previous hop (hx)
            dra = t.hops[hx+1].responders  # Responders for this hop (hx+1)
            s_dups = [];  s_addrs = []
            for dr in dra:
                for x,sr in enumerate(sra):
                    if sr.ip_addr.is_rfc1918:
                        n_1918_deleted += 1
                    if sr.ip_addr == dr.ip_addr or sr.ip_addr.is_rfc1918:
                        if not str(sr.ip_addr) in s_addrs:
                            s_dups.append(x);  s_addrs.append(str(sr.ip_addr))
            total_addrs += len(dra)
            if len(s_dups) > 0:
                if debug_traces:
                    print("trace %d, hx %d, s_dups %s, s_addrs %s" % (
                        tn, hx, s_dups, s_addrs))
                ss_dups = sorted(s_dups)
                for x in range(len(ss_dups)-1, -1, -1):
                    sra.pop(ss_dups[x])
                addrs_deleted += len(s_dups)
                bad = True
            total_hops += len(t.hops)

        if debug_traces:  # After removing empty hops
            print("Trace %d: ts=%d, dest=%s, cycle=%d" % (
                tn, t.ts, t.dest, cycle))
            for j,h in enumerate(t.hops):
                h.print_hop(j)
            print()

        if bad:
            for hx in range(len(t.hops)-1, -1, -1):
                if len(t.hops[hx].responders) == 0:
                    t.hops.pop(hx)
                    hops_deleted += 1
        else:
            break

    # Delete all but the last mx_hops+1 hops
    if len(t.hops) > mx_hops+1:
        new_hops = t.hops[-(mx_hops+1):]
        t.hops = new_hops

    succ = False
    if len(t.hops) > 0:
        last_responders = t.hops[-1].responders
        if len(last_responders) == 1:
            succ = last_responders[0].ip_addr == t.dest
    #print("=== deleted: 1918 %d, addrs %d, hops %d, total_hops %d" % (
    #    n_1918_deleted, addrs_deleted, hops_deleted, total_hops))

    return n_1918_deleted, addrs_deleted, hops_deleted, \
        total_addrs, total_hops, succ

def cleanup_bin(tb, bn, mx_hops):
    t_traces = t_1918_deleted = t_addrs_deleted = t_hops_deleted = 0
    t_addrs = t_hops = t_succ = 0
    #print("cleanup_bin(%d), tb=%s" % (bn, tb))
    for tn,t in enumerate(tb.bins[bn]):
        t_traces += 1
        if t_traces % 1000 == 0:
            sys.stdout.write("- ");  sys.stdout.flush()
        #print("bn=%d, tn=%d, t = %s" % (bn, tn, t))
        n_1918_deleted, addrs_deleted, hops_deleted, n_addrs, \
            n_hops, succ = cleanup_trace(t, tn, mx_hops)

        t_1918_deleted += n_1918_deleted
        t_addrs_deleted += addrs_deleted
        t_hops_deleted += hops_deleted
        t_addrs += n_addrs
        t_hops += n_hops
        if succ:
            t_succ += 1
    print("\n*** tot_traces %d, tot_addrs %d, tot_hops %d, tot_succ %d" % (
        t_traces, t_addrs, t_hops, t_succ))
    print("*** rfc1918 deleted %d, recurring addrs %d, hops %d" % (
        t_1918_deleted, t_addrs_deleted, t_hops_deleted))
    return t_traces, t_addrs, t_hops, t_succ, t_addrs_deleted, t_hops_deleted
