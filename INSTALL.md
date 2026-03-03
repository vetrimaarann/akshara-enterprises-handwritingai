# HandwriteAI - Installation & Setup Guide

Complete step-by-step guide to install, configure, and run HandwriteAI locally.

---

## **Prerequisites**

Before starting, ensure you have:
- **Windows 10/11** (or Linux/Mac with Python 3.10+)
- **Python 3.10+** installed from https://www.python.org/
- **Git** installed from https://git-scm.com/
- **At least 2GB RAM** available (for model loading)
- **At least 3GB disk space** (for dependencies + ML models)
- **Internet connection** (for downloading models on first run)

### **Check Python Version**
```powershell
python --version
# Should output: Python 3.10.x or higher
```

---

## **Step 1: Clone the Repository**

```powershell
git clone https://github.com/vetrimaarann/akshara-enterprises-handwritingai.git
cd akshara-enterprises-handwritingai
```

---

## **Step 2: Create Virtual Environment**

Create a Python virtual environment to isolate dependencies:

```powershell
python -m venv venv
```

### **Activate Virtual Environment**

**Windows PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

You should see `(venv)` appear in your terminal prompt.

---

## **Step 3: Install All Dependencies**

Run this single command to install everything:

```powershell
pip install -r requirements.txt
```

### **What Gets Installed (Full Dependency List)**

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | Latest | REST API framework |
| uvicorn[standard] | Latest | ASGI web server |
| sqlalchemy | Latest | ORM database toolkit |
| passlib[bcrypt] | Latest | Password hashing library |
| bcrypt | 4.0.1 | Pinned for compatibility |
| python-jose[cryptography] | Latest | JWT token generation |
| python-multipart | Latest | File upload support |
| email-validator | Latest | Email validation |
| easyocr | Latest | Optical character recognition (~500MB) |
| numpy | Latest | Numerical computing |
| Pillow | Latest | Image processing |
| opencv-python | Latest | Computer vision library |
| textblob | Latest | NLP text corrections |
| transformers | Latest | Hugging Face models |
| torch | Latest | Deep learning (CPU mode) |
| torchvision | Latest | Vision utilities for PyTorch |
| torchaudio | Latest | Audio processing |
| requests | Latest | HTTP client for testing |

### **Manual Installation (If Needed)**

If the `requirements.txt` doesn't work, install packages individually:

```powershell
# Core Framework
pip install fastapi
pip install uvicorn[standard]

# Database
pip install sqlalchemy

# Authentication
pip install passlib[bcrypt]
pip install bcrypt==4.0.1
pip install python-jose[cryptography]

# File Handling
pip install python-multipart
pip install email-validator

# Image Processing
pip install opencv-python
pip install numpy
pip install Pillow

# OCR
pip install easyocr

# NLP
pip install textblob
pip install transformers

# Deep Learning (CPU)
pip install torch
pip install torchvision
pip install torchaudio

# Testing
pip install requests
```

---

## **Step 4: Initialize Database**

Run the seed script to create the database and test users:

```powershell
python seed.py
```

**Expected Output:**
```
✅ Created admin user: admin@handwriteai.com / password: admin123
✅ Created test user: user@handwriteai.com / password: user123
✅ Database seeding complete!
```

This creates `handwriteai.db` (SQLite database) with two test accounts.

---

## **Step 5: Start the Backend Server**

Launch the FastAPI application:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### **Server is Ready!** ✅

The server is now running at: **http://127.0.0.1:8000**

⚠️ **Keep this terminal open!** The server must stay running.

---

## **Step 6: Access the Website**

### **Open in Browser**

Open a new browser tab and navigate to:

```
http://127.0.0.1:8000
```

### **Login with Test Account**

**Admin Account:**
- Email: `admin@handwriteai.com`
- Password: `admin123`

**Regular User Account:**
- Email: `user@handwriteai.com`
- Password: `user123`

---

## **First Run: Model Downloads**

⏳ **First time inference takes 30-60 seconds** while models download:
- EasyOCR: ~500MB
- TrOCR: ~1.33GB
- Transformers models: ~100MB+

**Total: ~2GB** downloaded to your computer (cached for future use)

Once downloaded, subsequent runs are much faster (8-12 seconds per image).

---

## **How to Use the Application**

### **Test Upload**

1. **Click "Choose File"** or drag-drop an image
2. **Supported formats:** PNG, JPEG, JPG
3. **For best results:**
   - Use images with **black or blue ink** (brown ink struggles)
   - **Clear, high-contrast text**
   - **Minimal background noise** (blank white paper preferred)

### **View Results**

After upload completes:
- ✅ **Extracted Text** - The recognized text
- ✅ **Confidence Score** - How sure the OCR is (0-100%)
- ✅ **Engine Used** - Which OCR method won (TrOCR or EasyOCR variant)
- ✅ **Text Insights:**
  - Sentiment (positive/neutral/negative)
  - Readability Score (Flesch Reading Ease)
  - Word count, sentence count
  - Top keywords

### **Download or Copy**

- Click **"Copy"** to copy text to clipboard
- Click **"Download"** to save as `.txt` file

### **View History**

Click **"Refresh History"** to see all your past uploads

### **Admin Panel** (Admin Only)

- View total registered users
- View total OCR jobs processed
- List all users in the system

---

