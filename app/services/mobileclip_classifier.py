"""
MobileCLIP-S0 ONNX zero-shot classifier for the Artisan app.

Model: Xenova/mobileclip_s0 (ONNX port of apple/MobileCLIP-S0)
  - onnx/vision_model*.onnx  -> image_embeds
  - onnx/text_model*.onnx    -> text_embeds
  - preprocessor: resize shortest_edge=256, center_crop=256, rescale 1/255,
                  RGB, NO normalize  (see preprocessor_config.json)
  - tokenizer: CLIPTokenizer, context length 77, logit_scale = 100.0
    (same formula as the official Transformers.js example:
     probs = softmax(100 * image_embeds_norm @ text_embeds_norm.T))

Why zero-shot (no training)?
  dataset/ has only 12 images across 5 folders, far too few to train a CNN.
  Zero-shot lets you pass your own product names as labels with no retraining.

Public API (just returns the label string):
    from app.services.mobileclip_classifier import predict_label
    label: str = predict_label(image_bytes)

Labels = dataset folder names:
    ["bamboo_basket", "pottery", "textile", "wooden_craft"]
"""

from __future__ import annotations

import io
import os
from functools import lru_cache
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

try:
    import pillow_avif  # noqa: F401  # enables .avif (1 file in dataset/pottery)
except ImportError:
    pass

MODEL_ID = os.environ.get("MOBILECLIP_MODEL_ID", "Xenova/mobileclip_s0")
# Full-precision by default on server; use the *_quantized.onnx file on phone.
VISION_ONNX_FILE = os.environ.get("MOBILECLIP_VISION_ONNX", "onnx/vision_model.onnx")
TEXT_ONNX_FILE = os.environ.get("MOBILECLIP_TEXT_ONNX", "onnx/text_model.onnx")

IMAGE_SIZE = 256        # crop_size / shortest_edge from preprocessor_config.json
CONTEXT_LENGTH = 77     # CLIP context length
LOGIT_SCALE = 100.0     # matches Transformers.js MobileCLIP example

# ---------------------------------------------------------------------------
# Labels — exactly the dataset/ folder names so predictions map 1:1 to data.
# ---------------------------------------------------------------------------
ARTISAN_LABELS: List[str] = [
    "bamboo_basket",
    "pottery",
    "textile",
    "wooden_craft",
]

# Descriptive prompts greatly improve zero-shot accuracy vs bare folder names.
LABEL_PROMPTS: Dict[str, List[str]] = {
    "bamboo_basket": [
        "a photo of a handmade bamboo basket",
        "a woven bamboo basket craft",
    ],
    "pottery": [
        "a photo of handmade pottery",
        "a clay terracotta pot or cup",
    ],
    "textile": [
        "a photo of a colorful textile fabric",
        "a handwoven saree textile",
    ],
    "wooden_craft": [
        "a photo of a handmade wooden craft",
        "a carved wooden decoration",
    ],
}


