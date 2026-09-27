# Troubleshooting Guide - Решение проблем

---

## Таблица проблем и решений

| Проблема | Причина | Решение |
|----------|---------|---------|
| Backend не запускается | Неправильный путь | см. [Backend не стартует](#backend-не-стартует) |
| БД не подключается | PostgreSQL не запущена | см. [Ошибка подключения БД](#ошибка-подключения-бд) |
| Frontend не видит API | CORS ошибка | см. [CORS ошибка](#cors-ошибка) |
| Токен не работает | Неверный SECRET_KEY | см. [Аутентификация не работает](#аутентификация-не-работает) |
| Hot reload не работает | Файлы не сохраняются | см. [Hot reload не работает](#hot-reload-не-работает) |

---

## Проблемы Backend

### Backend не стартует

**Признаки:**
```
ModuleNotFoundError: No module named 'app'
ImportError: cannot import name 'app'
```

**Быстрое решение:**
```bash
# Убедиться что вы в правильной директории
cd backend

# Проверить структуру
ls -la   # или: dir (Windows)
# Должны увидеть: app/, main.py, requirements.txt, .env

# Запустить заново
python main.py
```

**Полное решение:**
```bash
# 1. Удалить кеш Python
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 2. Переустановить зависимости
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# 3. Проверить Python версию
python --version  # Должна быть 3.10+

# 4. Запустить с verbose
python -u main.py
```

---

### Ошибка подключения БД

**Признаки:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) FATAL: 
database "allegro_db" does not exist
```

**Решение 1: Создать базу данных**
```bash
# Linux/Mac
psql -U postgres

# Windows (если psql в PATH)
psql -U postgres

# Затем в psql:
CREATE DATABASE allegro_db;
\q

# Проверить подключение
psql -U user -d allegro_db -c "SELECT 1"
```

**Решение 2: Проверить .env**
```bash
cat .env

# Должно быть:
DATABASE_URL=postgresql://user:password@localhost:5432/allegro_db

# Где:
# user = имя пользователя PostgreSQL
# password = пароль
# localhost = хост (обычно localhost для разработки)
# 5432 = порт (стандартный)
# allegro_db = имя базы
```

**Решение 3: Проверить что PostgreSQL запущена**

**macOS (Homebrew):**
```bash
brew services start postgresql
psql --version
```

**Ubuntu/Debian:**
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

**Windows:**
```powershell
# PostgreSQL обычно стартует автоматически
# Если нет, запустить Services:
# Start → Services → postgresql → Start
```

**Docker способ:**
```bash
# Если используете docker-compose
docker-compose up postgres
# или запустить Postgres в контейнере
docker run --name allegro-postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15
```

---

### Migrations работают неправильно

**Признаки:**
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable)
relation "blog_posts" does not exist
```

**Решение:**
```bash
# SQLAlchemy создает таблицы автоматически
# Если таблиц нет, запустить:

python -c "
from app.core.database import Base, engine
from app.domain.compositions.models import Composition
from app.domain.blog.models import BlogPost
from app.domain.workshop.models import WorkshopPost
from app.domain.comments.models import Comment
from app.domain.admin.models import AdminUser

Base.metadata.create_all(bind=engine)
print('Tables created successfully!')
"

# Проверить что таблицы созданы
psql -U user -d allegro_db -c "\dt"
```

---

## Проблемы Frontend

### Frontend не подключается к backend

**Признаки:**
```
Failed to fetch http://localhost:8000/api/compositions/
CORS error: No 'Access-Control-Allow-Origin' header
```

**Решение 1: Проверить что backend запущен**
```bash
# Откройте в браузере
http://localhost:8000/health

# Должны увидеть
{"status": "healthy", "app": "Allegro"}

# Если не работает - запустить backend
cd backend
python main.py
```

**Решение 2: Проверить CORS конфигурацию**

**В backend/app/main.py:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],  # Должен быть http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**В backend/.env:**
```
FRONTEND_URL=http://localhost:5173
```

**Решение 3: Проверить proxy конфигурацию**

**В frontend/vite.config.js:**
```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
  }
}
```

---

### npm dependencies не устанавливаются

**Признаки:**
```
npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
```

**Решение:**
```bash
cd frontend

# Способ 1: Force installation
npm install --legacy-peer-deps

# Способ 2: Очистить кеш
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# Способ 3: Использовать yarn (если установлен)
yarn install
```

---

### Hot reload не работает

**Признаки:**
- Изменения в коде не отражаются сразу
- Нужно перезагружать страницу вручную

**Решение для Frontend:**
```bash
cd frontend

# Убедиться что запущен dev сервер
npm run dev

# Если не работает - перезапустить
# 1. Нажать Ctrl+C
# 2. npm run dev

# Проверить что files are watching
# Должны увидеть [62] ready in 123ms

# Если файлы не сохраняются - проверить .gitignore
# node_modules не должны быть в root .gitignore
```

**Для Backend:**
```bash
cd backend
python main.py

# Venv должен быть активирован
# Reload должен быть включен по умолчанию
# Если не работает - добавить --reload
python -m uvicorn app.main:app --reload
```

---

## Проблемы с аутентификацией

### Аутентификация не работает

**Признаки:**
```
401 Unauthorized
Invalid token
```

**Решение 1: Проверить SECRET_KEY**
```bash
# backend/.env
SECRET_KEY=your-super-secret-key-here

# ВАЖНО: Должен быть одинаков для:
# - Создания токена (login endpoint)
# - Проверки токена (verify endpoint)
```

**Решение 2: Проверить token в localStorage**
```javascript
// В консоли браузера (F12)
localStorage.getItem('access_token')
// Должен вернуть: eyJhbGc...

// Если пусто - нужно заново залогиниться
```

**Решение 3: Проверить Authorization header**
```javascript
// Правильно:
authorization: 'Bearer eyJhbGc...'

// Неправильно:
authorization: 'eyJhbGc...'  // Без "Bearer"
authorization: 'Bearer ' // Без токена
```

**Решение 4: Проверить что token не истек**
```python
# backend/app/core/config.py
ACCESS_TOKEN_EXPIRE_MINUTES=30  # токен действует 30 минут

# Если нужно дольше, увеличить значение
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # = 24 часа
```

---

### Логин возвращает 401

**Решение:**
```bash
# backend/app/api/routes/auth.py
# Сейчас простая проверка (username == "admin")

# Пока пароль любой
# Для production нужно:
# 1. Hash пароль при создании админа
# 2. Сравнить hashed пароль

# Временно: используйте username="admin"
```

---

## Проблемы с данными

### Данные не сохраняются в БД

**Решение:**
```bash
# 1. Проверить что БД запущена
psql -U user -d allegro_db -c "SELECT 1"

# 2. Проверить таблицы
psql -U user -d allegro_db -c "\dt"

# 3. Проверить данные
psql -U user -d allegro_db -c "SELECT * FROM compositions LIMIT 1"

# 4. Проверить транзакции в коде
# backend/app/application/services.py должны заканчиваться:
db.commit()
db.refresh(db_object)  # Для получения ID
```

---

### Произведения не загружаются

**Решение:**
```bash
# 1. Проверить API endpoint
curl http://localhost:8000/api/compositions/
# Должен вернуть JSON массив

# 2. Проверить что compositions есть в БД
psql -U user -d allegro_db -c "SELECT COUNT(*) FROM compositions"
# Если 0 - добавить через админ панель

# 3. Проверить браузер console (F12)
# Может быть CORS ошибка или другая проблема
```

---

## Performance Issues

### Медленная загрузка композиций

**Решение:**
```python
# backend/app/application/services.py

@staticmethod
def get_compositions(db: Session, skip: int = 0, limit: int = 10) -> List[Composition]:
    # Добавить limit по умолчанию
    return db.query(Composition).offset(skip).limit(limit).all()

# Frontend должен использовать pagination
axios.get('/api/compositions/?skip=0&limit=20')
```

---

### Frontend лагает при большом количестве постов

**Решение:**
```vue
<!-- frontend/src/views/Blog.vue -->
<template>
  <!-- Использовать v-show вместо v-if для списков -->
  <div v-show="post.visible" :key="post.id">
    {{ post.title }}
  </div>
  
  <!-- Использовать виртуальный список -->
  <!-- npm install vue-virtual-list -->
</template>

<script setup>
// Использовать lazy loading вместо загрузки всех сразу
const loadMorePosts = async () => {
  const newPosts = await axios.get('/api/blog/', {
    params: { skip: posts.value.length, limit: 20 }
  })
  posts.value.push(...newPosts.data)
}
</script>
```

---

## Docker Проблемы

### Docker container не запускается

**Решение:**
```bash
# 1. Проверить логи
docker logs allegro-backend
docker logs allegro-frontend

# 2. Проверить что образсоздан
docker image ls | grep allegro

# 3. Пересобрать образ
docker-compose down
docker-compose build --no-cache
docker-compose up

# 4. Проверить что порты свободны
# Backend: 8000
# Frontend: 5173
# PostgreSQL: 5432
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

---

### Database connection в Docker

**Решение:**
```yaml
# docker-compose.yml
services:
  postgres:
    environment:
      POSTGRES_DB: allegro_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password

  backend:
    environment:
      # ВАЖНО: использовать service name, не localhost!
      DATABASE_URL: postgresql://user:password@postgres:5432/allegro_db
      # Не: postgresql://localhost:5432/...
```

---

## Deployment Проблемы

### Railway deployment fails

**Решение:**
```bash
# 1. Проверить что requirements.txt есть
cd backend
pip freeze > requirements.txt
git add requirements.txt

# 2. Проверить что .env в .gitignore
# НЕ загружать .env на production!

# 3. Set environment variables в Railway Dashboard
# DATABASE_URL = Railway provides это автоматически
# SECRET_KEY = Сгенерировать случайно
# FRONTEND_URL = Vercel domain

# 4. Проверить Dockerfile
cat Dockerfile
# Должен содержать: CMD ["uvicorn", "app.main:app", ...]
```

### Vercel deployment fails

**Решение:**
```bash
# 1. Проверить package.json
npm run build

# 2. Проверить что dist/ создан
ls dist/

# 3. Проверить environment variables
# VITE_API_URL = Backend URL

# 4. Vercel configuration
# vercel.json должен содержать build settings
```

---

## General Debugging Tips

### Логирование

**Backend:**
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

**Frontend:**
```javascript
console.log("Log")
console.error("Error")
console.warn("Warning")
console.table(data)  // Красиво выводит объекты
```

### Проверка окружения

**Backend:**
```bash
# Что установлено
pip list

# Python версия
python --version

# PostgreSQL версия
psql --version

# Переменные окружения
env | grep DATABASE
```

**Frontend:**
```bash
# Node версия
node --version

# npm версия
npm --version

# node_modules установлены?
ls node_modules | wc -l  # Должно быть >100
```

---

## Когда все не помогает

**1. Ядерная опция - полная очистка:**
```bash
# Backend
cd backend
rm -rf venv __pycache__ .env
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Отредактировать .env

# Frontend
cd ../frontend
rm -rf node_modules package-lock.json
npm install
```

**2. Удалить все контейнеры:**
```bash
docker-compose down
docker system prune -a  # Осторожно! Удаляет все неиспользуемые образы
docker-compose up --build
```

**3. Сброс БД:**
```bash
# ВНИМАНИЕ: Это удалит ВСЕ данные!
psql -U postgres
DROP DATABASE allegro_db;
CREATE DATABASE allegro_db;
\q

# Таблицы восстановятся при запуске backend
```

**4. Проверить логи всего:**
```bash
# Backend
tail -100 /tmp/allegro.log

# Frontend  
# F12 → Console → посмотреть все ошибки

# Docker
docker-compose logs -f
```

---

## Контакт для помощи

- GitHub Issues: https://github.com/your-repo/Allegro/issues
- Email: composer@allegro.local
- Documentation: [DOCUMENTATION.md](DOCUMENTATION.md)
- API Reference: [API_REFERENCE.md](API_REFERENCE.md)

---

**Last Updated:** September 24, 2024  
**Версия приложения:** 0.1.0-beta
