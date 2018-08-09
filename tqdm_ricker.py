"""Tqdm audio progress ticker and Ricker

Some ideas drawn from https://github.com/simonm3/nbextensions/blob/master/cellevents.py
"""

import tqdm
import urllib
import os
from IPython import display as disp
from IPython.core.display import HTML
import numpy as np
from scipy.io.wavfile import read
import note_utils

def hide_audio():
    """Hide the audio control.
    """
    disp.display(HTML("<span><style>audio{display:none}</style><span>"))

def activate_audio(framerate):
    temp_dur = .0001
    temp_t = np.linspace(0, temp_dur, int(framerate*temp_dur))
    qtr_t_ix = int(len(temp_t)/4)
    qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
    mid_fac = np.ones(len(temp_t)-2*qtr_t_ix)
    data = np.sin(2*np.pi*100.0*temp_t) * np.concatenate((qtr_fac, mid_fac,
                                            qtr_fac[::-1]), axis=0) #* volume
    # activate the audio object (will make a brief click)
    return disp.display(disp.Audio(data, rate=framerate, autoplay=True),
                                               display_id='tqdm_alerter');


class Alert(object):
    def __init__(self, duration=0.06, wav_kind='sine', volume=0.25):
        self.volume = volume # currently not implemented
        self.framerate = 44100
        self.duration = duration
        self.wav_kind = wav_kind
        self.display = activate_audio(self.framerate)
        hide_audio();
        # allow for update later, based on changing parameters
        self.set_sound()

    def set_sound(self, wav_kind=None):
        self.t = np.linspace(0, self.duration, int(self.framerate*self.duration))
        # fade in and out settings for chunks, so no click
        qtr_t_ix = int(len(self.t)/4)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(len(self.t)-2*qtr_t_ix)
        self.envelope = np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0)
        if wav_kind is not None:
            self.wav_kind = wav_kind

    def alert(self, freq=400):
        # freq in Hz
        if freq < 70:
            freq = 70
        elif freq > 2500:
            freq = 2500
        data = note_utils.syn_kinds[self.wav_kind](float(freq), self.duration, 1, self.framerate, self.volume, self.envelope)
        #np.sin(2*np.pi*float(freq)*self.t) * self.envelope #* self.volume
        # norm=False parameter to Audio only exists in this PR https://github.com/ipython/ipython/pull/11161
        self.display.update(disp.Audio(data, rate=self.framerate, autoplay=True));


class Sequence(object):
    def __init__(self, volume=0.25):
        # note_duration is value of eighth note
        self.volume = volume # currently not implemented
        self.framerate = 44100
        self.display = activate_audio(self.framerate)
        hide_audio();
        self.seq = []
        self.n = 0
        self.every = 1
        self.reset()

    def reset(self):
        self.i = 0
        self.tick = 0 # used with every

    def set_sound(self, seq, note_duration, wav_kind='sine'):
        assert len(seq) > 0
        assert note_duration > 0
        self.note_duration = note_duration
        self.seq, self.n = note_utils.sequence_spec_to_wav(seq, note_duration,
                                                    self.framerate, wav_kind)

    def play(self):
        self.tick += 1
        if self.tick % self.every == 0:
            data = self.seq[self.i]
            if data is not None:
                # norm=False parameter to Audio only exists in this PR https://github.com/ipython/ipython/pull/11161
                self.display.update(disp.Audio(data, rate=self.framerate, autoplay=True));
            self.i = (1+self.i) % self.n

# ### Careful not to let the frequency get above 2kHz, as there's no volume control and it will be piercing
#
# You could make a logarithmic saturation so the freq doesn't get above say 1.5kHz

# # Main tqdm-overloading classes


# adapted from tqdm docs: https://github.com/tqdm/tqdm#hooks-and-callbacks
class tqdm_audio_ticker(tqdm.tqdm):
    A = Alert() # will make a tiny click when instantiated in class, one time only!

    def __init__(self, *args, freq_step=0, duration=0.02, start_freq=150,
                 wav_kind='sine', **kwargs):
        self.freq_step = freq_step
        self.start_freq = start_freq
        self.A.duration = duration
        self.A.set_sound(wav_kind)
        super(tqdm_audio_ticker, self).__init__(*args, **kwargs)

    def update_to(self, b=1, bsize=1, tsize=None):
        """
        b  : int, optional
            Number of blocks transferred so far [default: 1].
        bsize  : int, optional
            Size of each block (in tqdm units) [default: 1].
        tsize  : int, optional
            Total size (in tqdm units). If [default: None] remains unchanged.
        """
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n, True)  # will also set self.n = b * bsize
        #if b % 2 == 0:
        self.A.alert(self.start_freq + b*10)

    def update(self, n=1, from_update_to=False):
        if not from_update_to:
            # avoid multiple plays at once
            self.A.alert(self.start_freq + self.n * n)
        super(tqdm_audio_ticker, self).update()

    def __iter__(self, *args, **kwargs):
        try:
            for obj in super(tqdm_audio_ticker, self).__iter__(*args, **kwargs):
                # return super(tqdm...) will not catch exception
                self.A.alert(self.start_freq + self.n * self.freq_step)
                yield obj
        # NB: except ... [ as ...] breaks IPython async KeyboardInterrupt
        except:
            self.sp(' ') #bar_style='danger')
            raise


