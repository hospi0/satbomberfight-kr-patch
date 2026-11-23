# -*- coding: utf-8 -*-
r"""대사 글꼴용 한글 글자 그리기(2026-11-23) — 원본 TALKCHR 글자처럼 16×16 · 색 번호 = 진하기(0 투명 ‥ 15 완전)
  4배로 그려 줄인 덮임 비율 → 0‥15. 잉크 범위를 15×15 칸 가운데(왼쪽 위 1px 여백 원본과 같게)에 둠.
  python tools/kfont.py 글자… → work/check/그림미리보기/한글글꼴_시험.png (원본 몇 자와 나란히)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = r'C:/claude/utils/font/nanum-gothic/NanumGothicExtraBold.ttf'
SIZE = 15                                                            # 잉크 높이 목표(원본 가나·한자 ≈ 14‥15)
S = 4


def glyph(ch, font=FONT, size=SIZE):
    """한 글자 → 16×16 int(0‥15)"""
    if ch == ' ': return np.zeros((16, 16), int)
    f = ImageFont.truetype(font, size * S)
    im = Image.new('L', (24 * S, 24 * S), 0); dr = ImageDraw.Draw(im)
    bb = dr.textbbox((0, 0), '가', font=f)                          # 세로 기준 = '가' 잉크(글자마다 위아래 들쭉날쭉 막음)
    top = bb[1]; h = bb[3] - bb[1]
    b2 = dr.textbbox((0, 0), ch, font=f); w = b2[2] - b2[0]
    x = (16 * S - w) // 2 - b2[0] + S // 2; y = (16 * S - h) // 2 - top + S // 2
    dr.text((x, y), ch, font=f, fill=255)
    a = np.array(im, np.float32)[:16 * S, :16 * S].reshape(16, S, 16, S).mean((1, 3)) / 255
    return np.clip(np.round(a * 15 * 1.25), 0, 15).astype(int)       # 살짝 진하게(원본 획이 굵음)


def pack(g):
    f = g.ravel(); return bytes(((f[0::2] << 4) | f[1::2]).astype(np.uint8))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    txt = ' '.join(sys.argv[1:]) or '뭐야! 첫 상대가 검은봄이냐!'
    d = open(os.path.join(ROOT, 'work', 'TALKCHR.BIN'), 'rb').read()
    orig = [np.stack([np.frombuffer(d[0x60 + (633 + c) * 128:0x60 + (633 + c) * 128 + 128], np.uint8) >> 4,
                      np.frombuffer(d[0x60 + (633 + c) * 128:0x60 + (633 + c) * 128 + 128], np.uint8) & 15], 1).ravel().reshape(16, 16) for c in (9, 8, 14, 1, 40, 22, 4, 5)]
    row1 = np.hstack(orig); row2 = np.hstack([glyph(ch) for ch in txt])
    W = max(row1.shape[1], row2.shape[1]); S2 = np.zeros((36, W), int); S2[:16, :row1.shape[1]] = row1; S2[20:, :row2.shape[1]] = row2
    Image.fromarray((S2 * 17).astype(np.uint8)).resize((W * 4, 36 * 4), Image.NEAREST).save(os.path.join(ROOT, 'work', 'check', '그림미리보기', '한글글꼴_시험.png'))
