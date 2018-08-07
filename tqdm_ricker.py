"""Tqdm audio progress ticker and Ricker

Some ideas drawn from https://github.com/simonm3/nbextensions/blob/master/cellevents.py
"""

import tqdm
import urllib
import os
from IPython import display as disp
from IPython.core.display import HTML
import numpy as np
from requests import get
import io
from scipy.io.wavfile import read

def hide_audio():
    """ hide the audio control """
    disp.display(HTML("<span><style>audio{display:none}</style><span>"))

class Alert(object):
    def __init__(self, duration=0.04, volume=0.25):
        self.volume = volume # currently not implemented
        self.framerate = 44100
        self.duration = duration
        temp_dur = .0001
        temp_t = np.linspace(0, temp_dur, int(self.framerate*temp_dur))
        self.t = np.linspace(0, self.duration, int(self.framerate*self.duration))
        qtr_t_ix = int(len(temp_t)/4)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(len(temp_t)-2*qtr_t_ix)
        data = np.sin(2*np.pi*100.0*temp_t) * np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0) #* self.volume

        # activate the audio object
        self.display = disp.display(disp.Audio(data, rate=self.framerate, autoplay=True),
                                               display_id='tqdm_alerter');
        hide_audio(); # not needed inside here

    def alert(self, freq=400):
        # freq in Hz
        # fade in and out so no click
        qtr_t_ix = int(len(self.t)/4)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(len(self.t)-2*qtr_t_ix)
        data = np.sin(2*np.pi*float(freq)*self.t) * np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0) #* self.volume
        # norm=False parameter to Audio only exists in this PR https://github.com/ipython/ipython/pull/11161
        self.display.update(disp.Audio(data, rate=self.framerate, autoplay=True));



# ### Careful not to let the frequency get above 2kHz, as there's no volume control and it will be piercing
#
# You could make a logarithmic saturation so the freq doesn't get above say 1.5kHz

# # Main tqdm-overloading classes


# adapted from tqdm docs: https://github.com/tqdm/tqdm#hooks-and-callbacks
class TqdmAudioTicker(tqdm.tqdm):
    A = Alert(duration=0.02) # will make a tiny click when instantiated in class, one time only!

    def __init__(self, *args, freq_step=10, **kwargs):
        self.freq_step = freq_step
        super(TqdmAudioTicker, self).__init__(*args, **kwargs)

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
        self.A.alert(200+b*10)

    def update(self, n=1, from_update_to=False):
        if not from_update_to:
            self.A.alert(200 + self.n * n) # base of 200Hz
        super(TqdmAudioTicker, self).update()

    def __iter__(self):
        """Backward-compatibility to use: for x in tqdm(iterable)"""

        # Inlining instance variables as locals (speed optimisation)
        iterable = self.iterable

        # If the bar is disabled, then just walk the iterable
        # (note: keep this check outside the loop for performance)
        if self.disable:
            for obj in iterable:
                yield obj
        else:
            mininterval = self.mininterval
            maxinterval = self.maxinterval
            miniters = self.miniters
            dynamic_miniters = self.dynamic_miniters
            last_print_t = self.last_print_t
            last_print_n = self.last_print_n
            n = self.n
            smoothing = self.smoothing
            avg_time = self.avg_time
            _time = self._time

            try:
                sp = self.sp
            except AttributeError:
                raise TqdmDeprecationWarning("""Please use `tqdm_gui(...)` instead of `tqdm(..., gui=True)`
""", fp_write=getattr(self.fp, 'write', sys.stderr.write))

            for obj in iterable:
                yield obj
                # Update and possibly print the progressbar.
                # Note: does not call self.update(1) for speed optimisation.
                n += 1
                # check counter first to avoid calls to time()
                if n - last_print_n >= self.miniters:
                    miniters = self.miniters  # watch monitoring thread changes
                    delta_t = _time() - last_print_t
                    if delta_t >= mininterval:
                        cur_t = _time()
                        delta_it = n - last_print_n
                        # EMA (not just overall average)
                        if smoothing and delta_t and delta_it:
                            avg_time = delta_t / delta_it                                 if avg_time is None                                 else smoothing * delta_t / delta_it +                                 (1 - smoothing) * avg_time

                        self.n = n
                        self.A.alert(200 + self.n * self.freq_step)
                        with self._lock:
                            if self.pos:
                                self.moveto(abs(self.pos))
                            # Print bar update
                            sp(self.__repr__())
                            if self.pos:
                                self.moveto(-abs(self.pos))

                        # If no `miniters` was specified, adjust automatically
                        # to the max iteration rate seen so far between 2 prints
                        if dynamic_miniters:
                            if maxinterval and delta_t >= maxinterval:
                                # Adjust miniters to time interval by rule of 3
                                if mininterval:
                                    # Set miniters to correspond to mininterval
                                    miniters = delta_it * mininterval / delta_t
                                else:
                                    # Set miniters to correspond to maxinterval
                                    miniters = delta_it * maxinterval / delta_t
                            elif smoothing:
                                # EMA-weight miniters to converge
                                # towards the timeframe of mininterval
                                miniters = smoothing * delta_it *                                     (mininterval / delta_t
                                     if mininterval and delta_t else 1) + \
                                    (1 - smoothing) * miniters
                            else:
                                # Maximum nb of iterations between 2 prints
                                miniters = max(miniters, delta_it)

                        # Store old values for next call
                        self.n = self.last_print_n = last_print_n = n
                        self.last_print_t = last_print_t = cur_t
                        self.miniters = miniters

            # Closing the progress bar.
            # Update some internal variables for close().
            self.last_print_n = last_print_n
            self.n = n
            self.miniters = miniters
            self.close()


