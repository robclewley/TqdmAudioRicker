# TqdmAudioRicker

Audio progress ticker (and Ricker) for Jupyter notebooks, overloading tqdm.

 - You can play notes (sine, saw, or square wave) at a chosen frequency
   - including duration and optional frequency step
 - You can cut up wave file samples
   - Rick & Morty sample is the default
 - You can import monophonic MIDI files as ticker sequences
   - Make sure to `pip install mido`

First, make sure you've installed tqdm dependency: `pip install tqdm`

See the tqdm_ricker_test.ipynb notebook for usage and examples.

Due to the hacky way of getting the audio to work nicely, you can only import the classes once
per session and successfully get sound. Otherwise, you'll have to restart the kernel to re-import.

Also, since ipython audio currently forces normalization of output data amplitude, you should absolutely keep your computer's volume down when using this library. Watch https://github.com/robclewley/TqdmAudioRicker/issues/2 for updates when the existing PR is merged into master and published.