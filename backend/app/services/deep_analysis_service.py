"""Deep analysis service - comprehensive art analysis using CV + LLM.

This module provides deep analysis functionality including:
- Color extraction and psychology analysis
- Composition analysis (saliency, rule of thirds, symmetry)
- Scene/semantic analysis (objects, text, symbolism)
- Technique analysis
- Historical context interpretation

Uses computer vision for feature extraction and LLM for interpretation.
"""
import json
import logging
import math
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import settings
from app.services.llm_client import get_cached_provider, LLMError, clean_think_tags
from app.services.prompts import (
    COLOR_PSYCHOLOGY_SYSTEM_PROMPT,
    build_color_psychology_prompt,
    COMPOSITION_ANALYSIS_SYSTEM_PROMPT,
    build_composition_prompt,
    SCENE_ANALYSIS_SYSTEM_PROMPT,
    build_scene_prompt,
    TECHNIQUE_ANALYSIS_SYSTEM_PROMPT,
    build_technique_prompt,
    HISTORICAL_CONTEXT_SYSTEM_PROMPT,
    build_historical_context_prompt,
    DEEP_ANALYSIS_SUMMARY_SYSTEM_PROMPT,
    build_summary_prompt,
    format_prediction_for_prompt,
)

logger = logging.getLogger(__name__)


# ============ Robust JSON Parser ============

def extract_json_from_response(text: str) -> Optional[Dict]:
    """Extract JSON from LLM response that may contain extra text.
    
    Handles cases where LLM outputs:
    - Markdown code blocks: ```json {...} ```
    - Extra text before/after JSON
    - Multiple JSON objects (takes first valid)
    """
    if not text:
        return None
    
    # First try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code block
    code_block_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
    matches = re.findall(code_block_pattern, text)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    # Try to find JSON object in text using brace matching
    brace_start = text.find('{')
    if brace_start != -1:
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[brace_start:], start=brace_start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = text[brace_start:i+1]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            break
    
    return None


# ============ Inline Marker Parser ============

# Marker pattern: {type|value|optional_label} or {type|value} (single braces)
MARKER_PATTERN = re.compile(r'\{(\w+)\|([^}|]+)(?:\|([^}]+))?\}')

# Marker type configurations with icons
MARKER_TYPES = {
    "color": {"icon": "palette", "css_class": "marker-color"},
    "technique": {"icon": "brush", "css_class": "marker-technique"},
    "composition": {"icon": "layers", "css_class": "marker-composition"},
    "mood": {"icon": "heart", "css_class": "marker-mood"},
    "era": {"icon": "clock", "css_class": "marker-era"},
    "artist": {"icon": "user", "css_class": "marker-artist"},
}


def parse_inline_markers(text: str) -> Dict[str, Any]:
    """Parse inline markers from summary text.
    
    Finds all {type|value|label} markers and returns:
    - cleaned_text: Text with markers replaced by placeholders
    - markers: List of extracted markers with positions
    - html_text: Text with markers replaced by HTML spans
    
    Args:
        text: Raw text containing {type|value|label} markers
        
    Returns:
        Dict with cleaned_text, markers list, and html_text
    """
    markers = []
    marker_count = 0
    
    def replace_marker(match):
        nonlocal marker_count
        marker_type = match.group(1).lower()
        value = match.group(2).strip()
        label = match.group(3).strip() if match.group(3) else value
        
        # Get marker config
        config = MARKER_TYPES.get(marker_type, {"icon": "info", "css_class": "marker-generic"})
        
        marker = {
            "id": f"marker_{marker_count}",
            "type": marker_type,
            "value": value,
            "label": label,
            "icon": config["icon"],
            "css_class": config["css_class"],
            "position": match.start()
        }
        markers.append(marker)
        marker_count += 1
        
        # Return placeholder for cleaned text
        return f"[[MARKER_{marker['id']}]]"
    
    # Replace markers with placeholders
    cleaned_text = MARKER_PATTERN.sub(replace_marker, text)
    
    # Generate HTML version with styled spans
    def to_html_marker(match):
        marker_type = match.group(1).lower()
        value = match.group(2).strip()
        label = match.group(3).strip() if match.group(3) else value
        config = MARKER_TYPES.get(marker_type, {"icon": "info", "css_class": "marker-generic"})
        
        # Special handling for color markers
        if marker_type == "color" and value.startswith("#"):
            return f'<span class="inline-marker {config["css_class"]}" data-type="{marker_type}" data-value="{value}"><span class="color-swatch" style="background-color:{value}"></span>{label}</span>'
        
        return f'<span class="inline-marker {config["css_class"]}" data-type="{marker_type}" data-value="{value}" data-icon="{config["icon"]}">{label}</span>'
    
    # Parse with same pattern (already using single braces)
    html_text = MARKER_PATTERN.sub(to_html_marker, text)
    
    return {
        "raw_text": text,
        "cleaned_text": cleaned_text,
        "markers": markers,
        "html_text": html_text,
        "marker_count": len(markers)
    }


def extract_all_colors_from_markers(markers: List[Dict]) -> List[str]:
    """Extract all color hex codes from markers."""
    return [m["value"] for m in markers if m["type"] == "color" and m["value"].startswith("#")]


