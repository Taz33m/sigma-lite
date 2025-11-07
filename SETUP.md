# SigmaLite Setup Guide

This guide will walk you through setting up SigmaLite on your local machine.

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **PostgreSQL** 14+
- **Redis** (optional, for caching)

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd SigmaLite
```

### 2. Backend Setup

#### Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sigmalite

# JWT Secret (generate a secure random string)
SECRET_KEY=your-secret-key-here

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

#### Set Up Database

```bash
# Create PostgreSQL database
createdb sigmalite

# Or using psql
psql -U postgres
CREATE DATABASE sigmalite;
\q

# Run migrations
alembic upgrade head
```

#### Start Backend Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

#### Start Development Server

```bash
npm run dev
```

The frontend will be available at http://localhost:5173

## Testing

### Backend Tests

```bash
cd backend
pytest
pytest --cov=app  # With coverage
```

### Frontend Tests

```bash
cd frontend
npm test
npm run test:coverage
```

## Database Migrations

### Create a New Migration

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## Production Deployment

### Backend (Render)

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from `.env`
5. Create a PostgreSQL database and link it

### Frontend (Vercel)

1. Install Vercel CLI: `npm i -g vercel`
2. Build and deploy:
   ```bash
   cd frontend
   npm run build
   vercel --prod
   ```
3. Set environment variables in Vercel dashboard

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Check connection
psql -U postgres -d sigmalite
```

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

### Module Not Found Errors

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### CORS Issues

Ensure `ALLOWED_ORIGINS` in backend `.env` includes your frontend URL.

## Development Tips

### Hot Reload

Both backend and frontend support hot reload:
- Backend: `--reload` flag in uvicorn
- Frontend: Vite's built-in HMR

### API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

### Database GUI

Use tools like:
- **pgAdmin**: GUI for PostgreSQL
- **DBeaver**: Universal database tool
- **TablePlus**: Modern database client

### VS Code Extensions

Recommended extensions:
- Python
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- PostgreSQL

## Next Steps

1. **Create your first user**: Visit http://localhost:5173/register
2. **Upload a dataset**: Use the dashboard to upload a CSV file
3. **Explore data**: View and filter your dataset
4. **Create visualizations**: Build charts from your data

## Support

For issues and questions:
- Check the [README](README.md)
- Review [API Documentation](http://localhost:8000/docs)
- Open an issue on GitHub

---

**Happy coding! 🚀**
