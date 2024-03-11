#!/usr/bin/env python
# Python 3.12.0
# 2023-11-17

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
from tqdm.autonotebook import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hackeeg import HackEEGBoard
from hackeeg import ads1299

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 100000

samples_per_second = 4000
gain = 1
channel_test = False

duration = 1
speed = samples_per_second
display_output = True
max_samples = DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE

debug = False
# debug = True
display_output = debug

hackeeg = HackEEGBoard(debug=debug)

try:
    # hackeeg.connect()
    # # print(hackeeg.mode)
    # # print(hackeeg.version())
    # hackeeg.sdatac()
    # hackeeg.reset()
    # hackeeg.blink_board_led()
    # hackeeg.disable_all_channels()
    # sample_mode = ads1299.HIGH_RES_250_SPS | ads1299.CONFIG1_const
    # # sample_mode = ads1299.HIGH_RES_16k_SPS | ads1299.CONFIG1_const
    # hackeeg.wreg(ads1299.CONFIG1, sample_mode)
    # test_signal_mode = ads1299.INT_TEST_4HZ | ads1299.CONFIG2_const
    # hackeeg.wreg(ads1299.CONFIG2, test_signal_mode)
    # hackeeg.enable_all_channels()
    # # print('mode:', hackeeg.mode)
    # # hackeeg.jsonlines_mode()
    # hackeeg.messagepack_mode()
    # # print('mode:', hackeeg.mode)
    # hackeeg.start()
    # hackeeg.scan(duration=1, samples_per_second=250)

    hackeeg.sdatac()
    hackeeg.reset()

    hackeeg.setup(samples_per_second=samples_per_second, gain=gain, messagepack=True, channel_test=channel_test)

    max_sample_time = duration * speed

    # hackeeg.start()

    samples = []
    sample_counter = 0

    # hackeeg.sdatac()
    hackeeg.rdatac()

    progress = tqdm(total = max_sample_time, miniters=1)
    tqdm.write("Flushing buffer...")
    # result = hackeeg.raw_serial_port.read_all() # initial data read_all
    result = hackeeg.flush_buffer(timeout=2, flushing_levels=4)
    # result = hackeeg.read_rdatac_response() # initial data read to flush buffer and avoid sample miscounting

    tqdm.write("Acquiring data...")
    end_time = time.perf_counter()
    start_time = time.perf_counter()
    while ((sample_counter < max_samples) and (sample_counter < max_sample_time)):
        # result = hackeeg.read_rdatac_response()
        # result = hackeeg._serial_read_messagepack_message()
        result = hackeeg.message_pack_unpacker.unpack()
        # result = hackeeg.message_pack_unpacker.read_bytes(38)
        # result = hackeeg.message_pack_unpacker.tell()


        end_time = time.perf_counter()
        sample_counter += 1
        progress.update(1)
        if hackeeg.mode == 2:  # MessagePack mode
            samples.append(result)
        else:
            hackeeg.process_sample(result, samples)

        # optional display of samples
        if display_output:
            tqdm.write(str(samples[-1]))

    progress.close()
    # tqdm.write(f'Buffer size: {len(result)}')

    dur = end_time - start_time
    hackeeg.stop_and_sdatac_messagepack()
    samples = hackeeg.process_sample_batch(samples)

    tqdm.write(f"duration in seconds: {dur}")
    sampps = sample_counter / dur
    tqdm.write(f"samples per second: {sampps}")


finally:
    hackeeg.raw_serial_port.close()
    print('Port Closed')