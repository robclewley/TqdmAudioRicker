"""Some ideas from https://github.com/sparida/Score-Creator
"""
import numpy as np
from math import pi, sin, floor
from fractions import gcd

SAMPLE_RATE = 44100 # 11250 # Overall sampling rate
TOTAL_WHOLE_NOTES = 16 # Maximum length of a music score
TOTAL_EIGHTH_NOTES = TOTAL_WHOLE_NOTES * 8 # Maximum number of eigth notes in a music score

# Note characters without specific octyav number
octave1Notes       = [ "C"  , "Db" , "D"  , "Eb" , "E"  , "F"  , "Gb"  , "G"  , "Ab" , "A"  , "Bb" , "B" ]
# Note frequencies for the first octave
octave1Frequencies = [ 32.70, 34.65, 36.71, 38.89, 41.20, 43.65,  46.25, 49.00, 51.91, 55.00, 58.27, 61.74 ]
# Dictionary of the two lists above
octave1Dict        = dict(zip(octave1Notes, octave1Frequencies))


# Note Lengths (Total number of 8th notes in each note type)
WHOLE_NOTE   = 8
HALF_NOTE    = 4
QUARTER_NOTE = 2
EIGHTH_NOTE  = 1 # Smallest possible note length

# close encounters
ce_sequence = [('G', 4, EIGHTH_NOTE), ('A', 4, EIGHTH_NOTE), ('F', 4, EIGHTH_NOTE),
               ('F', 3, EIGHTH_NOTE), ('C', 4, QUARTER_NOTE)]

def make_sinewave(freq, eighth_duration, value, framerate):
    t = np.linspace(0, eighth_duration*value,
                    int(framerate*eighth_duration*value))
    # fade in and out settings for chunks, so no click
    qtr_t_ix = int(len(t)/4)
    qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
    mid_fac = np.ones(len(t)-2*qtr_t_ix)
    envelope = np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0)
    return np.sin(2*np.pi*freq*t) * envelope #* self.volume

def sequence_spec_to_wav(seq_spec, eighth_value, framerate):
    seq = []
    for note, octave, dur in seq_spec:
        f = getNoteFrequency(note, octave)
        seq.append(make_sinewave(f, eighth_value, dur, framerate))
        if dur > 1:
            # no new 8th notes in sequence during play of this note
            seq.extend([None]*(dur-1))
    return seq, len(seq)

# Convert time in millisecs to number of samples needed to fill that duration
def convertTimeToSampleCount(time):
    return int(time / (1000.0/SAMPLE_RATE))

# Return the duration of an eigth note in secs
def getDurationOf8thNote(tempo):
    return 30.0/tempo

# Return the frequency of a note based on note character and octave number
# Works on the principle that frequency of the same note character an octave
#   higher is twice that of the current octave
# Example : Frequency of C2 = 2 x Frequency of C1
def getNoteFrequency(noteChar, octave):
    baseFrequency        = octave1Dict[noteChar]
    octaveBasedFrequency = baseFrequency * ( 2**(octave - 1) )
    return octaveBasedFrequency


# Takes the note character, current octave and the number of halfsteps and returns the pitch changed note data
# HalfSteps: +ve = Pitch Up, -ve = Pitch Down
def getPitchChangedData(noteChar, octave, halfSteps):

    octaveChange   = floor(float(halfSteps) / 12.0)
    noteTypeChange = halfSteps % 12

    newOctave = octave + octaveChange
    newChar   = octave1Notes[octave1Notes.index(noteChar) + noteTypeChange]

    return(newChar, newOctave)