# ---------------------------------------------------------------------------
# Preprocessing (must match preprocessor_config.json exactly)
# ---------------------------------------------------------------------------
def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """PIL bytes -> float32 NCHW [1, 3, 256, 256] in 0..1 (no mean/std norm)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    # resize so shortest edge == 256 (BILINEAR == resample:2)
    scale = IMAGE_SIZE / min(w, h)
    img = img.resize((round(w * scale), round(h * scale)), Image.BILINEAR)
    # center crop 256x256
    w, h = img.size
    left, top = (w - IMAGE_SIZE) // 2, (h - IMAGE_SIZE) // 2
    img = img.crop((left, top, left + IMAGE_SIZE, top + IMAGE_SIZE))
    arr = np.asarray(img, dtype=np.float32) / 255.0  # rescale 1/255
    arr = np.transpose(arr, (2, 0, 1))[None, ...]    # HWC -> [1,3,256,256]
    return arr.astype(np.float32)


def _softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max(axis=-1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=-1, keepdims=True)


def _l2norm(x: np.ndarray, axis: int = -1, eps: float = 1e-12) -> np.ndarray:
    return x / np.maximum(np.linalg.norm(x, axis=axis, keepdims=True), eps)


# ---------------------------------------------------------------------------
# ONNX sessions (lazy, cached)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _get_sessions():
    """Load (vision_session, text_session, tokenizer). Downloads from HF once."""
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer

    vision_path = hf_hub_download(repo_id=MODEL_ID, filename=VISION_ONNX_FILE)
    text_path = hf_hub_download(repo_id=MODEL_ID, filename=TEXT_ONNX_FILE)
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = max(1, (os.cpu_count() or 4) - 1)
    vision = ort.InferenceSession(vision_path, sess_options=opts,
                                  providers=["CPUExecutionProvider"])
    text = ort.InferenceSession(text_path, sess_options=opts,
                                providers=["CPUExecutionProvider"])
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    return vision, text, tokenizer


@lru_cache(maxsize=1)
def get_text_embeddings() -> Tuple[List[str], np.ndarray, List[str]]:
    """
    Returns (labels, normalized_text_embeds [num_labels, dim], prompts_used).
    Each label embedding = L2-normalized mean of its prompt embeddings.
    Cached so the text encoder runs only once per process.
    """
    vision, text_sess, tokenizer = _get_sessions()
    in_names = [i.name for i in text_sess.get_inputs()]

    labels, embs, prompts_used = [], [], []
    for label in ARTISAN_LABELS:
        prompts = LABEL_PROMPTS.get(label, [f"a photo of a {label}"])
        tok = tokenizer(prompts, padding="max_length", max_length=CONTEXT_LENGTH,
                        truncation=True, return_tensors="np")
        feed = {}
        # input names are typically input_ids + attention_mask
        for k, v in tok.items():
            if k in in_names:
                feed[k] = v.astype(np.int64)
        if "input_ids" in in_names and "input_ids" not in feed:
            feed["input_ids"] = tok["input_ids"].astype(np.int64)
        out = text_sess.run(None, feed)[0]          # [num_prompts, dim]
        out = _l2norm(np.asarray(out, dtype=np.float32))
        mean = _l2norm(out.mean(axis=0, keepdims=True))[0]
        labels.append(label)
        embs.append(mean)
        prompts_used.append(" || ".join(prompts))
    return labels, np.stack(embs).astype(np.float32), prompts_used


def _run_vision(pixel_values: np.ndarray) -> np.ndarray:
    vision, _, _ = _get_sessions()
    name = vision.get_inputs()[0].name
    out = vision.run(None, {name: pixel_values})[0]  # [1, dim]
    return _l2norm(np.asarray(out, dtype=np.float32))[0]


# ---------------------------------------------------------------------------
# Public API — just the label
# ---------------------------------------------------------------------------
def predict_label(image_bytes: bytes) -> str:
    """Zero-shot classify raw image bytes -> one of ARTISAN_LABELS. Just the label."""
    return predict_with_scores(image_bytes)[0]


def predict_with_scores(image_bytes: bytes) -> Tuple[str, float, Dict[str, float]]:
    """Returns (label, confidence, {label: prob}). Confidence = softmax prob."""
    labels, text_embs, _ = get_text_embeddings()
    img_emb = _run_vision(preprocess_image(image_bytes))          # [dim]
    logits = LOGIT_SCALE * (img_emb @ text_embs.T)               # [num_labels]
    probs = _softmax(logits)
    idx = int(np.argmax(probs))
    return labels[idx], float(probs[idx]), {l: float(p) for l, p in zip(labels, probs)}


def classify_file(path: str) -> str:
    """Convenience: image path -> label string."""
    with open(path, "rb") as f:
        return predict_label(f.read())


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        try:
            label, conf, scores = predict_with_scores(open(p, "rb").read())
            print(f"{p} -> {label} ({conf:.3f}) {scores}")
        except Exception as e:
            print(f"{p} -> ERROR: {e}")
