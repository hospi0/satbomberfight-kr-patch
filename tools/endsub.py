# -*- coding: utf-8 -*-
r"""엔딩 그림 장면 음성 자막(2026-11-23) — build_text.py 가 끝에서 부름
  원본은 엔딩 둘째 서술(그림 장면 6개)이 음성만 나오고 글자를 안 찍는다 → END1.BIN 안에 자막 루틴을 넣음.
  · 음성 재생 리터럴 END1 0x0607251C(0x06009498) → play: (폴더<<8 | 번호)로 쪽 표를 찾아 걸어 두고 원래 함수로.
  · 컨트롤러 객체 클래스 0x0608BB40 의 매 프레임 함수(0x06070500) → tick: 재생 상태 0x060360C4 == 3 이 되면 시각 시작
    (SGL VBlank 카운터 u16 0x060FFC22, 60fps), 쪽 시각이 되면 표식(stamp)을 올리고 글자 객체를 새로 만듦 → 원래 함수로.
  · 글자 객체 = 원래 엔딩 글자 객체(초기화 0x06072524 그대로) + 우리 매 프레임 함수 upd(자기 표식 ≠ 지금 표식이면 지움 표시 0x8000).
  · 코드·자료 = END1 대본 자리(0x8398+0x106C4) 끝의 남는 곳 · 글자 그림 = 엔딩 서술이 안 쓰는 END1CHR 칸(검은 테두리 1px, 팔레트 7E0 회색 램프).
"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from kfont import glyph, pack
from sh2asm import assemble

BASE = 0x06070000; END = 0x18A5C                                      # END1 적재 · 대본 자리 끝(파일)
PLAY_LIT, TICK_LIT = 0x251C, 0x1BB44
COLS = 19; MAXW = 304                                               # 한 줄 글자 수 · 폭(px)
NARROW = '.,!'                                                       # 8px 부호 — 코드 0x300 이상 칸(루틴이 코드>>8 == 3 이면 8px, 공백도 8px, 나머지 15px)
# 쪽 시각(초) = 음성 파일 무음 구간(−35 dB)으로 잰 말 시작. 줄 = 화면 줄 그대로(글자는 data/ko.tsv 번역 그대로, 부호 뒤 공백 없음)
SUBS = [  # (폴더 번호, 음성 번호, ko.tsv 줄, [(초, [줄…])…])
    (0, 78, 84, [(0, ['그러기 위해서도 특훈이다~!', '하자~검은봄!'])]),
    (0, 79, 85, [(0, ['그러니까,왜 나만~!!'])]),
    (1, 91, 177, [(0, ['조금만 더 하면 된다~!', '힘내라 검은봄~!'])]),
    (1, 92, 178, [(0, ['알고 있다고~!'])]),
    (3, 81, 344, [(0.3, ['코테츠~!쇼핑하러 갈 거야~!']), (3.6, ['이것도 수행이니까,', '제대로 짐을 들도록 해~!'])]),
    (3, 82, 345, [(0.3, ['……추신']), (2.2, ['가끔,소생이 선택한 길이 잘못이었던', '게 아닌가 싶을 때가 있소…'])]),
    (6, 65, 481, [(0, ['이~~크!'])]),
    (8, 65, 614, [(0, ['……페기,너도 남자아이였구나'])]),
    (7, 74, 974, [(0.2, ['나의 일은 이른바 뒷일이다.']), (4.5, ['닌자에게 널리 신상이', '알려진다는 것은']), (8.2, ['닌자로서 죽은 것이나 다름없다.']),
                  (11.2, ['그것을 잊고,대회 따위에', '참가해 버린 것은']), (15.7, ['의뢰라고는 해도 나의 불찰.']), (19.3, ['어둠 속에 살아야 비로소 닌자.']),
                  (22.5, ['나는 새로운 땅에서', '다시 어둠 속에 살 작정이다.']), (27.5, ['이만 작별'])]),
    (7, 75, 975, [(0.3, ['프리랜서 닌자,덴타.']), (3.5, ['그는 지금도,아무도 모르게', '어둠 속에 산다'])]),
]
Y = {1: (84,), 2: (64, 84)}                                          # 줄 y(화면 가운데 0, 224줄 → 아래 여백 12)

SRC = r"""
play:
  mov.l #%(VARS)s,r3
  mov #0,r0
  mov.l r0,@r3
  mov.l r0,@(8,r3)
  mov.l @(4,r3),r1
  add #1,r1
  mov.l r1,@(4,r3)
  mov.l #%(TABLE)s,r2
  mov r5,r1
  shll8 r1
  add r4,r1
ploop:
  mov.l @r2+,r0
  tst r0,r0
  bt pdone
  cmp/eq r0,r1
  bt pfound
  bra ploop
  add #4,r2
pfound:
  mov.l @r2,r0
  mov.l r0,@r3
