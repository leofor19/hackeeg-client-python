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

        # if serial_port_path is None:
        #     self.serial_port_path = self.locate_arduino_port()
        # else:
        #     self.serial_port_path = serial_port_path
        # self.raw_serial_port = serial.serial_for_url(self.serial_port_path, baudrate=self.baudrate, timeout=ConnectionSleepTime)
        self.raw_serial_port = 'COM2'
        if self.debug:
            tqdm.write('Connected to Serial Port:')
            tqdm.write(self.raw_serial_port)
        # self.raw_serial_port.reset_input_buffer()
        # self.raw_serial_port.reset_output_buffer()
        self.serial_port= self.raw_serial_port
        self.message_pack_unpacker = msgpack.Unpacker(self.raw_serial_port,  raw=False, use_list=False)

    def flush_buffer(self, timeout=2, flushing_levels=3):
        """
        Flushes the buffer of any non-messagepack or non-JSONlines data.

        Args:
            timeout (int, optional): The maximum time to wait for flushing to complete, in seconds. Defaults to 2.
            flushing_levels (int, optional): The number of times to attempt flushing before raising an exception. Defaults to 3.

        Raises:
            HackEEGException: If flushing the buffer fails after the specified number of attempts.

        Returns:
            The flushed buffer.
        """
        if self.mode == self.MessagePackMode:
            start = time.perf_counter()
            dur = 0
            buffer = self._serial_read_messagepack_message()
            try:
                while isinstance(buffer, int) and (dur <= timeout):
                    # this routine flushes the buffer of any non-messagepack data
                    # buffer = self.raw_serial_port.read_all()
                    buffer = self._serial_read_messagepack_message()
                    dur = time.perf_counter() - start

                    # if dur >= timeout:
                if isinstance(buffer, int) and (flushing_levels > 1):
                    for flush in np.arange(2, flushing_levels + 1):
                        tqdm.write(f'Flushing taking too long. Attempting to stop and restart sdatac. Flush attempt: {flush}')
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
            start = time.perf_counter()
            dur = 0
            buffer = self._serial_readline()
            try:
                while isinstance(buffer, int) and (dur <= timeout):
                    # this routine flushes the buffer of any non-JSONlines data
                    buffer = self._serial_readline()
                    dur = time.perf_counter() - start
                if isinstance(buffer, int) and (flushing_levels > 1):
                    for flush in np.arange(2, flushing_levels + 1):
                        tqdm.write(f'Flushing taking too long. Attempting to stop and restart sdatac. Flush attempt: {flush}')
                        self.stop()
                        self.sdatac()
                        time.sleep(1)
                        # self.rdatac()
                        start2 = time.perf_counter()
                        while isinstance(buffer, int) and (dur <= timeout):
                            buffer = self._serial_readline()
                            dur = time.perf_counter() - start2
                if isinstance(buffer, int):
                        raise HackEEGException('Flushing buffer failed. Please try again.')
            except HackEEGException as error:
                tqdm.write(f'Flushing buffer failed. Please try again. Last message received: {buffer}')
                raise

        return buffer

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
        # except (UnicodeDecodeError, AttributeError, TypeError):
        #     pass
        except (UnicodeDecodeError, AttributeError, TypeError):
            try:
                response_obj = self.flush_buffer(timeout=0.1, flushing_levels=1) # attempts to reflush buffer
                result = self._decode_data(response_obj)
            except (UnicodeDecodeError, AttributeError, TypeError):
                result = response_obj
        return result

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

            # self.rdatac()

            progress = tqdm(total = max_sample_time, miniters=1)
            tqdm.write("Flushing buffer...")
            # result = self.raw_serial_port.read_all() # initial data read_all
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
            # self.stop_and_sdatac_messagepack()

            return samples, sample_counter, dur

if __name__ == "__main__":
    hackeeg = HackEEGBoard()
    hackeeg.acquire_data(max_samples=100000, duration=1, speed=16000, display_output=True)
    hackeeg.raw_serial_port.close()