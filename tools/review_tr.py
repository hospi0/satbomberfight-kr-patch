# -*- coding: utf-8 -*-
r"""받은 번역 검수(2026-11-23) — my files/Download/sbf_*.tsv(처음 내보낸 1,167줄 판) → 바른 대본 1,121대사 + HOW 15줄로 옮겨 붙이고 검사
  옮기기: 새 대사 [시작, 다음 대사 시작) 안에 시작하는 옛 줄들의 KO 를 이어 붙임. 옛 판의 머리 잘못 읽은 조각(ー·最……·さ 처럼 KO=JP 그대로)은
          버리고, 남는 게 없으면 새 JP 가 부호뿐일 때 그대로 씀. 옛 서술 줄 앞 두 글자(머리를 글자로 읽은 것)는 KO 에 없으니 문제 없음.
  출력: work/review/merged.tsv(번호·위치·머리·JP·KO) · work/review/report.txt
  python tools/review_tr.py"""
import os, sys, glob, re, struct
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from ocr_lines import messages
from decode_script import table

W = 15                                                              # 대사창 한 줄 칸
PUNCT = set('!?、。…ー,.~♡「」()・')
TOK = re.compile(r'\{G\d+\}')


def load_old():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'my files', 'Download', 'sbf_*.tsv'))):
        for l in open(f, encoding='utf-8').read().splitlines()[1:]:
            p = l.split('\t'); p += [''] * (5 - len(p)); rows.append(dict(no=p[0], pos=p[1], head=p[2], jp=p[3], ko=p[4], file=os.path.basename(f)))
    return rows


