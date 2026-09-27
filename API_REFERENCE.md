# API Reference - Полный справочник

**Версия API:** v1.0  
**Base URL:** `http://localhost:8000` (разработка) / `https://yourdomain.com` (продакшн)

---

## Таблица всех endpoint'ов

| Метод | Путь | Описание | Auth | Rate Limit |
|-------|------|---------|------|-----------|
| GET | `/health` | Проверка здоровья | ❌ | Нет |
| **COMPOSITIONS** |
| GET | `/api/compositions/` | Все произведения | ❌ | 100/min |
| GET | `/api/compositions/{id}` | Одно произведение | ❌ | 100/min |
| POST | `/api/compositions/` | Создать произведение | ✅ | 10/min |
| **BLOG** |
| GET | `/api/blog/` | Список постов | ❌ | 100/min |
| GET | `/api/blog/{slug}` | Пост по slug | ❌ | 100/min |
| POST | `/api/blog/` | Создать пост | ✅ | 10/min |
| **WORKSHOP** |
| GET | `/api/workshop/` | Все workshop посты | ❌ | 100/min |
| POST | `/api/workshop/` | Создать workshop пост | ✅ | 10/min |
| **COMMENTS** |
| GET | `/api/comments/post/{id}` | Комментарии к посту | ❌ | 100/min |
| POST | `/api/comments/` | Написать комментарий | ❌ | 10/min |
| **AUTHENTICATION** |
| POST | `/api/auth/login` | Вход админа | ❌ | 5/min |
| POST | `/api/auth/verify` | Проверить токен | ❌ | 20/min |

---

## Детальные API docs

### Health Check

```
GET /health
```

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "app": "Allegro"
}
```

---

### Compositions (Произведения)

#### Получить все произведения

```
GET /api/compositions/?skip=0&limit=10
```

**Query Parameters:**
| Параметр | Type | Default | Описание |
|----------|------|---------|---------|
| `skip` | int | 0 | Пропустить N записей (pagination) |
| `limit` | int | 10 | Максимально вернуть записей |

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "youtube_id": "dQw4w9WgXcQ",
    "title": "Symphony No. 1 in D Major",
    "description": "A grand orchestral piece",
    "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "duration": 480,
    "published_at": "2024-01-15T10:30:00",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00",
    "is_featured": true
  }
]
```

---

#### Получить одно произведение

```
GET /api/compositions/1
```

**Path Parameters:**
| Параметр | Type | Описание |
|----------|------|---------|
| `id` | int | ID произведения |

**Response:** `200 OK` (как выше)

**Ошибки:**
| Код | Сообщение |
|-----|-----------|
| 404 | Composition not found |

---

#### Создать произведение

```
POST /api/compositions/
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "title": "New Symphony",
  "description": "A beautiful new work",
  "youtube_id": "VIDEO_ID"
}
```

**Response:** `201 Created`
```json
{
  "id": 2,
  "youtube_id": "VIDEO_ID",
  "title": "New Symphony",
  "description": "A beautiful new work",
  "thumbnail_url": null,
  "duration": null,
  "published_at": null,
  "created_at": "2024-09-24T12:00:00",
  "updated_at": "2024-09-24T12:00:00",
  "is_featured": false
}
```

**Ошибки:**
| Код | Сообщение |
|-----|-----------|
| 401 | Not authenticated |
| 422 | Validation error |

---

### Blog Posts (Блог)

#### Получить все посты

```
GET /api/blog/?skip=0&limit=10
```

**Query Parameters:**
| Параметр | Type | Default |
|----------|------|---------|
| `skip` | int | 0 |
| `limit` | int | 10 |

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "title": "My Creative Process",
    "slug": "my-creative-process",
    "content": "Full article text...",
    "excerpt": "How I create...",
    "author": "Composer",
    "created_at": "2024-01-20T14:00:00",
    "updated_at": "2024-01-20T14:00:00",
    "published_at": "2024-01-20T14:00:00",
    "is_published": true,
    "view_count": 42
  }
]
```

---

#### Получить пост по slug

```
GET /api/blog/my-creative-process
```

**Path Parameters:**
| Параметр | Type | Описание |
|----------|------|---------|
| `slug` | string | URL-safe название поста |

**Notes:**
- Просмотр счетчика увеличивается автоматически

**Response:** `200 OK` (как выше)

**Ошибки:**
| Код | Сообщение |
|-----|-----------|
| 404 | Post not found |

---

#### Создать блог пост

```
POST /api/blog/
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "title": "Latest Thoughts on Music",
  "slug": "latest-thoughts-music",
  "content": "Full article content here...",
  "excerpt": "Short summary of the article"
}
```

**Validation Rules:**
- `title`: 1-255 characters
- `slug`: 1-255 characters, должен быть уникален, только буквы/цифры/-_
- `content`: не пусто
- `excerpt`: опционально, макс 512 characters

**Response:** `201 Created`
```json
{
  "id": 5,
  "title": "Latest Thoughts on Music",
  "slug": "latest-thoughts-music",
  "content": "Full article content here...",
  "excerpt": "Short summary of the article",
  "author": "Composer",
  "created_at": "2024-09-24T15:00:00",
  "updated_at": "2024-09-24T15:00:00",
  "published_at": "2024-09-24T15:00:00",
  "is_published": true,
  "view_count": 0
}
```

**Ошибки:**
| Код | Сообщение | Решение |
|-----|-----------|---------|
| 401 | Not authenticated | Добавить token в Authorization header |
| 422 | Validation error | Проверить формат данных |

---

### Workshop Posts (Процесс создания)

#### Получить все workshop посты

```
GET /api/workshop/?skip=0&limit=10
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "title": "Creating Symphony Movement 1",
    "description": "Process and thoughts...",
    "image_urls": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg"
    ],
    "file_urls": [
      "https://example.com/draft1.midi",
      "https://example.com/notes.pdf"
    ],
    "created_at": "2024-09-20T10:00:00",
    "updated_at": "2024-09-20T10:00:00",
    "is_published": true
  }
]
```

---

#### Создать workshop пост

```
POST /api/workshop/
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "title": "Composing the Final Movement",
  "description": "Detailed process description...",
  "image_urls": [
    "https://cdn.example.com/temp_image1.jpg",
    "https://cdn.example.com/temp_image2.jpg"
  ],
  "file_urls": [
    "https://cdn.example.com/composition.midi",
    "https://cdn.example.com/annotations.pdf"
  ]
}
```

**Notes:**
- URLs должны быть полные HTTP(S) URLs
- Вы отвечаете за хостинг файлов (Google Drive, Dropbox, AWS S3 и т.д.)
- Максимум 10 файлов на пост (рекомендуется)

**Response:** `201 Created`

---

### Comments (Комментарии)

#### Получить комментарии к посту

```
GET /api/comments/post/1
```

**Path Parameters:**
| Параметр | Type | Описание |
|----------|------|---------|
| `id` | int | ID блог поста |

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "blog_post_id": 1,
    "author_name": "John Doe",
    "author_email": null,
    "content": "Amazing article, thank you!",
    "created_at": "2024-09-22T16:30:00",
    "is_approved": true,
    "is_anonymous": true
  },
  {
    "id": 2,
    "blog_post_id": 1,
    "author_name": "Jane Smith",
    "author_email": "jane@example.com",
    "content": "Would love to know more about your technique",
    "created_at": "2024-09-23T09:15:00",
    "is_approved": true,
    "is_anonymous": false
  }
]
```