class tqdm_music_ticker(tqdm.tqdm):
    S = Sequence() # will make a tiny click when instantiated in class, one time only!

    def __init__(self, *args, seq=note_utils.ce_sequence, note_duration=0.05, every=1, wav_kind='saw', **kwargs):
        self.S.set_sound(seq, note_duration, wav_kind)
        self.S.every = every
        super(tqdm_music_ticker, self).__init__(*args, **kwargs)

    def update_to(self, b=1, bsize=1, tsize=None):
        """
        b  : int, optional
            Number of blocks transferred so far [default: 1].
        bsize  : int, optional
            Size of each block (in tqdm units) [default: 1].
        tsize  : int, optional
            Total size (in tqdm units). If [default: None] remains unchanged.
        """
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n, True)  # will also set self.n = b * bsize
        #if b % 2 == 0:
        self.S.play()

    def update(self, n=1, from_update_to=False):
        if not from_update_to:
            # avoid multiple plays at once
            self.S.play()
        super(tqdm_music_ticker, self).update()

    def __iter__(self, *args, **kwargs):
        self.S.reset()
        try:
            for obj in super(tqdm_music_ticker, self).__iter__(*args, **kwargs):
                # return super(tqdm...) will not catch exception
                self.S.play()
                yield obj
        # NB: except ... [ as ...] breaks IPython async KeyboardInterrupt
        except:
            self.sp(' ') #bar_style='danger')
            raise


# # For playing iterated clips through a wave file, let's get Rick's catchphrase


class Ricker(object):
    def __init__(self, total=100):
        wav_data = read(note_utils.fetch_resource('http://sound.peal.io/ps/audios/000/000/537/original/woo_vu_luvub_dub_dub.wav'))
        self.sample_rate = wav_data[0]
        self.wav = np.array(wav_data[1], dtype=float)[:,0] # make it mono
        self.set_total(total)
        self.display = activate_audio(self.sample_rate)
        hide_audio();

    def set_total(self, total):
        self.total = total
        self.chunk_size = int(len(self.wav)/total)
        # fade in and out settings for chunks, so no click
        qtr_t_ix = int(self.chunk_size/8)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(self.chunk_size-2*qtr_t_ix)
        self.envelope = np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0)

    def alert(self, n):
        if n >= self.total-1:
            # keep playing the last chunk if more sounds are needed
            n = self.total-1
        data_chunk = self.wav[n*self.chunk_size:(n+1)*self.chunk_size]
        self.display.update(disp.Audio(data_chunk * self.envelope, #* self.volume
                                rate=self.sample_rate, autoplay=True));
        #hide_audio()
        # norm=False parameter to Audio only exists in this PR https://github.com/ipython/ipython/pull/11161


class tqdm_audio_ricker(tqdm.tqdm):
    R = Ricker() # will make a tiny click when instantiated in class, one time only!

    def __init__(self, *args, total=100, **kwargs):
        self.R.set_total(total)
        super(tqdm_audio_ricker, self).__init__(*args, **kwargs)

    def update_to(self, b=1, bsize=1, tsize=None):
        """
        b  : int, optional
            Number of blocks transferred so far [default: 1].
        bsize  : int, optional
            Size of each block (in tqdm units) [default: 1].
        tsize  : int, optional
            Total size (in tqdm units). If [default: None] remains unchanged.
        """
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n, True)  # will also set self.n = b * bsize
        #if b % 2 == 0:
        self.R.alert(b)

    def update(self, n=1, from_update_to=False):
        super(tqdm_audio_ricker, self).update()
        if not from_update_to:
            # avoid multiple plays at once
            self.R.alert(self.n)

    def __iter__(self, *args, **kwargs):
        try:
            for obj in super(tqdm_audio_ricker, self).__iter__(*args, **kwargs):
                # return super(tqdm...) will not catch exception
                self.R.alert(self.n)
                yield obj
        # NB: except ... [ as ...] breaks IPython async KeyboardInterrupt
        except:
            self.sp(' ') #bar_style='danger')
            raise
