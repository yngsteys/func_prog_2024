import socket
import threading
import time

class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # {username: (socket, room)}
        self.rooms = {}    # {room: [username1, username2]}
        self.online_users = set()  # Отслеживаем онлайн пользователей для приватных сообщений

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server started on {self.host}:{self.port}")
        threading.Thread(target=self.broadcast_rooms, daemon=True).start()

        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()

    def broadcast_rooms(self):
        while True:
            time.sleep(3)  # Интервал обновления списка комнат
            rooms_list = "/rooms " + ",".join(f"{room} ({len(self.rooms.get(room, []))} users)" for room in self.rooms)
            for username, (client_socket, _) in self.clients.items():
                try:
                    client_socket.send(rooms_list.encode())
                except:
                    self.disconnect_client(username)

    def handle_client(self, client_socket, addr):
        username = None
        room = None

        try:
            while True:
                data = client_socket.recv(4096).decode().strip()
                if not data:
                    break

                if data.startswith("/join"):
                    parts = data.split()
                    room = parts[1]
                    username = parts[2] if len(parts) > 2 else f"{addr[0]}:{addr[1]}"
                    self.clients[username] = (client_socket, room)
                    self.online_users.add(username)

                    if room not in self.rooms:
                        self.rooms[room] = []
                    self.rooms[room].append(username)

                    self.send_to_room(room, f"[INFO] {username} has joined the room {room}")
                    self.send_current_rooms(client_socket)

                elif data.startswith("/quit"):
                    break

                elif data.startswith("/private"):
                    parts = data.split(" ", 2)
                    if len(parts) == 3:
                        recipient, message = parts[1], parts[2]
                        self.send_private_message(username, recipient, message)
                    else:
                        self.send_to_client(username, "[ERROR] Incorrect /private message format.")

                else:
                    self.send_to_room(room, f"{username}: {data}")

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            self.disconnect_client(username)

    def send_current_rooms(self, client_socket):
        rooms_list = "/rooms " + ",".join(f"{room} ({len(self.rooms[room])} users)" for room in self.rooms)
        try:
            client_socket.send(rooms_list.encode())
        except:
            pass

    def send_to_room(self, room, message):
        if room in self.rooms:
            for user in self.rooms[room]:
                if user in self.clients:
                    client_socket, _ = self.clients[user]
                    try:
                        client_socket.send(message.encode())
                    except:
                        self.disconnect_client(user)

    def send_private_message(self, sender, recipient, message):
        if recipient in self.online_users and recipient in self.clients:
            client_socket, _ = self.clients[recipient]
            try:
                client_socket.send(f"[PRIVATE] {sender}: {message}".encode())
            except:
                self.disconnect_client(recipient)
        else:
            self.send_to_client(sender, f"[ERROR] User '{recipient}' not found or offline.")

    def send_to_client(self, username, message):
        if username in self.clients:
            client_socket, _ = self.clients[username]
            try:
                client_socket.send(message.encode())
            except:
                self.disconnect_client(username)

    def disconnect_client(self, username):
        if username in self.clients:
            client_socket, room = self.clients[username]
            try:
                client_socket.close()
            except:
                pass
            del self.clients[username]
            self.online_users.discard(username)

            if room in self.rooms:
                self.rooms[room].remove(username)
                if not self.rooms[room]:
                    del self.rooms[room]

            self.send_to_room(room, f"[INFO] {username} has left the room")


if __name__ == "__main__":
    server = ChatServer("127.0.0.1", 5003)
    server.start()