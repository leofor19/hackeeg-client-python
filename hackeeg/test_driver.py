from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hackeeg.driver import HackEEGBoard
# from driver import Driver

class TestDriver(unittest.TestCase):
    def setUp(self):
        self.driver = unittest.mock.create_autospec(HackEEGBoard)

    def test_read_rdatac_response_json(self):
        # Test reading a JSON response
        self.driver.mode = self.driver.JSONMode
        self.driver._serial_readline = MagicMock(return_value='{"key": "value"}')
        result = self.driver.read_rdatac_response()
        self.assertEqual(result, {"key": "value"})

    def test_read_rdatac_response_msgpack(self):
        # Test reading a MessagePack response
        self.driver.mode = self.driver.MessagePackMode
        self.driver.flush_buffer = MagicMock(return_value=b'\x81\xa3key\xa5value')
        result = self.driver.read_rdatac_response()
        self.assertEqual(result, {"key": "value"})

    def test_read_rdatac_response_invalid_json(self):
        # Test reading an invalid JSON response
        self.driver.mode = self.driver.JSONMode
        self.driver._serial_readline = MagicMock(return_value='invalid json')
        result = self.driver.read_rdatac_response()
        self.assertEqual(result, {})

    def test_read_rdatac_response_invalid_msgpack(self):
        # Test reading an invalid MessagePack response
        self.driver.mode = self.driver.MessagePackMode
        self.driver.flush_buffer = MagicMock(return_value=b'invalid msgpack')
        result = self.driver.read_rdatac_response()
        self.assertEqual(result, b'invalid msgpack')

if __name__ == '__main__':
    unittest.main()