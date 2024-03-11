#!/usr/bin/env python
# Python 3.11.5
# 2023-11-01

# Leonardo Fortaleza
# Canadian Space Mining Corporation (CSMC) / McGill University
# leonardo.fortaleza@csmc-scms.ca
# leonardo.fortaleza@mail.mcgill.ca


# Based upon the example used in the documentation.

# SERIAL_PORT_PATH="/dev/cu.usbmodem14434401"  # your actual path to the Arduino Native serial port device goes here
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import socket
import struct
import sys
import time
import uuid
import warnings
from matplotlib import pyplot as plt

import numpy as np
import scipy.io as sio
from scipy import signal
# from PyQt5.QtCore import QTimer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from hackeeg import hackeeg_scan
# from hackeeg import ads1299
import hackeeg
import hackeeg.analysis as han

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 100000

filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_data'))
# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_baseline-0-1-10-0-02'))
# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_noise-0-0-00-0-03'))
# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_experiment_1-A-2-10-02'))

# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_experiment_1-D-2-10-02'))

# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_dry_test_00-01'))

# hackeeg_scan(duration=1, samples_per_second=250)
# hackeeg.hackeeg_scan(duration=1, samples_per_second=250, channel_test=True, debug=True)
# df = hackeeg.hackeeg_scan(duration=0.1, samples_per_second=8000, channel_test=False, debug=False, gain=1, filepath=filepath, out_df=True, find_dropped_samples=True)
df = hackeeg.hackeeg_scan(duration=1, samples_per_second=16000, channel_test=False, debug=False, gain=1, filepath=filepath, out_df=True, find_dropped_samples=True)
# df = hackeeg.hackeeg_scan(duration=0.01, samples_per_second=16000, channel_test=False, debug=True, gain=1, filepath=filepath, out_df=True, find_dropped_samples=True)
# df = hackeeg.hackeeg_scan(duration=1, samples_per_second=1000, channel_test=False, debug=False, gain=1, filepath=filepath, out_df=True, find_dropped_samples=True)
# df = hackeeg.hackeeg_scan(duration=10/4000, samples_per_second=4000, channel_test=False, debug=True, gain=1, filepath=filepath, out_df=True, find_dropped_samples=True)
# df = hackeeg.hackeeg_scan(duration=1, samples_per_second=1000, channel_test=False, debug=True, gain=1, filepath=filepath, out_df=True)

# ax1 = quick_scatterplot(df, x='sample_number', y='voltage', hue='ch', style='ch', normalization='zscore')

# ax2 = han.quick_lineplot(df, x='sample_number', y='voltage', hue='ch', style='ch', normalization='zscore')
ax2 = han.quick_lineplot(df, x='sample_number', y='voltage', hue='ch', style='ch', normalization=None)
# ax2.set_xlim(2400, 2500)


plt.show()

han.quick_fftplot(df, scale='dB', normalization=None)

plt.show()