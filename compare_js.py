import json
import sys

## Usage(compare_js.py):
## 1st and 2nd argument must be a valid json file
## if other format like "name": "key", "value": "value" then use converter.py

def load_json_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)

def extract_name_value_pairs(json_data):
    pairs = {}
    for key, value in json_data.items():
        pairs[key] = value
    return pairs

def compare_json_files(file1_data, file2_data):
    differences = []
    for key, value in file2_data.items():
        if key not in file1_data or file1_data[key] != value:
            differences.append((key, value))
    return differences

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <json_file1> <json_file2>")
        return

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    json_data1 = load_json_file(file1)
    json_data2 = load_json_file(file2)

    name_value_pairs1 = extract_name_value_pairs(json_data1)
    name_value_pairs2 = extract_name_value_pairs(json_data2)

    print("First JSON file:")
    for key, value in name_value_pairs1.items():
        print(f'"{key}": "{value}"')

    print("\nSecond JSON file:")
    for key, value in name_value_pairs2.items():
        print(f'"{key}": "{value}"')

    differences = compare_json_files(json_data1, json_data2)

    if differences:
        print("\nDifferences found:")
        for key, value in differences:
            print(f"Key: {key}, Value in {file2}: {value}, Value in {file1}: {json_data1.get(key, 'Not found')}")
    else:
        print("\nNo differences found.")

if __name__ == "__main__":
    main()
