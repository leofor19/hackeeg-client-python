#!/usr/bin/env python
# Python 3.11.5
# 2023-09-18

# Leonardo Fortaleza
# Canadian Space Mining Corporation (CSMC) / McGill University
# leonardo.fortaleza@csmc-scms.ca
# leonardo.fortaleza@mail.mcgill.ca


# Based upon the example used in the documentation.

SERIAL_PORT_PATH="/dev/cu.usbmodem14434401"  # your actual path to the Arduino Native serial port device goes here
import json
import os
import queue
import socket
import status
import struct
import sys
import time
import uuid
import warnings

import numpy as np
import scipy.io as sio
from scipy import signal
# from PyQt5.QtCore import QTimer

import hackeeg
from hackeeg import ads1299

max_samples = 100000

arduino_ports = [
    p.device
    for p in serial.tools.list_ports.comports()
    if 'Arduino' in p.description  # may need tweaking to match new arduinos
]
if not arduino_ports:
    raise IOError("No Arduino found")
if len(arduino_ports) > 1:
    warnings.warn('Multiple Arduinos found - using the first')

# print(arduino_ports)
SERIAL_PORT_PATH = arduino_ports[0]

hackeeg = hackeeg.HackEEGBoard(SERIAL_PORT_PATH)
hackeeg.connect()
hackeeg.sdatac()
hackeeg.reset()
hackeeg.blink_board_led()
hackeeg.disable_all_channels()
hackeeg.messagepack_mode()
sample_mode = ads1299.HIGH_RES_16k_SPS | ads1299.CONFIG1_const
hackeeg.wreg(ads1299.CONFIG1, sample_mode)
test_signal_mode = ads1299.INT_TEST_4HZ | ads1299.CONFIG2_const
hackeeg.wreg(ads1299.CONFIG2, test_signal_mode)
# hackeeg.enable_channel(7, gain=ads1299.GAIN_24X)
hackeeg.enable_all_channels(gain=ads1299.GAIN_24X)
hackeeg.wreg(ads1299.CH7SET, ads1299.TEST_SIGNAL | ads1299.GAIN_1X)
hackeeg.rreg(ads1299.CH5SET)

# Unipolar mode - setting SRB1 bit sends mid-supply voltage to the N inputs
hackeeg.wreg(ads1299.MISC1, ads1299.SRB1)
# add channels into bias generation
hackeeg.wreg(ads1299.BIAS_SENSP, ads1299.BIAS8P)
hackeeg.rdatac()
hackeeg.start()

# while True:
#     result = hackeeg.read_response()
#     status_code = result.get('STATUS_CODE')
#     status_text = result.get('STATUS_TEXT')
#     data = result.get(hackeeg.DataKey)
#     if data:
#         decoded_data = result.get(hackeeg.DecodedDataKey)
#         if decoded_data:
#             timestamp = decoded_data.get('timestamp')
#             ads_gpio = decoded_data.get('ads_gpio')
#             loff_statp = decoded_data.get('loff_statp')
#             loff_statn = decoded_data.get('loff_statn')
#             channel_data = decoded_data.get('channel_data')
#             print(f"timestamp:{timestamp} | gpio:{ads_gpio} loff_statp:{loff_statp} loff_statn:{loff_statn} |   ",
#                   end='')
#             for channel_number, sample in enumerate(channel_data):
#                 print(f"{channel_number + 1}:{sample} ", end='')
#             print()
#         else:
#             print(data)
#         sys.stdout.flush()

# self.parse_args()

samples = []
sample_counter = 0
quiet = False
hex = False

end_time = time.perf_counter()
start_time = time.perf_counter()
while (sample_counter < max_samples):
    result = hackeeg.read_rdatac_response()
    end_time = time.perf_counter()
    sample_counter += 1
    # hackeeg.process_sample(result, samples)
    status_code = result.get(hackeeg.MpStatusCodeKey)
    data = result.get(hackeeg.MpDataKey)
    samples.append(result)
    if result:
        if status_code == hackeeg.driver.Status.Ok and data:
            if not quiet:
                timestamp = result.get('timestamp')
                sample_number = result.get('sample_number')
                ads_gpio = result.get('ads_gpio')
                loff_statp = result.get('loff_statp')
                loff_statn = result.get('loff_statn')
                channel_data = result.get('channel_data')
                data_hex = result.get('data_hex')
                print(
                    f"timestamp:{timestamp} sample_number: {sample_number}| gpio:{ads_gpio} loff_statp:{loff_statp} loff_statn:{loff_statn}   ",
                    end='')
                if self.hex:
                    print(data_hex)
                else:
                    for channel_number, sample in enumerate(channel_data):
                        print(f"{channel_number + 1}:{sample} ", end='')
                    print()
        else:
            if not quiet:
                    print(data)
    else:
        print("no data to decode")
        print(f"result: {result}")


duration = end_time - start_time
hackeeg.stop_and_sdatac_messagepack()
hackeeg.blink_board_led()

print(f"duration in seconds: {duration}")
samples_per_second = sample_counter / duration
print(f"samples per second: {samples_per_second}")
# dropped_samples = hackeeg.find_dropped_samples(samples, sample_counter)
# print(f"dropped samples: {dropped_samples}")