# Python 3.11
# 2023-10-13

# Leonardo Fortaleza
# Canadian Space Mining Corporation (CSMC) / McGill University
# leonardo.fortaleza@mail.mcgill.ca
# leonardo.fortaleza@csmc-scms.ca

"""This driver module for the HackEEG device provides a Python interface for
communicating with the device over a serial connection. This module is for singleboard operation.

Seeveral adaptations were made to the original code by Adam Feuer (Starcat LLC) for
use of the HackEEG device with the Arduino Due.
Original repository: https://github.com/starcat-io/hackeeg-client-python (Apache License 2.0)

Main operation is through the HackEEGBoard class. The main command is scan, which can be called thusly:
    ```
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hackeeg import HackEEGBoard

    hackeeg = HackEEGBoard(debug=False)

    try:
        hackeeg.scan(duration=1, samples_per_second=16000)
    finally:
        # routine to properly close serial port
        hackeeg.raw_serial_port.close()
        tqdm.write('Port Closed')
    ```

    or

    ```
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import hackeeg

    hackeeg.hackeeg_scan(duration=1, samples_per_second=16000)
    ```

Classes
-------
HackEEGBoard
    The main class for communicating with the HackEEG device.

The driver supports the following modes of operation:
- Text mode
- JSON Lines mode
- MessagePack mode

The driver also supports the following commands:
- nop
- version
- boardledon
- boardledoff
- ledon
- ledoff
- micros
- text
- reset
- start
- stop
- rdata
- rdatac
- sdatac
- wreg
- rreg
- scan

Functions
---------
filter_24
    Converts a 24-bit value to scaled voltages.
filter_2scomplement_np
    Converts a 2's complement value to its decimal equivalent.
int_to_float
    Convert the int value out of the ADS into a value in scaled voltages.

Raises
------
HackEEGException
    For problems connecting to Arduino.
IOError
    If no Arduino is found on port lookup in HackEEG.locate_arduino_port().
ValueError
    Incorrect input values for HackEEG._isBase64().
"""

import base64
import binascii
from datetime import datetime
import io
import json
from json import JSONDecodeError
import os
from pathlib import Path
import sys
import time
import warnings

import msgpack
import numpy as np
import pandas as pd
import serial
import serial.tools.list_ports
from tqdm.autonotebook import tqdm

from . import ads1299

NUMBER_OF_SAMPLES = 100000
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
    """
    A class representing status codes used in the HackEEG driver.
    """
    Ok = 200
    BadRequest = 400
    Error = 500


class HackEEGException(Exception):
    """
    Exception raised for errors in the HackEEG driver.

    Attributes:
        None
    """
    pass


