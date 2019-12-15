# 1730, Mon 15 Feb 2016 (NZDT)
#
# timebins.py: A class to hold info about TimeBins
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import datetime, calendar
from pytz import timezone
    # http://www.saltycrane.com/blog/2009/05/converting-time-zones-datetime-objects-python/

#./tr_gather.rb: 2012-05-01T00 to 2012-05-02T00, msm_id = 5006

def str2time(dt):
    ddt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H %Z")
    return calendar.timegm(ddt.timetuple())

class TimeBins:
    SampleInterval = 30*60

    def __init__(self, start_dt, end_dt):  # _dt are strings!
        self.start_dt = start_dt;  self.end_dt = end_dt
        self.start_ts = str2time(start_dt + ' UTC')
        end_ts = str2time(end_dt + ' UTC')
        self.start_tb = int(self.start_ts/TimeBins.SampleInterval)
        end_tb = int(end_ts/TimeBins.SampleInterval)
        self.nbins = end_tb-self.start_tb
        print("from %s to %s, %d bins" % (start_dt, end_dt, self.nbins))
        print("   timestamps from %u to %u" % (self.start_ts, end_ts))

        self.bins = [[] for j in range(self.nbins)]  # Traces for each bin
        #self.tindex = [ None ]  # Trace nbr -> (bin, index in bin) map
        #    # Built by appending traces, starting with tnbr 1

    def __str__(self):
        return "start_ts=%d, nbins=%d" % (self.start_ts, self.nbins)

    def bin_nbr(self, ts):
        bn = int((ts-self.start_ts - 1)/TimeBins.SampleInterval)
        return bn

    def bin_end_time(self, bn):
        return self.start_ts + bn*TimeBins.SampleInterval

    def bin_py_time(self, bn):
        bn_ts = self.start_ts + bn*TimeBins.SampleInterval
        t_loc = datetime.datetime.utcfromtimestamp(bn_ts)
        return timezone('UTC').localize(t_loc)
    

if __name__ == "__main__":  # Running as main()
    start_dt = "2012-05-01T00"
    end_dt = "2012-05-02T00"
    tb= TimeBins(start_dt, end_dt)
    for bn in range(0, 49):
        print("%3d: %s %s" % (bn, tb.bin_py_time(bn), tb.bin_py_time(bn).tzinfo))
