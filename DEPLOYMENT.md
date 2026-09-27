"""
Deployment Guide for Allegro

## Backend Deployment (Railway/Render)

### Option 1: Railway (Recommended for simplicity)

1. Sign up at railway.app
2. Connect your GitHub repository
3. Railway automatically detects Python and creates services
4. Set environment variables:
   - DATABASE_URL: Provided by Railway PostgreSQL
   - SECRET_KEY: Generate a secure key
   - YOUTUBE_API_KEY: From Google Console
   - FRONTEND_URL: Your Vercel domain

5. Deploy via git push

### Option 2: Render

1. Sign up at render.com
2. Click "New+" → "Web Service"
3. Connect GitHub repository
4. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Add PostgreSQL database
6. Set environment variables

## Frontend Deployment (Vercel)

1. Sign up at vercel.com
2. Import your GitHub repository
3. Framework preset: Vite
4. Build settings are auto-detected from vite.config.js
5. Environment variables:
   - VITE_API_URL: Your backend URL (e.g., https://your-backend.railway.app)
6. Deploy

## Local Development with Docker

### Start everything locally:

```bash
docker-compose up
```

This starts:
- PostgreSQL on localhost:5432
- Backend on localhost:8000
- Frontend on localhost:5173

### Database Setup:

```bash
docker-compose exec backend alembic upgrade head
```

## Production Checklist

- [ ] Set strong SECRET_KEY
- [ ] Enable HTTPS
- [ ] Set DEBUG=False in production
- [ ] Create admin user with strong password
- [ ] Backup database regularly
- [ ] Set up monitoring/logging
- [ ] Configure CORS properly
- [ ] Set up SSL certificates
"""
