import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image
import multiprocessing as mp
import os
from tkinter import Tk, messagebox, filedialog, Text, Button, Label, ttk, END

# Функция классификации объекта на основе площади и яркости
def classify_object(area, brightness):
    if area < 10 and brightness > 100:
        return "звезда"
    elif area < 10 and brightness > 50:
        return "комета"
    elif area < 10 and brightness > 0:
        return "планета"
    elif area > 10000 and brightness > 1000000:
        return "галактика"
    elif area < 10000 and brightness > 1000000:
        return "квазар"
    else:
        return "звезда"

# Функция анализа одного фрагмента изображения
def analyse_fragment(image, number, output_directory, font_path):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
    _, binary_image = cv2.threshold(blurred_image, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    space_objects = []

    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, width, height = cv2.boundingRect(contour)
        brightness = np.sum(gray_image[y:y + height, x:x + width])
        object_type = classify_object(area, brightness)

        space_objects.append({
            "x": x + width / 2,
            "y": y + height / 2,
            "brightness": brightness,
            "type": object_type,
            "size": width * height
        })

    # Сохранение результатов анализа фрагмента
    output_image_path = os.path.join(output_directory, f"{number}_fragment.png")
    cv2.imwrite(output_image_path, image)

    return space_objects

# Основная функция параллельной обработки изображений
def process_image(file_path, output_directory, num_processes, log_area, progress_bar):
    image = cv2.imread(file_path)
    height, width, _ = image.shape
    font_path = "/Library/Fonts/Arial.ttf"  # Путь к шрифту Arial в macOS

    # Определение размеров фрагментов
    fragment_height = height // num_processes
    fragment_width = width // num_processes
    fragments = []

    # Разделение изображения на фрагменты
    for i in range(num_processes):
        for j in range(num_processes):
            y_start = i * fragment_height
            x_start = j * fragment_width
            fragment = image[y_start:y_start + fragment_height, x_start:x_start + fragment_width]
            fragments.append((fragment, i * num_processes + j))

    # Параллельная обработка фрагментов
    with mp.Pool(num_processes) as pool:
        results = pool.starmap(analyse_fragment, [(frag[0], frag[1], output_directory, font_path) for frag in fragments])

    # Сбор и запись статистики
    with open(os.path.join(output_directory, "summary.txt"), "w", encoding="utf-8") as file:
        for i, objects in enumerate(results):
            file.write(f"Фрагмент {i}:\n")
            for obj in objects:
                file.write(f"  Координаты: ({obj['x']:.2f}, {obj['y']:.2f}), Яркость: {obj['brightness']}, "
                           f"Размер: {obj['size']}, Тип: {obj['type']}\n")
    log_area.insert(END, f"Обработка {file_path} завершена.\n")
    progress_bar.step(100 / len(fragments))

# Функция для выбора и обработки изображений
def select_and_process_images(log_area, progress_bar):
    try:
        Tk().withdraw()  # Скрытие главного окна Tkinter
        file_paths = filedialog.askopenfilenames(filetypes=[("TIFF files", "*.tif"), ("JPEG files", "*.jpg"), ("PNG files", "*.png")])
        
        if not file_paths:
            messagebox.showwarning("Внимание", "Изображения не были выбраны.")
            return

        output_directory = "image_result"
        os.makedirs(output_directory, exist_ok=True)

        progress_bar['value'] = 0
        log_area.delete('1.0', END)
        log_area.insert(END, "Начало обработки изображений...\n")

        for file_path in file_paths:
            process_image(file_path, output_directory, num_processes=4, log_area=log_area, progress_bar=progress_bar)
        
        messagebox.showinfo("Готово", "Анализ завершен. Результаты сохранены в папке 'image_result'.")
        log_area.insert(END, "Анализ завершен.\n")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Произошла ошибка при обработке изображений: {e}")

# Основной интерфейс программы
def create_gui():
    root = Tk()
    root.title("Анализ космических изображений")
    root.geometry("600x400")
    root.configure(bg="#2D2D2D")

    title_label = Label(root, text="Анализ космических изображений", font=("Arial", 16, "bold"), bg="#2D2D2D", fg="white")
    title_label.pack(pady=10)

    instruction_label = Label(root, text="Выберите изображения и начните анализ", font=("Arial", 12), bg="#2D2D2D", fg="white")
    instruction_label.pack()

    # Кнопка для загрузки изображений
    select_button = Button(root, text="Загрузить изображения", width=25, font=("Arial", 10), bg="#4CAF50", fg="black", command=lambda: select_and_process_images(log_area, progress_bar))
    select_button.pack(pady=10)

    # Прогресс-бар для отображения процесса обработки
    progress_bar = ttk.Progressbar(root, length=400, mode='determinate')
    progress_bar.pack(pady=10)

    # Журнал логов
    log_label = Label(root, text="Логи обработки:", font=("Arial", 12), bg="#2D2D2D", fg="white")
    log_label.pack()

    log_area = Text(root, wrap='word', width=70, height=10, bg="#333333", fg="white", font=("Arial", 10))
    log_area.pack(pady=5)

    root.mainloop()

if __name__ == '__main__':
    create_gui()