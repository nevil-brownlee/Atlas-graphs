# 1546, Thu 11 Feb 2021 (NZDT)
#
# svg-table.py:  Make SVG tables from msm-performance.txt
#
# Copyright 2021, Nevil Brownlee,  U Auckland | RIPE NCC

import sys, svgwrite

import config as c  # For run_bash_commands

if len(sys.argv) == 1:
    print("Expected input filename as first parameter!")
    exit()
in_fn = sys.argv[1]
print("Will read file %s" % in_fn)

ifa = in_fn.split("performance")
if len(ifa) != 2:
    print("Input filename didn't contain \"performance\"!")
    exit()
nfa = ifa[1].split("txt")
print("nfa %s" % nfa)
svg_fn = "table%ssvg" % nfa[0]
t_cols = int(nfa[0][1])
print("Will write output to %s, %d data colums" % (svg_fn, t_cols))

sf = open(in_fn, "r", encoding='utf-8')  # Fail if not present

class table:
    def __init__(self, svg_filename, font_size, # px
            c0_chars, n_cols, c_chars):  # chars
        self.n_cols = n_cols
        self.border = 2
        self.font_height = font_size  # px
        self.font_width = font_size*0.3  #0.6
        self.xmargin = font_size/10.0  # Margin either side of text
        self.tmargin = self.xmargin*3  # Margin above text
        self.bmargin = self.xmargin*6  # Margin below text
        self.row_height = self.tmargin + self.font_height*0.7 + self.bmargin
        self.bottom = self.top = self.border
        self.dwg = svgwrite.Drawing(filename=svg_filename,
            profile='tiny', version='1.2', font_family='serif')
        co = 10  # centre offset px
        cm = 1.5  # Multiplier for char widths
        c0_chars *= cm;  c_chars *= cm
        self.col_centres = [self.border + co + int(c0_chars*self.font_width)]
        co += c0_chars*self.font_width + 24
        col_px = int((c_chars+2)*self.font_width)
        for cn in range(1,n_cols+1):
             self.col_centres.append(int(co+col_px/2))
             co += col_px
        print("col_centres %s" % self.col_centres)
        self.width_6 = int(self.col_centres[0] + 6*col_px + col_px/2) + 10
        self.width = int(self.col_centres[n_cols] + col_px/2) + 10
        print("width_6 = %d, width = %d" % (self.width_6, self.width))

    def save(self):
        self.dwg.viewbox(0,0, self.width_6,int(self.bottom+8))
        self.dwg.save()

    def draw_text(self, weight, text,  align, cx):
        self.dwg.add(self.dwg.text("%s" % text, font_weight=weight,
            font_size=self.font_height, text_anchor=align,
            insert=(cx, int(self.bottom)) ))  # Bottom edge of text!

    def draw_frame(self):
        self.bottom += int(self.row_height*0.4)
        self.dwg.add(self.dwg.rect(
            size=(self.width+9, self.bottom),
            insert=(self.border, self.top),
            stroke='black', fill="none", stroke_width=1))

    def row(self, weight, row_hdr, row_contents):
        self.bottom += self.row_height
        self.draw_text(weight, row_hdr, "end", self.col_centres[0])
        if not ":" in row_contents[0]:
            for cn in range(0,self.n_cols):                
                self.draw_text(weight, row_contents[cn],
                    "middle", self.col_centres[cn+1])
        else:
            for cn in range(0,self.n_cols):                
                mean,iqr = row_contents[cn].split(":")
                #print("cn %s; mean %s, iqr %s" % (cn, mean, iqr))
                self.draw_text(weight, mean, "end",  self.col_centres[cn+1]-5)
                self.draw_text(weight, "|", "middle",  self.col_centres[cn+1])
                self.draw_text(weight, iqr, "start",  self.col_centres[cn+1]+5)
        return

    def tbl_space(self):
        self.bottom += int(self.row_height*0.4)
        self.dwg.add(self.dwg.line(start=(self.border, self.bottom+4),
            end=(self.width+11, self.bottom+4), 
            stroke='black', stroke_width=1))
        self.bottom += int(self.font_height*0.6)

st = table(svg_fn, 12, 19, t_cols, 15)  #  font_size, c0_chars,n_cols,c_chars
#st.draw_caption("bold", t_caption)

ln = -1
table_id = False
next_line = None
while True:  # Loop to make tables
    if next_line:
        line = next_line;  next_line = None
    else:
        line = sf.readline()
        ln += 1
    line = line.rstrip()
    #print("%3d: %s" % (ln, line))
    if ln < 2:
        continue  # Ignore first two lines
    
    if len(line) > 1:  # Not an empty "end of table" line
        label = line[0:15]
        la = line.split()
        
        if label == " "*15:  # msm_ or ymd_  header lines
            if la[0] == la[1] and not table_id:  # Write md table format
                table_id = la[0]
                n_cols = len(la)
            else:  # Write table header
                st.row("bold", table_id, la)
        else:
            label = line[0:15]
            ymd_table = table_id[0:2] == "20"
            ltxt = label.split()[0]
            
            if ltxt != "destination":
                reqd = True
            else:
                reqd = not ymd_table
            if reqd:
                ls = line[15:].split()
                st.row("normal", label, ls)
    else:  # Empty input line
        next_line = sf.readline()
        if len(next_line) == 0:
            break
        st.tbl_space()
        table_id = False  # Ready for next table

st.draw_frame()
st.save()

def run_cmd(cmd):
    output, rc = c.run_bash_commands(cmd)
    if rc != 0:
        print(output)
    return rc

rt = run_cmd("python3 tweak-svg-headers.py %s" % svg_fn)
if rt != 0:
    print(">>>>> tweak run failed!");  exit()
