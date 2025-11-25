# Art Style Attribution Lab

Educational prototype for neural art attribution: a pipeline that classifies a painting's style with a CNN, explains the result with an LLM, and generates new images in similar styles via ComfyUI.

## 🏗️ Project Structure

```
art-style-attribution-lab/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Config, database, security
│   │   ├── models/         # SQLAlchemy models & Pydantic schemas
│   │   └── services/       # Business logic services
│   ├── alembic/            # Database migrations
│   ├── uploads/            # Uploaded images storage
│   └── requirements.txt
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── context/       # React context (auth)
│   │   └── pages/         # Page components
│   └── package.json
├── ml/                     # ML model and prediction
│   ├── models/            # Trained model files
│   └── predict_artists.py # Prediction module
└── docs/                   # Documentation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### 1. Database Setup

Create a PostgreSQL database:

```sql
CREATE DATABASE art_style_db;
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate
# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
copy .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## 🔧 Environment Variables

### Backend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/art_style_db` |
| `SECRET_KEY` | JWT signing key | `your-super-secret-key-change-in-production` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry time | `1440` (24 hours) |
| `DEBUG` | Enable debug mode | `false` |
| `MAX_UPLOAD_SIZE` | Max file size in bytes | `10485760` (10MB) |

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login and get token |

### Analysis

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/analyze` | Analyze image for art style | ✅ Required |

### Example: Analyze Image

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@your_image.jpg"
```

Response:

```json
{
  "success": true,
  "image_path": "/uploads/uuid.jpg",
  "top_artists": [
    {"index": 0, "artist_slug": "vincent-van-gogh", "probability": 0.85},
    {"index": 1, "artist_slug": "claude-monet", "probability": 0.08},
    {"index": 2, "artist_slug": "paul-cezanne", "probability": 0.04}
  ],
  "explanation": {
    "text": "Based on the analysis, this artwork shows...",
    "source": "stub"
  },
  "generated_thumbnails": [
    {"url": "https://...", "artist_slug": "vincent-van-gogh", "prompt": "..."}
  ]
}
```

## 🔐 Authentication Flow

1. **Register**: POST `/api/auth/register` with email, username, password
2. **Login**: POST `/api/auth/login` with email, password → receive JWT token
3. **Use token**: Add `Authorization: Bearer <token>` header to protected requests

## 🎨 Features

- **Art Style Classification**: Upload an image and get top-3 artist predictions using a MobileNetV2-based CNN
- **User Authentication**: Secure registration and login with JWT tokens
- **Explanation Generation**: (Stub) LLM-powered explanations for predictions
- **Style Variations**: (Stub) ComfyUI-generated images in similar styles

## 🛠️ Development

### API Documentation

When backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.
