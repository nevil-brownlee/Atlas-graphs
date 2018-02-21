# 1728, Thu 4 Jan 2016 (NZDT)
#
# traceroute.py: base classes for traceroute data
#
# Copyright 2016, Nevil Brownlee,  U Auckland | RIPE NCC

class Responder:
    def __init__(self, ip_addr, rtts):
        self.ip_addr = ip_addr  # ipp prefix (length None)
        self.rtts = rtts  # List

    def __str__(self):
        return str(self.rtts)

class Hop:
    def __init__(self, nbr, loss, responders):
        self.hop = nbr;  self.loss = loss
        self.responders = responders  # List of d.values()

    def n_responders(self):
        return len(self.responders)
    
    def get_empty(self):
        return len(responders) == 0
    empty = property(get_empty)

    def print_hop(self, hop_nbr):
        hns = "%5d: %d" % (hop_nbr+1, self.loss)  # 1-org in traceroute
        hn_offset = ' '.ljust(len(hns))
        if len(self.responders) == 0:  # Empty hop
            print("%s%s %s" % (hns, ' '.ljust(len(hns)), '--'))
        else:
            for r in self.responders:
                print("%s  %s %s" % (hns, r.ip_addr, r.rtts))
                hns = hn_offset
                
class Trace:
    def __init__(self, msm_id, probe_id, ts, dest, hops):
        self.msm_id = msm_id;  self.probe_id = probe_id
        self.ts = ts;  self.dest = dest  # ipp prefix (length None)
        self.hops = hops  # List

    def __str__(self):
        return "<pid=%d, hops=%s,  mx_hops=%d>" % (
            self.probe_id, self.hops, len(self.hops))
        
    def print_trace(self):
        print("msm_id=%s, probe_id=%d, dest=%s, ts=%d" % (
            self.msm_id, self.probe_id, self.dest, self.ts))
        if len(self.hops) == 0:
            print("   []")
        else:
            for n,hop in enumerate(self.hops):
                hop.print_hop(n)