pdone:
  mov.l #0x06009498,r0
  jmp @r0
  nop
tick:
  sts.l pr,@-r15
  mov.l r4,@-r15
  mov.l r5,@-r15
  mov.l r6,@-r15
  mov.l r8,@-r15
  mov.l r9,@-r15
  mov.l r10,@-r15
  mov.l r11,@-r15
  mov.l #%(VARS)s,r8
  mov.l @r8,r9
  tst r9,r9
  bt out
  mov.l #0x060360C4,r1
  mov.l @r1,r1
  mov.l #0x060FFC22,r2
  mov.w @r2,r2
  extu.w r2,r2
  mov.l @(8,r8),r0
  tst r0,r0
  bf running
  mov r1,r0
  cmp/eq #3,r0
  bf out
  mov #1,r0
  mov.l r0,@(8,r8)
  mov.l r2,@(12,r8)
running:
  mov.l @(4,r8),r3
  add #1,r3
  mov #0,r0
  cmp/ge r0,r1
  bt alive
  mov.l r0,@r8
  bra out
  mov.l r3,@(4,r8)
alive:
  mov.l @(12,r8),r0
  sub r0,r2
  extu.w r2,r2
  mov.w @r9,r0
  extu.w r0,r0
  cmp/hs r0,r2
  bf out
  mov.l r3,@(4,r8)
  add #2,r9
next:
  mov.w @r9+,r0
  cmp/pz r0
  bt char
  cmp/eq #-1,r0
  bt pgend
  cmp/eq #-3,r0
  bt adv
  extu.b r0,r10
  add #-128,r10
  shll r10
  shlr8 r0
  mov #0x7f,r11
  bra next
  and r0,r11
char:
  mov.l #0x0604A890,r1
  mov.l r0,@r1
  mov r10,r2
  shll16 r2
  mov.l r2,@(4,r1)
  mov r11,r2
  shll16 r2
  mov.l r2,@(8,r1)
  mov.l @(4,r8),r2
  mov.l r2,@(12,r1)
  mov.l #%(CLS)s,r5
  mov.l #0x06048B20,r4
  mov.l #0x060077A0,r1
  jsr @r1
  nop
  mov.l #0x0604A890,r1
  mov.l @r1,r0
  shlr8 r0
  cmp/eq #3,r0
  bt adv
  bra next
  add #15,r10
adv:
  bra next
  add #8,r10
pgend:
  mov.l r9,@r8
out:
  mov.l @r15+,r11
  mov.l @r15+,r10
  mov.l @r15+,r9
  mov.l @r15+,r8
  mov.l @r15+,r6
  mov.l @r15+,r5
  mov.l @r15+,r4
  lds.l @r15+,pr
  mov.l #0x06070500,r0
  jmp @r0
  nop
upd:
  mov.l #%(VARS)s,r2
  mov.l @(4,r2),r2
  extu.w r2,r2
  mov r6,r3
  add #2,r3
  mov.w @r3,r3
  extu.w r3,r3
  mov r5,r1
  add #9,r1
  cmp/eq r2,r3
  bt live
  mov #-1,r0
  mov.b r0,@r1
  add #-7,r1
  mov #-128,r0
  shll8 r0
  rts
  mov.w r0,@r1
live:
  mov #3,r0
  rts
  mov.b r0,@r1
