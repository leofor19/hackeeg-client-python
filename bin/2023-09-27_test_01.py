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
from hackeeg import HackEEGBoard
from hackeeg import ads1299

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 10000

# arduino_ports = [
#     p.device
#     for p in serial.tools.list_ports.comports()
#     if 'Arduino' in p.description  # may need tweaking to match new arduinos
# ]
# if not arduino_ports:
#     raise IOError("No Arduino found")
# if len(arduino_ports) > 1:
#     warnings.warn('Multiple Arduinos found - using the first')

# # print(arduino_ports)
# SERIAL_PORT_PATH = arduino_ports[0]

# hackeeg = HackEEGBoard(debug=False)
hackeeg = HackEEGBoard(debug=True)

try:
    hackeeg.connect()
    # print(hackeeg.mode)
    # print(hackeeg.version())
    hackeeg.sdatac()
    hackeeg.reset()
    hackeeg.blink_board_led()
    hackeeg.disable_all_channels()
    sample_mode = ads1299.HIGH_RES_250_SPS | ads1299.CONFIG1_const
    # sample_mode = ads1299.HIGH_RES_16k_SPS | ads1299.CONFIG1_const
    hackeeg.wreg(ads1299.CONFIG1, sample_mode)
    test_signal_mode = ads1299.INT_TEST_4HZ | ads1299.CONFIG2_const
    hackeeg.wreg(ads1299.CONFIG2, test_signal_mode)
    hackeeg.enable_all_channels()
    # print('mode:', hackeeg.mode)
    # hackeeg.jsonlines_mode()
    hackeeg.messagepack_mode()
    # print('mode:', hackeeg.mode)
    hackeeg.scan(duration=1, samples_per_second=250)
    # hackeeg.wreg(ads1299.CH7SET, ads1299.TEST_SIGNAL | ads1299.GAIN_1X)
    # # hackeeg.rreg(ads1299.CH7SET)


    # # Unipolar mode - setting SRB1 bit sends mid-supply voltage to the N inputs
    # hackeeg.wreg(ads1299.MISC1, ads1299.SRB1)
    # # add channels into bias generation
    # hackeeg.wreg(ads1299.BIAS_SENSP, ads1299.BIAS8P)
    # hackeeg.rdatac()
    # # hackeeg.read_rdatac_response()
    # hackeeg.start()

    # # time.sleep(1)

    # i = 0
    # while i <= 10 :
    #     # result = hackeeg.read_response()
    #     result = hackeeg.read_rdatac_response()
    #     # result = hackeeg.rdatac()
    #     # print('RESULT:',result)
    #     status_code = result.get('STATUS_CODE')
    #     status_text = result.get('STATUS_TEXT')
    #     status_code = result.get('ads_status')
    #     data = result.get(hackeeg.DataKey)
    #     if data:
    #         print('Something was found!')
    #         decoded_data = result.get(hackeeg.DecodedDataKey)
    #         if decoded_data:
    #             timestamp = decoded_data.get('timestamp')
    #             ads_gpio = decoded_data.get('ads_gpio')
    #             loff_statp = decoded_data.get('loff_statp')
    #             loff_statn = decoded_data.get('loff_statn')
    #             channel_data = decoded_data.get('channel_data')
    #             print(f"timestamp:{timestamp} | gpio:{ads_gpio} loff_statp:{loff_statp} loff_statn:{loff_statn} |   ",
    #                 end='')
    #             for channel_number, sample in enumerate(channel_data):
    #                 print(f"{channel_number + 1}:{sample} ", end='')
    #             print()
    #         else:
    #             print('Nothing was found! :(')
    #             print(data)
    #         sys.stdout.flush()
    #     i += 1
finally:
    hackeeg.raw_serial_port.close()
    print('Port Closed')