import sqlite3
from datetime import datetime
import os

class DynamicDatabase:
    def __init__(self, db_path='/home/qhyoo/pycode/qt_code/data/test_data.db'):
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        # Create initial tables if they don't exist
        self._create_main_table()
        self._create_change_log_table()

    def _create_main_table(self):
        query = """
                CREATE TABLE IF NOT EXISTS records (
                    仓库_id INTEGER,
                    录入时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    产品_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    名称 TEXT,
                    cas TEXT,
                    lot TEXT,
                    净含量 REAL,
                    UNIQUE(产品_id, 仓库_id, 录入时间)
                );
                """
        self.cursor.execute(query)
        self.conn.commit()

    def _create_change_log_table(self):
        query = """
                CREATE TABLE IF NOT EXISTS change_logs (
                    记录_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    产品_id INTEGER,
                    更新时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    净含量 REAL,
                    FOREIGN KEY (产品_id) REFERENCES records(产品_id)
                );
                """
        self.cursor.execute(query)
        self.conn.commit()

    def insert_initial_data(self, data_dict, warehouse_id=None):
        # 检查必填字段
        required_fields = set()  # 移除所有必填字段
        missing_fields = required_fields - set(data_dict.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Check and add new columns if necessary
        self._add_new_columns('records', data_dict)

        # Prepare column names and values for insertion
        columns = list(data_dict.keys())
        placeholders = ', '.join([f":{col}" for col in columns])  # 确保占位符格式正确

        # Update the input time to current timestamp with second precision
        data_dict['录入时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Automatically assign warehouse_id if provided
        if warehouse_id is not None:
            data_dict['仓库_id'] = warehouse_id

        # Insert data into the table
        query = f"INSERT INTO records ({', '.join(columns)}) VALUES ({placeholders});"
        self.cursor.execute(query, data_dict)  # 使用字典绑定参数
        self.conn.commit()
        product_id = self.get_latest_product_id()
        return product_id

    def _add_new_columns(self, table_name, data_dict):
        existing_columns = set(self._get_column_names(table_name))
        new_columns = set(data_dict.keys()) - existing_columns

        for column in new_columns:
            alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column} TEXT;"
            self.cursor.execute(alter_query)
            self.conn.commit()

    def _get_column_names(self, table_name):
        self.cursor.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in self.cursor.fetchall()]

    def close(self):
        self.conn.close()

    def print_records_contents(self):
        self.cursor.execute("SELECT * FROM records;")
        rows = self.cursor.fetchall()

        if not rows:
            print("No records found.")
            return

        # Get column names
        column_names = self._get_column_names('records')

        # Print header
        print("\t".join(column_names))

        # Print each row
        for row in rows:
            print("\t".join(str(item) for item in row))

    def print_change_logs_contents(self):
        self.cursor.execute("SELECT * FROM change_logs;")
        rows = self.cursor.fetchall()

        if not rows:
            print("No change logs found.")
            return

        # Get column names dynamically
        column_names = self._get_column_names('change_logs')

        # Print header
        print("\t".join(column_names))

        # Print each row
        for row in rows:
            print("\t".join(str(item) for item in row))

    def get_latest_product_id(self):
        query = "SELECT MAX(产品_id) FROM records;"
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_record_from_main_table(self, product_id, warehouse_id):
        query = """
                SELECT r.*, cl.净含量 AS 最新净含量, cl.更新时间 AS 最新更新时间
                FROM records r
                LEFT JOIN change_logs cl ON r.产品_id = cl.产品_id
                WHERE r.产品_id = ? AND r.仓库_id = ?
                ORDER BY cl.更新时间 DESC
                LIMIT 1;
                """
        self.cursor.execute(query, (product_id, warehouse_id))
        row = self.cursor.fetchone()

        if not row:
            return None

        # Get column names
        column_names = self._get_column_names('records') + ['最新净含量', '最新更新时间']

        # Convert row to dictionary
        record_dict = dict(zip(column_names, row))

        # Replace the original net content with the latest one
        if record_dict['最新净含量'] is not None:
            record_dict['净含量'] = record_dict['最新净含量']

        # Remove the extra columns
        del record_dict['最新净含量']
        del record_dict['最新更新时间']

        return record_dict

    def insert_change_log_from_dict(self, change_log_dict):
        # Ensure all keys are valid columns in change_logs table or add them if not
        existing_columns = set(self._get_column_names('change_logs'))
        new_columns = set(change_log_dict.keys()) - existing_columns

        for column in new_columns:
            alter_query = f"ALTER TABLE change_logs ADD COLUMN {column} TEXT;"
            self.cursor.execute(alter_query)
            self.conn.commit()

        # Set default update time
        change_log_dict['更新时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Prepare column names and values for insertion
        columns = list(change_log_dict.keys())
        placeholders = ', '.join([f":{col}" for col in columns])  # 使用命名占位符

        # Insert data into the change_logs table
        query = f"INSERT INTO change_logs ({', '.join(columns)}) VALUES ({placeholders});"
        
        # 确保净含量保持原始精度
        if '净含量' in change_log_dict:
            change_log_dict['净含量'] = float(change_log_dict['净含量'])
        
        self.cursor.execute(query, change_log_dict)  # 使用字典绑定参数
        self.conn.commit()

    def get_change_logs_as_dict(self, product_id, warehouse_id):
        query = """
                SELECT * 
                FROM change_logs cl
                JOIN records r ON cl.产品_id = r.产品_id
                WHERE cl.产品_id = ? AND r.仓库_id = ?
                ORDER BY cl.更新时间 DESC
                LIMIT 1;
                """
        self.cursor.execute(query, (product_id, warehouse_id))
        row = self.cursor.fetchone()

        if not row:
            return None

        # Get column names dynamically, excluding 记录_id
        column_names = [col for col in self._get_column_names('change_logs') if col != '记录_id']

        # Convert the row to a dictionary
        change_log_dict = dict(zip(column_names, row[1:]))  # Skip the first column (记录_id)
        del change_log_dict['使用量']

        return change_log_dict









