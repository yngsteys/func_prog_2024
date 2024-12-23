import os
import tkinter as tk
from tkinter import filedialog, messagebox
from concurrent.futures import ProcessPoolExecutor
from PIL import Image
import numpy as np
from skimage import measure
from skimage.filters import threshold_otsu
import multiprocessing
from functools import partial
import cv2

# Константы
RESULTS_FOLDER = 'results'

def create_results_folder():
    """Создает папку для хранения результатов, если ее нет."""
    if not os.path.exists(RESULTS_FOLDER):
        os.makedirs(RESULTS_FOLDER)

def classify_object(brightness, area, eccentricity):
    """
    Определяет тип объекта на основе характеристик: яркости, площади и эксцентриситета (формы).
    """
    if brightness > 200 and area < 100:  # маленький и яркий объект
        return 'Star'
    elif 100 <= area <= 1000 and eccentricity < 0.5:  # объект круглой формы среднего размера
        return 'Planet'
    elif area > 1000:  # крупный объект с неправильной формой
        return 'Galaxy'
    else:
        return 'Unknown'

def process_object(obj_slice, image_array, img_name):
    """
    Обработка отдельного объекта: вычисляет статистику для объекта, определяет его тип и сохраняет изображение объекта.
    """
    obj_region = image_array[obj_slice]
    brightness = np.mean(obj_region)

    # Центр массы объекта
    x_indices, y_indices = np.meshgrid(np.arange(obj_region.shape[1]), np.arange(obj_region.shape[0]))
    total_mass = np.sum(obj_region)
    if total_mass > 0:
        center_x = int(np.sum(x_indices * obj_region) / total_mass)
        center_y = int(np.sum(y_indices * obj_region) / total_mass)
    else:
        center_x, center_y = (0, 0)

    # Площадь и эксцентриситет объекта
    area = obj_region.size
    labeled_obj = measure.label(obj_region > 0)  # лейблинг для нахождения формы
    region_props = measure.regionprops(labeled_obj)
    eccentricity = region_props[0].eccentricity if region_props else 0  # форма объекта

    # Классификация объекта
    obj_type = classify_object(brightness, area, eccentricity)

    # Формируем результаты
    stats = {
        'object_brightness': brightness,
        'object_center': (center_x, center_y),
        'object_type': obj_type
    }

    return stats

def annotate_image(image, objects):
    """
    Рисует зеленые квадратики вокруг объектов и подписывает их тип.
    """
    annotated_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)  # Конвертация в цветной формат для аннотаций

    for obj in objects:
        x, y = obj['object_center']
        obj_type = obj['object_type']

        # Определяем размеры квадрата
        box_size = 10
        start_point = (x - box_size, y - box_size)
        end_point = (x + box_size, y + box_size)

        # Рисуем квадрат
        cv2.rectangle(annotated_image, start_point, end_point, (0, 255, 0), 2)

        # Добавляем текст
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(annotated_image, obj_type, (x + 5, y - 10), font, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

    return annotated_image

def analyze_image(image_path):
    """
    Выполняет анализ изображения: сегментирует изображение и обрабатывает каждый объект отдельно.
    """
    try:
        img = Image.open(image_path).convert('L')
        img_array = np.array(img)

        threshold = threshold_otsu(img_array)
        binary_image = img_array > threshold
        labeled_image = measure.label(binary_image, connectivity=2)
        regions = measure.regionprops(labeled_image)

        img_name = os.path.basename(image_path)
        img_result_folder = os.path.join(RESULTS_FOLDER, img_name)
        os.makedirs(img_result_folder, exist_ok=True)

        process_obj_partial = partial(process_object, image_array=img_array, img_name=img_name)

        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            results = list(executor.map(process_obj_partial, [region.slice for region in regions]))

        # Собираем данные для аннотации
        objects_data = [{'object_center': stat['object_center'], 'object_type': stat['object_type']} for stat in results]

        # Аннотируем изображение
        annotated_img = annotate_image(img_array, objects_data)
        cv2.imwrite(os.path.join(img_result_folder, 'annotated_image.png'), annotated_img)

        return {
            'filename': img_name,
            'objects_analyzed': len(results),
            'objects_stats': results
        }

    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

class AstroDataAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Astro Data Analyzer")
        self.root.geometry("600x400")

        # Кнопка загрузки изображений
        self.load_button = tk.Button(root, text="Load Images", command=self.load_images)
        self.load_button.pack(pady=10)

        # Список для отображения результатов анализа
        self.result_text = tk.Text(root, wrap=tk.WORD, height=15, width=70)
        self.result_text.pack(pady=10)

        # Пул процессов для параллельной обработки
        self.executor = ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())
        self.images = []

    def load_images(self):
        # Открываем диалоговое окно выбора файлов
        image_paths = filedialog.askopenfilenames(title="Select Images", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if not image_paths:
            return

        # Очищаем список изображений и текстовое поле с результатами
        self.images = image_paths
        self.result_text.delete(1.0, tk.END)

        # Запускаем параллельную обработку изображений
        self.start_analysis()

    def start_analysis(self):
        create_results_folder()
        self.result_text.insert(tk.END, "Starting analysis...\n")

        # Параллельный запуск анализа для каждого изображения
        futures = [self.executor.submit(analyze_image, image_path) for image_path in self.images]

        # Ожидание завершения всех задач
        for future in futures:
            result = future.result()
            if result:
                self.display_result(result)
            else:
                self.result_text.insert(tk.END, "An error occurred during analysis.\n")

        messagebox.showinfo("Analysis Complete", "Analysis of all images is complete.")

    def display_result(self, result):
        # Вывод результатов анализа в текстовое поле
        self.result_text.insert(tk.END, f"Filename: {result['filename']}\n")
        self.result_text.insert(tk.END, f"Objects Analyzed: {result['objects_analyzed']}\n\n")
        for obj_stat in result['objects_stats']:
            self.result_text.insert(tk.END, f" Object Brightness: {obj_stat['object_brightness']}\n")
            self.result_text.insert(tk.END, f" Object Center of Mass: {obj_stat['object_center']}\n")
            self.result_text.insert(tk.END, f" Object Type: {obj_stat['object_type']}\n")
        self.result_text.insert(tk.END, "\n")

# Запуск приложения
if __name__ == "__main__":
    root = tk.Tk()
    app = AstroDataAnalyzerApp(root)
    root.mainloop()