class HackEEGBoard:
    """
    The HackEEGBoard class is responsible for initializing the HackEEG Driver class, connecting to the Arduino board, 
    setting the communication mode to either JSON Lines or MessagePack, writing a command to the serial port, and reading 
    a line from the specified serial port and returning it as a string.

    Attributes
    ----------
    TextMode : int
        The text mode for the recording.
    JsonLinesMode : int
        The JSON Lines mode for the recording.
    MessagePackMode : int
        The MessagePack mode for the recording.
    CommandKey : str
        The command key for the recording.
    ParametersKey : str
        The parameters key for the recording.
    HeadersKey : str
        The headers key for the recording.
    DataKey : str
        The data key for the recording.
    DecodedDataKey : str
        The decoded data key for the recording.
    StatusCodeKey : str
        The status code key for the recording.
    StatusTextKey : str
        The status text key for the recording.
    MpCommandKey : str
        The MessagePack command key for the recording.
    MpParametersKey : str
        The MessagePack parameters key for the recording.
    MpHeadersKey : str
        The MessagePack headers key for the recording.
    MpDataKey : str
        The MessagePack data key for the recording.
    MpStatusCodeKey : str
        The MessagePack status code key for the recording.
    MpStatusTextKey : str
        The MessagePack status text key for the recording.
    MaxConnectionAttempts : int
        The maximum connection attempts before cancelling.
    ConnectionSleepTime : float
        The maximum wait time for connection before cancelling.

    Methods
    -------
    __init__(self, serial_port_path=None, baudrate=DEFAULT_BAUDRATE, debug=False, quiet=True,
                    max_samples=100000, duration=1, target_mode=2, samples_per_second=16000, MaxConnectionAttempts=10, ConnectionSleepTime=0.1)
        Initializes the HackEEG Driver class.
    connect(self)
        Connects to the Arduino board and sets the communication mode to either JSON Lines or MessagePack.
        If the connection fails, it retries a maximum of `MaxConnectionAttempts` = 10 times.
    _serial_write(self, command)
        Writes a command to the serial port.
    _serial_readline(self, serial_port='raw')
        Reads a line from the specified serial port and returns it as a string.
    """
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
                    max_samples=100000, duration=1, target_mode=2, samples_per_second=16000, MaxConnectionAttempts=10, ConnectionSleepTime=0.1):
        """
        Initializes the HackEEG Driver class.

        Parameters
        ----------
        serial_port_path : str, optional
            The path to the serial port, by default None
        baudrate : int, optional
            The baudrate for serial communication, by default DEFAULT_BAUDRATE = 115200
        debug : bool, optional
            Whether to print debug information, by default False
        quiet : bool, optional
            Whether to suppress output, by default True
        max_samples : int, optional
            The maximum number of samples to collect, by default 100000
        duration : int, optional
            The duration of the recording in seconds, by default 1
        target_mode : int, optional
            The target mode for the recording, by default 2
                0: text
                1: JSON Lines
                2: MessagePack
        speed : int, optional
            The sampling rate of the recording in samples per second, by default 16000
        MaxConnectionAttempts : int, optional, by default 10
            Maximum connection attempts before cancelling.
        ConnectionSleepTime: float, optional, by default 0.1 s
            Maximum wait time for connection before cancelling.
        """
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
        self.speed = samples_per_second

        if serial_port_path is None:
            self.serial_port_path = self.locate_arduino_port()
        else:
            self.serial_port_path = serial_port_path
        self.raw_serial_port = serial.serial_for_url(self.serial_port_path, baudrate=self.baudrate, timeout=ConnectionSleepTime)
        if self.debug:
            tqdm.write('Connected to Serial Port:')
            tqdm.write(self.raw_serial_port)
        self.raw_serial_port.reset_input_buffer()
        self.raw_serial_port.reset_output_buffer()
        self.serial_port= self.raw_serial_port
        self.message_pack_unpacker = msgpack.Unpacker(self.raw_serial_port,  raw=False, use_list=False)
        self.connect()

    def connect(self):
        """
        Connects to the Arduino board and sets the communication mode to either JSON Lines or MessagePack.
        If the connection fails, it retries a maximum of `MaxConnectionAttempts` = 10 times.
        """
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
                    break
                except JSONDecodeError:
                    if attempts == 0:
                        tqdm.write("Connecting...", end='')
                    elif attempts > 0:
                        tqdm.write('.', end='')
                    sys.stdout.flush()
                    attempts += 1
                    time.sleep(self.ConnectionSleepTime)
            if attempts > 0:
                tqdm.write()
            if not connected:
                raise HackEEGException("Can't connect to Arduino")
        self.sdatac()
        line = self.serial_port.readline()
        while line:
            line = self.serial_port.readline()

    def _serial_write(self, command):
        """
        Writes a command to the serial port.

        Args:
            command (str or bytes): The command to be written to the serial port.

        Returns:
            None
        """
        if isinstance(command, str):
            self.serial_port.write(command.encode())
        else:
            self.serial_port.write(command)
        self.serial_port.flush()

    def _serial_readline(self, serial_port='raw'):
        """
        Reads a line from the specified serial port and returns it as a string.

        Args:
            serial_port (str): The serial port to read from. Must be either None or "raw".

        Returns:
            str: The line read from the serial port.

        Raises:
            HackEEGException: If an unknown serial port designator is provided.
        """
        if serial_port is None:
            line = self.serial_port.readline()
        elif serial_port == "raw":
            # line = self.raw_serial_port.readline().decode()
            # line = self.raw_serial_port.readline().decode(errors='replace')
            line = self.raw_serial_port.readline().decode(errors='ignore')
            # line = self.raw_serial_port.readline()
        else:
            raise HackEEGException('Unknown serial port designator; must be either None or "raw"')
        return line

    def _serial_read_messagepack_message(self):
        """
        Reads a message from the serial port using MessagePack format.

        Returns:
        - message (bytes): The message read from the serial port.
        """
        message = self.message_pack_unpacker.unpack()
        if self.debug:
            tqdm.write(f"message: {message}")
        return message

    def _decode_data(self, response):
        """decode ADS1299 sample status bits - datasheet, p36
        The format is:
        1100 + LOFF_STATP[0:7] + LOFF_STATN[0:7] + bits[4:7] of the GPIOregister

        Args:
                response (str or bytes): The ADS1299 response to be decoded.

        Returns:
                decoded response (dict)

        """
        error = False
        if (not self.quiet) or (self.debug):
            tqdm.write(response)
        if response:
            # if isinstance(response, dict):
            try:
                data = response.get(self.DataKey)
            except (AttributeError, KeyError):
                data = response
            if data is None:
                data = response.get(self.MpDataKey)
                # if data:
                    # data = bytearray(data)
            # if type(data) is str:
            # if isinstance(data, str) or isinstance(data, bytes):
            # if self._isBase64(data):
            if isinstance(data, str):
                try:
                    data = base64.b64decode(data)
                except binascii.Error:
                    tqdm.write(f"incorrect padding: {data}")
                except TypeError:
                    # keep data as is
                    pass
            # if data and (type(data) is list) or (type(data) is bytes):
            # if data and (isinstance(data, list) or isinstance(data, bytes)):
            if data:
                try:
                    # data = bytearray(data)
                    data_hex = ":".join("{:02x}".format(c) for c in data)
                    if error:
                        tqdm.write(data_hex)
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
                except (UnicodeDecodeError, AttributeError, TypeError):
                    response = data
        return response

    def set_debug(self, debug):
        """
        Set the debug mode for the driver.

        Args:
            debug (bool): Whether to enable debug mode or not.
        """
        self.debug = debug

    def read_response(self, serial_port='raw'):
        """
        Read a response from the Arduino in JSON Lines mode.

        Important: Must be in JSON Lines mode.

        Args:
            serial_port (str): The serial port to read from. Defaults to 'raw'.

        Returns:
            The decoded data from the response object.
        """

        message = self._serial_readline(serial_port=serial_port)
        try:
            response_obj = json.loads(message)
        except UnicodeDecodeError:
            response_obj = None
        except JSONDecodeError:
            response_obj = None
        if self.debug:
            tqdm.write(f"read_response line: {message}")
        if self.debug:
            tqdm.write("json response:")
            tqdm.write(self.format_json(response_obj))
        return self._decode_data(response_obj)

    def read_rdatac_response(self):
        """Read a response from the Arduino in either JSON Lines or MessagePack modes."""
        if self.mode == self.MessagePackMode:
            buffer = self.flush_buffer()
            response_obj = buffer
        else:
            buffer = self._serial_readline()
            while isinstance(buffer, int):
                # this routine flushes the buffer of any non-JSONlines data
                buffer = self._serial_readline()
            message = buffer
            try:
                response_obj = json.loads(message)
            except JSONDecodeError:
                response_obj = {}
                tqdm.write()
                tqdm.write(f"json decode error: {message}")
        if self.debug:
            tqdm.write(f"read_response obj: {response_obj}")
        result = None
        try:
            result = self._decode_data(response_obj)
        except AttributeError:
            pass
        return result

    # def read_rdatac_response(self):
    #     """Read a response from the Arduino in either JSON Lines or MessagePack modes."""
    #     if self.mode == self.MessagePackMode:
    #         buffer = self._serial_read_messagepack_message()
    #         response_obj = buffer
    #     else:
    #         buffer = self._serial_readline()
    #         while isinstance(buffer, int):
    #             # this routine flushes the buffer of any non-JSONlines data
    #             buffer = self._serial_readline()
    #         message = buffer
    #         try:
    #             response_obj = json.loads(message)
    #         except JSONDecodeError:
    #             response_obj = {}
    #             tqdm.write()
    #             tqdm.write(f"json decode error: {message}")
    #     if self.debug:
    #         tqdm.write(f"read_response obj: {response_obj}")
    #     result = None
    #     try:
    #         result = self._decode_data(response_obj)
    #     except AttributeError:
    #         pass
    #     return result

    def flush_buffer(self, timeout=10, flushing_levels=3):
        if self.mode == self.MessagePackMode:
            start = time.perf_counter()
            dur = 0
            buffer = self._serial_read_messagepack_message()
            try:
                while isinstance(buffer, int) and (dur <= timeout):
                    # this routine flushes the buffer of any non-messagepack data
                    buffer = self.raw_serial_port.read_all()
                    buffer = self._serial_read_messagepack_message()
                    dur = time.perf_counter() - start

                    # if dur >= timeout:
                if isinstance(buffer, int) and (flushing_levels > 1):
                    tqdm.write('Flushing taking too long. Attempting to stop and restart sdatac.')
                    self.stop_and_sdatac_messagepack()
                    self.sdatac()
                    time.sleep(1)
                    # self.rdatac()
                    start2 = time.perf_counter()
                    while isinstance(buffer, int) and (dur <= timeout):
                        buffer = self._serial_read_messagepack_message()
                        dur = time.perf_counter() - start2
                if isinstance(buffer, int):
                    raise HackEEGException('Flushing buffer failed. Please try again.')
            except HackEEGException as error:
                tqdm.write(f'Flushing buffer failed. Please try again. Last message received: {buffer}')
                raise

        else:
            buffer = self._serial_readline()
            while isinstance(buffer, int):
                # this routine flushes the buffer of any non-JSONlines data
                buffer = self._serial_readline()
        return buffer

    def format_json(self, json_obj):
        """
        Formats a JSON object as a string with indentation and sorted keys.

        Args:
            json_obj (dict): The JSON object to format.

        Returns:
            str: The formatted JSON object as a string.
        """
        return json.dumps(json_obj, indent=4, sort_keys=True)

    def send_command(self, command, parameters=None):
        """
        Sends a command to the device over serial connection in JSON Lines mode.

        Args:
            command (str): The command to send to the device.
            parameters (dict, optional): A dictionary of parameters to include with the command. Defaults to None.

        Returns:
            None
        """
        if self.debug:
            tqdm.write(f"command: {command}  parameters: {parameters}")
        # commands are only sent in JSON Lines mode
        new_command_obj = {self.CommandKey: command, self.ParametersKey: parameters}
        new_command = str(json.dumps(new_command_obj)) # EXTREMELY IMPORTANT: convert to string, otherwise does not work
        if self.debug:
            tqdm.write("json command:")
            tqdm.write(self.format_json(new_command_obj))
        self._serial_write(new_command)
        self._serial_write('\n')

    def send_text_command(self, command):
        """
        Sends a text command to the device.

        Args:
            command (str): The command to send.

        Returns:
            None
        """
        new = command + '\n'
        self._serial_write(new.encode())

    def execute_command(self, command, parameters=None, serial_port='raw'):
        """
        Executes a command on the HackEEG device and returns the response.

        Args:
            command (str): The command to execute.
            parameters (list, optional): The parameters for the command. Defaults to None.
            serial_port (str, optional): The serial port to use. Defaults to 'raw'.

        Returns:
            str: The response from the device.
        """
        if parameters is None:
            parameters = []
        self.send_command(command, parameters)
        response = self.read_response(serial_port=serial_port)
        return response

    def _sense_protocol_mode(self):
        """Senses the protocol mode of the Arduino. Returns either Text Mode or JSON Lines Mode.
        """
        try:
            self.send_command("stop")
            self.send_command("sdatac")
            result = self.execute_command("nop")
            if self.ok(result):
                return self.JsonLinesMode
        except Exception:
            return self.TextMode

    def ok(self, response):
        """Checks if the response from the Arduino is OK."""
        return response.get(self.StatusCodeKey) == Status.Ok

    def wreg(self, register, value):
        """
        Writes a value to a register in the HackEEG device.

        Args:
            register (int): The register to write to.
            value (int): The value to write to the register.

        Returns:
            str: The response from the device.
        """
        command = "wreg"
        parameters = [register, value]
        return self.execute_command(command, parameters)

    def rreg(self, register):
        """
        Reads the value of a specified register from the HackEEG device.

        Args:
            register (int): The register number to read.

        Returns:
            str: The response from the device.
        """
        command = "rreg"
        parameters = [register]
        response = self.execute_command(command, parameters)
        return response

    def nop(self):
        """
        Sends a 'no operation' ('nop') command to the device and returns the response.
        """
        return self.execute_command("nop")

    def boardledon(self):
        """
        Sends a command to turn on the HackEEG Shield LED (blue) and returns the response from the board.
        """
        return self.execute_command("boardledon")

    def boardledoff(self):
        """
        Turns off the HackEEG Shield LED (blue).

        Returns:
        --------
        str:
            The response from the command execution.
        """
        return self.execute_command("boardledoff")

    def ledon(self):
        """
        Sends a command to turn on the Arduino Due onboard LED.

        Returns:
        -------
        str
            The response from the device after executing the command.
        """
        return self.execute_command("ledon")

    def ledoff(self):
        """
            Sends a command to turn off the Arduino Due onboard LED.

            Returns:
            -------
            str
                The response from the device after executing the command.
        """
        return self.execute_command("ledoff")

    def micros(self):
        """
        Returns the number of microseconds since the HackEEG board was last reset.

        Obtained by executing the 'micros' command in the Arduino board.
        """
        return self.execute_command("micros")

    def text_mode(self):
        """
        Sends a command to switch the device to text mode.

        Returns:
        str: The response from the device.
        """
        return self.send_command("text")

    def reset(self):
        """
        Resets the device by executing the "reset" command.
        """
        return self.execute_command("reset")

    def start(self):
        """
        Sends a command to start the EEG device and returns the response.

        Also resets the 'sample number' within the board.
        """
        return self.execute_command("start")

    def stop(self):
        """
        Sends a command to stop data acquisition.

        Returns:
        -------
        str
            The response from the device after executing the command.
        """
        return self.execute_command("stop")

    def rdata(self):
        """
        Reads one sample of data from the ADS129x chip.
        """
        return self.execute_command("rdata")

    def version(self):
        """
        Returns the driver version of the HackEEG device.
        """
        result = self.execute_command("version")
        return result

    def status(self):
        """
        Sends a command to the device to retrieve its status.

        Returns:
        str: The status of the device.
        """
        return self.execute_command("status")

    def jsonlines_mode(self):
        """
        Sets operation to JSON Lines Mode and returns the response from the device.
        """
        old_mode = self.mode
        self.mode = self.JsonLinesMode
        if old_mode == self.TextMode:
            self.send_text_command("jsonlines")
            return self.read_response()
        if old_mode == self.JsonLinesMode:
            self.execute_command("jsonlines")

    def messagepack_mode(self):
        """
        Sets operation to MessagePack mode and returns the response from the device.
        """
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
        """
        Enables a specified channel with a specified gain.

        If no gain is specified, the default gain is 1x.

        Args:
            channel (int): The channel to enable.
            gain (int, optional): The gain to use for the channel. Defaults to None.
                    Options are: 1, 2, 4, 6, 8, 12, 24

        Returns:
            None
        """
        if gain is None:
            gain = ads1299.GAIN_1X
        elif gain in (1,2,4,6,8,12,24):
            gain = GAINS[gain]
        elif gain in GAINS.values(): # if gain is already in the correct format for registers
            pass
        else:
            raise ValueError(f"Gain was {gain}, but gain must be 1, 2, 4, 6, 8, 12, or 24")
        temp_rdatac_mode = self.rdatac_mode
        if self.rdatac_mode:
            self.sdatac()
        command = "wreg"
        parameters = [ads1299.CHnSET + channel, ads1299.ELECTRODE_INPUT | gain]
        self.execute_command(command, parameters)
        if temp_rdatac_mode:
            self.rdatac()

    def disable_channel(self, channel):
        """
        Disables a specified channel on the ADS1299 chip by setting its power-down bit and shorting the inputs.

        Args:
        - channel (int): The channel number to disable (1-8).
        """
        command = "wreg"
        parameters = [ads1299.CHnSET + channel, ads1299.PDn | ads1299.SHORTED]
        self.execute_command(command, parameters)

    def enable_all_channels(self, gain=None):
        """
        Enables all channels of the HackEEG device with the specified gain (or the default gain if none).

        Args:
        - gain (float): the gain to set for all channels (optional). Defaults to None, resulting in 1x.
        """
        for channel in range(1, 9):
            self.enable_channel(channel, gain)

    def disable_all_channels(self):
        """Disables all channels of the HackEEG device."""
        for channel in range(1, 9):
            self.disable_channel(channel)

    def blink_board_led(self):
        """Blinks the HackEEG Shield LED (blue) on the Arduino board."""
        self.execute_command("boardledon")
        time.sleep(0.3)
        self.execute_command("boardledoff")

    def locate_arduino_port(self):
        """
        Locates the port where the Arduino is connected to the computer.

        Returns:
        str: The port where the Arduino is connected to the computer.

        Raises:
        IOError: If no Arduino is found.
        Warning: If multiple Arduinos are found, uses the first.
        """
        arduino_ports = [
            p.device for p in serial.tools.list_ports.comports() if 'Arduino' in p.description  # may need tweaking to match new arduinos
            ]

        if not arduino_ports:
            raise IOError("No Arduino found")
        if len(arduino_ports) > 1:
            warnings.warn('Multiple Arduinos found - using the first')

        return arduino_ports[0]

    def _isBase64(self, sb):
        """Identifies if input is Base64 encoded, returns bool.

        From: https://stackoverflow.com/questions/12315398/check-if-a-string-is-encoded-in-base64-using-python

        Parameters
        ----------
        sb : any
        input to determine whether Base64 encoded

        Returns
        -------
        bool
            'True' if input is string or byte with Base64 encoding, otherwise returns 'False'

        Raises
        ------
        ValueError
            "Argument must be string or bytes"
        """
        try:
            if isinstance(sb, str):
                # If there's any unicode here, an exception will be thrown and the function will return false
                sb_bytes = bytes(sb, 'ascii')
            elif isinstance(sb, bytes):
                sb_bytes = sb
            else:
                raise ValueError("Argument must be string or bytes")
            return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
        except Exception:
            return False

    def process_sample(self, result, samples, outhex=False):
        """
        Processes a sample of data received from the EEG device.

        Args:
            result (dict): A dictionary containing the sample data.
            samples (list): A list to which the sample will be appended.
            outhex (bool, optional): Whether to output the sample data in hexadecimal format. Defaults to False.
        """
        data = None
        channel_data = None
        if result:
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
                    tqdm.write(
                        f"timestamp:{timestamp} sample_number: {sample_number}| gpio:{ads_gpio} loff_statp:{loff_statp} loff_statn:{loff_statn}   ",
                        end='')
                    if outhex:
                        tqdm.write(data_hex)
                    for channel_number, sample in enumerate(channel_data):
                        tqdm.write(f"{channel_number + 1}:{sample} ", end='')
                    tqdm.write()
            else:
                if not self.quiet:
                    tqdm.write(data)
        else:
            tqdm.write("no data to decode")
            tqdm.write(f"result: {result}")

    def save2csv(self, data, filepath=None):
        """
        Saves data to a CSV file at the specified filepath.

        If no filepath is provided, the default filepath is used ('./data/{%Y-%m-%d_%H-%M-%S}_data.csv').

        Args:
        - data: the data to be saved to the CSV file. Can be a Pandas DataFrame or a list of lists.
        - filepath: the filepath where the CSV file will be saved. If not provided, the default filepath is used.

        Returns:
        None
        """
        if filepath is None:
            filepath = self.default_filepath
        if ~filepath.endswith('.csv'):
            filepath = "".join((filepath.rstrip('/'), '.csv'))
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)
        df.to_csv(filepath)

    def save2parquet(self, data, filepath=None, parquet_engine='pyarrow'):
        """
        Save data to a parquet file using the specified engine.

        If no filepath is provided, the default filepath is used ('./data/{%Y-%m-%d_%H-%M-%S}_data.parquet').

        Args:
            data (pd.DataFrame or list): The data to be saved to a parquet file.
            filepath (str): The path to the parquet file. If None, the default filepath will be used.
            parquet_engine (str): The engine to use for writing the parquet file. Defaults to 'pyarrow'.

        Returns:
            None
        """
        if filepath is None:
            filepath = self.default_filepath
        if ~filepath.endswith('.parquet'):
            filepath = "".join((filepath.rstrip('/'), '.parquet'))
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)
        if parquet_engine == 'pyarrow':
            df.to_parquet(filepath, engine=parquet_engine, index= False)
        else:
            df.to_parquet(filepath, engine=parquet_engine, object_encoding='utf8', write_index= False)

    def scan(self, max_samples=None, duration=None, samples_per_second=None, gain=1, process_data=True, save2parquet=True, save2csv=True, 
                find_dropped_samples=False, out_df=False, scale=1e-3, debug=False, channel_test=False, filepath = None):
        """
        Perform data scan using the HackEEG board and process it into a pandas DataFrame.

        Uses MessagePack Mode to allow for up to 16 ksps sampling rate.

        Args:
            max_samples (int, optional):
                The maximum number of samples to acquire. Defaults to None, which becomes 100,000.
            duration (float, optional):
                The duration of the acquisition in seconds. Defaults to None, which leads to 1 second.
            samples_per_second (int, optional):
                The sample rate in Hz. Defaults to None, which leads to 16 ksps.
            gain (int, optional):
                The gain to use for the acquisition. Defaults to 1.
                Options are: 1, 2, 4, 6, 8, 12, 24.
            process_data (bool, optional):
                Whether to process the DataFrame. Defaults to True.
            save2parquet (bool, optional):
                Whether to save the DataFrame to a parquet file. Defaults to True.
            save2csv (bool, optional):
                Whether to save the DataFrame to a CSV file. Defaults to True.
            find_dropped_samples (bool, optional):
                Whether to find and print the number of dropped samples. Defaults to False.
            out_df (bool, optional):
                Whether to return the DataFrame. Defaults to False.
            scale (float, optional):
                The scale to apply to the voltage data. Defaults to 1e-3 for milivolts.
            debug (bool, optional):
                Whether to activate debugging mode, by default False
            channel_test (bool, optional):
                Whether to activate channel test mode, by default False

        Returns:
            None or pd.DataFrame:
                The DataFrame containing the processed data (if out_df is set to 'True').
            """

        if samples_per_second is None:
            samples_per_second = self.speed

        self.debug = debug

        self.sdatac()
        self.reset()

        self.setup(samples_per_second=samples_per_second, gain=gain, messagepack=True, channel_test=channel_test)

        self.stop_and_sdatac_messagepack()
        self.sdatac()

        time.sleep(1)

        samples, sample_counter, dur = self.acquire_data(max_samples, duration, samples_per_second)

        if find_dropped_samples:
            dropped_samples = self.find_dropped_samples(samples, sample_counter)
            for s in np.arange(len(samples)):
                samples[s]["total_dropped_samples"] = dropped_samples
        df = pd.DataFrame(samples)
        if process_data:
            df = process_df(df, sample_counter=sample_counter, duration=dur, scale=scale, gain=gain)
        if save2csv:
            self.save2csv(df, filepath=filepath)
        if save2parquet:
            self.save2parquet(df, filepath=filepath)

        tqdm.write(f"duration in seconds: {dur}")
        samples_per_second = sample_counter / dur
        tqdm.write(f"samples per second: {samples_per_second}")
        if find_dropped_samples:
            tqdm.write(f"dropped samples: {dropped_samples}")
        self.reset()
        self.blink_board_led()
        if out_df:
            return df

    def scan_and_close(self, max_samples=None, duration=None, samples_per_second=None, gain=1, process_data=True, save2parquet=True, save2csv=True,
                    find_dropped_samples=False, out_df=False, scale=1e-3, debug=False, channel_test=False):
        """
        Perform data scan using the HackEEG board and close the serial port when finished.

        Uses MessagePack Mode to allow for up to 16 ksps sampling rate.

        Args:
            max_samples (int, optional):
                The maximum number of samples to acquire. Defaults to None, which becomes 100,000.
            duration (float, optional):
                The duration of the acquisition in seconds. Defaults to None, which leads to 1 second.
            samples_per_second (int, optional):
                The sample rate in Hz. Defaults to None, which leads to 16 ksps.
            gain (int, optional):
                The gain to use for the acquisition. Defaults to 1.
                Options are: 1, 2, 4, 6, 8, 12, 24.
            process_data (bool, optional):
                Whether to process the DataFrame. Defaults to True.
            save2parquet (bool, optional):
                Whether to save the DataFrame to a parquet file. Defaults to True.
            save2csv (bool, optional):
                Whether to save the DataFrame to a CSV file. Defaults to True.
            find_dropped_samples (bool, optional):
                Whether to find and print the number of dropped samples. Defaults to False.
            out_df (bool, optional):
                Whether to return the DataFrame. Defaults to False.
            scale (float, optional):
                The scale to apply to the voltage data. Defaults to 1e-3 for milivolts.
            debug (bool, optional):
                Whether to activate debugging mode, by default False
            channel_test (bool, optional):
                Whether to activate channel test mode, by default False

        Returns:
            None or pd.DataFrame:
                The DataFrame containing the processed data (if out_df is set to 'True').
        """
        try:
            df = self.scan(max_samples, duration, samples_per_second, gain, process_data, save2parquet, save2csv,
                                find_dropped_samples, out_df, scale, debug, channel_test)
        finally:
            # routine to properly close serial port
            self.raw_serial_port.close()
            tqdm.write('Port Closed')
            if out_df:
                return df

    def acquire_data(self, max_samples, duration, speed, display_output=False):
        """
        Acquires continuous data stream from the HackEEG device.

        Args:
            max_samples (int): The maximum number of samples to acquire.
            duration (float): The duration of the acquisition in seconds.
            speed (int): The sampling rate in Hz (or sps).
            display_output (bool, optional): Whether to display the acquired samples. Defaults to False.

        Returns:
            Tuple: A tuple containing the acquired samples, the number of samples acquired, and the duration of the acquisition.
        """

        if max_samples is None:
            max_samples = self.max_samples

        if duration is None:
            duration = self.duration

        if speed is None:
            speed = self.speed

        max_sample_time = duration * speed

        # self.start()

        samples = []
        sample_counter = 0

        self.rdatac()

        progress = tqdm(total = max_sample_time, miniters=1)
        tqdm.write("Flushing buffer...")
        result = self.read_rdatac_response() # initial data read to flush buffer and avoid sample miscounting
        # result = self.flush_buffer()

        tqdm.write("Acquiring data...")
        end_time = time.perf_counter()
        start_time = time.perf_counter()
        while ((sample_counter < max_samples) and (sample_counter < max_sample_time)):
            result = self.read_rdatac_response()
            end_time = time.perf_counter()
            sample_counter += 1
            progress.update(1)
            if self.mode == 2:  # MessagePack mode
                samples.append(result)
            else:
                self.process_sample(result, samples)

            # optional display of samples
            if display_output:
                tqdm.write(samples[-1])

        progress.close()
        tqdm.write(f'Buffer size: {len(result)}')

        dur = end_time - start_time
        self.stop_and_sdatac_messagepack()

        return samples, sample_counter, dur

    def find_dropped_samples(self, samples, number_of_samples):
        """
        Finds the number of missing samples in a given list of samples.

        Args:
        samples (list): A list of samples to check for missing samples.
        number_of_samples (int): The expected number of samples in the list.

        Returns:
        int: The number of missing samples in the list.
        """
        sample_numbers = {self.get_sample_number(sample): 1 for sample in samples}
        correct_sequence = {index: 1 for index in range(0, number_of_samples)}
        missing_samples = [sample_number for sample_number in correct_sequence.keys()
                        if sample_number not in sample_numbers]
        return len(missing_samples)

    def get_sample_number(self, sample):
        """
        Returns the sample number from the given sample dictionary.

        Args:
        - sample: A dictionary containing the sample data.

        Returns:
        - The sample number (int) if it exists in the dictionary, otherwise -1.
        """
        sample_number = sample.get('sample_number', -1)
        return sample_number

    def process_df(self, df, sample_counter, duration, scale=1e-3, gain=1):
        """
        Processes a Pandas DataFrame containing EEG data, including conversion of raw data to voltage values.

        Args:
        - df: A Pandas DataFrame containing EEG data.
        - sample_counter: The number of samples in the DataFrame.
        - duration: The duration of the recording in seconds.
        - scale: The scale to apply to the voltage data. Defaults to 1e-3 for milivolts.
        - gain: The gain setting used for the recording. Defaults to 1.

        Returns:
        - df: The processed DataFrame.
        """
        df['total_samples'] = sample_counter
        df['total_duration'] = duration
        df['avg_sample_rate'] = sample_counter / duration
        df['gain'] = gain
        df['num_chs'] = len(df['channel_data'][0])
        for ch in np.arange(1, len(df.loc[0,'channel_data']) + 1):
            df[f'raw_ch{ch:02d}'] = df['channel_data'].apply(lambda x: x[ch-1])
            df[f'ch{ch:02d}'] = df[f'raw_ch{ch:02d}'].apply(lambda x: int_to_float(x, scale)) # convert to milivolts
        if scale == 1e-3:
            df['ch_unit'] = 'mV'
        elif scale == 1e-6:
            df['ch_unit'] = 'uV'
        elif scale == 1e-9:
            df['ch_unit'] = 'nV'
        elif scale == 1:
            df['ch_unit'] = 'V'
        else:
            df['ch_unit'] = f'{scale:0.0e}'

        return df

    def setup(self, samples_per_second=16000, gain=1, messagepack=True, channel_test=False):
        """
        Configures the HackEEG board with the specified settings.

        Args:
            samples_per_second (int) (optional): The number of samples per second to collect. Must be a valid speed. Default is 16000.
            gain (int) (optional): The gain to use for the channels. Must be within 1, 2, 4, 6, 8, 12, 24. Default is 1.
            messagepack (bool) (optional): Whether to use messagepack mode or jsonlines mode. Default is True.
            channel_test (bool) (optional): Whether to run a channel test or not. Default is False.

        Raises:
            HackEEGException: If an invalid speed or gain is specified.

        Returns:
            None
        """

        if samples_per_second not in SPEEDS.keys():
            raise HackEEGException("{} is not a valid speed; valid speeds are {}".format(
                samples_per_second, sorted(SPEEDS.keys())))
        if gain not in GAINS.keys():
            raise HackEEGException("{} is not a valid gain; valid gains are {}".format(
                gain, sorted(GAINS.keys())))

        # self.stop_and_sdatac_messagepack()
        # self.sdatac()
        self.blink_board_led()
        sample_mode = SPEEDS[samples_per_second] | ads1299.CONFIG1_const
        self.wreg(ads1299.CONFIG1, sample_mode)

        gain_setting = GAINS[gain]

        self.disable_all_channels()
        if channel_test:
            self.channel_config_test()
        else:
            # self.channel_config_input(gain_setting)
            self.enable_all_channels(gain=gain_setting)


        # Route reference electrode to SRB1: JP8:1-2, JP7:NC (not connected)
        # use this with humans to reduce noise
        #self.wreg(ads1299.MISC1, ads1299.SRB1 | ads1299.MISC1_const)

        # Single-ended mode - setting SRB1 bit sends mid-supply voltage to the N inputs
        # use this with a signal generator
        # self.wreg(ads1299.MISC1, ads1299.SRB1)

        # Dual-ended mode
        # self.wreg(ads1299.MISC1, ads1299.MISC1_const)
        # add channels into bias generation
        # self.wreg(ads1299.BIAS_SENSP, ads1299.BIAS8P)

        if messagepack:
            self.messagepack_mode()
        else:
            self.jsonlines_mode()
        self.start()
        return

    def channel_config_input(self, gain_setting):
        """
        Configures the input channels of the HackEEG device with the specified gain setting.

        Args:
            gain_setting (int): The gain setting to use for the channels.

        Returns:
            None
        """
        # all channels enabled
        # for channel in range(1, 9):
        #     self.wreg(ads1299.CHnSET + channel, ads1299.TEST_SIGNAL | gain_setting )

        # self.wreg(ads1299.CHnSET + 1, ads1299.INT_TEST_DC | gain_setting)
        # self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.INT_TEST_DC | gain_setting)
        self.wreg(ads1299.CHnSET + 1, ads1299.ELECTRODE_INPUT | gain_setting)
        self.wreg(ads1299.CHnSET + 2, ads1299.ELECTRODE_INPUT | gain_setting)
        self.wreg(ads1299.CHnSET + 3, ads1299.ELECTRODE_INPUT | gain_setting)
        self.wreg(ads1299.CHnSET + 4, ads1299.ELECTRODE_INPUT | gain_setting)
        self.wreg(ads1299.CHnSET + 5, ads1299.ELECTRODE_INPUT | gain_setting)
        self.wreg(ads1299.CHnSET + 6, ads1299.ELECTRODE_INPUT | gain_setting)
        self.wreg(ads1299.CHnSET + 7, ads1299.ELECTRODE_INPUT | gain_setting)
        self.wreg(ads1299.CHnSET + 8, ads1299.ELECTRODE_INPUT | gain_setting)

    def channel_config_test(self):
        """
        Configures the channels for testing purposes.
        Sets the test signal mode, gain, and channel settings for each channel.
        Disables the 8th channel.
        """
        test_signal_mode = ads1299.INT_TEST_4HZ | ads1299.CONFIG2_const
        self.wreg(ads1299.CONFIG2, test_signal_mode)
        self.wreg(ads1299.CHnSET + 1, ads1299.INT_TEST_DC | ads1299.GAIN_1X)
        self.wreg(ads1299.CHnSET + 2, ads1299.SHORTED | ads1299.GAIN_1X)
        self.wreg(ads1299.CHnSET + 3, ads1299.MVDD | ads1299.GAIN_1X)
        self.wreg(ads1299.CHnSET + 4, ads1299.BIAS_DRN | ads1299.GAIN_1X)
        self.wreg(ads1299.CHnSET + 5, ads1299.BIAS_DRP | ads1299.GAIN_1X)
        self.wreg(ads1299.CHnSET + 6, ads1299.TEMP | ads1299.GAIN_1X)
        self.wreg(ads1299.CHnSET + 7, ads1299.TEST_SIGNAL | ads1299.GAIN_1X)
        self.disable_channel(8)

