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
import warnings

import numpy as np
import scipy.io as sio
from scipy import signal
from PyQt5.QtCore import QTimer

import hackeeg
from hackeeg import ads1299

# DATA_LIST_TEMP_CH = [[]]  # data pool
# DATA_QUEUE_TEMP_CH = queue.Queue()  # Queues for data storage
#
# class FileSettings:
#     """_summary_

#     Based upon BEATS (https://github.com/buptantEEG/BEATS/).
#     """
#     def __init__(self) -> None:
#          # initial save_data
#         self.save_data_queue = queue.Queue()
#         self.save_counter = 1
#         self.save_all_data = []
#         self.save_all_status = []
#         self.save_start_time_stamp = 0
#         self.save_time = 5
#         self.sample_rate = 16000
#         self.package_length = 800
#         self.save_pkg_length = self.sample_rate / self.package_length * self.save_time
#         self.saving_data=False
#         self.is_filt = False

#         # initial stimulation parameters
#         self.start_time = 0
#         self.sti_times = []
#         self.sti_event = []
#         self.sti_point = []

#         # front overlap
#         self.overlap_begin = [[] for i in range(self.channel_num)]
#         self.overlap_end = [[] for i in range(self.channel_num)]
#         self.before_data = [[] for i in range(self.channel_num)]

#     def save_data(self, filepath='./Data'):
#         self.timer_save_data = QTimer()
#         self.timer_save_data.start(self.save_time)
#         if not os.path.exists(filepath):
#              os.mkdir(filepath)
#         while self.save_data_queue.empty() == False:
#         #
#         # print(self.save_data_queue.empty())
#         # self.statusBar.showMessage('saving data...')
#             datapool = self.save_data_queue.get()
#             if (datapool == 'end'):
#                 # print('save_pkg_length ', save_pkg_length)
#                 # if not longer than save_pkg_length，the data is not saved automatically and save it here
#                 if len(self.save_all_data)!=0:
#                     sio.savemat('./Data/data' + str(int(self.save_counter / self.save_pkg_length) + 1) + '.mat',
#                                 mdict={'data': self.save_all_data, 'status': self.save_all_status, 'time_stamp':self.save_start_time_stamp})
#                 else:
#                     # print('No more data~')
#                     pass
#                 self.save_all_data = []
#                 self.save_all_status = []
#                 self.timer_save_data.stop()
#                 self.stack_data()
#             else:
#                 # print('p_save ', type(datapool), len(datapool))
#                 if (self.save_counter == 1):
#                     self.save_start_time_stamp = datapool['time_stamp']
#                 self.save_all_data.extend(datapool['dec_data'])
#                 self.save_all_status.extend(datapool['status'])
#                 if (self.save_counter % self.save_pkg_length == 0):
#                     sio.savemat('./Data/data' + str(int(self.save_counter / self.save_pkg_length)) + '.mat',
#                                 mdict={'data': self.save_all_data, 'status': self.save_all_status, 'time_stamp': self.save_start_time_stamp})
#                     self.save_all_data = []
#                     self.save_all_status = []
#                 self.save_counter += 1
#                 # time.sleep(0.1)

#     def stack_data(self):
#         # self.statusBar.showMessage('Stacking and saving data...')
#         path = './Data/'
#         files = os.listdir(path)
#         if len(files)!=0:
#             files.sort(key=lambda x: int(x[4:-4]))
#             # print(files[0])

#             for file in files:
#                 if file == files[0]:
#                     dataFile = sio.loadmat(path + file)
#                     data = dataFile['data']
#                     self.start_time = dataFile['time_stamp'][0][0]
#                     # print("start time: ", self.start_time)
#                 else:
#                     tempFile = sio.loadmat(path + file)
#                     tempData = tempFile['data']
#                     data = np.vstack((data, tempData))
#             # print(self.sti_times)
#             for i in range(len(self.sti_times)):
#                 self.sti_point.append(int(round((self.sti_times[i] - self.start_time) * self.sample_rate)))

#             sio.savemat('./data_stacked.mat',
#                         mdict={'data': data, 'events': self.sti_event, 'event_time': self.sti_point,
#                                'exp_start_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))})
#             # self.statusBar.showMessage('All data saved!')
#         # print("saved!")

#         # def tcp_server_init(self):
#         # """
#         # """
#         # self.sockServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         # self.sockServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         # self.sockServer.bind(self.server_addr)
#         # self.is_socket_seted=True
#         # print('ready for receiving!')

#     def thread_tcp_server(self):
#         """
#         thread for tcp server
#         :return:
#         """
#         try:
#             self.statusBar.showMessage('Connecting...')
#             self.sockServer.listen(10)
#             self.conn, client_addr = self.sockServer.accept()
#             self.statusBar.showMessage('Connection success!')
#             self.is_connected=True

