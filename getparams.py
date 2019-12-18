# 1608, Wed 28 Feb 2018 (NZDT)
# 1355, Sun 12 Nov 2017 (SGT)
# 0935, Fri 27 Oct 2017 (NZST)
#
# getparams.py:  get Atlas trace parameters from command line or params.txt,
#                save their 'last-used' values in params.txt
#
# Copyright 2017, Nevil Brownlee,  U Auckland | RIPE NCC

import getopt, sys, os

class AgParams:  # Atlas graph Parameters
    def usage(self):
        print("Atlas graph options:")
        print("  -y or --start_ymd   str  e.g. 20170220")
        print("  -h or --start_hhmm  str  e.g. 0000")
        print("  -n or --n_bins      int  e.g. 48")
        print("  -d or --n_days      int  e.g. 7\n")
        print("  -m or --msm_id      int  e.g. 5005")
        print("  -f or --full_graphs T/F  e.g. True")
        print("  -s or --write_stats T/F  e.g. False")

    def save_params(self):
        pf = open(self.params_fn, "w")
        pf.write("start_ymd = %s\n" % self.start_ymd)
        pf.write("start_hhmm = %s\n" % self.start_hhmm)
        pf.write("n_bins = %d\n" % self.n_bins)
        pf.write("n_days = %d\n" % self.n_days)
        pf.write("msm_id = %d\n" % self.msm_id)
        pf.write("full_graphs = %s\n" % self.full_graphs)
        pf.write("write_stats = %s\n" % self.write_stats)
        pf.close()

    def __init__(self, dir):
        self.params_fn = dir + "/params.txt"
        print("self.params_fn = %s" % self.params_fn)
        try:
            opts, args = getopt.gnu_getopt(sys.argv[1:], "y:h:n:d:m:f:s:r:",
                # gnu handling stops parse at first non-matching arg,
                #   or first arg starting with '+'
                ["start_ymd=", "start_hhmm=", "n_bins=", "n_days=",
                 "msm_nbr=",
                 "full_graphs=", "write_stats=",
                 "help"])
        except getopt.GetoptError as err:
            # print help information and exit:
            print(str(err))  # will print something like "option -a not recognized"
            sa = str(err).split()
            self.usage()
            sys.exit(2)

        self.start_ymd = self.start_hhmm = \
            self.msm_id = self.n_bins = self.n_days = \
            self.write_stats = None

        if os.path.isfile(self.params_fn):
            pf = open(self.params_fn, "r")  # Read last-use param values
            for line in pf:
                la = line.strip().split()
                if la[0] == "start_ymd":
                    self.start_ymd = la[2]
                elif la[0] == "start_hhmm":
                    self.start_hhmm = la[2]
                elif la[0] == "n_bins":
                    self.n_bins = int(la[2])
                elif la[0] == "n_days":
                    self.n_days = int(la[2])
                elif la[0] == "msm_id":
                    self.msm_id = int(la[2])
                elif la[0] == "full_graphs":
                    self.full_graphs = la[2][0] == "T"
                elif la[0] == "write_stats":
                    self.write_stats = la[2][0] == "T"
                else:
                    print("Failed to parse file %s <<<" % self.params_fn)
                    exit()
        else:
            print("No params.txt file, using default values")
            self.start_ymd = "20171023";  self.start_hhmm = "0000"
            self.n_bins = 48;  self.n_days = 7;
            self.msm_id = 5005;  self.full_graphs = True
            self.write_stats = False
            
        for o, a in opts:
            #print("o >%s<, a >%s<" % (o,a))
            if o in ("-y", "--start_ymd"):
                self.start_ymd = a
            elif o in ( "-h", "--start_hhmm"):
                self.start_hhmm = a
            elif o in ("-n", "--n_bins"):
                self.n_bins = int(a)
            elif o in ("-d", "--n_days"):
                self.n_days = int(a)
            elif o in ("-m", "--msm_id"):
                self.msm_id = int(a)
            elif o in ("-f", "--full_graphs"):
                self.full_graphs = a[0] == "T"
            elif o in ("-s", "--write_stats"):
                self.write_stats = a[0] == "T"
            else:  # Option --help or 'not recognised'
                self.usage();  exit()
        self.save_params()

        self.rem_cpx = 0  # Index of first +param in sys.argv
        for x,p in enumerate(sys.argv):
            if p[0] == '+':
                self.rem_cpx = x;  break

    def param_values(self):
        return (self.start_ymd, self.start_hhmm, \
            self.msm_id, self.n_bins, self.n_days, \
            self.full_graphs, self.write_stats, \
            self.rem_cpx)

if __name__ == "__main__":
    agp = AgParams(".")
    print("ymd=%s, hhmm=%s, n_bins=%d, n_days=%d, msm_id=%d, full=%s, statf=%s" % (
        agp.start_ymd, agp.start_hhmm, agp.n_bins, agp.n_days, agp.msm_id,
        agp.full_graphs, agp.write_stats))
