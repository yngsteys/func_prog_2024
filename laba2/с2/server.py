import asyncio
from collections import defaultdict


class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = {}  # {username: (writer, room)}
        self.rooms = defaultdict(list)  # {room: [username1, username2]}
        self.online_users = set()  # Keeps track of online users for private messages

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"Server started on {self.host}:{self.port}")
        await self.broadcast_rooms()

        async with server:
            await server.serve_forever()

    async def broadcast_rooms(self):
        while True:
            await asyncio.sleep(3)
            rooms_list = "/rooms " + ",".join(self.rooms.keys())
            for username, (writer, _) in list(self.clients.items()):
                try:
                    writer.write(rooms_list.encode() + b'\n')
                    await writer.drain()
                except:
                    await self.disconnect_client(username)

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        username = None
        room = None

        try:
            while data := await reader.readline():
                data = data.decode().strip()
                if not data:
                    break

                if data.startswith("/join"):
                    parts = data.split()
                    room = parts[1]
                    username = parts[2] if len(parts) > 2 else f"{addr[0]}:{addr[1]}"  # Allow username specification
                    self.clients[username] = (writer, room)
                    self.online_users.add(username)
                    self.rooms[room].append(username)
                    await self.send_to_room(room, f"[INFO] {username} has joined the room {room}")

                elif data.startswith("/quit"):
                    break

                elif data.startswith("/private"):
                    parts = data.split(" ", 2)  # Split into command, recipient, message
                    if len(parts) == 3:
                        recipient, message = parts[1], parts[2]
                        await self.send_private_message(username, recipient, message)
                    else:
                        await self.send_to_client(username, "[ERROR] Incorrect /private message format.")

                else:
                    await self.send_to_room(room, f"{username}: {data}")

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            await self.disconnect_client(username)

    async def send_to_room(self, room, message):
        if room in self.rooms:
            for user in self.rooms[room]:
                if user in self.clients:
                    writer, _ = self.clients[user]
                    try:
                        writer.write(message.encode() + b'\n')
                        await writer.drain()
                    except:
                        await self.disconnect_client(user)

    async def send_private_message(self, sender, recipient, message):
        if recipient in self.online_users and recipient in self.clients:
            writer, _ = self.clients[recipient]
            try:
                writer.write(f"[PRIVATE] {sender}: {message}".encode() + b'\n')
                await writer.drain()
            except:
                await self.disconnect_client(recipient)
        else:
            await self.send_to_client(sender, f"[ERROR] User '{recipient}' not found or offline.")

    async def send_to_client(self, username, message):
        if username in self.clients:
            writer, _ = self.clients[username]
            try:
                writer.write(message.encode() + b'\n')
                await writer.drain()
            except:
                await self.disconnect_client(username)

    async def disconnect_client(self, username):
        if username in self.clients:
            writer, room = self.clients[username]
            writer.close()
            await writer.wait_closed()
            del self.clients[username]
            self.online_users.discard(username)

            if room in self.rooms:
                self.rooms[room].remove(username)
                if not self.rooms[room]:
                    del self.rooms[room]

            await self.send_to_room(room, f"[INFO] {username} has left the room")


if __name__ == "__main__":
    server = ChatServer("127.0.0.1", 5004)
    asyncio.run(server.start())
