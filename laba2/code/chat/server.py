import asyncio
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

clients = {}

async def handle_client_messages(reader, writer, client_address, connections_widget, messages_widget):
    while True:
        data = await reader.read(100)
        if not data:
            break
        message = data.decode()
        display_message = f"Получено сообщение от {client_address} {clients[writer]}: {message}\n"
        messages_widget.insert(tk.END, display_message)
        messages_widget.see(tk.END)
        message = f" {clients[writer]} - " + message
        for client in clients:
            client.write(message.encode())
            await client.drain()
            print("Сообщение отправлено")

async def handle_new_client(reader, writer, connections_widget, messages_widget):
    client_address = writer.get_extra_info('peername')
    print(f"Новое подключение: {client_address}")
    
    message = "Добро пожаловать! Пожалуйста, введите свое имя: "
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(100)
    message = data.decode()

    clients[writer] = message
    connections_widget.insert(tk.END, f"{client_address} - {message}\n")
    
    message = f"Ваше имя: {message}"
    writer.write(message.encode())
    await writer.drain()

    try:
        await handle_client_messages(reader, writer, client_address, connections_widget, messages_widget)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if writer in clients.keys():
            clients.pop(writer)
            connections_widget.delete(1.0, tk.END)
            connections_widget.insert(tk.END, "\n".join([str(client.get_extra_info('peername')) + f" - {clients[client]}" for client in clients]))
        writer.close()
        await writer.wait_closed()
        print(f"Соединение с {client_address} разорвано")

async def start_server(connections_widget, messages_widget):
    server = await asyncio.start_server(lambda r, w: handle_new_client(r, w, connections_widget, messages_widget), '127.0.0.1', 8888)
    async with server:
        print("Сервер запущен и слушает на 127.0.0.1:8888")
        await server.serve_forever()

def run_server_loop(connections_widget, messages_widget):
    asyncio.run(start_server(connections_widget, messages_widget))

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("800x600")
    root.title("Server")
    root.configure(bg="#f0f0f0")

    style = ttk.Style()
    style.configure("TFrame", background="#f0f0f0")
    style.configure("TLabel", background="#f0f0f0", font=("Arial", 12))
    style.configure("TButton", font=("Arial", 12))

    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    connections_frame = ttk.LabelFrame(main_frame, text="Подключения", padding="10")
    connections_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    connections_output = scrolledtext.ScrolledText(connections_frame, wrap=tk.WORD, width=30, height=20, font=("Arial", 12))
    connections_output.pack(fill=tk.BOTH, expand=True)

    messages_frame = ttk.LabelFrame(main_frame, text="Сообщения", padding="10")
    messages_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    messages_output = scrolledtext.ScrolledText(messages_frame, wrap=tk.WORD, width=50, height=20, font=("Arial", 12))
    messages_output.pack(fill=tk.BOTH, expand=True)

    asyncio_thread = threading.Thread(target=run_server_loop, args=(connections_output, messages_output))
    asyncio_thread.start()

    root.mainloop()