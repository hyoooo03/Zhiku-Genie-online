import serial
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal


class SerialCommunicator(QObject):
    data_received = pyqtSignal(str)  # 定义一个信号

    def __init__(self, port='/dev/ttyACM0', baudrate=115200):
        super().__init__()  # 初始化QObject
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.running = False
        self.read_thread = None
        self.send_thread = None
        self.command = bytes([0x7E, 0x00, 0x08, 0x01, 0x00, 0x02, 0x01, 0xAB, 0xCD])
        self.unwanted_data = b'\x02\x00\x00\x01\x0031'
        self.expected_data = "1:12"
        self.last_received_data = ""
        self.received_expected_data = False

    def start(self):
        """打开串口"""
        if not self.ser.is_open:
            self.ser.open()
            print(f"串口已打开: {self.ser.name}")

    def stop(self):
        """关闭串口"""
        if self.ser.is_open:
            self.close()

    def send_command_periodically(self):
        """每隔1秒发送一次指定的十六进制指令"""
        while self.running:
            if self.ser.is_open:
                self.ser.write(self.command)
                # print(f"发送指令: {self.command.hex()}")
                self.received_expected_data = False  # 每次发送指令时重置标志位
                time.sleep(1)  # 每隔1秒发送一次指令

    def read_from_serial(self):
        """从串口读取数据并尝试使用GBK解码"""
        while self.running:
            if self.ser.in_waiting > 0:
                try:
                    # 读取所有可用的数据
                    data = self.ser.read(self.ser.in_waiting)

                    if self.unwanted_data == data:
                        print("未识别到预期数据")
                    else:
                        decoded_data = data.decode('gbk')
                        print(f"接收到的数据: {decoded_data.strip()}")
                        self.last_received_data = decoded_data.strip()

                        # 发出信号
                        self.data_received.emit(decoded_data.strip())

                except UnicodeDecodeError as e:
                    # 如果解码失败，则打印错误信息和原始十六进制数据
                    print(f"解码失败: {e}")
                    print(f"原始数据（十六进制）: {data.hex()}")

    def start_threads(self):
        """开启后台线程用于发送和接收数据"""
        if not self.running:
            self.running = True
            self.read_thread = threading.Thread(target=self.read_from_serial)
            self.send_thread = threading.Thread(target=self.send_command_periodically)
            self.read_thread.start()
            self.send_thread.start()
            print("开始读取和发送串口数据...")

    def stop_threads(self):
        """停止后台线程"""
        if self.running:
            self.running = False
            if self.read_thread is not None:
                self.read_thread.join()
                self.read_thread = None
            if self.send_thread is not None:
                self.send_thread.join()
                self.send_thread = None
            print("停止读取和发送串口数据.")

    def close(self):
        """关闭串口连接"""
        self.stop_threads()
        if self.ser.is_open:
            self.ser.close()
            print("串口已关闭")


# # 使用示例
# if __name__ == "__main__":
#     from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
#     import sys

#     class MainWindow(QWidget):
#         def __init__(self):
#             super().__init__()
#             self.label = QLabel("等待数据...", self)
#             layout = QVBoxLayout()
#             layout.addWidget(self.label)
#             self.setLayout(layout)

#             # 创建SerialCommunicator实例
#             self.communicator = SerialCommunicator(port='/dev/ttyACM0')

#             # 连接信号和槽函数
#             self.communicator.data_received.connect(self.update_label)

#             # 启动串口通信
#             self.communicator.start()
#             self.communicator.start_threads()

#         def update_label(self, data):
#             """更新标签文本"""
#             self.label.setText(f"接收到的数据: {data}")

#         def closeEvent(self, event):
#             """确保在关闭窗口时停止串口通信"""
#             self.communicator.stop()
#             event.accept()

#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec_())