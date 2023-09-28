import base64
import binascii
from datetime import datetime
import io
import json
import sys
from json import JSONDecodeError
import os
from pathlib import Path
import warnings

import msgpack
import pandas as pd
import serial
import serial.tools.list_ports
import time

from . import ads1299

# TODO
# - MessagePack
# - MessagePack / Json Lines testing convenience functions

NUMBER_OF_SAMPLES = 10000
DEFAULT_BAUDRATE = 115200
SAMPLE_LENGTH_IN_BYTES = 38  # 216 bits encoded with base64 + '\r\n\'

SPEEDS = {250: ads1299.HIGH_RES_250_SPS,
          500: ads1299.HIGH_RES_500_SPS,
          1000: ads1299.HIGH_RES_1k_SPS,
          2000: ads1299.HIGH_RES_2k_SPS,
          4000: ads1299.HIGH_RES_4k_SPS,
          8000: ads1299.HIGH_RES_8k_SPS,
          16000: ads1299.HIGH_RES_16k_SPS}

GAINS = {1: ads1299.GAIN_1X,
         2: ads1299.GAIN_2X,
         4: ads1299.GAIN_4X,
         6: ads1299.GAIN_6X,
         8: ads1299.GAIN_8X,
         12: ads1299.GAIN_12X,
         24: ads1299.GAIN_24X}


class Status:
    Ok = 200
    BadRequest = 400
    Error = 500


class HackEEGException(Exception):
    pass


