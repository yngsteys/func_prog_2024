import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image
import multiprocessing as mp
import os
import tkinter as tk
from tkinter import messagebox, filedialog

# Глобальные переменные
file_paths = []  # Список для хранения путей к выбранным изображениям.

# Функция для анализа части изображения, выделения объектов и сохранения результатов
def analysing(image, number, queue, output_directory):
    image_with_objects = image.copy()
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    image = cv2.filter2D(image, -1, kernel)

    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
    _, binary_image = cv2.threshold(blurred_image, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    space_objects = []

    # Заменяем путь к шрифту на подходящий для macOS
    font_path = "/Library/Fonts/Arial.ttf"  # Путь к шрифту Arial в macOS
    font = ImageFont.truetype(font_path, 14)

    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, width, height = cv2.boundingRect(contour)
        center_x = x + width / 2
        center_y = y + height / 2
        brightness = np.sum(gray_image[y:y + height, x:x + width])
        object_type = classified(area, brightness)
        space_object = {
            "x": center_x,
            "y": center_y,
            "brightness": brightness,
            "type": object_type,
            "size": width * height
        }
        space_objects.append(space_object)
        cv2.rectangle(image_with_objects, (x, y), (x + width, y + height), (0, 255, 0), 2)

        # Использование PIL для добавления текста
        pil_image = Image.fromarray(image_with_objects)
        draw = ImageDraw.Draw(pil_image)
        draw.text((x, y - 10), object_type, font=font, fill=(0, 0, 0))
        image_with_objects = np.array(pil_image)

    os.makedirs(output_directory, exist_ok=True)
    output2_directory = os.path.join(output_directory, "image_crop")
    os.makedirs(output2_directory, exist_ok=True)
    cv2.imwrite(os.path.join(output2_directory, f"{number}.tif"), image_with_objects)

    with open(os.path.join(output_directory, f"{number}.txt"), "w", encoding="utf-8") as file:
        for obj in space_objects:
            file.write(f"Координаты: ({obj['x']}, {obj['y']}); Яркость: {obj['brightness']}; Размер: {obj['size']}; Тип: {obj['type']}\n")
    print(f"Выполнен процесс №{number}")
    queue.put((image_with_objects, number - 1))

# Классифицирует объекты на основе площади и яркости
def classified(area, brightness):
    return {
        area < 10 and brightness > 100: "звезда",
        area < 10 and brightness > 50: "планета",
        area < 10 and brightness > 0: "звезда",
        area > 10000 and brightness > 1000000: "галактика",
        area < 10000 and brightness > 1000000: "квазар",
        area >= 10 and brightness > 0: "звезда"
    }[True]

# Разделяет изображение на части для параллельной обработки
def split_image(image, num_parts):
    height, width, _ = image.shape
    part_width = (width // num_parts) + 1
    part_height = (height // num_parts) + 1
    parts = []
    for chunk_width in range(num_parts):
        for chunk_height in range(num_parts):
            part = image[chunk_height * part_height:min((chunk_height + 1) * part_height, len(image))]
            part = part[:, chunk_width * part_width:(chunk_width + 1) * part_width, :]
            parts.append(part)
    return parts

# Обрабатывает изображения параллельно
def parallel_processing(image_paths):
    for full_path_to_image in image_paths:
        output_directory = os.path.join("image_result", os.path.splitext(os.path.basename(full_path_to_image))[0])
        queue = mp.Manager().Queue()  # Используем Manager для очереди
        image = cv2.imread(full_path_to_image)
        num_parts = 4
        mp_parts = split_image(image, num_parts)

        processes = []
        number = 0

        for mp_part in mp_parts:
            number += 1
            process = mp.Process(target=analysing, args=(mp_part, number, queue, output_directory))
            process.start()
            processes.append(process)

        sum_finish = 0
        image_parts = [0] * len(mp_parts)

        while sum_finish != len(processes):
            if not queue.empty():
                sum_finish += 1
                image_part = queue.get()
                image_parts[image_part[1]] = image_part[0].copy()

        image_vstack = [image_parts[i] for i in range(0, num_parts ** 2, num_parts)]

        k = 0
        for i in range(num_parts):
            for j in range(1, num_parts):
                image_vstack[i] = np.vstack([image_vstack[i], image_parts[j + k]])
            k += num_parts

        image_with_objects = np.hstack(image_vstack)
        cv2.imwrite(os.path.join(output_directory, "new_image.tif"), image_with_objects)
        messagebox.showinfo("Готово", "Результат сохранен")

# Открывает диалоговое окно для выбора изображений
def select_images():
    global file_paths
    try:
        file_paths = filedialog.askopenfilenames(filetypes=[("TIFF files", "*.tif"), ("JPEG files", "*.jpg"), ("PNG files", "*.png")])
        if file_paths:
            messagebox.showinfo("Готово", "Изображения успешно загружены")
        else:
            messagebox.showwarning("Внимание", "Изображения не были выбраны.")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить изображения: {e}")

# Создание интерфейса
def create_ui():
    root = tk.Tk()
    root.title("Обработка изображений")
    root.geometry("500x400")

    lbl_title = tk.Label(root, text="Обработка космических изображений", font=("Arial", 16))
    lbl_title.pack(pady=10)

    lbl_instructions = tk.Label(root, text="1. Выберите изображения.\n2. Нажмите 'Начать'.\n3. Дождитесь результата.", font=("Arial", 12))
    lbl_instructions.pack(pady=10)

    btn_select = tk.Button(root, text="Выбрать изображения", width=25, command=select_images)
    btn_select.pack(pady=10)

    btn_process = tk.Button(root, text="Начать обработку", width=25, command=lambda: parallel_processing(file_paths))
    btn_process.pack(pady=10)

    root.mainloop()

if __name__ == '__main__':
    create_ui()