"""
Test the HTTP API endpoint to verify the full response structure.
Tests: Login -> Upload -> Verify response includes engine_used + analysis
"""
import requests
import json
from pathlib import Path

API_URL = "http://127.0.0.1:8000"

# Step 1: Login and get token
print("=" * 80)
print("TESTING API ENDPOINT: /uploads/extract")
print("=" * 80)

print("\n🔐 Step 1: Logging in to get JWT token...")
login_response = requests.post(
    f"{API_URL}/auth/login",
    data={"username": "admin@handwriteai.com", "password": "admin123"}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token_data = login_response.json()
access_token = token_data.get("access_token")
print(f"✅ Login successful, token obtained")

# Step 2: Upload a file
print("\n📤 Step 2: Uploading handwriting image...")
image_path = Path("uploads/83e6bc6561c14f0fbe7c288b22d78336.jpeg")

if not image_path.exists():
    print(f"❌ Image not found: {image_path}")
    exit(1)

headers = {"Authorization": f"Bearer {access_token}"}
files = {"file": (image_path.name, open(image_path, "rb"), "image/jpeg")}

upload_response = requests.post(
    f"{API_URL}/uploads/extract",
    headers=headers,
    files=files
)

if upload_response.status_code != 200:
    print(f"❌ Upload failed: {upload_response.status_code}")
    print(upload_response.text)
    exit(1)

print(f"✅ Upload successful (HTTP {upload_response.status_code})")

# Step 3: Parse and display response
print("\n📊 Step 3: Analyzing response structure...")
response_data = upload_response.json()

# Check required fields
required_fields = ["image_path", "extracted_text", "confidence_score", "engine_used", "analysis"]
for field in required_fields:
    if field in response_data:
        print(f"  ✅ {field}: Present")
    else:
        print(f"  ❌ {field}: MISSING")

# Analyze the analysis object
analysis = response_data.get("analysis", {})
analysis_fields = ["word_count", "sentence_count", "avg_word_length", "sentiment", "sentiment_polarity", "readability_score", "keywords"]
print("\n  Analysis Fields:")
for field in analysis_fields:
    if field in analysis:
        print(f"    ✅ {field}: {analysis[field]}")
    else:
        print(f"    ❌ {field}: MISSING")

# Full response display
print("\n📄 Full Response:")
print("-" * 80)
print(json.dumps(response_data, indent=2))
print("-" * 80)

# Summary
print("\n✅ API ENDPOINT TEST COMPLETE")
print(f"   Engine: {response_data.get('engine_used', '-')}")
print(f"   Confidence: {response_data.get('confidence_score', 0):.1%}")
print(f"   Analysis Present: {bool(response_data.get('analysis'))}")
print()
