from collections import Counter
from functools import lru_cache
import re

import cv2
import easyocr
import numpy as np
from fastapi import HTTPException, UploadFile, status
from textblob import TextBlob

from app.trocr_engine import run_trocr


@lru_cache(maxsize=1)
def get_reader() -> easyocr.Reader:
    return easyocr.Reader(["en"], gpu=False)


def clean_ocr_text(text: str) -> str:
    """
    Post-process OCR output to remove common artifacts.
    
    - Removes duplicate whitespace
    - Strips random symbols (preserve punctuation)
    - Joins broken words on same line
    """
    if not text:
        return text
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove standalone special characters (but keep punctuation in context)
    text = re.sub(r'\s+[^\w\s.,!?;:\-\'\"]+\s+', ' ', text)
    
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    return '\n'.join(lines)


def upscale_image(image_array: np.ndarray) -> np.ndarray:
    h, w = image_array.shape[:2]
    if min(h, w) < 1000:
        return cv2.resize(
            image_array,
            None,
            fx=2.0,
            fy=2.0,
            interpolation=cv2.INTER_CUBIC,
        )
    return image_array


def deskew(image: np.ndarray) -> np.ndarray:
    """
    Estimate skew angle from foreground pixels and rotate image to deskew.
    Returns the input unchanged when angle cannot be estimated.
    """
    if image is None or image.size == 0:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary_inv = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    coords = np.column_stack(np.where(binary_inv > 0))

    if coords.size == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.3:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    return cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def auto_crop_text_region(image: np.ndarray) -> np.ndarray:
    """
    Detect likely text regions and crop image to their combined bounding box.
    Falls back to original image if no reliable region is found.
    """
    if image is None or image.size == 0:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )

    connect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, connect_kernel, iterations=2)

    contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    h, w = image.shape[:2]
    min_area = max(50, int(h * w * 0.0005))

    boxes: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        area = cw * ch
        if area < min_area or ch < 8 or cw < 8:
            continue
        boxes.append((x, y, x + cw, y + ch))

    if not boxes:
        return image

    x1 = min(box[0] for box in boxes)
    y1 = min(box[1] for box in boxes)
    x2 = max(box[2] for box in boxes)
    y2 = max(box[3] for box in boxes)

    pad = 12
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)

    if x2 <= x1 or y2 <= y1:
        return image

    return image[y1:y2, x1:x2]


