## HandwriteAI — End-to-End Test Checklist

### Prerequisites
1. Navigate to project root: `D:\Akshara Enterprises`
2. Ensure Python `3.10+` is installed
3. Dependencies installed: `pip install -r requirements.txt`

---

### Phase 1: Backend Setup

#### Step 1 — Start the API Server
```powershell
uvicorn app.main:app --reload
```
Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

#### Step 2 — Seed Database (Optional but recommended for admin testing)
In a **separate terminal**:
```powershell
python seed.py
```
Expected output:
```
✅ Created admin user: admin@handwriteai.com / password: admin123
✅ Created test user: user@handwriteai.com / password: user123
✅ Database seeding complete!
```

---

### Phase 2: Frontend & User Flow Testing

#### Step 3 — Open Frontend in Browser
Navigate to: `http://127.0.0.1:8000/`

**Expected View:**
- 4 sections visible: Register, Login, Dashboard (upload), Previous Uploads

---

#### Step 4 ✅ Register a New User
**Test Form:**
- Full name: `John Doe`
- Email: `john@example.com`
- Password: `testpass123`

**Expected Result:**
- Alert: "Registration successful"
- DB now contains user with hashed password

**Check:**
```bash
# Optional: Inspect database
# sqlite3 handwriteai.db "SELECT id, email, role FROM users;"
```

---

#### Step 5 ✅ Login with Registered User
**Test Form:**
- Email: `john@example.com`
- Password: `testpass123`

**Expected Result:**
- Alert: "Login successful"
- Auth status changes to: "Logged in"
- JWT token stored in `localStorage`

**Verify in Browser DevTools** (F12):
```javascript
localStorage.getItem("handwriteai_token")
// Should return a long JWT string (header.payload.signature)
```

---

#### Step 6 ✅ Upload & Extract Handwritten Image
**Prepare a test image:**
- Use any handwritten text image (scan, photo, etc.)
- File format: `.png`, `.jpg`, `.jpeg`, `.bmp`

**Test Flow:**
1. Click "Choose File" under Dashboard
2. Select your handwritten image
3. Click "Upload & Extract"

**Expected Result:**
- Extracted Text section populates with recognized text
- Confidence score displayed (0–1 scale)
- No CORS errors in console

**Example Output:**
```
Hello World Test
Confidence: 0.925
```

---

#### Step 7 ✅ View Upload History
**In the same browser session:**
1. Scroll to "Previous Uploads" section
2. Click "Refresh History"

**Expected Result:**
- List appears with entries like:
  ```
  2026-03-02T10:45:32 | uploads/a1b2c3d4e5f6.png | Hello World Test
  ```
- Sorted by timestamp descending (newest first)

---

#### Step 8 ✅ Test Admin Routes

**Option A: Use seeded admin account**
1. Logout (click Logout button)
2. Login with:
   - Email: `admin@handwriteai.com`
   - Password: `admin123`

**Option B: Manually promote user in DB**
```bash
sqlite3 handwriteai.db "UPDATE users SET role='admin' WHERE email='john@example.com';"
```

**Test Admin Endpoints (Swagger UI):**
1. Navigate to: `http://127.0.0.1:8000/docs`
2. Authorize with admin JWT token
3. Test these endpoints:

**GET /admin/users**
- Expected: List of all users with `id`, `full_name`, `email`, `role`
- Example:
  ```json
  [
    { "id": 1, "full_name": "Admin User", "email": "admin@handwriteai.com", "role": "admin" },
    { "id": 2, "full_name": "John Doe", "email": "john@example.com", "role": "user" }
  ]
  ```

**GET /admin/stats**
- Expected:
  ```json
  { "total_users": 2, "total_uploads": 1 }
  ```

---

### Phase 3: CORS & Error Handling

#### Step 9 ✅ Verify CORS is Working
**In Browser Console (F12):**
- No errors like `Access to XMLHttpRequest blocked by CORS policy`
- All fetch requests to `/auth/login`, `/upload`, `/history` succeed

**If CORS errors appear:**
- Check [app/main.py](app/main.py) has `CORSMiddleware` configured (it should)
- Restart server: `Ctrl+C` → `uvicorn app.main:app --reload`

