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
GENRE_NAMES = labels["genre_names"]
STYLE_NAMES = labels["style_names"]

# Indices to ignore (Unknown categories)
UNKNOWN_ARTIST_IDX = 0  # "Unknown Artist"
UNKNOWN_GENRE_IDX = GENRE_NAMES.index("Unknown Genre") if "Unknown Genre" in GENRE_NAMES else -1

IMG_SIZE = (224, 224)


def preprocess_image(image_path: str) -> np.ndarray:
    """Load image, resize and apply MobileNetV2 preprocessing."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize(IMG_SIZE)
    arr = np.array(img)
    arr = mb_preprocess(arr)
    arr = np.expand_dims(arr, axis=0) 
    return arr


def get_top_predictions(probs: np.ndarray, names: list, top_k: int, ignore_indices: list = None):
    """Get top-k predictions, optionally ignoring certain indices, and renormalize."""
    if ignore_indices is None:
        ignore_indices = []
    
    # Create mask for valid indices
    mask = np.ones(len(probs), dtype=bool)
    for idx in ignore_indices:
        if 0 <= idx < len(probs):
            mask[idx] = False
    
    # Get valid probabilities and renormalize
    valid_probs = probs.copy()
    valid_probs[~mask] = 0
    
    # Renormalize so valid probs sum to 1
    total = valid_probs.sum()
    if total > 0:
        valid_probs = valid_probs / total
    
    # Get top-k indices
    top_indices = valid_probs.argsort()[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        i = int(idx)
        if valid_probs[i] > 0:
            results.append({
                "index": i,
                "name": names[i],
                "probability": float(valid_probs[i]),
            })
    return results


def predict_top_artists(image_path: str, top_k: int = 3):
    """Legacy function for backward compatibility."""
    result = predict_full(image_path, top_k=top_k)
    return result["artists"]


def predict_full(image_path: str, top_k: int = 3):
    """
    Full prediction returning artists, genres, and styles.
    Filters out 'Unknown' categories and renormalizes probabilities.
    """
    x = preprocess_image(image_path)
    predictions = model.predict(x, verbose=0)

    if not isinstance(predictions, dict):
        raise TypeError(f"Expected dict from model.predict, got {type(predictions)}")

    # Artist predictions (filter Unknown Artist)
    artist_logits = predictions["artist"][0]
    artist_probs = tf.nn.softmax(artist_logits).numpy()
    artists = get_top_predictions(
        artist_probs, ARTIST_NAMES, top_k, 
        ignore_indices=[UNKNOWN_ARTIST_IDX]
    )
    # Convert name to artist_slug format for compatibility
    for a in artists:
        a["artist_slug"] = a.pop("name")

    # Genre predictions (filter Unknown Genre)
    genre_logits = predictions["genre"][0]
    genre_probs = tf.nn.softmax(genre_logits).numpy()
    genres = get_top_predictions(
        genre_probs, GENRE_NAMES, top_k,
        ignore_indices=[UNKNOWN_GENRE_IDX] if UNKNOWN_GENRE_IDX >= 0 else []
    )

    # Style predictions (no unknown to filter)
    style_logits = predictions["style"][0]
    style_probs = tf.nn.softmax(style_logits).numpy()
    styles = get_top_predictions(style_probs, STYLE_NAMES, top_k)

    return {
        "artists": artists,
        "genres": genres,
        "styles": styles,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m ml.predict_artists path/to/image.jpg")
        sys.exit(1)

    image_path = sys.argv[1]
    result = predict_full(image_path, top_k=3)
    
    print("Top-3 artists:")
    for r in result["artists"]:
        print(f"  - {r['artist_slug']}: {r['probability']*100:.1f}%")
    
    print("\nTop-3 genres:")
    for r in result["genres"]:
        print(f"  - {r['name']}: {r['probability']*100:.1f}%")
    
    print("\nTop-3 styles:")
    for r in result["styles"]:
        print(f"  - {r['name']}: {r['probability']*100:.1f}%")