def preprocess_common(image_array: np.ndarray, max_dim: int = 1800) -> np.ndarray:
    """
    Shared normalization:
    - Aggressive 3x upscale for small handwriting (CRITICAL)
    - Limit max dimensions
    - Deskew rotated captures
    - Auto-crop likely text area
    """
    if image_array is None or image_array.size == 0:
        raise ValueError("Empty or invalid image array")

    # CRITICAL: Aggressive upscaling for small handwriting
    # Small letters are invisible to OCR model without this
    h, w = image_array.shape[:2]
    normalized = cv2.resize(
        image_array,
        None,
        fx=3.0,
        fy=3.0,
        interpolation=cv2.INTER_CUBIC,
    )
    
    # Limit max dimensions to prevent memory issues
    h, w = normalized.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        normalized = cv2.resize(normalized, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    normalized = deskew(normalized)
    normalized = auto_crop_text_region(normalized)
    return normalized


def preprocess_for_printed(image_array: np.ndarray, max_dim: int = 1800) -> np.ndarray:
    normalized = preprocess_common(image_array, max_dim=max_dim)
    gray = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
    return cv2.fastNlMeansDenoising(gray, h=8)


def remove_watermark_region(image_array: np.ndarray) -> np.ndarray:
    """
    Remove top watermark/header region from exam answer sheets.
    Crops top 8% of image to remove "ADDITIONAL ANSWER SHEET" type headers.
    """
    if image_array is None or image_array.size == 0:
        return image_array
    
    h, w = image_array.shape[:2]
    crop_height = int(h * 0.08)  # Remove top 8%
    
    if crop_height >= h - 50:  # Safety check
        return image_array
    
    return image_array[crop_height:, :]


def preprocess_for_handwriting(image_array: np.ndarray, max_dim: int = 1800) -> np.ndarray:
    """
    Simplified handwriting preprocessing:
    - Aggressive 3x upscaling FIRST (via preprocess_common)
    - Remove watermark header
    - Light denoising only
    - NO thresholding (was destroying text)
    """
    # Aggressive 3x upscaling first via common preprocessing
    normalized = preprocess_common(image_array, max_dim=max_dim)
    
    # Remove watermark after upscaling
    no_watermark = remove_watermark_region(normalized)
    
    # Convert to grayscale
    gray = cv2.cvtColor(no_watermark, cv2.COLOR_BGR2GRAY)
    
    # Light denoising only (NO thresholding)
    denoised = cv2.fastNlMeansDenoising(gray, h=5)
    
    return denoised


def preprocess_light_ink_handwriting(image_array: np.ndarray, max_dim: int = 1800) -> np.ndarray:
    """
    Specialized pipeline for light-colored ink (brown pen, pencil).
    Uses contrast enhancement but NO thresholding.
    """
    # Aggressive 3x upscaling first
    normalized = preprocess_common(image_array, max_dim=max_dim)
    
    # Remove watermark after upscaling
    no_watermark = remove_watermark_region(normalized)
    
    gray = cv2.cvtColor(no_watermark, cv2.COLOR_BGR2GRAY)
    
    # Histogram equalization for light ink visibility
    equalized = cv2.equalizeHist(gray)
    
    # Light CLAHE for contrast
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(equalized)
    
    return enhanced


def parse_easyocr_results(results: list) -> tuple[str, float]:
    texts: list[str] = []
    confidences: list[float] = []
    for item in results:
        if isinstance(item, (list, tuple)):
            if len(item) >= 2 and isinstance(item[1], str):
                texts.append(item[1])
            if len(item) >= 3:
                try:
                    confidences.append(float(item[2]))
                except (TypeError, ValueError):
                    pass
        elif isinstance(item, str):
            texts.append(item)

    extracted_text = clean_ocr_text("\n".join(texts))
    avg_confidence = (
        float(sum(confidences) / len(confidences)) if confidences else 0.0
    )
    return extracted_text, avg_confidence


def run_ocr(reader: easyocr.Reader, image_array: np.ndarray) -> tuple[str, float]:
    """
    Run OCR with detail=1 to always get confidence scores.
    Paragraph mode is NOT used here to preserve detailed confidence data.
    """
    try:
        # detail=1 always returns: [(bbox, text, confidence), ...]
        results = reader.readtext(image_array, detail=1, paragraph=False)
    except (TypeError, ValueError):
        # Fallback: use detail=0 if the model doesn't support it
        # But keep paragraph=False to get consistent structure
        results = reader.readtext(image_array, detail=0, paragraph=False)

    if not results:
        return "", 0.0
    
    text, confidence = parse_easyocr_results(results)
    return text, confidence


def correct_text(text: str) -> str:
    if not text or not text.strip():
        return text
    try:
        return str(TextBlob(text).correct())
    except Exception:
        return text


def post_correct_text(text: str) -> str:
    """
    Safer language correction pass.
    Avoids over-correcting very short/noisy OCR outputs.
    """
    if not text or len(text.strip()) < 8:
        return text

    alpha_ratio = sum(ch.isalpha() for ch in text) / max(len(text), 1)
    if alpha_ratio < 0.45:
        return text

    corrected = correct_text(text)

    if not corrected:
        return text

    length_delta = abs(len(corrected) - len(text)) / max(len(text), 1)
    if length_delta > 0.35:
        return text

    return corrected


def extract_keywords(text: str, top_k: int = 8) -> list[str]:
    tokens = re.findall(r"[A-Za-z]{3,}", text.lower())
    stop_words = {
        "the", "and", "for", "with", "this", "that", "from", "are", "was",
        "have", "has", "you", "your", "they", "their", "them", "into", "about",
        "there", "would", "could", "should", "been", "being", "will", "shall",
        "can", "may", "might", "not", "but", "all", "any", "our", "out", "one",
        "two", "three", "what", "when", "where", "which", "while", "than", "then",
    }
    filtered = [token for token in tokens if token not in stop_words]
    if not filtered:
        return []

    freq = Counter(filtered)
    return [word for word, _ in freq.most_common(top_k)]


def analyze_extracted_text(text: str) -> dict:
    clean_text = (text or "").strip()
    if not clean_text:
        return {
            "word_count": 0,
            "sentence_count": 0,
            "avg_word_length": 0.0,
            "sentiment": "neutral",
            "sentiment_polarity": 0.0,
            "readability_score": 0.0,
            "keywords": [],
        }

    words = re.findall(r"\b\w+\b", clean_text)
    sentences = re.split(r"[.!?]+", clean_text)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

    word_count = len(words)
    sentence_count = len(sentences)
    avg_word_length = (
        float(sum(len(word) for word in words) / word_count)
        if word_count
        else 0.0
    )

    syllable_count = sum(max(1, len(re.findall(r"[aeiouyAEIOUY]+", word))) for word in words)
    if word_count and sentence_count:
        readability = 206.835 - (1.015 * (word_count / sentence_count)) - (84.6 * (syllable_count / word_count))
        readability = float(max(0.0, min(100.0, readability)))
    else:
        readability = 0.0

    polarity = float(TextBlob(clean_text).sentiment.polarity)
    if polarity > 0.1:
        sentiment = "positive"
    elif polarity < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_word_length": round(avg_word_length, 2),
        "sentiment": sentiment,
        "sentiment_polarity": round(polarity, 3),
        "readability_score": round(readability, 2),
        "keywords": extract_keywords(clean_text),
    }


