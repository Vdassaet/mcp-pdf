"""
Image processing module for NJ Fence and Railing Catalog Studio.
Isolates railings/fences from raw photographs and mounts them on a pure white (#FFFFFF)
catalog background with high-resolution studio framing and contrast enhancement.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


PURE_WHITE = (255, 255, 255)


def _border_flood_background_mask(rgb_arr: np.ndarray, tolerance: float = 42.0) -> np.ndarray:
    """
    Detect background connected to the outer borders of the photograph using
    border color sampling + breadth-first flood fill in RGB space, combined with
    local gradient protection so thin railing pickets and posts are never erased.
    Returns a float alpha mask in [0.0, 1.0] where 1.0 = foreground railing.
    """
    h, w, _ = rgb_arr.shape
    work_scale = 1.0
    if max(h, w) > 640:
        work_scale = 640.0 / float(max(h, w))
        small_w = max(32, int(w * work_scale))
        small_h = max(32, int(h * work_scale))
        small_img = Image.fromarray(rgb_arr).resize((small_w, small_h), Image.Resampling.BILINEAR)
        arr = np.asarray(small_img, dtype=np.float32)
    else:
        arr = rgb_arr.astype(np.float32)

    sh, sw, _ = arr.shape

    # Sample border strips (top, left, right, and corners)
    top_strip = arr[0:max(2, sh // 20), :, :].reshape(-1, 3)
    left_strip = arr[:, 0:max(2, sw // 20), :].reshape(-1, 3)
    right_strip = arr[:, sw - max(2, sw // 20):sw, :].reshape(-1, 3)
    border_samples = np.concatenate([top_strip, left_strip, right_strip], axis=0)
    bg_median = np.median(border_samples, axis=0)

    # Compute Euclidean distance in RGB from dominant border background color
    dist_global = np.linalg.norm(arr - bg_median[None, None, :], axis=2)

    # Compute local edge magnitude so strong railing edges act as flood barriers
    gx = np.linalg.norm(np.diff(arr, axis=1, prepend=arr[:, :1, :]), axis=2)
    gy = np.linalg.norm(np.diff(arr, axis=0, prepend=arr[:1, :, :]), axis=2)
    edge_mag = np.hypot(gx, gy)

    visited = np.zeros((sh, sw), dtype=bool)
    is_bg = np.zeros((sh, sw), dtype=bool)
    queue: deque[Tuple[int, int]] = deque()

    # Seed from all 4 borders where color is reasonably close to border distribution
    seed_tol = tolerance * 1.35
    for x in range(sw):
        for y in (0, sh - 1):
            if dist_global[y, x] <= seed_tol:
                visited[y, x] = True
                is_bg[y, x] = True
                queue.append((y, x))
    for y in range(sh):
        for x in (0, sw - 1):
            if not visited[y, x] and dist_global[y, x] <= seed_tol:
                visited[y, x] = True
                is_bg[y, x] = True
                queue.append((y, x))

    step_limit = 22.0
    edge_barrier = 34.0

    while queue:
        cy, cx = queue.popleft()
        cur_color = arr[cy, cx]
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < sh and 0 <= nx < sw and not visited[ny, nx]:
                visited[ny, nx] = True
                if edge_mag[ny, nx] > edge_barrier and dist_global[ny, nx] > tolerance * 0.7:
                    continue
                step_dist = float(np.linalg.norm(arr[ny, nx] - cur_color))
                if dist_global[ny, nx] <= tolerance or (
                    step_dist <= step_limit and dist_global[ny, nx] <= tolerance * 1.45
                ):
                    is_bg[ny, nx] = True
                    queue.append((ny, nx))

    # Also remove interior holes between railing pickets if they closely match the background color
    # and have low edge gradient (critical for fence/railing balusters!)
    between_pickets_bg = (dist_global <= (tolerance * 0.88)) & (edge_mag < edge_barrier * 0.85)
    combined_bg = is_bg | between_pickets_bg

    fg_mask_small = (~combined_bg).astype(np.float32) * 255.0

    # Safety fallback: if foreground is < 3% of image, keep full image
    if np.mean(fg_mask_small > 127) < 0.03:
        fg_mask_small[:, :] = 255.0

    mask_img = Image.fromarray(fg_mask_small.astype(np.uint8), mode="L")
    if (sw, sh) != (w, h):
        mask_img = mask_img.resize((w, h), Image.Resampling.BILINEAR)
    # Soft feathering for clean anti-aliased edges on white background
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=1.1))
    return np.asarray(mask_img, dtype=np.float32) / 255.0


def process_photo_to_white_background(
    input_path: str | Path,
    output_path: str | Path,
    mode: str = "auto_isolate_white",
    target_size: Tuple[int, int] = (1200, 900),
    padding_ratio: float = 0.08,
    tolerance: float = 42.0,
) -> Path:
    """
    Process a product photograph and place it on a pure white (#FFFFFF) background.

    Modes:
    - 'rembg_ai_white' or 'auto_isolate_white': Deep learning AI background removal (rembg)
      with fast thumbnail scaling, compositing foreground over pure white #FFFFFF.
    - 'railing_metal_isolate_white': Specialized dark-metal railing isolator that strips
      vinyl siding, stairs, scaffolding, and dirt.
    - 'studio_frame_white': Enhances contrast/sharpness and mounts the full photo inside
      a clean white catalog border (#FFFFFF).
    """
    in_path = Path(input_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    raw_img = Image.open(in_path)
    raw_img = ImageOps.exif_transpose(raw_img)

    canvas_w, canvas_h = target_size
    max_fg_w = int(canvas_w * (1.0 - 2.0 * padding_ratio))
    max_fg_h = int(canvas_h * (1.0 - 2.0 * padding_ratio))

    # Fast deep learning AI removal via rembg if requested or auto
    if mode in ("rembg_ai_white", "auto_isolate_white"):
        try:
            import rembg
            # Downsample to max 1200px for 3-second fast execution on CPU
            work_img = raw_img.copy()
            work_img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            rgba = rembg.remove(work_img)
            # Composite over pure white #FFFFFF
            white_canvas = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            white_canvas.paste(rgba, (0, 0), rgba)
            rgb_comp = white_canvas.convert("RGB")

            # Crop bounding box of non-white pixels
            bbox = ImageOps.invert(white_canvas.convert("L")).getbbox()
            if bbox:
                rgb_comp = rgb_comp.crop(bbox)

            rgb_comp.thumbnail((max_fg_w, max_fg_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (canvas_w, canvas_h), PURE_WHITE)
            ox = (canvas_w - rgb_comp.width) // 2
            oy = (canvas_h - rgb_comp.height) // 2
            canvas.paste(rgb_comp, (ox, oy))
            canvas.save(out_path, format="PNG", optimize=True)
            return out_path
        except Exception:
            pass  # Fall through to algorithmic isolator

    if mode == "railing_metal_isolate_white":
        # Specific dark metal railing segmentation: strips cream siding, concrete stairs, dirt
        w, h = raw_img.size
        arr = np.asarray(raw_img.convert("RGB"), dtype=np.float32)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        max_c = np.maximum(np.maximum(r, g), b)
        diff = max_c - np.minimum(np.minimum(r, g), b)

        # Railing bounding box
        bbox = np.zeros((h, w), dtype=bool)
        bbox[int(h * 0.10):int(h * 0.85), int(w * 0.20):] = True
        is_metal = (max_c < 122) & (diff < 45) & bbox
        is_metal[int(h * 0.76):, :] = False  # exclude bottom dirt/shadows

        mask_img = Image.fromarray((is_metal.astype(np.uint8) * 255), mode="L")
        mask_img = mask_img.filter(ImageFilter.MaxFilter(size=3)).filter(ImageFilter.GaussianBlur(radius=1.2))
        alpha = np.asarray(mask_img, dtype=np.float32) / 255.0

        white_arr = np.full_like(arr, 255.0)
        comp = np.clip(arr * alpha[:, :, None] + white_arr * (1.0 - alpha[:, :, None]), 0, 255).astype(np.uint8)
        coords = np.argwhere(alpha > 0.2)
        if coords.size > 0:
            cy0, cx0 = coords.min(axis=0)
            cy1, cx1 = coords.max(axis=0)
            pad = 20
            cropped = Image.fromarray(comp[max(0, cy0-pad):min(h, cy1+pad), max(0, cx0-pad):min(w, cx1+pad)])
        else:
            cropped = Image.fromarray(comp)

        cropped.thumbnail((max_fg_w, max_fg_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (canvas_w, canvas_h), PURE_WHITE)
        ox = (canvas_w - cropped.width) // 2
        oy = (canvas_h - cropped.height) // 2
        canvas.paste(cropped, (ox, oy))
        canvas.save(out_path, format="PNG", optimize=True)
        return out_path

    if mode == "studio_frame_white":
        rgb = raw_img.convert("RGB")
        rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
        rgb = ImageEnhance.Sharpness(rgb).enhance(1.12)
        rgb.thumbnail((max_fg_w, max_fg_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (canvas_w, canvas_h), PURE_WHITE)
        ox = (canvas_w - rgb.width) // 2
        oy = (canvas_h - rgb.height) // 2
        canvas.paste(rgb, (ox, oy))
        canvas.save(out_path, format="PNG", optimize=True)
        return out_path

    # Check if image already has meaningful transparency
    if raw_img.mode in ("RGBA", "LA") or ("transparency" in raw_img.info):
        rgba = raw_img.convert("RGBA")
        alpha_arr = np.asarray(rgba.split()[-1], dtype=np.float32) / 255.0
        if np.mean(alpha_arr < 0.95) > 0.02:
            rgb_arr = np.asarray(rgba.convert("RGB"), dtype=np.float32)
            fg_alpha = alpha_arr
        else:
            rgb_arr = np.asarray(rgba.convert("RGB"), dtype=np.uint8)
            fg_alpha = _border_flood_background_mask(rgb_arr, tolerance=tolerance)
            rgb_arr = rgb_arr.astype(np.float32)
    else:
        rgb_uint8 = np.asarray(raw_img.convert("RGB"), dtype=np.uint8)
        if mode == "high_contrast_metal_white":
            lum = (
                0.299 * rgb_uint8[:, :, 0]
                + 0.587 * rgb_uint8[:, :, 1]
                + 0.114 * rgb_uint8[:, :, 2]
            )
            p70 = float(np.percentile(lum, 70))
            thresh = max(140.0, min(225.0, p70))
            fg_alpha = np.clip((thresh - lum) / 28.0, 0.0, 1.0).astype(np.float32)
            if np.mean(fg_alpha > 0.5) < 0.03:
                fg_alpha = _border_flood_background_mask(rgb_uint8, tolerance=tolerance)
        else:
            fg_alpha = _border_flood_background_mask(rgb_uint8, tolerance=tolerance)
        rgb_arr = rgb_uint8.astype(np.float32)

    # Composite foreground over pure white (#FFFFFF)
    white_arr = np.full_like(rgb_arr, 255.0)
    alpha_3d = fg_alpha[:, :, None]
    comp_arr = np.clip(rgb_arr * alpha_3d + white_arr * (1.0 - alpha_3d), 0, 255).astype(np.uint8)

    # Auto-crop to foreground bounding box so the railing fills the catalog frame nicely
    fg_coords = np.argwhere(fg_alpha > 0.22)
    if fg_coords.size > 0:
        y0, x0 = fg_coords.min(axis=0)
        y1, x1 = fg_coords.max(axis=0)
        pad_y = max(6, int((y1 - y0) * 0.03))
        pad_x = max(6, int((x1 - x0) * 0.03))
        y0 = max(0, int(y0) - pad_y)
        x0 = max(0, int(x0) - pad_x)
        y1 = min(comp_arr.shape[0], int(y1) + pad_y)
        x1 = min(comp_arr.shape[1], int(x1) + pad_x)
        cropped_img = Image.fromarray(comp_arr[y0:y1, x0:x1])
    else:
        cropped_img = Image.fromarray(comp_arr)

    # Subtle studio enhancement (sharpness & contrast for crisp metal/vinyl edges)
    cropped_img = ImageEnhance.Contrast(cropped_img).enhance(1.08)
    cropped_img = ImageEnhance.Sharpness(cropped_img).enhance(1.18)
    cropped_img.thumbnail((max_fg_w, max_fg_h), Image.Resampling.LANCZOS)

    # Place centered on pure #FFFFFF canvas with subtle ground contact line shadow
    canvas = Image.new("RGB", (canvas_w, canvas_h), PURE_WHITE)
    draw = ImageDraw.Draw(canvas)
    ox = (canvas_w - cropped_img.width) // 2
    oy = (canvas_h - cropped_img.height) // 2

    # Soft studio floor shadow line under the product
    shadow_y = min(canvas_h - 18, oy + cropped_img.height + 6)
    shadow_margin = int(cropped_img.width * 0.08)
    draw.ellipse(
        [ox + shadow_margin, shadow_y - 4, ox + cropped_img.width - shadow_margin, shadow_y + 5],
        fill=(238, 240, 243),
    )

    canvas.paste(cropped_img, (ox, oy))
    canvas.save(out_path, format="PNG", optimize=True)
    return out_path


def create_sample_railing_photo(output_path: str | Path) -> Path:
    """
    Create a realistic sample site photograph of an NJ Fence and Railing
    black powder-coated aluminum/wrought-iron railing against an outdoor sky/stone backdrop.
    Used for instant testing of background removal, Gemini analysis, and PDF generation.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 1000, 750
    img = Image.new("RGB", (w, h), (214, 224, 235))
    draw = ImageDraw.Draw(img)

    # Outdoor sky/patio gradient background (non-white, so white-background processing is clearly visible)
    for y in range(h):
        r = int(205 + (y / h) * 22)
        g = int(218 + (y / h) * 18)
        b = int(232 - (y / h) * 10)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Draw a modern matte-black architectural railing with square posts, top/bottom rails,
    # decorative intermediate horizontal bar, and vertical balusters with spear/ring accents
    metal_dark = (26, 30, 36)
    metal_highlight = (62, 68, 78)
    gold_accent = (184, 152, 72)

    left_post_x = 130
    right_post_x = 870
    top_rail_y = 175
    sub_rail_y = 225
    bottom_rail_y = 565
    post_bottom_y = 620

    # Main Newel Posts (3"x3" architectural posts with pyramid caps)
    for px in (left_post_x, right_post_x):
        # Post shaft
        draw.rectangle([px - 22, top_rail_y - 25, px + 22, post_bottom_y], fill=metal_dark, outline=metal_highlight, width=2)
        # Post highlight stripe
        draw.line([(px - 10, top_rail_y - 20), (px - 10, post_bottom_y - 10)], fill=metal_highlight, width=3)
        # Post base flange
        draw.rectangle([px - 36, post_bottom_y - 14, px + 36, post_bottom_y + 4], fill=metal_dark, outline=metal_highlight, width=2)
        # Pyramid post cap
        draw.polygon([(px - 28, top_rail_y - 25), (px, top_rail_y - 46), (px + 28, top_rail_y - 25)], fill=metal_dark, outline=metal_highlight)

    # Top molded handrail
    draw.rectangle([left_post_x + 22, top_rail_y, right_post_x - 22, top_rail_y + 20], fill=metal_dark, outline=metal_highlight, width=2)
    draw.line([(left_post_x + 24, top_rail_y + 5), (right_post_x - 24, top_rail_y + 5)], fill=metal_highlight, width=2)

    # Upper ornamental channel rail
    draw.rectangle([left_post_x + 22, sub_rail_y, right_post_x - 22, sub_rail_y + 14], fill=metal_dark, outline=metal_highlight, width=1)

    # Bottom structural rail
    draw.rectangle([left_post_x + 22, bottom_rail_y, right_post_x - 22, bottom_rail_y + 18], fill=metal_dark, outline=metal_highlight, width=2)

    # Vertical balusters (pickets) + decorative rings in the upper channel
    num_pickets = 13
    span = (right_post_x - 22) - (left_post_x + 22)
    spacing = span / (num_pickets + 1)

    for i in range(1, num_pickets + 1):
        bx = int(left_post_x + 22 + i * spacing)
        # Vertical square baluster from sub-rail to bottom rail
        draw.rectangle([bx - 5, sub_rail_y + 14, bx + 5, bottom_rail_y], fill=metal_dark)
        draw.line([(bx - 2, sub_rail_y + 16), (bx - 2, bottom_rail_y - 2)], fill=metal_highlight, width=1)
        # Upper picket segment
        draw.rectangle([bx - 5, top_rail_y + 20, bx + 5, sub_rail_y], fill=metal_dark)
        # Decorative ring between top rail and sub rail
        ring_cy = (top_rail_y + 20 + sub_rail_y) // 2
        draw.ellipse([bx - 14, ring_cy - 12, bx + 14, ring_cy + 12], outline=metal_dark, width=4)
        # Subtle central knuckle detail on alternating pickets
        if i % 2 == 1:
            mid_y = (sub_rail_y + 14 + bottom_rail_y) // 2
            draw.rectangle([bx - 9, mid_y - 12, bx + 9, mid_y + 12], fill=metal_dark, outline=gold_accent, width=2)

    # Center support foot under bottom rail
    mid_x = (left_post_x + right_post_x) // 2
    draw.rectangle([mid_x - 7, bottom_rail_y + 18, mid_x + 7, post_bottom_y], fill=metal_dark)
    draw.rectangle([mid_x - 16, post_bottom_y - 6, mid_x + 16, post_bottom_y + 2], fill=metal_dark)

    img.save(out, format="JPEG", quality=94)
    return out
