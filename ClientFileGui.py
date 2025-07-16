# A simple chat client with file sharing capabilities and a GUI.

import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog, simpledialog, messagebox
import os

SERVER_IP = "127.0.0.1" # Change to your server's IP address "192.168..." for local network
PORT = 2011 # Port number for the server

client_socket = None
client_name = ""
open_file_windows = {}  # Dictionary to track opened file windows
SAVE_DIRECTORY = "received_files"  # Folder to save received files

if not os.path.exists(SAVE_DIRECTORY):
    os.makedirs(SAVE_DIRECTORY)  # Create folder if it doesn't exist

# GUI
def display_message(message):
    chat_box.config(state=tk.NORMAL)
    chat_box.insert(tk.END, message + "\n")
    chat_box.config(state=tk.DISABLED)
    chat_box.yview(tk.END)

def send_message():
    message = message_entry.get()
    if message:
        try:
            client_socket.send(message.encode())
            display_message(f"{client_name}: {message}")
            message_entry.delete(0, tk.END)
        except:
            display_message("Failed to send message.")

def receive_messages():
    while True:
        try:
            data = client_socket.recv(4096).decode()
            if not data:
                break

            if data.startswith("FILE_UPDATE::"): #FILE_UPDATE::filename::content
                _, filename, content = data.split("::", 2)
                root.after(0, update_file, filename, content)

            elif data.startswith("VERSIONS::"): #VERSIONS::filename::filename_v1::filename_v2::...
                try:
                    _, filename, versions_str = data.split("::", 2)
                    versions = versions_str.split("::") if versions_str else []  #  Properly split versions
                    if not versions or versions == [""]:
                        root.after(0, messagebox.showinfo, "No Versions", f"No versions available for {filename}")
                    else:
                        root.after(0, show_version_selection, filename, versions)  #  Display correctly
                except Exception as e:
                    print(f"Error processing versions: {e}")  #  Debugging

            elif data.startswith("ERROR::"): #ERROR::error message
                _, error_msg = data.split("::", 1)
                root.after(0, display_message, f" {error_msg}")

            else:
                root.after(0, display_message, data)
        except:
            break

def update_file(filename, content):
    file_path = os.path.join(SAVE_DIRECTORY, filename)
    with open(file_path, "w") as file:
        file.write(content)  # Save file locally
    if filename not in open_file_windows:
        open_file(filename, content)

def upload_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        with open(file_path, "r") as file:
            content = file.read()
        filename = os.path.basename(file_path)
        try:
            client_socket.send(f"FILE_UPLOAD::{filename}::{content}".encode())
            display_message(f"Uploaded: {filename}")
        except:
            display_message("Failed to upload file.")

def request_file():
    filename = simpledialog.askstring("Request File", "Enter filename:")
    if filename:
        client_socket.send(f"REQUEST_VERSIONS::{filename}".encode())

def request_version(filename, version): # Request a specific version of a file
    client_socket.send(f"REQUEST_FILE::{filename}::{version}".encode())

def show_version_selection(filename, versions):   # Display a list of versions to choose from
    if not versions or versions == [""]:
        messagebox.showinfo("No Versions", f"No versions available for {filename}")
        return
    version_window = tk.Toplevel(root)
    version_window.title(f"Versions of {filename}")

    listbox = tk.Listbox(version_window)
    for versioned_filename in versions:
        version_label = versioned_filename.split("_v")[-1]
        listbox.insert(tk.END, f"Version {version_label}")
    listbox.pack(pady=10)

    def restore_version():
        index = listbox.curselection()
        if index:
            version_number = index[0] + 1     
            request_version(filename, str(version_number))
            version_window.destroy()

    restore_button = tk.Button(version_window, text="Restore", command=restore_version)
    restore_button.pack(pady=5)

def open_file(filename, content):
    if filename in open_file_windows:
        return  # Prevent opening multiple windows for the same file   
    editor_window = tk.Toplevel(root)
    editor_window.title(filename)
    editor_window.geometry("500x600")
    
    text_area = tk.Text(editor_window, wrap=tk.WORD)
    text_area.insert(tk.END, content)
    text_area.pack(expand=True, fill=tk.BOTH)
    
    def save_changes():
        updated_content = text_area.get("1.0", tk.END).strip()
        file_path = os.path.join(SAVE_DIRECTORY, filename)
        with open(file_path, "w") as file:
            file.write(updated_content)  # Save updated file locally
        client_socket.send(f"FILE_UPLOAD::{filename}::{updated_content}".encode())
        display_message(f"Updated & Saved: {filename}")
        on_close()  # Close window after saving
    
    save_button = tk.Button(editor_window, text="Save & Upload", command=save_changes)
    save_button.pack()
    
    open_file_windows[filename] = editor_window  # Track the opened window
    
    def on_close():
        if filename in open_file_windows:
            del open_file_windows[filename]  # Remove from tracking when closed
        editor_window.destroy()
    
    editor_window.protocol("WM_DELETE_WINDOW", on_close)

def send_private_message(): # Send a private message to a specific client
    recipient = simpledialog.askstring("Private Message", "Enter recipient's name:")
    if recipient:
        message = simpledialog.askstring("Message", f"Message to {recipient}:")
        if message:
            client_socket.send(f"/msg {recipient} {message}".encode())
            display_message(f"[Private to {recipient}]: {message}")

def connect_to_server():
    global client_socket
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_IP, PORT))
        client_socket.send(client_name.encode())
        threading.Thread(target=receive_messages, daemon=True).start()
    except:
        print("Could not connect to server")
        root.quit()

# GUI Setup
root = tk.Tk()
root.withdraw()

client_name = simpledialog.askstring("Name", "Enter your name:", parent=root)
if not client_name:
    exit()

root.deiconify()
root.title(f"Chat - {client_name}")
root.geometry("500x600")

chat_box = scrolledtext.ScrolledText(root, state=tk.DISABLED, height=20)
chat_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

message_entry = tk.Entry(root, width=50)
message_entry.pack(pady=5, padx=10, fill=tk.X)
message_entry.bind("<Return>", lambda event: send_message())

send_button = tk.Button(root, text="Send", command=send_message)
send_button.pack(pady=5)

upload_button = tk.Button(root, text="Upload File", command=upload_file)
upload_button.pack(pady=5)

request_button = tk.Button(root, text="Request File Versions", command=request_file)
request_button.pack(pady=5)

private_message_button = tk.Button(root, text="Private Message", command=send_private_message)
private_message_button.pack(pady=5)

threading.Thread(target=connect_to_server, daemon=True).start()
root.mainloop()
