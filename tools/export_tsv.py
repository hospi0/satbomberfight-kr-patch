# -*- coding: utf-8 -*-
r"""번역용 TSV 내보내기(2026-11-23, 하스피 «TSV 로 뽑아 주기») — my files/tsv/sbf_NNN.tsv (UTF-8, 18 KB 단위, 자투리는 합침)
  열: 번호 · 위치(파일:바이트) · 머리(말하는 쪽,대사 번호,4) · JP · KO(빈칸)
  대사 = TALKANM.BIN 1,152줄(END1.BIN 사본도 같은 번역을 씀) · HOW TO PLAY = VS.BIN 15줄(번호 H1‥H15)
  {G778}‥{G783} = 글꼴 칸 안 그림 조각/제어(뜻 미확정) — 번역문에도 같은 자리에 그대로 둘 것.
  python tools/export_tsv.py"""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, 'tools'))
from ocr_lines import messages
from decode_script import table

LIMIT = 18 * 1024


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t, _ = table(); rows = []
    for k, m in enumerate(messages()):
        rows.append(('%d' % (k + 1), 'TALKANM.BIN:%05X' % m['off'], ','.join(map(str, m['head'])), ''.join(t.get(c, '{%d}' % c) for c in m['codes'])))
    how = json.load(open(os.path.join(ROOT, 'work', 'ocr_how', 'messages.json')))
    for k, (m, s) in enumerate(zip(how, open(os.path.join(ROOT, 'data', 'how_ja.txt'), encoding='utf-8').read().splitlines())):
        rows.append(('H%d' % (k + 1), 'VS.BIN:%05X' % m['off'], ','.join(map(str, m['head'])), s))
    out = os.path.join(ROOT, 'my files', 'tsv'); os.makedirs(out, exist_ok=True)
    head = '번호\t위치\t머리\tJP\tKO\n'; files = []; cur = head
    for r in rows:
        line = '\t'.join(r) + '\t\n'
        if len((cur + line).encode('utf-8')) > LIMIT: files.append(cur); cur = head
        cur += line
    files.append(cur)
    if len(files) > 1 and len((files[-2] + files[-1][len(head):]).encode('utf-8')) <= LIMIT: files[-2] += files[-1][len(head):]; files.pop()
    for i, c in enumerate(files):
        open(os.path.join(out, 'sbf_%03d.tsv' % (i + 1)), 'w', encoding='utf-8', newline='\n').write(c)
    print('줄', len(rows), '· 파일', len(files), '·', out)


if __name__ == '__main__':
    main()