def filter_24(value, scale=1e-3):
    """
    Converts a 24-bit value to scaled voltages.

    Adapted from source: Portiloop repository (https://github.com/MISTLab/Portiloop)

    Args:
        value (int): A 24-bit value.
        scale (float, optional): The scale to apply to the value. Defaults to 1e-3 for milivolts.

    Returns:
        float: The value converted to scaled voltages.
    """
    # scale = 1e-3 applied for milivolts, 1e-6 for microvolts in the original code
    return (value * 4.5) / (2**23 - 1) / 24.0 / scale  # 23 because 1 bit is lost for sign

def filter_2scomplement_np(value):
    """
    Converts a 2's complement value to its decimal equivalent.

    Source: Portiloop repository (https://github.com/MISTLab/Portiloop)

    Args:
        value (int): The 2's complement value to be converted.

    Returns:
        int: The decimal equivalent of the 2's complement value.
    """
    return np.where((value & (1 << 23)) != 0, value - (1 << 24), value)

def int_to_float(value, scale=1e-3):
    """
    Convert the int value out of the ADS into a value in scaled voltages.

    Source: Portiloop repository (https://github.com/MISTLab/Portiloop)

    Args:
        value (int): The value to be converted.
        scale (float, optional): The scale to apply to the value. Defaults to 1e-3 for milivolts.

    Returns:
        float: The value converted to scaled voltages.
    """
    return filter_24(filter_2scomplement_np(value), scale)

