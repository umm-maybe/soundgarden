# Colby's CSound Python wrapper
# Implements simple sample playback according to a 16-step sequence with conditional triggers
# 

import sys, os

sample_file = sys.argv[1]

instrument = f"""
sr     = 44100
ksmps  = 32
nchnls = 2
0dbfs  = 1

instr 1

a1     diskin "{sample_file}", p4, p5
       outs a1, a1

endin
"""

# Syntax
# i  p1  p2  p3  p4  p5
# Initialization
# p1 -- Instrument number
# p2 -- Starting time (in beats).
# p3 -- Duration time (in beats).
# p4 -- Pitch (playback speed ratio).
# p5 -- Initial skip time (in seconds)