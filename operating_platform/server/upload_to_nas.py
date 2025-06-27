coding = "utf-8"

import threading
import datetime
import os
import time
import random
import json
import shutil
import os
import re
from nas_sdk import NASAuthenticator
 
nas_auth = NASAuthenticator()

fold_path1 = "/home/liuyou/Documents/local_to_nas/aloha-1/"
#fold_path2 = "/home/liuyou/Documents/local_to_nas/aloha-2/"

nas_path = "/传输路径/ceshi/cache"
nas_data_path = '/传输路径/ceshi/collect_data'


def copy_files(source_paths, destination_paths):
    """
    将源文件路径列表中的文件复制到目标文件路径列表中。
 
    :param source_paths: 源文件路径列表
    :param destination_paths: 目标文件路径列表
    :raises ValueError: 如果源文件路径和目标文件路径数量不匹配
    :raises FileNotFoundError: 如果源文件不存在
    """
    if len(source_paths) != len(destination_paths):
        raise ValueError("源文件路径和目标文件路径数量不匹配")
 
    for src, dest in zip(source_paths, destination_paths):
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            print(f"成功复制文件: {src} -> {dest}")
        except FileNotFoundError:
            print(f"源文件不存在: {src}")
        except Exception as e:
            print(f"复制文件时发生错误: {src} -> {dest}, 错误信息: {e}")


def add_random_milliseconds():
    # 获取当前时间戳（毫秒）
    current_timestamp = int(time.time() * 1000)
    
    # 生成一个随机的毫秒数（例如，1到1000毫秒之间）
    random_milliseconds = random.randint(1, 1000)
    
     # 将毫秒转换为秒，因为 time.sleep() 使用秒
    wait_time = random_milliseconds / 1000.0
    
    # 等待指定的时间
    time.sleep(wait_time)
    # 计算新的时间戳
    new_timestamp = current_timestamp + random_milliseconds
    print(f"当前时间戳: {current_timestamp}")
    print(f"随机毫秒数: {random_milliseconds}")
    print(f"新的时间戳: {new_timestamp}")
    return new_timestamp

def get_today_date():
    # 获取当前日期和时间
    today = datetime.datetime.now()
    
    # 格式化日期为字符串，格式为 "YYYY-MM-DD"
    date_string = today.strftime("%Y%m%d")
    print(date_string)
    return date_string

def extract_number(episode_name):
    # 使用正则表达式提取数字部分
    match = re.match(r'episode_(\d+)', episode_name)
    if match:
        return int(match.group(1))
    return 0  # 如果没有匹配，返回一个默认值


def get_path_after_last_data(file_path, name):
    """
    获取路径中最后一个名为 'data' 的子目录之后的路径。
 
    :param file_path: 文件的完整路径
    :return: 最后一个 'data' 目录之后的路径
    """
    parts = file_path.split(os.sep)
    last_data_index = -1
 
    # 查找最后一个 'data' 目录的索引
    for i, part in enumerate(parts):
        if part == name:
            last_data_index = i
 
    # 如果找到了 'data' 目录，则返回其后的路径
    if last_data_index != -1 and last_data_index + 1 < len(parts):
        return os.path.join(*parts[last_data_index + 1:])
    else:
        return file_path  # 如果没有找到 'data' 目录，返回完整路径
    
def delete_directory(directory_path):
    """
    删除指定目录及其所有内容。
 
    :param directory_path: 要删除的目录路径
    """
    try:
        # 检查目录是否存在
        if os.path.exists(directory_path):
            # 删除目录及其所有子目录和文件
            shutil.rmtree(directory_path)
            print(f"目录 '{directory_path}' 已成功删除。")
        else:
            print(f"目录 '{directory_path}' 不存在。")
    except Exception as e:
        print(f"删除目录时发生错误: {e}")

def delete_file(file_list):
    for file_path in file_list:
        # 检查文件是否存在
        if os.path.exists(file_path):
            try:
                # 删除文件
                os.remove(file_path)
                print(f"文件 {file_path} 已成功删除")
            except OSError as e:
                print(f"删除文件时出错: {e}")
        else:
            print(f"文件 {file_path} 不存在")

def increment_episode_number(filename, n=0):
    """
    增加文件名中数字部分的数值，并保持位数不变。
 
    :param filename: 原始文件名
    :param n: 要增加的数值，默认为 1
    :return: 修改后的文件名
    """
    # 使用正则表达式查找文件名中的数字部分
    match = re.search(r'(\d+)', filename)
    if n == 0:
       return filename
    if match:
        # 提取数字部分
        number_str = match.group(1)
        # 将数字部分转换为整数并增加 n
        new_number = int(number_str) + n
        # 计算数字部分的位数
        num_digits = len(number_str)
        # 格式化新的数字部分，保持位数不变
        new_number_str = f"{new_number:0{num_digits}d}"
        # 替换文件名中的数字部分
        new_filename = re.sub(r'\d+', new_number_str, filename, count=1)
        return new_filename
    else:
        # 如果没有找到数字部分，返回原始文件名
        return filename

