# TqdmAudioRicker
Audio progress ticker (and Ricker) for Jupyter notebooks, overloading tqdm

First, make sure you've installed tqdm dependency: `pip install tqdm`

See the tqdm_ricker_test.ipynb notebook for usage and examples.

Due to the hacky way of getting the audio to work nicely, you can only import the classes once
per session and successfully get sound. Otherwise, you'll have to restart the kernel to re-import.
