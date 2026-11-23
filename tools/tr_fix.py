# -*- coding: utf-8 -*-
r"""번역 일괄 고침(2026-11-23 하스피 결정) — work/review/merged.tsv → data/ko.tsv(빌드 입력) + work/review/changes.tsv(바뀐 줄 전부 기록)
  1) 이름: 하얀 봄버→흰봄·검은 봄버→검은봄(그림 판에 맞춤, 조사 받침) · 코테쓰 → 코테츠
  2) アチキ(저승사자 1인칭) «아치키» → «이 몸» + 조사 받침 맞춤(는→은·가→이·를→을, 한테·의·만·한텐 그대로) · 맨 «아치키 명사» → «이 몸의 명사»(«따라» 앞만 «이 몸»)
  3) 장음 ー → ~
  4) 남은 가나: ッ → 잇 · ク → 크
  5) 원문 배치용 문장 중간 {G780} 정리(mid_break) · 6) HOW 글자 111칸 맞춤: 높은 곳에도→높은 데에도, 땅에 놓지 않고→놓지 않고
  python tools/tr_fix.py"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RULES = [
    ('흰봄·검은봄', lambda s: re.sub(r'(하얀|검은) ?봄버(?!맨)(가|는|를|냐|)',            # 하스피 «대사는 그림판에 맞추자» — 받침 ㅁ 조사
                                  lambda m: ('흰봄' if m.group(1) == '하얀' else '검은봄') + {'가': '이', '는': '은', '를': '을', '냐': '이냐'}.get(m.group(2), m.group(2)), s)),
    ('코테쓰', lambda s: s.replace('코테쓰', '코테츠')),
    ('아치키→이 몸', lambda s: re.sub(r'아치키(는|가|를|한테|한텐|의|만| 따라| |)',
                                   lambda m: '이 몸' + {'는': '은', '가': '이', '를': '을', ' ': '의 ', ' 따라': ' 따라'}.get(m.group(1), m.group(1)), s)),
    ('ー→~', lambda s: s.replace('ー', '~')),
    ('ッ→잇·ク→크', lambda s: s.replace('ッ', '잇').replace('ク', '크')),
    ('문장 중간 {G780}', lambda s: mid_break(s)),
    ('HOW H6 3줄', lambda s: s.replace('폭탄이 발밑에 놓여 있을 때 A·C 버튼을 누르면 폭탄을 듭니다. 그 상태에서 다시 한 번 A·C 버튼을 누르면 던집니다.',
                                       '폭탄이 발밑에 있을 때 A·C 버튼을 누르면 폭탄을 듭니다. 한 번 더 A·C 버튼을 누르면 던집니다.')),   # HOW 창 3줄(20×3, 쪽 넘김 없음) — 하스피 선택
    ('HOW 글자 111칸', lambda s: s.replace('높은 곳에도', '높은 데에도').replace('땅에 놓지 않고', '놓지 않고')),   # 하스피 승인(113종→111)
]


def mid_break(s):
    """원문 배치(줄 끝 맞춤)용 줄바꿈이 번역에 그대로 옮겨진 것 — 앞이 문장 끝 부호가 아니면: 낱말 사이(목록)·쉼표 뒤 → 공백, 낱말 안 → 붙임.
       문장 끝 부호(!?.…~♡) 뒤 줄바꿈은 일부러 넣은 것으로 보고 둠(앞 공백만 지움)."""
    for a in ('용서치{G780}않', '봤자{G780}시시'): s = s.replace(a, a.replace('{G780}', ' '))   # 낱말 사이(눈으로 확인한 2곳)
    def f(m):
        L = m.group(1)
        if not L: return '{G780}'                                    # 대사 맨 앞(서술 단락) — 둠
        if re.search(r'[!?.…~♡)\]]$', L): return L + '{G780}'
        if L.endswith(' '): return L.rstrip() + '{G780}' if re.search(r'[!?.…~♡]$', L.rstrip()) else L
        if L.endswith(','): return L + ' '
        return L
    return re.sub(r'(.?\s?)\{G780\}', f, s)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = os.path.join(ROOT, 'work', 'review', 'merged.tsv')
    lines = open(src, encoding='utf-8').read().splitlines(); head = lines[0].split('\t')
    out = [lines[0]]; log = ['번호\t규칙\t전\t후']; n = 0
    for l in lines[1:]:
        p = l.split('\t'); ko = p[4]
        for name, f in RULES:
            new = f(ko)
            if new != ko: log.append('\t'.join((p[0], name, ko, new))); ko = new
        if ko != p[4]: n += 1
        p[4] = ko; out.append('\t'.join(p))
    left = [l.split('\t')[0] for l in out[1:] if re.search(r'[぀-ヿ一-鿿]', re.sub(r'\{G\d+\}', '', l.split('\t')[4]).replace('・', ''))]
    assert not left, ('가나·한자 남음', left)
    assert not any('아치키' in l.split('\t')[4] or '코테쓰' in l.split('\t')[4] for l in out[1:])
    open(os.path.join(ROOT, 'data', 'ko.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    open(os.path.join(ROOT, 'work', 'review', 'changes.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(log) + '\n')
    print('바뀐 줄', n, '· 규칙 적용', len(log) - 1, '→ data/ko.tsv · work/review/changes.tsv')


if __name__ == '__main__':
    main()