# ============ Color Analysis ============

# Color name mapping (basic)
COLOR_NAMES = {
    (255, 0, 0): "красный",
    (0, 255, 0): "зелёный",
    (0, 0, 255): "синий",
    (255, 255, 0): "жёлтый",
    (255, 165, 0): "оранжевый",
    (128, 0, 128): "фиолетовый",
    (255, 192, 203): "розовый",
    (165, 42, 42): "коричневый",
    (0, 0, 0): "чёрный",
    (255, 255, 255): "белый",
    (128, 128, 128): "серый",
    (0, 128, 128): "бирюзовый",
    (128, 0, 0): "бордовый",
    (0, 128, 0): "тёмно-зелёный",
    (0, 0, 128): "тёмно-синий",
    (245, 222, 179): "пшеничный",
    (210, 180, 140): "загар",
    (139, 69, 19): "сиена",
    (205, 133, 63): "охра",
}


def rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Convert RGB to LAB color space."""
    # Normalize RGB to 0-1
    r, g, b = [x / 255.0 for x in rgb]
    
    # Apply gamma correction
    def gamma_correct(c):
        if c > 0.04045:
            return ((c + 0.055) / 1.055) ** 2.4
        return c / 12.92
    
    r, g, b = map(gamma_correct, (r, g, b))
    
    # Convert to XYZ
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    # Normalize for D65 illuminant
    x, y, z = x / 0.95047, y / 1.0, z / 1.08883
    
    # Convert to LAB
    def f(t):
        if t > 0.008856:
            return t ** (1/3)
        return 7.787 * t + 16/116
    
    L = 116 * f(y) - 16
    a = 500 * (f(x) - f(y))
    b_val = 200 * (f(y) - f(z))
    
    return (L, a, b_val)


def get_color_temperature(rgb: Tuple[int, int, int]) -> str:
    """Determine if a color is warm, cool, or neutral."""
    r, g, b = rgb
    
    # Convert to hue
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    
    if max_c == min_c:
        return "neutral"
    
    d = max_c - min_c
    
    if max_c == r:
        h = (g - b) / d + (6 if g < b else 0)
    elif max_c == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    
    h = h / 6  # Normalize to 0-1
    
    # Warm colors: red, orange, yellow (roughly 0-0.17 and 0.92-1.0)
    # Cool colors: green, blue, purple (roughly 0.25-0.75)
    
    if h < 0.17 or h > 0.92:
        return "warm"
    elif 0.17 <= h < 0.42:  # Yellow-green to green
        return "neutral"
    elif 0.42 <= h < 0.75:  # Green-blue to blue-purple
        return "cool"
    else:
        return "warm"


def get_nearest_color_name(rgb: Tuple[int, int, int]) -> str:
    """Find the nearest named color."""
    min_dist = float('inf')
    nearest_name = "неизвестный"
    
    for ref_rgb, name in COLOR_NAMES.items():
        dist = sum((a - b) ** 2 for a, b in zip(rgb, ref_rgb))
        if dist < min_dist:
            min_dist = dist
            nearest_name = name
    
    return nearest_name


def extract_dominant_colors(image_path: str, n_colors: int = 7) -> List[Dict[str, Any]]:
    """Extract dominant colors using k-means clustering."""
    try:
        # Load and resize image for speed
        img = Image.open(image_path).convert('RGB')
        img.thumbnail((200, 200))
        
        pixels = np.array(img).reshape(-1, 3).astype(np.float32)
        
        # Simple k-means implementation
        # Initialize centroids randomly
        np.random.seed(42)
        indices = np.random.choice(len(pixels), n_colors, replace=False)
        centroids = pixels[indices].copy()
        
        for _ in range(20):  # 20 iterations
            # Assign points to nearest centroid
            distances = np.sqrt(((pixels[:, np.newaxis] - centroids) ** 2).sum(axis=2))
            labels = np.argmin(distances, axis=1)
            
            # Update centroids
            new_centroids = np.array([
                pixels[labels == k].mean(axis=0) if (labels == k).any() else centroids[k]
                for k in range(n_colors)
            ])
            
            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids
        
        # Calculate percentages
        _, counts = np.unique(labels, return_counts=True)
        percentages = counts / len(labels)
        
        # Sort by percentage
        sorted_indices = np.argsort(percentages)[::-1]
        
        colors = []
        for idx in sorted_indices:
            rgb = tuple(map(int, centroids[idx]))
            lab = rgb_to_lab(rgb)
            colors.append({
                "hex": "#{:02x}{:02x}{:02x}".format(*rgb),
                "rgb": list(rgb),
                "lab": list(lab),
                "percentage": float(percentages[idx]),
                "name": get_nearest_color_name(rgb),
                "temperature": get_color_temperature(rgb)
            })
        
        return colors
        
    except Exception as e:
        logger.error(f"Error extracting colors: {e}")
        return []


def calculate_color_metrics(image_path: str) -> Dict[str, float]:
    """Calculate overall color metrics (contrast, saturation, brightness)."""
    try:
        img = Image.open(image_path).convert('RGB')
        img.thumbnail((300, 300))
        pixels = np.array(img).astype(np.float32)
        
        # Calculate brightness (mean luminance)
        luminance = 0.299 * pixels[:,:,0] + 0.587 * pixels[:,:,1] + 0.114 * pixels[:,:,2]
        brightness = luminance.mean() / 255.0
        
        # Calculate contrast (std of luminance)
        contrast = luminance.std() / 128.0  # Normalize roughly to 0-1
        contrast = min(1.0, contrast)
        
        # Calculate saturation
        max_rgb = pixels.max(axis=2)
        min_rgb = pixels.min(axis=2)
        
        with np.errstate(divide='ignore', invalid='ignore'):
            saturation = np.where(max_rgb > 0, (max_rgb - min_rgb) / max_rgb, 0)
        
        avg_saturation = float(np.nanmean(saturation))
        
        return {
            "brightness": float(brightness),
            "overall_contrast": float(contrast),
            "overall_saturation": float(avg_saturation)
        }
        
    except Exception as e:
        logger.error(f"Error calculating color metrics: {e}")
        return {"brightness": 0.5, "overall_contrast": 0.5, "overall_saturation": 0.5}


def extract_color_features(image_path: str) -> Dict[str, Any]:
    """Extract all color features from image."""
    colors = extract_dominant_colors(image_path, n_colors=7)
    metrics = calculate_color_metrics(image_path)
    
    # Calculate warm/cool ratio from dominant colors
    warm_total = sum(c["percentage"] for c in colors if c["temperature"] == "warm")
    cool_total = sum(c["percentage"] for c in colors if c["temperature"] == "cool")
    total = warm_total + cool_total
    
    warm_ratio = warm_total / total if total > 0 else 0.5
    cool_ratio = cool_total / total if total > 0 else 0.5
    
    return {
        "dominant_colors": colors,
        "warm_ratio": warm_ratio,
        "cool_ratio": cool_ratio,
        **metrics
    }


# ============ Composition Analysis ============

def compute_saliency_map(image_path: str) -> np.ndarray:
    """Compute saliency map using spectral residual approach."""
    try:
        from scipy.ndimage import uniform_filter, gaussian_filter
        
        img = Image.open(image_path).convert('L')
        img.thumbnail((256, 256))
        gray = np.array(img, dtype=np.float32)
        
        # FFT
        fft = np.fft.fft2(gray)
        fft_shifted = np.fft.fftshift(fft)
        
        # Log amplitude spectrum
        amplitude = np.abs(fft_shifted)
        log_amplitude = np.log(amplitude + 1e-10)
        
        # Average filter for spectral residual
        avg_log_amplitude = uniform_filter(log_amplitude, size=3)
        spectral_residual = log_amplitude - avg_log_amplitude
        
        # Reconstruct
        phase = np.angle(fft_shifted)
        saliency_fft = np.exp(spectral_residual) * np.exp(1j * phase)
        saliency = np.fft.ifft2(np.fft.ifftshift(saliency_fft))
        saliency = np.abs(saliency) ** 2
        
        # Gaussian blur for smoothing
        saliency = gaussian_filter(saliency, sigma=10)
        
        # Normalize
        saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-10)
        
        return saliency
        
    except ImportError:
        logger.warning("scipy not available, using simple saliency")
        return _simple_saliency(image_path)
    except Exception as e:
        logger.error(f"Error computing saliency: {e}")
        return _simple_saliency(image_path)


def _simple_saliency(image_path: str) -> np.ndarray:
    """Simple saliency based on contrast (fallback when scipy not available)."""
    try:
        from scipy.ndimage import sobel, gaussian_filter
        
        img = Image.open(image_path).convert('L')
        img.thumbnail((256, 256))
        gray = np.array(img, dtype=np.float32)
        
        # Simple edge detection as saliency proxy
        gx = sobel(gray, axis=1)
        gy = sobel(gray, axis=0)
        edges = np.sqrt(gx**2 + gy**2)
        saliency = gaussian_filter(edges, sigma=5)
        saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-10)
        
        return saliency
    except ImportError:
        # Ultra-simple fallback without scipy
        img = Image.open(image_path).convert('L')
        img.thumbnail((256, 256))
        gray = np.array(img, dtype=np.float32)
        
        # Simple gradient-based saliency
        gx = np.abs(np.diff(gray, axis=1, append=gray[:, -1:]))
        gy = np.abs(np.diff(gray, axis=0, append=gray[-1:, :]))
        edges = np.sqrt(gx**2 + gy**2)
        
        # Simple smoothing using convolution
        kernel_size = 5
        kernel = np.ones((kernel_size, kernel_size)) / (kernel_size ** 2)
        
        # Pad and convolve
        pad = kernel_size // 2
        padded = np.pad(edges, pad, mode='edge')
        saliency = np.zeros_like(edges)
        for i in range(edges.shape[0]):
            for j in range(edges.shape[1]):
                saliency[i, j] = np.sum(padded[i:i+kernel_size, j:j+kernel_size] * kernel)
        
        saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-10)
        return saliency


def compute_symmetry(image_path: str) -> Tuple[float, float]:
    """Compute horizontal and vertical symmetry scores."""
    try:
        img = Image.open(image_path).convert('L')
        img.thumbnail((128, 128))
        gray = np.array(img, dtype=np.float32)
        
        h, w = gray.shape
        
        # Horizontal symmetry (left vs right)
        left = gray[:, :w//2]
        right = gray[:, w//2:w//2 + left.shape[1]][:, ::-1]
        
        if left.shape == right.shape:
            diff_h = np.abs(left - right).mean()
            h_symmetry = 1.0 - (diff_h / 255.0)
        else:
            h_symmetry = 0.5
        
        # Vertical symmetry (top vs bottom)
        top = gray[:h//2, :]
        bottom = gray[h//2:h//2 + top.shape[0], :][::-1, :]
        
        if top.shape == bottom.shape:
            diff_v = np.abs(top - bottom).mean()
            v_symmetry = 1.0 - (diff_v / 255.0)
        else:
            v_symmetry = 0.5
        
        return (float(h_symmetry), float(v_symmetry))
        
    except Exception as e:
        logger.error(f"Error computing symmetry: {e}")
        return (0.5, 0.5)


def compute_rule_of_thirds_alignment(saliency: np.ndarray) -> Tuple[float, List[Dict]]:
    """Check how well salient points align with rule of thirds."""
    h, w = saliency.shape
    
    # Rule of thirds lines
    third_h = [h // 3, 2 * h // 3]
    third_w = [w // 3, 2 * w // 3]
    
    # Find local maxima (focal points)
    try:
        from scipy.ndimage import maximum_filter
        local_max = maximum_filter(saliency, size=20) == saliency
    except ImportError:
        # Fallback: simple thresholding
        local_max = saliency > (saliency.mean() + saliency.std())
    
    threshold = saliency.mean() + saliency.std()
    focal_mask = local_max & (saliency > threshold)
    
    focal_points = []
    ys, xs = np.where(focal_mask)
    strengths = saliency[focal_mask]
    
    # Sort by strength and take top 5
    sorted_indices = np.argsort(strengths)[::-1][:5]
    
    for idx in sorted_indices:
        y, x = ys[idx], xs[idx]
        focal_points.append({
            "x": float(x / w),
            "y": float(y / h),
            "strength": float(strengths[idx])
        })
    
    # Calculate alignment score
    if not focal_points:
        return (0.3, [{"x": 0.5, "y": 0.5, "strength": 0.5}])
    
    total_alignment = 0
    for fp in focal_points:
        x_px = fp["x"] * w
        y_px = fp["y"] * h
        
        # Distance to nearest third line
        min_x_dist = min(abs(x_px - third_w[0]), abs(x_px - third_w[1]))
        min_y_dist = min(abs(y_px - third_h[0]), abs(y_px - third_h[1]))
        
        # Normalize (closer = higher score)
        x_alignment = 1.0 - min(min_x_dist / (w / 6), 1.0)
        y_alignment = 1.0 - min(min_y_dist / (h / 6), 1.0)
        
        total_alignment += (x_alignment + y_alignment) / 2 * fp["strength"]
    
    total_strength = sum(fp["strength"] for fp in focal_points)
    alignment_score = total_alignment / total_strength if total_strength > 0 else 0.3
    
    return (float(alignment_score), focal_points)


def determine_visual_weight_distribution(saliency: np.ndarray) -> str:
    """Determine which part of the image has more visual weight."""
    h, w = saliency.shape
    
    left = saliency[:, :w//2].mean()
    right = saliency[:, w//2:].mean()
    top = saliency[:h//2, :].mean()
    bottom = saliency[h//2:, :].mean()
    
    threshold = 0.15  # 15% difference to be considered unbalanced
    
    h_diff = (left - right) / (left + right + 1e-10)
    v_diff = (top - bottom) / (top + bottom + 1e-10)
    
    if abs(h_diff) < threshold and abs(v_diff) < threshold:
        return "balanced"
    
    if abs(h_diff) > abs(v_diff):
        return "left-heavy" if h_diff > 0 else "right-heavy"
    else:
        return "top-heavy" if v_diff > 0 else "bottom-heavy"


def detect_perspective_lines(image_path: str) -> Tuple[bool, List[Dict]]:
    """Detect vanishing points using line detection."""
    try:
        from PIL import ImageFilter
        
        img = Image.open(image_path).convert('L')
        img.thumbnail((400, 400))
        
        # Edge detection
        edges = img.filter(ImageFilter.FIND_EDGES)
        edges = np.array(edges)
        
        # Simple Hough-like line detection would require OpenCV
        # For now, return basic detection based on edge density
        h, w = edges.shape
        
        # Check for strong vertical/horizontal edges (indicates architecture/perspective)
        center_strip_v = edges[:, w//3:2*w//3].mean()
        center_strip_h = edges[h//3:2*h//3, :].mean()
        
        has_perspective = center_strip_v > 30 or center_strip_h > 30
        
        vanishing_points = []
        if has_perspective:
            # Estimate vanishing point in upper center (common for landscapes/architecture)
            vanishing_points.append({"x": 0.5, "y": 0.3})
        
        return (has_perspective, vanishing_points)
        
    except Exception as e:
        logger.error(f"Error detecting perspective: {e}")
        return (False, [])


def extract_composition_features(image_path: str) -> Dict[str, Any]:
    """Extract all composition features from image."""
    saliency = compute_saliency_map(image_path)
    
    # Saliency center of mass
    h, w = saliency.shape
    y_coords, x_coords = np.mgrid[0:h, 0:w]
    total_saliency = saliency.sum()
    
    if total_saliency > 0:
        center_x = (x_coords * saliency).sum() / total_saliency / w
        center_y = (y_coords * saliency).sum() / total_saliency / h
    else:
        center_x, center_y = 0.5, 0.5
    
    h_symmetry, v_symmetry = compute_symmetry(image_path)
    rot_alignment, focal_points = compute_rule_of_thirds_alignment(saliency)
    weight_dist = determine_visual_weight_distribution(saliency)
    has_perspective, vanishing = detect_perspective_lines(image_path)
    
    return {
        "saliency_center_x": float(center_x),
        "saliency_center_y": float(center_y),
        "rule_of_thirds_alignment": float(rot_alignment),
        "horizontal_symmetry": float(h_symmetry),
        "vertical_symmetry": float(v_symmetry),
        "visual_weight_distribution": weight_dist,
        "focal_points": focal_points,
        "perspective_lines_detected": has_perspective,
        "vanishing_points": vanishing
    }


# ============ Scene Analysis ============
# Vision prompts imported from prompts.py
from app.services.prompts import VISION_SCENE_SYSTEM_PROMPT, VISION_SCENE_PROMPT


async def extract_scene_features_with_vision(image_path: str) -> Dict[str, Any]:
    """Extract scene features using Vision LLM.
    
    This sends the image to a vision-capable LLM (GPT-4o, Claude Vision, etc.)
    to extract objects, descriptions, and text.
    """
    from app.services.llm_client import generate_with_vision, LLMError
    from app.core.config import settings
    
    if not settings.VISION_LLM_ENABLED:
        logger.info("Vision LLM disabled, returning empty scene features")
        return {
            "detected_objects": [],
            "style_tags": [],
            "clip_description": None,
            "detected_text": [],
            "primary_subject": None
        }
    
    try:
        response = await generate_with_vision(
            image_path=image_path,
            prompt=VISION_SCENE_PROMPT,
            system_prompt=VISION_SCENE_SYSTEM_PROMPT,
            max_tokens=2500,
            temperature=0.3  # Lower temperature for more consistent JSON
        )
        
        # Parse JSON response using robust extractor
        data = extract_json_from_response(response)
        if data:
            return {
                "detected_objects": data.get("detected_objects", []),
                "style_tags": data.get("style_tags", []),
                "clip_description": data.get("description"),
                "detected_text": data.get("detected_text", []),
                "primary_subject": data.get("primary_subject"),
                "mood": data.get("mood"),
                "setting": data.get("setting")
            }
        else:
            logger.warning("Failed to parse Vision LLM JSON response")
            # Return raw text as description
            return {
                "detected_objects": [],
                "style_tags": [],
                "clip_description": response[:500] if response else None,
                "detected_text": [],
                "primary_subject": None
            }
            
    except LLMError as e:
        logger.error(f"Vision LLM failed: {e}")
        return {
            "detected_objects": [],
            "style_tags": [],
            "clip_description": f"Vision analysis failed: {str(e)}",
            "detected_text": [],
            "primary_subject": None
        }


def extract_scene_features(image_path: str) -> Dict[str, Any]:
    """Extract scene/semantic features (sync wrapper).
    
    Note: This is a sync function for compatibility. For async context,
    use extract_scene_features_with_vision directly.
    """
    # Return empty for sync context - actual extraction happens in async analyze_scene
    return {
        "detected_objects": [],
        "style_tags": [],
        "clip_description": None,
        "detected_text": [],
        "primary_subject": None
    }


# ============ LLM Integration ============

async def analyze_color_psychology(color_features: Dict[str, Any]) -> Dict[str, Any]:
    """Generate color psychology analysis using LLM."""
    if settings.LLM_PROVIDER.lower() == "none":
        return _build_stub_color_analysis(color_features)
    
    try:
        provider = get_cached_provider()
        user_prompt = build_color_psychology_prompt(color_features)
        
        response = await provider.generate(
            system_prompt=COLOR_PSYCHOLOGY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2500,
            temperature=0.7
        )
        
        cleaned = clean_think_tags(response)
        
        # Parse JSON response using robust extractor
        result = extract_json_from_response(cleaned)
        if result:
            result["source"] = settings.LLM_PROVIDER
            return result
        else:
            logger.warning("Failed to parse color analysis JSON, using extracted text")
            return {
                "palette_interpretation": cleaned[:500],
                "mood_tags": ["неопределённый"],
                "color_harmony": "смешанная",
                "emotional_impact": "Требуется дополнительный анализ.",
                "source": settings.LLM_PROVIDER
            }
            
    except LLMError as e:
        logger.error(f"LLM color analysis failed: {e}")
        return _build_stub_color_analysis(color_features)


def _build_stub_color_analysis(color_features: Dict) -> Dict:
    """Build stub color analysis."""
    colors = color_features.get("dominant_colors", [])
    color_names = [c.get("name", "") for c in colors[:3]]
    
    return {
        "palette_interpretation": f"Палитра состоит преимущественно из {', '.join(color_names)}.",
        "mood_tags": ["нейтральный"],
        "color_harmony": "смешанная",
        "emotional_impact": "Анализ недоступен (LLM не настроен).",
        "source": "stub"
    }


async def analyze_composition(composition_features: Dict[str, Any]) -> Dict[str, Any]:
    """Generate composition analysis using LLM."""
    if settings.LLM_PROVIDER.lower() == "none":
        return _build_stub_composition_analysis(composition_features)
    
    try:
        provider = get_cached_provider()
        user_prompt = build_composition_prompt(composition_features)
        
        response = await provider.generate(
            system_prompt=COMPOSITION_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2500,
            temperature=0.7
        )
        
        cleaned = clean_think_tags(response)
        
        result = extract_json_from_response(cleaned)
        if result:
            result["source"] = settings.LLM_PROVIDER
            return result
        else:
            logger.warning("Failed to parse composition JSON")
            return {
                "composition_type": "смешанная",
                "balance_description": cleaned[:300],
                "visual_flow": "Требуется дополнительный анализ.",
                "focal_point_analysis": "Основной фокус в центральной части.",
                "spatial_depth": "Умеренная глубина.",
                "dynamism_level": "moderate",
                "source": settings.LLM_PROVIDER
            }
            
    except LLMError as e:
        logger.error(f"LLM composition analysis failed: {e}")
        return _build_stub_composition_analysis(composition_features)


def _build_stub_composition_analysis(comp_features: Dict) -> Dict:
    """Build stub composition analysis."""
    weight = comp_features.get("visual_weight_distribution", "balanced")
    rot = comp_features.get("rule_of_thirds_alignment", 0.5)
    
    return {
        "composition_type": "asymmetrical" if weight != "balanced" else "balanced",
        "balance_description": f"Визуальный вес: {weight}.",
        "visual_flow": "Анализ недоступен.",
        "focal_point_analysis": f"Соответствие правилу третей: {rot*100:.0f}%.",
        "spatial_depth": "Анализ недоступен.",
        "dynamism_level": "moderate",
        "source": "stub"
    }


async def analyze_scene(
    scene_features: Dict[str, Any],
    ml_predictions: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generate scene/semantic analysis using LLM."""
    if settings.LLM_PROVIDER.lower() == "none":
        return _build_stub_scene_analysis(scene_features)
    
    try:
        provider = get_cached_provider()
        user_prompt = build_scene_prompt(scene_features, ml_predictions)
        
        response = await provider.generate(
            system_prompt=SCENE_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2500,
            temperature=0.7
        )
        
        cleaned = clean_think_tags(response)
        
        result = extract_json_from_response(cleaned)
        if result:
            result["source"] = settings.LLM_PROVIDER
            return result
        else:
            return {
                "narrative_interpretation": cleaned[:400],
                "symbolism": "Требуется дополнительный анализ.",
                "subject_analysis": "Анализ сюжета.",
                "text_interpretation": None,
                "cultural_references": [],
                "source": settings.LLM_PROVIDER
            }
            
    except LLMError as e:
        logger.error(f"LLM scene analysis failed: {e}")
        return _build_stub_scene_analysis(scene_features)


