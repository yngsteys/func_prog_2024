import pandas as pd

# Загрузка CSV файла
df = pd.read_csv('dataset/BooksDataset.csv')

# Удаление строк, где Description или Category пустые
df_cleaned = df.dropna(subset=['Description', 'Category'], how='any')

# Удаление дубликатов по полю "Title" (оставляем только первую встреченную книгу с уникальным названием)
df_cleaned_unique_titles = df_cleaned.drop_duplicates(subset=['Title'], keep='first')

df_cleaned_unique_titles = df_cleaned_unique_titles.drop(columns=['Price'])

# Сохранение очищенного датасета в новый CSV файл
df_cleaned_unique_titles.to_csv('dataset/cleaned_books.csv', index=False)

print("Очищенный файл сохранен как 'cleaned_books.csv'.")
