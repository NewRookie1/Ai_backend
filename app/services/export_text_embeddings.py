"""
Export precomputed MobileCLIP-S0 text embeddings for the Android APK.

Why: on-device you do NOT need the text encoder (~40MB) or the tokenizer.
Bundle ONLY:
  ai_saathi/assets/models/vision_model_quantized.onnx   (~11MB image encoder)
  ai_saathi/assets/models/text_embeddings.json          (this script's output)
  ai_saathi/assets/models/labels.json                   (label list)

The Flutter app then: image -> vision ONNX -> cosine vs these embeddings
-> argmax -> label string. Fully offline.

Usage:
    cd backend
    pip install -r requirements.txt          # includes onnxruntime, transformers, huggingface_hub
    python -m app.services.export_text_embeddings
    # or: python app/services/export_text_embeddings.py --out ../ai_saathi/assets/models

Output text_embeddings.json format:
    {"labels": [...], "prompts": [...], "embeddings": [[...], ...],
     "dim": 512, "logit_scale": 100.0, "model": "Xenova/mobileclip_s0"}
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.mobileclip_classifier import (  # noqa: E402
    ARTISAN_LABELS,
    LOGIT_SCALE,
    MODEL_ID,
    get_text_embeddings,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "ai_saathi", "assets", "models"))
    ap.add_argument("--model", default=None,
                    help="Optional: also download vision_model_quantized.onnx into --out")
    args = ap.parse_args()

    labels, embs, prompts = get_text_embeddings()
    os.makedirs(args.out, exist_ok=True)

    with open(os.path.join(args.out, "text_embeddings.json"), "w") as f:
        json.dump({
            "labels": labels,
            "prompts": prompts,
            "embeddings": embs.tolist(),
            "dim": int(embs.shape[1]),
            "logit_scale": LOGIT_SCALE,
            "model": MODEL_ID,
        }, f)
    with open(os.path.join(args.out, "labels.json"), "w") as f:
        json.dump(ARTISAN_LABELS, f, indent=2)

    print(f"labels: {labels}  dim={embs.shape[1]}")
    print(f"wrote {os.path.join(args.out, 'text_embeddings.json')}")
    print(f"wrote {os.path.join(args.out, 'labels.json')}")

    # Optionally fetch the small quantized vision encoder for the APK.
    if args.model == "quantized" or True:
        try:
            from huggingface_hub import hf_hub_download
            import shutil
            src = hf_hub_download(repo_id=MODEL_ID,
                                  filename="onnx/vision_model_quantized.onnx")
            dst = os.path.join(args.out, "vision_model_quantized.onnx")
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copyfile(src, dst)
            size_mb = os.path.getsize(dst) / 1e6
            print(f"vision encoder -> {dst} ({size_mb:.1f} MB)")
            print("Add to ai_saathi/pubspec.yaml assets: assets/models/")
        except Exception as e:
            print(f"[warn] could not download vision_model_quantized.onnx: {e}")


if __name__ == "__main__":
    main()
