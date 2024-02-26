import json


def json_to_dict(path):
    with open(path) as schema_json:
        dict_text = schema_json.read()

    dict_obj = json.loads(dict_text)
    return dict_obj
