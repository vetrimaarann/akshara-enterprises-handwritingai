# HandwriteAI

HandwriteAI is a FastAPI-based backend application for handwritten text extraction from uploaded images.  
It provides secure user authentication with JWT, role-based access control, OCR processing using EasyOCR, and upload history tracking in SQLite.

## Project Overview

### What it does
- Registers and authenticates users
- Restricts sensitive endpoints by role (`user` / `admin`)
- Accepts image uploads and extracts handwritten text
- Stores upload history for each user
- Exposes admin endpoints for user and platform statistics

### Core technologies
- **Backend:** FastAPI
- **Database:** SQLite + SQLAlchemy ORM
- **Authentication:** JWT (`python-jose`) + bcrypt hashing (`passlib`)
- **OCR:** EasyOCR
- **Image preprocessing:** Pillow + NumPy
- **Frontend:** Minimal HTML + Fetch API (`index.html`)

## System Architecture

HandwriteAI follows a modular layered architecture:

- `app/main.py`  
  FastAPI app bootstrap, CORS setup, route registration, and top-level API routes (`/upload`, `/history`).
- `app/database.py`  
  SQLAlchemy engine/session setup and DB dependency.
- `app/models.py`  
  ORM models (`User`, `UploadHistory`) and relationships.
- `app/schemas.py`  
  Pydantic request/response schemas.
- `app/auth.py`  
  Password hashing, JWT creation/validation, current-user and admin dependencies.
- `app/ocr.py`  
  OCR service: image validation, preprocessing, EasyOCR execution.
- `app/routers/`  
  Route modules by domain (`auth_routes`, `user_routes`, `admin_routes`).
- `index.html`  
  Lightweight UI for registration, login, upload, and history display.

### Request flow (upload)
1. Client sends image with JWT token.
2. API validates JWT and resolves current user.
3. OCR module preprocesses image and runs EasyOCR.
4. Upload metadata and extracted text are saved in DB.
5. API returns extracted text (and confidence where applicable).

## Model Explanation: How EasyOCR Works Internally

EasyOCR is a deep-learning OCR pipeline with two major stages:

1. **Text Detection**  
   EasyOCR detects regions in the image likely to contain text using a convolutional detector (e.g., CRAFT-style detector in many setups). It outputs bounding boxes around candidate text areas.

2. **Text Recognition**  
   Each detected region is normalized and passed to a recognition network (typically CNN + sequence modeling + CTC decoding). The network predicts character sequences and confidence scores.

### In this project
- Input image is validated as an image MIME type.
- **CLAHE (Contrast Limited Adaptive Histogram Equalization)** is applied to enhance local contrast in low-light or faded documents.
- **Adaptive thresholding** converts the image to binary (black/white) using intelligent local thresholds, significantly improving text clarity.
- Large images are resized to max 1500px to improve speed and memory efficiency.
- EasyOCR detects text regions and recognizes character sequences with paragraph mode for better line merging.
- Post-processing cleans OCR artifacts: removes duplicate whitespace, strips random symbols.
- The app aggregates text and computes average confidence across all detections.

**Note:** This preprocessing improves contrast-based issues but does NOT correct perspective distortion, significant skew, or complex backgrounds. Best results on plain documents with good contrast.

## Model Training Process (Documentation)

This project currently uses a hybrid inference approach with pretrained deep-learning OCR models:

- **EasyOCR** for baseline handwritten/printed extraction.
- **TrOCR (microsoft/trocr-base-handwritten)** as transformer-based handwriting path.

### Current training status

- No full custom model training has been performed inside this repository yet.
- The system uses transfer learning in inference mode via pretrained checkpoints.
- Performance improvements are currently achieved through preprocessing and model selection rather than full retraining.

### Recommended fine-tuning workflow (for production-grade handwriting)

1. **Dataset preparation**
  - Collect labeled handwriting image-text pairs (line-level or word-level).
  - Normalize resolution, remove blurred/invalid samples, split train/val/test.
