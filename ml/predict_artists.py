from pathlib import Path
import json

import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input as mb_preprocess

# Paths
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "wikiart_mobilenetv2_multihead.keras"
LABELS_PATH = BASE_DIR / "models" / "class_labels.json"

print(f"Loading model from {MODEL_PATH} ...")
model = tf.keras.models.load_model(MODEL_PATH)

with open(LABELS_PATH, "r", encoding="utf-8") as f:
    labels = json.load(f)

ARTIST_NAMES = labels["artist_names"] 

IMG_SIZE = (224, 224)


def preprocess_image(image_path: str) -> np.ndarray:
    """Load image, resize and apply MobileNetV2 preprocessing."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize(IMG_SIZE)
    arr = np.array(img)
    arr = mb_preprocess(arr)
    arr = np.expand_dims(arr, axis=0) 
    return arr


def predict_top_artists(image_path: str, top_k: int = 3):
    x = preprocess_image(image_path)

    predictions = model.predict(x, verbose=0)

    if not isinstance(predictions, dict):
        raise TypeError(
            f"Expected dict from model.predict, got {type(predictions)} "
            f"with value: {predictions}"
        )

    if "artist" not in predictions:
        raise KeyError(
            f"'artist' key not found in predictions. Available keys: {list(predictions.keys())}"
        )

    artist_logits = predictions["artist"][0] 
    artist_probs = tf.nn.softmax(artist_logits).numpy()

    top_indices = artist_probs.argsort()[-top_k:][::-1]

    results = []
    for idx in top_indices:
        i = int(idx)
        results.append(
            {
                "index": i,
                "artist_slug": ARTIST_NAMES[i],
                "probability": float(artist_probs[i]),
            }
        )
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m ml.predict_artists path/to/image.jpg")
        sys.exit(1)

    image_path = sys.argv[1]
    res = predict_top_artists(image_path, top_k=3)
    print("Top-3 artists:")
    for r in res:
        print(f"- {r['artist_slug']}: {r['probability']:.3f}")
