# 1546, Thu 11 Feb 2021 (NZDT)
#
# md-table.py:  Make markdown tables from msm-performance.txt
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

def centre_txt(text, width, bold):    
    ns = int((width-len(text))/2)
    #print("ct: %s (%d) %d -> %s" % (text, len(text), width, ns))
    write_spaces(c_spaces[ns]);
    if bold:
        mdf.write("**%s**" % text)
    else:
        mdf.write(text)

txt_hdr1 = line = sf.readline()  # Ignore first 2 lines
txt_hdr2 = line = sf.readline()  #   (performance file hdr)
ln = -1
table_id = False
for line in sf:  # Loop to make tables
    ln += 1
    #print("%2d (%2d) >%s<" % (ln, len(line), line))

    if len(line) > 1:  # Not an empty "end of table" line
        label = line[0:15]
        #print("%s (%d) >%s<" % (line, len(line), label))
        la = line.split()
        if label == " "*15:  # msm_ or ymd_ md headers
            if la[0] == la[1] and not table_id:  # Write md table format
                table_id = la[0]
                mdf.write("| ----: |")
                n_cols = len(la)
                for n in range(0,n_cols):
                    mdf.write(" :---- |")
            else:  # Write md table header
                mdf.write("|")             
                centre_txt(table_id, 15, True)
                mdf.write(" &emsp;|")             
                for n in range(0,n_cols):  # msm_id col headings
                    centre_txt(la[n], 15, True)
                    mdf.write("|")
                    v_space = "<p style=\"font-size: 5pt\">  </p>"
                        # Spacer between ymd blocks
            mdf.write("\n")
        else:
            label = line[0:15]
            ymd_table = table_id[0:2] == "20"
            ltxt = label.split()[0]
            
            if ltxt != "destination":
                reqd = True
            else:
                reqd = not ymd_table
            #print("label >%s<, ltxt >%s<, ymd_table %s, reqd %s" % (
            #    label, ltxt, ymd_table, reqd))
            if reqd:
                ls = line[15:].split()
                mdf.write("| %s &emsp;|" % label)
                for v in ls:
                    if not ":" in v:
                        centre_txt(v, 15, False)
                    else:
                        mean, iqr = v.split(":")
                        add_spaces(mean)
                        mdf.write("%s&thinsp;&#124;&thinsp;%s" % (mean, iqr))
                        add_spaces(iqr)
                    mdf.write("|")
                mdf.write("\n")
    else:  # Empty input line
        mdf.write("\n")
        mdf.write("%s\n" % v_space)  # 5pt vertical spacer
        table_id = False  # Ready for next table

mdf.write("\n")  # Empty line to end table

def emspaces(n):
    for n in range(0,n):  # Centre the table's label line
        mdf.write("&emsp;")

if not n_cols == 4: 
    emspaces(14)
    mdf.write("**Table 1: Trace statistics for 6 Destinations on 12 Nov 2019 (UTC)**\n ")
else:
    emspaces(8)
    mdf.write("**Table 2: Four-year Trace statistics for 4 Destinations**\n ")
mdf.write("\n")

sf.close()

mdf.close()

ofna = out_fn.split(".")
html_fn = ("%s.html" % ofna[0])
print("html filename = %s" % html_fn)
#c.run_bash_commands("pandoc -f markdown %s > %s" % (out_fn, html_fn))
c.run_bash_commands("markdown -f footnote -o %s %s" % (html_fn, out_fn))