def process_df(df, sample_counter, duration, scale=1e-3, gain=1):
    """
    Processes a Pandas DataFrame containing EEG data, including conversion of raw data to voltage values.

    Args:
    - df: A Pandas DataFrame containing EEG data.
    - sample_counter: The number of samples in the DataFrame.
    - duration: The duration of the recording in seconds.
    - scale: The scale to apply to the voltage data. Defaults to 1e-3 for milivolts.
    - gain: The gain setting used for the recording. Defaults to 1.

    Returns:
    - df: The processed DataFrame.
    """
    df['total_samples'] = sample_counter
    df['total_duration'] = duration
    df['avg_sample_rate'] = sample_counter / duration
    df['gain'] = gain
    df['num_chs'] = len(df['channel_data'][0])
    for ch in np.arange(1, len(df.loc[0,'channel_data']) + 1):
        df[f'raw_ch{ch:02d}'] = df['channel_data'].apply(lambda x: x[ch-1])
        df[f'ch{ch:02d}'] = df[f'raw_ch{ch:02d}'].apply(lambda x: int_to_float(x, scale)) # convert to milivolts
    if scale == 1e-3:
        df['ch_unit'] = 'mV'
    elif scale == 1e-6:
        df['ch_unit'] = 'uV'
    elif scale == 1e-9:
        df['ch_unit'] = 'nV'
    elif scale == 1:
        df['ch_unit'] = 'V'
    else:
        df['ch_unit'] = f'{scale:0.0e}'

    return df

