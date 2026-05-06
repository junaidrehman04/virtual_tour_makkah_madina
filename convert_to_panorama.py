#!/usr/bin/env python3
"""
Convert regular photos to equirectangular-like panoramas for Pannellum.js
Creates a 4096x2048 (2:1) image by intelligently extending the original photo.
"""
from PIL import Image, ImageFilter, ImageDraw
import os
import sys

def convert_to_equirectangular(input_path, output_path, target_w=4096, target_h=2048):
    print(f"Converting: {os.path.basename(input_path)}")
    img = Image.open(input_path).convert('RGB')
    orig_w, orig_h = img.size
    print(f"  Original size: {orig_w}x{orig_h} (ratio: {orig_w/orig_h:.2f})")

    # Scale the image to fill the full height
    scale = target_h / orig_h
    new_w = int(orig_w * scale)

    # If scaled width > target, scale by width instead
    if new_w > target_w:
        scale = target_w / orig_w
        new_w = target_w
        new_h = int(orig_h * scale)
    else:
        new_h = target_h

    resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Create a new 2:1 canvas filled with stretched background
    # First: create a very blurred + stretched version as base background
    bg = img.resize((target_w, target_h), Image.LANCZOS)
    # Heavy blur for the background fill areas
    for _ in range(5):
        bg = bg.filter(ImageFilter.GaussianBlur(radius=15))

    # Darken the blurred background slightly for depth effect
    from PIL import ImageEnhance
    bg = ImageEnhance.Brightness(bg).enhance(0.4)

    # Paste the resized original in the center
    canvas = bg.copy()
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    canvas.paste(resized, (x_offset, y_offset))

    # Create smooth fade blend at edges
    # Left fade zone
    fade_width = min(200, x_offset) if x_offset > 0 else 0
    if fade_width > 0:
        for x in range(fade_width):
            alpha = x / fade_width  # 0 at edge, 1 at center
            for y in range(new_h):
                cx = x_offset + x - fade_width
                if cx >= 0:
                    orig_px = canvas.getpixel((x_offset + x - fade_width, y_offset + y))
                    bg_px = bg.getpixel((x_offset + x - fade_width, y_offset + y))
                    blended = tuple(int(alpha * o + (1-alpha) * b) for o, b in zip(orig_px, bg_px))
                    canvas.putpixel((x_offset + x - fade_width, y_offset + y), blended)

    # For the sides, use a simpler mirror+fade approach
    if x_offset > 30:
        # Left side: mirror the left portion of the image
        left_strip_w = min(new_w // 3, x_offset)
        left_strip = resized.crop((0, 0, left_strip_w, new_h))
        left_strip_flipped = left_strip.transpose(Image.FLIP_LEFT_RIGHT)

        # Resize to fill the gap
        left_fill = left_strip_flipped.resize((x_offset, new_h), Image.LANCZOS)

        # Create alpha mask for blending (fade in from left)
        mask = Image.new('L', (x_offset, new_h))
        draw = ImageDraw.Draw(mask)
        for xi in range(x_offset):
            alpha_val = int(255 * (xi / x_offset) ** 2)  # quadratic fade
            draw.line([(xi, 0), (xi, new_h)], fill=alpha_val)

        # Blend the fill with background
        blended_left = Image.composite(left_fill, bg.crop((0, y_offset, x_offset, y_offset + new_h)), mask)
        canvas.paste(blended_left, (0, y_offset))

        # Right side: mirror the right portion
        right_strip_w = min(new_w // 3, target_w - x_offset - new_w)
        if right_strip_w > 0:
            right_gap = target_w - x_offset - new_w
            right_strip = resized.crop((new_w - right_strip_w, 0, new_w, new_h))
            right_strip_flipped = right_strip.transpose(Image.FLIP_LEFT_RIGHT)
            right_fill = right_strip_flipped.resize((right_gap, new_h), Image.LANCZOS)

            # Fade mask (fade out to right)
            mask_r = Image.new('L', (right_gap, new_h))
            draw_r = ImageDraw.Draw(mask_r)
            for xi in range(right_gap):
                alpha_val = int(255 * (1 - xi / right_gap) ** 2)
                draw_r.line([(xi, 0), (xi, new_h)], fill=alpha_val)

            bg_right = bg.crop((x_offset + new_w, y_offset, x_offset + new_w + right_gap, y_offset + new_h))
            blended_right = Image.composite(right_fill, bg_right, mask_r)
            canvas.paste(blended_right, (x_offset + new_w, y_offset))

    canvas.save(output_path, 'JPEG', quality=88, optimize=True)
    out_size = os.path.getsize(output_path) / (1024*1024)
    print(f"  Saved: {output_path} ({out_size:.1f}MB)")

def main():
    base_dir = "/home/developer-1/Desktop/makkah Madina/public/images"

    images = {
        "makkah": [
            ("01_masjid_exterior.jpg", "01_masjid_exterior_pano.jpg"),
            ("02_kaaba.jpg", "02_kaaba_pano.jpg"),
            ("03_tawaf.jpg", "03_tawaf_pano.jpg"),
            ("04_hajar_aswad.jpg", "04_hajar_aswad_pano.jpg"),
            ("05_zamzam.jpg", "05_zamzam_pano.jpg"),
            ("06_safa.jpg", "06_safa_pano.jpg"),
            ("07_maqam_ibrahim.jpg", "07_maqam_ibrahim_pano.jpg"),
        ],
        "madina": [
            ("01_nabawi_exterior.jpg", "01_nabawi_exterior_pano.jpg"),
            ("02_green_dome.jpg", "02_green_dome_pano.jpg"),
            ("03_jannat_baqi.jpg", "03_jannat_baqi_pano.jpg"),
        ]
    }

    for location, img_list in images.items():
        loc_dir = os.path.join(base_dir, location)
        print(f"\n=== Converting {location.upper()} images ===")
        for inp, out in img_list:
            in_path = os.path.join(loc_dir, inp)
            out_path = os.path.join(loc_dir, out)
            if os.path.exists(in_path):
                try:
                    convert_to_equirectangular(in_path, out_path)
                except Exception as e:
                    print(f"  ERROR: {e}")
            else:
                print(f"  SKIP (not found): {inp}")

if __name__ == "__main__":
    main()
