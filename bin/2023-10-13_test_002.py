#!/usr/bin/env python
# Python 3.11.5
# 2023-09-18

# Leonardo Fortaleza
# Canadian Space Mining Corporation (CSMC) / McGill University
# leonardo.fortaleza@csmc-scms.ca
# leonardo.fortaleza@mail.mcgill.ca


# Based upon the example used in the documentation.

# SERIAL_PORT_PATH="/dev/cu.usbmodem14434401"  # your actual path to the Arduino Native serial port device goes here
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

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 10000

# hackeeg_scan(duration=1, samples_per_second=250)
# hackeeg.hackeeg_scan(duration=1, samples_per_second=250, channel_test=True, debug=True)
hackeeg.hackeeg_scan(duration=1, samples_per_second=250, channel_test=False, debug=True, gain=24)