def hackeeg_scan(hackeeg=None, max_samples=None, duration=None, samples_per_second=None, gain=1, process_data=True, save2parquet=True,             save2csv=True,
                find_dropped_samples=False, out_df=False, scale=1e-3, debug=False, channel_test=False, filepath=None):
    """
    Perform data scan using the HackEEG board and close the serial port when finished.

    Uses MessagePack Mode to allow for up to 16 ksps sampling rate.

    Args:
        hackeeg (class, optional):
            Instance of the HackEEGBoard class.
        max_samples (int, optional):
            The maximum number of samples to acquire. Defaults to None, which becomes 100,000.
        duration (float, optional):
            The duration of the acquisition in seconds. Defaults to None, which leads to 1 second.
        samples_per_second (int, optional):
            The sample rate in Hz. Defaults to None, which leads to 16 ksps.
        gain (int, optional):
            The gain to use for the acquisition. Defaults to 1.
            Options are: 1, 2, 4, 6, 8, 12, 24.
        process_data (bool, optional):
            Whether to process the DataFrame. Defaults to True.
        save2parquet (bool, optional):
            Whether to save the DataFrame to a parquet file. Defaults to True.
        save2csv (bool, optional):
            Whether to save the DataFrame to a CSV file. Defaults to True.
        find_dropped_samples (bool, optional):
            Whether to find and print the number of dropped samples. Defaults to False.
        out_df (bool, optional):
            Whether to return the DataFrame. Defaults to False.
        scale (float, optional):
            The scale to apply to the voltage data. Defaults to 1e-3 for milivolts.
        debug (bool, optional):
            Whether to activate debugging mode, by default False
        channel_test (bool, optional):
            Whether to activate channel test mode, by default False

    Returns:
        None or pd.DataFrame:
            The DataFrame containing the processed data (if out_df is set to 'True').
    """
    try:
        if hackeeg is None:
            hackeeg = HackEEGBoard(debug=debug)

        df = hackeeg.scan(max_samples, duration, samples_per_second, gain, process_data, save2parquet, save2csv,
                            find_dropped_samples, out_df, scale, debug, channel_test, filepath)

    finally:
        # routine to properly close serial port
        hackeeg.raw_serial_port.close()
        tqdm.write('Port Closed')
        if out_df:
            return df