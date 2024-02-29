import sys

## Usage(compare_js.py):
## 1st and 2nd argument must be a valid json file
## if other format like "name": "key", "value": "value" then use converter.py

def convert_to_valid_json(input_file):
    json_data = {}
    with open(input_file, 'r') as file:
        for line in file:
            line = line.strip()
            if '"name"' in line and line.endswith(','):
                # Extract name
                name = line.split(': ')[1].strip().strip('"')
                
                # Move to the next line to get the value
                line = next(file).strip()
                if line.startswith('"value"'):
                    # Extract value
                    value = line.split(': ')[1].strip().strip('"')
                    
                    # Add to dictionary
                    json_data[name] = value

    return json_data

def main():
    input_file = sys.argv[1]
    output_json = convert_to_valid_json(input_file)
    for key, value in output_json.items():
        print(f'"{key}": "{value}",')  # Add comma and newline after printing each pair

if __name__ == "__main__":
    main()
