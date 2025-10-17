import json
import time
import re
from typing import Dict, Optional
import requests

class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str, 
                 timeout: int = 60, max_retries: int = 3, retry_interval: int = 2):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        
    def _extract_json_object(self, text: str) -> Optional[str]:
        """
        从文本中提取完整的JSON对象
        """
        # 更强健的markdown代码块移除
        # 移除开始的markdown标记
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        # 移除结束的markdown标记
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
        text = text.strip()
        
        # 如果文本为空，直接返回None
        if not text:
            return None
        
        # 查找JSON对象的开始
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # 使用栈来匹配括号，找到完整的JSON对象
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            # 处理转义字符
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            # 处理字符串
            if char == '"':
                in_string = not in_string
                continue
            
            # 只在非字符串中计数括号
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # 找到完整的JSON对象
                        json_str = text[start_idx:i+1]
                        # 验证提取的JSON是否完整
                        try:
                            json.loads(json_str)
                            return json_str
                        except json.JSONDecodeError:
                            # 如果JSON不完整，继续寻找
                            continue
        
        # 如果没有找到完整的JSON对象，但存在开始的大括号，返回从开始到末尾的内容
        if start_idx != -1:
            potential_json = text[start_idx:].strip()
            # 尝试解析，如果可以解析就返回
            try:
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _safe_parse_json(self, json_str: str) -> Optional[Dict]:
        """
        安全地解析JSON，处理常见的格式问题
        """
        if not json_str:
            return None
        
        try:
            # 首先尝试直接解析
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 尝试修复常见问题
        try:
            # 替换智能引号为普通引号
            fixed = json_str.replace('"', '"').replace('"', '"')
            fixed = fixed.replace(''', "'").replace(''', "'")
            
            # 尝试解析
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # 尝试手动提取字段
        try:
            result = {}
            
            # 提取话题归类
            match = re.search(r'"话题归类"\s*:\s*"([^"]*)"', json_str)
            if match:
                result['话题归类'] = match.group(1)
            
            # 提取话题标签 (处理数组) - 修改字段名
            match = re.search(r'"话题标签"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
            if match:
                tags_str = match.group(1)
                # 提取所有引号中的内容
                tags = re.findall(r'"([^"]*)"', tags_str)
                result['话题标签'] = tags
            
            # 提取话题描述
            match = re.search(r'"话题描述"\s*:\s*"([^"]*)"', json_str)
            if match:
                result['话题描述'] = match.group(1)
            
            # 提取相关回忆（可能跨行）
            match = re.search(r'"相关回忆"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str, re.DOTALL)
            if match:
                memory = match.group(1)
                # 清理换行和多余空格
                memory = re.sub(r'\s+', ' ', memory).strip()
                result['相关回忆'] = memory
            
            # 验证是否提取到所有必需字段 - 修改字段名
            required_fields = ['话题归类', '话题标签', '话题描述', '相关回忆']
            if all(field in result for field in required_fields):
                return result
            
        except Exception as e:
            print(f"  ⚠️  手动提取失败: {e}")
        
        return None
    
    def call_llm(self, prompt: str) -> Optional[Dict]:
        """
        调用LLM API并返回解析后的JSON结果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/conversation-analysis",
            "X-Title": "Conversation Analysis Tool"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
                # 提取LLM返回的内容
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    
                    # 调试信息：显示完整返回内容
                    if attempt == 0:
                        print(f"  完整返回内容长度: {len(content)}")
                        if len(content) < 100:
                            print(f"  完整返回内容: {content}")
                        else:
                            print(f"  返回内容开头: {content[:200]}...")
                            print(f"  返回内容结尾: ...{content[-200:]}")
                    
                    # 提取JSON对象
                    json_str = self._extract_json_object(content)
                    
                    if not json_str:
                        print(f"  ⚠️  无法从返回内容中提取JSON对象")
                        if attempt < self.max_retries - 1:
                            print(f"  第 {attempt + 1} 次尝试失败，{self.retry_interval}秒后重试...")
                            time.sleep(self.retry_interval)
                        continue
                    
                    # 解析JSON
                    parsed_json = self._safe_parse_json(json_str)
                    
                    if parsed_json:
                        # 验证必需字段
                        required_fields = ['话题归类', '话题标签', '话题描述', '相关回忆']
                        if all(field in parsed_json for field in required_fields):
                            return parsed_json
                        else:
                            missing = set(required_fields) - set(parsed_json.keys())
                            print(f"  ⚠️  缺少字段: {missing}")
                            print(f"  实际字段: {list(parsed_json.keys())}")
                    else:
                        print(f"  ⚠️  JSON解析失败")
                        if attempt == 0 and json_str:
                            print(f"  提取的JSON长度: {len(json_str)}")
                            print(f"  提取的JSON: {json_str[:300]}...")
                    
                    if attempt < self.max_retries - 1:
                        print(f"  第 {attempt + 1} 次尝试失败，{self.retry_interval}秒后重试...")
                        time.sleep(self.retry_interval)
                    
            except requests.exceptions.RequestException as e:
                print(f"  ⚠️  API请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    print(f"  {self.retry_interval}秒后重试...")
                    time.sleep(self.retry_interval)
            except Exception as e:
                print(f"  ⚠️  未知错误: {e}")
                import traceback
                traceback.print_exc()
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)
        
        return None