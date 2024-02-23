import tkinter as tk
from tkinter import messagebox
import boto3
import copy
import os
import sys

def describe_task_definition(ecs_client, task_definition_arn):
    response = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
    return response['taskDefinition']

def get_old_smtp_credentials(task_definition):
    old_smtp_user = None
    old_smtp_pass = None
    smtp_user_key = None
    smtp_pass_key = None
    for container in task_definition['containerDefinitions']:
        for environment in container.get('environment', []):
            key = environment.get('name', '').lower()
            value = environment.get('value', '')
            if 'smtp' in key or 'mail' in key:
                if 'user' in key or 'username' in key:
                    old_smtp_user = value
                    smtp_user_key = key
                elif 'pass' in key or 'password' in key:
                    old_smtp_pass = value
                    smtp_pass_key = key
    return old_smtp_user, old_smtp_pass, smtp_user_key, smtp_pass_key

def update_strings(obj, old_smtp, new_smtp):
    if isinstance(obj, str):
        return obj.replace(old_smtp, new_smtp)
    elif isinstance(obj, list):
        return [update_strings(item, old_smtp, new_smtp) for item in obj]
    elif isinstance(obj, dict):
        updated_obj = copy.deepcopy(obj)
        for key, value in updated_obj.items():
            updated_obj[key] = update_strings(value, old_smtp, new_smtp)
        return updated_obj
    else:
        return obj

def register_new_task_definition(ecs_client, task_definition):
    response = ecs_client.register_task_definition(
        family = task_definition['family'],
        containerDefinitions=task_definition['containerDefinitions'],
        volumes = task_definition.get('volumes'),
        memory = task_definition.get('memory'), # Appended for personal account - might not work with other TD
    )
    new_task_definition_arn = response['taskDefinition']['taskDefinitionArn']
    return new_task_definition_arn

def update_credentials():
    try:
        account = account_entry.get()
        session = boto3.Session(profile_name=account)
        client = session.client('ecs')

        current_td = task_definition_entry.get()

        task_definition = describe_task_definition(client, current_td)
        task_definition_arn = task_definition['taskDefinitionArn']

        old_smtp_user, old_smtp_pass, smtp_user_key, smtp_pass_key = get_old_smtp_credentials(task_definition)

        if not old_smtp_user or not old_smtp_pass:
            messagebox.showerror("Error", "Old SMTP credentials not found in task definition environment variables.")
            return

        old_credentials_text.config(state=tk.NORMAL)
        old_credentials_text.delete(1.0, tk.END)
        old_credentials_text.insert(tk.END, f"Old SMTP username ('{smtp_user_key}'): {old_smtp_user}\n")
        old_credentials_text.insert(tk.END, f"Old SMTP password ('{smtp_pass_key}'): {old_smtp_pass}\n")
        old_credentials_text.config(state=tk.DISABLED)

        # Dynamically adjust the height of old_credentials_text based on the content
        old_credentials_text_height = min(10, old_credentials_text.get("1.0", "end-1c").count("\n") + 2)
        old_credentials_text.config(height=old_credentials_text_height)

        new_smtp_user = new_smtp_user_entry.get()
        new_smtp_pass = new_smtp_pass_entry.get()

        if not new_smtp_user or not new_smtp_pass:
            messagebox.showerror("Error", "New SMTP credentials not provided.")
            return

        if len(old_smtp_user) != len(new_smtp_user) or len(old_smtp_pass) != len(new_smtp_pass):
            messagebox.showerror("Error", "Old and new SMTP credentials must have the same length.")
            return

        updated_task_definition = update_strings(task_definition, old_smtp_user, new_smtp_user)
        updated_task_definition = update_strings(updated_task_definition, old_smtp_pass, new_smtp_pass)

        new_task_definition_arn = register_new_task_definition(client, updated_task_definition)

        new_task_definition_entry.delete(0, tk.END)
        new_task_definition_entry.insert(tk.END, new_task_definition_arn)

        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, f"New task definition registered: {new_task_definition_arn}\n")
        log_text.config(state=tk.DISABLED)

        messagebox.showinfo("Success", f"New task definition registered: {new_task_definition_arn}")
    except KeyboardInterrupt:
        messagebox.showinfo("Info", "Exiting...")
        sys.exit(1)
    except Exception as e:
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, f"Error: {str(e)}\n")
        log_text.config(state=tk.DISABLED)
        messagebox.showerror("Error", str(e))

