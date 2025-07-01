import os
import datetime
import json


def get_today_date():
    # 获取当前日期和时间
    today = datetime.datetime.now()
    
    # 格式化日期为字符串，格式为 "YYYY-MM-DD"
    date_string = today.strftime("%Y%m%d")
    return date_string

def file_size(path,n):
    has_directory = False
    has_file = False
    file_size = 0

    # 获取目录中的所有条目
    pre_entries = os.listdir(path)

    for entry in pre_entries:
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path):
            has_directory = True
        elif os.path.isfile(entry_path):
            has_file = True
        break
    if has_file:
        for file_name in pre_entries:
            # 分割文件名和扩展名
            base, ext = file_name.split(".")
            # 分割前缀和数字部分
            prefix, old_num = base.rsplit("_", 1)
            # 计算数字部分的位数
            num_digits = len(old_num)
            # 格式化新数字，保持位数（用 zfill 补零）
            new_num = str(n).zfill(num_digits)
            # 重新组合文件名
            new_file_name = f"{prefix}_{new_num}.{ext}"
            break
        file_path = os.path.join(path,new_file_name)
        #print(file_path)
        file_size += os.path.getsize(file_path)  # 获取文件大小（字节）
        return file_size

    if has_directory:
        # 遍历子目录，查找第 n 个文件
        for subdir in pre_entries:
            pre_entry =  os.listdir(os.path.join(path,subdir))
            for file_name in pre_entry:
                # 分割文件名和扩展名
                base, ext = file_name.split(".")
                # 分割前缀和数字部分
                prefix, old_num = base.rsplit("_", 1)
                # 计算数字部分的位数
                num_digits = len(old_num)
                # 格式化新数字，保持位数（用 zfill 补零）
                new_num = str(n).zfill(num_digits)
                # 重新组合文件名
                new_file_name = f"{prefix}_{new_num}.{ext}"
                break
            
            file_path = os.path.join(path,subdir,new_file_name)
            #print(file_path)
            file_size += os.path.getsize(file_path)  # 获取文件大小（字节）
        return file_size
                                

def get_data_size(fold_path, data): # 文件大小单位(MB)
    try:
        size_bytes = 0
        directory_path = os.path.join(fold_path, get_today_date())
        print(directory_path)
        #directory_path = os.path.join(fold_path1, "2025701")
        if not os.path.exists(directory_path):
            return 500
        # task_path = os.path.join(directory_path,f"{str(data['task_name'])}_{str(data['task_id'])}")

        task_path=fold_path
        opdata_path = os.path.join(task_path,"meta","op_dataid.jsonl")
        with open(opdata_path, 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    # 去除行末的换行符，并解析为 JSON 对象
                    json_object_data = json.loads(line.strip())
                    if json_object_data["dataid"] == str(data["task_data_id"]):
                        episode_index = json_object_data["episode_index"]
                        break
                except json.JSONDecodeError as e:
                    print(f"解析 JSON 失败，行内容: {line.strip()}, 错误信息: {e}")
        
        entries_1 = os.listdir(task_path) 
        for entry in entries_1:
            if entry == "meta":
                continue
            data_path = os.path.join(task_path,entry,"chunk-000")
            size_bytes += file_size(data_path,episode_index)
        size_mb = round(size_bytes / (1024 * 1024),2)
        return size_mb


    except Exception as e:
        print(str(e))
        return 500
    




def get_data_duration(fold_path,data):  # 文件时长单位(s)
    try:
        directory_path = os.path.join(fold_path, get_today_date())
        print(directory_path)
        #directory_path = os.path.join(fold_path1, "2025701")
        if not os.path.exists(directory_path):
            return 30
        # task_path = os.path.join(directory_path,f"{str(data['task_name'])}_{str(data['task_id'])}")
        task_path = fold_path
        info_path = os.path.join(task_path,"meta","info.json")
        opdata_path = os.path.join(task_path,"meta","op_dataid.jsonl")
        episodes_path = os.path.join(task_path,"meta","episodes.jsonl")
        with open(info_path,"r",encoding="utf-8") as f:
            info_data = json.load(f)
            fps = info_data["fps"] # 
        with open(opdata_path, 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    # 去除行末的换行符，并解析为 JSON 对象
                    json_object_data = json.loads(line.strip())
                    if json_object_data["dataid"] == str(data["task_data_id"]):
                        episode_index = json_object_data["episode_index"]
                        break
                except json.JSONDecodeError as e:
                    print(f"解析 JSON 失败，行内容: {line.strip()}, 错误信息: {e}")
        with open(episodes_path, 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    # 去除行末的换行符，并解析为 JSON 对象
                    json_object_data = json.loads(line.strip())
                    if json_object_data["episode_index"] == episode_index:
                        length= json_object_data["length"]
                        break
                except json.JSONDecodeError as e:
                    print(f"解析 JSON 失败，行内容: {line.strip()}, 错误信息: {e}")
        duration = round(length/fps,2)
        return duration        
    except Exception as e:
        print(str(e))
        return 30
    
# if __name__ == '__main__':
#     fold_path = '/home/liuyou/Documents'
#     data = {
#         "task_id": "187",
#         "task_name": "刀具安全取放",
#         "task_data_id": "2043",
#         "collector_id":"001",
#         "task_steps": [
#             {
#                 "doruation": "10",
#                 "instruction": "put"
#             },
#             {
#                 "doruation": "2",
#                 "instruction": "close"
#             },
#             {
#                 "doruation": "5",
#                 "instruction": "clean"
#             }
#         ]
#     } # 之后作为参数传递
#     print(data_size(fold_path,data))
#     print(data_duration(fold_path,data))
        









