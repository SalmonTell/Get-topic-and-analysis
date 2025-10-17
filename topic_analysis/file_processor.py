import json
import os
from pathlib import Path
from typing import Dict, List, Optional

def find_all_json_files(base_path: str) -> List[str]:
    """
    查找所有需要处理的JSON文件
    """
    json_files = []
    
    for root, dirs, files in os.walk(base_path):
        if 'empathy' in root:
            for file in files:
                if file.endswith('.json') and not file.endswith('_analysis.json'):
                    file_path = os.path.join(root, file)
                    json_files.append(file_path)
    
    return sorted(json_files)

def extract_conversation_data(file_path: str) -> Optional[Dict]:
    """
    从JSON文件中提取system content和对话记录
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            return None
        
        system_content = ""
        conversation = []
        
        for message in data:
            if not isinstance(message, dict):
                continue
                
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role == 'system':
                system_content = content
            elif role in ['user', 'assistant']:
                conversation.append({
                    'role': role,
                    'content': content
                })
        
        return {
            'system_content': system_content,
            'conversation': conversation
        }
        
    except Exception as e:
        print(f"✗ 读取文件失败 {file_path}: {e}")
        return None

def format_conversation_for_llm(conversation: List[Dict]) -> str:
    """
    将对话记录格式化为适合LLM阅读的文本
    """
    formatted = []
    
    for msg in conversation:
        role = msg['role']
        content = msg['content']
        
        if role == 'assistant':
            # 移除情感标签，只保留实际内容
            if content.startswith('['):
                end_idx = content.find(']')
                if end_idx > 0:
                    actual_content = content[end_idx+1:].strip()
                    formatted.append(f"[Assistant]: {actual_content}")
                else:
                    formatted.append(f"[Assistant]: {content}")
            else:
                formatted.append(f"[Assistant]: {content}")
        elif role == 'user':
            # 用户消息可能包含JSON格式的元信息
            try:
                user_data = json.loads(content)
                if isinstance(user_data, dict):
                    # 提取用户输入
                    if '[用户输入]' in user_data:
                        user_input = user_data['[用户输入]']
                        formatted.append(f"[User]: {user_input}")
                    
                    # 提取聊天提示信息（如果存在且不为空）
                    if '[聊天提示信息]' in user_data:
                        background_info = user_data['[聊天提示信息]']
                        if background_info and background_info.strip():
                            formatted.append(f"[Background]: {background_info}")
                else:
                    formatted.append(f"[User]: {content}")
            except:
                formatted.append(f"[User]: {content}")
        else:
            formatted.append(f"[{role.capitalize()}]: {content}")
    
    return "\n".join(formatted)

def save_progress(progress_file: str, processed_files: List[str]):
    """
    保存处理进度
    """
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                'processed_files': processed_files,
                'count': len(processed_files)
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存进度失败: {e}")

def load_progress(progress_file: str) -> List[str]:
    """
    加载处理进度
    """
    if not os.path.exists(progress_file):
        return []
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
            return progress_data.get('processed_files', [])
    except Exception as e:
        print(f"加载进度失败: {e}")
        return []

def save_results(output_file: str, results: List[Dict]):
    """
    保存分析结果
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存结果失败: {e}")

def load_existing_results(output_file: str) -> List[Dict]:
    """
    加载已有的分析结果
    """
    if not os.path.exists(output_file):
        return []
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载结果失败: {e}")
        return []