# Art Style Attribution Lab

![Banner](docs/banner.jpg)

Production-grade система атрибуции художественных стилей с использованием глубокого обучения, LLM и генеративного AI.

## Обзор

Полнофункциональная платформа для анализа изображений, которая классифицирует произведения искусства по 132 художникам, 27 стилям и 11 жанрам. Система генерирует детальные объяснения через LLM и создает новые изображения в обнаруженных стилях.

**Ключевые возможности:**
- Multi-head CNN классификация на базе MobileNetV2
- LLM-интеграция (OpenAI, OpenRouter, Ollama) для объяснений
- 5-модульная система глубокого анализа (цвет, композиция, сцена, техника, история)
- Генерация изображений через ComfyUI/Stable Diffusion
- Production-ready API с JWT auth, rate limiting, concurrent control
- Modern React SPA с Tailwind CSS

## Технический стек

**Backend:** FastAPI 0.104+, PostgreSQL 14+, SQLAlchemy 2.0, TensorFlow 2.15+, Pydantic 2.5+

**Frontend:** React 18.2, Vite 5.0, TailwindCSS 3.4, Axios, React Router 6.20, Framer Motion

**ML:** MobileNetV2 (ImageNet pretrained), 224x224 RGB input, Multi-head output (132+27+11 classes)

## Архитектура

```
React SPA (Vite) → FastAPI Backend → PostgreSQL / TensorFlow / External APIs
                                     ↓           ↓              ↓
                                  Database   ML Model    OpenAI/OpenRouter/ComfyUI
```

**Rate Limiting:**
- `/api/analyze`: 10 req/min
- `/api/generate`: 5 req/min
- `/api/deep-analysis/full`: 3 req/min
- Concurrent operation blocking (нельзя запускать анализ + генерацию одновременно)

**Security:**
- JWT authentication с bcrypt
- Magic number file validation
- CORS whitelist
- SQL injection protection via ORM
- Rate limiting per user

## Установка

### Требования
- Python 3.10+, Node.js 18+, PostgreSQL 14+, 8GB+ RAM

### Быстрый старт

**1. База данных:**
```sql
CREATE DATABASE art_style_db;
```

**2. Backend:**
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
copy .env.example .env
# Отредактировать .env (DATABASE_URL, SECRET_KEY, LLM_PROVIDER)
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**3. Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**4. ML модель:**
Скачать `wikiart_mobilenetv2_multihead.keras` и разместить в `ml/models/`

**5. (Опционально) ComfyUI:**
```bash
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
pip install -r requirements.txt
python main.py --listen 127.0.0.1 --port 8188
```

## Конфигурация (.env)

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/art_style_db

# Security (КРИТИЧНО!)
SECRET_KEY=<сгенерировать через: python -c "import secrets; print(secrets.token_urlsafe(32))">
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM (выбрать один)
LLM_PROVIDER=openrouter  # или openai, ollama, none
OPENROUTER_API_KEY=sk-or-v1-your-key
OPENROUTER_MODEL=anthropic/claude-3-haiku

# ML
ML_TOP_K=3
ML_INCLUDE_UNKNOWN_ARTIST=false

# ComfyUI (опционально)
COMFYUI_ENABLED=true
COMFYUI_BASE_URL=http://127.0.0.1:8188

# Upload
MAX_UPLOAD_SIZE=10485760  # 10MB
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Регистрация
- `POST /api/auth/login` - Вход (получить JWT)
- `POST /api/auth/guest` - Гостевой доступ

### Analysis
- `POST /api/analyze` - Анализ изображения (требует auth, 10/min)
- `POST /api/generate` - Генерация вариаций (требует auth, 5/min)

### Deep Analysis
- `GET /api/deep-analysis/full` - Полный анализ 5 модулей (требует auth, 3/min)
- `GET /api/deep-analysis/module/{name}` - Один модуль (требует auth, 10/min)

### History
- `GET /api/history` - История анализов
- `DELETE /api/history/{id}` - Удалить запись

**Swagger UI:** `http://localhost:8000/docs`

## Примеры использования

**Регистрация:**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "artist", "password": "SecurePass123!"}'
```

**Вход:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'
# Response: {"access_token": "...", "token_type": "bearer"}
```

