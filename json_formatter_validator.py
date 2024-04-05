import json
import tkinter as tk
from tkinter import filedialog
from tkinter import scrolledtext

def load_json_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)

def compare_json_files(json_data1, json_data2):
    differences = {}
    for key, value in json_data2.items():
        if key not in json_data1 or json_data1[key] != value:
            differences[key] = {'file1': json_data1.get(key, 'Not found'), 'file2': value}
    return differences

def convert_to_valid_json(input_text):
    try:
        # Attempt to parse the input text as JSON
        json_data = json.loads(input_text)
        return json_data
    except json.JSONDecodeError:
        # If parsing fails, assume the input follows the specific format and convert
        json_data = {}
        lines = input_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if '"name"' in line and line.endswith(','):
                name = line.split(': ')[1].strip().split(',')[0].strip('"')
                i += 1
                line = lines[i].strip()
                if line.startswith('"value"'):
                    value = line.split(': ')[1].strip().strip('"')
                    json_data[name] = value
            i += 1
        return json_data

def convert():
    input_text = input_box.get("1.0", tk.END)
    output_json = convert_to_valid_json(input_text)
    
    # Convert JSON data to formatted text
    output_text = json.dumps(output_json, indent=4)
    
    output_box.delete("1.0", tk.END)
    output_box.insert(tk.END, output_text)

def open_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        with open(file_path, 'r') as file:
            input_text = file.read()
            input_box.delete("1.0", tk.END)
            input_box.insert(tk.END, input_text)

def clear_text():
    input_box.delete("1.0", tk.END)
    output_box.delete("1.0", tk.END)
    result_box.delete("1.0", tk.END)

def compare_files():
    # Get the contents of both text boxes
    input_text1 = input_box.get("1.0", tk.END)
    input_text2 = output_box.get("1.0", tk.END)

    # Convert text box contents to JSON for comparison
    json_data1 = convert_to_valid_json(input_text1)
    json_data2 = convert_to_valid_json(input_text2)

    # Compare JSON data
    differences = compare_json_files(json_data1, json_data2)

    if differences:
        output_text = "\nDifferences found:\n"
        for key, value in differences.items():
            output_text += f"Key: {key}, Value in file1: {value['file1']}, Value in file2: {value['file2']}\n"
    else:
        output_text = "\nNo differences found."

    result_box.delete("1.0", tk.END)
    result_box.insert(tk.END, output_text)

def reset_comparison():
    result_box.delete("1.0", tk.END)

# Create the main window
root = tk.Tk()
root.title("JSON Formatter and Validator")

# Create Text widgets
file1_label = tk.Label(root, text="JSON1")
file1_label.grid(row=0, column=0, padx=(10, 5), pady=5)

input_box = scrolledtext.ScrolledText(root, height=20, width=50, wrap=tk.WORD)
input_box.grid(row=0, column=1, padx=(5, 10), pady=5, sticky="nsew")

file2_label = tk.Label(root, text="JSON2")
file2_label.grid(row=0, column=2, padx=(10, 5), pady=5)

output_box = scrolledtext.ScrolledText(root, height=20, width=50, wrap=tk.WORD)
output_box.grid(row=0, column=3, padx=(5, 10), pady=5, sticky="nsew")

result_box = scrolledtext.ScrolledText(root, height=10, width=100, wrap=tk.WORD)
result_box.grid(row=1, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

# Configure grid resizing
for i in range(4):
    root.grid_columnconfigure(i, weight=1)
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=1)

# Create buttons
convert_button = tk.Button(root, text="Convert", command=convert)
convert_button.grid(row=2, column=0, padx=10, pady=5)

open_button = tk.Button(root, text="Open File", command=open_file)
open_button.grid(row=2, column=1, padx=10, pady=5)

clear_button = tk.Button(root, text="Clear", command=clear_text)
clear_button.grid(row=2, column=2, padx=10, pady=5)

compare_button = tk.Button(root, text="Compare", command=compare_files)
compare_button.grid(row=2, column=3, padx=10, pady=5)

# reset_button = tk.Button(root, text="Reset", command=reset_comparison)
# reset_button.grid(row=3, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")

# Run the main event loop
root.mainloop()
