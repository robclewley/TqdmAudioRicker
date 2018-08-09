"""Some ideas from https://github.com/sparida/Score-Creator
"""
import numpy as np
from math import pi, sin, floor
from fractions import gcd
try:
    import mido
except ImportError:
    mido = None
import io
from requests import get

def fetch_resource(name):
    """
    name is either a local file path or an http resource URL.
    """
    if name.startswith('https://') or name.startswith('http://'):
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
           'Accept-Encoding': 'none',
           'Accept-Language': 'en-US,en;q=0.8',
           'Connection': 'keep-alive'}
        data = get(name, headers=hdr).content
        return io.BytesIO(data)
    else:
        with open(name, 'rb') as f:
            return f.read()

# SAMPLE_RATE = 44100 # 11250 # Overall sampling rate

# Note characters without specific octyav number
octave1Notes       = [ "C"  , "Db" , "D"  , "Eb" , "E"  , "F"  , "Gb"  , "G"  , "Ab" , "A"  , "Bb" , "B" ]
# Note frequencies for the first octave
octave1Frequencies = [ 32.70, 34.65, 36.71, 38.89, 41.20, 43.65,  46.25, 49.00, 51.91, 55.00, 58.27, 61.74 ]
octave1Dict = dict(zip(octave1Notes, octave1Frequencies))

# Note Lengths (Total number of 8th notes in each note type)
WHOLE_NOTE   = 8
HALF_NOTE    = 4
QUARTER_NOTE = 2
EIGHTH_NOTE  = 1

# close encounters of the tqdm kind
ce_sequence = [(('G', 4), EIGHTH_NOTE), (('A', 4), EIGHTH_NOTE), (('F', 4), EIGHTH_NOTE),
               (('F', 3), EIGHTH_NOTE), (('C', 4), QUARTER_NOTE), (('', 0), QUARTER_NOTE)]

def make_sinewave(freq, eighth_duration, value, framerate, volume=0.5,
                  envelope=None):
    t = np.linspace(0, eighth_duration*value,
                    int(framerate*eighth_duration*value))
    # fade in and out settings for chunks, so no click
    if envelope is None:
        qtr_t_ix = int(len(t)/4)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(len(t)-2*qtr_t_ix)
        envelope = np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0)
    return np.sin(2*np.pi*freq*t) * envelope * volume

def make_sawtoothwave(freq, eighth_duration, value, framerate, volume=0.5,
                      envelope=None):
    singleCycleLength = framerate / float(freq)
    omega = np.pi * 2 / singleCycleLength
    phaseArray = np.arange(0, int(singleCycleLength)) * omega
    piInverse = 1/np.pi
    saw = np.vectorize(lambda x: 1 - piInverse * x)
    singleCycle = saw(phaseArray)
    data = np.resize(singleCycle, (int(eighth_duration*value*framerate),)).astype(np.float)
    if envelope is None:
        qtr_t_ix = int(len(data)/4)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(len(data)-2*qtr_t_ix)
        envelope = np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0)
    return data * envelope * volume

def make_squarewave(freq, eighth_duration, value, framerate, volume=0.5,
                    envelope=None):
    data = np.sign(make_sinewave(freq, eighth_duration, value, framerate, volume, 1))
    # sine wave envelope lost in sign()
    if envelope is None:
        qtr_t_ix = int(len(data)/4)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(len(data)-2*qtr_t_ix)
        envelope = np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0)
    return data * envelope


syn_kinds = {'sine': make_sinewave,
             'saw': make_sawtoothwave,
             'square': make_squarewave
             }

def sequence_spec_to_wav(seq_spec, eighth_value, framerate, wav_kind, volume=0.5):
    # volume doesn't work yet because ipython's audio system currently renormalizes all the waves
    # to full amplitude.
    seq = []
    for tone, dur in seq_spec:
        if dur == 0:
            continue
        try:
            note, octave = tone
        except:
            f = tone # given directly
        else:
            if note == '':
                f = None
            else:
                f = get_note_frequency(note, octave)
        if f is None:
            seq.extend([None]*dur) # rest
        else:
            seq.append(syn_kinds[wav_kind](f, eighth_value, dur, framerate, volume))
        if dur > 1:
            # no new "8th" notes in sequence during play of this note
            seq.extend([None]*(dur-1))
    return seq, len(seq)


def get_note_frequency(note_char, octave):
    """
    Return the frequency of a note based on note character and octave number
    Works on the principle that frequency of the same note character an octave
      higher is twice that of the current octave
    Example : Frequency of C2 = 2 x Frequency of C1
    """
    baseFrequency = octave1Dict[note_char]
    octaveBasedFrequency = baseFrequency * ( 2**(octave - 1) )
    return octaveBasedFrequency

def get_note_from_midi(midi, channel=None, smallest_duration=None):
    """
    Convert monophonic data from a .mid file to a TqdmAudioRicker-compatible format!
    This is experimental and very hacky.

    Either pass a filename string as `midi` or an open file / stream handle.

    Requires mido to be installed (`pip install mido`)

    If channel=None, all channels are read.

    If smallest_duration is None (default), the smallest time duration
    of a non-zero velocity note message found will be used as a base.

    Assumes no chords in same channel.

    Assumes midi note on usage where the on message with velocity > 0 has time 0
    and is repeated right after for the same note with 0 velocity but time > 0.
    """
    if mido is not None:
        freqs = []
        durs = []
        in_note = 0
        dur_note = 0
        if isinstance(midi, str):
            iterator = mido.MidiFile(filename=midi)
        else:
            iterator = mido.MidiFile(file=midi)
        for i, x in enumerate(iterator):
            if x.is_meta or x.is_realtime:
                continue
            if channel is not None:
                try:
                    if x.channel != channel:
                        continue
                except AttributeError:
                    continue
            if x.type == 'note_on':
                if x.velocity > 0:
                    if in_note > 0:
                        # there's another note i.e. a chord
                        if x.time == 0:
                            # ignore it
                            continue
                        else:
                            dur_note += x.time
                    else:
                        f = pow(2, (x.note - 69) / 12) * 440
                        freqs.append(f)
                        if x.time == 0:
                            in_note = x.note
                            # wait for next corresponding msg for duration
                        else:
                            # it's all in one msg
                            durs.append(x.time)
                else:
                    if x.note == in_note:
                        # end note
                        durs.append(dur_note + x.time)
                        dur_note = 0
                        in_note = 0
                    elif x.time > 0:
                        if in_note:
                            dur_note += x.time
                        else:
                            # no notes, just silence!
                            freqs.append(None)
                            durs.append(x.time)
        if smallest_duration is not None:
            eighth = smallest_duration
        else:
            eighth = min(durs) # for the sake of argument
        return [(f, int(round((dur/eighth)))) for f, dur in zip(freqs, durs)]
    else:
        raise ImportError("mido library is not installed.")


def get_pitch_changed_data(note_char, octave, half_steps):
    """
    Takes the note character, current octave and the number of half steps and
    returns the pitch changed note data.
    half_steps: +ve = Pitch Up, -ve = Pitch Down
    """
    octaveChange = floor(half_steps / 12)
    noteTypeChange = half_steps % 12
    newOctave = octave + octaveChange
    newChar = octave1Notes[octave1Notes.index(note_char) + noteTypeChange]
    return newChar, newOctave
