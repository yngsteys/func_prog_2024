import os
os.environ["TCL_THREADS"] = "1"

import asyncio
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from threading import Thread


class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Client")
        self.running = False

        # GUI элементы
        self.chat_window = ScrolledText(self.root, state='disabled', wrap='word', height=20, width=50)
        self.chat_window.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

        self.entry_field = tk.Entry(self.root, width=40)
        self.entry_field.grid(row=1, column=0, padx=10, pady=10)

        self.send_button = tk.Button(self.root, text="Send", command=self.send_message)
        self.send_button.grid(row=1, column=1, padx=10, pady=10)

        self.exit_button = tk.Button(self.root, text="Exit", command=self.stop_client)
        self.exit_button.grid(row=2, column=0, columnspan=2, pady=10)

        # Asyncio loop для обработки событий
        self.loop = asyncio.new_event_loop()
        self.reader = None
        self.writer = None


        # Подключение к серверу (в отдельном потоке чтобы не блокировать GUI)
        Thread(target=self.start_client, daemon=True).start()


        # Закрытие приложения
        self.root.protocol("WM_DELETE_WINDOW", self.stop_client)


    def start_client(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect_to_server())

    async def connect_to_server(self):
        try:
            self.reader, self.writer = await asyncio.open_connection('127.0.0.1', 8888)
            self.running = True
            self.chat_window.config(state='normal')
            self.chat_window.insert(tk.END, "Connected to the server.\n")
            self.chat_window.config(state='disabled')

            # Присоединение к комнате
            self.writer.write("/join default_room\n".encode())
            await self.writer.drain()

            asyncio.create_task(self.receive_messages())  # Запуск получения сообщений

        except ConnectionRefusedError:
            self.chat_window.config(state='normal')
            self.chat_window.insert(tk.END, "Failed to connect to the server.\n")
            self.chat_window.config(state='disabled')

    async def receive_messages(self):
        while self.running:
            try:
                data = await self.reader.readline()
                if not data:
                    break
                message = data.decode().strip()

                self.chat_window.config(state='normal') # Включить редактирование
                self.chat_window.insert(tk.END, f"{message}\n") # Добавить сообщение
                self.chat_window.config(state='disabled') # Отключить редактирование
                self.chat_window.yview(tk.END)  # Прокрутить вниз

                self.chat_window.update_idletasks()  

            except Exception as e:
                print(f"Error receiving message: {e}")
                break

        self.stop_client()


    def send_message(self):
        message = self.entry_field.get()
        if message and self.writer:
            self.entry_field.delete(0, tk.END)
            self.root.after(0, self.send_message_async, message)

    def send_message_async(self, message):
        asyncio.run_coroutine_threadsafe(self._send_message(message), self.loop)


    async def _send_message(self, message):
        try:
            self.writer.write(f"{message}\n".encode())
            await self.writer.drain()

            if message.strip() == "/quit":
                await self._stop_writer()


        except Exception as e:
            print(f"Error sending message: {e}")


    def stop_client(self):
        if self.running:
            self.running = False
            if self.writer:
                self.loop.call_soon_threadsafe(asyncio.create_task, self._stop_writer())

        self.loop.stop()
        self.root.destroy()

    async def _stop_writer(self):
        try:
            self.writer.write("/quit\n".encode())
            await self.writer.drain()

            self.writer.close()
            await self.writer.wait_closed()

        except Exception as e:
            print(f"Error closing connection: {e}")




async def main():
    root = tk.Tk()
    app = ChatClient(root)
    try:
        root.mainloop()
    finally:
        if app.running:
            app.stop_client()


if __name__ == "__main__":
    asyncio.run(main())