import asyncio

class ChatServer:
    def __init__(self):
        self.rooms = {}  # Комнаты: {'room_name': set(client_writer)}
        self.lock = asyncio.Lock()  # Для синхронизации доступа

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"Client connected: {addr}")
        
        writer.write("Welcome to the chat server!\n".encode())
        writer.write("Enter '/join room_name' to join a room.\n".encode())
        writer.write("Enter '/quit' to exit.\n".encode())
        await writer.drain()

        room = None  # Текущая комната клиента
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                message = data.decode().strip()
                print(f"Received from {addr}: {message}")  # Лог для отладки

                if message.startswith("/join"):
                    room = await self.join_room(writer, room, message)
                elif message.startswith("/quit"):
                    break
                else:
                    await self.send_message(room, writer, message)
        except (asyncio.CancelledError, Exception) as e:
            print(f"Error with client {addr}: {e}")
        finally:
            await self.leave_room(writer, room)
            writer.close()
            await writer.wait_closed()
            print(f"Client disconnected: {addr}")

    async def join_room(self, writer, current_room, command):
        """Переключение клиента в указанную комнату"""
        _, room_name = command.split(maxsplit=1)
        async with self.lock:
            # Удалить клиента из текущей комнаты
            if current_room:
                self.rooms[current_room].remove(writer)
                if not self.rooms[current_room]:
                    del self.rooms[current_room]

            # Добавить клиента в новую комнату
            if room_name not in self.rooms:
                self.rooms[room_name] = set()
            self.rooms[room_name].add(writer)

        writer.write(f"Joined room: {room_name}\n".encode())
        await writer.drain()
        return room_name

    async def leave_room(self, writer, room):
        """Удаление клиента из комнаты"""
        if room:
            async with self.lock:
                self.rooms[room].remove(writer)
                if not self.rooms[room]:
                    del self.rooms[room]

    async def send_message(self, room, sender_writer, message):
        """Рассылка сообщения в комнате"""
        if not room:
            sender_writer.write("You are not in a room. Use /join to enter one.\n".encode())
            await sender_writer.drain()
            return

        async with self.lock:
            for writer in self.rooms.get(room, []):
                try:
                    writer.write(f"{message}\n".encode())
                    await writer.drain()
                except Exception as e:
                    print(f"Error sending message to {writer}: {e}")

    async def run_server(self, host='127.0.0.1', port=8888):
        server = await asyncio.start_server(self.handle_client, host, port)
        addr = server.sockets[0].getsockname()
        print(f"Server running on {addr}")
        async with server:
            await server.serve_forever()


if __name__ == "__main__":
    server = ChatServer()
    try:
        asyncio.run(server.run_server())
    except KeyboardInterrupt:
        print("Server shut down.")