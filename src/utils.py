import os
import json


def gen_filename(data_folder, filename):
    return f"{data_folder}/{filename}"


def save_data_json(full_path, data):
    f = open(full_path, "w+")
    json.dump(data, f)
    f.close()


def read_data_json(full_path):
    if not os.path.exists(full_path)
        return {}

    f = open(full_path, "r")
    data = json.load(f)
    f.close()

    return data
