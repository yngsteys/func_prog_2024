import asyncio
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading


class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.username = None
        self.connected = False

    async def connect(self, username, room):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.username = username
            self.writer.write(f"/join {room} {username}\n".encode())
            await self.writer.drain()
            self.connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")

    async def send_message(self, message):
        if self.connected:
            self.writer.write(message.encode())
            await self.writer.drain()

    async def receive_messages(self, callback):
        try:
            while self.connected:
                data = await self.reader.readline()
                if data:
                    callback(data.decode().strip())
                else:
                    break
        except Exception as e:
            callback(f"[ERROR] {e}")
            self.connected = False

    async def disconnect(self):
        if self.connected:
            try:
                self.writer.write("/quit\n".encode())
                await self.writer.drain()
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
        self.connected = False


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Application")
        self.client = ChatClient("127.0.0.1", 5004)

        self.setup_ui()

    def setup_ui(self):
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(self.top_frame, text="Username:").grid(row=0, column=0, padx=5, sticky="w")
        self.username_entry = tk.Entry(self.top_frame)
        self.username_entry.grid(row=0, column=1, padx=5, sticky="ew")

        tk.Label(self.top_frame, text="Room:").grid(row=1, column=0, padx=5, sticky="w")
        self.room_entry = tk.Entry(self.top_frame)
        self.room_entry.grid(row=1, column=1, padx=5, sticky="ew")

        self.connect_button = tk.Button(self.top_frame, text="Connect", command=self.on_connect)
        self.connect_button.grid(row=2, column=0, columnspan=2, pady=5)

        self.disconnect_button = tk.Button(self.top_frame, text="Disconnect", command=self.on_disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=3, column=0, columnspan=2, pady=5)

        self.messages = scrolledtext.ScrolledText(self.root, state="disabled", wrap="word")
        self.messages.pack(padx=10, pady=10, fill="both", expand=True)

        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(pady=10, padx=10, fill="x")

        self.message_entry = tk.Entry(self.bottom_frame)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.send_button = tk.Button(self.bottom_frame, text="Send", command=self.on_send_message)
        self.send_button.pack(side="left", padx=5)

    def add_message(self, message):
        self.messages.configure(state="normal")
        self.messages.insert(tk.END, message + "\n")
        self.messages.configure(state="disabled")
        self.messages.see(tk.END)

    def on_connect(self):
        username = self.username_entry.get().strip()
        room = self.room_entry.get().strip()

        if not username or not room:
            messagebox.showerror("Error", "Username and room are required!")
            return

        async def connect():
            try:
                await self.client.connect(username, room)
                self.add_message("[INFO] Connected!")
                self.disconnect_button.config(state=tk.NORMAL)
                self.connect_button.config(state=tk.DISABLED)
                asyncio.create_task(self.run_receive_loop())
            except ConnectionError as e:
                messagebox.showerror("Connection Error", str(e))

        def start_async_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)  # Устанавливаем новый цикл событий
            loop.run_until_complete(connect())

        threading.Thread(target=start_async_task, daemon=True).start()

    async def run_receive_loop(self):
        await self.client.receive_messages(self.add_message)

    def on_disconnect(self):
        async def disconnect():
            await self.client.disconnect()
            self.add_message("[INFO] Disconnected!")
            self.disconnect_button.config(state=tk.DISABLED)
            self.connect_button.config(state=tk.NORMAL)

        asyncio.run_coroutine_threadsafe(disconnect(), asyncio.get_event_loop())

    def on_send_message(self):
        message = self.message_entry.get().strip()
        if message:
            async def send():
                try:
                    await self.client.send_message(message + "\n")
                    self.message_entry.delete(0, tk.END)
                except ConnectionError:
                    messagebox.showerror("Error", "Failed to send message.")

            asyncio.run_coroutine_threadsafe(send(), asyncio.get_event_loop())


def start_asyncio_loop():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_forever()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)

    # Запуск asyncio в отдельном потоке
    threading.Thread(target=start_asyncio_loop, daemon=True).start()

    root.mainloop()
