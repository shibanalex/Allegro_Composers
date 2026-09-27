# Deployment Checklist - Чек-лист развертывания

---

## Pre-Deployment Checklist ✅

### 1 неделю перед выходом в production

- [ ] **Code Review**
  - [ ] Все коды имеют comments
  - [ ] Нет console.log() в продакшене
  - [ ] Нет hardcoded значений (API URLs, passwords)
  - [ ] Следуются стиль-гайды

- [ ] **Security**
  - [ ] SECRET_KEY - сгенерирован случайными символами
  - [ ] Пароли админа - сильные (минимум 12 символов)
  - [ ] CORS настроен правильно (только frontend domain)
  - [ ] Set DEBUG=False в production
  - [ ] Удалить .env из git (в .gitignore)
  - [ ] Удалить тестовые endpoints

- [ ] **Database**
  - [ ] Миграции применены
  - [ ] Backup сделан
  - [ ] Индексы добавлены для часто используемых полей
  - [ ] Connection pooling настроен

- [ ] **Frontend**
  - [ ] npm run build завершается без ошибок
  - [ ] dist/ папка создана и валидна
  - [ ] API URL правильно указана (не localhost)
  - [ ] Все шрифты загружены
  - [ ] Изображения оптимизированы

- [ ] **Backend**
  - [ ] pip install requirements.txt работает
  - [ ] Все migrations работают  
  - [ ] API endpoints тестированы (curl, Postman)
  - [ ] Rate limiting включен
  - [ ] Логирование настроено
  - [ ] Error handling правильный

- [ ] **Infrastructure**
  - [ ] PostgreSQL готова к production
  - [ ] Backup система настроена
  - [ ] SSL сертификаты готовы
  - [ ] CDN для статических файлов (опционально)
  - [ ] Мониторинг включен

- [ ] **Documentation**
  - [ ] README актуален
  - [ ] API документация актуальна
  - [ ] Deployment гайд написан
  - [ ] Emergency чек-лист подготовлен

---

## Vercel Deployment (Frontend)

### Шаг 1: Подготовка код

```bash
cd frontend
npm run build
# Проверить: dist/ создана
ls dist/

# Убедиться что работает
npm run preview
# http://localhost:4173
```

### Шаг 2: Git setup

```bash
git add .
git commit -m "feat: prepare for deployment"
git push origin main
```

### Шаг 3: Vercel Dashboard

1. Перейти на https://vercel.com
2. Click "New Project"
3. Import GitHub repository
4. Framework: Vite (auto-detected)
5. Build settings: Auto-detected
6. Environment variables:
   ```
   VITE_API_URL=https://your-backend.railway.app
   VITE_APP_NAME=Allegro
   ```
7. Click "Deploy"

### Шаг 4: Проверка

```bash
# Дождиться деплоя (обычно 2-3 минуты)
# Проверить: https://your-project.vercel.app

# Проверить что API работает
# DevTools → Network → вызовите API
# Должна быть успешная 200 response
```

### Troubleshooting Vercel

<details>
<summary>Deployment fails - "Build failed"</summary>

```bash
# 1. Проверить build локально
npm run build

# 2. Проверить that все dependencies есть
npm list

# 3. Очистить node_modules
rm -rf node_modules package-lock.json
npm install

# 4. Проверить vercel.json
cat vercel.json
```

</details>

---

## Railway Deployment (Backend)

### Шаг 1: Подготовка

```bash
cd backend

# Убедиться что requirements.txt актуален
pip freeze > requirements.txt

# Проверить Dockerfile
cat Dockerfile

# Create .env для local testing (не загружать!)
cp .env.example .env
```

### Шаг 2: Git setup

```bash
git add requirements.txt
git commit -m "chore: update requirements for deployment"
git push origin main
```

### Шаг 3: Railway Dashboard

1. Перейти на https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select repository
4. Railway auto-detects Python project
5. Set environment variables:
   ```
   DATABASE_URL = Railway PostgreSQL (auto-provided)
   SECRET_KEY = <generate random string>
   YOUTUBE_API_KEY = <your youtube api key>
   FRONTEND_URL = https://your-vercel-app.vercel.app
   DEBUG = False
   ALGORITHM = HS256
   ACCESS_TOKEN_EXPIRE_MINUTES = 30
   ```
6. Click "Deploy"

### Шаг 4: Database setup

```bash
# Railway создаст PostgreSQL автоматически
# Подключиться к ней:
# 1. В Railway dashboard найти PostgreSQL service
# 2. Click → "Connect"
# 3. Копировать DATABASE_URL

# Создать таблицы (one-time):
# Option 1: Через python подключение (смотри below)
# Option 2: Railway запустит migrations автоматически
```

### Шаг 5: Проверка

```bash
# Дождаться деплоя (обычно 5-10 минут)
# Проверить: https://your-backend-railway.up.railway.app/health

# Должны увидеть:
# {"status": "healthy", "app": "Allegro"}
```

### Troubleshooting Railway

<details>
<summary>Build logs показывают errors</summary>

```bash
# 1. Проверить requirements.txt
cat requirements.txt
# Должны быть основные packages

# 2. Проверить Python version
# Railway использует последнюю версию по умолчанию
# Если нужна конкретная - создать runtime.txt:
echo "python-3.11.4" > runtime.txt

# 3. Проверить что Dockerfile есть и валидна
cat Dockerfile

# 4. View build logs в Railway dashboard detail
```

</details>

---

## Environment Variables Checklist

### Frontend (.env или в Vercel)

```
VITE_API_URL=https://your-backend.railway.app
VITE_APP_NAME=Allegro
VITE_LOG_LEVEL=error  # production: error, development: debug
```

### Backend (.env или в Railway)

