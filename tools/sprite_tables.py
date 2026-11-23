# -*- coding: utf-8 -*-
r"""스프라이트 정의 표 전수(2026-11-23) — 코드 파일 안 8 B 항목 [u16 폭][u16 높이][u16 VRAM/8][u16 크기(폭/8<<8|높이)]
  그림 파일 기준 = 스테이트 짝짓기(work/states_map.tsv)의 «VRAM − 파일 위치»(파일마다 하나여야 함).
  항목의 VRAM 이 기준 + 파일 크기 안이면 그 그림 파일의 스프라이트로 봄 → work/sprites.tsv(그림 파일·위치·폭·높이·표 파일·표 위치)
  그림판(회색조 4비트) work/check/전체그림/<그림 파일>_N.png
  python tools/sprite_tables.py"""
import os, struct, sys
from collections import Counter, defaultdict
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from iso import Disc


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    D = Disc(1); files = {p.strip('/'): D.read(p.strip('/')) for p, l, s in D.files if not p.endswith(('.DAT', '.SND'))}
    base = defaultdict(Counter)
    for l in open(os.path.join(ROOT, 'work', 'states_map.tsv'), encoding='utf-8').read().splitlines()[1:]:
        r = l.split('\t')
        if not r[8]: continue
        fn, off = r[8].split(':'); base[fn][int(r[1], 16) - int(off, 16)] += 1
    bases = {fn: c.most_common(1)[0][0] for fn, c in base.items()}
    print('그림 파일 기준', {k: hex(v) for k, v in bases.items()})
    def ent(d, o):
        if o < 0 or o + 8 > len(d): return None
        w, h, src, sz = struct.unpack_from('>HHHH', d, o)
        if not (8 <= w <= 352 and 1 <= h <= 256 and w % 8 == 0 and sz == ((w // 8) << 8 | h)): return None
        return w, h, src * 8
    cand = defaultdict(list)                                         # (표 파일, 그림 파일) → [(그림 위치, 폭, 높이, 표 위치)]
    for tf, d in files.items():
        for o in range(0, len(d) - 8, 2):
            e = ent(d, o)
            if not e: continue
            w, h, va = e
            for fn, b in bases.items():
                fo = va - b
                if not (0 <= fo and fo + w * h // 2 <= len(files[fn])): continue
                ok = False
                for oo in (o - 8, o + 8):                            # 이웃 항목도 같은 그림 파일
                    e2 = ent(d, oo)
                    if e2 and 0 <= e2[2] - b and e2[2] - b + e2[0] * e2[1] // 2 <= len(files[fn]): ok = True
                if ok: cand[(tf, fn)].append((fo, w, h, o))
    PAIRS = {('TIT.BIN', 'TITCHR.BIN'), ('PLS.BIN', 'PLSCHR.BIN'), ('PLS.BIN', 'STGSPR.A'), ('PLS.BIN', 'VPMDCHR.BIN'), ('PLS2.BIN', 'PLS2.BIN'),
             ('PLS2.BIN', 'NUKI.BIN'), ('VS.BIN', 'VSCHR.BIN'), ('VS.BIN', 'HOWCHR.BIN'), ('VS.BIN', 'TALKCHR.BIN'), ('VS.BIN', 'END1CHR.BIN')}   # 스테이트 스프라이트가 든 표로 확인한 짝
    found = {}
    for (tf, fn), L in cand.items():
        if (tf, fn) not in PAIRS: continue
        for fo, w, h, o in L: found.setdefault((fn, fo, w, h), (tf, o))
    print('표 짝', sorted(((tf, fn, len(L)) for (tf, fn), L in cand.items() if len(L) >= 10), key=lambda x: -x[2]))
    with open(os.path.join(ROOT, 'work', 'sprites.tsv'), 'w', encoding='utf-8') as f:
        f.write('chr\toff\tw\th\ttable\ttoff\n')
        for (fn, fo, w, h), (tf, o) in sorted(found.items()): f.write('%s\t%X\t%d\t%d\t%s\t%X\n' % (fn, fo, w, h, tf, o))
    print('스프라이트', len(found), Counter(k[0] for k in found).most_common())
    out = os.path.join(ROOT, 'work', 'check', '전체그림3'); os.makedirs(out, exist_ok=True)
    by = defaultdict(list)
    for (fn, fo, w, h) in sorted(found): by[fn].append((fo, w, h))
    for fn, L in by.items():
        d = files[fn]; W = 1400; x = y = rh = 0; pg = 0; S = Image.new('L', (W, 1600), 40); Dd = ImageDraw.Draw(S)
        for fo, w, h in L:
            a = np.frombuffer(d[fo:fo + w * h // 2], np.uint8); ix = np.stack([a >> 4, a & 15], 1).ravel().reshape(h, w)
            im = Image.fromarray((ix * 17).astype(np.uint8))
            if x + max(w, 60) > W: x = 0; y += rh + 12; rh = 0
            if y + h + 12 > 1600:
                S.save(os.path.join(out, '%s_%d.png' % (fn, pg))); pg += 1; S = Image.new('L', (W, 1600), 40); Dd = ImageDraw.Draw(S); x = y = rh = 0
            Dd.text((x, y), '%X' % fo, fill=255); S.paste(im, (x, y + 10)); x += max(w, 60) + 6; rh = max(rh, h + 10)
        S.crop((0, 0, W, y + rh + 12)).save(os.path.join(out, '%s_%d.png' % (fn, pg)))


if __name__ == '__main__':
    main()
