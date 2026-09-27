# Development Setup & Contributing Guide

---

## Локальная разработка

### Prerequisites

- Python 3.10+ (проверить: `python --version`)
- Node.js 18+ (проверить: `node --version`)
- PostgreSQL 12+ (проверить: `psql --version`)
- Git

### Первый раз

```bash
# 1. Клонировать
git clone https://github.com/your-repo/Allegro.git
cd Allegro

# 2. Настроить Backend
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# 3. Настроить Frontend
cd ../frontend
npm install

# 4. Setup Database
# Убедиться что PostgreSQL запущена
# Создать базу данных
psql -U postgres
CREATE DATABASE allegro_db;
\q

# В терминале backend:
# SQLAlchemy создаст таблицы при первом запуске
```

### Повседневная разработка

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
python main.py
# http://localhost:8000

# Terminal 2 - Frontend
cd frontend
npm run dev
# http://localhost:5173
```

### Вспомогательные команды

```bash
# Работа с БД
psql -U postgres -d allegro_db
\dt                                    # List tables
SELECT * FROM compositions;            # Query data
\q                                     # Exit

# Смотрение логов
tail -f /tmp/allegro.log              # Linux/Mac
Get-Content -Tail 10 -Wait allegro.log # Windows

# Тестирование
cd backend
pytest                                 # Run all tests
pytest -v                              # Verbose
pytest tests/test_api.py               # Specific file
pytest -k "test_login"                 # Specific test

# Зависимости
pip freeze > requirements.txt          # Export pip deps
npm list                               # List npm deps
npm outdated                           # Check for updates
```

---

## Кодовые стандарты

### Backend (Python)

**PEP 8 - Style Guide**

```python
# ✅ Good
def get_composition(composition_id: int) -> Optional[Composition]:
    """Get a composition by ID."""
    return db.query(Composition).filter(
        Composition.id == composition_id
    ).first()

# ❌ Bad
def getComposition(composition_id):
    comp = db.query(Composition).filter(Composition.id==composition_id).first()
    return comp
```

**Naming Conventions:**
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `SCREAMING_SNAKE_CASE`
- Private variables: `_leading_underscore`

**Type Annotations (обязательно):**
```python
from typing import Optional, List

def create_post(db: Session, post: BlogPostCreate) -> BlogPost:
    """Create a new blog post."""
    pass

def get_posts(db: Session, limit: int = 10) -> List[BlogPost]:
    """Get multiple blog posts."""
    pass
```

**Docstrings:**
```python
def get_composition(composition_id: int) -> Optional[Composition]:
    """
    Retrieve a composition by ID.
    
    Args:
        composition_id: The ID of the composition to retrieve
        
    Returns:
        The Composition object if found, None otherwise
        
    Raises:
        HTTPException: If composition not found (404)
    """
    pass
```

**Code Formatting:**
```bash
# Auto-format with Black
black app/

# Check style with Flake8
flake8 app/

# Sort imports with isort
isort app/
```

### Frontend (JavaScript/Vue)

**ESLint Regulations**

```javascript
// ✅ Good
const getCompositions = async (skip = 0, limit = 10) => {
  try {
    const response = await axios.get('/api/compositions/', {
      params: { skip, limit }
    })
    return response.data
  } catch (error) {
    console.error('Failed to fetch compositions:', error)
    throw error
  }
}

// ❌ Bad
const comp = async () => {
  let data = await axios.get('/api/compositions/')
  return data
}
```

**Vue Conventions:**

```vue
<!-- ✅ Good -->
<template>
  <div class="compositions-grid">
    <CompositionCard 
      v-for="composition in compositions" 
      :key="composition.id" 
      :composition="composition"
      @click="handleSelect"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import CompositionCard from '@/components/CompositionCard.vue'
import { getCompositions } from '@/api/compositions'

const compositions = ref([])
const loading = ref(false)

const featured = computed(() => 
  compositions.value.filter(c => c.is_featured)
)

const handleSelect = (id) => {
  // Handle selection
}

