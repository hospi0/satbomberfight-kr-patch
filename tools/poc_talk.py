# -*- coding: utf-8 -*-
r"""첫 대사 한글 PoC(2026-11-23) — 스샷에 보이는 첫 대사 «なんだー!?最初の相手は黒ボンかー!» → «뭐야!? 첫 상대가 검은봄이냐!»
  한글 음절은 대본 뒤쪽에서 «한 번만·가장 늦게» 쓰이는 한자 칸을 빌려 덮음(그 대사들만 잠깐 엉뚱한 글자 — 시험본 한정).
  ! ? 는 원래 코드(40, 22) 그대로 · 빈칸 = 779(루틴: 778 초과 = 안 그리고 한 칸 넘김) · 남는 칸은 779 로 채워 길이 같게.
  출력: work/text/TALKANM.BIN@0.bin(대본 첫 대사 범위) · work/text/TALKCHR.BIN@<위치>.bin(글자 칸) · 미리보기 work/check/그림미리보기/PoC_첫대사.png
  python tools/poc_talk.py"""
import os, sys, struct, glob
from collections import Counter
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from ocr_lines import messages
from decode_script import table
from kfont import glyph, pack

KO = '뭐야!? 첫 상대가 검은봄이냐!'
KEEP = {'!': 40, '?': 22}
SPACE = 779


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t, _ = table(); inv = {}
    for c, ch in t.items(): inv.setdefault(ch, c)
    assert t[40] == '!' and t[22] == '?', (t[40], t[22])
    ms = messages(); m0 = ms[0]
    first = {}; cnt = Counter()
    for k, m in enumerate(ms):
        for c in m['codes']: cnt[c] += 1; first.setdefault(c, k)
    # 빌릴 칸: 0‥777 중 줄 끝 부호(3,21,22,40,51) 아님 · 1회 사용 · 처음 쓰임이 가장 늦은 것
    cand = sorted((c for c in range(778) if cnt[c] == 1 and c not in (3, 21, 22, 40, 51)), key=lambda c: -first[c])
    syl = []
    for ch in KO:
        if ch not in KEEP and ch != ' ' and ch not in syl: syl.append(ch)
    slot = dict(zip(syl, cand)); assert len(slot) == len(syl)
    codes = [KEEP.get(ch) or (SPACE if ch == ' ' else slot[ch]) for ch in KO]
    n = len(m0['codes']); assert len(codes) <= n, (len(codes), n)
    codes += [SPACE] * (n - len(codes))
    out = os.path.join(ROOT, 'work', 'text'); os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, '*@*.bin')): os.remove(f)
    T = open(os.path.join(ROOT, 'work', 'TALKANM.BIN'), 'rb').read()
    o = m0['off'] + 2 * len(m0['head'])
    assert struct.unpack('>%dH' % n, T[o:o + 2 * n]) == tuple(m0['codes'])
    open(os.path.join(out, 'TALKANM.BIN@%X.bin' % o), 'wb').write(struct.pack('>%dH' % n, *codes))
    tiles = []
    for ch, c in slot.items():
        g = glyph(ch); tiles.append(g); off = 0x60 + (633 + c) * 128
        open(os.path.join(out, 'TALKCHR.BIN@%X.bin' % off), 'wb').write(pack(g))
        print('  %s → 칸 %d(원래 %s, 처음 쓰임 대사 %d)' % (ch, c, t.get(c), first[c] + 1))
    print('  첫 대사 코드', codes)
    img = np.hstack([np.pad(g, 1) for g in tiles]) * 17
    Image.fromarray(img.astype(np.uint8)).resize((img.shape[1] * 4, img.shape[0] * 4), Image.NEAREST).save(
        os.path.join(ROOT, 'work', 'check', '그림미리보기', 'PoC_첫대사_글자.png'))


if __name__ == '__main__':
    main()
