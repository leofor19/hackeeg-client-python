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

import numpy as np
import scipy.io as sio
from scipy import signal
# from PyQt5.QtCore import QTimer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from hackeeg import hackeeg_scan
# from hackeeg import ads1299
import hackeeg
import hackeeg.analysis as han

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 10000

# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_data'))
# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_baseline-0-0-01-0-02'))
# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_noise-0-0-00-0-02'))
# filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_experiment_1-A-1-01-03'))

filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_experiment_1-D-2-10-01'))

# hackeeg_scan(duration=1, samples_per_second=250)
# hackeeg.hackeeg_scan(duration=1, samples_per_second=250, channel_test=True, debug=True)
df = hackeeg.hackeeg_scan(duration=1, samples_per_second=16000, channel_test=False, debug=False, gain=1, filepath=filepath)
# hackeeg.hackeeg_scan(duration=1, samples_per_second=16000, channel_test=False, debug=True, gain=1, filepath=filepath)

# ax1 = quick_scatterplot(df, x='sample_number', y='voltage', hue='ch', style='ch', normalization='zscore')

ax2 = quick_lineplot(df, x='sample_number', y='voltage', hue='ch', style='ch', normalization='zscore')

quick_fftplot(df, scale='dB', normalization=None)