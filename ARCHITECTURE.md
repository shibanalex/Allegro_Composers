# Allegro - Architecture & Development Guide

## DDD Architecture Overview

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │
├─────────────────────────────────────┤
│    Application Layer (Services)     │
│   - CompositionService              │
│   - BlogService                     │
│   - CommentService                  │
│   - WorkshopService                 │
├─────────────────────────────────────┤
│      Domain Layer (Entities)        │
│   ┌──────────┬────────┬───────┐      │
│   │Composition│ Blog   │Comment │     │
│   │Workshop  │ Admin  │        │      │
│   └──────────┴────────┴───────┘      │
├─────────────────────────────────────┤
│   Infrastructure Layer (DB, APIs)   │
│   - PostgreSQL Database             │
│   - YouTube API Integration         │
│   - JWT Authentication              │
└─────────────────────────────────────┘
```

## Domain Description

### 1. **Compositions Domain** 
- **Purpose**: Store and display musical compositions
- **Entities**: Composition (YouTube video info)
- **Key Features**: 
  - Auto-sync with YouTube channel
  - Featured compositions support
  - Metadata caching

### 2. **Workshop Domain**
- **Purpose**: Document creative process
- **Entities**: WorkshopPost
- **Features**:
  - Multiple images per post
  - File attachments (MIDI, docs)
  - Timeline-based documentation

### 3. **Blog Domain**
- **Purpose**: Share thoughts and essays
- **Entities**: BlogPost
- **Features**:
  - Slug-based URLs
  - Publishing schedule
  - View counting

### 4. **Comments Domain**
- **Purpose**: Community engagement
- **Entities**: Comment
- **Features**:
  - Anonymous comments
  - Moderation support
  - Nested comments (future)

### 5. **Admin Domain**
- **Purpose**: Content management
- **Entities**: AdminUser
- **Features**:
  - JWT authentication
  - Role-based access (future)
  - Audit logging (future)

## Frontend Architecture

```
src/
├── views/        # Page components
├── components/   # Reusable components
├── router/       # Vue Router config
├── stores/       # Pinia state management
├── api/          # API integration
└── assets/       # Images, styles
```

## API Endpoints

```
# Compositions
GET    /api/compositions/          - List all
GET    /api/compositions/{id}      - Get one
POST   /api/compositions/          - Create (admin)

# Blog
GET    /api/blog/                  - List posts
GET    /api/blog/{slug}            - Get post
POST   /api/blog/                  - Create (admin)

# Workshop
GET    /api/workshop/              - List posts
POST   /api/workshop/              - Create (admin)

# Comments
GET    /api/comments/post/{id}     - Get comments
POST   /api/comments/              - Create comment

# Auth
POST   /api/auth/login             - Login admin
POST   /api/auth/verify            - Verify token
```

## Database Schema

### compositions
- id (PK)
- youtube_id (UNIQUE)
- title
- description
- thumbnail_url
- duration
- published_at
- created_at, updated_at
- is_featured

### blog_posts
- id (PK)
- title
- slug (UNIQUE)
- content
- excerpt
- author
- created_at, updated_at
- published_at
- is_published
- view_count

### workshop_posts
- id (PK)
- title
- description
- image_urls (JSON)
- file_urls (JSON)
- created_at, updated_at
- is_published

### comments
- id (PK)
- blog_post_id (FK)
- author_name
- author_email
- content
- created_at
- is_approved
- is_anonymous

### admin_users
- id (PK)
- username (UNIQUE)
- email (UNIQUE)
- hashed_password
- is_active
- created_at
- last_login

## Scalability Path

### Current: Monolith
✅ Simple deployment
✅ Easy development
✅ Sufficient for <1000 users

### Future: Microservices
- Extract Workshop (file handling) → Separate service
- Extract YouTube sync → Background worker
- Separate auth service
- Message queue for notifications

### Future: Social Network
- User profiles
- Following/followers
- Notifications
- Recommendations
- Collaborative features

---

**Next Steps:**
1. Set up PostgreSQL locally
2. Run backend: `python main.py`
3. Run frontend: `npm run dev`
4. Create admin account
5. Add initial content
"""
