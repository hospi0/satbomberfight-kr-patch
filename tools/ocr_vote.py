# -*- coding: utf-8 -*-
r"""OCR 결과(work/ocr/ocr.tsv) → 코드별 글자 투표 → work/ocr/vote.tsv(코드·1위·표·2위·표·총) + 확인용 그림판
  읽힌 글자 수(줄 구분 | 제거, 공백 제거) = 코드 수인 대사만 씀. 흔한 OCR 혼동(一→ー, 工→エ, 口→ロ …)은 투표 전에 맞춤.
  python tools/ocr_vote.py"""
import json, os, sys
from collections import Counter, defaultdict
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = {'一': 'ー', '|': '', ' ': '', '・・・': '…', '...': '…'}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ms = json.load(open(os.path.join(ROOT, 'work', 'ocr', 'messages.json')))
    ocr = {}
    for l in open(os.path.join(ROOT, 'work', 'ocr', 'ocr.tsv'), encoding='utf-8-sig'):
        k, _, t = l.rstrip('\n').partition('\t'); ocr[int(k)] = t
    votes = defaultdict(Counter); used = 0
    for k, m in enumerate(ms):
        t = ocr.get(k, '')
        for a, b in FIX.items(): t = t.replace(a, b)
        if len(t) == len(m['codes']):
            used += 1
            for c, ch in zip(m['codes'], t): votes[c][ch] += 1
    print('쓴 대사 %d / %d' % (used, len(ms)))
    # 반복: 확정 코드(표 ≥2, 70%↑)를 기준점으로 OCR 문장과 정렬(difflib) — 기준점 사이 칸 수가 같은 빈칸의 코드에 표
    import difflib
    texts = {}
    for k, m in enumerate(ms):
        t = ocr.get(k, '')
        for a, b in FIX.items(): t = t.replace(a, b)
        texts[k] = t
    for it in range(4):
        sure = {c: v.most_common(1)[0][0] for c, v in votes.items() if v and v.most_common(1)[0][1] >= max(2, 0.7 * sum(v.values()))}
        add = defaultdict(Counter)
        for k, m in enumerate(ms):
            cs = m['codes']; t = texts[k]
            if len(t) == len(cs): continue
            pred = ''.join(sure.get(c, '￿') for c in cs)
            sm = difflib.SequenceMatcher(None, pred, t, autojunk=False)
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op == 'replace' and i2 - i1 == j2 - j1:
                    for c, ch in zip(cs[i1:i2], t[j1:j2]): add[c][ch] += 1
        for c, v in add.items(): votes[c].update(v)
        print('  반복 %d: 정렬로 더한 코드 %d' % (it + 1, len(add)))
    allc = sorted({c for m in ms for c in m['codes']})
    with open(os.path.join(ROOT, 'work', 'ocr', 'vote.tsv'), 'w', encoding='utf-8') as f:
        f.write('code\t1위\t표\t2위\t표\t총\n')
        for c in allc:
            v = votes[c].most_common(2) + [('', 0)] * 2; tot = sum(votes[c].values())
            f.write('%d\t%s\t%d\t%s\t%d\t%d\n' % (c, v[0][0], v[0][1], v[1][0], v[1][1], tot))
    nov = [c for c in allc if not votes[c]]; weak = [c for c in allc if votes[c] and votes[c].most_common(1)[0][1] < 0.7 * sum(votes[c].values())]
    print('코드 %d · 표 없음 %d · 갈린 것 %d' % (len(allc), len(nov), len(weak)))
    # 확인 그림판(코드 순, 1위 글자 옆에)
    d = open(os.path.join(ROOT, 'work', 'TALKCHR.BIN'), 'rb').read(); F = ImageFont.truetype(r'C:/Windows/Fonts/meiryob.ttc', 15)
    per = 400
    for pg in range(0, 797, per):
        S = Image.new('RGB', (20 * 64, 20 * 40), (30, 30, 30)); dr = ImageDraw.Draw(S)
        for k in range(min(per, 797 - pg)):
            c = pg + k; x, y = (k % 20) * 64, (k // 20) * 40
            o = 0x60 + (633 + c) * 128; a = np.frombuffer(d[o:o + 128], np.uint8); g = np.stack([a >> 4, a & 15], 1).ravel().reshape(16, 16)
            S.paste(Image.fromarray((g * 17).astype(np.uint8)).convert('RGB').resize((32, 32), Image.NEAREST), (x, y))
            v = votes[c].most_common(1); tot = sum(votes[c].values())
            col = (120, 120, 120) if not v else ((255, 255, 0) if v[0][1] >= 0.7 * tot and tot >= 2 else (255, 90, 90))
            dr.text((x + 34, y + 2), v[0][0] if v else '?', font=F, fill=col); dr.text((x + 34, y + 22), str(c), fill=(150, 150, 150))
        S.save(os.path.join(ROOT, 'work', 'ocr', 'vote_%d.png' % (pg // per)))


if __name__ == '__main__':
    main()
