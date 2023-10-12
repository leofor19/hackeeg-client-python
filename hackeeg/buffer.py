# Python 3.11

import serial
import platform

is_windows = platform.system() == "Windows"
if is_windows:
    import msvcrt
else:
    import select


class Buffer:
    def __init__(self, serial_port, buffer_size, write_threshold, output_file, baudrate=115200, is_windows=is_windows):
        self.serial_port = serial_port
        self.buffer_size = buffer_size
        self.write_threshold = write_threshold
        self.output_file = output_file
        self.baudrate = baudrate
        self.buffer = bytearray(buffer_size)
        self.buffer_index = 0
        self.ser = None
        self.is_windows = is_windows

    def open_serial_port(self):
        try:
            self.ser = serial.Serial(self.serial_port, baudrate=self.baudrate)  # Replace with your desired baudrate
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")

    def close_serial_port(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()

    def collect_and_write_data(self):
        self.open_serial_port()
        try:
            with open(self.output_file, 'wb') as f:
                while True:
                    if self.is_windows:
                        if msvcrt.kbhit():  # Check for keyboard input (non-blocking) on Windows
                            key = msvcrt.getch()
                            if key == b'\x03':  # Check for Ctrl+C (KeyboardInterrupt)
                                break
                        else:
                            if self.ser.in_waiting > 0:
                                data = self.ser.read(1)
                                if data:
                                    self.buffer[self.buffer_index] = data[0]
                                    self.buffer_index += 1

                    else:
                        # Check if there is data available to read from the serial port
                        if select.select([self.ser], [], [], 0.1)[0]:
                            data = self.ser.read(1)  # Read one byte at a time, adjust as needed
                            if data:
                                self.buffer[self.buffer_index] = data[0]
                                self.buffer_index += 1

                    if self.buffer_index >= self.write_threshold:
                        try:
                            f.write(self.buffer[:self.buffer_index])
                        except Exception as e:
                            print(f"Error writing data: {e}")
                        self.buffer_index = 0

        except KeyboardInterrupt:
            pass
        finally:
            self.close_serial_port()

    def write_buffer_to_file(self):
        try:
            with open('output_file.txt', 'wb') as f:  # Replace 'output_file' with your actual output file or device
                f.write(self.buffer[:self.buffer_index])
        except Exception as e:
            print(f"Error writing data: {e}")

if __name__ == "__main__":
    serial_port = "/dev/ttyUSB0" if not platform.system() == "Windows" else "COM1"  # Replace with your serial port
    buffer_size = 1024  # Adjust the buffer size as needed
    write_threshold = 512  # Adjust the threshold as needed
    output_file = 'output_file'  # Replace with your actual output file

    buffer_instance = Buffer(serial_port, buffer_size, write_threshold, output_file)
    buffer_instance.collect_and_write_data()
