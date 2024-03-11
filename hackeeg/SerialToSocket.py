import socket
import threading
import serial

class SerialToSocket:
    # def __init__(self, serial_port_path, baudrate, socket_port):
    #     self.serial_port = serial.Serial(serial_port_path, baudrate=baudrate)
    #     self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     self.server_socket.bind(('localhost', socket_port))
    #     self.server_socket.listen(1)

        def __init__(self, serial_port, socket_port):
        self.serial_port = serial.Serial(serial_port_path, baudrate=baudrate)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('localhost', socket_port))
        self.server_socket.listen(1)

    def start(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            return client_socket

    def handle_client(self, client_socket):
        while True:
            data = self.serial_port.read(38)  # Read 38 bytes from the serial port
            client_socket.send(data)

# Usage:
sts = SerialToSocket('/dev/ttyS0', 9600, 12345)
sts.start()