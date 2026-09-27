# Quick Start Guide - Быстрый старт (5 минут)

**⚡ Это самый быстрый путь к запуску проекта**

---

## 🚀 Запуск (5 минут)

### Требования

```bash
python --version    # 3.10+
node --version      # 18+
psql --version      # 12+
```

### 1️⃣ Clone & Setup

```bash
git clone <repo-url>
cd Allegro

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux: или venv\Scripts\activate (Windows)
pip install -r requirements.txt
cp .env.example .env

# Frontend
cd ../frontend
npm install
```

### 2️⃣ Database

```bash
# Убедиться PostgreSQL запущена
psql -U postgres

# В psql консоли:
CREATE DATABASE allegro_db;
\q
```

### 3️⃣ Run (два терминала)

**Терминал 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python main.py
# http://localhost:8000
```

**Терминал 2 - Frontend:**
```bash
cd frontend
npm run dev
# http://localhost:5173
```

### 4️⃣ Login

Открыть http://localhost:5173 → Admin → username: `admin`

✅ Готово!

---

## 📚 Documentation

| Документ | Для кого | Что внутри |
|----------|----------|----------|
| **[README.md](README.md)** | Все | Обзор проекта, структура |
| **[DOCUMENTATION.md](DOCUMENTATION.md)** | Разработчики | Полная документация (стени кода, конфиг, API) |
| **[API_REFERENCE.md](API_REFERENCE.md)** | API users | Все endpoints с примерами |
| **[DEVELOPMENT.md](DEVELOPMENT.md)** | Разработчики | Как разрабатывать, стиль-гайды, тестирование |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | При проблемах | Q&A, debug tips, решения |
| **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** | Перед launch | Чек-лист, инструкции Railway/Vercel |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Архитекторы | DDD, масштабирование, домены |

---

## 🆘 Быстрые ответы

**Q: Backend не запускается**
```bash
# В backend/
rm -rf __pycache__
python main.py
```

**Q: БД не работает**
```bash
psql -U postgres -c "CREATE DATABASE allegro_db"
```

**Q: Frontend не видит backend**
```bash
# Проверить http://localhost:8000/health
# Должна быть {"status": "healthy"}
```

**Q: Токен не работает**
```bash
# В backend/.env
SECRET_KEY=anything  # (На разработке может быть любым)
```

**Больше ответов:** см. [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📋 Что где?

```
├── backend/                    # FastAPI
│   ├── app/
│   │   ├── domain/            # Бизнес логика (compositions, blog, etc.)
│   │   ├── application/       # Services (get_post, create_comment, etc.)
│   │   ├── api/
│   │   │   ├── routes/        # API endpoints
│   │   │   └── schemas.py     # Request/response models
│   │   └── core/
│   │       ├── config.py      # Settings
│   │       ├── database.py    # DB connection
│   │       └── security.py    # JWT
│   └── main.py               # Entry point
│
├── frontend/                   # Vue 3
│   ├── src/
│   │   ├── views/            # Страницы (Home, Blog, Admin, etc.)
│   │   ├── components/       # Переиспользуемые компоненты
│   │   ├── router/           # Маршруты
│   │   ├── api/              # Axios клиент
│   │   └── assets/           # CSS, шрифты
│   └── vite.config.js        # Build config
│
└── docs/
    ├── README.md            # ← Начните отсюда
    ├── DOCUMENTATION.md     # Полная документация
    ├── API_REFERENCE.md     # API docs
    ├── DEVELOPMENT.md       # Разработка
    ├── TROUBLESHOOTING.md   # Проблемы
    ├── DEPLOYMENT.md        # Deploy
    ├── ARCHITECTURE.md      # Архитектура
    └── QUICK_START.md       # ← Вы здесь
```

---

## 🎯 Что дальше?

### 1. Разработка
- Читать [DEVELOPMENT.md](DEVELOPMENT.md)
- Создавать новые features в отдельных branches
- Коммитить в conventional format

### 2. Тестирование
```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm run test
```

### 3. Добавление контента
- Открыть http://localhost:5173/admin
- Добавить произведения, посты, workshop

### 4. Развертывание
- Когда готово: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- Railway (backend) + Vercel (frontend)

---

## 💡 Полезные команды

```bash
# Backend API docs
http://localhost:8000/docs

# Watch tests
pytest --watch  # или: pytest -v --tb=short

# Format code
black app/   # Python
npm run lint # Vue

# Check types
mypy app/  # Python (если установлен)

# Database
psql -U user -d allegro_db
\dt          # Tables
SELECT * FROM compositions LIMIT 5;
```

---

## 🆘 Еще не работает?

1. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 90% проблем там
2. **Логи:** `python main.py` или `npm run dev` (посмотреть output)
3. **Browser console:** F12 → Console (смотреть ошибки)
4. **Database:** `psql -U user -d allegro_db` (проверить таблицы и данные)

---

## 📞 Помощь

- **Документация:** [DOCUMENTATION.md](DOCUMENTATION.md)
- **API Docs:** [API_REFERENCE.md](API_REFERENCE.md)
- **Проблемы:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **GitHub Issues:** https://github.com/your/repo/issues

---

## ✅ Чек-лист первого запуска

- [ ] Python 3.10+ установлен
- [ ] Node 18+ установлен
- [ ] PostgreSQL запущена
- [ ] Backend dependencies установлены (`pip install -r requirements.txt`)
- [ ] Frontend dependencies установлены (`npm install`)
- [ ] .env файл скопирован и заполнен
- [ ] Backend запускается (`python main.py`)
- [ ] Frontend запускается (`npm run dev`)
- [ ] Можно открыть http://localhost:5173
- [ ] Admin панель доступна

---

**🎉 Поздравляю! Проект готов для разработки!**

**Дальше:** 
- Разработка → [DEVELOPMENT.md](DEVELOPMENT.md)
- Проблемы → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Deploy → [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

