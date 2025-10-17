import json
import os
import re
from pathlib import Path

def extract_required_sections(content):
    """
    从system的content中提取# 用户信息 和 # 双方共同信息部分
    """
    # 使用正则表达式匹配这两个部分
    user_info_pattern = r'(# 用户信息\s*\{[^}]*\})'
    common_info_pattern = r'(# 双方共同信息\s*\{[^}]*\})'
    
    user_info_match = re.search(user_info_pattern, content, re.DOTALL)
    common_info_match = re.search(common_info_pattern, content, re.DOTALL)
    
    result = ""
    
    if user_info_match:
        result += user_info_match.group(1) + "\n"
    
    if common_info_match:
        result += common_info_match.group(1)
    
    return result.strip()

def process_json_file(file_path):
    """
    处理单个JSON文件
    """
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否是列表格式
        if not isinstance(data, list):
            print(f"跳过文件 {file_path}: 不是列表格式")
            return False
        
        # 遍历所有消息
        modified = False
        for message in data:
            if isinstance(message, dict) and message.get('role') == 'system':
                original_content = message.get('content', '')
                # 提取需要保留的部分
                new_content = extract_required_sections(original_content)
                
                if new_content != original_content:
                    message['content'] = new_content
                    modified = True
        
        # 如果有修改,保存文件
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 已处理: {file_path}")
            return True
        else:
            print(f"- 无需修改: {file_path}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"✗ JSON解析错误 {file_path}: {e}")
        return False
    except Exception as e:
        print(f"✗ 处理文件出错 {file_path}: {e}")
        return False

def main():
    """
    主函数:遍历指定目录下的所有JSON文件并处理
    """
    # 基础路径
    base_path = r"D:\Users\32354\Desktop\algorithm_nas\empathy_data"
    
    if not os.path.exists(base_path):
        print(f"错误: 路径不存在 {base_path}")
        return
    
    # 统计信息
    total_files = 0
    processed_files = 0
    
    # 遍历所有子目录
    for root, dirs, files in os.walk(base_path):
        # 只处理empathy子目录中的文件
        if 'empathy' in root:
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    total_files += 1
                    if process_json_file(file_path):
                        processed_files += 1
    
    # 输出统计信息
    print("\n" + "="*50)
    print(f"处理完成!")
    print(f"总文件数: {total_files}")
    print(f"已修改文件数: {processed_files}")
    print(f"未修改文件数: {total_files - processed_files}")
    print("="*50)

if __name__ == "__main__":
    main()