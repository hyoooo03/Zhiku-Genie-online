from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
import cv2



class CameraThread(QThread):
    image_ready = pyqtSignal(QImage)  # 用于UI显示的信号
    frame_signal = pyqtSignal(object)  # 用于发送原始图像数据
    error_occurred = pyqtSignal(str)
    

    def __init__(self, camera_id=0, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.running = False
        self.cap = None
        self.target_width = 400  # 目标宽度
        self.target_height = 300  # 目标高度
   

    ########## 摄像头 ##########

    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                self.error_occurred.emit("无法打开摄像头")
                return

            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            self.running = True

            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    self.error_occurred.emit("无法读取摄像头画面")
                    break

                # 调整图像大小以匹配UI显示区域
                resized_frame = cv2.resize(frame, (self.target_width, self.target_height))
                rgb_image = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                
                # 发送图像数据用于UI显示
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qimage = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.image_ready.emit(qimage)
                
                # 发送原始RGB图像数据
                self.frame_signal.emit(rgb_image)


        except Exception as e:
            self.error_occurred.emit(f"摄像头错误: {str(e)}")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None