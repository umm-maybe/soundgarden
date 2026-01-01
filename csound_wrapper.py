# Colby's CSound Python wrapper
# Implements simple sample playback according to a 16-step sequence with conditional triggers
# 

import sys, os
import networkx as nx
import random
import subprocess
import yaml

class sound_graph:
    def __init__(self, sound_file=None, tempo=None, subsounds=None, transitions=None):
        # the sound_file is the path to the actual WAV or other sound source file
        # subsounds must be a list of tuples where the second item in the tuple is a dictionary
        # each dictionary contains the parameters of the CSound "note", mainly inskip and pitch ratio
        # [(1, {"inskip": 1, "duration": 1, "pitch": 1})]
        self.G = nx.DiGraph()
        self.G.add_nodes_from(subsounds)
        # transitions is an "ebunch", i.e. an iterable container of edge-tuples
        # An edge-tuple can be a 2-tuple of nodes or a 3-tuple with 2 nodes followed by an edge attribute dictionary, 
        # e.g., (2, 3, {'weight': 3.1415, 'duration': 2}).
        self.G.add_edges_from(transitions)
        self.tempo = tempo
        self.instrument = f"""
sr     = 44100
ksmps  = 32
nchnls = 2
0dbfs  = 1

instr 1

a1  diskin "{self.sound_file}", p4, p5
    outs a1, a1

endin
"""
    def render_score(self, starting_node=1, beats=16, audio_file="temp.wav", score_file="temp.csd"):
        last_subsound = starting_node
        # the score_array is a table to which we're appending sound events
        score_array = []
        last_beat = 0
        pitches = self.G.data('pitch')
        durations = self.G.data('duration')
        inskips = self.G.data('inskip')
        while last_beat < beats:
            duration_beats = durations[last_subsound]
            score_array.append({
                'start_beat': last_beat,
                'duration_beats': duration_beats,
                'pitch_ratio': pitches[last_subsound],
                'skip_time': inskips[last_subsound]
            })
            # iterate over the outbound edges and select one in proportion to weight
            sum_weight = {}
            sum_weights = 0
            for subsound_id, datadict in self.G.adj[last_subsound].items():
                sum_weights += outbound_weights[subsound_id]
                sum_weight[subsound_id] = sum_weights
            r = random.random() * sum_weights
            for next_subsound in outbound_weights.keys():
                if r < sum_weight[next_subsound]:
                    break
            last_beat += duration_beats
            last_subsound = next_subsound
        with open(filename, 'w') as f:
            f.write('<CsoundSynthesizer>\n')
            f.write('<CsOptions>\n')
            f.write(f'-o {audio_file} -W\n')
            f.write('</CsOptions>\n')
            f.write('<CsInstruments>\n')
            f.write(self.instrument)
            f.write('</CsInstruments>\n')
            f.write('<CsScore>\n')
            f.write(f't {self.tempo}')
            for s in score_array:
                f.write('i1\t{start_beat}\t{duration_beats}\t{pitch_ratio}\t{skip_time}\n'.format(**s))
                # Syntax
                # i  p1  p2  p3  p4  p5
                # Initialization
                # p1 -- Instrument number
                # p2 -- Starting time (in beats).
                # p3 -- Duration time (in beats).
                # p4 -- Pitch (playback speed ratio).
                # p5 -- Initial skip time (in seconds)
            f.write('e\n')
            f.write('</CsScore>\n')
            f.write('</CsoundSynthesizer>\n')
        # Actually run CSound
        subprocess.run(['csound',score_file])



if __name__ == '__main__':
    config_file = sys.argv[1]
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    subsounds = []
    for event in config['events']:
        subsounds.append((event['id'], {'inskip': event['inskip'], 'pitch': event['pitch']}))
    transitions = []
    from_id = 1
    for transition_map in config['transitions']:
        for to_id in transition_map:
            transitions.append()
    sg = sound_graph()
