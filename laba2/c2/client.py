import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import logging
from datetime import datetime

# Настройка логирования на клиенте
logging.basicConfig(
    filename="client_log.txt",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.connected = False

    def connect(self, username, room):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.username = username
            self.socket.send(f"/join {room} {username}\n".encode())  # Отправляем команду /join
            self.connected = True
            logging.info(f"Connected to server as '{username}' in room '{room}'.")
            return True
        except Exception as e:
            logging.error(f"Connection error: {str(e)}")
            return str(e)

    def send_message(self, message):
        if self.connected:
            try:
                self.socket.send(message.encode())
                logging.info(f"Message sent: {message.strip()}")
            except:
                self.connected = False
                logging.error("Failed to send message. Connection lost.")
                messagebox.showerror("Error", "Connection lost.")

    def receive_messages(self, callback, update_rooms_callback):
        def listen():
            while self.connected:
                try:
                    data = self.socket.recv(4096).decode()
                    if data.startswith("/rooms"):
                        rooms_data = data.replace("/rooms ", "").strip()
                        update_rooms_callback(rooms_data)
                        logging.info(f"Updated room list received: {rooms_data}")
                    else:
                        callback(data)
                        logging.info(f"Message received: {data.strip()}")
                except:
                    self.connected = False
                    callback("[INFO] Connection lost.")
                    logging.warning("Connection lost while listening.")
                    break

        threading.Thread(target=listen, daemon=True).start()

    def disconnect(self):
        if self.connected:
            try:
                self.socket.send("/quit\n".encode())
                self.socket.close()
                logging.info("Disconnected from server.")
            except:
                logging.error("Error while disconnecting.")
        self.connected = False


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Application")
        self.root.configure(bg="#333333")

        self.client = None

        # Фрейм для подключения
        self.top_frame = tk.Frame(self.root, bg="#333333")
        self.top_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(self.top_frame, text="Username:", bg="#333333", fg="white").grid(row=0, column=0, padx=5, sticky="w")
        self.username_entry = tk.Entry(self.top_frame, bg="#444444", fg="white")
        self.username_entry.grid(row=0, column=1, padx=5, sticky="ew")

        tk.Label(self.top_frame, text="Room:", bg="#333333", fg="white").grid(row=1, column=0, padx=5, sticky="w")
        self.room_entry = tk.Entry(self.top_frame, bg="#444444", fg="white")
        self.room_entry.grid(row=1, column=1, padx=5, sticky="ew")

        self.connect_button = tk.Button(self.top_frame, text="Connect", command=self.connect, bg="#111111", fg="black")
        self.connect_button.grid(row=2, column=0, columnspan=2, pady=5)

        self.disconnect_button = tk.Button(self.top_frame, text="Disconnect", command=self.disconnect, bg="#111111", fg="black", state=tk.DISABLED)
        self.disconnect_button.grid(row=3, column=0, columnspan=2, pady=5)

        # Поле для отображения сообщений
        self.messages = scrolledtext.ScrolledText(self.root, state="disabled", wrap="word", bg="#444444", fg="white")
        self.messages.pack(padx=10, pady=10, fill="both", expand=True)

        # Фрейм для отправки сообщений
        self.bottom_frame = tk.Frame(self.root, bg="#333333")
        self.bottom_frame.pack(pady=10, padx=10, fill="x")

        self.message_entry = tk.Entry(self.bottom_frame, bg="#444444", fg="white")
        self.message_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.private_entry = tk.Entry(self.bottom_frame, width=15, bg="#444444", fg="white")
        self.private_entry.pack(side="left", padx=5)
        tk.Label(self.bottom_frame, text="Private to:", bg="#333333", fg="white").pack(side="left")

        self.send_button = tk.Button(self.bottom_frame, text="Send", command=self.send_message, bg="#111111", fg="black")
        self.send_button.pack(side="left", padx=5)

        # Поле для отображения активных комнат
        tk.Label(self.root, text="Active Rooms:", bg="#333333", fg="white").pack()
        self.rooms_list = tk.Listbox(self.root, bg="#444444", fg="white", height=5)
        self.rooms_list.pack(padx=10, pady=5, fill="x")

    def connect(self):
        username = self.username_entry.get().strip()
        room = self.room_entry.get().strip()

        if not username or not room:
            messagebox.showerror("Error", "Username and room are required!")
            return

        self.client = ChatClient("127.0.0.1", 5003)
        result = self.client.connect(username, room)

        if result is True:
            self.add_message("[INFO] Connected!")
            self.client.receive_messages(self.add_message, self.update_rooms)
            self.disconnect_button.config(state=tk.NORMAL)
            self.connect_button.config(state=tk.DISABLED)
        else:
            messagebox.showerror("Error", result)

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            self.add_message("[INFO] Disconnected!")
            self.disconnect_button.config(state=tk.DISABLED)
            self.connect_button.config(state=tk.NORMAL)

    def send_message(self):
        message = self.message_entry.get().strip()
        recipient = self.private_entry.get().strip()

        if message:
            if recipient:
                self.client.send_message(f"/private {recipient} {message}\n")
            else:
                self.client.send_message(message + "\n")
            self.message_entry.delete(0, tk.END)
            self.private_entry.delete(0, tk.END)

    def add_message(self, message):
        self.messages.configure(state="normal")
        self.messages.insert(tk.END, f"{message}\n")
        self.messages.configure(state="disabled")
        self.messages.see(tk.END)

    def update_rooms(self, rooms_data):
        self.rooms_list.delete(0, tk.END)
        rooms = rooms_data.split(",")
        for room_info in rooms:
            self.rooms_list.insert(tk.END, room_info)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()