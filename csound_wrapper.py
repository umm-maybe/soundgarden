# Colby's CSound Python wrapper
# Implements sample playback using Markov chains
# Recoded to use NumPy instead of NetworkX

import sys
import os
import numpy as np
import random
import subprocess
import yaml
import wave

def simple_ratio():
    simple_numbers = [1,2,3]
    # choose two numbers at random without replacement
    x = random.sample(simple_numbers,2)
    y = x[0]/x[1]
    return(y)

def new_inskip(file_length):
    index = random.randrange(16) # select random 16th note to start on
    slack = 16-index # this is the amount of beats left until end
    beats = random.randrange(slack)/4 # convert to quarter notes
    inskip = file_length*index/16
    return inskip, beats

def get_duration(wav_path):
    with wave.open(wav_path, 'r') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duration = frames / float(rate)
        return(duration)

class sound_graph:
    def __init__(self, sound_file=None, tempo=None, subsounds=None, transitions=None):
        # the sound_file is the path to the actual WAV or other sound source file
        # subsounds must be a list of tuples where the second item in the tuple is a dictionary
        # each dictionary contains the parameters of the CSound "note", mainly inskip and pitch ratio
        
        # Store node attributes in a dictionary indexed by node ID
        self.nodes = {}
        for node_id, attrs in subsounds:
            self.nodes[node_id] = attrs
        
        # Create transition matrix
        # Find the maximum node ID to size the matrix
        max_node = max(node_id for node_id, _ in subsounds)
        self.num_nodes = max_node
        
        # Initialize transition matrix (adjacency matrix with weights)
        self.transition_matrix = np.zeros((max_node, max_node))
        
        # Fill in the transition weights
        # transitions is an "ebunch", i.e. an iterable container of edge-tuples
        # An edge-tuple can be a 2-tuple of nodes or a 3-tuple with 2 nodes followed by an edge attribute dictionary
        for edge in transitions:
            if len(edge) == 3:
                from_node, to_node, attrs = edge
                weight = attrs.get('weight', 1.0)
            else:
                from_node, to_node = edge
                weight = 1.0
            
            # Convert to 0-indexed for numpy array
            self.transition_matrix[from_node - 1, to_node - 1] = weight
        
        self.audio_length = get_duration(sound_file)
        self.tempo = tempo
        self.instrument = f"""
sr     = 44100
ksmps  = 32
nchnls = 2
0dbfs  = 1

instr 1

a1, a2  diskin "{sound_file}", p4, p5
    outs a1, a2

endin
"""

    def render_score(self, starting_node=1, beats=16, audio_file="temp.wav", score_file="temp.csd"):
        last_subsound = starting_node
        # the score_array is a table to which we're appending sound events
        score_array = []
        last_beat = 0
        
        while last_beat < beats:
            duration_beats = self.nodes[last_subsound]['duration']
            score_array.append({
                'start_beat': last_beat,
                'duration_beats': duration_beats,
                'pitch_ratio': self.nodes[last_subsound]['pitch'],
                'skip_time': self.nodes[last_subsound]['inskip']
            })
            
            # Get the transition weights for the current node (0-indexed)
            weights = self.transition_matrix[last_subsound - 1, :]
            
            # Get non-zero weights (valid transitions)
            valid_transitions = np.where(weights > 0)[0]
            
            if len(valid_transitions) == 0:
                # No valid transitions, break
                break
            
            # Get the weights for valid transitions
            transition_weights = weights[valid_transitions]
            
            # Normalize to probabilities
            probabilities = transition_weights / np.sum(transition_weights)
            
            # Select next node based on weighted probabilities
            next_subsound_idx = np.random.choice(valid_transitions, p=probabilities)
            next_subsound = next_subsound_idx + 1  # Convert back to 1-indexed
            
            last_beat += duration_beats
            last_subsound = next_subsound
        
        with open(score_file, 'w') as f:
            f.write('<CsoundSynthesizer>\n')
            f.write('<CsOptions>\n')
            f.write(f'-o {audio_file} -W\n')
            f.write('</CsOptions>\n')
            f.write('<CsInstruments>\n')
            f.write(self.instrument)
            f.write('</CsInstruments>\n')
            f.write('<CsScore>\n')
            f.write(f't 0 {self.tempo}\n')
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
        subprocess.run(['csound', score_file])
    def mutate_eges(self,mutation_probability):
        for row in self.transition_matrix:
            for col in row:
                if random.random() < mutation_probability:
                    self.transition_matrix[row,col] = self.transition_matrix[row,col]*simple_ratio()
    def create_edges(self):
        for row in self.transition_matrix:
            for col in row:
                self.transition_matrix[row,col] = simple_ratio()
    def mutate_nodes(self,mutation_probability):
        for node_id in self.nodes.keys():
            node_attrs = self.nodes[node_id]
            if random.random() < mutation_probability:
                mutation = random.choice(['skipdur','pitch'])
                if mutation == 'skipdur':
                    # choose a different 16th note beat and duration
                    inskip, duration = new_inskip(self.audio_length)
                    node_attrs['inskip'] = inskip
                    node_attrs['duration'] = duration
                else: # mutation == 'pitch'
                    # adjust the pitch (playback speed)
                    node_attrs['pitch'] = node_attrs['pitch']*simple_ratio()
            self.nodes[node_id] = node_attrs
    def create_nodes(self):
        for node_id in range(len(self.nodes)):
            node_attrs = {}
            inskip, duration = new_inskip(self.audio_length)
            node_attrs['inskip'] = inskip
            node_attrs['duration'] = duration
            node_attrs['pitch'] = random.randrange(1,4,1)/random.randrange(1,4,1)

if __name__ == '__main__':
    config_file = sys.argv[1]
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    edges = []
    from_id = 1
    for transition_map in config['transitions']:
        for to_id in transition_map:
            edges.append((from_id, to_id, {'weight': transition_map[to_id]}))
        from_id += 1
    
    nodes = []
    node_id = 1
    for event in config['events']:
        nodes.append((node_id, event))
        node_id += 1
    
    sg = sound_graph(
        sound_file=config['audio'],
        tempo=config['tempo'],
        subsounds=nodes,
        transitions=edges
    )
    sg.render_score()