---

#### Написать комментарий

```
POST /api/comments/
```

**Request Body:**
```json
{
  "blog_post_id": 1,
  "author_name": "Your Name",
  "author_email": "optional@email.com",
  "content": "Great post! I really enjoyed reading this.",
  "is_anonymous": true
}
```

**Validation Rules:**
- `author_name`: 1-255 characters, обязательно
- `author_email`: валидный email, опционально
- `content`: 1-5000 characters, обязательно
- `is_anonymous`: boolean, default true

**Response:** `201 Created`
```json
{
  "id": 3,
  "blog_post_id": 1,
  "author_name": "Your Name",
  "author_email": null,
  "content": "Great post! I really enjoyed reading this.",
  "created_at": "2024-09-24T12:30:00",
  "is_approved": true,
  "is_anonymous": true
}
```

**Ошибки:**
| Код | Сообщение |
|-----|-----------|
| 404 | Blog post not found |
| 422 | Validation error |

---

### Authentication (Аутентификация)

#### Вход админа

```
POST /api/auth/login
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "your_password"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Ошибки:**
| Код | Сообщение | Решение |
|-----|-----------|---------|
| 401 | Invalid credentials | Проверить username/password |
| 422 | Validation error | Проверить формат JSON |

---

#### Проверить токен

```
POST /api/auth/verify
```

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** `200 OK`
```json
{
  "valid": true,
  "user": "admin"
}
```

**Response (invalid token):** `401 Unauthorized`
```json
{
  "detail": "Invalid token"
}
```

---

## Аутентификация

### JWT Token типы

1. **Access Token** - Используется для API запросов (30 минут по умолчанию)
2. **Refresh Token** - Для получения нового Access Token (TODO)

### Использование токена

**Способ 1: Authorization Header (РЕКОМЕНДУЕТСЯ)**
```
Authorization: Bearer {access_token}
```

**Способ 2: Cookie (для браузера)**
```
Cookie: access_token={access_token}
```

### Примеры

**cURL:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/blog/create \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{
       "title": "My Post",
       "slug": "my-post",
       "content": "Content here"
     }'
```

**JavaScript/Fetch:**
```javascript
const token = localStorage.getItem('access_token')

fetch('/api/blog/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'My Post',
    slug: 'my-post',
    content: 'Content here'
  })
})
```

**Axios:**
```javascript
const token = localStorage.getItem('access_token')

axios.defaults.headers.common['Authorization'] = `Bearer ${token}`

axios.post('/api/blog/', {
  title: 'My Post',
  slug: 'my-post',
  content: 'Content here'
})
```

---

## Error Handling

### Стандартные HTTP коды

| Код | Значение | Действие |
|-----|----------|----------|
| 200 | OK | Успешный запрос |
| 201 | Created | Ресурс создан |
| 400 | Bad Request | Ошибка в формате запроса |
| 401 | Unauthorized | Нужна аутентификация |
| 403 | Forbidden | Недостаточно прав |
| 404 | Not Found | Ресурс не найден |
| 422 | Validation Error | Ошибка валидации данных |
| 500 | Internal Server Error | Ошибка сервера |

### Error Response Format

```json
{
  "detail": "Error description"
}
```

### Validation Error Response

```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Rate Limiting

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Public GET | 100 | 1 минута |
| Public POST (comments) | 10 | 1 минута |
| Admin POST | 10 | 1 минута |
| Auth (login) | 5 | 1 минута |

**Header ответа:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1632408300
```

---

## Versioning

- **Current Version:** v1
- **API Path:** `/api/v1/` (future)
- **Backward Compatibility:** Поддерживается на текущей версии

---

**Last Updated:** September 24, 2024  
**API Stability:** ⚠️ Beta (Changes possible)
