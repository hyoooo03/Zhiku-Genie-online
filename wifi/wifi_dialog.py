from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QComboBox, QLineEdit, QMessageBox)
import subprocess
import re
import time
import threading
import os
import json

class WiFiDialog(QDialog):
    # 定义信号
    status_update = QtCore.pyqtSignal(str)
    connection_result = QtCore.pyqtSignal(bool, str)
    disconnect_result = QtCore.pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WiFi设置")
        self.setFixedSize(400, 300)
        self.wifi_credentials_file = os.path.expanduser("~/.wifi_credentials.json")
        self.load_wifi_credentials()
        self.setup_ui()
        self.scan_wifi()
        self.current_ssid = self.get_current_ssid()
        
    def load_wifi_credentials(self):
        """加载保存的WiFi凭据"""
        try:
            if os.path.exists(self.wifi_credentials_file):
                with open(self.wifi_credentials_file, 'r') as f:
                    self.wifi_credentials = json.load(f)
            else:
                self.wifi_credentials = {}
        except Exception as e:
            print(f"加载WiFi凭据失败: {e}")
            self.wifi_credentials = {}
            
    def save_wifi_credentials(self):
        """保存WiFi凭据"""
        try:
            with open(self.wifi_credentials_file, 'w') as f:
                json.dump(self.wifi_credentials, f)
        except Exception as e:
            print(f"保存WiFi凭据失败: {e}")
            
    def update_wifi_credentials(self, ssid, password):
        """更新WiFi凭据"""
        self.wifi_credentials[ssid] = password
        self.save_wifi_credentials()
        
    def remove_wifi_credentials(self, ssid):
        """删除WiFi凭据"""
        if ssid in self.wifi_credentials:
            del self.wifi_credentials[ssid]
            self.save_wifi_credentials()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 当前连接状态
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.scan_wifi)
        layout.addWidget(refresh_btn)
        
        # WiFi下拉列表
        wifi_layout = QHBoxLayout()
        wifi_label = QLabel("WiFi网络:")
        self.wifi_combo = QComboBox()
        self.wifi_combo.currentTextChanged.connect(self.on_wifi_selected)
        wifi_layout.addWidget(wifi_label)
        wifi_layout.addWidget(self.wifi_combo)
        layout.addLayout(wifi_layout)
        
        # 密码输入框
        password_layout = QHBoxLayout()
        password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.connect_wifi)
        self.connect_btn.setEnabled(False)
        button_layout.addWidget(self.connect_btn)
        
        # 断开按钮
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.clicked.connect(self.disconnect_wifi)
        self.disconnect_btn.setEnabled(False)
        button_layout.addWidget(self.disconnect_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.status_update.connect(self._update_status_text)
        self.connection_result.connect(self._handle_connection_result)
        self.disconnect_result.connect(self._handle_disconnect_result)
        
        self.update_status()
        
    def get_current_ssid(self):
        """获取当前连接的WiFi名称"""
        try:
            result = subprocess.run(['iwconfig', 'wlan0'], 
                                 capture_output=True, text=True)
            match = re.search(r'ESSID:"([^"]*)"', result.stdout)
            return match.group(1) if match else None
        except:
            return None
            
    def update_status(self):
        """更新状态显示"""
        current_ssid = self.get_current_ssid()
        if current_ssid:
            self.status_label.setText(f"当前连接: {current_ssid}")
            self.disconnect_btn.setEnabled(True)
        else:
            self.status_label.setText("未连接")
            self.disconnect_btn.setEnabled(False)
    
    @QtCore.pyqtSlot(str)
    def _update_status_text(self, text):
        """在主线程中更新状态文本"""
        self.status_label.setText(text)
        
    def scan_wifi(self):
        """扫描可用的WiFi网络"""
        self.wifi_combo.clear()
        self.status_update.emit("正在扫描WiFi...")
        
        try:
            # 使用iwlist命令获取WiFi列表
            output = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan'], encoding='utf-8')
            # 提取SSID
            ssids = re.findall(r'ESSID:"([^"]*)"', output)
            # 去重
            unique_ssids = list(dict.fromkeys(ssids))
            
            # 添加空选项
            self.wifi_combo.addItem("")
            
            # 添加WiFi网络
            for ssid in unique_ssids:
                if ssid:  # 只添加非空的SSID
                    self.wifi_combo.addItem(ssid)
            
            # 如果有当前连接，选中它
            current_ssid = self.get_current_ssid()
            if current_ssid:
                index = self.wifi_combo.findText(current_ssid)
                if index >= 0:
                    self.wifi_combo.setCurrentIndex(index)
            
            self.update_status()
        except Exception as e:
            self.status_update.emit(f"扫描失败: {str(e)}")
    
    def on_wifi_selected(self, ssid):
        """当选择WiFi时启用连接按钮并自动填充密码"""
        self.connect_btn.setEnabled(bool(ssid))
        self.selected_ssid = ssid
        
        # 如果这个WiFi之前连接过，自动填充密码
        if ssid in self.wifi_credentials:
            self.password_input.setText(self.wifi_credentials[ssid])
        else:
            self.password_input.clear()
    
    def connect_wifi(self):
        """连接到选中的WiFi"""
        if not hasattr(self, 'selected_ssid') or not self.selected_ssid:
            return
            
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, "警告", "请输入WiFi密码")
            return
            
        self.status_update.emit("正在连接...")
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(False)
        
        # 在新线程中执行连接操作
        threading.Thread(target=self._connect_wifi_thread, 
                        args=(self.selected_ssid, password),
                        daemon=True).start()
    
    def disconnect_wifi(self):
        """断开当前WiFi连接"""
        self.status_update.emit("正在断开连接...")
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(False)
        
        # 在新线程中执行断开操作
        threading.Thread(target=self._disconnect_wifi_thread, 
                        daemon=True).start()
    
    def _disconnect_wifi_thread(self):
        """在新线程中执行断开连接"""
        try:
            # 停止wpa_supplicant
            subprocess.run(['sudo', 'killall', 'wpa_supplicant'], 
                         check=False, capture_output=True)
            subprocess.run(['sudo', 'killall', 'dhclient'], 
                         check=False, capture_output=True)
            
            # 关闭wlan0接口
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], 
                         check=True, capture_output=True)
            
            # 等待一下确保接口完全关闭
            time.sleep(1)
            
            # 重新启动wlan0接口
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], 
                         check=True, capture_output=True)
            
            self.disconnect_result.emit(True, "WiFi已断开连接")
        except Exception as e:
            self.disconnect_result.emit(False, str(e))
    
    @QtCore.pyqtSlot(bool, str)
    def _handle_disconnect_result(self, success, message):
        """处理断开连接的结果"""
        self.update_status()
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "错误", f"断开连接失败: {message}")
    
    def _connect_wifi_thread(self, ssid, password):
        """在新线程中执行WiFi连接"""
        try:
            # 先断开当前连接
            subprocess.run(['sudo', 'killall', 'wpa_supplicant'], 
                         check=False, capture_output=True)
            subprocess.run(['sudo', 'killall', 'dhclient'], 
                         check=False, capture_output=True)
            
            # 关闭wlan0接口
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], 
                         check=True, capture_output=True)
            
            # 等待一下确保接口完全关闭
            time.sleep(1)
            
            # 重新启动wlan0接口
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], 
                         check=True, capture_output=True)
            
            # 创建wpa_supplicant配置
            config = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=CN

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}"""
            
            # 保存配置文件
            with open("/tmp/wpa_supplicant.conf", "w") as f:
                f.write(config)
            
            # 启动wpa_supplicant
            subprocess.run(['sudo', 'wpa_supplicant', '-B', '-i', 'wlan0', '-c', '/tmp/wpa_supplicant.conf'], 
                         check=True, capture_output=True)
            
            # 等待wpa_supplicant启动
            time.sleep(2)
            
            # 获取IP地址
            subprocess.run(['sudo', 'dhclient', 'wlan0'], 
                         check=True, capture_output=True)
            
            # 等待连接成功
            for _ in range(10):  # 最多等待10秒
                time.sleep(1)
                result = subprocess.run(['iwconfig', 'wlan0'], 
                                     capture_output=True, text=True)
                if ssid in result.stdout:
                    # 连接成功，保存凭据
                    self.update_wifi_credentials(ssid, password)
                    self.connection_result.emit(True, "WiFi连接成功")
                    return
            
            # 连接失败，如果之前保存过这个WiFi的凭据，则删除
            if ssid in self.wifi_credentials:
                self.remove_wifi_credentials(ssid)
            self.connection_result.emit(False, "连接超时")
            
        except Exception as e:
            # 连接失败，如果之前保存过这个WiFi的凭据，则删除
            if ssid in self.wifi_credentials:
                self.remove_wifi_credentials(ssid)
            self.connection_result.emit(False, str(e))
        finally:
            # 清理临时文件
            try:
                os.remove("/tmp/wpa_supplicant.conf")
            except:
                pass
    
    @QtCore.pyqtSlot(bool, str)
    def _handle_connection_result(self, success, message):
        """处理连接结果"""
        self.update_status()
        if success:
            QMessageBox.information(self, "成功", message)
            self.close()  # 连接成功后关闭对话框
        else:
            self.status_label.setText(f"连接失败: {message}")
            self.connect_btn.setEnabled(True)
            QMessageBox.warning(self, "错误", f"WiFi连接失败: {message}") 