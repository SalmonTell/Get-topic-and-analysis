import time
import os
from datetime import datetime
from config import *
from file_processor import *
from llm_client import LLMClient

def main():
    print("="*60)
    print("对话分析系统 - 启动")
    print("="*60)
    
    # 创建输出目录（如果不存在）
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"analysis_results_{timestamp}.json")
    progress_file = os.path.join(PROGRESS_DIR, f"progress_{timestamp}.json")
    
    print(f"\n本次运行信息:")
    print(f"  结果文件: {output_file}")
    print(f"  进度文件: {progress_file}")
    
    # 初始化LLM客户端
    llm_client = LLMClient(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        model=MODEL_NAME,
        timeout=REQUEST_TIMEOUT,
        max_retries=MAX_RETRIES,
        retry_interval=RETRY_INTERVAL
    )
    
    # 查找所有JSON文件
    print("\n正在扫描文件...")
    all_files = find_all_json_files(BASE_PATH)
    print(f"找到 {len(all_files)} 个文件")
    
    # 加载进度
    processed_files = load_progress(progress_file)
    print(f"已处理 {len(processed_files)} 个文件")
    
    # 加载已有结果
    results = load_existing_results(output_file)
    print(f"已有 {len(results)} 条分析结果")
    
    # 过滤出未处理的文件
    remaining_files = [f for f in all_files if f not in processed_files]
    
    # 应用测试模式限制
    if TEST_MODE:
        remaining_files = remaining_files[:TEST_FILE_COUNT]
        print(f"⚠️  测试模式：限制处理 {len(remaining_files)} 个文件")
    else:
        print(f"待处理 {len(remaining_files)} 个文件")
    
    if len(remaining_files) == 0:
        print("\n所有文件已处理完成！")
        return
    
    # 开始处理
    print("\n开始处理...")
    print("="*60)
    
    start_time = datetime.now()
    success_count = 0
    fail_count = 0
    
    for idx, file_path in enumerate(remaining_files, 1):
        print(f"\n[{idx}/{len(remaining_files)}] 处理: {os.path.basename(file_path)}")
        
        # 提取对话数据
        conversation_data = extract_conversation_data(file_path)
        
        if not conversation_data:
            print("✗ 提取数据失败，跳过")
            fail_count += 1
            continue
        
        # 格式化对话
        formatted_conversation = format_conversation_for_llm(
            conversation_data['conversation']
        )
        
        # 构建prompt
        prompt = ANALYSIS_PROMPT.format(
            system_content=conversation_data['system_content'],
            conversation=formatted_conversation
        )
        
        # 调用LLM
        print("  调用LLM分析中...")
        analysis_result = llm_client.call_llm(prompt)
        
        if analysis_result:
            # 保存结果
            result_entry = {
                "file_name": os.path.basename(file_path),
                "analysis": analysis_result
            }
            
            results.append(result_entry)
            processed_files.append(file_path)
            
            print(f"  ✓ 分析完成")
            print(f"    话题归类: {analysis_result.get('话题归类', 'N/A')}")
            print(f"    话题标签: {', '.join(analysis_result.get('话题标签', []))}")
            
            success_count += 1
            
            # 每处理10个文件保存一次进度
            if len(processed_files) % 10 == 0:
                save_progress(progress_file, processed_files)
                save_results(output_file, results)
                print(f"  💾 进度已保存")
        else:
            print("  ✗ 分析失败")
            fail_count += 1
        
        # 显示进度统计
        elapsed = (datetime.now() - start_time).total_seconds()
        avg_time = elapsed / idx if idx > 0 else 0
        remaining_time = avg_time * (len(remaining_files) - idx)
        
        print(f"  进度: {success_count}成功 / {fail_count}失败")
        print(f"  预计剩余时间: {remaining_time/60:.1f} 分钟")
        
        # 请求间隔
        if idx < len(remaining_files):
            time.sleep(REQUEST_INTERVAL)
    
    # 最终保存
    save_progress(progress_file, processed_files)
    save_results(output_file, results)
    
    # 统计信息
    print("\n" + "="*60)
    print("处理完成!")
    if TEST_MODE:
        print(f"⚠️  测试模式运行")
    print(f"总文件数: {len(all_files)}")
    print(f"本次处理: {len(remaining_files)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"总耗时: {(datetime.now() - start_time).total_seconds()/60:.1f} 分钟")
    print(f"\n结果已保存至: {output_file}")
    print(f"进度已保存至: {progress_file}")
    print("="*60)

if __name__ == "__main__":
    main()