## **Validation & Testing**

### **Test 1: Pipeline Validation**

Open a **new terminal** (keep the server running in the first terminal):

```powershell
cd akshara-enterprises-handwritingai
venv\Scripts\Activate.ps1
python test_handwriting_pipeline.py "uploads/83e6bc6561c14f0fbe7c288b22d78336.jpeg"
```

**Expected Output:**
```
✅ OCR Engine Used: EasyOCR-Handwriting
✅ Confidence: 0.38
✅ Sentiment: neutral
✅ Readability: 45.1
✅ Keywords: ['additional', 'answer', 'sheet', ...]
```

### **Test 2: API Endpoint Validation**

```powershell
python test_api_endpoint.py
```

**Expected Output:**
```
✅ Login successful
✅ Upload successful (HTTP 200)
✅ Response fields: image_path, extracted_text, confidence_score, engine_used, analysis
```

---

## **File Structure**

```
akshara-enterprises-handwritingai/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── auth.py                 # JWT authentication
│   ├── database.py             # SQLAlchemy setup
│   ├── models.py               # Database models
│   ├── schemas.py              # Request/response schemas
│   ├── ocr.py                  # 3-layer OCR pipeline
│   ├── trocr_engine.py         # Transformer OCR
│   └── routers/
│       ├── auth_routes.py      # Login/register endpoints
│       ├── user_routes.py      # Upload endpoints
│       └── admin_routes.py     # Admin endpoints
├── index.html                  # Frontend (SPA)
├── requirements.txt            # All dependencies
├── seed.py                     # Database initializer
├── handwriteai.db              # SQLite database (auto-created)
├── README.md                   # Architecture docs
├── INSTALL.md                  # This file
├── DEMO_SCRIPT.md              # Demo recording guide
├── SUBMISSION.md               # Submission info
└── test_*.py                   # Validation scripts
```

---

## **Troubleshooting**

### **Error: "ModuleNotFoundError: No module named 'fastapi'"**

**Solution:** Make sure you activated the virtual environment:
```powershell
venv\Scripts\Activate.ps1
```

Then reinstall dependencies:
```powershell
pip install -r requirements.txt
```

---

### **Error: "Address already in use" on port 8000**

**Solution:** Another application is using port 8000. Either:

1. **Use a different port:**
   ```powershell
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
   ```
   Then open: `http://127.0.0.1:8001`

2. **Or kill the existing process:**
   ```powershell
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

---

### **Error: "Database is locked"**

**Solution:** Delete the old database and reseed:
```powershell
Remove-Item handwriteai.db
python seed.py
```

---

### **Error: "No such file or directory: 'uploads/...'"**

**Solution:** The uploads folder is created automatically. If it's missing:
```powershell
mkdir uploads
```

---

### **Models not downloading / "Connection timeout"**

**Solution:** Model downloads happen on first inference. This is normal:
- EasyOCR downloads on first OCR call (~500MB, takes 2-5 min)
- TrOCR downloads on first TrOCR call (~1.33GB, takes 3-10 min)
- Check internet connection
- Try again - downloads may resume if interrupted

---

### **Low OCR Confidence (Below 30%)**

**Causes:**
- Brown/light pen (low contrast)
- Ruled/graph paper background
- Curved/fancy handwriting
- Poor image quality

**Solutions:**
- Use blue or black pen
- Capture on plain white paper
- Use good lighting
- Ensure text is legible to humans first

---

## **Performance Tips**

1. **First run is slow** (models download + initialize)
2. **GPU acceleration:** If you have NVIDIA GPU, install CUDA for 5x faster inference
3. **Batch processing:** Upload multiple images (they're processed in sequence)
4. **Cache models:** Models are cached locally, second run is much faster

---

## **API Endpoints Reference**

### **Authentication**
```
POST /auth/register
POST /auth/login
```

### **User Operations**
```
POST /uploads/extract        # Upload and extract text
GET /uploads/history         # Get past uploads
GET /dashboard               # User profile
```

### **Admin Operations**
```
GET /admin/users            # List all users (admin only)
GET /admin/stats            # System statistics (admin only)
```

---

## **Environment Variables (Optional)**

Create a `.env` file if you need to customize:

```env
# Server
HOST=127.0.0.1
PORT=8000

# Database
DATABASE_URL=sqlite:///./handwriteai.db

# JWT
SECRET_KEY=change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## **Deployment (Production)**

For production deployment, see `SUBMISSION.md` for:
- Docker deployment
- Cloud hosting options (Azure, AWS, Google Cloud)
- Security hardening
- SSL/HTTPS setup

---

## **Support & Documentation**

- **Architecture:** See `README.md`
- **Demo Guide:** See `DEMO_SCRIPT.md`
- **Submission Info:** See `SUBMISSION.md`
- **Code Comments:** Inline documentation in all `.py` files

---

## **Quick Reference Commands**

```powershell
# Clone
git clone https://github.com/vetrimaarann/akshara-enterprises-handwritingai.git

# Setup
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py

# Run
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Test (new terminal)
python test_handwriting_pipeline.py "uploads/83e6bc6561c14f0fbe7c288b22d78336.jpeg"
python test_api_endpoint.py
```

---

**Installation complete! 🎉 Your HandwriteAI website is ready to use!**

For questions, refer to the documentation files or check inline code comments.
