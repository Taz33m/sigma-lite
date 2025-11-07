# SigmaLite 📊

A collaborative, web-based data exploration and visualization platform that democratizes analytics through spreadsheet-like interactions and intuitive dashboards.

![SigmaLite](https://img.shields.io/badge/status-active-success.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🎯 Overview

SigmaLite bridges the simplicity of spreadsheets with the power of modern data systems, enabling users to:
- Upload and explore datasets interactively
- Create visualizations with drag-and-drop simplicity
- Collaborate in real-time with team members
- Build dashboards without writing code

## ✨ Features

### Core Functionality
- **📁 Data Upload**: Support for CSV files up to 10MB
- **📊 Spreadsheet Interface**: Editable grid with sorting, filtering, and formula support
- **📈 Interactive Visualizations**: Line, bar, scatter, and pie charts with real-time updates
- **👥 Real-Time Collaboration**: Multi-user editing with live cursors and WebSocket sync
- **🔐 Secure Authentication**: JWT-based auth with user workspaces
- **💾 Persistent Storage**: Save and reload sheets and dashboards

### Technical Highlights
- Type-safe TypeScript frontend
- High-performance data virtualization for large datasets
- RESTful API with query endpoints
- PostgreSQL database with optimized queries
- Redis caching layer for performance
- Comprehensive test coverage

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  • TypeScript • Tailwind CSS • Chart.js • AG Grid       │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API / WebSocket
┌───────────────────────▼─────────────────────────────────┐
│                  Backend (FastAPI)                       │
│  • Python 3.11+ • JWT Auth • WebSocket Manager          │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
┌───────▼────────┐            ┌────────▼────────┐
│   PostgreSQL   │            │     Redis       │
│   (Database)   │            │    (Cache)      │
└────────────────┘            └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL 14+
- Redis (optional, for caching)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/sigmalite.git
cd sigmalite
```

2. **Set up the backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

3. **Set up the frontend**
```bash
cd frontend
npm install

# Configure environment variables
cp .env.example .env
# Edit .env with your API URL

# Start the development server
npm run dev
```

4. **Access the application**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📁 Project Structure

```
SigmaLite/
├── frontend/                 # React + TypeScript frontend
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── services/        # API services
│   │   ├── store/           # State management
│   │   ├── types/           # TypeScript types
│   │   └── utils/           # Utility functions
│   ├── public/              # Static assets
│   └── package.json
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Core configuration
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── main.py         # Application entry point
│   ├── tests/              # Backend tests
│   └── requirements.txt
├── docs/                   # Documentation
│   ├── PRD.md             # Product Requirements Document
│   └── architecture.md    # Architecture details
└── README.md
```

## 🧪 Testing

### Frontend Tests
```bash
cd frontend
npm test                    # Run unit tests
npm run test:coverage      # Generate coverage report
```

### Backend Tests
```bash
cd backend
pytest                     # Run all tests
pytest --cov=app          # Run with coverage
```

## 📊 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login and get JWT token |
| `/api/datasets` | GET/POST | List or upload datasets |
| `/api/datasets/{id}` | GET/PUT/DELETE | Manage specific dataset |
| `/api/datasets/{id}/filter` | POST | Filter dataset |
| `/api/datasets/{id}/aggregate` | POST | Aggregate data |
| `/api/charts` | GET/POST | Create and list charts |
| `/ws/collaborate/{sheet_id}` | WebSocket | Real-time collaboration |

## 🎨 Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast builds
- **Tailwind CSS** for styling
- **shadcn/ui** for component library
- **AG Grid** for spreadsheet functionality
- **Chart.js** for visualizations
- **Zustand** for state management
- **React Query** for data fetching

### Backend
- **FastAPI** for high-performance API
- **SQLAlchemy** for ORM
- **Alembic** for migrations
- **PostgreSQL** for database
- **Redis** for caching
- **JWT** for authentication
- **WebSockets** for real-time features
- **Pydantic** for validation

## 🔒 Security

- JWT-based authentication with refresh tokens
- Password hashing with bcrypt
- Input sanitization and validation
- Rate limiting on API endpoints
- CORS configuration
- SQL injection prevention via ORM
- XSS protection

## 🚀 Deployment

### Frontend (Vercel)
```bash
cd frontend
npm run build
vercel --prod
```

### Backend (Render)
1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### Database (Render PostgreSQL)
1. Create a PostgreSQL instance on Render
2. Copy connection string to backend `.env`

## 📈 Performance Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Initial load (10K rows) | < 2s | ✅ |
| Chart render time | < 500ms | ✅ |
| API response time | < 200ms | ✅ |
| Test coverage | > 80% | ✅ |
| Concurrent users | 10+ | ✅ |

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [Sigma Computing](https://www.sigmacomputing.com/)
- Built as a demonstration of full-stack engineering capabilities
- Special thanks to the open-source community

## 📧 Contact

For questions or feedback, please open an issue or reach out to the maintainers.

---

**Built with ❤️ for democratizing data analytics**