---

#### Step 10 ✅ Test Invalid Image Upload
**Upload a non-image file** (e.g., `.txt` file)

**Expected Result:**
- Alert: `Only image uploads are supported.`
- No crash, graceful error handling

---

#### Step 11 ✅ Test Unauthorized Access
**In a fresh browser (no token):**
1. Open DevTools Console
2. Run:
   ```javascript
   fetch('http://127.0.0.1:8000/history')
     .then(r => r.json())
     .then(data => console.log(data))
   ```

**Expected Result:**
```json
{ "detail": "Not authenticated" }
```
HTTP 403 status

---

### Phase 4: Repo Cleanliness

#### Step 12 ✅ Clean Up Before Submission

**From project root, run:**
```powershell
# Remove Python caches
Remove-Item -Recurse -Force .\app\__pycache__
Remove-Item -Recurse -Force .\app\routers\__pycache__

# Optional: Delete local DB if you want a fresh start
Remove-Item .\handwriteai.db

# Optional: Delete uploads folder if empty
Remove-Item -Recurse -Force .\uploads
```

**Verify structure is clean:**
```powershell
Get-ChildItem -Recurse -Hidden | Where-Object Name -like '__pycache__'
# Should return nothing
```

**Ensure these files exist:**
```powershell
Test-Path .\requirements.txt     # ✅ Should be True
Test-Path .\README.md            # ✅ Should be True
Test-Path .\seed.py              # ✅ Should be True (optional helper)
Test-Path .\.gitignore           # ✅ Should be True
Test-Path .\app\main.py          # ✅ Should be True
Test-Path .\index.html           # ✅ Should be True
```

---

### Summary: Quick Pass/Fail Checklist
- [ ] Server starts without errors
- [ ] Frontend loads at `http://127.0.0.1:8000/`
- [ ] Register creates user with bcrypt hashed password
- [ ] Login returns valid JWT token
- [ ] Upload image extracts text via EasyOCR
- [ ] History shows previous uploads (sorted descending)
- [ ] Admin routes restricted to admin role
- [ ] `/admin/users` and `/admin/stats` work
- [ ] CORS enabled (no blocked requests)
- [ ] Error handling graceful (no 500 crashes)
- [ ] Repo clean (__pycache__, .venv, *.db excluded)
- [ ] .gitignore present
- [ ] requirements.txt complete
- [ ] README up-to-date

---

### If Tests Fail: Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'easyocr'` | Run `pip install -r requirements.txt` again |
| CORS errors in console | Verify `CORSMiddleware` in `app/main.py` line ~17 |
| JWT token invalid | Restart server (clears token cache) |
| "Email already registered" | Use unique email or delete DB: `rm handwriteai.db` |
| OCR extraction takes long (>30s) | First run downloads EasyOCR model (~200MB) |
| `401 Unauthorized` on protected routes | Check `Authorization: Bearer <token>` header is sent |

---

### Screen Recording Script (3–4 min)

```
[0:00–0:20] Intro & folder structure
  "This is HandwriteAI, a FastAPI OCR backend. Let me show you the structure."
  Show: ls app/, ls app/routers/, cat requirements.txt

[0:20–0:30] Start server
  "Starting the server now."
  uvicorn app.main:app --reload
  → Show "Application startup complete"

[0:30–0:45] Open frontend
  "Opening the browser frontend."
  → Navigate to http://127.0.0.1:8000/

[0:45–1:15] Register & login
  "Registering a new user, then logging in."
  → Fill form, register, login
  → Show JWT token in localStorage (F12)

[1:15–2:00] Upload image & extract text
  "Now uploading a handwritten image for OCR processing."
  → Select image, upload
  → Show extracted text + confidence

[2:00–2:30] Check history
  "Viewing the upload history for this user."
  → Click "Refresh History"
  → Show list of previous uploads

[2:30–3:00] Admin routes
  "Testing admin-only routes."
  → Login as admin (or promote user)
  → Show /admin/users and /admin/stats in Swagger (docs)

[3:00–3:15] Closing
  "The application successfully handles auth, OCR, and RBAC. Thanks!"
```

---

**Status: Ready for submission ✅**
