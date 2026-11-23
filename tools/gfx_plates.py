# -*- coding: utf-8 -*-
r"""그림 글자 판 한글화(2026-11-23) — 압축 없는 *CHR.BIN·PLS2.BIN·STGSPR.A 안 4비트 스프라이트를 제자리 다시 그림
  판 = (파일, 위치, 폭, 높이, 한글, 바꿀 가로 범위 x0‥x1, 정렬, 채움 방식). 범위 밖(아이콘·영문·숫자)은 원본 그대로.
  자동 판정: 바탕 = 범위 가장자리 최빈색(투명 0 포함) · 글자 = 바탕 아닌 칸 · 외곽선색 = 바탕과 닿은 글자 칸 최빈 · 속색 = 안쪽 칸 최빈(또는 줄마다).
  글꼴: 높이 ≤8 → 갈무리7 · ≤16 → 갈무리11 Bold 12(넘치면 Condensed) · 그 위 → 나눔고딕 ExtraBold(원본 잉크 높이).
  출력 work/gfx/<파일>@<위치>.bin(판 바이트) · 미리보기 work/check/그림미리보기/<묶음>_원본_한글.png(스테이트 실제 색)
  python tools/gfx_plates.py [묶음 …]"""
import os, sys
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from iso import Disc
import vdp2render as V

G = r'C:/claude/utils/font/Galmuri-v2.40.3/'
F7, F9, F11, F11C = G + 'Galmuri7.ttf', G + 'Galmuri9.ttf', G + 'Galmuri11-Bold.ttf', G + 'Galmuri11-Condensed.ttf'
NEB = r'C:/claude/utils/font/nanum-gothic/NanumGothicExtraBold.ttf'
BHS = r'C:/claude/utils/font/blackhansans/BlackHanSans-Regular.ttf'
JUA = r'C:/claude/utils/font/jua/Jua-Regular.ttf'
BASE = {'NUKI.BIN': 0x4BD84, 'SRNK.BIN': 0xB7D0, 'TITCHR.BIN': 0x10000, 'PLSCHR.BIN': 0x30000, 'PLS2.BIN': 0x39F18, 'STGSPR.A': 0x4FFBC, 'HOWCHR.BIN': 0x30000, 'VSCHR.BIN': 0x50000}
NAMES = ['흰봄', '검은봄', '허니', '코테츠', '바그로', '12호', 'G.봄버', '페기JR', '라지봄', '푸이푸이', '마미', '레위시아', '덴타', '판프', '데라루']

