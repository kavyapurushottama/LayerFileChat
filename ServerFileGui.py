# Server side of the chat application with file sharing and private messaging.

import socket
import threading
import os

#  Server Configuration
SERVER_IP = "127.0.0.1" # Change to your server's IP address "192.168..." for local network
PORT = 2011 # Port number for the server, can change if needed

clients = {}  # Dictionary to store client sockets with names
file_versions = {}  # Dictionary to store file versions

SAVE_DIRECTORY = "server_files"
if not os.path.exists(SAVE_DIRECTORY):
    os.makedirs(SAVE_DIRECTORY)

def broadcast(message, sender_socket=None): #Send a message to all connected clients except the sender.
    for client_socket in list(clients.keys()):
        if client_socket != sender_socket:
            try:
                client_socket.send(message.encode())
            except:
                client_socket.close()
                if client_socket in clients:
                    del clients[client_socket] 

def save_file_with_version(filename, content):  #Save a file with a version number and return the versioned filename.
    if filename not in file_versions:
        file_versions[filename] = []

    version = len(file_versions[filename]) + 1
    versioned_filename = f"{filename}_v{version}"
    file_path = os.path.join(SAVE_DIRECTORY, versioned_filename)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

    file_versions[filename].append(versioned_filename)
    return versioned_filename, version

def send_private_message(sender_socket, sender_name, recipient_name, message): #Send a private message to a specific client.
    found = False
    for client_socket, client_name in clients.items():
        if client_name == recipient_name:
            try:
                client_socket.send(f"[Private] {sender_name}: {message}".encode())
                found = True
                return
            except:
                pass
    if not found:
        sender_socket.send(f"User {recipient_name} not found.".encode())

def handle_client(client_socket, client_address): #Handle a client connection.
    try:
        # Receive client's name
        client_name = client_socket.recv(1024).decode()
        clients[client_socket] = client_name
        print(f"{client_name} connected from {client_address}")
        # Notify other clients
        broadcast(f"{client_name} joined the chat.", client_socket)
        while True:
            data = client_socket.recv(4096).decode()
            if not data:
                break
            if data.startswith("FILE_UPLOAD::"):
                _, filename, content = data.split("::", 2)
                versioned_filename, version = save_file_with_version(filename, content)
                broadcast(f"{clients[client_socket]} uploaded {filename} (Version {version})", client_socket)
                broadcast(f"FILE_UPDATE::{filename}::Version {version}", client_socket)
                print(f"{filename} updated by {client_name} (Version {version})")

            elif data.startswith("REQUEST_VERSIONS::"):
                _, filename = data.split("::")
                if filename in file_versions:
                    versions = "::".join(file_versions[filename])
                    client_socket.send(f"VERSIONS::{filename}::{versions}".encode())
                else:
                    client_socket.send(f"VERSIONS::{filename}::No versions available".encode())
                    
            elif data.startswith("REQUEST_FILE::"):
                parts = data.split("::")
                if len(parts) == 3:
                    _, filename, version = parts
                    try:
                        version_index = int(version) - 1
                        if filename in file_versions and 0 <= version_index < len(file_versions[filename]):
                            file_path = os.path.join(SAVE_DIRECTORY, file_versions[filename][version_index])
                            with open(file_path, "r", encoding="utf-8") as file:
                                content = file.read()
                            client_socket.send(f"FILE_UPDATE::{filename}::{content}".encode())
                        else:
                            client_socket.send(f"ERROR::Version {version} not found.".encode())
                    except ValueError:
                        client_socket.send("ERROR::Invalid version number.".encode())

            elif data.startswith("/msg "):
                parts = data.split(" ", 2)
                if len(parts) >= 3:
                    recipient_name, message = parts[1], parts[2]
                    send_private_message(client_socket, client_name, recipient_name, message)

            else:
                broadcast(f"{client_name}: {data}", client_socket)
                print(f"{client_name}: {data}")
    except Exception as e:
        print(f"Error with {client_name}: {e}")

    finally:
        print(f"{client_name} disconnected.")
        broadcast(f"{client_name} left the chat.", None)
        client_socket.close()
        if client_socket in clients:
            del clients[client_socket] 

def start_server(): #Start the chat server.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(5)  # Accept up to 5 simultaneous connections
    print(f"Server started on {SERVER_IP}:{PORT}")
    while True:
        client_socket, client_address = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

if __name__ == "__main__":
    start_server()
