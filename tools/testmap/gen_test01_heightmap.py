#!/usr/bin/env python3
"""生成 test_01 灰盒测试地图的 16 位灰度高程图（WS02-002）。

只用 Python 标准库，结果完全确定（不用随机数）。
用法：python3 tools/testmap/gen_test01_heightmap.py
输出：data/levels/test_01/map/heightmap.png

地形设计：
- 基准海拔约 130 m，整体略向东南倾斜
- 河谷：沿 layers.json 中的河道下切约 35 m（巡航导弹低飞通道）
- 东北山脊：高出周围约 150 m，在其背后形成雷达低空盲区（WS01-006 测试用）
"""
import math
import struct
import zlib
from pathlib import Path

WIDTH_M = 20000.0
HEIGHT_M = 20000.0
M_PER_PX = 100.0
MIN_ELEV = 80.0     # 灰度 0
MAX_ELEV = 330.0    # 灰度 65535

# 与 layers.json 的 river_main 保持一致
RIVER = [(0, 15500), (5000, 13000), (9000, 11000), (12000, 9000), (16000, 6500), (20000, 4500)]


def dist_to_polyline(x, y, pts):
    best = float("inf")
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        px, py = x1 + t * dx, y1 + t * dy
        best = min(best, math.hypot(x - px, y - py))
    return best


def elevation(x, y):
    # 基准 + 向东南缓降
    h = 140.0 - 0.0006 * x + 0.0004 * y
    # 低幅起伏（确定性的正弦叠加）
    h += 6.0 * math.sin(x / 1700.0) * math.cos(y / 2300.0)
    h += 3.0 * math.sin((x + y) / 900.0)
    # 东北山脊：沿西北—东南方向拉长的高斯包
    cx, cy = 15500.0, 15500.0
    u = ((x - cx) + (y - cy)) / math.sqrt(2)   # 沿山脊方向
    v = ((x - cx) - (y - cy)) / math.sqrt(2)   # 垂直山脊方向
    h += 150.0 * math.exp(-(u * u) / (2 * 3500.0 ** 2) - (v * v) / (2 * 900.0 ** 2))
    # 河谷下切
    d = dist_to_polyline(x, y, RIVER)
    h -= 35.0 * math.exp(-(d * d) / (2 * 900.0 ** 2))
    return h


def write_png16(path, w, h, rows):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + struct.pack(">%dH" % w, *r) for r in rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 0, 0, 0, 0))  # 16 位灰度
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def main():
    w, h = int(WIDTH_M / M_PER_PX), int(HEIGHT_M / M_PER_PX)
    rows = []
    lo, hi = float("inf"), float("-inf")
    for row in range(h):
        y = HEIGHT_M - (row + 0.5) * M_PER_PX   # 第 0 行 = 最北边
        r = []
        for col in range(w):
            x = (col + 0.5) * M_PER_PX
            e = elevation(x, y)
            lo, hi = min(lo, e), max(hi, e)
            g = round((e - MIN_ELEV) / (MAX_ELEV - MIN_ELEV) * 65535)
            r.append(max(0, min(65535, g)))
        rows.append(r)
    out = Path(__file__).resolve().parents[2] / "data/levels/test_01/map/heightmap.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_png16(out, w, h, rows)
    print(f"{out}  {w}x{h}px  海拔 {lo:.1f}–{hi:.1f} m")


if __name__ == "__main__":
    main()
