import sys
import warnings

from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from ui.main_ui import Ui_Dialog
from ui.main_ui_event import MainUIEvent
from camera.camera_thread import CameraThread


# 过滤 SIP 弃用警告
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PyQt5")
class MyApp(QDialog, Ui_Dialog):
    def __init__(self):
        super(MyApp, self).__init__()
        self.setupUi(self)  # 初始化 UI
        self.event_handler = MainUIEvent(self)  # 初始化事件处理类
        
        # 初始化摄像头
        self.camera_thread = CameraThread()
        self.camera_thread.image_ready.connect(self.update_camera_view)
        self.camera_thread.frame_signal.connect(self.handle_camera_frame)
        self.camera_thread.error_occurred.connect(self.handle_camera_error)
        self.camera_thread.start()

    def handle_camera_frame(self, frame):
        """处理摄像头帧数据"""
        self.event_handler.handle_camera_frame(frame)

    def update_camera_view(self, image):
        """更新摄像头显示区域"""
        # 获取显示区域的大小
        display_size = self.display_label.size()
        
        # 计算缩放比例，保持原始比例
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(
            display_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # 设置固定大小，防止布局自动缩放
        self.display_label.setFixedSize(display_size)
        self.display_label.setPixmap(scaled_pixmap)
        
       

    def handle_camera_error(self, error_message):
        """处理摄像头错误"""
        self.log_browser.append(f"摄像头错误: {error_message}")
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None

    def closeEvent(self, event):
        """重写关闭事件以释放资源"""
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None
        self.event_handler.closeEvent()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())