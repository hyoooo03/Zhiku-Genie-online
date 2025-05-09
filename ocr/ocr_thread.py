from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import requests
import json
import base64
import time


class OCRThread(QThread):
    ocr_result_signal = pyqtSignal(dict)  # 发送OCR识别结果
    error_signal = pyqtSignal(str)  # 发送错误信息
    
    def __init__(self):
        super().__init__()
        self.image_data = None
        self.running = True
        self.condition = True  # 用于控制线程挂起
        self.timeout = 5  # 设置3秒超时
        
    def run(self):
        """线程主循环"""
        while self.running:
            if self.condition:
                # 如果没有图像数据，挂起线程
                time.sleep(0.1)  # 使用time.sleep替代msleep
                continue
                
            if self.image_data is not None:
                try:
                    # 调用OCR服务
                    result = self.call_ocr_service(self.image_data)
                    if result is not None:  # 只有在成功获取结果时才发送信号
                        self.ocr_result_signal.emit(result)
                except Exception as e:
                    print(f"OCR识别错误: {str(e)}")
                finally:
                    # 重置状态，等待下一次识别
                    self.image_data = None
                    self.condition = True
                    
    def process_image(self, image):
        """处理新的图像数据"""
        self.image_data = image
        self.condition = False  # 唤醒线程进行识别
        
    def call_ocr_service(self, image):
        """调用OCR服务"""
        try:
            # 将OpenCV图像转换为base64
            _, buffer = cv2.imencode('.jpg', image)
            base64_string = base64.b64encode(buffer).decode('utf-8')
            
            # 准备请求数据
            url = "http://8.155.50.231:80/api/ocr"  # 使用Windows的IP地址
            data = {
                "base64": base64_string,
                "options": {
                    "data.format": "text",
                }
            }
            headers = {"Content-Type": "application/json"}
            
            try:
                # 发送请求，设置超时
                response = requests.post(url, data=json.dumps(data), headers=headers, timeout=self.timeout)
                response.raise_for_status()
            
                # 返回识别结果
                return json.loads(response.text)
            except requests.exceptions.Timeout:
                self.error_signal.emit("OCR服务响应超时，请检查服务是否正常运行")
                return None
            except requests.exceptions.ConnectionError:
                self.error_signal.emit("无法连接到OCR服务，请检查服务是否已启动")
                return None
        except Exception as e:
            self.error_signal.emit(f"OCR处理错误: {str(e)}")
            return None
        
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()  # 等待线程结束 