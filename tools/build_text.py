# -*- coding: utf-8 -*-
r"""대사·엔딩·HOW TO PLAY 한글 대본+글꼴 만들기(2026-11-23) — data/ko.tsv(tools/tr_fix.py) → work/text/<파일>@<위치>.bin (tools/build.py 가 넣음)
  대본 규칙(VS.BIN 루틴 분석, docs/00_초기조사.md 4차): 글자 0‥778 그림 · 779 = 빈칸(안 그리고 한 칸) · 780 = 줄바꿈 · FFFF/FFFE/FFFD/FFFC 끝 표시.
  · 부호 뒤 공백 삭제(전프로젝트 규칙) · 공백 = 779 · 낱말 단위 줄바꿈: 공백을 780 으로(줄이 꽉 차면 엔진이 스스로 넘기므로 780 생략)
    줄 폭 = 대사·엔딩 13칸(말하는 쪽마다 13‥15, 21−표값 — 가장 좁은 값), HOW 20칸(0x06083EC2 MOV #0x14).
  · 글꼴: 원래 글꼴에 있는 부호·숫자·영문은 원래 코드·그림 그대로. 줄 끝 매달기 코드 3(、)·51(。)은 한글 , . 로 다시 그림.
    나머지(한글·새 부호)는 남는 코드에 많이 쓰는 순으로. 대사 0‥777(778 = 원래 그림 조각 그대로), HOW 0‥110.
  · 대본은 원래 자리 크기 그대로(뒤 애니메이션 표 절대 주소) — 남으면 마지막 끝 표시 뒤를 FFFF 로 채움, 넘치면 실패.
  · 대사 대본 한 벌을 TALKANM.BIN(0)과 END1.BIN(0x8398) 두 곳에, 글꼴을 TALKCHR(0x60+(633+c)×128)·END1CHR(c×128) 두 곳에.
  python tools/build_text.py"""
import os, re, sys, glob, struct, json
from collections import Counter
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from ocr_lines import messages
from decode_script import table
from kfont import glyph, pack

TOK = re.compile(r'\{G(\d+)\}')
PUNCT_SP = re.compile(r'([!?,.~…♡・:;)」』\]]) +')
SPACE, NL = 779, 780
REDRAW = {',': 3, '.': 51}                                          # 줄 끝 매달기 칸을 한글 부호로


def prep(s):
    s = s.replace('{G779}', ' ')                                    # 779 = 빈칸 — 보통 공백으로(줄 첫머리 빈칸 막음, 부호 뒤면 지움)
    return PUNCT_SP.sub(r'\1', s).strip(' ')


def tokens(s):
    """문자열 → [('c', 글자) | ('g', 코드)]"""
    out = []; i = 0
    for m in TOK.finditer(s):
        out += [('c', ch) for ch in s[i:m.start()]]; out.append(('g', int(m.group(1)))); i = m.end()
    return out + [('c', ch) for ch in s[i:]]


BRK = set(',.!?~…♡')


def wrap(toks, W, exact=False):
    """낱말 단위 줄바꿈(2026-11-23 고침 — 하스피 스샷 «않았어도확실히», «네부하야?»):
       창 폭이 말하는 쪽마다 13·15·16칸으로 달라 «꽉 찬 줄은 엔진이 넘긴다»는 가정이 16칸 창에서 깨져 공백이 사라졌다.
       → 한 줄을 W(= 가장 좁은 창 13 − 1 = 12)칸 이하로 하고 줄바꿈은 «항상 780 을 직접» 넣는다. 공백은 지우지 않는다(줄 첫머리 공백만 버림).
       끊는 자리 = 공백, 부호(, . ! ? ~ … ♡) 바로 뒤. W 보다 긴 낱말은 W 칸마다 780 으로 자름.
       exact=True(HOW TO PLAY — 창 폭 20칸 하나뿐): 줄이 W 칸을 꽉 채우면 엔진이 넘기므로 그 뒤 공백·780 을 넣지 않는다."""
    segs = []; cur = []; sp = False
    def flush():
        nonlocal cur, sp
        if cur: segs.append((sp, cur))
        cur = []; sp = False
    for t in toks:
        if t == ('g', NL): flush(); segs.append(('NL', None)); continue
        if t == ('c', ' '): flush(); sp = True; continue
        cur.append(t)
        if t[0] == 'c' and t[1] in BRK: flush()
    flush()
    out = []; col = 0; auto = False
    for sp, seg in segs:
        if sp == 'NL':
            if not auto: out.append(('g', NL))
            col = 0; auto = False; continue
        if exact and auto: sp = False                               # 엔진이 막 넘긴 줄 첫머리
        auto = False
        need = len(seg) + (1 if sp and col else 0)
        if col and col + need > W:
            out.append(('g', NL)); col = 0
        elif sp and col:
            out.append(('c', ' ')); col += 1
        while col + len(seg) > W:                                   # 한 줄보다 긴 낱말
            k = W - col; out += seg[:k]; out.append(('g', NL)); seg = seg[k:]; col = 0
        out += seg; col += len(seg)
        if exact and col == W: col = 0; auto = True
    while out and out[-1] in (('c', ' '), ('g', NL)): out.pop()
    n = 0
    for t in out:
        n = 0 if t == ('g', NL) or (exact and n == W) else n
        if t != ('g', NL): n += 1
        assert n <= W, ('줄 넘침', n)
    return out


