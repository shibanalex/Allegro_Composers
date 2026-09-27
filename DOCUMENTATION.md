# Allegro - Полная документация

**Версия:** 0.1.0  
**Дата:** Сентябрь 2024  
**Автор:** Composer

---

## Оглавление

1. [Быстрый старт](#быстрый-старт)
2. [Установка](#установка)
3. [Конфигурация](#конфигурация)
4. [Запуск проекта](#запуск-проекта)
5. [Структура проекта](#структура-проекта)
6. [Backend API](#backend-api)
7. [Frontend компоненты](#frontend-компоненты)
8. [База данных](#база-данных)
9. [Права доступа](#права-доступа)
10. [Развертывание](#развертывание)
11. [Решение проблем](#решение-проблем)
12. [Расширение функционала](#расширение-функционала)

---

## Быстрый старт

### Требования
- Python 3.10+
- Node.js 18+
- PostgreSQL 12+
- Git

### Установка за 5 минут

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd Allegro

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Отредактировать .env с правильными переменными

# 3. Frontend
cd ../frontend
npm install

# 4. Запустить оба (в разных терминалах)
# Терминал 1: cd backend && python main.py
# Терминал 2: cd frontend && npm run dev
```

Готово! Сайт доступен на http://localhost:5173

---

## Установка

### Backend - Подробно

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv

# Активировать
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt

# Копировать и настроить .env
cp .env.example .env
```

**Содержимое .env:**
```
DATABASE_URL=postgresql://user:password@localhost:5432/allegro_db
SECRET_KEY=your-super-secret-key-generate-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
YOUTUBE_API_KEY=your-youtube-api-key
FRONTEND_URL=http://localhost:5173
DEBUG=True
LOG_LEVEL=INFO
```

### Frontend - Подробно

```bash
cd frontend

# Установить npm зависимости
npm install

# Если используются npm workspace или монорепо
npm install --workspace=frontend
```

---

## Конфигурация

### Backend конфигурация

**Файл:** `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # Database
    database_url: str                    # PostgreSQL URL
    
    # Security
    secret_key: str                      # JWT secret (VERY IMPORTANT!)
    algorithm: str = "HS256"             # JWT algorithm
    access_token_expire_minutes: int = 30 # Token lifetime
    
    # YouTube
    youtube_api_key: Optional[str]       # For YouTube integration
    
    # CORS
    frontend_url: str                    # Разрешить запросы с фронта
    
    # App
    debug: bool = True
    log_level: str = "INFO"
```

### Frontend конфигурация

**Файл:** `frontend/vite.config.js`

```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // Backend URL для разработки
        changeOrigin: true,
      }
    }
  }
})
```

**Для production:** Отредактировать в `frontend/src/api/client.js`

---

## Запуск проекта

### Локальное развитие

#### Способ 1: Два терминала

```bash
# Терминал 1 - Backend
cd backend
source venv/bin/activate
python main.py
# Backend слушает на http://localhost:8000
# Документация API: http://localhost:8000/docs

# Терминал 2 - Frontend  
cd frontend
npm run dev
# Frontend на http://localhost:5173
```

#### Способ 2: Docker Compose

```bash
docker-compose up

# Все сервисы запустятся:
# - PostgreSQL: localhost:5432
# - Backend: localhost:8000
# - Frontend: localhost:5173
```

#### Способ 3: VSCode

```bash
# Создать tasks.json в .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Backend",
      "type": "shell",
      "command": "python main.py",
      "cwd": "${workspaceFolder}/backend",
      "isBackground": true,
      "problemMatcher": "$python"
    },
    {
      "label": "Run Frontend",
      "type": "shell",
      "command": "npm run dev",
      "cwd": "${workspaceFolder}/frontend",
      "isBackground": true
    }
  ]
}
```

---

## Структура проекта

```
Allegro/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app factory
│   │   ├── core/
│   │   │   ├── config.py          # Settings
│   │   │   ├── database.py        # DB session
│   │   │   └── security.py        # JWT utilities
│   │   ├── domain/
│   │   │   ├── compositions/
│   │   │   │   └── models.py      # Composition entity
│   │   │   ├── blog/
│   │   │   │   └── models.py      # BlogPost entity
│   │   │   ├── workshop/
│   │   │   │   └── models.py      # WorkshopPost entity
│   │   │   ├── comments/
│   │   │   │   └── models.py      # Comment entity
│   │   │   └── admin/
│   │   │       └── models.py      # AdminUser entity
│   │   ├── application/
│   │   │   └── services.py        # Business logic
│   │   ├── infrastructure/
│   │   │   └── youtube_client.py  # YouTube API (TODO)
│   │   ├── api/
│   │   │   ├── schemas.py         # Pydantic schemas
│   │   │   └── routes/
│   │   │       ├── compositions.py
│   │   │       ├── blog.py
│   │   │       ├── workshop.py
│   │   │       ├── comments.py
│   │   │       └── auth.py
│   ├── main.py                     # Entry point
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── main.js                 # App entry point
│   │   ├── App.vue                 # Root component
│   │   ├── views/
│   │   │   ├── Home.vue           # Главная страница
│   │   │   ├── Compositions.vue    # Галерея произведений
│   │   │   ├── Workshop.vue       # Процесс создания
│   │   │   ├── Blog.vue           # Список постов
│   │   │   ├── BlogPost.vue       # Отдельный пост
│   │   │   └── Admin.vue          # Админ панель
│   │   ├── components/            # Переиспользуемые компоненты
│   │   ├── router/
│   │   │   └── index.js           # Vue Router конфиг
│   │   ├── stores/                # Pinia (state management)
│   │   ├── api/
│   │   │   └── client.js          # Axios instance
│   │   └── assets/
│   │       └── styles.css         # Tailwind styles
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── README.md
├── ARCHITECTURE.md
├── DEPLOYMENT.md
└── DOCUMENTATION.md (этот файл)
```

---

## Backend API

### API структура

```
http://localhost:8000/api/{resource}/{action}
```

### Compositions (Произведения)

#### GET /api/compositions/
Получить все произведения

**Query параметры:**
- `skip` (int, default=0) - Пропустить N записей
- `limit` (int, default=10) - Получить максимум N записей

**Response:**
```json
[
  {
    "id": 1,
    "title": "Symphony No. 1",
    "description": "My first symphony",
    "youtube_id": "dQw4w9WgXcQ",
    "thumbnail_url": "https://...",
    "duration": 480,
    "published_at": "2024-01-15T10:30:00",
    "created_at": "2024-01-15T10:30:00",
    "is_featured": true
  }
]
```

#### GET /api/compositions/{id}
Получить конкретное произведение

**Parameters:**
- `id` (int, path) - ID произведения

#### POST /api/compositions/
Создать новое произведение ⚠️ ТРЕБУЕТ АУТЕНТИФИКАЦИИ

**Body:**
```json
{
  "title": "New Composition",
  "description": "Description",
  "youtube_id": "VIDEO_ID"
}
```

---

### Blog (Блог)

#### GET /api/blog/
Получить все опубликованные посты

**Query параметры:**
- `skip` (int, default=0)
- `limit` (int, default=10)

#### GET /api/blog/{slug}
Получить пост по slug

**Example:** `/api/blog/my-first-post`

#### POST /api/blog/
Создать новый пост ⚠️ ТРЕБУЕТ АУТЕНТИФИКАЦИИ

**Body:**
```json
{
  "title": "My Blog Post",
  "slug": "my-blog-post",
  "content": "Full article text here...",
  "excerpt": "Short preview..."
}
```

---

### Workshop (Процесс создания)

#### GET /api/workshop/
Получить все workshop посты

**Query параметры:**
- `skip`, `limit`

#### POST /api/workshop/
Создать workshop пост ⚠️ ТРЕБУЕТ АУТЕНТИФИКАЦИИ

**Body:**
```json
{
  "title": "Creating Symphony",
  "description": "Process description",
  "image_urls": ["url1", "url2"],
  "file_urls": ["file1.midi", "file2.pdf"]
}
```

---

### Comments (Комментарии)

#### GET /api/comments/post/{blog_post_id}
Получить все одобренные комментарии к посту

#### POST /api/comments/
Создать комментарий (анонимный или зарегистрированный)

**Body:**
```json
{
  "blog_post_id": 1,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "content": "Great post!",
  "is_anonymous": false
}
```

**Notes:**
- `author_email` опциональна
- Если `is_anonymous=true`, email не показывается

---

### Authentication (Аутентификация)

#### POST /api/auth/login
Вход админа

**Body:**
```json
{
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### POST /api/auth/verify
Проверка токена

**Body:**
```json
{
  "token": "eyJhbGc..."
}
```

**Response:**
```json
{
  "valid": true,
  "user": "admin"
}
```

---

### Использование токена в запросах

```javascript
// Headers
Authorization: Bearer {access_token}
```

**JavaScript пример:**
```javascript
const token = localStorage.getItem('token')
axios.post('/api/blog/', data, {
  headers: {
    Authorization: `Bearer ${token}`
  }
})
```

---

## Frontend компоненты

### Vue компоненты

#### Home.vue
- Hero section
- Featured compositions
- About section

#### Compositions.vue
- Grid галерея
- Загрузка данных с API
- YouTube интеграция (TODO)

#### Workshop.vue
- Timeline постов
- Images & files
- Rich content

#### Blog.vue
- Список постов
- Search (TODO)
- Pagination

#### BlogPost.vue
- Полная статья
- Comments section
- Comment form

#### Admin.vue
- Вход
- Dashboard
- Forms для создания контента
- Управление постами

### Стили

**Dark Academia палитра:**
- Основной фон: `#1a1410`
- Средний фон: `#2d2620`
- Светлый текст: `#f8f7f4`
- Акцент (gold): `#d4a574`

**Tailwind классы:**
- `.btn-primary` - Основная кнопка
- `.btn-secondary` - Вторичная кнопка
- `.card` - Карточка
- `.nav-active` - Активный пункт навигации

---

## База данных

### Schema

```sql
-- Compositions
CREATE TABLE compositions (
  id SERIAL PRIMARY KEY,
  youtube_id VARCHAR(255) UNIQUE NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  thumbnail_url VARCHAR(512),
  duration INTEGER,
  published_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  is_featured BOOLEAN DEFAULT FALSE
);

-- Blog Posts
CREATE TABLE blog_posts (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  content TEXT NOT NULL,
  excerpt VARCHAR(512),
  author VARCHAR(255) DEFAULT 'Composer',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP,
  is_published BOOLEAN DEFAULT TRUE,
  view_count INTEGER DEFAULT 0
);

-- Workshop Posts
CREATE TABLE workshop_posts (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  image_urls JSON,
  file_urls JSON,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  is_published BOOLEAN DEFAULT TRUE
);

-- Comments
CREATE TABLE comments (
  id SERIAL PRIMARY KEY,
  blog_post_id INTEGER REFERENCES blog_posts(id),
  author_name VARCHAR(255) NOT NULL,
  author_email VARCHAR(255),
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  is_approved BOOLEAN DEFAULT TRUE,
  is_anonymous BOOLEAN DEFAULT TRUE
);

-- Admin Users
CREATE TABLE admin_users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  hashed_password VARCHAR(512) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP
);
```

### Создание таблиц

```bash
# SQLAlchemy автоматически создаст таблицы при запуске
# Или вручную через PostgreSQL:

psql -U user -d allegro_db < schema.sql
```

---

## Права доступа

### Типы пользователей

1. **Анонимный пользователь** - Может читать посты, смотреть произведения, писать комментарии
2. **Зарегистрированный** - Как анонимный, но комментарии с именем
3. **Админ** - Полный доступ к управлению контентом

### Защищенные маршруты

| Маршрут | Метод | Требует Auth |
|---------|-------|--------------|
| GET /api/compositions/ | GET | ❌ |
| POST /api/compositions/ | POST | ✅ |
| GET /api/blog/ | GET | ❌ |
| POST /api/blog/ | POST | ✅ |
| POST /api/workshop/ | POST | ✅ |
| POST /api/comments/ | POST | ❌ |

---

## Развертывание

### Vercel (Frontend)

```bash
cd frontend
npm run build

# Загрузить на GitHub
# Подключить репо в Vercel Dashboard
```

**Environment variables в Vercel:**
```
VITE_API_URL=https://your-backend.railway.app
```

### Railway/Render (Backend)

1. Загрузить на GitHub
2. Подключить репо
3. Set environment variables:
   - DATABASE_URL
   - SECRET_KEY
   - YOUTUBE_API_KEY
   - FRONTEND_URL

Система автоматически запустит `pip install -r requirements.txt` и uvicorn

### Собственный сервер

```bash
# Docker build
docker build -t allegro-backend ./backend
docker run -p 8000:8000 allegro-backend

# Nginx proxy
server {
    listen 80;
    server_name your-domain.com;
    
    location /api {
        proxy_pass http://localhost:8000;
    }
    
    location / {
        proxy_pass http://localhost:5173;
    }
}
```

---

## Решение проблем

### Backend не запускается

**Ошибка:** `ModuleNotFoundError: No module named 'app'`

**Решение:**
```bash
# Убедиться в правильной структуре
cd backend
python main.py  # Должен работать из backend/
```

### Ошибка подключения БД

**Ошибка:** `SQLALCHEMY_DATABASE_URI not set`

**Решение:**
```bash
# Проверить .env
cat .env

# Убедиться что PostgreSQL запущена
psql -U user -d allegro_db -c "SELECT 1"

# Проверить строку подключения
# postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

### Frontend не подключается к backend

**Ошибка:** `Failed to fetch /api/compositions/`

**Решение:**
1. Проверить что backend запущен: `http://localhost:8000/health`
2. Проверить CORS настройки в `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],  # Должен быть http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Токен не работает

**Ошибка:** `401 Unauthorized`

**Решение:**
1. Убедиться что token сохранен в localStorage
2. Проверить что header правильный: `Authorization: Bearer {token}`
3. Проверить что `SECRET_KEY` одинаков в конфиге

### Hot reload не работает

**Решение:**
```bash
# Для backend - includer reload=True в uvicorn
python -m uvicorn app.main:app --reload

# Для frontend - перезапустить npm
npm run dev  # Должен автоматически пересчитывать
```

---

## Расширение функционала

### Добавить новый домен (например, Events)

1. Создать папку `backend/app/domain/events/`

2. Создать модель:
```python
# backend/app/domain/events/models.py
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    date = Column(DateTime)
    location = Column(String(255))
```

3. Создать сервис:
```python
# backend/app/application/services.py - добавить
class EventService:
    @staticmethod
    def create_event(db: Session, event: EventCreate) -> Event:
        db_event = Event(**event.model_dump())
        db.add(db_event)
        db.commit()
        return db_event
```

4. Создать routes:
```python
# backend/app/api/routes/events.py
from fastapi import APIRouter
from app.application.services import EventService

router = APIRouter(prefix="/api/events", tags=["events"])

@router.get("/")
def get_events(db: Session = Depends(get_db)):
    return EventService.get_events(db)
```

5. Регистр в app:
```python
# backend/app/main.py
from app.api import routes
app.include_router(routes.events.router)
```

6. Frontend компонент:
```vue
<!-- frontend/src/views/Events.vue -->
<template>
  <div>
    <h1>Events</h1>
    <!-- v-for events, display them -->
  </div>
</template>
```

### Добавить YouTube автосинк

```python
# backend/app/infrastructure/youtube_client.py
import httpx

class YouTubeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def get_channel_videos(self, channel_id: str):
        url = f"https://www.googleapis.com/youtube/v3/search"
        params = {
            "channelId": channel_id,
            "key": self.api_key,
            "part": "id,snippet",
            "order": "date",
            "maxResults": 50,
            "type": "video"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            return response.json()
```

### Добавить Pinia Store (Frontend)

```javascript
// frontend/src/stores/compositions.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useCompositionStore = defineStore('compositions', () => {
  const items = ref([])
  const loading = ref(false)
  
  const fetchCompositions = async () => {
    loading.value = true
    const { data } = await axios.get('/api/compositions/')
    items.value = data
    loading.value = false
  }
  
  const featured = computed(() => 
    items.value.filter(c => c.is_featured)
  )
  
  return { items, loading, fetchCompositions, featured }
})
```

---

## Полезные команды

```bash
# Backend
python main.py                    # Запустить
python -m pytest                  # Тесты
python -m black app/              # Форматирование
python -m flake8 app/             # Линтинг

# Frontend  
npm run dev                       # Разработка
npm run build                     # Production build
npm run preview                   # Preview build
npm run lint                      # Проверка

# Database
psql -U user -d allegro_db        # Вход в БД
\dt                               # Показать таблицы
\d compositions                   # Schema таблицы

# Docker
docker-compose up                 # Запустить все
docker-compose down               # Остановить все
docker-compose logs -f backend    # Логи
```

---

**Версия документа:** v1.0  
**Последнее обновление:** Сентябрь 2024  
**Контакт:** composer@allegro.local