def wrap_lines(s):
    """엔진 규칙(글자 단위 15칸 + {G780} 줄바꿈)으로 줄 수. 한글은 빌더가 낱말 단위로 줄바꿈 넣을 예정이라 낱말 단위로도 셈."""
    n = 0
    for part in s.split('{G780}'):
        part = TOK.sub(' ', part); words = part.split(' '); col = 0; ln = 1
        for w in words:
            if not w: continue
            need = len(w) + (1 if col else 0)
            if col + need > W:
                if col: ln += 1; col = 0
                while len(w) > W: ln += 1; w = w[W:]
                col = len(w)
            else: col += need
        n += ln
    return n


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t, _ = table(); ms = messages(); old = load_old()
    newoff = [m['off'] for m in ms] + [0x106C4]
    byoff = defaultdict(list)
    for r in old:
        if r['pos'].startswith('TALKANM'): byoff[int(r['pos'].split(':')[1], 16)].append(r)
    rep = []; out = []
    def say(*a): rep.append(' '.join(str(x) for x in a))
    for k, m in enumerate(ms):
        jp = ''.join(t.get(c, '{G%d}' % c) for c in m['codes'])
        parts = [r for o in sorted(byoff) if newoff[k] <= o < newoff[k + 1] for r in byoff[o]]
        ko = ''.join(r['ko'] for r in parts if r['ko'] != r['jp'] or not set(r['jp']) <= set('ー最……さ!'))
        if not ko and set(jp) <= PUNCT: ko = jp
        out.append(dict(no=str(k + 1), pos='TALKANM.BIN:%05X' % m['off'], head=','.join(map(str, m['head'])), jp=jp, ko=ko, src='+'.join(r['no'] for r in parts), kind='서술' if len(m['head']) == 2 else '대사'))
    for k, (r) in enumerate([r for r in old if r['pos'].startswith('VS')]):
        out.append(dict(no=r['no'], pos=r['pos'], head=r['head'], jp=r['jp'], ko=r['ko'], src=r['no'], kind='HOW'))
    os.makedirs(os.path.join(ROOT, 'work', 'review'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'review', 'merged.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('번호\t위치\t머리\tJP\tKO\t옛번호\n')
        for o in out: f.write('\t'.join((o['no'], o['pos'], o['head'], o['jp'], o['ko'], o['src'])) + '\n')

    say('== 옮기기: 옛 %d줄 → 새 %d줄(대사 %d · 서술 %d · HOW %d)' % (len(old), len(out), sum(o['kind'] == '대사' for o in out), sum(o['kind'] == '서술' for o in out), sum(o['kind'] == 'HOW' for o in out)))
    empty = [o for o in out if not o['ko']]
    say('== 빈 KO', len(empty)); [say('  ', o['no'], o['jp'][:40]) for o in empty[:20]]
    # 토큰
    bad = [o for o in out if TOK.findall(o['jp']) != TOK.findall(o['ko'])]
    say('== 토큰({G…}) 순서·개수 다름', len(bad))
    for o in bad: say('  ', o['no'], 'JP', TOK.findall(o['jp']), 'KO', TOK.findall(o['ko']), '|', o['ko'][:50])
    # 일본어 남음
    jpch = re.compile(r'[぀-ヿ一-鿿]')
    left = [(o, ''.join(sorted(set(jpch.findall(TOK.sub('', o['ko'].replace('ー', '')))))) ) for o in out]
    left = [(o, s) for o, s in left if s]
    say('== KO 에 일본어·한자 남음(ー 제외)', len(left))
    for o, s in left: say('  ', o['no'], s, '|', o['ko'][:60])
    # 줄 넘침: 원문 최대 줄 수(같은 종류) 대비
    jl = Counter();
    for o in out:
        if o['kind'] == 'HOW': continue
        jpn = sum(-(-len(TOK.sub('', p)) // W) or 1 for p in o['jp'].split('{G780}'))
        o['jpl'] = jpn; o['kol'] = wrap_lines(o['ko']); jl[o['kind'], jpn] += 1
    for kind in ('대사', '서술'):
        mx = max(o['jpl'] for o in out if o['kind'] == kind)
        say('== %s: 원문 줄 수 분포' % kind, sorted((n, c) for (kd, n), c in jl.items() if kd == kind), '최대', mx)
        over = [o for o in out if o['kind'] == kind and o['kol'] > max(o['jpl'], 0) and o['kol'] > 3]
        say('   KO(낱말 줄바꿈) 줄 수 > 원문 줄 수 이고 4줄 이상', len(over))
        for o in over[:40]: say('    ', o['no'], 'JP %d줄 KO %d줄' % (o['jpl'], o['kol']), '|', o['ko'][:70])
    # 부호 뒤 공백(빌더가 지움 — 참고)
    ps = sum(len(re.findall(r'[!?、。…,.~ー][ ]', o['ko'])) for o in out)
    say('== 부호 뒤 공백(빌더에서 자동 삭제 예정)', ps)
    # 글자 수요·대본 길이
    body = [o for o in out if o['kind'] != 'HOW']
    def norm(s): return re.sub(r'([!?、。…,.~ー]) ', r'\1', s)
    glyphs = Counter(ch for o in body for ch in TOK.sub('', norm(o['ko'])) if ch != ' ')
    say('== 대사 글자 종류', len(glyphs), '(한글 %d · 그 밖 %d)' % (sum(1 for c in glyphs if '가' <= c <= '힣'), sum(1 for c in glyphs if not '가' <= c <= '힣')), '/ 칸 778(+102 확장 가능)')
    say('   한글 아닌 글자', ''.join(sorted(c for c in glyphs if not '가' <= c <= '힣')))
    words = sum(len(m['head']) + 1 for m in ms) + sum(len(TOK.sub('x', norm(o['ko']))) for o in body) + Counter(m['end'] for m in ms)[0xFFFE] * 0
    jpw = sum(len(m['head']) + 1 + len(m['codes']) for m in ms)
    say('== 대본 길이(낱말 단위 줄바꿈 코드 빼고) KO %d워드 · 원문 %d워드 · 자리 %d워드' % (words, jpw, 0x106C4 // 2))
    how = [o for o in out if o['kind'] == 'HOW']
    hg = set(ch for o in how for ch in norm(o['ko']) if ch != ' ')
    say('== HOW 글자 종류', len(hg), '/ 칸 111(+11)', '· 길이 KO', sum(len(norm(o['ko'])) for o in how), '원문', sum(len(o['jp']) for o in how))
    open(os.path.join(ROOT, 'work', 'review', 'report.txt'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