# 묶음 → [(파일, 위치, 폭, 높이, 한글, x0, x1, 정렬, 채움)]  x1 = None 이면 폭 끝
JOBS = {
    '옵션': [   # ON/OFF·1/3/5 는 원래 자리 그대로(커서 위치가 고정 — sx 로 당기면 어긋남, 하스피 2026-11-23)
('TITCHR.BIN', 0x1EC80, 88, 8, '미니봄', 0, 32, 'l', 's'), ('TITCHR.BIN', 0x1EDE0, 96, 8, '셔플', 0, 40, 'l', 's'),
             ('TITCHR.BIN', 0x1EF60, 104, 8, '배틀 횟수', 0, 56, 'l', 's'), ('TITCHR.BIN', 0x1F100, 72, 8, '스테레오/모노', 0, None, 'l', 's'),
             ('TITCHR.BIN', 0x1F5E0, 32, 8, '스테레오', 0, None, 'l', 's'), ('TITCHR.BIN', 0x1F660, 32, 8, '모노', 0, None, 'l', 's'),
             ('TITCHR.BIN', 0x22BA0, 56, 8, '체력', 8, 50, 'l', 's'), ('TITCHR.BIN', 0x22C80, 56, 8, '완력', 8, 50, 'l', 's'),
             ('TITCHR.BIN', 0x22D60, 56, 8, '순발력', 8, 50, 'l', 's'), ('TITCHR.BIN', 0x22E40, 64, 8, '킥력', 16, 58, 'l', 's', dict(move=(0, 8, 8)))],   # 킥력: 64폭 판이 8px 왼쪽에 찍힘 → 별·글자를 8px 오른쪽으로(하스피 «킥력 줄맞춤»)
    '단추': [('TITCHR.BIN', 0x569A0, 64, 16, '선택', 26, None, 'l', 's'), ('TITCHR.BIN', 0x56BA0, 64, 16, '돌아가기', 26, None, 'l', 's', dict(font=(F11C, 12))),
             ('TITCHR.BIN', 0x56DA0, 80, 16, '등록', 26, None, 'l', 's'), ('TITCHR.BIN', 0x57020, 112, 16, '취소', 58, None, 'l', 's')],
    '안내문': [('TITCHR.BIN', 0x4D3A0, 176, 16, '덮어써도 될까요?', 0, None, 'l', 's'), ('TITCHR.BIN', 0x4D920, 160, 16, '이름을 정해 주세요!!', 0, None, 'l', 's'),
              ('TITCHR.BIN', 0x4DE20, 144, 16, '이대로 괜찮나요?', 0, None, 'l', 's'), ('TITCHR.BIN', 0x4EB20, 224, 16, '캐릭터를 정해 주세요!!', 0, None, 'l', 's'),
              ('TITCHR.BIN', 0x4F220, 192, 16, '파일을 골라 주세요!!', 0, None, 'l', 's')],
    '인원': [('PLSCHR.BIN', 0xE460, 64, 16, '2인 플레이!', 0, None, 'c', 's', dict(big=NEB, outline=15, split=(2, [11, 2, 2, 2], [8, 4, 4, 4]), shadow=1)), ('PLSCHR.BIN', 0xE660, 72, 16, '3인 플레이!', 0, None, 'c', 's', dict(big=NEB, outline=15, split=(2, [2], [8, 4, 4, 4]), shadow=1)),   # 3인 = 하늘색 단색(하스피)
             ('PLSCHR.BIN', 0xE8A0, 72, 16, '4인 플레이!!', 0, None, 'c', 's', dict(big=NEB, outline=15, split=(2, [11, 2, 2, 2], [8, 4, 4, 4]), shadow=1))],
    '대전설정': [('PLSCHR.BIN', 0x31BA0, 72, 24, '미니봄', 0, 64, 'l', 's', dict(font=(F11, 12))), ('PLSCHR.BIN', 0x31F00, 72, 16, '셔플', 0, 64, 'l', 's', dict(font=(F11, 12))),
              ('PLSCHR.BIN', 0x32140, 88, 24, '배틀 횟수', 0, 80, 'l', 's', dict(font=(F11, 12))), ('PLSCHR.BIN', 0x32B20, 40, 16, '1회', 0, None, 'l', 's', dict(font=(F11, 12))),
              ('PLSCHR.BIN', 0x32C60, 40, 16, '3회', 0, None, 'l', 's', dict(font=(F11, 12))), ('PLSCHR.BIN', 0x32DA0, 40, 16, '5회', 0, None, 'l', 's', dict(font=(F11, 12)))],
}
NAME_OFFS = {'PLS2.BIN': [(0x22108, 56), (0x223A8, 56), (0x22648, 56), (0x228E8, 56), (0x22B88, 72), (0x22EE8, 56), (0x23188, 88), (0x235A8, 72),
                          (0x23908, 72), (0x23C68, 88), (0x24088, 56), (0x24328, 88), (0x24748, 56), (0x249E8, 72), (0x24D48, 56)],
             'PLSCHR.BIN': [(0x3C600, 56), (0x3C8A0, 56), (0x3CB40, 56), (0x3CDE0, 56), (0x3D080, 72), (0x3D3E0, 56), (0x3D680, 88), (0x3DAA0, 72),
                            (0x3DE00, 72), (0x3E160, 88), (0x3E580, 56), (0x3E820, 88), (0x3EC40, 56), (0x3EEE0, 72), (0x3F240, 56)]}