```
# Database
DATABASE_URL=postgresql://user:pass@host:5432/allegro_db

# Security
SECRET_KEY=generate-something-long-random-and-unique
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# YouTube
YOUTUBE_API_KEY=your-youtube-api-key-from-console.cloud.google.com

# CORS
FRONTEND_URL=https://your-vercel-app.vercel.app

# App
DEBUG=False                # ВАЖНО: False в production!
LOG_LEVEL=INFO            # INFO или WARNING для production
APP_NAME=Allegro
```

---

## Database Backup Strategy

### Ежедневный backup (Railway)

```bash
# Railway автоматически backups
# Но сделать backup вручную:

# 1. Dump database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
# Or via Railway console:
pg_dump -Fc $DATABASE_URL > backup.dump

# 2. Загрузить в безопасное место
# AWS S3, Google Drive, Dropbox и т.д.
```

### Восстановление из backup

```bash
# 1. Получить backup файл
# 2. Подключиться к БД
# 3. Restore:
psql $DATABASE_URL < backup.sql
# Or for custom format:
pg_restore -d $DATABASE_URL backup.dump
```

---

## Monitoring & Logging

### Railway Monitoring

1. Dashboard → Metrics tab
2. Смотреть:
   - CPU usage
   - Memory usage
   - Network I/O
   - Errors per minute

### Backend Logging

```python
# app/core/config.py
LOG_LEVEL = "INFO"  # production
# DEBUG за это логирует слишком много

# app/main.py
import logging
logging.basicConfig(level=settings.log_level)
```

### Frontend Error Tracking

```javascript
// src/main.js
window.addEventListener('error', (event) => {
  console.error('Uncaught error:', event.error)
  // Отправить на server (TODO - add error tracking service)
})

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason)
})
```

---

## SSL/HTTPS Setup

### For Vercel
✅ Автоматически настроено

### For Railway
✅ Автоматически настроено

### For custom domain (if not using Vercel/Railway)
```bash
# Use Let's Encrypt via Certbot
sudo certbot certonly --standalone -d your-domain.com
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Configure Nginx
sudo nano /etc/nginx/sites-available/default
# Add:
# ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
```

---

## Post-Deployment Validation

### ✅ Проверить что все работает

```bash
# 1. Frontend loads
curl https://your-app.vercel.app
# Должен вернуть HTML

# 2. Backend health
curl https://your-backend.railway.app/health
# Должен вернуть {"status": "healthy"}

# 3. API work
curl https://your-backend.railway.app/api/compositions/
# Должен вернуть JSON массив

# 4. CORS работает
# Из браузера (F12 → Console):
fetch('https://your-backend.railway.app/api/blog/')
  .then(r => r.json())
  .then(d => console.log(d))
# Should work без CORS ошибок

# 5. Admin login
curl -X POST https://your-backend.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
# Should return token
```

---

## Rollback Plan

### Если deployment не удался

**Step 1: Vercel Rollback**
1. Vercel Dashboard → Project Settings
2. Deployments tab
3. Select previous working deployment
4. Click "Promote to Production"

**Step 2: Railway Rollback**
1. Railway Dashboard → Deployments tab
2. Select previous working deployment
3. Click "Redeploy"

**Step 3: Database Rollback**
```bash
# Restore from backup if data was corrupted
pg_restore -d $DATABASE_URL backup.dump
```

---

## Performance Optimization

### Frontend
- [ ] Minification enabled (Vite auto)
- [ ] Images optimized
- [ ] CSS purging enabled (Tailwind auto)
- [ ] Assets cached (Vercel auto)

### Backend
- [ ] Connection pooling: `echo "pool_size = 10" >> .env`
- [ ] Query optimization (add indexes)
- [ ] Caching layer (Redis - future)

### Database
```sql
-- Add indexes for common queries
CREATE INDEX idx_blog_posts_slug ON blog_posts(slug);
CREATE INDEX idx_compositions_youtube_id ON compositions(youtube_id);
CREATE INDEX idx_comments_blog_post_id ON comments(blog_post_id);
```

---

## Security Checklist

- [ ] HTTPS enabled (auto on Vercel/Railway)
- [ ] CORS restricted to frontend domain only
- [ ] SQL Injection prevention (SQLAlchemy ORM - safe by default)
- [ ] XSS prevention (Vue escapes by default)
- [ ] CSRF tokens (if form handling)
- [ ] Password hashing (bcrypt - TODO in auth.py)
- [ ] Rate limiting (TODO in FastAPI)
- [ ] Regular dependency updates
  ```bash
  pip list --outdated
  npm outdated
  ```

---

## Go-Live Announcement Checklist

- [ ] Create social media post
- [ ] Send email to friends/beta users
- [ ] Update CV/portfolio
- [ ] Share on composer forums/communities
- [ ] Monitor for issues after launch

---

## Continuous Deployment (Auto Deployment)

### GitHub Actions Setup (Auto deploy on push)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
      
      # Railway auto-deploys on git push
```

---

## Emergency Contacts & Procedures

### If site is down

**Time to respond:** < 5 minutes

```
1. Check HTTP status (downfoyer.com)
2. Check Railway/Vercel dashboards
3. Check error logs
4. Check database status
5. If data issue - restore from backup
6. If code issue - rollback to previous deployment
7. Communicate status to users
```

---

## Next Steps After Launch

- [ ] Set up analytics (Google Analytics)
- [ ] Set up error tracking (Sentry, Rollbar)
- [ ] Set up monitoring (UptimeRobot)
- [ ] Plan regular maintenance windows
- [ ] Plan feature releases (biweekly?)
- [ ] Community feedback mechanism

---

**Deployment Date:** _________________
**Deployed By:** _________________
**Notes:** 

---

**Last Updated:** September 24, 2024
