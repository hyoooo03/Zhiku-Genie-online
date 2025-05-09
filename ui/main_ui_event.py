from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog
from libra.Libra import SerialConfigDialog, SerialMonitor
from qr.qr1 import SerialCommunicator
from printer.printerQR import print_string_to_printer
from ocr.ocr_thread import OCRThread
from ocr.ocr_result import extract_cas_number, extract_lot_number_from_data, extract_weight_from_data, extract_purity_from_data
from SQL.chemical import query_by_cas_number
from SQL.sql import DynamicDatabase
from wifi import WiFiDialog  # 添加导入语句
import json
import os



class MainUIEvent:
    def __init__(self, ui):
        """
        初始化事件处理类。
        :param ui: 由 PyQt5 加载的 UI 对象。
        """
        self.ui = ui
        self.current_frame = None
        self.input_data_dict = {}
        self.jing_han_liang = 0.0
        self.product_id = None
        self.last_qr_result = None
        self.get_message_for_qr_result_flag = False  # 用来限定扫描逻辑，避免识别同一个二维码后多次查询数据库
        self.get_record_from_sql_flag = False  # 用来限定是否计算
        self.ocr_result_flag = False  # 用来限定是否识别
        self.use_data_flag = False  # 用来限定是否使用
        
        # 设置配置文件路径
        self.config_file = os.path.expanduser('~/.chemical_manager_config.json')
        
        # 绑定按钮事件
        self.ui.serial_button.clicked.connect(self.set_port)
        self.ui.export_button.clicked.connect(self.export_data)
        self.ui.input_button.clicked.connect(self.input_data)
        self.ui.use_button.clicked.connect(self.use_event)
        self.ui.save_button.clicked.connect(self.save_table)
        self.ui.print_button.clicked.connect(self.print_qr)
        self.ui.wifi_button.clicked.connect(self.wifi_settings)  # 添加WiFi按钮事件绑定

        # 设置表格参数
        self.setup_table()

        # 连接表格单元格改动信号
        self.ui.input_table.cellChanged.connect(self.handle_cell_changed)
        
        # 连接仓库ID修改信号
        self.ui.warehouse_id_spinbox.valueChanged.connect(self.save_warehouse_id)

        self.serial_communicator = None
        self.user_weight_thread = None
        self.ocr_thread = None
        self.db_manager = DynamicDatabase()
        
        # 加载保存的仓库ID
        self.load_warehouse_id()

    def setup_table(self):
        """设置表格参数"""
        # 设置录入表格行数
        self.ui.input_table.setRowCount(12)
        
        # 定义参数名称
        parameters = [
            "净含量",
            "位置",
            "cas",
            "lot",
            "名称",
            "中文名称",
            "分子式",
            "分子量",
            "纯度"
        ]
        
        # 设置参数名称
        for i, param in enumerate(parameters):
            self.ui.input_table.setItem(i, 0, QtWidgets.QTableWidgetItem(param))
            self.ui.input_table.setItem(i, 1, QtWidgets.QTableWidgetItem(""))
            
        # 设置使用表格的固定参数
        self.ui.use_table.setRowCount(14)  # 修改为14行
        self.ui.use_table.setItem(0, 0, QtWidgets.QTableWidgetItem("使用量"))
        self.ui.use_table.setItem(1, 0, QtWidgets.QTableWidgetItem("最新净含量"))

    def set_port(self):
        """设置串口按钮功能"""
        dialog = SerialConfigDialog(self.ui)  # 使用 self.ui 作为父对象
        if dialog.exec_() == QDialog.Accepted:
            selected_port, baud_rate = dialog.get_settings()
            print(f"Selected Port: {selected_port}, Baud Rate: {baud_rate}")
      
            if self.user_weight_thread is not None:
                if self.user_weight_thread.running:
                    self.user_weight_thread.stop()
                self.user_weight_thread = None
            self.user_weight_thread = SerialMonitor(selected_port, int(baud_rate))
            self.user_weight_thread.weight_signal.connect(self.get_weight)
            self.ui.log_browser.append("串口设置成功")
    
    def get_weight(self, weight):
        """获取重量"""
        print(f"重量: {weight}")
        # 将重量值显示在使用表格的使用量行
        self.ui.use_table.setItem(0, 1, QtWidgets.QTableWidgetItem(str(weight)))
        if self.get_record_from_sql_flag:
            # 获取weight的小数位数
            weight_str = str(weight)
            decimal_places = len(weight_str.split('.')[1]) if '.' in weight_str else 0
            
            # 计算净含量并格式化
            jing_han_liang = self.jing_han_liang - weight
            formatted_jing_han_liang = f"{jing_han_liang:.{decimal_places}f}"
            self.ui.use_table.setItem(1, 1, QtWidgets.QTableWidgetItem(formatted_jing_han_liang))


    def export_data(self):
        """导出数据按钮功能"""
        print("导出数据按钮被点击")
        # 在这里添加数据导出的逻辑

    def clear_input_table_values(self):
        """清空录入表格的数值列"""
        for row in range(self.ui.input_table.rowCount()):
            self.ui.input_table.setItem(row, 1, QtWidgets.QTableWidgetItem(""))

    def clear_use_table_values(self):
        """清空使用表格的数值列"""
        for row in range(self.ui.use_table.rowCount()):
            self.ui.use_table.setItem(row, 1, QtWidgets.QTableWidgetItem(""))

    def input_data(self):
        """数据录入按钮功能"""
        # 切换到录入表格
        # 清空录入表格的数值列
        self.ui.table_stack.setCurrentWidget(self.ui.input_table)
        # 停止并清除所有串口通信相关对象
        if self.user_weight_thread is not None:
            self.user_weight_thread.stop()
        if self.serial_communicator is not None:
            self.serial_communicator.stop_threads()
            self.serial_communicator.stop()
            self.serial_communicator = None
        if self.ocr_thread is None:
            try:
                # 创建OCR服务线程
                self.ocr_thread = OCRThread()
                self.ocr_thread.ocr_result_signal.connect(self.handle_ocr_result)
                self.ocr_thread.error_signal.connect(self.handle_ocr_error)  # 连接错误信号
                self.ocr_thread.start()  # 启动服务线程，它会自动挂起等待数据
            except Exception as e:
                self.ui.log_browser.append(f"录入出错: {str(e)}")
        
        # 如果有当前帧，发送给OCR服务线程
        if self.current_frame is not None:
            self.ui.log_browser.append("正在进行OCR识别")
            self.ocr_thread.process_image(self.current_frame)  # 发送图像数据给OCR服务线程
        else:
            self.ui.log_browser.append("错误：没有可用的图像数据")

    def handle_ocr_result(self, result):
        """处理OCR识别结果"""
        try:
            # 获取data字段
            ocr_text = result.get('data', '')
            # print(ocr_text)
            cas_number, cas_success = extract_cas_number(ocr_text)
            lot_number, lot_success = extract_lot_number_from_data(ocr_text)
            weight, weight_success = extract_weight_from_data(ocr_text)
            purity, purity_success = extract_purity_from_data(ocr_text)
            
            # print("result:")
            # print(f"CAS号: {cas_number}, 批号: {lot_number}, 重量: {weight}, 纯度: {purity}")
            if cas_success:
                self.ui.input_table.setItem(2, 1, QtWidgets.QTableWidgetItem(str(cas_number)))
            if lot_success:
                self.ui.input_table.setItem(3, 1, QtWidgets.QTableWidgetItem(str(lot_number)))
            if weight_success:
                self.ui.input_table.setItem(0, 1, QtWidgets.QTableWidgetItem(str(weight)))
            if purity_success:
                self.ui.input_table.setItem(8, 1, QtWidgets.QTableWidgetItem(str(purity)))

            # 记录日志
            self.ui.log_browser.append("OCR识别完成")
            self.ocr_result_flag = True
            
        except Exception as e:
            self.ui.log_browser.append(f"处理OCR结果错误: {str(e)}")

    def query_chemical_info(self, cas_number):
        """查询化学品信息"""
        chemical_info = query_by_cas_number(cas_number)
        self.ui.input_table.setItem(7, 1, QtWidgets.QTableWidgetItem(str(chemical_info[1])))
        self.ui.input_table.setItem(6, 1, QtWidgets.QTableWidgetItem(str(chemical_info[2])))
        self.ui.input_table.setItem(5, 1, QtWidgets.QTableWidgetItem(str(chemical_info[3])))
        self.ui.input_table.setItem(4, 1, QtWidgets.QTableWidgetItem(str(chemical_info[4])))
    
    def handle_camera_frame(self, frame):
        """处理摄像头帧数据"""
        self.current_frame = frame
        


    def use_event(self):
        """使用按钮功能"""
        # 清空使用表格的数值列
        self.clear_use_table_values()
        # 切换到使用表格
        self.ui.table_stack.setCurrentWidget(self.ui.use_table)
        self.last_qr_result = None
        self.get_message_for_qr_result_flag = False
        
        # 停止OCR服务线程
        if self.ocr_thread is not None:
            try:
                self.ocr_thread.stop()  # 停止线程
                self.ocr_thread.wait(1000)  # 等待线程结束，最多等待1秒
                if self.ocr_thread.isRunning():  # 如果线程还在运行
                    self.ocr_thread.terminate()  # 强制终止线程
            except Exception as e:
                print(f"停止OCR线程时出错: {str(e)}")
            finally:
                self.ocr_thread = None
        
        # 在这里添加使用数据的逻辑
        if self.user_weight_thread is not None and not self.user_weight_thread.running:
            self.serial_communicator = SerialCommunicator(port='/dev/ttyACM0')
            self.serial_communicator.data_received.connect(self.get_qr_result)
            self.serial_communicator.start()
            self.serial_communicator.start_threads()
            self.user_weight_thread.start()
            self.ui.log_browser.append("使用模式已开启")
        else:
            if self.user_weight_thread is None:
                self.ui.log_browser.append("错误：请先设置串口")

    def insert_record_into_use_table(self, record):
        """将记录数据按照固定顺序插入到使用表格中，同时显示键和值"""
        # 定义字段顺序
        field_order = [
            '中文名称',
            '名称',
            '分子式',
            '分子量',
            'cas',
            '净含量',
            '位置',
            'lot',
            '纯度',
            '仓库_id',
            '产品_id',
            '录入时间'
        ]
        
        # 从第2行开始插入数据
        for row, field in enumerate(field_order, start=2):
            # 插入键（参数名）
            self.ui.use_table.setItem(row, 0, QtWidgets.QTableWidgetItem(field))
            
            # 获取值并处理
            value = record.get(field, '')
            # 如果值为'null'，则显示为空
            if value == 'null':
                value = ''
            # 插入值
            self.ui.use_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(value)))

    def get_message_for_qr_result(self, result_id):
        """获取二维码结果对应的数据
        :param result_id: 二维码结果ID
        :return: bool - 是否成功查询到数据
        """
        # 分割 result_id 并转换为 int 类型
        parts = result_id.split(':')
        if len(parts) == 2:
            part1 = int(parts[0])
            part2 = int(parts[1].split(';')[0])  # 假设分号后面还有其他数据，这里只取分号前的部分
            print(f"Part 1: {part1}, Part 2: {part2}")
        else:
            print("Invalid format of result_id")
            return False
            
        try:
            record = self.db_manager.get_change_logs_as_dict(part2,part1)  # 使用分割后的第一部分作为 product_id
            if record == None:
                record = self.db_manager.get_record_from_main_table(part2,part1)
            if record:
                print("成功获取记录:", record)
                self.use_data_flag = True
                self.get_record_from_sql_flag = True
                self.clear_use_table_values()
                self.insert_record_into_use_table(record)
                self.jing_han_liang = float(record["净含量"])
                return True
            else:
                self.ui.log_browser.append('<font color="red">未找到对应数据，请先录入</font>')
                return False
        except Exception as e:
            print("发生异常:", str(e))
            return False

    def get_qr_result(self, data):
        """获取二维码结果"""
        try:
            if self.get_message_for_qr_result_flag is False:
                if data != self.last_qr_result:
                    self.ui.log_browser.append(f"获取到二维码结果: {data}")
                    if self.get_message_for_qr_result(data):
                        self.get_message_for_qr_result_flag = True
                        self.last_qr_result = data
        except Exception as e:
            print(f"{e}")

        

    def get_warehouse_id(self):
        """获取仓库ID的值"""
        return self.ui.warehouse_id_spinbox.value()

    def get_input_table_data(self):
        """获取输入表格的数据，返回字典形式，空值以null表示"""
        data = {}
        for row in range(self.ui.input_table.rowCount()):
            param_item = self.ui.input_table.item(row, 0)  # 参数名
            value_item = self.ui.input_table.item(row, 1)  # 参数值
            
            # 只有当参数名和数值都为空时才跳过
            if not param_item and not value_item:
                continue
                
            # 获取参数名，如果为空则跳过
            if not param_item:
                continue
            param_name = param_item.text().strip()
            
            # 获取参数值，如果为空则设为null
            param_value = "null"
            if value_item and value_item.text().strip():
                param_value = value_item.text().strip()
                
            data[param_name] = param_value
        return data

    def get_use_table_data(self):
        """获取使用表格的数据，返回字典形式，空值以null表示"""
        data = {}
        for row in range(self.ui.use_table.rowCount()):
            param_item = self.ui.use_table.item(row, 0)  # 参数名
            value_item = self.ui.use_table.item(row, 1)  # 参数值
            
            # 只有当参数名和数值都为空时才跳过
            if not param_item and not value_item:
                continue
                
            # 获取参数名，如果为空则跳过
            if not param_item:
                continue
            param_name = param_item.text().strip()
            
            # 获取参数值，如果为空则设为null
            param_value = "null"
            if value_item and value_item.text().strip():
                param_value = value_item.text().strip()
                
            data[param_name] = param_value
        return data

    def save_table(self):
        """保存表格按钮功能"""
        print("保存表格按钮被点击")
        self.get_message_for_qr_result_flag = False
        self.ui.log_browser.append("开始保存")
        # 根据当前显示的表格决定保存哪个表格的数据
        current_table = self.ui.table_stack.currentWidget()
        if current_table == self.ui.input_table and self.ocr_result_flag:
            print("此时是录入表格")
            self.input_data_dict = self.get_input_table_data()
            self.input_data_dict['仓库_id'] = self.get_warehouse_id()
            print(self.input_data_dict)
            self.product_id = self.db_manager.insert_initial_data(self.input_data_dict)
            self.db_manager.print_records_contents()
            self.ui.log_browser.append("保存成功")
            self.ocr_result_flag = False
        elif current_table == self.ui.input_table and not self.ocr_result_flag:
            self.ui.log_browser.append("请先点击录入按钮进行内容识别")
        if current_table == self.ui.use_table and self.use_data_flag:
            print("此时是使用表格")
            use_data = self.get_use_table_data()
            # 将净含量的值替换为最新净含量的值
            if '最新净含量' in use_data:
                use_data['净含量'] = use_data['最新净含量']
                del use_data['最新净含量']
            
            # 确保净含量的小数位数与原始数据一致
            if '净含量' in use_data:
                # 获取原始净含量的小数位数
                original_net_weight = use_data['净含量']
                decimal_places = len(original_net_weight.split('.')[1]) if '.' in original_net_weight else 0
                # 格式化净含量，保持原始小数位数
                use_data['净含量'] = f"{float(original_net_weight):.{decimal_places}f}"
            
            print(use_data)
            self.db_manager.insert_change_log_from_dict(use_data)
            self.db_manager.print_change_logs_contents()
            self.ui.log_browser.append("保存成功")
            self.get_record_from_sql_flag = False
            self.use_data_flag = False
        elif current_table == self.ui.use_table and not self.use_data_flag:
            self.ui.log_browser.append("请点击使用按钮再次识别同一二维码或放入新的二维码识别")
            

    def print_qr(self):
        """打印二维码按钮功能"""
        print("打印二维码按钮被点击")
        if self.ui.table_stack.currentWidget() == self.ui.input_table:
            self.ui.log_browser.append("开始打印")
            # 检查input_data_dict是否存在且包含必要数据
            if not self.input_data_dict:
                self.ui.log_browser.append("错误：没有可用的数据")
                return
            
            product_id = self.product_id
                
            # 获取仓库ID和产品ID
            warehouse_id = self.input_data_dict.get('仓库_id')
            position = self.input_data_dict.get('位置', '')
            
            if warehouse_id is None or product_id is None:
                self.ui.log_browser.append("错误：缺少仓库ID或产品ID")
                return
                
            # 生成二维码内容
            content = f"{warehouse_id}:{product_id}"
            content1 = position if position else "未知位置"
            
            # 调用打印函数
            try:
                print_string_to_printer(content, content1)
                self.ui.log_browser.append("打印成功")
                self.clear_input_table_values()
            except Exception as e:
                self.ui.log_browser.append(f"打印失败：{e}")

    def closeEvent(self):
        """关闭窗口时释放资源"""
        try:
            # 停止串口通信
            if self.serial_communicator is not None:
                self.serial_communicator.stop()
                self.serial_communicator.stop_threads()
            
            # 停止OCR服务线程
            if self.ocr_thread is not None:
                self.ocr_thread.stop()
                
            # 停止重量线程
            if self.user_weight_thread is not None:
                self.user_weight_thread.stop()
        except Exception as e:
            pass

    def handle_ocr_error(self, error_message):
        """处理OCR错误"""
        self.ui.log_browser.append(f'<font color="red">{error_message}</font>')
        # 如果OCR服务不可用，停止OCR线程
        if "无法连接到OCR服务" in error_message or "OCR服务响应超时" in error_message:
            if self.ocr_thread is not None:
                self.ocr_thread.stop()
                self.ocr_thread = None

    def handle_cell_changed(self, row, column):
        """处理表格单元格内容改动
        :param row: 行号
        :param column: 列号
        """
        # 只处理第二列（数值列）的改动
        if column != 1:
            return
            
        # 获取参数名
        param_item = self.ui.input_table.item(row, 0)
        if not param_item:
            return
            
        param_name = param_item.text().strip()
        
        # 如果是CAS号行
        if param_name == "cas":
            # 获取新的CAS号值
            value_item = self.ui.input_table.item(row, column)
            if value_item:
                new_cas = value_item.text().strip()
                if new_cas:  # 如果CAS号不为空
                    try:
                        # 查询化学品信息
                        chemical_info = query_by_cas_number(new_cas)
                        if chemical_info:
                            # 更新其他字段
                            self.ui.input_table.setItem(7, 1, QtWidgets.QTableWidgetItem(str(chemical_info[1])))  # 分子量
                            self.ui.input_table.setItem(6, 1, QtWidgets.QTableWidgetItem(str(chemical_info[2])))  # 分子式
                            self.ui.input_table.setItem(5, 1, QtWidgets.QTableWidgetItem(str(chemical_info[3])))  # 中文名称
                            self.ui.input_table.setItem(4, 1, QtWidgets.QTableWidgetItem(str(chemical_info[4])))  # 名称
                            self.ui.log_browser.append(f"已更新CAS号 {new_cas} 对应的化学品信息")
                        else:
                            self.ui.log_browser.append(f'<font color="red">未找到CAS号 {new_cas} 对应的化学品信息</font>')
                    except Exception as e:
                        self.ui.log_browser.append(f'<font color="red">查询化学品信息出错: {str(e)}</font>')

    def wifi_settings(self):
        """WiFi设置按钮功能"""
        dialog = WiFiDialog(self.ui)
        dialog.exec_()

    def save_warehouse_id(self):
        """保存仓库ID到JSON文件"""
        warehouse_id = self.ui.warehouse_id_spinbox.value()
        config = {
            'warehouse_id': warehouse_id
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            self.ui.log_browser.append(f"保存仓库ID失败: {str(e)}")

    def load_warehouse_id(self):
        """从JSON文件加载仓库ID"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    warehouse_id = config.get('warehouse_id', 1)  # 默认值为1
                    self.ui.warehouse_id_spinbox.setValue(warehouse_id)
        except Exception as e:
            self.ui.log_browser.append(f"加载仓库ID失败: {str(e)}")
            self.ui.warehouse_id_spinbox.setValue(1)  # 如果加载失败，设置默认值