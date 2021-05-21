# 1450, Sun  y Feb 2021 (NZDT)
#
# md-table.py:  Make markdown table from msm-performance.txt
#
# Copyright 2021, Nevil Brownlee,  U Auckland | RIPE NCC

import sys

import config as c  # For run_bash_commands

if len(sys.argv) == 1:
    print("Expected input filename as first parameter!")
    exit()
in_fn = sys.argv[1]
print("Will read file %s" % in_fn)
sf = open(in_fn, "r", encoding='utf-8')  # Fail if not present

ifa = in_fn.split("performance")
if len(ifa) != 2:
    print("Input filename didn't contain \"performance\"!")
    exit()
nfa = ifa[1].split("txt")
out_fn = "table%smd" % nfa[0]
print("Will write output to %s" % out_fn)

mdf = open(out_fn, "w", encoding='utf-8')

def write_spaces(n):
    for j in range(0,n):
        mdf.write("&thinsp;")
        #mdf.write("+")
        #mdf.write("&#124;")  # |

#             0,  1,   2,  3,  4,  5,  6,  7, 8, 9
c_spaces =   [15, 13,  9,  8, 16, 16, 19, 22, 1, 0]  # For centre_txt
bar_spaces = [ 0, 18, 15, 12,  9,  5,  2,  1, 1, 0]  # For mean|iqr

def add_spaces(txt):
    #print(">%s< %d > %d" % (txt, len(txt), reqd_spaces[len(txt)]))
    write_spaces(bar_spaces[len(txt)])

def centre_txt(text, width):    
    ns = int((width-len(text))/2)
    print("ct: %s (%d) %d -> %s" % (text, len(text), width, ns))
    #write_spaces(ns);  mdf.write(text);  write_spaces(ns)
    write_spaces(c_spaces[ns]);  mdf.write(text)

ln = 0
for line in sf:
    if ln > 0 and len(line) != 1:  # Ignore header and empty lines
        line = line.strip()
        print("%s (%d, %d)" % (line, ln, len(line)))
        if ln == 2:  # msm_id headers line
            mdf.write("| ----: |")
            la = line.split()
            print("la %s" % la)
            n_cols = len(la)
            #print("n_cols %d, la >%s<" % (n_cols, la))
            for n in range(0,n_cols):
                mdf.write(" :---- |")
            mdf.write("\n")

            #mdf.write("|");  write_spaces(15);  mdf.write("|")
            mdf.write("| |")
            for n in range(0,n_cols):  # msm_id col headings
                #mdf.write(" %s |" % la[n])
                mdf.write("**")
                centre_txt(la[n], 15)
                mdf.write("**")
                mdf.write("|")
            mdf.write("\n")
        else:
            label = line[:15]  # Row header
            ls = line[15:].split()
            mdf.write("| %s &emsp;|" % label)
            for v in ls:
                if not ":" in v:
                    centre_txt(v, 15)  #40)
                else:
                    mean, iqr = v.split(":")
                    add_spaces(mean)
                    mdf.write("%s&thinsp;&#124;&thinsp;%s" % (mean, iqr))
                    add_spaces(iqr)
                mdf.write("|")
            mdf.write("\n")
        #if ln == 6:
        #    break
            #print("ln_out >%s< (%s)" % (ln_out, type(ln_out)))
    ln += 1
mdf.write("\n")  # Empty line to end table
for n in range(0,19):
    mdf.write("&emsp;")
mdf.write("**Table 1: Trace statistics for 12 Nov 2019 (UTC)**\n ")
mdf.write("\n")
sf.close()

mdf.close()

html_fn = out_fn.replace("md","html")
c.run_bash_commands("pandoc -f markdown %s > %s" % (out_fn, html_fn))

