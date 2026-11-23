# -*- coding: utf-8 -*-
r"""대본(TALKANM.BIN) 대사마다 글꼴 그림을 이어 붙인 줄 이미지 → work/ocr/lines/<번호>.png (윈도우 일본어 OCR 입력)
  대사 = [머리 u16×3][코드 …][FFFF]. 코드 0‥796 만 글자로 봄. 줄은 18자씩 끊어 여러 줄.
  python tools/ocr_lines.py  → 이어서 tools/ocr_win.ps1 → tools/ocr_vote.py"""
import os, struct, sys, json
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PER = 18


def messages(path='TALKANM.BIN', start=0, end=None):
    """대본 분할(2026-11-23 확정): 끝 표시 FFFF 대사 끝·FFFE 대화 끝·FFFD 장 서술 끝·FFFC 장 끝.
       FFFC 바로 뒤 조각 = 머리 2워드(그림 번호, 값) + 서술문, 그 밖 = 머리 3워드(말하는 쪽, 음성 번호 또는 FFFF, 4) + 대사.
       머리를 정해진 길이만큼 먼저 읽고(음성 번호 FFFF 를 끝 표시로 오인하지 않게) 글자를 읽음. TALKANM 대본 끝 = 0x106C4(그 뒤 애니메이션 표)."""
    d = open(os.path.join(ROOT, 'work', path), 'rb').read(); a = struct.unpack('>%dH' % (len(d) // 2), d)
    if end is None: end = 0x106C4 if path == 'TALKANM.BIN' else len(d)
    E = end // 2; msgs = []; i = start // 2; prev = None
    while i < E:
        if a[i] >= 0xFF00: prev = a[i]; i += 1; continue             # 끝 표시 연속(FFFE FFFC)
        hl = 2 if prev == 0xFFFC else 3; head = tuple(a[i:i + hl]); j = i + hl
        while j < E and a[j] < 0xFF00: j += 1
        if j >= E: break
        msgs.append(dict(off=i * 2, head=head, codes=list(a[i + hl:j]), end=a[j])); prev = a[j]; i = j + 1
    return msgs


def glyph(d, c):
    o = 0x60 + (633 + c) * 128; a = np.frombuffer(d[o:o + 128], np.uint8)
    return np.stack([a >> 4, a & 15], 1).ravel().reshape(16, 16)


def main():
    d = open(os.path.join(ROOT, 'work', 'TALKCHR.BIN'), 'rb').read()
    ms = messages(); out = os.path.join(ROOT, 'work', 'ocr', 'lines'); os.makedirs(out, exist_ok=True)
    for f in os.listdir(out): os.remove(os.path.join(out, f))
    for k, m in enumerate(ms):
        cs = m['codes']; rows = [cs[i:i + PER] for i in range(0, len(cs), PER)]
        img = np.full((len(rows) * 24 + 8, PER * 17 + 8), 255, np.uint8)
        for r, row in enumerate(rows):
            for c, code in enumerate(row):
                g = glyph(d, code).astype(int); img[4 + r * 24:4 + r * 24 + 16, 4 + c * 17:4 + c * 17 + 16] = 255 - np.clip(g * 17, 0, 255)
        Image.fromarray(img).resize((img.shape[1] * 3, img.shape[0] * 3), Image.LANCZOS).save(os.path.join(out, '%04d.png' % k))
    json.dump(ms, open(os.path.join(ROOT, 'work', 'ocr', 'messages.json'), 'w'))
    print('대사', len(ms), '글자', sum(len(m['codes']) for m in ms), '마지막 위치', hex(ms[-1]['off']))


if __name__ == '__main__':
    main()