def _build_stub_scene_analysis(scene_features: Dict) -> Dict:
    """Build stub scene analysis."""
    return {
        "narrative_interpretation": "Анализ сюжета недоступен (LLM не настроен).",
        "symbolism": "Символика не определена.",
        "subject_analysis": "Требуется настройка LLM.",
        "text_interpretation": None,
        "cultural_references": [],
        "source": "stub"
    }


async def analyze_technique(
    ml_predictions: Dict[str, Any],
    color_features: Dict[str, Any] = None,
    composition_features: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generate technique analysis using LLM."""
    if settings.LLM_PROVIDER.lower() == "none":
        return _build_stub_technique_analysis(ml_predictions)
    
    try:
        provider = get_cached_provider()
        user_prompt = build_technique_prompt(ml_predictions, color_features, composition_features)
        
        response = await provider.generate(
            system_prompt=TECHNIQUE_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2500,
            temperature=0.7
        )
        
        cleaned = clean_think_tags(response)
        
        result = extract_json_from_response(cleaned)
        if result:
            result["source"] = settings.LLM_PROVIDER
            return result
        else:
            return {
                "brushwork": cleaned[:300],
                "light_analysis": "Требуется дополнительный анализ.",
                "spatial_treatment": "Анализ пространства.",
                "medium_estimation": "неизвестно",
                "technical_skill_indicators": [],
                "source": settings.LLM_PROVIDER
            }
            
    except LLMError as e:
        logger.error(f"LLM technique analysis failed: {e}")
        return _build_stub_technique_analysis(ml_predictions)


def _build_stub_technique_analysis(ml_predictions: Dict) -> Dict:
    """Build stub technique analysis."""
    artist = "неизвестный"
    if ml_predictions and ml_predictions.get("artists"):
        artist = ml_predictions["artists"][0].get("name", "неизвестный")
    
    return {
        "brushwork": f"Стиль похож на работы {artist}.",
        "light_analysis": "Анализ света недоступен.",
        "spatial_treatment": "Анализ пространства недоступен.",
        "medium_estimation": "неизвестно",
        "technical_skill_indicators": [],
        "source": "stub"
    }


async def analyze_historical_context(
    ml_predictions: Dict[str, Any],
    color_analysis: Dict[str, Any] = None,
    composition_analysis: Dict[str, Any] = None,
    scene_analysis: Dict[str, Any] = None,
    technique_analysis: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generate historical context analysis using LLM."""
    if settings.LLM_PROVIDER.lower() == "none":
        return _build_stub_historical_analysis(ml_predictions)
    
    try:
        provider = get_cached_provider()
        user_prompt = build_historical_context_prompt(
            ml_predictions,
            color_analysis,
            composition_analysis,
            scene_analysis,
            technique_analysis
        )
        
        response = await provider.generate(
            system_prompt=HISTORICAL_CONTEXT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1500,
            temperature=0.7
        )
        
        cleaned = clean_think_tags(response)
        
        result = extract_json_from_response(cleaned)
        if result:
            result["source"] = settings.LLM_PROVIDER
            return result
        else:
            return {
                "estimated_era": "Неопределённая эпоха",
                "art_movement_connections": [],
                "artistic_influences": cleaned[:400],
                "historical_significance": "Требуется дополнительный анализ.",
                "cultural_context": "Анализ контекста.",
                "confidence_note": "Это интерпретация, а не строгая атрибуция.",
                "source": settings.LLM_PROVIDER
            }
            
    except LLMError as e:
        logger.error(f"LLM historical analysis failed: {e}")
        return _build_stub_historical_analysis(ml_predictions)


def _build_stub_historical_analysis(ml_predictions: Dict) -> Dict:
    """Build stub historical analysis."""
    style = "неизвестный стиль"
    if ml_predictions and ml_predictions.get("styles"):
        style = ml_predictions["styles"][0].get("name", "неизвестный стиль")
    
    return {
        "estimated_era": "Неопределённая эпоха",
        "art_movement_connections": [style],
        "artistic_influences": "Анализ влияний недоступен (LLM не настроен).",
        "historical_significance": "Требуется настройка LLM для анализа.",
        "cultural_context": "Контекст не определён.",
        "confidence_note": "Данные ограничены из-за отсутствия LLM.",
        "source": "stub"
    }


async def generate_summary(
    color_analysis: Dict,
    composition_analysis: Dict,
    scene_analysis: Dict,
    technique_analysis: Dict,
    historical_analysis: Dict,
    ml_predictions: Dict
) -> Dict[str, Any]:
    """Generate final summary synthesizing all analyses.
    
    Returns a rich summary with inline markers parsed for frontend rendering.
    """
    if settings.LLM_PROVIDER.lower() == "none":
        raw_summary = _build_stub_summary(ml_predictions)
        return parse_inline_markers(raw_summary)
    
    try:
        provider = get_cached_provider()
        user_prompt = build_summary_prompt(
            color_analysis,
            composition_analysis,
            scene_analysis,
            technique_analysis,
            historical_analysis,
            ml_predictions
        )
        
        # Use high max_tokens for comprehensive analysis (8000+ words possible)
        response = await provider.generate(
            system_prompt=DEEP_ANALYSIS_SUMMARY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=8000,  # Increased significantly for deep analysis
            temperature=0.75  # Slightly higher for more creative writing
        )
        
        cleaned_response = clean_think_tags(response)
        
        # Parse inline markers and return structured result
        return parse_inline_markers(cleaned_response)
        
    except LLMError as e:
        logger.error(f"LLM summary generation failed: {e}")
        raw_summary = _build_stub_summary(ml_predictions)
        return parse_inline_markers(raw_summary)


def _build_stub_summary(ml_predictions: Dict) -> str:
    """Build stub summary with example markers (single braces)."""
    artist = "неизвестный художник"
    if ml_predictions and ml_predictions.get("artists"):
        artist = ml_predictions["artists"][0].get("name", "неизвестный художник")
    
    return f"""## Сводный анализ

Произведение демонстрирует стилистическое сходство с работами {{artist|{artist}}}. 
Характерные {{technique|мазки}} и {{composition|композиционное построение}} указывают на 
{{era|классический период}} развития художественной традиции.

В палитре преобладают {{color|#4a5568|приглушённые тона}}, создающие 
{{mood|созерцательное}} настроение произведения.

Для получения полного глубокого анализа необходимо настроить LLM-провайдер в конфигурации приложения.

*Примечание: данный анализ является предварительным и требует расширенной интерпретации.*"""


# ============ Main Service Functions ============

def prepare_ml_predictions_for_prompt(ml_result: Dict) -> Dict:
    """Convert ML predictions to prompt-friendly format."""
    artists = [
        format_prediction_for_prompt({"artist_slug": a.get("artist_slug", ""), "probability": a.get("probability", 0)})
        for a in ml_result.get("artists", [])
    ]
    
    genres = [
        format_prediction_for_prompt({"name": g.get("name", ""), "probability": g.get("probability", 0)})
        for g in ml_result.get("genres", [])
    ]
    
    styles = [
        format_prediction_for_prompt({"name": s.get("name", ""), "probability": s.get("probability", 0)})
        for s in ml_result.get("styles", [])
    ]
    
    return {"artists": artists, "genres": genres, "styles": styles}


async def run_single_module_analysis(
    module: str,
    image_path: str,
    ml_predictions: Dict = None
) -> Dict[str, Any]:
    """Run a single analysis module.
    
    Args:
        module: One of "color", "composition", "scene", "technique", "historical"
        image_path: Path to image file
        ml_predictions: Optional ML predictions from classifier
        
    Returns:
        Dict with features and analysis
    """
    ml_prompt_data = prepare_ml_predictions_for_prompt(ml_predictions) if ml_predictions else None
    
    if module == "color":
        features = extract_color_features(image_path)
        analysis = await analyze_color_psychology(features)
        return {"features": features, "analysis": analysis}
    
    elif module == "composition":
        features = extract_composition_features(image_path)
        analysis = await analyze_composition(features)
        return {"features": features, "analysis": analysis}
    
    elif module == "scene":
        # Use Vision LLM for scene extraction
        features = await extract_scene_features_with_vision(image_path)
        analysis = await analyze_scene(features, ml_prompt_data)
        return {"features": features, "analysis": analysis}
    
    elif module == "technique":
        color_features = extract_color_features(image_path)
        comp_features = extract_composition_features(image_path)
        analysis = await analyze_technique(ml_prompt_data, color_features, comp_features)
        return {"features": None, "analysis": analysis}
    
    elif module == "historical":
        # Historical needs all other analyses
        color_features = extract_color_features(image_path)
        color_analysis = await analyze_color_psychology(color_features)
        
        comp_features = extract_composition_features(image_path)
        comp_analysis = await analyze_composition(comp_features)
        
        # Use Vision LLM for scene
        scene_features = await extract_scene_features_with_vision(image_path)
        scene_analysis = await analyze_scene(scene_features, ml_prompt_data)
        
        technique_analysis = await analyze_technique(ml_prompt_data, color_features, comp_features)
        
        analysis = await analyze_historical_context(
            ml_prompt_data,
            color_analysis,
            comp_analysis,
            scene_analysis,
            technique_analysis
        )
        return {"features": None, "analysis": analysis}
    
    else:
        raise ValueError(f"Unknown module: {module}")


async def run_full_deep_analysis(
    image_path: str,
    ml_predictions: Dict = None
) -> Dict[str, Any]:
    """Run full deep analysis with all modules.
    
    This implements the "deep research" pattern by making multiple
    sequential LLM calls, each building on previous results.
    
    Args:
        image_path: Path to image file
        ml_predictions: ML predictions from classifier
        
    Returns:
        Complete analysis with all modules and summary
    """
    ml_prompt_data = prepare_ml_predictions_for_prompt(ml_predictions) if ml_predictions else None
    
    # Step 1: Extract all visual features (parallel for sync, Vision async)
    logger.info("Step 1: Extracting visual features...")
    color_features = extract_color_features(image_path)
    composition_features = extract_composition_features(image_path)
    
    # Step 1b: Extract scene features with Vision LLM (async)
    logger.info("Step 1b: Extracting scene features with Vision LLM...")
    scene_features = await extract_scene_features_with_vision(image_path)
    
    # Step 2: Color psychology analysis
    logger.info("Step 2: Analyzing color psychology...")
    color_analysis = await analyze_color_psychology(color_features)
    
    # Step 3: Composition analysis
    logger.info("Step 3: Analyzing composition...")
    composition_analysis = await analyze_composition(composition_features)
    
    # Step 4: Scene/semantic analysis (uses ML predictions + Vision features)
    logger.info("Step 4: Analyzing scene and semantics...")
    scene_analysis = await analyze_scene(scene_features, ml_prompt_data)
    
    # Step 5: Technique analysis (uses color + composition)
    logger.info("Step 5: Analyzing technique...")
    technique_analysis = await analyze_technique(ml_prompt_data, color_features, composition_features)
    
    # Step 6: Historical context (uses all previous)
    logger.info("Step 6: Analyzing historical context...")
    historical_analysis = await analyze_historical_context(
        ml_prompt_data,
        color_analysis,
        composition_analysis,
        scene_analysis,
        technique_analysis
    )
    
    # Step 7: Final synthesis
    logger.info("Step 7: Generating summary synthesis...")
    summary = await generate_summary(
        color_analysis,
        composition_analysis,
        scene_analysis,
        technique_analysis,
        historical_analysis,
        ml_prompt_data or {}
    )
    
    return {
        "color": color_analysis,
        "color_features": color_features,
        "composition": composition_analysis,
        "composition_features": composition_features,
        "scene": scene_analysis,
        "scene_features": scene_features,
        "technique": technique_analysis,
        "historical": historical_analysis,
        "summary": summary
    }