def get_nth_file_in_subdirectories(fold_path, m, n=0, task=0,middle_name=None,meta=0):
    """
    获取指定目录或其子目录中的第 n 个文件。
 
    :param fold_path: 目录路径
    :param n: 要获取的文件索引（从 0 开始）
    :return: 找到的第 n 个文件的路径，如果没有找到则返回 None
    """
    # 检查目录是否存在
    if not os.path.isdir(fold_path):
        print(f"目录不存在: {fold_path}")
        return None
 
    # 获取目录中的所有条目
    pre_entries = os.listdir(fold_path)

    has_directory = False
    has_file = False
    file_list = []
    nas_file_list = []

    if meta:
        for subdir in pre_entries:
            # if subdir == "common_record.json":
            #     continue
            entry =  os.path.join(fold_path,subdir)
            file_list.append(entry)
            nas_file = get_path_after_last_data(entry,task)
            nas_final_path = os.path.join(nas_data_path,middle_name,nas_file)
            nas_file_list.append(nas_final_path)
        return file_list, nas_file_list
 
    for entry in pre_entries:
        entry_path = os.path.join(fold_path, entry)
        if os.path.isdir(entry_path):
            has_directory = True
        elif os.path.isfile(entry_path):
            has_file = True
        break

    if has_file:
        entries = sorted(pre_entries, key=extract_number)
        file_path = os.path.join(fold_path,entries[m])
        nas_file_path = os.path.join(fold_path,increment_episode_number(entries[m],n))
        nas_file = get_path_after_last_data(nas_file_path,task)
        nas_final_path = os.path.join(nas_data_path,middle_name,nas_file)
        return file_path,nas_final_path
    elif has_directory:
        # 遍历子目录，查找第 n 个文件
        for subdir in pre_entries:
            pre_entry =  os.listdir(os.path.join(fold_path,subdir))
            entry = sorted(pre_entry, key=extract_number)
            file_list.append(os.path.join(fold_path,subdir,entry[m]))
            nas_file_path = os.path.join(fold_path,subdir,increment_episode_number(entry[m],n))
            nas_file = get_path_after_last_data(nas_file_path,task)
            nas_final_path = os.path.join(nas_data_path,middle_name,nas_file)
            nas_file_list.append(nas_final_path)
        return file_list, nas_file_list  

def change_number(task_path, nas_meta_file_path, n, m):
    json_objects = []
    with open(task_path, 'r', encoding='utf-8') as file:
        # 跳过前 m 行
        for _ in range(m):
            next(file, None)  # 使用 next() 跳过 m 行
 
        # 处理剩余的行
        for line in file:
            try:
                # 去除行末的换行符，并解析为 JSON 对象
                json_object = json.loads(line.strip())
                json_object_copy = json_object.copy()
                json_object_copy["episode_index"] = int(json_object_copy["episode_index"]) + n
                json_objects.append(json_object_copy)
            except json.JSONDecodeError as e:
                print(f"解析 JSON 失败，行内容: {line.strip()}, 错误信息: {e}")
 
    # 将 json_objects 中的对象追加到文件
    with open(nas_meta_file_path, 'a', encoding='utf-8') as file:
        for json_obj in json_objects:
            file.write(json.dumps(json_obj) + '\n')

def create_json(path,data):   
    # 创建并写入 JSON 文件
    with open(path, 'w') as file:
        json.dump(data, file, indent=4) 

