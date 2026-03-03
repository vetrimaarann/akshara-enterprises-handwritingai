"""
TrOCR (Transformer-based OCR) engine for handwriting recognition.
Uses line-wise decoding for better accuracy on multi-line handwritten pages.
"""
from functools import lru_cache
import re
from typing import Tuple

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


@lru_cache(maxsize=1)
def get_trocr_model() -> tuple[TrOCRProcessor, VisionEncoderDecoderModel]:
    model_name = "microsoft/trocr-base-handwritten"
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    model.eval()
    return processor, model


def clean_trocr_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"[^\w\s.,!?;:\-()'\"]+", "", cleaned)
    return cleaned


def remove_header_region(image_array: np.ndarray) -> np.ndarray:
    if image_array is None or image_array.size == 0:
        return image_array

    h, _ = image_array.shape[:2]
    crop_height = int(h * 0.1)
    if crop_height < h - 40:
        return image_array[crop_height:, :]
    return image_array


def prepare_page_for_segmentation(image_array: np.ndarray) -> np.ndarray:
    page = remove_header_region(image_array)

    if len(page.shape) == 3:
        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    else:
        gray = page

    gray = cv2.fastNlMeansDenoising(gray, h=6)
    gray = cv2.equalizeHist(gray)
    return gray


def segment_text_lines(gray: np.ndarray) -> list[np.ndarray]:
    if gray is None or gray.size == 0:
        return []

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary_inv = cv2.threshold(
        blur,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )

    h, w = binary_inv.shape
    connect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 50), 3))
    connected = cv2.morphologyEx(binary_inv, cv2.MORPH_CLOSE, connect_kernel, iterations=1)

    projection = np.sum(connected > 0, axis=1)
    threshold = max(12, int(w * 0.008))

    regions: list[tuple[int, int]] = []
    start = None
    for i, value in enumerate(projection):
        if value > threshold and start is None:
            start = i
        elif value <= threshold and start is not None:
            end = i
            if end - start >= 16:
                regions.append((start, end))
            start = None

    if start is not None:
        end = h
        if end - start >= 16:
            regions.append((start, end))

    lines: list[np.ndarray] = []
    for y1, y2 in regions:
        pad = 10
        top = max(0, y1 - pad)
        bottom = min(h, y2 + pad)
        line = gray[top:bottom, :]

        if line.size == 0:
            continue

        _, line_bin = cv2.threshold(line, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        ink_pixels = int(np.sum(line_bin > 0))
        if ink_pixels < 120:
            continue

        lines.append(line)

    return lines


def preprocess_line_for_trocr(line_gray: np.ndarray) -> Image.Image:
    if line_gray is None or line_gray.size == 0:
        return Image.new("RGB", (384, 64), color="white")

    h, w = line_gray.shape[:2]
    target_h = 64
    scale = target_h / max(h, 1)
    target_w = max(128, int(w * scale))

    resized = cv2.resize(
        line_gray,
        (target_w, target_h),
        interpolation=cv2.INTER_CUBIC,
    )

    rgb = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(rgb)


def estimate_generation_confidence(generation_output, text: str) -> float:
    model_conf = 0.0

    try:
        seq_scores = getattr(generation_output, "sequences_scores", None)
        if seq_scores is not None and len(seq_scores) > 0:
            score = float(seq_scores[0].detach().cpu().item())
            model_conf = float(np.exp(score))
        else:
            scores = getattr(generation_output, "scores", None)
            if scores:
                token_conf: list[float] = []
                for step_logits in scores:
                    probs = torch.softmax(step_logits[0], dim=-1)
                    token_conf.append(float(torch.max(probs).detach().cpu().item()))
                if token_conf:
                    model_conf = float(sum(token_conf) / len(token_conf))
    except Exception:
        model_conf = 0.0

    model_conf = max(0.0, min(1.0, model_conf))

    if not text:
        return 0.0

    alpha_ratio = sum(ch.isalpha() for ch in text) / max(len(text), 1)
    length_score = min(len(text) / 24.0, 1.0)
    quality = 0.6 * alpha_ratio + 0.4 * length_score

    confidence = 0.7 * model_conf + 0.3 * quality
    return float(max(0.0, min(1.0, confidence)))


def decode_single_line(
    processor: TrOCRProcessor,
    model: VisionEncoderDecoderModel,
    line_gray: np.ndarray,
) -> tuple[str, float]:
    pil_line = preprocess_line_for_trocr(line_gray)
    pixel_values = processor(images=pil_line, return_tensors="pt").pixel_values

    with torch.no_grad():
        generated = model.generate(
            pixel_values,
            max_new_tokens=96,
            num_beams=4,
            early_stopping=True,
            output_scores=True,
            return_dict_in_generate=True,
        )

    text = processor.batch_decode(generated.sequences, skip_special_tokens=True)[0]
    text = clean_trocr_text(text)
    conf = estimate_generation_confidence(generated, text)
    return text, conf


def run_trocr(image_array: np.ndarray) -> Tuple[str, float]:
    try:
        processor, model = get_trocr_model()

        gray_page = prepare_page_for_segmentation(image_array)
        lines = segment_text_lines(gray_page)

        if not lines:
            lines = [gray_page]

        decoded_lines: list[str] = []
        weighted_conf_sum = 0.0
        weighted_len_sum = 0

        for line in lines:
            text, conf = decode_single_line(processor, model, line)
            if not text:
                continue

            decoded_lines.append(text)
            weight = max(len(text), 1)
            weighted_conf_sum += conf * weight
            weighted_len_sum += weight

        final_text = "\n".join(decoded_lines).strip()
        final_text = clean_trocr_text(final_text)

        if final_text:
            final_conf = weighted_conf_sum / max(weighted_len_sum, 1)
            return final_text, float(max(0.0, min(1.0, final_conf)))

        # Fallback: decode full page as one image when line segmentation fails
        full_page_pil = preprocess_line_for_trocr(gray_page)
        pixel_values = processor(images=full_page_pil, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated = model.generate(
                pixel_values,
                max_new_tokens=128,
                num_beams=4,
                early_stopping=True,
                output_scores=True,
                return_dict_in_generate=True,
            )
        fallback_text = processor.batch_decode(generated.sequences, skip_special_tokens=True)[0]
        fallback_text = clean_trocr_text(fallback_text)
        fallback_conf = estimate_generation_confidence(generated, fallback_text)

        if not fallback_text:
            return "", 0.0

        return fallback_text, fallback_conf

    except Exception:
        return "", 0.0


def run_trocr_simple(image_array: np.ndarray) -> str:
    text, _ = run_trocr(image_array)
    return text