JOBS['이름'] = [(f, o, w, 24, NAMES[k], 0, None, 'c', 'g', dict(italic=0.3, outline=1, grad=[15, 14, 13, 12, 11, 10, 9, 8])) for f, L in NAME_OFFS.items() for k, (o, w) in enumerate(L)]


def mask(t, fp, fs):
    im = Image.new('L', (400, 40), 0); ImageDraw.Draw(im).text((4, 4), t, font=ImageFont.truetype(fp, fs), fill=255)
    m = np.array(im) > 127; yy, xx = np.where(m); return m[yy.min():yy.max() + 1, xx.min():xx.max() + 1]


def big_mask(t, h, fp=None):
    for fs in range(40, 6, -1):
        im = Image.new('L', (800, 160), 0); ImageDraw.Draw(im).text((8, 8), t, font=ImageFont.truetype(fp or NEB, fs * 4), fill=255)
        a = np.array(im, np.float32) / 255; yy, xx = np.where(a > 0.1); a = a[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
        H = -(-a.shape[0] // 4) * 4; W = -(-a.shape[1] // 4) * 4
        m = np.pad(a, ((0, H - a.shape[0]), (0, W - a.shape[1]))).reshape(H // 4, 4, W // 4, 4).mean((1, 3)) >= 0.5
        yy, xx = np.where(m); m = m[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
        if m.shape[0] <= h: return m


def dil8(m):
    p = np.pad(m, 1); o = np.zeros_like(m)
    for dy in range(3):
        for dx in range(3): o |= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    return o


def draw(o, ko, x0, x1, align, fillmode, opt=None):
    opt = opt or {}
    h, w = o.shape; x1 = w if x1 is None else x1; reg = o[:, x0:x1]
    edge = np.concatenate([reg[0], reg[-1], reg[:, 0], reg[:, -1]]); bg = Counter(edge.tolist()).most_common(1)[0][0]
    T = np.isin(reg, list(opt['tc'])) if opt.get('tc') else reg != bg; ys, xs = np.where(T)
    if opt.get('tc'): bg = 0
    if not len(ys): return None
    inner = T & ~dil8(~T)[:, :] if False else T.copy()
    nb = np.zeros_like(T)
    p = np.pad(T, 1, constant_values=False)
    for dy, dx in ((0, 1), (2, 1), (1, 0), (1, 2)): nb |= ~p[dy:dy + h, dx:dx + reg.shape[1]]
    border = T & nb; core = T & ~nb
    oc = Counter(reg[border].tolist()).most_common(1)[0][0]
    fc = Counter(reg[core].tolist()).most_common(1)[0][0] if core.any() else oc
    outline = core.any() and oc != fc
    ih = ys.max() - ys.min() + 1                                     # 원본 글자 높이
    room_w = x1 - x0 - (2 if outline else 0); room_h = min(h, ih + 2) - (2 if outline else 0)
    if opt.get('font'): cands = [opt['font']]
    elif opt.get('big'): cands = None
    elif h <= 8: cands = [(F7, 8)]
    elif h <= 16: cands = [(F11, 12), (F11C, 12), (F9, 10), (F7, 8)]
    else: cands = None
    m = None
    if cands:
        for fp, fs in cands:
            mm = mask(ko, fp, fs)
            if mm.shape[1] <= room_w and mm.shape[0] <= max(room_h, mm.shape[0] if h <= 8 else 0): m = mm; break
    else:
        for hh in range(opt.get('fixh', room_h), 6, -1):
            mm = big_mask(ko, hh, opt.get('big'))
            if opt.get('italic'):                                     # 원본처럼 기울임(오른쪽 위로)
                k = opt['italic']; H0, W0 = mm.shape; sh = int(np.ceil(k * H0)); z = np.zeros((H0, W0 + sh), bool)
                for r in range(H0): d = int(round(k * (H0 - 1 - r))); z[r, d:d + W0] = mm[r]
                mm = z
            if opt.get('bold'): mm = np.pad(mm, ((0, 0), (0, 1))); mm[:, 1:] |= mm[:, :-1].copy()   # 가짜 굵게(오른쪽 1px)
            if mm.shape[1] <= room_w - (4 if opt.get('shadow') is not None or opt.get('outline') is not None else 0): m = mm; break
    if m is None: return 'TOO WIDE'
    out = o.copy(); R = out[:, x0:x1]; R[T] = bg
    H, W = m.shape; y = ys.min() + (ih - H) // 2 + (0 if not outline else 0); y = max(1 if outline else 0, min(y, h - H - (1 if outline else 0)))
    x = (1 if outline else 0) if align == 'l' else (x1 - x0 - W) // 2
    M = np.zeros(R.shape, bool); M[y:y + H, x:x + W] = m
    if opt.get('outline') is not None: oc = opt['outline']; outline = True
    if opt.get('shadow') is not None:                               # 아래 그림자(원본 이름판·인원판)
        Sd = np.zeros_like(M); Sd[1:] = dil8(M)[:-1]; R[Sd & ~dil8(M)] = opt['shadow']
    if opt.get('shadow11') is not None:                             # 오른쪽 아래 1px 그림자(스테이지 이름)
        Sd = np.zeros_like(M); Sd[1:, 1:] = M[:-1, :-1]; R[Sd & ~M] = opt['shadow11']
    if outline: R[dil8(M) & ~M] = oc
    if opt.get('sx') is not None:                                   # 원본 뒤 부분(영문·숫자)을 한글 바로 뒤로 당김
        sx = opt['sx']; suf = o[:, sx:]; cols = np.where((suf != bg).any(0))[0]
        if len(cols):
            suf = suf[:, cols[0]:]; nx = x0 + x + W + 2
            out[:, x0 + x + W + 1:] = bg
            ww = min(suf.shape[1], w - nx); out[:, nx:nx + ww] = suf[:, :ww]
    if opt.get('split'):                                            # 앞 글자(숫자+인)와 뒤 글자 색 따로(인원판: 앞 b/2, 뒤 8/4)
        na, ga, gb = opt['split']; fp = opt.get('big') or NEB
        wa = big_mask(ko[:na], H, fp).shape[1] if na else 0
        for r in range(y, y + H):
            g = ga if True else gb
            for c in range(x, x + W):
                if not M[r, c]: continue
                gl = ga if c - x < wa + 1 else gb; R[r, c] = gl[min(len(gl) - 1, (r - y) * len(gl) // max(1, H))]
    elif opt.get('grad'):                                           # 지정한 색 순서로 세로 그라데이션(위→아래)
        gl = opt['grad']
        for r in range(y, y + H): R[r][M[r]] = gl[min(len(gl) - 1, (r - y) * len(gl) // max(1, H))]
    elif fillmode == 'g':                                              # 줄마다 원본 글자 속색(세로 그라데이션)
        rows = {r: Counter(reg[r][core[r]].tolist()).most_common(1)[0][0] for r in range(h) if core[r].any()}
        ks = sorted(rows)
        for r in range(y, y + H):
            t = (r - y) / max(1, H - 1); src = ks[0] + t * (ks[-1] - ks[0]); R[r][M[r]] = rows[min(ks, key=lambda k: abs(k - src))]
    else: R[M] = opt.get('fill', fc)
    return out


def panel_player(o):
    """플레이어 정보 판(TITCHR 3BEA0 352×88, 바탕 = 16px 바둑판 8/9): 글자 칸 지우고 같은 줄 32px 주기 바탕 복사, 한글은 원본 색으로"""
    out = o.copy()
    def erase(x0, x1, y0, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if out[y, x] in (8, 9): continue
                for k in (32, -32, 64, -64, 96, -96):
                    if 0 <= x + k < 352 and o[y, x + k] in (8, 9): out[y, x] = o[y, x + k]; break
    def put(t, fp, fs, x0, x1, y0, y1, fill, shade=None):
        m = mask(t, fp, fs); H, W = m.shape; y = y0 + (y1 - y0 + 1 - H) // 2; x = x0 + (x1 - x0 + 1 - W) // 2
        M = np.zeros(out.shape, bool); M[y:y + H, x:x + W] = m; out[M] = fill
        if shade is not None:                                        # 원본처럼 획 아래쪽 한 줄 어둡게
            lo = M & ~np.roll(M, -1, 0); out[lo] = shade
    erase(112, 151, 3, 10); put('플레이어', F7, 8, 112, 151, 3, 10, 0xC)
    for y0 in (37, 53, 69):
        erase(128, 142, y0, y0 + 12); put('인', F11, 12, 128, 142, y0, y0 + 12, 3, 2)
        erase(145, 175, y0, y0 + 12); put('대전', F11, 12, 145, 175, y0, y0 + 12, 0xE, 0xD)
        for x0, t in ((217, '전'), (265, '승'), (313, '패')):
            erase(x0, x0 + 14, y0, y0 + 12); put(t, F11, 12, x0, x0 + 14, y0, y0 + 12, 0xF, 6)
    return out


JOBS['플레이어정보'] = [('TITCHR.BIN', 0x3BEA0, 352, 88, panel_player, 0, None, 'l', 's')]


def pad_labels(labels):
    """패드 그림(A/B-TYPE 72×56): 네 귀퉁이 방향 한자(속 e·그림자 1, 바탕 = 판 바탕색) → 좌·상·하·우 한 글자"""
    def fn(o):
        out = o.copy(); bgc = Counter(o[10:52, 20:50].ravel().tolist()).most_common(1)[0][0]
        for (y0, y1, x0, x1), t in zip(((11, 20, 3, 17), (11, 20, 54, 69), (40, 51, 3, 17), (40, 51, 54, 69)), labels):
            sub = out[y0:y1 + 1, x0:x1 + 1]; sub[np.isin(sub, (0xE, 1))] = bgc
            m = mask(t, F11, 12); H, W = m.shape; y = y0 + (y1 - y0 + 1 - H) // 2; x = x0 + (x1 - x0 + 1 - W) // 2
            M = np.zeros(out.shape, bool); M[y:y + H, x:x + W] = m
            Sd = np.zeros_like(M); Sd[1:, 1:] = M[:-1, :-1]; out[Sd & ~M] = 1; out[M] = 0xE
        return out
    return fn


STAGES = [(0x1A4A4, 120, '북쪽 나라에서', 16, 104), (0x1AA44, 80, '늘 하던 곳', 19, 80), (0x1AE04, 104, '전화의 궁전', 0, 104),
          (0x1B2E4, 176, '꽃밭에서 함께', 20, 166), (0x1BB24, 144, '자연을 소중히!', 0, 144), (0x1C1E4, 112, '이름 없는 옛 성', 0, 112),
          (0x1C724, 224, '잔티랜드에 어서 오세요', 0, 224), (0x1D1A4, 96, '황야의 공방', 0, 96), (0x1D624, 104, '부유성의 요새', 0, 104),
          (0x1DB04, 72, '결전!', 0, 72), (0x1DE64, 80, '보너스 1', 0, 80), (0x1E224, 88, '보너스 2', 0, 88), (0x1E644, 88, '보너스 3', 0, 88)]   # 決戦·おまけ = PLS.BIN 8464 표 위치(66CC 표는 0x20 어긋남)
JOBS['스테이지'] = [('STGSPR.A', o, w, 24, t, x0, x1, 'c', 's', dict(tc={15, 1}, big=JUA, fill=15, shadow11=1, fixh=15, bold=1)) for o, w, t, x0, x1 in STAGES]
JOBS['패드'] = [('TITCHR.BIN', 0x217E0, 72, 56, pad_labels('좌상하우'), 0, None, 'l', 's'), ('TITCHR.BIN', 0x21FC0, 72, 56, pad_labels('상우좌하'), 0, None, 'l', 's')]
JOBS['입력단추'] = [('TITCHR.BIN', o, 80, 24, t, 7, 74, 'c', 's', dict(y0=3, y1=20, font=(F11, 12))) for o, t in
                ((0x40DE0, '히라가나'), (0x411A0, '가타카나'), (0x41560, '로마자'), (0x41920, '히라가나'), (0x41CE0, '가타카나'), (0x420A0, '로마자'))]


def colr_of(states, f, off):
    va = BASE[f] + off
    best = None
    for r in states:
        if r[0] == va: return r[1], r[2]
        if best is None or abs(r[0] - va) < abs(best[0] - va): best = r
    return best[1], best[2]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    D = Disc(1); files = {}
    states = []
    for l in open(os.path.join(ROOT, 'work', 'states_map.tsv'), encoding='utf-8').read().splitlines()[1:]:
        r = l.split('\t'); states.append((int(r[1], 16), int(r[5], 16), r[0]))
    want = [a for a in sys.argv[1:]] or list(JOBS)
    os.makedirs(os.path.join(ROOT, 'work', 'gfx'), exist_ok=True)
    for grp in want:
        rows = []
        for job in JOBS[grp]:
            f, off, w, h, ko, x0, x1, al, fm = job[:9]; opt = job[9] if len(job) > 9 else None
            if f not in files: files[f] = D.read(f)
            a = np.frombuffer(files[f][off:off + w * h // 2], np.uint8); o = np.stack([a >> 4, a & 15], 1).ravel().reshape(h, w).astype(int)
            src = o
            if opt and 'move' in opt:                               # (원래 x0, x1, 옮길 x) — 판 안 아이콘(별) 옮기고 원래 자리는 투명
                a0, a1, d0 = opt['move']; src = o.copy(); src[:, d0:d0 + a1 - a0] = o[:, a0:a1]; src[:, a0:min(a1, d0)] = 0
            if callable(ko): new = ko(src)
            elif opt and 'y0' in opt:
                sub = draw(o[opt['y0']:opt['y1']], ko, x0, x1, al, fm, opt)
                new = sub if not isinstance(sub, np.ndarray) else np.vstack([o[:opt['y0']], sub, o[opt['y1']:]])
            else: new = draw(src, ko, x0, x1, al, fm, opt)
            if not isinstance(new, np.ndarray): print('⚠️', grp, f, hex(off), ko, new); continue
            fl = new.ravel(); open(os.path.join(ROOT, 'work', 'gfx', '%s@%X.bin' % (f, off)), 'wb').write(bytes(((fl[0::2] << 4) | fl[1::2]).astype(np.uint8)))
            col, st = colr_of(states, f, off); _, _, cram = V.load(st); cram = np.asarray(cram).astype(int)
            def rgb(ix):
                e = cram[((col & 0x7F0) + ix) & 0x7FF]; im = np.stack([(e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3], -1).astype(np.uint8); im[ix == 0] = (40, 40, 60); return im
            rows.append(np.concatenate([rgb(o), np.full((h, 4, 3), 120, np.uint8), rgb(new)], 1))
        if not rows: continue
        W = max(r.shape[1] for r in rows); S = np.full((sum(r.shape[0] + 4 for r in rows), W, 3), 25, np.uint8); y = 0
        for r in rows: S[y:y + r.shape[0], :r.shape[1]] = r; y += r.shape[0] + 4
        os.makedirs(os.path.join(ROOT, 'work', 'check', '그림미리보기'), exist_ok=True)
        Image.fromarray(S).resize((W * 3, S.shape[0] * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', 'check', '그림미리보기', '%s_원본_한글.png' % grp))
        print(grp, len(rows), '장')


if __name__ == '__main__':
    main()
