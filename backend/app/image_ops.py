from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image

from .config import FACE_CASCADE, FACE_DETECTION_MAX_DIMENSION, HOG_DESCRIPTOR, TEXT_DETECTION_MAX_DIMENSION

NumpyImage = np.ndarray[Any, Any]


def pil_to_bgr(pil_img: Image.Image) -> NumpyImage:
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def bgr_to_png_bytes(bgr: NumpyImage) -> bytes:
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("Failed to encode image as PNG.")
    return buf.tobytes()


def bgr_to_jpeg_bytes(bgr: NumpyImage, quality: int) -> bytes:
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("Failed to encode image as JPEG.")
    return buf.tobytes()


def resize_long_edge(bgr: NumpyImage, max_dimension: int) -> NumpyImage:
    resized, _ = resize_with_scale(bgr, max_dimension)
    return resized


def resize_with_scale(bgr: NumpyImage, max_dimension: int) -> tuple[NumpyImage, float]:
    height, width = bgr.shape[:2]
    longest_edge = max(height, width)
    if longest_edge <= max_dimension:
        return bgr, 1.0
    scale = max_dimension / float(longest_edge)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    return cv2.resize(bgr, (new_width, new_height), interpolation=cv2.INTER_AREA), scale


def blur_region(bgr: NumpyImage, x: int, y: int, w: int, h: int, kernel_size: int) -> None:
    height, width = bgr.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(width, x + w), min(height, y + h)
    if x2 <= x1 or y2 <= y1:
        return
    roi = bgr[y1:y2, x1:x2]
    kernel_size = max(3, int(kernel_size) | 1)
    bgr[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)


@dataclass
class Options:
    blur_people: bool
    remove_text: bool
    blur_strength: int
    detect_bodies: bool


def scrub_text(bgr: NumpyImage) -> NumpyImage:
    analysis_bgr, scale = resize_with_scale(bgr, TEXT_DETECTION_MAX_DIMENSION)
    rgb = cv2.cvtColor(analysis_bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.bilateralFilter(cv2.cvtColor(analysis_bgr, cv2.COLOR_BGR2GRAY), 7, 50, 50)
    data = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)
    mask = np.zeros(bgr.shape[:2], dtype=np.uint8)
    for i, text in enumerate(data.get("text", [])):
        try:
            confidence = float(data.get("conf", ["-1"])[i])
        except Exception:
            confidence = -1.0
        if not (text or "").strip() or confidence < 60:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        if scale != 1.0:
            x, y = int(x / scale), int(y / scale)
            w, h = max(1, int(w / scale)), max(1, int(h / scale))
        pad = max(2, int(min(w, h) * 0.15))
        x2, y2 = max(0, x - pad), max(0, y - pad)
        w2 = min(mask.shape[1] - x2, w + 2 * pad)
        h2 = min(mask.shape[0] - y2, h + 2 * pad)
        cv2.rectangle(mask, (x2, y2), (x2 + w2, y2 + h2), 255, thickness=-1)
    if mask.max() == 0:
        return bgr
    return cv2.inpaint(bgr, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)


def scrub_people(bgr: NumpyImage, blur_strength: int, detect_bodies: bool) -> NumpyImage:
    out = bgr.copy()
    face_input, face_scale = resize_with_scale(out, FACE_DETECTION_MAX_DIMENSION)
    faces = FACE_CASCADE.detectMultiScale(cv2.cvtColor(face_input, cv2.COLOR_BGR2GRAY), scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
    for x, y, w, h in faces:
        if face_scale != 1.0:
            x, y = int(x / face_scale), int(y / face_scale)
            w, h = max(1, int(w / face_scale)), max(1, int(h / face_scale))
        pad = int(0.25 * w)
        blur_region(out, x - pad, y - pad, w + 2 * pad, h + 2 * pad, blur_strength)
    if detect_bodies:
        scale = 0.75 if max(out.shape[:2]) > 900 else 1.0
        small = cv2.resize(out, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale != 1.0 else out
        rects, weights = HOG_DESCRIPTOR.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)
        for (x, y, w, h), weight in zip(rects, weights):
            if weight < 0.5:
                continue
            if scale != 1.0:
                x, y, w, h = int(x / scale), int(y / scale), int(w / scale), int(h / scale)
            blur_region(out, x, y, w, h, blur_strength)
    return out


def process_image(pil_img: Image.Image, opts: Options) -> NumpyImage:
    bgr = pil_to_bgr(pil_img)
    if opts.remove_text:
        bgr = scrub_text(bgr)
    if opts.blur_people:
        bgr = scrub_people(bgr, blur_strength=opts.blur_strength, detect_bodies=opts.detect_bodies)
    return bgr
