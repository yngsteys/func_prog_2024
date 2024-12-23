import asyncio

class ChatServer:
    def __init__(self):
        # Храним клиентов в формате: {адрес: (номер_комнаты, writer, имя)}
        self.clients = dict()  # Все подключенные клиенты
        # Храним информацию о комнатах
        self.rooms = dict()  # {room_number: [client1, client2, ...]}

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        addr_str = f"{addr[0]}:{addr[1]}"
        print(f"Client {addr_str} connected", flush=True)

        name = None
        room_number = None

        try:
            # Регистрация клиента
            await writer.drain()
            name = (await reader.readline()).decode().strip()
            if not name:
                raise ValueError("Name cannot be empty.")

            await writer.drain()
            room_number = (await reader.readline()).decode().strip()
            if not room_number.isdigit():
                raise ValueError("Room number must be a valid integer.")
            room_number = int(room_number)

            print(f"Client {addr_str} joined room {room_number}! His name is {name}", flush=True)
        except Exception as e:
            print(f"Error during registration: {e}", flush=True)
            writer.write("Error during registration. Please try again.\n".encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return

        try:
            # Добавляем клиента в списки
            self.clients[addr_str] = (room_number, writer, name)
            if room_number not in self.rooms:
                self.rooms[room_number] = []
            self.rooms[room_number].append(name)
            await self.broadcast(f"{name} has joined the room!", room_number)

            # Основной цикл обработки сообщений
            while True:
                data = await reader.readline()
                message = data.decode().strip()

                if not message:  # Клиент разорвал соединение
                    break

                if message.lower() == "/quit":
                    await self.broadcast(f"{name} has left the room.", room_number)
                    break

                elif message.lower() == "/help":
                    await self.send_help(writer)
                elif message.lower() == "/listrooms":
                    await self.list_rooms(writer)
                else:
                    message = self.replace_emojis(message)
                    await self.broadcast(f"{name}: {message}", room_number)
        except Exception as e:
            print(f"Error handling messages for {addr_str}: {e}", flush=True)
        finally:
            # Отключение клиента
            print(f"Client {addr_str} disconnected", flush=True)
            if addr_str in self.clients:
                del self.clients[addr_str]
            if room_number in self.rooms and name in self.rooms[room_number]:
                self.rooms[room_number].remove(name)
                if not self.rooms[room_number]:  # Удаляем комнату, если она пустая
                    del self.rooms[room_number]
            writer.close()
            await writer.wait_closed()

    async def send_help(self, writer):
        """Отправка инструкции пользователю."""
        help_text = (
            "Welcome to the chat server! Here are some commands you can use:\n"
            "/help - Show this help message\n"
            "/listrooms - List all rooms and the users inside\n"
            "/quit - Exit the chat\n"
        )
        writer.write(help_text.encode())
        await writer.drain()

    async def list_rooms(self, writer):
        """Отправка списка всех комнат и пользователей в них."""
        message = "List of rooms:\n"
        for room_number, users in self.rooms.items():
            message += f"Room {room_number}: {', '.join(users)}\n"
        
        if not message.strip():
            message = "No rooms available.\n"
        
        writer.write(message.encode())
        await writer.drain()

    async def broadcast(self, message, room_number):
        """Отправка сообщения всем клиентам в указанной комнате."""
        print(f"Broadcasting message in room {room_number}: {message}", flush=True)
        for addr, (client_room, client_writer, client_name) in self.clients.items():
            if client_room == room_number:
                try:
                    print(f"Sending to {client_name} in room {room_number}", flush=True)
                    client_writer.write((message + "\n").encode())
                    await client_writer.drain()
                except Exception as e:
                    print(f"Error broadcasting to {addr}: {e}", flush=True)



    async def main(self):
        server = await asyncio.start_server(self.handle_client, '0.0.0.0', 8080)
        print('Server started and listening on 0.0.0.0:8080', flush=True)
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    print('Server starting...', flush=True)
    chat_server = ChatServer()
    asyncio.run(chat_server.main())
