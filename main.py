import weaviate
import json
import config
import datetime
import helper
from weaviate.util import generate_uuid5
from ctransformers import AutoModelForCausalLM
import argparse

client_addr = config.CLIENT_ADDR
class_name = config.CLASS_NAME
client = weaviate.Client(client_addr)
menu_path = config.MENU_PATH
schema_path = config.SCHEMA_PATH


def map_values_to_weaviate_with_ninfo(value, output_data):
    output_data.append({
        "name": value[0],
        "price": value[1],
        "details": {
            "nutritionalInfo": {
                "kcal": value[2]["nutritionalInfo"]["kcal"],
                "fat": value[2]["nutritionalInfo"]["fat"],
                "protein": value[2]["nutritionalInfo"]["protein"],
                "itemId": value[2]["nutritionalInfo"]["itemId"],
                "allergens": value[2]["nutritionalInfo"]["allergens"]
            },
            "available": value[2]["available"]
        }
    })
    return output_data


def map_values_to_weaviate_without_ninfo(value, output_data):
    output_data.append({
        "name": value[0],
        "price": value[1],
        "details": {
            "available": value[2]["available"]
        }
    })
    return output_data


def map_values_to_weaviate_format(input_data):
    output_data = []
    for key, value in input_data.items():
        if "nutritionalInfo" in value[2]:
            output_data = map_values_to_weaviate_with_ninfo(value, output_data)
        else:
            output_data = map_values_to_weaviate_without_ninfo(value, output_data)

    return output_data


def add_data_client(path_new_data, class_name_for_client="Menu"):
    all_data = helper.json_to_dict(path_new_data)

    for data in all_data.values():

        data = map_values_to_weaviate_format(data)

        client.batch.configure(batch_size=4)  # Configure batch
        with client.batch as batch:
            for data_obj in data:
                print(data_obj)

                batch.add_data_object(
                    data_obj,
                    class_name_for_client,
                    uuid=generate_uuid5(data_obj)  # Optional: Specify an object ID
                )


def get_response(client, query):
    response = (
        client.query
            .get(class_name="Menu", properties=["name", "price", "details{available}",
                                                "details{nutritionalInfo{allergens}}"])
            .with_near_text({"concepts": [query]})
            .with_additional(["distance"])
            .with_limit(3)
            .do()
    )
    return response


def parse_response_with_allergens_and_available(details, allergens):
    return "The product {} costs {} and has allergens {} is available " \
                            "and the distance of product with the query is {}".format(
                details["name"],
                details["price"],
                " ".join(allergens),
                details["_additional"]["distance"]
            )


def parse_response_with_allergens_and_unavailable(details, allergens):
    return "The product {} costs {} and has allergens {} but is not available " \
                            "and the distance of product with the query is {}".format(
                details["name"],
                details["price"],
                " ".join(allergens),
                details["_additional"]["distance"]
            )


def parse_response_without_allergens_and_unavailable(details):
    return "The product {} costs {} but is not available " \
                            "and the distance of product with the query is {}".format(
                details["name"],
                details["price"],
                details["_additional"]["distance"]
            )


def parse_response(response):
    details_text = ""

    for details in response["data"]["Get"]["Menu"]:
        allergens = []
        if details["details"]["nutritionalInfo"] is not None:
            for allergen in details["details"]["nutritionalInfo"]["allergens"]:
                allergens.append(allergen)
        available = details["details"]["available"]
        if allergens and available:
            details_text += parse_response_with_allergens_and_available(details, allergens)
        elif allergens and not available:
            details_text += parse_response_with_allergens_and_unavailable(details, allergens)
        else:
            details_text += parse_response_without_allergens_and_unavailable(details)
        details_text += "\n"

    return details_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-data', dest="data")
    parser.add_argument('-query', dest="query")
    add_data = False
    query = "What is the best deal?"

    if parser.parse_args().data == "true":
        add_data = True

    if parser.parse_args().query:
        query = parser.parse_args().query
    else:
        print('Please provide the query in arguments\n Example: python main.py -query "Which Veggie options you have?"')
        exit()
    existing_classes = client.schema.get()['classes']

    if not any(cls['class'] == class_name for cls in existing_classes):
        schema = helper.json_to_dict(schema_path)
        client.schema.create_class(schema)

    if add_data:
        add_data_client(menu_path, class_name)

    response = get_response(client, query)
    details_text = parse_response(response)

    llm = AutoModelForCausalLM.from_pretrained("TheBloke/Mistral-7B-v0.1-GGUF",
                                               model_file="mistral-7b-v0.1.Q4_K_M.gguf",
                                               model_type="mistral", gpu_layers=0)
    start = datetime.datetime.now()

    answer = llm("<|prompter|>Given the following details \n{}, answer the query like a chatbot: {}?</s><|assistant|>"
              .format(details_text, query))
    if "<" in answer:
      answer = answer.split("<")[0]

    end = now = datetime.datetime.now()

    print(answer)
    print("Time taken in seconds: ")
    print((end - start).total_seconds())