**Анализ:**
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@painting.jpg"
```

**Response:**
```json
{
  "success": true,
  "top_artists": [
    {"artist_slug": "vincent-van-gogh", "probability": 0.85},
    {"artist_slug": "claude-monet", "probability": 0.08}
  ],
  "top_genres": [{"name": "landscape", "probability": 0.72}],
  "top_styles": [{"name": "Post_Impressionism", "probability": 0.65}],
  "explanation": {"text": "На основе анализа...", "source": "llm"}
}
```

## Особенности реализации

**Rate Limiting:** In-memory limiter с per-endpoint лимитами + блокировка одновременных тяжелых операций
**File Validation:** Magic number verification (PNG/JPEG/WebP/BMP), path traversal protection, size limits
**Deep Analysis:** 5-модульный pipeline с последовательными LLM вызовами (color → composition → scene → technique → historical → summary)
**LLM Abstraction:** Единый интерфейс для OpenAI/OpenRouter/Ollama с автоматическим fallback на stubs

Реализация:
- [backend/app/core/rate_limiter.py](backend/app/core/rate_limiter.py)
- [backend/app/core/file_validator.py](backend/app/core/file_validator.py)
- [backend/app/services/deep_analysis_service.py](backend/app/services/deep_analysis_service.py)

## Production Deployment

**Docker Compose:**
```yaml
services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: art_style_db
      POSTGRES_PASSWORD: ${DB_PASSWORD}
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://art_user:${DB_PASSWORD}@db/art_style_db
      SECRET_KEY: ${SECRET_KEY}
  frontend:
    build: ./frontend
    ports: ["80:80"]
```

**Nginx:**
```nginx
location /api { proxy_pass http://127.0.0.1:8000; }
location / { root /var/www/frontend/dist; try_files $uri /index.html; }
```

## ML Model

**Архитектура:** MobileNetV2 (ImageNet pretrained) → GlobalAvgPooling → 3x Dense → 3x Softmax
**Dataset:** WikiArt (80,000+ paintings)
**Classes:** 132 художника, 27 стилей, 11 жанров
**Training:** ~10 часов на RTX 3090, Adam optimizer, categorical crossentropy

**Поддерживаемые классы:** Vincent van Gogh, Claude Monet, Pablo Picasso, Rembrandt, Leonardo da Vinci, Salvador Dali, Илья Репин, Иван Айвазовский + 124 других художника. Стили: Impressionism, Post-Impressionism, Cubism, Baroque, Renaissance, Surrealism и др. Жанры: Portrait, Landscape, Still Life, Abstract и др.

Полный список: [ml/models/class_labels.json](ml/models/class_labels.json)

## Performance

**Benchmarks (CPU inference):**
- Image analysis: ~2-3 сек (ML только), ~5-8 сек (с LLM)
- Deep analysis: ~25-35 сек (5 модулей)
- Image generation: ~10-20 сек (ComfyUI + SD1.5)

GPU inference ускоряет ML в 5-10x.

## Troubleshooting

**Backend не запускается:**
- `ModuleNotFoundError: app` → проверить venv активирован
- `OperationalError: could not connect` → проверить PostgreSQL запущен и DATABASE_URL
- `ModuleNotFoundError: tensorflow` → `pip install tensorflow>=2.15.0`

**ML модель не найдена:**
- Загрузить `wikiart_mobilenetv2_multihead.keras` в `ml/models/`

**LLM не работает:**
- `LLM_PROVIDER=none` → stub responses (норма для тестирования)
- Проверить API ключи (OPENROUTER_API_KEY, OPENAI_API_KEY)
- Для Ollama: убедиться что запущен на `localhost:11434`

**ComfyUI fails:**
- Connection refused → запустить ComfyUI на порту 8188
- Timeout → увеличить COMFYUI_TIMEOUT
- No checkpoint → загрузить SD checkpoint в `ComfyUI/models/checkpoints/`

**Rate limit exceeded:**
- Error 429 → подождать 1 минуту
- Concurrent operation blocked → дождаться завершения текущей операции

## Безопасность

**КРИТИЧНО перед production:**
1. Сгенерировать криптостойкий SECRET_KEY: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Использовать сильные пароли БД
3. Настроить HTTPS
4. Ограничить CORS origins
5. Настроить firewall для PostgreSQL

**Реализовано:**
- JWT auth + bcrypt hashing
- SQL injection protection (ORM)
- File upload validation (magic numbers)
- Rate limiting + concurrent control
- CORS whitelist

## Лицензия

MIT License

## Контакты

- GitHub Issues: [создать issue](https://github.com/yourusername/art-style-attribution-lab/issues)
- API Docs: `http://localhost:8000/docs` (Swager)

---

**Версия:** 1.0.0
**Статус:** Production-ready (после security hardening)