def search_task_definition():
    try:
        account = account_entry.get()
        session = boto3.Session(profile_name=account)
        client = session.client('ecs')

        current_td = task_definition_entry.get()

        task_definition = describe_task_definition(client, current_td)
        task_definition_arn = task_definition['taskDefinitionArn']

        old_smtp_user, old_smtp_pass, smtp_user_key, smtp_pass_key = get_old_smtp_credentials(task_definition)

        if not old_smtp_user and not old_smtp_pass:
            messagebox.showerror("Error", "Old SMTP credentials not found in task definition environment variables.")
            return

        old_credentials_text.config(state=tk.NORMAL)
        old_credentials_text.delete(1.0, tk.END)
        old_credentials_text.insert(tk.END, f"Old SMTP username ('{smtp_user_key}'): {old_smtp_user}\n")
        old_credentials_text.insert(tk.END, f"Old SMTP password ('{smtp_pass_key}'): {old_smtp_pass}\n")
        old_credentials_text.config(state=tk.DISABLED)

        # Dynamically adjust the height of old_credentials_text based on the content
        old_credentials_text_height = min(10, old_credentials_text.get("1.0", "end-1c").count("\n") + 2)
        old_credentials_text.config(height=old_credentials_text_height)

    except Exception as e:
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, f"Error: {str(e)}\n")
        log_text.config(state=tk.DISABLED)
        messagebox.showerror("Error", str(e))

# Create Tkinter window
window = tk.Tk()
window.title("SMTP Credential Updater")
window.geometry("900x400")  # Fixed size window

# Account Name entry
tk.Label(window, text="Account profile:", font=("Arial", 8, "italic")).grid(row=0, column=0, sticky="w")
account_entry = tk.Entry(window)
account_entry.grid(row=0, column=1, sticky="ew")

# Task Definition ARN entry
tk.Label(window, text="Task Definition ARN:").grid(row=1, column=0, sticky="w")
task_definition_entry = tk.Entry(window)
task_definition_entry.grid(row=1, column=1, sticky="ew")

# New SMTP Username entry
tk.Label(window, text="New SMTP Username:").grid(row=2, column=0, sticky="w")
new_smtp_user_entry = tk.Entry(window)
new_smtp_user_entry.grid(row=2, column=1, sticky="ew")

# New SMTP Password entry
tk.Label(window, text="New SMTP Password:").grid(row=3, column=0, sticky="w")
new_smtp_pass_entry = tk.Entry(window)
new_smtp_pass_entry.grid(row=3, column=1, sticky="ew")

# Frame to contain update and search buttons
button_frame = tk.Frame(window)
button_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))

# Search button for Task Definition ARN
search_button = tk.Button(button_frame, text="Search", command=search_task_definition)
search_button.pack(side="left")

# Button to trigger update
update_button = tk.Button(button_frame, text="Update", command=update_credentials)
update_button.pack(side="left")

# Old SMTP Credentials display
tk.Label(window, text="Old SMTP Credentials:", anchor="w").grid(row=5, column=0, sticky="w")
old_credentials_text = tk.Text(window, height=2, width=30, wrap=tk.WORD)
old_credentials_text.grid(row=5, column=1, sticky="ew")
old_credentials_text.config(state=tk.DISABLED)

# Display for new task definition ARN
tk.Label(window, text="New Task Definition ARN:", anchor="w").grid(row=6, column=0, sticky="w")
new_task_definition_entry = tk.Entry(window)
new_task_definition_entry.grid(row=6, column=1, sticky="ew")

# Logs Textbox
tk.Label(window, text="Logs:", anchor="w").grid(row=7, column=0, sticky="w")
log_text = tk.Text(window, height=4, width=50, wrap=tk.WORD)
log_text.grid(row=8, column=0, columnspan=2, sticky="ew")
log_text.config(state=tk.DISABLED)

# Allow column to expand
window.columnconfigure(1, weight=1)

window.mainloop()