#         except Exception as e:
#             print(e)
#             pass

#         while (self.EEG_is_running==True and self.is_connected==True):
#             # print(self.is_connected)
#             receive_length = self.conn.recv(4)
#             # print('eee')
#             if receive_length == b'':

#                 break
#             data_length = struct.unpack('i', receive_length)[0]
#             # print(data_length)
#             # dataRecv = (clientSock.recv(data_length)).decode('utf-8')

#             # Python socket can only read all the data of the buffer at most at one time.
#             # If the size of the specified data packet is larger than the size of the buffer,
#             # the valid data read is only the data of the buffer.
#             # If it can be determined that the data sent is larger than the size of the buffer, multiple times are required:
#             # socket.recv(receiverBufsize)
#             # and then the received data is spliced into a complete data packet and then parsed.
#             receive_data = []
#             while data_length > 0:
#                 if data_length > self.BUFFER_SIZE:
#                     temp = self.conn.recv(self.BUFFER_SIZE)
#                 else:
#                     temp = self.conn.recv(data_length)
#                 receive_data.append(temp)
#                 data_length = data_length - len(temp)
#             receive_data = b''.join(receive_data).decode('utf-8')
#             # reference: https://www.cnblogs.com/luckgopher/p/4816919.html
#             temp_data = json.loads(receive_data)
#             # display_queue.put(data)

#             data = list(map(list, zip(*temp_data["dec_data"])))
#             data = data[0:self.channel_num]
#             # if len(DATA_LIST_TEMP_CH[0])==0:
#             #     timetemp1=time.time()
#             # elif len(DATA_LIST_TEMP_CH[0])%32000==0:
#             #     print(time.time()-timetemp1)

#             # detrend_data=detrend(data)
#             # self.overlap_end = [i[::-1] for i in data]

#             if self.is_filt:
#                 stackdata = np.hstack(
#                     (np.array(self.overlap_begin), np.array(self.before_data), np.array(self.overlap_end)))
#                 # print(stackdata.shape )
#                 listdata = stackdata.tolist()
#                 # print("data:",len(listdata[1]))
#                 # print(len(listdata[1]))
#                 if listdata[1][self.package_length:-self.package_length]:
#                     filtedData = signal.filtfilt(self.b, self.a, listdata)
#                     # print("filtdata:",len(filtedData[1]))
#                     filtedData = [i[self.package_length:-self.package_length] for i in filtedData]
#                     # print("no_overlap_data:",len(filtedData[1]))
#                     for i in range(self.channel_num):
#                         # DATA_LIST_TEMP_CH[i].extend(detrend(filtedData[i]))
#                         DATA_LIST_TEMP_CH[i].extend(filtedData[i])
#                     # DATA_QUEUE_TEMP_CH.put(filtedData)
#                     # print(1)
#                     # temp_data["dec_data"] = np.array(filtedData).T
#                     # if self.is_save_data:
#                     #     self.save_data_queue.put(temp_data)

#                 self.overlap_begin = self.before_data
#                 # self.before_data = [i[-50:] for i in data]
#                 self.before_data = self.overlap_end
#                 self.overlap_end = data
#                 # print(data)


#             elif not self.is_filt:
#                 for i in range(self.channel_num):
#                     DATA_LIST_TEMP_CH[i].extend(data[i])
#                 # DATA_QUEUE_TEMP_CH.put(data)
#                 # print(1)
#             if self.is_save_data:
#                 self.save_data_queue.put(temp_data)

#     def tcp_close(self):
#         """
#         Function to close the network connection
#         """
#         # if self.sockServer:
#         self.is_connected = False
#         self.conn.close()

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

try:
    hackeeg.connect()
    hackeeg.sdatac()
    hackeeg.reset()
    hackeeg.blink_board_led()
    hackeeg.disable_all_channels()
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

    while True:
        result = hackeeg.read_response()
        status_code = result.get('STATUS_CODE')
        status_text = result.get('STATUS_TEXT')
        data = result.get(hackeeg.DataKey)
        if data:
            decoded_data = result.get(hackeeg.DecodedDataKey)
            if decoded_data:
                timestamp = decoded_data.get('timestamp')
                ads_gpio = decoded_data.get('ads_gpio')
                loff_statp = decoded_data.get('loff_statp')
                loff_statn = decoded_data.get('loff_statn')
                channel_data = decoded_data.get('channel_data')
                print(f"timestamp:{timestamp} | gpio:{ads_gpio} loff_statp:{loff_statp} loff_statn:{loff_statn} |   ",
                    end='')
                for channel_number, sample in enumerate(channel_data):
                    print(f"{channel_number + 1}:{sample} ", end='')
                print()
            else:
                print(data)
            sys.stdout.flush()

finally:
    hackeeg.raw_serial_port.close()
    print('Port Closed')