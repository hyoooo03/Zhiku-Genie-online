from PyQt5.QtWidgets import QDialog, QPushButton, QVBoxLayout, QApplication
import sqlite3
import pandas as pd


class ExportDialog(QDialog):
    def __init__(self):
        super().__init__()
        
        self.initUI()
    
    def initUI(self):
        # 设置窗口标题
        self.setWindowTitle('选择导出类型')
        
        # 创建按钮
        btn_first_entry = QPushButton('导出首次录入数据', self)
        btn_usage_history = QPushButton('导出使用历史', self)
        btn_latest_data = QPushButton('导出各产品最新数据', self)
        
        # 当按钮被点击时关闭对话框，你可以在这里添加处理函数
        btn_first_entry.clicked.connect(lambda: self.onClicked('首次录入数据'))
        btn_usage_history.clicked.connect(lambda: self.onClicked('使用历史'))
        btn_latest_data.clicked.connect(lambda: self.onClicked('最新数据'))
        
        # 创建布局并添加部件
        layout = QVBoxLayout()
        layout.addWidget(btn_first_entry)
        layout.addWidget(btn_usage_history)
        layout.addWidget(btn_latest_data)
        
        # 设置对话框的布局
        self.setLayout(layout)
    

    def onClicked(self, text):
        print(f'{text} 被点击了')
        # 连接到 SQLite 数据库
        conn = sqlite3.connect('/home/qhyoo/pyproject/code/test_data.db')
        
        if text == '首次录入数据':
            # 使用 pandas 读取 SQL 查询结果
            df = pd.read_sql_query("SELECT * FROM records;", conn)
            # 导出为 Excel 文件
            df.to_excel('/home/qhyoo/Desktop/record.xlsx', index=False)
        elif text == '使用历史':
            df1 = pd.read_sql_query("SELECT * FROM change_logs;", conn)
            # 导出为 Excel 文件
            df1.to_excel('/home/qhyoo/Desktop/change_logs.xlsx', index=False)
        elif text == '最新数据':
            query = """
            SELECT r.*, cl.最新重量, cl.最新净含量, cl.最新更新时间
            FROM records r
            LEFT JOIN (
                SELECT 产品_id, 重量 AS 最新重量, 净含量 AS 最新净含量, 更新时间 AS 最新更新时间
                FROM change_logs
                WHERE (产品_id, 更新时间) IN (
                    SELECT 产品_id, MAX(更新时间)
                    FROM change_logs
                    GROUP BY 产品_id
                )
            ) cl ON r.产品_id = cl.产品_id;
            """
            df_latest = pd.read_sql_query(query, conn)

            # 如果最新更新时间为空，则用更新时间填充
            df_latest['最新更新时间'] = df_latest['最新更新时间'].fillna(df_latest['更新时间'])

            # 删除不再需要的列
            df_latest.drop(columns=['更新时间','位置','纯度','分子量','cas','lot','仓库_id'], inplace=True)
            
            # 如果需要删除重复的列或处理特定需求，请在此处进行
            # 示例：如果不需要原始的'重量'和'净含量'，只保留最新的：
            df_latest['重量'] = df_latest['最新重量'].combine_first(df_latest['重量'])
            df_latest['净含量'] = df_latest['最新净含量'].combine_first(df_latest['净含量'])
            df_latest.drop(columns=['最新重量', '最新净含量'], inplace=True)

            # 导出为 Excel 文件
            df_latest.to_excel('/home/qhyoo/Desktop/latest_data.xlsx', index=False)
        self.accept()

# # 修改你的 get_data_of_sql 方法来显示这个对话框
# def get_data_of_sql(self):
#     dialog = ExportDialog()
#     if dialog.exec_() == QDialog.Accepted:
#         # 根据用户的选择执行相应的操作
#         pass  # 替换成实际的操作代码