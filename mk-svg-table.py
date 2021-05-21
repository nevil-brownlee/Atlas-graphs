# 1715, Sun 4 Feb 2021 (NZDT)
#
# mk-svg-table.py  # Explore making msm-performance tables

import svgwrite

class table:
    def __init__(self, svg_filename, lines, font_size):
        self.font_height = font_size  # px
        self.font_width = font_size*0.3  #0.6
        self.xmargin = font_size/10.0  # Margin either side of text
        self.tmargin = self.xmargin*3  # Margin above text
        self.bmargin = self.xmargin*6  # Margin below text
        #self.cell_width = 2*self.xmargin + 2*self.font_width  # cols 0..31
        #self.cell_height = self.tmargin + self.font_height + self.bmargin
        width = (18+6*15)*self.font_width  # 32*self.cell_width;  
        height = 5*self.font_height  # (lines+1)*self.cell_height
        self.dwg = svgwrite.Drawing(filename=svg_filename,
            profile='tiny', version='1.2', font_family='serif'
            )size=(width, height))
        self.dwg.viewbox(0,0, width,height)
    
    #def col_centre(self, x):
    #    return x*self.cell_width + self.cell_width/2.0

    def heading(self, hw, cw, t_hdr, col_hdrs):
        hy = self.tmargin + self.font_height

        self.dwg.add(self.dwg.text("%s" % t_hdr, font_weight="bold",
            font_size=self.font_height*0.8, text_anchor="middle",
            insert=(10*self.font_width, hy) ))  # Start at x=0

        cols_x = (hw+12)*self.font_width
        col_width = cw*self.font_width
        for n,ch in enumerate(col_hdrs):
            self.dwg.add(self.dwg.text("%s" % ch, #font_family=self.family,
                font_size=self.font_height*0.8, text_anchor="middle",
                insert=(cols_x + n*col_width, hy)))
        self.top = hy + self.bmargin
        self.last_row = 0

#t = svgwrite.text.Text("destination")
#print("t.attrib = %s (%d)" % (t.text, len(t.text)))  # length in characters
#print("Tspan destination length = %d" % t.textlength)


pl = table("test_p1.svg", 7, 20)  # 7 lines, Font height 20px

pl.heading(18, 15,  # Header width, col width (chars)
    "20191211", [5017, 5004, 5005, 5006, 5016, 5015])

pl.dwg.save()
