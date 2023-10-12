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

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 100000

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

class HackEegTestApplicationException(Exception):
    pass

class HackEegSimpleApplication:
    """HackEEG commandline tool."""

    def __init__(self):
        self.serial_port_name = None
        self.hackeeg = None
        self.debug = False
        self.channel_test = False
        self.quiet = False
        self.hex = False
        self.messagepack = True
        self.channels = 8
        self.samples_per_second = 16000
        self.gain = 24
        self.max_samples = 100000
        self.lsl = False
        self.lsl_info = None
        self.lsl_outlet = None
        self.lsl_stream_name = "HackEEG"
        self.stream_id = str(uuid.uuid4())
        self.read_samples_continuously = True
        self.continuous_mode = False

        print(f"platform: {sys.platform}")
        if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
            self.non_blocking_console = NonBlockingConsole()
        elif sys.platform == "win32":
            self.non_blocking_console = WindowsNonBlockingConsole()
        self.non_blocking_console.init()
        # self.debug = True

    def find_dropped_samples(self, samples, number_of_samples):
        sample_numbers = {self.get_sample_number(sample): 1 for sample in samples}
        correct_sequence = {index: 1 for index in range(0, number_of_samples)}
        missing_samples = [sample_number for sample_number in correct_sequence.keys()
                           if sample_number not in sample_numbers]
        return len(missing_samples)

    def get_sample_number(self, sample):
        sample_number = sample.get('sample_number', -1)
        return sample_number

    def setup(self, samples_per_second=16000, gain=1, messagepack=True):
        if samples_per_second not in hackeeg.driver.SPEEDS.keys():
            raise HackEegTestApplicationException("{} is not a valid speed; valid speeds are {}".format(
                samples_per_second, sorted(hackeeg.driver.SPEEDS..keys())))
        if gain not in hackeeg.driver.GAINS.keys():
            raise HackEegTestApplicationException("{} is not a valid gain; valid gains are {}".format(
                gain, sorted(hackeeg.driver.GAINS.keys())))

        self.hackeeg.stop_and_sdatac_messagepack()
        self.hackeeg.sdatac()
        self.hackeeg.blink_board_led()
        sample_mode = hackeeg.driver.SPEEDS[samples_per_second] | ads1299.CONFIG1_const
        self.hackeeg.wreg(ads1299.CONFIG1, sample_mode)

        gain_setting = hackeeg.driver.GAINS[gain]

        self.hackeeg.disable_all_channels()
        if self.channel_test:
            self.channel_config_test()
        else:
            self.channel_config_input(gain_setting)


        # Route reference electrode to SRB1: JP8:1-2, JP7:NC (not connected)
        # use this with humans to reduce noise
        #self.hackeeg.wreg(ads1299.MISC1, ads1299.SRB1 | ads1299.MISC1_const)

        # Single-ended mode - setting SRB1 bit sends mid-supply voltage to the N inputs
        # use this with a signal generator
        self.hackeeg.wreg(ads1299.MISC1, ads1299.SRB1)

        # Dual-ended mode
        # self.hackeeg.wreg(ads1299.MISC1, ads1299.MISC1_const)
        # add channels into bias generation
        # self.hackeeg.wreg(ads1299.BIAS_SENSP, ads1299.BIAS8P)

        if messagepack:
            self.hackeeg.messagepack_mode()
        else:
            self.hackeeg.jsonlines_mode()
        self.hackeeg.start()
        self.hackeeg.rdatac()
        return

    def channel_config_input(self, gain_setting):
        # all channels enabled
        # for channel in range(1, 9):
        #     self.hackeeg.wreg(ads1299.CHnSET + channel, ads1299.TEST_SIGNAL | gain_setting )

        # self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.INT_TEST_DC | gain_setting)
        # self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.INT_TEST_DC | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 2, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 3, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 4, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 5, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 7, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 8, ads1299.ELECTRODE_INPUT | gain_setting)

    def channel_config_test(self):
        # test_signal_mode = ads1299.INT_TEST_DC | ads1299.CONFIG2_const
        test_signal_mode = ads1299.INT_TEST_4HZ | ads1299.CONFIG2_const
        self.hackeeg.wreg(ads1299.CONFIG2, test_signal_mode)
        self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.INT_TEST_DC | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 2, ads1299.SHORTED | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 3, ads1299.MVDD | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 4, ads1299.BIAS_DRN | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 5, ads1299.BIAS_DRP | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.TEMP | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 7, ads1299.TEST_SIGNAL | ads1299.GAIN_1X)
        self.hackeeg.disable_channel(8)

        # all channels enabled
        # for channel in range(1, 9):
        #     self.hackeeg.wreg(ads1299.CHnSET + channel, ads1299.TEST_SIGNAL | gain_setting )
        pass



    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("serial_port", help="serial port device path",
                            type=str)
        parser.add_argument("--debug", "-d", help="enable debugging output",
                            action="store_true")
        parser.add_argument("--samples", "-S", help="how many samples to capture",
                            default=DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE, type=int)
        parser.add_argument("--continuous", "-C", help="read data continuously (until <return> key is pressed)",
                            action="store_true")
        parser.add_argument("--sps", "-s",
                            help=f"ADS1299 samples per second setting- must be one of {sorted(list(SPEEDS.keys()))}, default is {self.samples_per_second}",
                            default=self.samples_per_second, type=int)
        parser.add_argument("--gain", "-g",
                            help=f"ADS1299 gain setting for all channels– must be one of {sorted(list(GAINS.keys()))}, default is {self.gain}",
                            default=self.gain, type=int)
        parser.add_argument("--lsl", "-L",
                            help=f"Send samples to an LSL stream instead of terminal",
                            action="store_true"),
        parser.add_argument("--lsl-stream-name", "-N",
                            help=f"Name of LSL stream to create",
                            default=self.lsl_stream_name, type=str),
        parser.add_argument("--messagepack", "-M",
                            help=f"MessagePack mode– use MessagePack format to send sample data to the host, rather than JSON Lines",
                            action="store_true")
        parser.add_argument("--channel-test", "-T",
                            help=f"set the channels to internal test settings for software testing",
                            action="store_true")
        parser.add_argument("--hex", "-H",
                            help=f"hex mode– output sample data in hexidecimal format for debugging",
                            action="store_true")
        parser.add_argument("--quiet", "-q",
                            help=f"quiet mode– do not print sample data (used for performance testing)",
                            action="store_true")
        args = parser.parse_args()
        if args.debug:
            self.debug = True
            print("debug mode on")
        self.samples_per_second = args.sps
        self.gain = args.gain

        if args.continuous:
            self.continuous_mode = True

        if args.lsl:
            self.lsl = True
            if args.lsl_stream_name:
                self.lsl_stream_name = args.lsl_stream_name
            self.lsl_info = StreamInfo(self.lsl_stream_name, 'EEG', self.channels, self.samples_per_second, 'int32',
                                       self.stream_id)
            self.lsl_outlet = StreamOutlet(self.lsl_info)

        self.serial_port_name = args.serial_port
        self.hackeeg = hackeeg.HackEEGBoard(self.serial_port_name, baudrate=2000000, debug=self.debug)
        self.max_samples = args.samples
        self.channel_test = args.channel_test
        self.quiet = args.quiet
        self.hex = args.hex
        self.messagepack = args.messagepack
        self.hackeeg.connect()
        self.setup(samples_per_second=self.samples_per_second, gain=self.gain, messagepack=self.messagepack)

    def process_sample(self, result, samples):
        data = None
        channel_data = None
        if result:
            status_code = result.get(self.hackeeg.MpStatusCodeKey)
            data = result.get(self.hackeeg.MpDataKey)
            samples.append(result)
            if status_code == hackeeg.driver.Status.Ok and data:
                if not self.quiet:
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
                if self.lsl and channel_data:
                    self.lsl_outlet.push_sample(channel_data)
            else:
                if not self.quiet:
                    print(data)
        else:
            print("no data to decode")
            print(f"result: {result}")

    def main(self):
        self.parse_args()

        samples = []
        sample_counter = 0

        end_time = time.perf_counter()
        start_time = time.perf_counter()
        while ((sample_counter < self.max_samples and not self.continuous_mode) or \
               (self.read_samples_continuously and self.continuous_mode)):
            result = self.hackeeg.read_rdatac_response()
            end_time = time.perf_counter()
            sample_counter += 1
            if self.continuous_mode:
                self.read_keyboard_input()
            self.process_sample(result, samples)

        duration = end_time - start_time
        self.hackeeg.stop_and_sdatac_messagepack()
        self.hackeeg.blink_board_led()

        print(f"duration in seconds: {duration}")
        samples_per_second = sample_counter / duration
        print(f"samples per second: {samples_per_second}")
        dropped_samples = self.find_dropped_samples(samples, sample_counter)
        print(f"dropped samples: {dropped_samples}")

max_samples = 100000

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

end_time = time.perf_counter()
start_time = time.perf_counter()
while (sample_counter < max_samples):
    result = hackeeg.read_rdatac_response()
    end_time = time.perf_counter()
    sample_counter += 1
    hackeeg.process_sample(result, samples)

duration = end_time - start_time
hackeeg.stop_and_sdatac_messagepack()
hackeeg.blink_board_led()

print(f"duration in seconds: {duration}")
samples_per_second = sample_counter / duration
print(f"samples per second: {samples_per_second}")
dropped_samples = hackeeg.find_dropped_samples(samples, sample_counter)
print(f"dropped samples: {dropped_samples}")

if __name__ == "__main__":
    hackeeg = HackEegSimpleApplication()

