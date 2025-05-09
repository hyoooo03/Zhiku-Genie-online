import os
import glob
import serial
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QDialog, QComboBox, QLineEdit, QDialogButtonBox
import re
from PyQt5.QtCore import pyqtSignal,QObject
import threading
import time



class SerialConfigDialog(QDialog):
    def __init__(self, parent=None):
        super(SerialConfigDialog, self).__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('串口设置')

        layout = QVBoxLayout()

        # 串口选择
        self.port_label = QLabel("选择串口:", self)
        layout.addWidget(self.port_label)
        self.port_combo = QComboBox(self)
        self.refresh_ports()
        layout.addWidget(self.port_combo)

        # 波特率设置
        self.baud_label = QLabel("设置波特率:", self)
        layout.addWidget(self.baud_label)
        self.baud_edit = QLineEdit(self)
        self.baud_edit.setText("9600")  # 默认波特率为9600
        layout.addWidget(self.baud_edit)

        # 添加标准按钮框
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def refresh_ports(self):
        """刷新串口列表"""
        ports = list_serial_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)

    def get_settings(self):
        """返回用户选择的串口和设置的波特率"""
        return self.port_combo.currentText(), self.baud_edit.text()

def list_serial_ports():
    """列出所有可用的串口设备"""
    if os.name == 'nt':  # Windows
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif os.name == 'posix':  # Unix-like systems, including Raspberry Pi
        ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyS*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result




class SerialMonitor(QObject):
    weight_signal = pyqtSignal(float)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self.thread = None
        self.buffer = ""

    def start(self):
        """Start the serial monitoring thread."""
        if not self.running:
            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                self.running = True
                self.thread = threading.Thread(target=self._monitor)
                self.thread.start()
                print(f"Started monitoring on {self.port} at {self.baudrate} baud.")
            except serial.SerialException as e:
                print(f"Failed to open serial port: {e}")
                self.running = False

    def stop(self):
        """Stop the serial monitoring thread."""
        self.running = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=2)  # Wait for thread to finish.
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
        print("Stopped monitoring.")



    def _monitor(self):
        """The actual method run by the thread to monitor serial data using regex."""
        # 定义用于匹配数字（整数或浮点数）的正则表达式模式
        pattern = re.compile(r'[-+]?\d*\.\d+|[-+]?\d+')
        
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    # Read raw bytes from the serial port
                    byte_data = self.ser.read(self.ser.in_waiting)
                    # 将字节字符串添加到缓冲区
                    self.buffer += byte_data.decode('utf-8', errors='ignore')

                    # 使用正则表达式找到所有匹配项
                    matches = pattern.findall(self.buffer)
                    
                    # 更新缓冲区，移除已处理的数据
                    self.buffer = pattern.sub('', self.buffer, count=len(matches))
                    
                    for match in matches:  # 遍历所有的匹配项
                        try:
                            # 尝试将匹配结果转换为浮点数
                            weight_value = float(match)
                            weight_value = weight_value * 0.1
                            self.weight_signal.emit(weight_value)
                            print(f"Received weight value: {weight_value}")
                        except ValueError:
                            print(f"Could not convert '{match}' to float")
            except serial.SerialException as e:
                print(f"Error reading from serial port: {e}")
                self.stop()
            except Exception as e:
                print(f"Unexpected error: {e}")
                self.stop()
            time.sleep(1)  # Small delay to avoid high CPU usage.


# # Example usage in main program
# if __name__ == "__main__":
#     import sys

#     # Example parameters
#     port = '/dev/ttyUSB0'
#     baudrate = 9600

#     # Create an instance of SerialMonitor
#     monitor = SerialMonitor(port, baudrate)

#     try:
#         # Start monitoring
#         monitor.start()

#         # Keep the main thread alive for a period or until interrupted
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("\nInterrupted! Stopping...")
#     finally:
#         # Ensure the monitoring stops properly
#         monitor.stop()
#         sys.exit(0)