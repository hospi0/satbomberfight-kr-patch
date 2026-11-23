# -*- coding: utf-8 -*-
r"""대본(TALKANM.BIN) → 일본어 문장(판독표 = OCR 투표 work/ocr/vote.tsv + 손 판독 data/charmap_fix.tsv)
  출력 work/script_ja.tsv(번호·위치·머리·끝표·문장) · 표 data/charmap.tsv(코드·글자·출처) · 같은 글자 여러 코드 문맥 work/script_dups.txt
  python tools/decode_script.py"""
import json, os, sys
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from ocr_lines import messages


def table():
    t = {}; src = {}
    for l in open(os.path.join(ROOT, 'work', 'ocr', 'vote.tsv'), encoding='utf-8').read().splitlines()[1:]:
        r = l.split('\t')
        if r[1]: t[int(r[0])] = r[1]; src[int(r[0])] = 'ocr %s/%s' % (r[2], r[5])
    for l in open(os.path.join(ROOT, 'data', 'charmap_fix.tsv'), encoding='utf-8').read().splitlines():
        if l.startswith('#') or l.startswith('code') or not l.strip(): continue
        r = l.split('\t'); t[int(r[0])] = r[1]; src[int(r[0])] = '손'
    return t, src


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t, src = table(); ms = messages()
    with open(os.path.join(ROOT, 'data', 'charmap.tsv'), 'w', encoding='utf-8') as f:
        f.write('code\t글자\t출처\n')
        for c in range(797): f.write('%d\t%s\t%s\n' % (c, t.get(c, ''), src.get(c, '')))
    END = {0xFFFF: '', 0xFFFE: '◆', 0xFFFC: '■'}
    lines = []
    with open(os.path.join(ROOT, 'work', 'script_ja.tsv'), 'w', encoding='utf-8') as f:
        for k, m in enumerate(ms):
            s = ''.join(t.get(c, '{%d}' % c) for c in m['codes']); lines.append(s)
            f.write('%d\t%05X\t%s\t%s\t%s\n' % (k, m['off'], ','.join(map(str, m['head'])), END.get(m['end'], m['end']), s))
    by = defaultdict(list)
    for c, ch in t.items(): by[ch].append(c)
    with open(os.path.join(ROOT, 'work', 'script_dups.txt'), 'w', encoding='utf-8') as f:
        for ch, cs in sorted(by.items()):
            if len(cs) < 2 or ch.startswith('{'): continue
            f.write('== %s %s\n' % (ch, cs))
            for c in cs:
                n = 0
                for m in ms:
                    if c in m['codes'] and n < 3:
                        i = m['codes'].index(c); ctx = ''.join(t.get(x, '?') for x in m['codes'][max(0, i - 5):i + 6])
                        f.write('  %d: %s\n' % (c, ctx)); n += 1
    unk = sorted({c for m in ms for c in m['codes'] if c not in t})
    print('대사', len(ms), '· 모르는 코드', len(unk), unk[:40])


if __name__ == '__main__':
    main()