def assign(texts, orig, nslots, keep_draw):
    """texts: 토큰 목록들 · orig: 원래 코드→글자 · 반환 글자→코드, 새로 그릴 {코드: 글자}"""
    inv = {}
    for c, ch in orig.items():
        if c < nslots and ch and not ('가' <= ch <= '힣'): inv.setdefault(ch, c)
    freq = Counter(ch for tk in texts for k, ch in tk if k == 'c' and ch != ' ')
    cmap = {}; draw = {}
    for ch, c in REDRAW.items():
        if ch in freq: cmap[ch] = c; draw[c] = ch
    for ch in freq:
        if ch in cmap: continue
        if ch in inv and inv[ch] not in draw: cmap[ch] = inv[ch]        # 원래 그림 그대로
    used = set(cmap.values()) | set(keep_draw)
    free = [c for c in range(nslots) if c not in used]
    new = [ch for ch, _ in freq.most_common() if ch not in cmap]
    assert len(new) <= len(free), ('글자 칸 모자람', len(new), len(free))
    for ch, c in zip(new, free): cmap[ch] = c; draw[c] = ch
    return cmap, draw


def encode(tk, cmap):
    out = []
    for k, v in tk:
        if k == 'g': out.append(v)
        elif v == ' ': out.append(SPACE)
        else:
            assert v in cmap, ('글자표에 없음', v); out.append(cmap[v])
    return out