def modify_json(path,episodes_id):
    # 读取现有 JSON 文件
    try:
        with open(path, 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        existing_data = {}
    
    # 修改数据
    existing_data['episodes_id'] = episodes_id
    
    # 写回文件
    with open(path, 'w') as file:
        json.dump(existing_data, file, indent=4)





# 线程1的任务
def upload():
    json_object_list = []
    #directory_path = os.path.join(fold_path1, get_today_date())
    directory_path = os.path.join(fold_path1, "20250624")
    if not os.path.exists(directory_path):
        return  
    entries = os.listdir(directory_path) # 各任务列表
    # 筛选出子目录
    subdirectories = [entry for entry in entries if os.path.isdir(os.path.join(directory_path, entry))] # 仅筛选目录
    try:
        for task_data_name in subdirectories: # 1813490901
            each_task_path = os.path.join(directory_path,task_data_name)
            each_common_record_path = os.path.join(each_task_path,"meta","common_record.json")
            each_opdata_path = os.path.join(each_task_path,"meta","op_dataid.jsonl")
            with open(each_common_record_path,"r",encoding="utf-8") as f:
                data = json.load(f)
                task_id = data["task_id"] # 云平台任务id
                machine_id = data["machine_id"]
                task_name = data["task_name"]

            with open(each_opdata_path, 'r', encoding='utf-8') as file:
                for line in file:
                    try:
                        # 去除行末的换行符，并解析为 JSON 对象
                        json_object_data = json.loads(line.strip())
                        json_object_list.append(json_object_data)
                        last_line_json = json_object_data  # 更新最后一行的 JSON 对象
                    except json.JSONDecodeError as e:
                        print(f"解析 JSON 失败，行内容: {line.strip()}, 错误信息: {e}")
            task_number = int(last_line_json["episode_index"]) + 1 # 需要上传的文件数量

            entries_1 = os.listdir(each_task_path) 
            subdirectories_1 = [entry for entry in entries_1 if os.path.isdir(os.path.join(each_task_path, entry))] # data video meta
            
            timestamp_nas = str(add_random_milliseconds()) # 等待毫秒，造成时间差
            
            task_nas_path = os.path.join(nas_path,task_id) # 缓存目录
            print(task_nas_path)
            if not nas_auth.check_path_exists(task_nas_path):
                nas_auth.create_folder(task_nas_path)
            # if not os.path.exists(task_nas_path):
            #     os.makedirs(task_nas_path, exist_ok=False) # 创造缓存目录

            task_cache_name = machine_id + "***" + timestamp_nas # 创建缓存排队目录
            task_cache_nas_path = os.path.join(task_nas_path,task_cache_name)
            if not nas_auth.check_path_exists(task_cache_nas_path):
                nas_auth.create_folder(task_cache_nas_path)

            # if not os.path.exists(task_cache_nas_path):
            #     os.makedirs(task_cache_nas_path, exist_ok=False)

            time.sleep(3) # 等待所有目录创造
            while True:
                meta_file_list = []
                entries_2 = nas_auth.get_directory_structure(task_nas_path)
                print(entries_2)
                # entries_2 = os.listdir(task_nas_path) 
                subdirectories_2 = [entry.split("***") for entry in entries_2]
                # 找到时间戳最小的设备编号
                min_timestamp_device = min(subdirectories_2, key=lambda x: int(x[1]))[0]
                print(f"时间戳最小的设备编号是: {min_timestamp_device}")
                if min_timestamp_device == machine_id: # 轮到自己论次
                    middle_name = task_name + "_" + task_id
                    nas_target_path = os.path.join(nas_data_path,middle_name)
                    nas_meta_file_path = os.path.join(nas_data_path,middle_name,"meta","op_dataid.jsonl")
                    local_nas_meta_file_path = os.path.join(directory_path,"op_dataid.jsonl")
                    print(nas_meta_file_path)
                    if nas_auth.check_file_exists(nas_meta_file_path):
                        nas_auth.download_file(nas_meta_file_path,local_nas_meta_file_path)
                    if os.path.exists(local_nas_meta_file_path):
                        with open(local_nas_meta_file_path, 'r', encoding='utf-8') as file:
                            for line in file:
                                try:
                                    # 去除行末的换行符，并解析为 JSON 对象
                                    json_object = json.loads(line.strip())
                                    last_line_json = json_object  # 更新最后一行的 JSON 对象
                                except json.JSONDecodeError as e:
                                    print(f"解析 JSON 失败，行内容: {line.strip()}, 错误信息: {e}")
                        last_episode_id = int(last_line_json["episode_index"]) + 1

                        record_json_path = os.path.join(directory_path,task_id+".json")
                        if os.path.exists(record_json_path):
                            with open(record_json_path,"r",encoding="utf-8") as f:
                                data = json.load(f)
                                last_epid = data["episodes_id"] # 当前任务上次上传的记录
                                last_episode_id = last_episode_id - last_epid
                            if task_number <= last_epid:
                                delete_file([local_nas_meta_file_path])
                                nas_auth.delete_folder(task_cache_nas_path)
                                break
                        else:
                            last_epid = 0
                        
                        op_dataid_path = os.path.join(each_task_path,"meta","op_dataid.jsonl")
                        change_number(op_dataid_path,local_nas_meta_file_path,last_episode_id, last_epid)
                        
                        meta_file_list.append(local_nas_meta_file_path)

                        local_nas_episodes_path = os.path.join(directory_path,"episodes.jsonl")
                        nas_episodes_file_path = os.path.join(nas_data_path,middle_name,"meta","episodes.jsonl")
                        nas_auth.download_file(nas_episodes_file_path,local_nas_episodes_path)

                        episodes_path = os.path.join(each_task_path,"meta","episodes.jsonl")
                        change_number(episodes_path,local_nas_episodes_path,last_episode_id,last_epid)
                       
                        meta_file_list.append(local_nas_episodes_path)
                        
                        
                        local_episodes_stats_path = os.path.join(directory_path,"episodes_stats.jsonl")
                        nas_episodes_stats_file_path = os.path.join(nas_data_path,middle_name,"meta","episodes_stats.jsonl")
                        nas_auth.download_file(nas_episodes_stats_file_path,local_episodes_stats_path)

                        episodes_stats_path = os.path.join(each_task_path,"meta","episodes_stats.jsonl")                  
                        change_number(episodes_stats_path,local_episodes_stats_path,last_episode_id,last_epid)
                    
                        meta_file_list.append(local_episodes_stats_path)
                        # 先上传信息
                        # nas_auth.upload()
                        # delete_file()
                        
                        for data_id in range(last_epid,task_number):
                            cloud_data_id = json_object_list[data_id]["dataid"]
                            local_file_list = []
                            nas_file_list = []
                            for task_part in subdirectories_1:
                                if task_part == "meta":
                                    if data_id == last_epid:
                                        local_file_list.extend([local_nas_meta_file_path,local_nas_episodes_path,local_episodes_stats_path])
                                        nas_file_list.extend([nas_meta_file_path,nas_episodes_file_path,nas_episodes_stats_file_path])
                                else:
                                    fold_path = os.path.join(each_task_path,task_part,"chunk-000")
                                    local_file, nas_file = get_nth_file_in_subdirectories(fold_path,data_id,last_episode_id,task_data_name,middle_name,0)
                                    if isinstance(local_file, str):
                                        local_file_list.append(local_file)
                                        nas_file_list.append(nas_file)
                                    elif isinstance(local_file,list):
                                        local_file_list.extend(local_file)
                                        nas_file_list.extend(nas_file)
                            
                            #print(local_file_list)
                            #print(nas_file_list)
                            task_msg = {
                                "task_id":int(task_id),
                                "task_data_id":int(cloud_data_id),
                                "source_path":each_task_path,
                                "target_path":str(nas_file_list)
                            }
                            #copy_files(local_file_list,nas_file_list) # nas_auth.upload()
                            nas_auth.upload_file(task_msg,local_file_list,nas_file_list)
                        #delete_directory(task_cache_nas_path)
                        delete_file(meta_file_list)  
                        nas_auth.delete_folder(task_cache_nas_path)
                        modify_json(record_json_path,task_number)
                        break
                    else:
                        for data_id in range(task_number): # 遍历任务数量
                            cloud_data_id = json_object_list[data_id]["dataid"]
                            local_file_list = []
                            nas_file_list = []
                            for task_part in subdirectories_1:
                                if task_part == "meta":
                                    if data_id == 0:
                                        fold_path = os.path.join(each_task_path,task_part)
                                        local_file, nas_file = get_nth_file_in_subdirectories(fold_path,data_id,0,task_data_name,middle_name,1)
                                        if isinstance(local_file, str):
                                            local_file_list.append(local_file)
                                            nas_file_list.append(nas_file)
                                        elif isinstance(local_file,list):
                                            local_file_list.extend(local_file)
                                            nas_file_list.extend(nas_file)
                                else:
                                    fold_path = os.path.join(each_task_path,task_part,"chunk-000")
                                    local_file, nas_file = get_nth_file_in_subdirectories(fold_path,data_id,0,task_data_name,middle_name,0)
                                    if isinstance(local_file, str):
                                        local_file_list.append(local_file)
                                        nas_file_list.append(nas_file)
                                    elif isinstance(local_file,list):
                                        local_file_list.extend(local_file)
                                        nas_file_list.extend(nas_file)    
                            #print(local_file_list)
                            #print(nas_file_list)
                            task_msg = {
                                "task_id":int(task_id),
                                "task_data_id":int(cloud_data_id),
                                "source_path":each_task_path,
                                "target_path":str(nas_file_list)
                            }
                            #copy_files(local_file_list,nas_file_list) 
                            nas_auth.upload_file(task_msg,local_file_list,nas_file_list)
                        nas_auth.delete_folder(task_cache_nas_path)
                        record_json_path = os.path.join(directory_path,task_id+".json")
                        record_data = {
                            "episodes_id":task_number
                        }
                        create_json(record_json_path,record_data)
                        break
                else:
                    time.sleep(10)
    except Exception as e:
        print(str(e))