"""


def outlined(ch):
    """글자 몸통(밝은 단색 + 바림) + 바깥 1px 검은 테두리(번호 1) — 16×16, 0 = 투명"""
    g = glyph(ch, size=14)
    a = np.zeros((16, 16), int)
    ys, xs = np.nonzero(g)
    dy = min(0, 14 - ys.max()); dx = min(0, 14 - xs.max())           # 테두리 자리(1‥14) 안으로
    dy += max(0, 1 - (ys.min() + dy)); dx += max(0, 1 - (xs.min() + dx))
    for y, x in zip(ys, xs):
        yy, xx = y + dy, x + dx
        if not (1 <= yy <= 14 and 1 <= xx <= 14):
            assert g[y, x] <= 4, (ch, yy, xx, g[y, x]); continue      # 흐린 가장자리 한 줄은 버림
        a[yy, xx] = g[y, x]
    ink = a >= 5; dil = np.zeros_like(ink)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1): dil |= np.roll(np.roll(ink, oy, 0), ox, 1)
    out = np.where(a >= 2, np.maximum(a, 1), np.where(dil, 1, 0))
    if ch in NARROW:                                                 # 8px 부호: 잉크를 왼쪽으로(테두리 포함 8칸 안)
        xs = np.nonzero(out.any(0))[0]; w = xs.max() - xs.min() + 1; assert w <= 8, (ch, w)
        out = np.roll(out, (8 - w) // 2 - xs.min(), 1)
    return out


def width(l): return sum(8 if c == ' ' or c in NARROW else 15 for c in l) + 1


def asm2(text, base):
    """어셈블 + 라벨 주소(명령 하나 2 B, 리터럴 풀은 끝에만 있음)"""
    lab = {}; pc = base
    for raw in text.split('\n'):
        s = raw.split(';')[0].strip()
        if not s: continue
        if s.endswith(':'): lab[s[:-1]] = pc
        else: pc += 2
    return assemble(text, base), lab


def build(rows, free):
    """→ (파일 시작 위치, 바이트, {코드: 그림}, 글자→코드, 라벨). free = 쓸 수 있는 END1CHR 글자 코드"""
    chars = []
    for f, n, k, pages in SUBS:                                      # 번역문과 글자 대조(공백·줄 나눔만 다름)
        src = rows[str(k)][4].replace('{G779}', ' '); a = ''.join(src.split()); b = ''.join(''.join(l) for _, p in pages for l in p).replace(' ', '')
        assert a == b, ('번역과 다름', k, a, b)
        for _, ls in pages:
            assert len(ls) <= 2
            for l in ls:
                assert len(l) <= COLS, ('줄 넘침', l, len(l)); chars += [c for c in dict.fromkeys(l) if c != ' ' and c not in chars]
    assert len(chars) <= len(free), (len(chars), len(free))
    hi = [c for c in free if c >= 0x300]; lo = [c for c in free if c < 0x300]; nar = [c for c in chars if c in NARROW]
    assert len(nar) <= len(hi); cmap = {**dict(zip([c for c in chars if c not in NARROW], lo)), **dict(zip(nar, hi))}; glyphs = {cmap[c]: pack(outlined(c)) for c in chars}
    pg = b''; key = []
    for f, n, k, pages in SUBS:
        key.append((f << 8 | n, len(pg)))
        for t, ls in pages:
            w = [round(t * 60)]
            for l, y in zip(ls, Y[len(ls)]):
                assert 0 < y < 127 and width(l) <= MAXW
                w += [0x8000 | y << 8 | (128 - width(l) // 4)] + [0xFFFD if c == ' ' else cmap[c] for c in l]
            pg += struct.pack('>%dH' % len(w), *w) + b'\xff\xff'
        pg += b'\xff\xff'                                            # 다음 쪽 시각 0xFFFF = 없음
    if len(pg) % 4: pg += b'\xff\xff'
    # 배치: [코드][클래스 20 B][변수 16 B][표][쪽] — 끝을 END 에 맞춤(4 B FFFF 는 남김)
    syms = lambda b, n: dict(VARS='0x%X' % (b + n + 20), TABLE='0x%X' % (b + n + 36), CLS='0x%X' % (b + n))
    n = (len(assemble(SRC % syms(BASE, 0), BASE)) + 3) & ~3
    total = n + 20 + 16 + len(key) * 8 + 4 + len(pg)
    start = END - 4 - total; assert start % 4 == 0; a0 = BASE + start
    code, lab = asm2(SRC % syms(a0, n), a0)
    assert len(code) <= n; code = code.ljust(n, b'\0')
    cls = struct.pack('>5I', 0x06072524, lab['upd'], 0x0608AEF8, 0x0608AEF8, 0x7E0)
    pbase = a0 + n + 36 + len(key) * 8 + 4
    tab = b''.join(struct.pack('>II', k, pbase + o) for k, o in key) + bytes(4)
    blob = code + cls + bytes(16) + tab + pg; assert len(blob) == total
    return start, blob, glyphs, cmap, lab


def emit(put, end1, rows, blob, used_codes):
    """build_text 에서: END1 대본 사본(blob)의 끝 남는 곳에 자막 덩어리를 끼운 바이트를 돌려주고, 글자 그림·리터럴 두 칸을 put"""
    free = [c for c in range(778) if c not in used_codes]
    start, sub, glyphs, cmap, lab = build(rows, free)
    o = start - 0x8398; assert set(blob[o - 2:]) == {0xFF}, ('대본 끝 남는 자리 모자람', hex(start))
    out = blob[:o] + sub + blob[o + len(sub):]; assert len(out) == len(blob)
    for at, old, new in ((PLAY_LIT, 0x06009498, lab['play']), (TICK_LIT, 0x06070500, lab['tick'])):
        assert struct.unpack('>I', end1[at:at + 4])[0] == old; put('END1.BIN', at, struct.pack('>I', new))
    for c, g in glyphs.items(): put('END1CHR.BIN', c * 128, g)
    spare = o - len(blob.rstrip(b'\xff'))
    print('엔딩 음성 자막: 음성 %d · 쪽 %d · 글자 %d종(빈 칸 %d) · %d B @END1 0x%X (더 남는 자리 %d B)' % (
        len(SUBS), sum(len(p) for *_, p in SUBS), len(glyphs), len(free), len(sub), start, spare))
    return out
