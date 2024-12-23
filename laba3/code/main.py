from flask import Flask, render_template, request, jsonify
import pandas as pd
import pickle
from sklearn.metrics.pairwise import euclidean_distances
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string
import numpy as np

app = Flask(__name__)

stop_words = set(stopwords.words('english'))

# Функция для предобработки текста
def preprocess_text(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))  # Убираем пунктуацию
    words = word_tokenize(text)
    words = [word for word in words if word not in stop_words]  # Убираем стоп-слова
    return ' '.join(words)

# Загружаем данные из pickle
with open('../dataset/processed_books.pkl', 'rb') as f:
    df = pickle.load(f)
    df['Publish Date'] = pd.to_datetime(df['Publish Date'], errors='coerce', format='%A, %B %d, %Y')
    df['Publish Date'] = df['Publish Date'].dt.year
    title_vectors = pickle.load(f)
    category_vectors = pickle.load(f)
    description_vectors = pickle.load(f)
    author_vectors = pickle.load(f)
    vectorizer = pickle.load(f)
    
def recommend_books(user_preferences, df, vectorizer, top_n=10):
    # Обрабатываем предпочтения пользователя, только если они были указаны
    if user_preferences.get('title'):
        user_processed_title = preprocess_text(user_preferences['title'])
        user_title_vector = vectorizer.transform([user_processed_title])
        title_distances = euclidean_distances(user_title_vector, title_vectors)
    else:
        title_distances = np.zeros((1, len(df))) 

    if user_preferences.get('category'):
        user_processed_category = preprocess_text(user_preferences['category'])
        user_category_vector = vectorizer.transform([user_processed_category])
        category_distances = euclidean_distances(user_category_vector, category_vectors)
    else:
        category_distances = np.zeros((1, len(df)))  

    if user_preferences.get('description'):
        user_processed_description = preprocess_text(user_preferences['description'])
        user_description_vector = vectorizer.transform([user_processed_description])
        description_distances = euclidean_distances(user_description_vector, description_vectors)
    else:
        description_distances = np.zeros((1, len(df))) 

    if user_preferences.get('author'):
        user_processed_author = preprocess_text(user_preferences['author'])
        user_author_vector = vectorizer.transform([user_processed_author])
        author_distances = euclidean_distances(user_author_vector, author_vectors)
    else:
        author_distances = np.zeros((1, len(df))) 

    # Инвертируем расстояние, так как меньшее расстояние - это большее сходство
    final_scores = 1 / (1 + 3.0 * title_distances + 1.5 * category_distances + 0.7 * description_distances + 3.5 * author_distances)

    # Создаем изначальную маску для фильтрации
    mask = np.ones(len(df), dtype=bool)

    # Применяем фильтрацию по жанрам
    if user_preferences.get('filter_category'):
        category_mask = df['Category'].str.contains(user_preferences['filter_category'], case=False, na=False)
        mask &= category_mask

    # Применяем фильтрацию по году публикации
    if user_preferences.get('filter_year'):
        year_mask = df['Publish Date'] >= int(user_preferences['filter_year'])
        mask &= year_mask

    # Применяем маску к DataFrame и final_scores
    df = df[mask].reset_index(drop=True)
    final_scores = final_scores[:, mask]

    if df.empty:
        return pd.DataFrame()  # Если после фильтрации ничего не осталось

    # Сортируем по Similarity_score
    recommended_books_indices = final_scores.argsort()[0][-top_n:][::-1]

    # Убедимся, что индексы корректны
    recommended_books_indices = [i for i in recommended_books_indices if i < len(df)]

    if not recommended_books_indices:
        return pd.DataFrame()  # Если индексы пусты, возвращаем пустой DataFrame

    # Выбираем из df по индексу
    recommended_books = df.iloc[recommended_books_indices].copy()

    # Добавляем столбец Similarity_score
    recommended_books['Similarity_score'] = final_scores[0][recommended_books_indices]

    # Применяем сортировку по выбранному критерию
    sort_by = user_preferences.get('sort_by', 'Similarity_score')
    if sort_by == 'Similarity_score':
        recommended_books = recommended_books.sort_values(by='Similarity_score', ascending=False).head(top_n)
    elif sort_by == 'Title':
        recommended_books = recommended_books.sort_values(by='Title').head(top_n)
    elif sort_by == 'Publish Date':
        recommended_books = recommended_books.sort_values(by='Publish Date', ascending=False).head(top_n)

    
    return recommended_books


@app.route('/')
def index():
    # Передаём пустые значения в user_preferences для начального рендера страницы
    user_preferences = {
        'title': '',
        'category': '',
        'description': '',
        'author': '',
        'filter_category': '',
        'filter_year': '',
        'sort_by': 'Similarity_score'  # Значение по умолчанию
    }
    return render_template('index.html', user_preferences=user_preferences)


@app.route('/recommend', methods=['POST'])
def recommend():
    user_preferences = {
        'title': request.form.get('title', ''),
        'category': request.form.get('category', ''),
        'description': request.form.get('description', ''),
        'author': request.form.get('author', ''),
        'filter_category': request.form.get('filter_category', ''),
        'filter_year': request.form.get('filter_year', ''),
        'sort_by': request.form.get('sort_by', 'Similarity_score')  # Установка значения по умолчанию
    }

    # Получаем рекомендации
    recommended_books = recommend_books(user_preferences, df, vectorizer)

    # Преобразуем результаты в формат, удобный для отображения
    if recommended_books.empty:
        return render_template(
            'index.html', 
            recommendations=[], 
            user_preferences=user_preferences, 
            message="No recommendations found."
        )

    recommendations = recommended_books[['Title', 'Authors', 'Category', 'Publish Date', 'Similarity_score', 'Description']].to_dict(orient='records')

    return render_template(
        'index.html', 
        recommendations=recommendations, 
        user_preferences=user_preferences
    )


@app.route('/save', methods=['POST'])
def save():
    data = request.json
    # Сохранение рекомендаций в CSV
    df = pd.DataFrame(data)
    df.to_csv('recommendations.csv', index=False)
    return jsonify({'message': 'Recommendations saved to recommendations.csv'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

