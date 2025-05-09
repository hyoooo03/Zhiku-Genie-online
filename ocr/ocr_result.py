import re

def extract_cas_number(text):
    """
    从 OCR 数据中提取 CAS 号，基于关键字"CAS"或"CAS号"。
    返回: (cas_number, success_flag)
    """
    # 正则表达式用于匹配 CAS 号
    cas_number_pattern = r'\b(\d{2,7}-\d{2}-\d)\b'
    
    # 查找 "CAS" 或 "CAS号" 关键字
    cas_keyword_index = text.lower().find("cas")
    cas_hao_keyword_index = text.lower().find("cas号")

    if cas_keyword_index != -1:
        # 从 "CAS" 关键字后面的内容中提取 CAS 号
        start_index = cas_keyword_index + len("cas")
        match = re.search(cas_number_pattern, text[start_index:])
        if match:
            return match.group(1), True  # 返回匹配到的 CAS 号和成功标志
    elif cas_hao_keyword_index != -1:
        # 从 "CAS号" 关键字后面的内容中提取 CAS 号
        start_index = cas_hao_keyword_index + len("cas号")
        match = re.search(cas_number_pattern, text[start_index:])
        if match:
            return match.group(1), True  # 返回匹配到的 CAS 号和成功标志

    return None, False  # 如果没有找到 CAS 号，返回 None 和失败标志

def extract_lot_number_from_data(text):
    """
    从 OCR 数据中提取批号（Lot Number），基于关键字"批"或"LOT"。
    返回: (lot_number, success_flag)
    """
    # 批号的正则表达式：假设批号是字母+数字的组合，长度为 5-15 个字符
    lot_pattern = r'(?:批|次号|批次号|批号|LOT|lot)\s*[:：]?\s*([A-Za-z0-9]{5,15})'
    
    # 使用正则表达式匹配关键字"批"或"LOT"后面的批号
    match = re.search(lot_pattern, text)
    if match:
        return match.group(1), True  # 返回匹配到的批号和成功标志
        
    return None, False  # 如果没有找到批号，返回 None 和失败标志

def extract_weight_from_data(text):
    """
    从 OCR 数据中提取重量信息（以 g, kg 等单位结尾的数值）。
    返回: (weight_str, success_flag)
    """
    weight_str = ""
    flag = True
    # 定义重量单位的正则表达式
    weight_pattern = r'(\d+(\.\d+)?)(g|kg|mg|lb|oz)\b'
    
    # 使用正则表达式查找所有匹配的重量信息
    matches = re.findall(weight_pattern, text, re.IGNORECASE)
    for match in matches:
        if flag:
            # 提取数字部分
            number = float(match[0])
            unit = match[2].lower()
            weight_str = str(number)+str(unit)
            flag = False
            return weight_str, True  # 返回找到的第一个重量信息和成功标志
    
    return "", False  # 如果没有找到任何重量信息，返回空字符串和失败标志

def extract_purity_from_data(text):
    """
    从 OCR 数据中提取纯度信息（以 % 结尾的数值）。
    返回: (purity_str, success_flag)
    """
    flag = True
    # 定义纯度的正则表达式
    purity_pattern = r'(\d+(\.\d+)?)%'
    
    purity = ""
    # 使用正则表达式查找所有匹配的纯度信息
    matches = re.findall(purity_pattern, text)
    for match in matches:
        if flag:
            # 提取完整的纯度字符串
            purity = f"{match[0]}%"  # 包括数字和百分号
            flag = False
            return purity, True  # 返回所有提取到的纯度信息和成功标志
    
    return "", False  # 如果没有找到任何纯度信息，返回空字符串和失败标志