2. **Preprocessing pipeline**
  - Deskew, denoise, contrast normalization, text-region cropping.
  - Augment with blur, brightness, tilt, and pen-style variations.
3. **Model fine-tuning (TrOCR/CRNN)**
  - Start from pretrained checkpoint.
  - Fine-tune on domain handwriting data with CTC/seq2seq objective.
  - Track CER (Character Error Rate) and WER (Word Error Rate).
4. **Evaluation and thresholding**
  - Compare against baseline EasyOCR on holdout set.
  - Calibrate confidence thresholds for fallback and rejection handling.
5. **Deployment strategy**
  - Export best checkpoint, version models, enable A/B comparison.
  - Keep hybrid fallback for low-confidence predictions.

### Why this design is used now

- Faster implementation and iteration before submission deadline.
- Clear modular architecture to plug in fine-tuned models later.
- Measurable, confidence-aware OCR behavior with secure user workflow.

## Database Schema

### `users`
- `id` (Integer, PK)
- `full_name` (String, required)
- `email` (String, unique, indexed, required)
- `hashed_password` (String, required)
- `role` (String, default: `user`)

### `upload_history`
- `id` (Integer, PK)
- `user_id` (Integer, FK → `users.id`, required)
- `image_path` (String, required)
- `extracted_text` (Text, required)
- `timestamp` (DateTime, auto-generated UTC)

### Relationship
- One user has many uploads: `User.uploads`
- Each upload belongs to one user: `UploadHistory.user`

## Authentication Flow

1. **Register** (`POST /auth/register`)  
   User submits name, email, password. Password is hashed with bcrypt before DB storage.

2. **Login** (`POST /auth/login`)  
   Credentials are verified. On success, server issues JWT access token (`HS256`).

3. **Authenticated Access**  
   Client includes header: `Authorization: Bearer <token>`.

4. **Authorization**
   - `get_current_user`: allows any authenticated user.
   - `get_current_admin`: blocks non-admin users with `403 Forbidden`.

## API Highlights

### Auth
- `POST /auth/register`
- `POST /auth/login`

### User
- `GET /dashboard` (protected)
- `POST /upload` (protected)
- `GET /history` (protected)
- `POST /uploads/extract` (protected, router-level OCR endpoint)
- `GET /uploads/history` (protected, router-level history endpoint)

### Admin
- `GET /admin/users` (admin only)
- `GET /admin/stats` (admin only)

### Utility
- `GET /health`

## How to Run Locally

## 1) Clone or open project
Ensure your working directory is the project root containing `app/` and `requirements.txt`.

## 2) Create virtual environment (recommended)

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux/macOS
```bash
python -m venv .venv
source .venv/bin/activate
```

## 3) Install dependencies
```bash
pip install -r requirements.txt
```

## 4) Run server
```bash
uvicorn app.main:app --reload
```

API base URL: `http://127.0.0.1:8000`

## 5) Open frontend
Open `http://127.0.0.1:8000/` in a browser.

## 6) API docs
Swagger UI: `http://127.0.0.1:8000/docs`

## Notes
- SQLite DB file (`handwriteai.db`) is created automatically.
- Uploaded images are stored in `uploads/`.
- For production, replace `SECRET_KEY` in `app/auth.py` with a strong secret from environment variables.

## Future Improvements

- Move secrets/configs to environment variables (`pydantic-settings`)
- Add refresh tokens and token revocation strategy
- Add email verification and password reset flow
- Add Alembic migrations for schema versioning
- Add async background jobs for OCR on large files
- Add better image preprocessing (binarization, denoising, skew correction)
- Add multilingual OCR support and language auto-detection
- Improve confidence post-processing and uncertainty thresholds
- Add pagination/filtering for upload history
- Add test suite (unit + integration) and CI pipeline
- Add Docker and deployment manifests (Nginx + Gunicorn/Uvicorn)
- Add object storage (S3/Azure Blob) instead of local upload folder
#   a k s h a r a - e n t e r p r i s e s - h a n d w r i t i n g a i  
 