onMounted(async () => {
  loading.value = true
  try {
    compositions.value = await getCompositions()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.compositions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
}
</style>
```

**Naming:**
- Components: `PascalCase` (CompositionCard.vue)
- Functions: `camelCase` (getCompositions)
- Constants: `SCREAMING_SNAKE_CASE` (API_URL)
- CSS classes: `kebab-case` (composition-card)

---

## Git Workflow

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting
- `refactor` - Code refactoring
- `perf` - Performance improvement
- `test` - Tests
- `chore` - Build, dependencies

**Examples:**

```
feat(compositions): add YouTube auto-sync

- Integrate YouTube API
- Auto-fetch new videos weekly
- Show thumbnail and duration

Closes #123
```

```
fix(blog): prevent double submission

If user double-clicks submit button, only create one post

Fixes #456
```

```
docs: update API reference

Add examples for authentication header
```

### Branch Naming

```
feature/youtube-sync
bugfix/comment-validation
docs/setup-guide
refactor/database-layer
```

### Pull Request Checklist

- [ ] Code follows style guides
- [ ] Tests pass (`pytest`, `npm run lint`)
- [ ] Documentation updated
- [ ] No console errors
- [ ] Database migrations included (if any)
- [ ] Backend and frontend builds successfully

---

## Testing

### Backend (pytest)

```bash
cd backend
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::test_get_compositions

# Run with coverage
pytest --cov=app tests/
```

**Test Structure:**
```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_compositions():
    """Test getting compositions."""
    response = client.get("/api/compositions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.parametrize("skip,limit", [(0, 10), (10, 5)])
def test_pagination(skip, limit):
    """Test composition pagination."""
    response = client.get(f"/api/compositions/?skip={skip}&limit={limit}")
    assert response.status_code == 200
```

### Frontend (Vitest/Jest)

```bash
cd frontend
npm install --save-dev vitest

# Run tests
npm run test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage
```

**Test Example:**
```javascript
// tests/compositionStore.spec.js
import { describe, it, expect, beforeEach } from 'vitest'
import { defineStore } from 'pinia'

describe('Composition Store', () => {
  it('should fetch compositions', async () => {
    // Test implementation
  })
})
```

---

## Debugging

### Backend Debug

**VSCode Debug Configuration:**
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "jinja": true,
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

**Breakpoints & Logging:**
```python
import logging

logger = logging.getLogger(__name__)

@router.get("/api/compositions/")
def get_compositions(db: Session = Depends(get_db)):
    logger.info("Fetching compositions")
    logger.debug(f"Database session: {db}")
    
    compositions = db.query(Composition).all()
    logger.info(f"Found {len(compositions)} compositions")
    
    return compositions
```

**PDB (Python Debugger):**
```python
import pdb

@router.post("/api/blog/")
def create_post(post: BlogPostCreate):
    pdb.set_trace()  # Execution will stop here
    # Now use: 
    # n - next line
    # s - step into
    # c - continue
    # p variable - print variable
```

### Frontend Debug

**Chrome DevTools:**
- F12 → Console (logs)
- F12 → Network (API calls)
- F12 → Application (localStorage, cookies)
- F12 → Vue DevTools (component state)

**VSCode Debugger:**
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "chrome",
      "request": "launch",
      "name": "Launch Chrome",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/frontend"
    }
  ]
}
```

---

## Performance Profiling

### Backend

```bash
# Memory profiling
pip install memory-profiler
python -m memory_profiler app/main.py

# CPU profiling
pip install cProfile
python -m cProfile -s cumulative main.py
```

### Frontend

```bash
# Chrome DevTools → Performance tab
# 1. Click Record
# 2. Interact with app
# 3. Click Stop
# 4. Analyze timeline

# Lighthouse (Chrome)
F12 → Lighthouse → Generate report
```

---

## Useful Development Extensions

### VSCode Extensions

```
Python
  - ms-python.python
  - ms-python.vscode-pylance
  
Backend
  - ms-python.debugpy
  
Frontend
  - Vue Language Features (Volar)
  - ESLint
  - Prettier - Code formatter
  
Database
  - PostgreSQL
  
General
  - GitLens
  - REST Client (to test API)
```

**Install them:**
```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
# ... etc
```

### Chrome Extensions

```
- Vue DevTools
- Redux DevTools
- REST Client
```

---

## Documentation Requirements

Every major feature should include:

1. **Code comments** - Why, not what
2. **Docstrings** - Function/class purpose
3. **README** - How to use
4. **API docs** - Endpoints, parameters, responses
5. **Examples** - Real usage examples

---

**Last Updated:** September 24, 2024
