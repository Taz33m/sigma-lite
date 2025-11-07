# 🚀 Quick Test Guide (No Auth Required!)

Get SigmaLite running in **3 minutes** without any authentication!

## ✅ Authentication is Already Disabled!

The project is pre-configured to skip login/register. Just start the servers!

## Step 1: Start Backend (1 min)

```bash
cd backend
source venv/bin/activate  # Already done if you followed setup
uvicorn app.main:app --reload
```

✅ Backend running at http://localhost:8000

## Step 2: Start Frontend (1 min)

```bash
# New terminal
cd frontend
npm run dev
```

✅ Frontend running at http://localhost:5173

## Step 3: Use the App! (1 min)

1. **Open** http://localhost:5173 in your browser
2. **Go directly to dashboard** - No login needed! 🎉
3. **Upload a CSV** and start exploring

## 📊 Test with Sample Data

Create a quick test file:

```bash
cat > sample.csv << EOF
name,age,city,salary,department
Alice,28,New York,75000,Engineering
Bob,35,San Francisco,95000,Engineering
Charlie,42,Chicago,68000,Sales
Diana,31,Boston,82000,Marketing
Eve,29,Seattle,78000,Engineering
Frank,38,Austin,71000,Sales
Grace,33,Denver,85000,Marketing
Henry,45,Portland,92000,Engineering
EOF
```

Then upload `sample.csv` in the dashboard!

## 🔄 Want to Enable Authentication?

Edit these files:

**backend/.env:**
```env
DISABLE_AUTH=False
```

**frontend/.env:**
```env
VITE_DISABLE_AUTH=false
```

Then restart both servers and register at http://localhost:5173/register

## 🎯 What You Can Test

With auth disabled, you can immediately:

✅ Upload CSV files  
✅ View data in spreadsheet format  
✅ Filter and sort columns  
✅ Create visualizations  
✅ Save sheets and charts  
✅ Test all features without friction  

All data is saved under a demo user account automatically!

## 📝 Notes

- All operations use a demo user (`demo_user`)
- Data persists in SQLite database
- Perfect for demos, testing, and development
- **Never use in production!**

---

**Enjoy testing SigmaLite! 🎉**
