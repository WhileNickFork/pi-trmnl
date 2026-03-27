#!/usr/bin/env python3
"""
Display driver for Pimoroni Inky Impression Spectra 13.3" (1600x1200).
Replaces bb_epaper's show_img for displays not supported by that library.
Called by trmnl-display Go binary via exec.Command.
"""

import argparse
import sys
from PIL import Image, ImageOps


def aspect_fill(image, target_width, target_height):
    """Scale image to fill target dimensions, cropping excess from center."""
    src_w, src_h = image.size
    target_ratio = target_width / target_height
    src_ratio = src_w / src_h

    if src_w == target_width and src_h == target_height:
        return image

    if src_ratio > target_ratio:
        # Source is wider: scale by height, crop width
        scale = target_height / src_h
        new_w = int(src_w * scale)
        resized = image.resize((new_w, target_height), Image.LANCZOS)
        left = (new_w - target_width) // 2
        return resized.crop((left, 0, left + target_width, target_height))
    else:
        # Source is taller: scale by width, crop height
        scale = target_width / src_w
        new_h = int(src_h * scale)
        resized = image.resize((target_width, new_h), Image.LANCZOS)
        top = (new_h - target_height) // 2
        return resized.crop((0, top, target_width, top + target_height))


def main():
    parser = argparse.ArgumentParser(
        description="Display an image on Pimoroni Inky Impression Spectra"
    )
    parser.add_argument(
        "--file", "-f", required=True, help="Path to image file"
    )
    parser.add_argument(
        "--invert", default="false", choices=["true", "false"],
        help="Invert image pixels for dark mode"
    )
    parser.add_argument(
        "--mode", default="fast", choices=["fast", "partial"],
        help="Update mode (accepted for compatibility; Spectra always does full refresh)"
    )
    parser.add_argument(
        "--saturation", "-s", type=float, default=0.5,
        help="Color saturation for palette mapping (0.0-1.0)"
    )
    args = parser.parse_args()

    # Initialize display via EEPROM auto-detection
    try:
        from inky.auto import auto
        inky = auto(ask_user=False, verbose=False)
    except ImportError:
        print("Error: inky library not installed. Run: pip3 install inky", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing display: {e}", file=sys.stderr)
        print("Check that the Inky Impression is connected and SPI/I2C are enabled.", file=sys.stderr)
        sys.exit(1)

    target_w, target_h = inky.resolution

    # Load image
    try:
        image = Image.open(args.file)
    except FileNotFoundError:
        print(f"Error: image file not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error opening image: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert palette or grayscale images to RGB for color processing
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    elif image.mode == "RGBA":
        # Composite alpha onto white background
        bg = Image.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[3])
        image = bg

    # Resize to display resolution using aspect-fill
    image = aspect_fill(image, target_w, target_h)

    # Apply dark mode inversion
    if args.invert == "true":
        image = ImageOps.invert(image)

    # Send to display
    try:
        inky.set_image(image, saturation=args.saturation)
        inky.show()
    except TypeError:
        # Older inky versions may not accept saturation parameter
        inky.set_image(image)
        inky.show()
    except Exception as e:
        print(f"Error updating display: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
