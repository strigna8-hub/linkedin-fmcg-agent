"""Render a clean minimal LinkedIn cover banner for Wise Trading Group.

Output: linkedin_cover.png at LinkedIn's exact 1584x396 spec.
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1584, 396

NAVY = (15, 30, 61)
NAVY_DARK = (7, 16, 36)
GOLD = (201, 168, 88)
GOLD_SOFT = (181, 148, 70)
CREAM = (244, 239, 230)
CREAM_DIM = (200, 195, 180)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def make_gradient_bg():
    base = Image.new("RGB", (W, H), NAVY)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    cx, cy = W * 0.62, H * 0.5
    max_d = (W ** 2 + H ** 2) ** 0.5 / 2
    for r in range(int(max_d), 0, -10):
        t = r / max_d
        alpha = int(90 * t)
        od.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(NAVY_DARK[0], NAVY_DARK[1], NAVY_DARK[2], alpha),
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(40))
    base.paste(overlay, (0, 0), overlay)
    return base


def draw_spaced(draw, xy, text, font, fill, tracking=0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        l, t, r, b = font.getbbox(ch)
        x += (r - l) + tracking


def measure_spaced(text, font, tracking=0):
    total = 0
    for ch in text:
        l, t, r, b = font.getbbox(ch)
        total += (r - l) + tracking
    return total - tracking if text else 0


def main():
    img = make_gradient_bg()
    draw = ImageDraw.Draw(img, "RGBA")

    title = "WISE TRADING GROUP"
    font_title = ImageFont.truetype(FONT_BOLD, 96)
    tracking_t = 18
    title_w = measure_spaced(title, font_title, tracking_t)
    title_x = (W - title_w) // 2
    title_y = 108
    draw_spaced(draw, (title_x, title_y), title, font_title, CREAM, tracking_t)

    line_y = title_y + 132
    line_w = 220
    line_x1 = (W - line_w) // 2
    draw.rectangle([line_x1, line_y, line_x1 + line_w, line_y + 3], fill=GOLD)

    tagline = "GLOBAL FMCG TRADING  ·  DISTRIBUTION  ·  SOURCING"
    font_tag = ImageFont.truetype(FONT_REG, 26)
    tracking_tag = 4
    tag_w = measure_spaced(tagline, font_tag, tracking_tag)
    tag_x = (W - tag_w) // 2
    tag_y = line_y + 24
    draw_spaced(draw, (tag_x, tag_y), tagline, font_tag, GOLD, tracking_tag)

    pad = 56
    bar = 70
    draw.rectangle([W - pad - 2, pad, W - pad, pad + bar], fill=GOLD)
    draw.rectangle([pad, H - pad - bar, pad + 2, H - pad], fill=GOLD_SOFT)

    img.save("/root/linkedin-fmcg-agent/linkedin_cover.png", "PNG", optimize=True)
    print("Saved: linkedin_cover.png", img.size)


if __name__ == "__main__":
    main()