def rebuild(words, msgs, newcodes, size):
    """원래 낱말 배열에서 각 대사의 글자 부분만 갈아 끼움(머리·끝 표시·대사 사이 낱말은 그대로)"""
    out = []; pos = 0; rebuild.offs = {}                            # 원래 대사 시작(바이트) → 새 시작(바이트)
    for m, nc in zip(msgs, newcodes):
        st = m['off'] // 2 + len(m['head'])
        out += words[pos:m['off'] // 2]; rebuild.offs[m['off']] = len(out) * 2
        out += words[m['off'] // 2:st]; out += nc; pos = st + len(m['codes'])
    out += words[pos:size // 2]
    assert len(out) <= size // 2, ('대본 넘침', len(out) * 2, size)
    out += [0xFFFF] * (size // 2 - len(out))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = {l.split('\t')[0]: l.split('\t') for l in open(os.path.join(ROOT, 'data', 'ko.tsv'), encoding='utf-8').read().splitlines()[1:]}
    out = os.path.join(ROOT, 'work', 'text'); os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, '*@*.bin')): os.remove(f)
    def put(name, off, data): open(os.path.join(out, '%s@%X.bin' % (name, off)), 'wb').write(data)
    t, _ = table()
    # ── 대사·엔딩
    ms = messages(); W = 12; WN = 18             # 대사 = 가장 좁은 창 13칸 − 1 · 서술 = 전체 화면 19칸(스샷 2026-11-23 실측) − 1
    toks = []
    for k, m in enumerate(ms):
        r = rows[str(k + 1)]; assert r[1] == 'TALKANM.BIN:%05X' % m['off'], (k, r[1])
        toks.append(wrap(tokens(prep(r[4])), W if len(m['head']) == 3 else WN))   # 서술(머리 2워드) = 전체 화면 19칸 → 18
    cmap, draw = assign(toks, t, 778, ())
    codes = [encode(tk, cmap) for tk in toks]
    T = open(os.path.join(ROOT, 'work', 'TALKANM.BIN'), 'rb').read(); words = list(struct.unpack('>%dH' % (len(T) // 2), T))
    new = rebuild(words, ms, codes, 0x106C4); blob = struct.pack('>%dH' % len(new), *new)
    used = sum(len(m['head']) + len(c) + 1 for m, c in zip(ms, codes))
    put('TALKANM.BIN', 0, blob)                                     # END1 사본은 아래 endsub.emit 이 자막 덩어리와 함께
    # ★이야기(캐릭터)별 시작 주소 표 15개 — VS.BIN 0x225A4(기준 0x002C0000, TALKANM) · END1.BIN 0x1C6AC(기준 0x06078398, END1 안 사본)
    #   대본 길이가 바뀌면 옛 주소가 대사 중간을 가리켜 크래시(실기 2026-11-23 하스피 스테이트) → 새 시작 위치로 고침
    V0 = open(os.path.join(ROOT, 'work', 'VS.BIN'), 'rb').read()
    for fn, at, base in (('VS.BIN', 0x225A4, 0x002C0000), ('END1.BIN', 0x1C6AC, 0x06078398)):
        src = V0 if fn == 'VS.BIN' else open(os.path.join(ROOT, 'work', 'END1.BIN'), 'rb').read()
        old = struct.unpack('>15I', src[at:at + 60]); new_t = []
        for x in old:
            assert x - base in rebuild.offs, ('이야기 시작이 대사 시작 아님', fn, hex(x))
            new_t.append(base + rebuild.offs[x - base])
        put(fn, at, struct.pack('>15I', *new_t))
        print('이야기 시작 표 %s@%X: %s' % (fn, at, ' '.join('%X' % (y - base) for y in new_t)))
    E = open(os.path.join(ROOT, 'work', 'END1.BIN'), 'rb').read()
    assert struct.unpack('>%dH' % (0x106C4 // 2), E[0x8398:0x8398 + 0x106C4])[-1] == words[0x106C4 // 2 - 1]
    for c, ch in sorted(draw.items()):
        g = pack(glyph(ch)); put('TALKCHR.BIN', 0x60 + (633 + c) * 128, g); put('END1CHR.BIN', c * 128, g)
    import endsub                                                    # 엔딩 그림 장면 음성 자막(2026-11-23)
    used_end = {c for m, nc in zip(ms, codes) if len(m['head']) != 3 for c in nc}   # 엔딩에서 찍히는 글자 = 서술(머리 2워드)
    put('END1.BIN', 0x8398, endsub.emit(put, E, rows, blob, used_end))
    print('대사: %d줄 · 글자 %d종 / 778(새로 그림 %d) · 대본 %d / %d 워드' % (len(ms), len(set(cmap.values())), len(draw), used + (len(words[:0x106C4 // 2]) - sum(len(m['head']) + len(m['codes']) + 1 for m in ms)), 0x106C4 // 2))
    # ── HOW TO PLAY
    how = json.load(open(os.path.join(ROOT, 'work', 'ocr_how', 'messages.json')))
    htab = {int(l.split('\t')[0]): l.split('\t')[1] for l in open(os.path.join(ROOT, 'data', 'how_charmap.tsv'), encoding='utf-8').read().splitlines()[2:] if '\t' in l}
    htok = [wrap(tokens(prep(rows['H%d' % (k + 1)][4])), 20, exact=True) for k in range(len(how))]
    for k, tk in enumerate(htok):                                   # HOW 창 = 20칸×3줄, 쪽 넘김 없음(실기 스샷 2026-11-23)
        n = 1; col = 0
        for x in tk:
            if x == ('g', NL): n += 1; col = 0
            else:
                col += 1
                if col == 20: col = 0; n += 1
        if col == 0: n -= 1
        assert n <= 3, ('HOW 3줄 넘침', 'H%d' % (k + 1), n)
    hc, hd = assign(htok, {c: ch for c, ch in htab.items() if ch}, 111, ())
    V = open(os.path.join(ROOT, 'work', 'VS.BIN'), 'rb').read()
    st, en = 0x2267C, 0x22A2C; vw = list(struct.unpack('>%dH' % ((en - st) // 2), V[st:en]))
    hm = []
    for m in how:                                                   # 첫 문장 머리 (0,0,4) 는 0x22678 부터 — 파싱이 0x2267C 에서 시작해 4 가 글자로 들어옴
        if not m['head'] and m['codes'][:1] == [4]: hm.append(dict(off=m['off'] - st, head=[4], codes=m['codes'][1:]))
        else: hm.append(dict(off=m['off'] - st, head=m['head'], codes=m['codes']))
    # 한글 HOW 대본은 원래 자리(944 B)보다 김 → HOWCHR.BIN 끝 섹터 남는 자리(0x6260‥0x6800)에 덧붙이고(VDP1 VRAM 0x36260 에 함께 실림,
    # HOW 화면에서 그 자리는 옛 TITCHR 찌꺼기 — s8 참조 0) 대본 포인터 리터럴 VS 0x06084064(원래 0x06092678) 를 0x25C36260 으로.
    hnew = rebuild(vw, hm, [encode(tk, hc) for tk in htok], 0x6800 - 0x6260 - 4)
    while hnew and hnew[-1] == 0xFFFF and hnew[-2] == 0xFFFF: hnew.pop()       # 끝 채움 걷어냄(마지막 문장 FFFF 하나는 둠)
    hblob = V[0x22678:0x2267C] + struct.pack('>%dH' % len(hnew), *hnew)
    assert len(hblob) <= 0x6800 - 0x6260
    put('HOWCHR.BIN', 0x6260, hblob)
    assert struct.unpack('>I', V[0x14064:0x14068])[0] == 0x06092678
    put('VS.BIN', 0x14064, struct.pack('>I', 0x25C36260))
    print('HOW 대본 %d B → HOWCHR.BIN 0x6260 (자리 %d B)' % (len(hblob), 0x6800 - 0x6260))
    H = open(os.path.join(ROOT, 'work', 'HOWCHR.BIN'), 'rb').read()
    for c, ch in sorted(hd.items()): put('HOWCHR.BIN', 0x2AE0 + c * 128, pack(glyph(ch)))
    print('HOW: %d줄 · 글자 %d종 / 111(새로 그림 %d)' % (len(how), len(set(hc.values())), len(hd)))
    # 확인용 줄 그림(대사 처음 몇 개 + HOW)
    json.dump(dict(cmap=cmap, hcmap=hc), open(os.path.join(ROOT, 'work', 'text_cmap.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return toks, htok


if __name__ == '__main__':
    main()
