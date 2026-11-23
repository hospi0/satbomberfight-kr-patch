# -*- coding: utf-8 -*-
r"""새턴 봄버맨 파이트!! 빌드(2026-11-23) — 압축 없는 그림 파일 안 판을 제자리 덮어쓰기 + 트랙 01 MODE1 EDC/ECC
  입력: work/gfx/<파일>@<위치 16진>.bin (tools/gfx_plates.py) — 판 바이트 그대로, 파일 크기 안.
  검사: 같은 파일 안 판끼리 겹침 없음 · 파일 크기 같음 · 바뀐 섹터가 바꾼 파일 안 · 되읽기 일치.
  python tools/build.py [--write] [--install]   ⛔--write·--install 은 하스피 허락 받고
"""
import glob, hashlib, os, shutil, struct, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from iso import Disc, ROMS
from cdrom_ecc import recalc_sector

F_DIR = r'F:\hospi\roms\ss roms\Saturn Bomberman Fight (Japan)'
OUT = os.path.join(ROOT, 'dist', 'build', 'Saturn Bomberman Fight (Japan)')


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''): h.update(c)
    return h.hexdigest()


def patches(D):
    """파일 안 덮어쓰기 + «마지막 섹터 남는 자리»까지 늘리기(늘면 디렉터리 크기도 고침, 2026-11-23 HOW 대본 → HOWCHR 끝)"""
    by = defaultdict(list)
    for fn in sorted(glob.glob(os.path.join(ROOT, 'work', 'gfx', '*@*.bin')) + glob.glob(os.path.join(ROOT, 'work', 'text', '*@*.bin'))):   # 그림 판 + 대본·글꼴(work/text)
        name, off = os.path.basename(fn)[:-4].split('@'); by[name].append((int(off, 16), open(fn, 'rb').read()))
    for fn in sorted(glob.glob(os.path.join(ROOT, 'work', 'kr', 'M0*.DAT'))):   # 동영상 자막(tools/moviesub.py 결과, 원래 크기로 0 채움) — work/text 는 build_text 가 비우므로 여기서 직접
        name = os.path.basename(fn)
        if not any(o == 0 for o, _ in by.get(name, [])): by[name].append((0, open(fn, 'rb').read()))
    jobs = []
    for name, L in by.items():
        lba, size = next((l, s) for p, l, s in D.files if p == '/' + name)
        cap = (size + 2047) // 2048 * 2048
        orig = D.sec(lba, cap // 2048); new = bytearray(orig); L.sort()
        for (o1, d1), (o2, d2) in zip(L, L[1:]): assert o1 + len(d1) <= o2, ('판 겹침', name, hex(o1), hex(o2))
        end = size
        for o, d in L:
            assert o + len(d) <= cap, ('섹터 밖', name, hex(o)); new[o:o + len(d)] = d; end = max(end, o + len(d))
        if end > size: assert not any(orig[size:cap]), ('남는 자리가 0 아님', name)
        jobs.append((name, lba, cap, bytes(orig), bytes(new), size, end))
        print('  %-12s 판 %d장 · 바뀐 바이트 %d%s' % (name, len(L), sum(a != b for a, b in zip(orig, new)), '' if end == size else ' · 크기 %X→%X' % (size, end)))
    return jobs


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    D = Disc(1); jobs = patches(D)
    if '--write' not in sys.argv: print('계획만'); return
    os.makedirs(OUT, exist_ok=True)
    src_dir = os.path.dirname(ROMS[1]); t1 = os.path.join(OUT, os.path.basename(ROMS[1]))
    shutil.copyfile(ROMS[1], t1)
    for f in os.listdir(src_dir):
        q = os.path.join(src_dir, f)
        if os.path.isfile(q) and f != os.path.basename(ROMS[1]) and not os.path.exists(os.path.join(OUT, f)): shutil.copyfile(q, os.path.join(OUT, f))
    dirty = set()
    with open(t1, 'r+b') as fh:
        for name, lba, size, orig, new, fsize, end in jobs:
            if end != fsize:                                        # 디렉터리 레코드 크기(LE +10, BE +14)
                rl, ro = D.record(name); fh.seek(rl * 2352); sec = bytearray(fh.read(2352))
                assert struct.unpack_from('<I', sec, 16 + ro + 10)[0] == fsize
                struct.pack_into('<I', sec, 16 + ro + 10, end); struct.pack_into('>I', sec, 16 + ro + 14, end)
                fh.seek(rl * 2352); fh.write(recalc_sector(bytes(sec))); dirty.add(rl)
            for i in range(0, size, 2048):
                if orig[i:i + 2048] == new[i:i + 2048]: continue
                s = lba + i // 2048
                fh.seek(s * 2352); sec = bytearray(fh.read(2352)); assert sec[15] == 1, ('MODE1 아님', name, s)
                chunk = new[i:i + 2048]; sec[16:16 + len(chunk)] = chunk
                fh.seek(s * 2352); fh.write(recalc_sector(bytes(sec))); dirty.add(s)
    N = Disc.__new__(Disc); N.n = 1; N.f = open(t1, 'rb'); N.files = D.files
    for name, lba, size, orig, new, fsize, end in jobs: assert N.sec(lba, size // 2048) == new, ('되읽기 다름', name)
    a = open(ROMS[1], 'rb'); b = open(t1, 'rb'); bad = []
    for s in range(os.path.getsize(t1) // 2352):
        if a.read(2352) != b.read(2352) and s not in dirty: bad.append(s)
    assert not bad, ('바꾼 파일 밖 섹터가 바뀜', bad[:5])
    print('  검산 통과 · 바뀐 섹터 %d · 트랙 01 md5 %s' % (len(dirty), md5(t1)))
    if '--install' in sys.argv:
        dst = os.path.join(F_DIR, os.path.basename(ROMS[1])); assert os.path.exists(dst), dst
        shutil.copyfile(t1, dst); assert md5(dst) == md5(t1)
        print('  F: 설치(원래 폴더 트랙 01 덮어씀)', dst)


if __name__ == '__main__':
    main()
