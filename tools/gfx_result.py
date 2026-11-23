# -*- coding: utf-8 -*-
r"""승자 진출(勝ち抜き) 결과·랭킹 화면 그림 글자(2026-11-23 하스피 스샷·스테이트 s22·s23·s24)
  NUKI.BIN(VRAM 기준 0x4BD84) 0x427C 112×48 結果 → 결과 · 0x645C 112×32 継続中! → 계속 중! · 0x60FC 72×24 人抜き → 연승
  SRNK.BIN(기준 0xB7D0) 0x6AB0 48×16 人抜き(랭킹 «10人抜き») → 연승
  색 = 원본 팔레트 번호 그대로(판마다 원본에서 잰 몸통·테두리·그림자 번호), 판 크기·자리 그대로.
  → work/gfx/<파일>@<위치>.bin + 미리보기 work/check/그림미리보기/결과화면_원본_한글.png (실제 색, 원본 | 한글)
  python tools/gfx_result.py"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import vdp2render as V

BHS = r'C:/claude/utils/font/blackhansans/BlackHanSans-Regular.ttf'
NEB = r'C:/claude/utils/font/nanum-gothic/NanumGothicExtraBold.ttf'
S = 4


def mask(text, font, box_w, box_h):
    """글자 덮개(0/1) — box 안에 꽉 차게(가로·세로 비율 유지), 4배로 그려 줄임"""
    for size in range(box_h * S * 2, 8, -2):
        f = ImageFont.truetype(font, size)
        im = Image.new('L', (box_w * S * 3, box_h * S * 3), 0); d = ImageDraw.Draw(im)
        d.text((box_w * S, box_h * S), text, font=f, fill=255)
        bb = im.getbbox()
        if bb and bb[2] - bb[0] <= box_w * S and bb[3] - bb[1] <= box_h * S: break
    g = im.crop(bb); w, h = (g.width + S - 1) // S, (g.height + S - 1) // S
    g = g.resize((w, h), Image.LANCZOS)
    return (np.array(g) >= 110).astype(np.uint8)


def dil(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + r: out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def place(m, W, H, x, y):
    c = np.zeros((H, W), np.uint8); c[y:y + m.shape[0], x:x + m.shape[1]] = m[:H - y, :W - x]; return c


def ramp(H, idxs, y0, y1):
    """세로 줄마다 색 번호(y0‥y1 를 idxs 로 고르게)"""
    rows = np.empty(H, int)
    for y in range(H):
        t = 0 if y1 <= y0 else min(max((y - y0) / (y1 - y0), 0), 1)
        rows[y] = idxs[min(int(t * len(idxs)), len(idxs) - 1)]
    return rows[:, None]


def big_outlined(text, W, H, body, rim, shadow, font=BHS, rimw=2, pad=(4, 3)):
    """몸통(세로 램프) + 바깥 테두리(세로 램프) + 오른쪽 아래 그림자(1번)"""
    m = mask(text, font, W - 2 * pad[0] - 2, H - 2 * pad[1] - 2)
    x = (W - 2 - m.shape[1]) // 2; y = (H - 2 - m.shape[0]) // 2
    M = place(m, W, H, x, y); R = dil(M, rimw) & ~M & 1; A = M | R
    Sh = np.roll(np.roll(A, 2, 0), 2, 1) & ~A & 1
    out = np.zeros((H, W), int)
    ys, ye = np.nonzero(A.any(1))[0][[0, -1]]
    out = np.where(Sh == 1, shadow, out)
    out = np.where(R == 1, np.broadcast_to(ramp(H, rim, ys, ye), (H, W)), out)
    out = np.where(M == 1, np.broadcast_to(ramp(H, body, ys, ye), (H, W)), out)
    return out


def flat(text, W, H, top, bot, hi=None, shadow=None, font=BHS, left=0, sh=(1, 1), bold=0, rim=None):
    """노란 단색 글자(위 반 top · 아래 반 bot, 맨 윗줄 hi) — 왼쪽 정렬(앞에 숫자 판이 붙음), 선택 그림자"""
    r = 1 if rim is not None else 0
    m = mask(text, font, W - left - (sh[0] if shadow is not None else 0) - 1 - 2 * r, H - (sh[1] if shadow is not None else 0) - 1 - 2 * r)
    y = (H - (sh[1] if shadow is not None else 0) - m.shape[0]) // 2
    M = place(m, W, H, left + r, y); out = np.zeros((H, W), int)
    for _ in range(bold): M = M | np.roll(M, 1, 1)                  # 가로로 굵게(작은 판)
    if shadow is not None:
        Sh = np.roll(np.roll(M, sh[1], 0), sh[0], 1) & ~M & 1; out[Sh == 1] = shadow
    ys, ye = np.nonzero(M.any(1))[0][[0, -1]]; mid = (ys + ye) // 2
    for yy in range(H):
        out[yy][M[yy] == 1] = top if yy <= mid else bot
    if rim is not None: out[(dil(M, 1) & ~M & 1) == 1] = rim         # 바깥 1px 테두리
    if hi is not None:
        top_edge = M & ~np.roll(M, 1, 0) & 1; out[top_edge == 1] = hi
    return out


JOBS = [   # (파일, 위치, 폭, 높이, 스테이트, colr, 만들기)
    ('NUKI.BIN', 0x427C, 112, 48, 's24', 0x6E0, lambda: big_outlined('결과', 112, 48, body=[3, 4, 5, 6, 7, 8, 9, 10], rim=[15, 14, 13, 12], shadow=1)),
    ('NUKI.BIN', 0x645C, 112, 32, 's22', 0x620, lambda: big_outlined('계속 중!', 112, 32, body=[3, 4, 5, 6], rim=[8, 9, 10, 11, 12, 13, 14, 15], shadow=1, rimw=1, pad=(2, 1))),
    ('NUKI.BIN', 0x60FC, 72, 24, 's22', 0x6A0, lambda: flat('연승', 72, 24, top=2, bot=2, rim=3)),   # 진한 노랑 몸통 + 밝은 노랑 테두리(하스피)
    ('SRNK.BIN', 0x6AB0, 48, 16, 's23', 0x7E0, lambda: flat('연승', 48, 16, top=6, bot=6, shadow=4, font=NEB, bold=1)),
]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = []
    for fn, off, w, h, st, col, mk in JOBS:
        d = open(os.path.join(ROOT, 'work', fn), 'rb').read()
        b = np.frombuffer(d[off:off + w * h // 2], np.uint8); orig = np.stack([b >> 4, b & 15], 1).ravel().reshape(h, w).astype(int)
        new = mk(); assert new.shape == (h, w) and new.max() <= 15
        fl = new.ravel(); open(os.path.join(ROOT, 'work', 'gfx', '%s@%X.bin' % (fn, off)), 'wb').write(bytes(((fl[0::2] << 4) | fl[1::2]).astype(np.uint8)))
        _, _, cram = V.load(st); cram = np.asarray(cram).astype(int)
        def rgb(p):
            e = cram[((col & 0x7F0) + p) & 0x7FF]; im = np.stack([(e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3], -1).astype(np.uint8); im[p == 0] = (60, 50, 40); return im
        rows.append(np.concatenate([rgb(orig), np.full((h, 6, 3), 120, np.uint8), rgb(new)], 1))
        print('  %s@%X %dx%d' % (fn, off, w, h))
    Wd = max(r.shape[1] for r in rows); Sx = np.full((sum(r.shape[0] + 6 for r in rows), Wd, 3), 25, np.uint8); y = 0
    for r in rows: Sx[y:y + r.shape[0], :r.shape[1]] = r; y += r.shape[0] + 6
    Image.fromarray(Sx).resize((Wd * 4, Sx.shape[0] * 4), Image.NEAREST).save(os.path.join(ROOT, 'work', 'check', '그림미리보기', '결과화면_원본_한글.png'))


if __name__ == '__main__':
    main()
