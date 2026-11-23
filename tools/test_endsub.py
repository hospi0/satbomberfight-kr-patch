# -*- coding: utf-8 -*-
r"""엔딩 음성 자막 흉내기 검산(2026-11-23) — 하스피 스테이트(work/mem/voice, 덴타 그림 장면)에 새 END1 을 얹고
  실제 게임 코드(객체 할당·초기화·지우기 0x06007410)까지 sh2sim 으로 돌림. 음성 10개 전부: play → 상태 0→3 → 쪽마다 글자 객체 → 상태 −1 → 다 지움.
  python -X utf8 tools/test_endsub.py"""
import os, struct, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sh2sim as S, endsub

rd = lambda p: open(os.path.join(ROOT, *p.split('/')), 'rb').read()


def main():
    ram = bytearray(rd('work/mem/voice/WorkRAMH.bin')); e = bytearray(rd('work/END1.BIN'))
    chr_ = bytearray(rd('work/END1CHR.BIN'))
    for f in os.listdir(os.path.join(ROOT, 'work', 'text')):
        n, o = f[:-4].split('@'); o = int(o, 16); d = rd('work/text/' + f)
        if n == 'END1.BIN': e[o:o + len(d)] = d
        if n == 'END1CHR.BIN': chr_[o:o + len(d)] = d
    ram[0x70000:0x70000 + len(e)] = e
    m = S.Mem(); m.map(0x06000000, ram); B = m.regions[0][1]
    g32 = lambda a: struct.unpack_from('>I', B, a - 0x06000000)[0]
    play, tick = g32(0x0607251C), g32(0x0608BB44)
    r0 = list(range(0x100, 0x110)); calls = []
    def call(pc, regs):
        c = S.CPU(m, pc, dict([(i, 0x1111 * i) for i in range(8, 15)] + list(enumerate(regs))), 0x060FE000)
        c.pr = 0x0DEAD000; keep = {i: c.r[i] for i in range(8, 15)}
        while c.pc != 0x0DEAD000:
            if c.pc in (0x06009498, 0x06070500):
                calls.append((c.pc, c.r[4], c.r[5], c.r[6])); c.pc = c.pr; continue
            c.step()
        assert c.r[15] == 0x060FE000, hex(c.r[15]); assert all(c.r[i] == v for i, v in keep.items()), '보존 레지스터'
    OBJ, WK = 0x0604A8E0, 0x0603C500
    def objs():
        out = []
        for i in range(0x1DD, 0x23D):
            a = OBJ + i * 0x4C
            if m.r8(a + 8) == 0: out.append((i, a, WK + i * 32))
        return out
    VARS = endsub.BASE; tot = 0; shots = {}
    rows = {l.split('\t')[0]: l.split('\t') for l in open(os.path.join(ROOT, 'data', 'ko.tsv'), encoding='utf-8').read().splitlines()[1:]}
    import json
    vb = 0xFF00                                                      # 카운터 넘침도 지나가게
    for folder, num, k, pages in endsub.SUBS:
        m.w32(0x060360C4, 0); calls.clear()
        call(play, [0, 0, 0, 0, num, folder, 2]); assert calls == [(0x06009498, num, folder, 2)], calls
        seen = []; last = None; t0 = None; dur = int((pages[-1][0] + 2) * 60)
        for f in range(40 + dur + 20):
            st = 0 if f < 30 else 3 if f < 30 + dur else 0xFFFFFFFF
            m.w32(0x060360C4, st); m.w16(0x060FFC22, (vb + f) & 0xFFFF); calls.clear()
            call(tick, [0, 0, 0, 0, 0x15D, OBJ + 0x15D * 0x4C, WK + 0x15D * 32])
            assert calls == [(0x06070500, 0x15D, OBJ + 0x15D * 0x4C, WK + 0x15D * 32)]
            for i, a, w in objs():                                   # 06007A88 의 순서: 지움 표시면 지우기, 아니면 매 프레임 함수
                if m.r16(a + 2) & 0x8000: call(0x06007410, [0, 0, 0, 0, i])
                else: call(m.r32(a + 0x48), [0, 0, 0, 0, i, a, w])
            vis = [(i, m.r16(a + 14), m.r32(a + 36), m.r32(a + 40), m.r32(a + 44)) for i, a, w in objs() if m.r8(a + 9) == 3]
            key = tuple(v[1:] for v in vis)
            if key != last: seen.append((f, key)); last = key
        assert not objs(), ('남은 객체', len(objs()))
        shown = [(f, x) for f, x in seen if x]
        assert len(shown) == len(pages), (k, len(shown), len(pages), [f for f, _ in seen])
        for (f, x), (t, ls) in zip(shown, pages):
            assert f == 30 + round(t * 60), (k, f, t)
            assert len(x) == sum(len(l.replace(' ', '')) for l in ls); tot += 1
            shots.setdefault((k, t), x)
        vb += 5000
    print('검산 통과: 음성 %d · 쪽 %d — 시각·글자 수·지움·레지스터 보존·원래 함수 인자' % (len(endsub.SUBS), tot))
    # 미리보기: 덴타 그림 위에 글자(실제 VRAM 그림·팔레트 7E0)
    cram = rd('work/mem/voice/CRAM.bin'); pal = [struct.unpack_from('<H', cram, (0x7E0 + i) * 2)[0] for i in range(16)]
    rgb = [((p & 31) << 3, (p >> 5 & 31) << 3, (p >> 10 & 31) << 3) for p in pal]
    bg = Image.open(os.path.join(ROOT, 'work', 'v2_voice_nbg0.png')).convert('RGB').crop((0, 0, 352, 224))
    S2 = np.frombuffer(bytes(chr_), np.uint8); ims = []
    for (k, t), x in shots.items():
        im = bg.copy(); px = im.load()
        for code, xx, yy, z in x:
            sx = S._s32(xx) // 65536 + 176; sy = S._s32(yy) // 65536 + 112
            d = chr_[code * 128:code * 128 + 128]
            for j in range(256):
                v = d[j // 2] >> 4 if j % 2 == 0 else d[j // 2] & 15
                if v and 0 <= sx + j % 16 < 352 and 0 <= sy + j // 16 < 224: px[sx + j % 16, sy + j // 16] = rgb[v]
        ims.append(im.crop((0, 160, 352, 224)))
    W = Image.new('RGB', (352 * 2 + 4, (len(ims) + 1) // 2 * 68), (80, 80, 80))
    for i, im in enumerate(ims): W.paste(im, ((i % 2) * 356, i // 2 * 68))
    p = os.path.join(ROOT, 'work', 'check', '그림미리보기', '엔딩음성자막_글자판.png'); W.resize((W.width * 2, W.height * 2), Image.NEAREST).save(p); print(p)


if __name__ == '__main__':
    main()
