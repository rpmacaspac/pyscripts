import sys

def convert_to_valid_json(input_file):
    json_data = {}
    with open(input_file, 'r') as file:
        for line in file:
            line = line.strip()
            if '"name"' in line and line.endswith(','):
                name = line.split(': ')[1].strip().split(',')[0].strip('"')
                line = next(file).strip()
                if line.startswith('"value"'):
                    value = line.split(': ')[1].strip().strip('"')
                    json_data[name] = value
    return json_data

def main():
    input_file = sys.argv[1]
    output_json = convert_to_valid_json(input_file)
    
    # Print the JSON object
    print("{")
    for i, (key, value) in enumerate(output_json.items()):
        print(f'    "{key}": "{value}"', end="")
        if i < len(output_json) - 1:
            print(",")
        else:
            print()
    print("}")

if __name__ == "__main__":
    main()