class HackEEGBoard:
    TextMode = 0
    JsonLinesMode = 1
    MessagePackMode = 2

    CommandKey = "COMMAND"
    ParametersKey = "PARAMETERS"
    HeadersKey = "HEADERS"
    DataKey = "DATA"
    DecodedDataKey = "DECODED_DATA"
    StatusCodeKey = "STATUS_CODE"
    StatusTextKey = "STATUS_TEXT"

    MpCommandKey = "C"
    MpParametersKey = "P"
    MpHeadersKey = "H"
    MpDataKey = "D"
    MpStatusCodeKey = "C"
    MpStatusTextKey = "T"
    MaxConnectionAttempts = 10
    ConnectionSleepTime = 0.1

    def __init__(self, serial_port_path=None, baudrate=DEFAULT_BAUDRATE, debug=False, quiet=True,
                 max_samples=100000, duration=1, target_mode=2, speed=16000):
        self.mode = None
        self.target_mode = target_mode
        self.message_pack_unpacker = None
        self.debug = debug
        self.quiet = quiet
        self.baudrate = baudrate
        self.rdatac_mode = False
        self.max_samples = max_samples
        self.duration = duration
        self.default_filepath = "".join((str(Path(__file__).resolve().parents[1]), '/data/',  datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), '_data'))
        self.speed = 16000

        if serial_port_path is None:
            self.serial_port_path = self.locate_arduino_port()
        else:
            self.serial_port_path = serial_port_path
        self.raw_serial_port = serial.serial_for_url(self.serial_port_path, baudrate=self.baudrate, timeout=0.1)
        if self.debug:
            print('Connected to Serial Port:')
            print(self.raw_serial_port)
        self.raw_serial_port.reset_input_buffer()
        self.serial_port= self.raw_serial_port
        # self.serial_port = io.TextIOWrapper(io.BufferedRWPair(self.raw_serial_port, self.raw_serial_port))
        # self.serial_port = io.TextIOWrapper(io.BufferedRWPair(self.raw_serial_port, self.raw_serial_port, 1), encoding='utf-8')
        # print(self.serial_port)
        # self.serial_port = io.TextIOWrapper(io.BufferedRandom(self.raw_serial_port))
        # self.serial_port = io.BufferedRWPair(self.raw_serial_port, self.raw_serial_port)
        # self.binaryBufferedSerialPort = io.BufferedReader(io.BufferedRWPair(self.raw_serial_port, self.raw_serial_port))
        # self.message_pack_unpacker = msgpack.Unpacker(self.binaryBufferedSerialPort, raw=False, use_list=False)
        self.message_pack_unpacker = msgpack.Unpacker(self.raw_serial_port, raw=False, use_list=False)

    def connect(self):
        self.mode = self._sense_protocol_mode()
        if self.mode == self.TextMode:
            attempts = 0
            connected = False
            while attempts < self.MaxConnectionAttempts:
                try:
                    if self.target_mode == 2:
                        self.messagepack_mode()
                    else:
                        self.jsonlines_mode()
                    connected = True
                    # sample_mode = ads1299.HIGH_RES_16k_SPS | ads1299.CONFIG1_const
                    # self.wreg(ads1299.CONFIG1, sample_mode)
                    break
                except JSONDecodeError:
                    if attempts == 0:
                        print("Connecting...", end='')
                    elif attempts > 0:
                        print('.', end='')
                    sys.stdout.flush()
                    attempts += 1
                    time.sleep(self.ConnectionSleepTime)
            if attempts > 0:
                print()
            if not connected:
                raise HackEEGException("Can't connect to Arduino")
        self.sdatac()
        line = self.serial_port.readline()
        while line:
            line = self.serial_port.readline()

    # def connect(self):
    #     # self.mode = self._sense_protocol_mode()
    #     # if self.mode == self.TextMode:
    #     #     attempts = 0
    #     #     connected = False
    #     #     while attempts < self.MaxConnectionAttempts:
    #     try:
    #         self.jsonlines_mode()
    #         connected = True
    #     except JSONDecodeError:
    #         if attempts == 0:
    #             print("Connecting...", end='')
    #         elif attempts > 0:
    #             print('.', end='')
    #         sys.stdout.flush()
    #         attempts += 1
    #         time.sleep(self.ConnectionSleepTime)
    #     # if attempts > 0:
    #     #     print()
    #     # if not connected:
    #     #     raise HackEEGException("Can't connect to Arduino")
    #     self.sdatac()
    #     line = self.serial_port.readline()
    #     while line:
    #         line = self.serial_port.readline()

    def _serial_write(self, command):
        # self.serial_port.write(command)
        if isinstance(command, str):
            self.serial_port.write(command.encode())
        else:
            self.serial_port.write(command)
        self.serial_port.flush()

    # def _serial_write(self, command, serial_port='raw'):
    #     if serial_port == "raw":
    #         self.raw_serial_port.write(command.encode())
    #     else:
    #         self.serial_port.write(command)
    #     self.serial_port.flush()

    # def _serial_readline(self, serial_port=None):
    def _serial_readline(self, serial_port='raw'):
        if serial_port is None:
            line = self.serial_port.readline()
        elif serial_port == "raw":
            line = self.raw_serial_port.readline().decode()
        else:
            raise HackEEGException('Unknown serial port designator; must be either None or "raw"')
        return line

    def _serial_read_messagepack_message(self):
        message = self.message_pack_unpacker.unpack()
        if self.debug:
            print(f"message: {message}")
        return message

    def _decode_data(self, response):
        """decode ADS1299 sample status bits - datasheet, p36
        The format is:
        1100 + LOFF_STATP[0:7] + LOFF_STATN[0:7] + bits[4:7] of the GPIOregister"""
        error = False
        if (not self.quiet) or (self.debug):
            print(response)
        if response:
            if isinstance(response, dict):
                data = response.get(self.DataKey)
                if data is None:
                    data = response.get(self.MpDataKey)
                    # if type(data) is str:
                    if isinstance(data, str):
                        try:
                            data = base64.b64decode(data)
                        except binascii.Error:
                            print(f"incorrect padding: {data}")
                # if data and (type(data) is list) or (type(data) is bytes):
                if data and (isinstance(data, list) or isinstance(data, bytes)):
                    data_hex = ":".join("{:02x}".format(c) for c in data)
                    if error:
                        print(data_hex)
                    timestamp = int.from_bytes(data[0:4], byteorder='little')
                    sample_number = int.from_bytes(data[4:8], byteorder='little')
                    ads_status = int.from_bytes(data[8:11], byteorder='big')
                    ads_gpio = ads_status & 0x0f
                    loff_statn = (ads_status >> 4) & 0xff
                    loff_statp = (ads_status >> 12) & 0xff
                    extra = (ads_status >> 20) & 0xff

                    channel_data = []
                    for channel in range(0, 8):
                        channel_offset = 11 + (channel * 3)
                        sample = int.from_bytes(data[channel_offset:channel_offset + 3], byteorder='big', signed=True)
                        channel_data.append(sample)

                    response['timestamp'] = timestamp
                    response['sample_number'] = sample_number
                    response['ads_status'] = ads_status
                    response['ads_gpio'] = ads_gpio
                    response['loff_statn'] = loff_statn
                    response['loff_statp'] = loff_statp
                    response['extra'] = extra
                    response['channel_data'] = channel_data
                    response['data_hex'] = data_hex
                    response['data_raw'] = data
            else:
                response = data
        return response

    def set_debug(self, debug):
        self.debug = debug

    # def read_response(self, serial_port=None):
    def read_response(self, serial_port='raw'):
        """read a response from the Arduino– must be in JSON Lines mode"""
        message = self._serial_readline(serial_port=serial_port)
        try:
            response_obj = json.loads(message)
        except UnicodeDecodeError:
            response_obj = None
        except JSONDecodeError:
            response_obj = None
        if self.debug:
            print(f"read_response line: {message}")
        if self.debug:
            print("json response:")
            print(self.format_json(response_obj))
        return self._decode_data(response_obj)

    def read_rdatac_response(self):
        """read a response from the Arduino– JSON Lines or MessagePack mode are ok"""
        if self.mode == self.MessagePackMode:
            response_obj = self._serial_read_messagepack_message()
        else:
            message = self._serial_readline()
            try:
                response_obj = json.loads(message)
            except JSONDecodeError:
                response_obj = {}
                print()
                print(f"json decode error: {message}")
        if self.debug:
            print(f"read_response obj: {response_obj}")
        result = None
        try:
            result = self._decode_data(response_obj)
        except AttributeError:
            pass
        return result

    def format_json(self, json_obj):
        return json.dumps(json_obj, indent=4, sort_keys=True)

    def send_command(self, command, parameters=None):
        if self.debug:
            print(f"command: {command}  parameters: {parameters}")
        # commands are only sent in JSON Lines mode
        new_command_obj = {self.CommandKey: command, self.ParametersKey: parameters}
        new_command = str(json.dumps(new_command_obj)) # EXTREMELY IMPORTANT: convert to string, otherwise does not work
        # print(new_command)
        if self.debug:
            print("json command:")
            print(self.format_json(new_command_obj))
        self._serial_write(new_command)
        self._serial_write('\n')

    def send_text_command(self, command):
        new = command + '\n'
        self._serial_write(new.encode())

    # def execute_command(self, command, parameters=None, serial_port=None):
    def execute_command(self, command, parameters=None, serial_port='raw'):
        if parameters is None:
            parameters = []
        self.send_command(command, parameters)
        response = self.read_response(serial_port=serial_port)
        return response

    def _sense_protocol_mode(self):
        try:
            self.send_command("stop")
            self.send_command("sdatac")
            result = self.execute_command("nop")
            if self.ok(result):
                return self.JsonLinesMode
        except Exception:
            return self.TextMode

    def ok(self, response):
        return response.get(self.StatusCodeKey) == Status.Ok

    def wreg(self, register, value):
        command = "wreg"
        parameters = [register, value]
        return self.execute_command(command, parameters)

    def rreg(self, register):
        command = "rreg"
        parameters = [register]
        response = self.execute_command(command, parameters)
        return response

    def nop(self):
        return self.execute_command("nop")

    def boardledon(self):
        return self.execute_command("boardledon")

    def boardledoff(self):
        return self.execute_command("boardledoff")

    def ledon(self):
        return self.execute_command("ledon")

    def ledoff(self):
        return self.execute_command("ledoff")

    def micros(self):
        return self.execute_command("micros")

    def text_mode(self):
        return self.send_command("text")

    def reset(self):
        return self.execute_command("reset")

    def start(self):
        return self.execute_command("start")

    def stop(self):
        return self.execute_command("stop")

    def rdata(self):
        return self.execute_command("rdata")

    def version(self):
        result = self.execute_command("version")
        return result

    def status(self):
        return self.execute_command("status")

    def jsonlines_mode(self):
        old_mode = self.mode
        self.mode = self.JsonLinesMode
        if old_mode == self.TextMode:
            self.send_text_command("jsonlines")
            return self.read_response()
        if old_mode == self.JsonLinesMode:
            self.execute_command("jsonlines")

    def messagepack_mode(self):
        old_mode = self.mode
        self.mode = self.MessagePackMode
        if old_mode == self.TextMode:
            self.send_text_command("jsonlines")
            response = self.read_response()
            self.execute_command("messagepack")
            return response
        elif old_mode == self.JsonLinesMode:
            response = self.execute_command("messagepack")
            return response

    def rdatac(self):
        result = self.execute_command("rdatac", serial_port="raw")
        if self.ok(result):
            self.rdatac_mode = True
        return result

    def sdatac(self):
        if self.mode == self.JsonLinesMode:
            result = self.execute_command("sdatac")
        else:
            self.send_command("sdatac")
            result = self.read_response(serial_port="raw")
        self.rdatac_mode = False
        return result

    def stop_and_sdatac_messagepack(self):
        """used to smoothly stop data transmission while in MessagePack mode–
        mostly avoids exceptions and other hiccups"""
        self.send_command("stop")
        self.send_command("sdatac")
        self.send_command("nop")
        try:
            line = self.serial_port.read()
        except UnicodeDecodeError:
            line = self.raw_serial_port.read()

    def enable_channel(self, channel, gain=None):
        if gain is None:
            gain = ads1299.GAIN_1X
        temp_rdatac_mode = self.rdatac_mode
        if self.rdatac_mode:
            self.sdatac()
        command = "wreg"
        parameters = [ads1299.CHnSET + channel, ads1299.ELECTRODE_INPUT | gain]
        self.execute_command(command, parameters)
        if temp_rdatac_mode:
            self.rdatac()

    def disable_channel(self, channel):
        command = "wreg"
        parameters = [ads1299.CHnSET + channel, ads1299.PDn | ads1299.SHORTED]
        self.execute_command(command, parameters)

    def enable_all_channels(self, gain=None):
        for channel in range(1, 9):
            self.enable_channel(channel, gain)

    def disable_all_channels(self):
        for channel in range(1, 9):
            self.disable_channel(channel)

    def blink_board_led(self):
        self.execute_command("boardledon")
        time.sleep(0.3)
        self.execute_command("boardledoff")

    def locate_arduino_port(self):
        arduino_ports = [
        p.device for p in serial.tools.list_ports.comports() if 'Arduino' in p.description  # may need tweaking to match new arduinos
        ]

        if not arduino_ports:
            raise IOError("No Arduino found")
        if len(arduino_ports) > 1:
            warnings.warn('Multiple Arduinos found - using the first')

        return arduino_ports[0]

    def process_sample(self, result, samples, outhex=False):
        data = None
        channel_data = None
        if result:
            # raw = result
            # result = self._decode_data(result)
            status_code = result.get(self.MpStatusCodeKey)
            data = result.get(self.MpDataKey)
            samples.append(result)
            if status_code == Status.Ok and data:
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
                    if outhex:
                        print(data_hex)
                    for channel_number, sample in enumerate(channel_data):
                        print(f"{channel_number + 1}:{sample} ", end='')
                    print()
                # else:
                #     for channel_number, sample in enumerate(channel_data):
                #         print(f"{channel_number + 1}:{sample} ", end='')
                #     print()
            else:
                if not self.quiet:
                    print(data)
        else:
            print("no data to decode")
            print(f"result: {result}")

    def save2csv(self, data, filepath=None):
        if filepath is None:
            filepath = self.default_filepath
        if ~filepath.endswith('.csv'):
            filepath = "".join((filepath.rstrip('/'), '.csv'))
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        pd.DataFrame(data).to_csv(filepath)

    def save2parquet(self, data, filepath=None, parquet_engine='pyarrow'):
        if filepath is None:
            filepath = self.default_filepath
        if ~filepath.endswith('.parquet'):
            filepath = "".join((filepath.rstrip('/'), '.parquet'))
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        if parquet_engine == 'pyarrow':
            pd.DataFrame(data).to_parquet(filepath, engine=parquet_engine, index= False)
        else:
            pd.DataFrame(data).to_parquet(filepath, engine=parquet_engine, object_encoding='utf8', write_index= False)

    def main(self, max_samples=None, duration=None, speed=None):

        if max_samples is None:
            max_samples = self.max_samples

        if duration is None:
            duration = self.duration

        if speed is None:
            speed = self.speed

        max_sample_time = duration * speed
        print(max_sample_time)

        samples = []
        sample_counter = 0
        clock = 0

        end_time = time.perf_counter()
        start_time = time.perf_counter()
        while ((sample_counter < max_samples) and (sample_counter < max_sample_time)):
            result = self.read_rdatac_response()
            end_time = time.perf_counter()
            sample_counter += 1
            # if self.continuous_mode:
            #     self.read_keyboard_input()
            if self.mode == 2:
                samples.append(result)
            else:
                self.process_sample(result, samples)

        dur = end_time - start_time
        self.stop_and_sdatac_messagepack()
        self.blink_board_led()

        # print(pd.DataFrame(samples))
        self.save2csv(samples)
        self.save2parquet(samples)

        print(f"duration in seconds: {dur}")
        samples_per_second = sample_counter / dur
        print(f"samples per second: {samples_per_second}")
        # dropped_samples = self.find_dropped_samples(samples, sample_counter)
        # print(f"dropped samples: {dropped_samples}")