# # For playing iterated clips through a wave file, let's get Rick's catchphrase


class Ricker(object):
    def __init__(self, total=100):
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}
        data = get('http://sound.peal.io/ps/audios/000/000/537/original/woo_vu_luvub_dub_dub.wav',
                   headers=hdr).content
        wav_data = read(io.BytesIO(data))
        #wav_data = read('woo_vu_luvub_dub_dub.wav')
        self.sample_rate = wav_data[0]
        self.wav = np.array(wav_data[1], dtype=float)[:,0] # make it mono
        self.set_total(total)
        temp_dur = .0001
        temp_t = np.linspace(0, temp_dur, int(self.sample_rate*temp_dur))
        qtr_t_ix = int(len(temp_t)/4)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(len(temp_t)-2*qtr_t_ix)
        data = np.sin(2*np.pi*100.0*temp_t) * np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0) #* self.volume
        # activate the audio object
        self.display = disp.display(disp.Audio(data, rate=self.sample_rate, autoplay=True),
                                               display_id='tqdm_alerter');
        hide_audio();

    def set_total(self, total):
        self.total = total
        self.chunk_size = int(len(self.wav)/total)

    def alert(self, n):
        if n >= self.total-1:
            n = self.total-1
        data_chunk = self.wav[n*self.chunk_size:(n+1)*self.chunk_size]
        # fade in and out so no click
        qtr_t_ix = int(self.chunk_size/8)
        qtr_fac = np.array(list(range(qtr_t_ix)))/qtr_t_ix
        mid_fac = np.ones(self.chunk_size-2*qtr_t_ix)
        self.display.update(disp.Audio(data_chunk * np.concatenate((qtr_fac, mid_fac, qtr_fac[::-1]), axis=0), #* self.volume
                                rate=self.sample_rate, autoplay=True));
        #hide_audio()
        # norm=False parameter to Audio only exists in this PR https://github.com/ipython/ipython/pull/11161


class TqdmAudioRicker(tqdm.tqdm):
    R = Ricker() # will make a tiny click when instantiated in class, one time only!

    def __init__(self, *args, total=100, **kwargs):
        self.R.set_total(total)
        super(TqdmAudioRicker, self).__init__(*args, **kwargs)

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
        super(TqdmAudioRicker, self).update()
        if not from_update_to:
            self.R.alert(self.n) # base of 200Hz

    def __iter__(self):
        """Backward-compatibility to use: for x in tqdm(iterable)"""

        # Inlining instance variables as locals (speed optimisation)
        iterable = self.iterable

        # If the bar is disabled, then just walk the iterable
        # (note: keep this check outside the loop for performance)
        if self.disable:
            for obj in iterable:
                yield obj
        else:
            mininterval = self.mininterval
            maxinterval = self.maxinterval
            miniters = self.miniters
            dynamic_miniters = self.dynamic_miniters
            last_print_t = self.last_print_t
            last_print_n = self.last_print_n
            n = self.n
            smoothing = self.smoothing
            avg_time = self.avg_time
            _time = self._time

            try:
                sp = self.sp
            except AttributeError:
                raise TqdmDeprecationWarning("""Please use `tqdm_gui(...)` instead of `tqdm(..., gui=True)`
""", fp_write=getattr(self.fp, 'write', sys.stderr.write))

            for obj in iterable:
                yield obj
                # Update and possibly print the progressbar.
                # Note: does not call self.update(1) for speed optimisation.
                n += 1
                # check counter first to avoid calls to time()
                if n - last_print_n >= self.miniters:
                    miniters = self.miniters  # watch monitoring thread changes
                    delta_t = _time() - last_print_t
                    if delta_t >= mininterval:
                        cur_t = _time()
                        delta_it = n - last_print_n
                        # EMA (not just overall average)
                        if smoothing and delta_t and delta_it:
                            avg_time = delta_t / delta_it                                 if avg_time is None                                 else smoothing * delta_t / delta_it +                                 (1 - smoothing) * avg_time

                        self.n = n
                        self.R.alert(self.n)
                        with self._lock:
                            if self.pos:
                                self.moveto(abs(self.pos))
                            # Print bar update
                            sp(self.__repr__())
                            if self.pos:
                                self.moveto(-abs(self.pos))

                        # If no `miniters` was specified, adjust automatically
                        # to the max iteration rate seen so far between 2 prints
                        if dynamic_miniters:
                            if maxinterval and delta_t >= maxinterval:
                                # Adjust miniters to time interval by rule of 3
                                if mininterval:
                                    # Set miniters to correspond to mininterval
                                    miniters = delta_it * mininterval / delta_t
                                else:
                                    # Set miniters to correspond to maxinterval
                                    miniters = delta_it * maxinterval / delta_t
                            elif smoothing:
                                # EMA-weight miniters to converge
                                # towards the timeframe of mininterval
                                miniters = smoothing * delta_it *                                     (mininterval / delta_t
                                     if mininterval and delta_t else 1) + \
                                    (1 - smoothing) * miniters
                            else:
                                # Maximum nb of iterations between 2 prints
                                miniters = max(miniters, delta_it)

                        # Store old values for next call
                        self.n = self.last_print_n = last_print_n = n
                        self.last_print_t = last_print_t = cur_t
                        self.miniters = miniters

            # Closing the progress bar.
            # Update some internal variables for close().
            self.last_print_n = last_print_n
            self.n = n
            self.miniters = miniters
            self.close()

