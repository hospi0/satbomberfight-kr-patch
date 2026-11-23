# -*- coding: utf-8 -*-
r"""대사 글꼴(TALKCHR.BIN, 코드 0‥796 = 글꼴 번호 633+) 1차 판독 — 일본어 글꼴(굵은 고딕 여러 개)로 그린 후보와 화소 비교
  글자: 4비트 바림 16×16 → 0.5 문턱 2값 → 잉크 범위로 잘라 16×16 에 맞춤. 후보: 히라가나·가타카나·부호·JIS 1·2수준 한자.
  점수 = 같은 크기로 맞춘 두 2값 그림의 상관(IoU). 결과 work/ocr/cand.tsv(코드·1~5위·점수) + 판독 그림판 work/ocr/sheet_N.png
  python tools/ocr_font.py"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = [r'C:/Windows/Fonts/BIZ-UDGothicB.ttc', r'C:/Windows/Fonts/meiryob.ttc', r'C:/Windows/Fonts/YuGothB.ttc']
N = 24                                                                # 비교 해상도


def glyphs():
    d = open(os.path.join(ROOT, 'work', 'TALKCHR.BIN'), 'rb').read(); out = []
    for c in range(797):
        o = 0x60 + (633 + c) * 128; a = np.frombuffer(d[o:o + 128], np.uint8)
        out.append(np.stack([a >> 4, a & 15], 1).ravel().reshape(16, 16).astype(int))
    return out


def norm(m):
    ys, xs = np.where(m)
    if len(ys) == 0: return np.zeros((N, N), np.float32)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; h, w = m.shape; s = max(h, w)
    c = np.zeros((s, s), np.uint8); c[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = m * 255
    return (np.array(Image.fromarray(c).resize((N, N), Image.BILINEAR)) > 100).astype(np.float32)


def charset():
    cs = [chr(c) for c in range(0x3041, 0x3097)] + [chr(c) for c in range(0x30A1, 0x30FB)] + list('ー・、。！？「」『』…‥～♪♥☆★（）：；，．＆％＋－＝／〜…')
    for b1 in range(0x88, 0xA0):
        for b2 in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            try: cs.append(bytes([b1, b2]).decode('shift_jis'))
            except UnicodeDecodeError: pass
    for b1 in range(0xE0, 0xEB):
        for b2 in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            try: cs.append(bytes([b1, b2]).decode('shift_jis'))
            except UnicodeDecodeError: pass
    return list(dict.fromkeys(cs))


def render(ch, f):
    im = Image.new('L', (40, 40), 0); ImageDraw.Draw(im).text((4, 4), ch, font=f, fill=255); return np.array(im) > 127


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    G = glyphs(); gv = np.stack([norm(g >= 8) for g in G]).reshape(len(G), -1)
    cs = charset(); best = np.full((len(G), 5), -1.0); bi = np.zeros((len(G), 5), int)
    for fp in FONTS:
        f = ImageFont.truetype(fp, 28)
        cv = np.stack([norm(render(ch, f)) for ch in cs]).reshape(len(cs), -1)
        inter = gv @ cv.T; union = gv.sum(1)[:, None] + cv.sum(1)[None, :] - inter; s = inter / np.maximum(union, 1)
        top = np.argsort(-s, 1)[:, :5]
        for i in range(len(G)):
            cand = list(zip(s[i, top[i]], top[i])) + list(zip(best[i], bi[i]))
            seen = {}; [seen.__setitem__(j, max(sc, seen.get(j, -1))) for sc, j in cand if j >= 0 or sc >= 0]
            tt = sorted(seen.items(), key=lambda kv: -kv[1])[:5]
            best[i] = [v for _, v in tt] + [-1] * (5 - len(tt)); bi[i] = [k for k, _ in tt] + [0] * (5 - len(tt))
    os.makedirs(os.path.join(ROOT, 'work', 'ocr'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'ocr', 'cand.tsv'), 'w', encoding='utf-8') as fo:
        fo.write('code\t1위\t점수\t2위\t3위\t4위\t5위\n')
        for i in range(len(G)):
            fo.write('%d\t%s\t%.3f\t%s\n' % (i, cs[bi[i, 0]], best[i, 0], '\t'.join(cs[k] for k in bi[i, 1:])))
    # 판독 그림판: 글자 그림 + 1위 후보(검증용)
    F = ImageFont.truetype(r'C:/Windows/Fonts/meiryob.ttc', 14)
    per = 400
    for pg in range(0, len(G), per):
        S = Image.new('RGB', (20 * 64, ((min(per, len(G) - pg) + 19) // 20) * 40), (30, 30, 30)); d = ImageDraw.Draw(S)
        for k in range(min(per, len(G) - pg)):
            i = pg + k; x, y = (k % 20) * 64, (k // 20) * 40
            g = (G[i] * 17).astype(np.uint8); S.paste(Image.fromarray(g).convert('RGB').resize((32, 32), Image.NEAREST), (x, y))
            d.text((x + 34, y + 2), cs[bi[i, 0]], font=F, fill=(255, 255, 0) if best[i, 0] > 0.6 else (255, 90, 90))
            d.text((x + 34, y + 22), str(i), fill=(150, 150, 150))
        S.save(os.path.join(ROOT, 'work', 'ocr', 'sheet_%d.png' % (pg // per)))
    print('낮은 점수(<0.6)', int((best[:, 0] < 0.6).sum()), '/', len(G))


if __name__ == '__main__':
    main()