async def extract_handwritten_text_with_meta(file: UploadFile) -> tuple[str, float, str, dict]:
    """
    Extract handwritten text with model metadata and NLP analysis.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image uploads are supported.",
        )

    try:
        content = await file.read()
        await file.seek(0)
        image_array = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if image_array is None:
            raise ValueError("Failed to decode image")
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file.",
        ) from error

    try:
        reader = get_reader()
        base_text, base_conf = run_ocr(reader, image_array)
        printed_text, printed_conf = run_ocr(reader, preprocess_for_printed(image_array))
        handwriting_text, handwriting_conf = run_ocr(reader, preprocess_for_handwriting(image_array))
        light_ink_text, light_ink_conf = run_ocr(reader, preprocess_light_ink_handwriting(image_array))

        easy_candidates = [
            ("EasyOCR-Raw", base_text, base_conf),
            ("EasyOCR-Printed", printed_text, printed_conf),
            ("EasyOCR-Handwriting", handwriting_text, handwriting_conf),
            ("EasyOCR-LightInk", light_ink_text, light_ink_conf),
        ]

        best_method, best_text, best_conf = max(
            easy_candidates,
            key=lambda triple: (triple[2], len(triple[1])),
        )

        # Run TrOCR fallback only when EasyOCR confidence is low or text is too short
        if best_conf < 0.55 or len(best_text.strip()) < 20:
            trocr_text, trocr_conf = run_trocr(image_array)
            if trocr_text and (trocr_conf > best_conf or len(trocr_text) > len(best_text) * 1.2):
                best_method, best_text, best_conf = "TrOCR", trocr_text, trocr_conf

        if best_text and best_conf == 0.0:
            try:
                detail_results = reader.readtext(image_array, detail=1, paragraph=False)
                _, detail_conf = parse_easyocr_results(detail_results)
                if detail_conf > 0.0:
                    best_conf = detail_conf
            except Exception:
                pass

        best_text = post_correct_text(best_text)
        analysis = analyze_extracted_text(best_text)

        return best_text, best_conf, best_method, analysis
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image preprocessing failed: {str(ve)}",
        ) from ve
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OCR processing failed.",
        ) from error


async def extract_handwritten_text(file: UploadFile) -> tuple[str, float]:
    text, confidence, _, _ = await extract_handwritten_text_with_meta(file)
    return text, confidence