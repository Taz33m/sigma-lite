# SigmaLite Quick Start Guide 🚀

Get SigmaLite running in under 10 minutes!

## Prerequisites Check

```bash
# Check Node.js (need 18+)
node --version

# Check Python (need 3.11+)
python3 --version
```

**Note:** No PostgreSQL needed! We use SQLite for easy local development.

## 🎯 Fast Setup (4 Steps)

### Step 1: Skip! (No Database Setup Needed)

✅ **SQLite is file-based - no installation required!**

### Step 2: Backend Setup (2 min)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (already done - uses SQLite by default!)
cp .env.example .env

# Create database tables
mkdir -p alembic/versions
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

Backend running at: **http://localhost:8000** ✅

### Step 3: Frontend Setup (2 min)

```bash
# Open new terminal
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```

Frontend running at: **http://localhost:5173** ✅

### Step 4: Test the Application (1 min)

1. Open http://localhost:5173
2. Click "Sign up"
3. Create an account
4. Upload a CSV file
5. Explore your data!

### Step 5: Verify Everything Works

```bash
# Test backend
curl http://localhost:8000/health

# Expected response: {"status":"healthy","version":"1.0.0"}
```

## 🎉 You're Done!

Your SigmaLite instance is now running!

## 📊 Sample Data

Don't have a CSV? Create a sample file:

```bash
cat > sample.csv << EOF
name,age,city,salary
Alice,28,New York,75000
Bob,35,San Francisco,95000
Charlie,42,Chicago,68000
Diana,31,Boston,82000
EOF
```

Upload this file to test the platform!

## 🔧 Common Issues

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

### Database Connection Failed

```bash
# Check PostgreSQL is running
brew services start postgresql  # macOS
sudo service postgresql start   # Linux

# Verify connection
psql -U postgres -d sigmalite
```

### Module Not Found

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
rm -rf node_modules
npm install
```

## 📚 Next Steps

- **API Docs**: http://localhost:8000/docs
- **Full Setup Guide**: See [SETUP.md](SETUP.md)
- **PRD**: See [docs/PRD.md](docs/PRD.md)
- **README**: See [README.md](README.md)

## 🆘 Need Help?

1. Check the logs in your terminal
2. Review [SETUP.md](SETUP.md) for detailed instructions
3. Visit API docs at http://localhost:8000/docs
4. Open an issue on GitHub

---

**Happy data exploring! 📊✨**
