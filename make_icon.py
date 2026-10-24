# -*- coding: utf-8 -*-
"""生成程序图标。

默认绘制一个原创的下载箭头图标（可自由再分发）。
想换成自己的图：
    python make_icon.py --src my_avatar.jpg
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_ICO = os.path.join(HERE, "icon.ico")
OUT_PNG = os.path.join(HERE, "icon.png")

S = 3                    # 超采样倍数
N = 1024 * S             # 内部画布

# 配色（与界面一致）
BG_TOP = (24, 38, 54)
BG_BOT = (8, 8, 10)
ARROW_HI = (140, 235, 250)
ARROW = (237, 252, 255)
TRAY = (120, 200, 220)


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return m


def vgrad(size, top, bot):
    w, h = size
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    return strip.resize((w, h), Image.BILINEAR)


def draw_original():
    """原创图标：深色圆角底 + 青白下载箭头 + 承接托盘。"""
    base = vgrad((N, N), BG_TOP, BG_BOT).convert("RGBA")

    # 顶部柔光，避免纯色过于死板
    glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [-N * 0.25, -N * 0.55, N * 0.95, N * 0.55], fill=(120, 220, 245, 46))
    base = Image.alpha_composite(base, glow.filter(ImageFilter.GaussianBlur(N * 0.10)))

    cx = 512
    SHAFT_X, SHAFT_TOP, SHAFT_BOT = 60, 250, 590
    HEAD_HALF, HEAD_TOP, HEAD_TIP = 178, 560, 748
    TRAY_X, TRAY_Y, TRAY_H = 226, 838, 32

    # 箭头形状蒙版（杆 + 三角头）
    mask = Image.new("L", (N, N), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle(
        [(cx - SHAFT_X) * S, SHAFT_TOP * S, (cx + SHAFT_X) * S, SHAFT_BOT * S],
        radius=SHAFT_X * S, fill=255)
    md.polygon([((cx - HEAD_HALF) * S, HEAD_TOP * S),
                ((cx + HEAD_HALF) * S, HEAD_TOP * S),
                (cx * S, HEAD_TIP * S)], fill=255)

    # 箭头本体：竖向渐变（白 -> 青白）
    grad = Image.new("RGB", (1, N))
    gp = grad.load()
    for y in range(N):
        t = y / (N - 1)
        gp[0, y] = tuple(int(ARROW[i] + (ARROW_HI[i] - ARROW[i]) * min(1.0, t * 1.35))
                         for i in range(3))
    grad = grad.resize((N, N), Image.BILINEAR).convert("RGBA")

    layer = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    layer.paste(grad, (0, 0), mask)

    # 托盘
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(
        [(cx - TRAY_X) * S, (TRAY_Y - TRAY_H) * S,
         (cx + TRAY_X) * S, (TRAY_Y + TRAY_H) * S],
        radius=TRAY_H * S, fill=TRAY)

    out = Image.alpha_composite(base, layer)
    out.putalpha(rounded_mask((N, N), 232 * S))
    return out


def from_image(path):
    """用自定义图片，居中裁成正方形。"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))


def build(src=None):
    if src:
        im = from_image(src)
        big = im.resize((N, N), Image.LANCZOS)
        # 自定义图：小尺寸收紧裁切以免糊
        small_src = im.crop((int(im.size[0] * 0.12), int(im.size[1] * 0.09),
                             int(im.size[0] * 0.90), int(im.size[1] * 0.87)))
    else:
        big = draw_original()
        small_src = None

    big.resize((256, 256), Image.LANCZOS).save(OUT_PNG)

    sizes = [256, 128, 64, 48, 32, 16]
    frames = []
    for s in sizes:
        if small_src is not None and s < 64:
            f = small_src.resize((s, s), Image.LANCZOS)
        else:
            f = big.resize((s, s), Image.LANCZOS)
        if s <= 48:
            f = ImageEnhance.Contrast(f).enhance(1.12)
            f = ImageEnhance.Sharpness(f).enhance(1.5)
        frames.append(f)

    frames[0].save(OUT_ICO, format="ICO",
                   sizes=[(s, s) for s in sizes], append_images=frames[1:])
    print("icon.png:", OUT_PNG)
    print("icon.ico:", OUT_ICO, os.path.getsize(OUT_ICO), "bytes")


def main():
    ap = argparse.ArgumentParser(description="生成 icon.ico / icon.png")
    ap.add_argument("--src", help="自定义图片路径（默认绘制内置原创图标）")
    a = ap.parse_args()
    if a.src and not os.path.exists(a.src):
        print("找不到图片:", a.src)
        return 1
    build(a.src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
