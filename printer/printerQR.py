import serial
import time

def print_string_to_printer(content, content1):
    """
    将指定字符串发送到通过串口连接的打印机进行打印。

    参数:
        content (str): 要打印的字符串。
    """
    def string_to_hex(input_string):
        """将字符串转换为十六进制表示"""
        return input_string.encode('utf-8').hex()

    def generate_instructions(print_content, print_content1):
        """
        动态生成打印指令。

        参数:
            print_content (str): 要打印的内容（二维码和文本内容）。

        返回:
            list: 包含所有打印指令的列表。
        """
        instructions = []

        # 1. 设置打印范围
        instructions.append("1A5B01000000008001AA0000")  # 设置X,Y轴打印初始位置和范围

        # 2. 打印二维码
        qr_code_start = "1A3100"                          # 打印二维码标签开始
        qr_version = "01"                                 # 二维码版本 [0-20]
        qr_error_correction = "04"                        # 矫错等级 [1-4]
        qr_position = "15001500"                         # X,Y轴打印位置
        qr_size = "04"                                   # 二维码大小 [1-7]
        qr_rotation = "00"                               # 旋转角度 [0-3]
        qr_content = string_to_hex(print_content)         # 二维码内容
        qr_end = "00"                                    # 截止数据流
        instructions.append(f"{qr_code_start}{qr_version}{qr_error_correction}{qr_position}{qr_size}{qr_rotation}{qr_content}{qr_end}")

        # 3. 打印文本内容
        text_start = "1A5401"                             # 文本打印标签开始
        text_position = "80002000"                        # X,Y轴打印位置
        text_fixed = "006000"                             # 固定不变
        text_size = "11"                                  # 打印文字大小 [11, 22, 33, 44, 55, 66]
        text_content = string_to_hex(print_content)       # 打印内容
        text_end = "00"                                   # 结束标志
        instructions.append(f"{text_start}{text_position}{text_fixed}{text_size}{text_content}{text_end}")

        # 3. 打印文本内容
        text_start1 = "1A5401"                             # 文本打印标签开始
        text_position1 = "80004000"                        # X,Y轴打印位置
        text_fixed1 = "006000"                             # 固定不变
        text_size1 = "11"                                  # 打印文字大小 [11, 22, 33, 44, 55, 66]
        text_content1 = string_to_hex(print_content1)       # 打印内容
        text_end1 = "00"                                   # 结束标志
        instructions.append(f"{text_start1}{text_position1}{text_fixed1}{text_size1}{text_content1}{text_end1}")

        # 4. 标签打印结束
        instructions.append("1A5D00")

        # 5. 将内容打印到纸上
        instructions.append("1A4F00")

        return instructions

    def hex_to_bytes(hex_str):
        """将十六进制字符串转换为字节流"""
        return bytes.fromhex(hex_str)

    # 初始化串口
    ser = serial.Serial('/dev/ttyAMA0', 9600)  # 根据实际情况修改串口号和波特率
    if not ser.is_open:
        print("无法打开串口")
        return

    try:
        # 动态生成指令
        instructions = generate_instructions(content, content1)

        # 合并所有指令为一个字节流
        all_data = b"".join(hex_to_bytes(instr) for instr in instructions)

        # 发送数据到打印机
        ser.write(all_data)
        print("指令已发送到打印机！")
    except Exception as e:
        print(f"打印失败: {e}")
    finally:
        ser.close()

# # 示例调用
# if __name__ == "__main__":
#     # 只需调用一个函数并传入要打印的字符串
#     print_string_to_printer("1:1")



