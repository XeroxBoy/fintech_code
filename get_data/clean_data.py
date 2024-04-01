import os
import re


def remove_subset_files(directory):
    files = os.listdir(directory)
    file_dict = {}

    # 构建字典，以股票代码和数据类型为键，值为包含起始日期的文件列表
    for file_name in files:
        print(file_name)
        # 使用正则表达式从文件名中提取股票代码、数据类型和起始日期
        pattern = r'(\w+)\.(\d+)\_(\w+)\_(\d{4}\-\d{2}\-\d{2})\_(\d{4}\-\d{2}\-\d{2})\.csv'
        match = re.match(pattern, file_name)
        if match:
            stock_code = match.group(1)
            data_type = match.group(2)
            start_date = match.group(3)
            file_info = (start_date, file_name)
            key = (stock_code, data_type)
            if key in file_dict:
                file_dict[key].append(file_info)
            else:
                file_dict[key] = [file_info]

    # 删除时间范围属于子集的重叠文件
    files_before_deletion = sum([len(file_list) for file_list in file_dict.values()])
    files_deleted = 0

    for key, file_list in file_dict.items():
        if len(file_list) > 1:
            sorted_files = sorted(file_list, key=lambda x: x[0])  # 按起始日期排序
            files_to_delete = []
            for i in range(len(sorted_files) - 1):
                curr_file = sorted_files[i]
                next_file = sorted_files[i + 1]
                if curr_file[0] <= next_file[0]:
                    files_to_delete.append(next_file[1])
            for file_to_delete in files_to_delete:
                file_path = os.path.join(directory, file_to_delete)
                print(f"删除文件: {file_path}")
                os.remove(file_path)  # 如果确定要删除文件，取消注释此行
                files_deleted += 1

    files_after_deletion = files_before_deletion - files_deleted
    print(f"删除前的文件数量: {files_before_deletion}")
    print(f"删除后的文件数量: {files_after_deletion}")


# 指定目录进行操作
directory_path = '../data/stock'
remove_subset_files(directory_path)
