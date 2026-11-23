# -*- coding: utf-8 -*-
r"""새턴 봄버맨 그림 압축 — 파이썬 풀기(0KRNL 0x0603EA08 이식, 2026-11-22)
  자료 = [u16 풀린 바이트 수 n][u16 방식(5 = 무압축)][압축 자료 …] — decode() 는 «압축 자료» 부분을 받는다.
  압축 자료:
    b0 = 코드 비트 수(0 이면 이후 n 바이트를 그대로 복사)
    b1 = 형식: 단위 = 1(b1 0·1) / 2(2·3) / 4(4) 바이트, 이력 마스크 = [0x1FF,0xFF,0xFF,0x7F,0x7F][b1], b1 홀수 = 두 이력 번갈아(짝·홀 단위)
    그 뒤 (1<<b0)−1 바이트 = 코드 1‥ 에 붙일 예측기 번호(코드 0 = 예측기 0 = 새 값 읽기)
    본문: 단위마다 코드(b0 비트, 1·2·4비트 = 한 바이트에서 아래 비트부터, 3비트 = 세 바이트의 같은 자리 비트 묶음)를 읽고
          예측기로 값을 정해 출력·이력에 넣는다. 코드용 바이트와 새 값 바이트는 같은 흐름에서 필요할 때마다 읽는다.
  예측기: 0 새 값(단위 크기, 빅 엔디언) · 1 직전 · 2‥7 직전+1,2,4,8,16,32 · 8‥13 직전−1,2,4,8,16,32 · 14‥19 2,4,8,16,32,64 단위 앞 값
"""
MASKS = [0x1FF, 0xFF, 0xFF, 0x7F, 0x7F]
ADD = {2: 1, 3: 2, 4: 4, 5: 8, 6: 16, 7: 32, 8: -1, 9: -2, 10: -4, 11: -8, 12: -16, 13: -32}
BACK = {14: 2, 15: 4, 16: 8, 17: 16, 18: 32, 19: 64}


def unit_of(b1):
    return 1 if b1 < 2 else 2 if b1 < 4 else 4


def decode(src, n):
    """src = 압축 자료(bytes), n = 풀린 바이트 수 → (bytes, 읽은 바이트 수)"""
    p = 0
    b0 = src[p]; p += 1
    if b0 == 0:
        return bytes(src[p:p + n]), p + n
    b1 = src[p]; p += 1
    u = unit_of(b1); mask = MASKS[b1]; full = (1 << (8 * u)) - 1
    pred = [0] + [src[p + i] for i in range((1 << b0) - 1)]; p += (1 << b0) - 1
    hist = [[0] * (mask + 1), [0] * (mask + 1)]; idx = [0, 0]
    bits = [0, 0, 0]; cnt = 0
    out = bytearray()
    units = (n + u - 1) // u
    for k in range(units):
        h = (k & 1) if b1 & 1 else 0
        H = hist[h]; i = idx[h]
        # 코드 읽기
        if b0 == 3:
            if cnt == 0:
                bits = [src[p], src[p + 1], src[p + 2]]; p += 3
            code = ((bits[2] & 1) << 2) | ((bits[1] & 1) << 1) | (bits[0] & 1)
            bits = [b >> 1 for b in bits]; cnt = (cnt + 1) & 7
        else:
            if cnt == 0:
                bits[0] = src[p]; p += 1
            code = bits[0] & ((1 << b0) - 1); bits[0] >>= b0; cnt = (cnt + b0) & 7
        f = pred[code]
        prev = H[(i - 1) & mask]
        if f == 0:
            v = int.from_bytes(src[p:p + u], 'big'); p += u
        elif f == 1:
            v = prev
        elif f in ADD:
            v = (prev + ADD[f]) & full
        elif f in BACK:
            v = H[(i - BACK[f]) & mask]
        else:
            raise ValueError('예측기 %d' % f)
        out += v.to_bytes(u, 'big')
        H[i] = v; idx[h] = (i + 1) & mask
    return bytes(out[:n]), p


def decode_blob(blob):
    """[u16 n][u16 방식][자료] → bytes"""
    n = int.from_bytes(blob[0:2], 'big'); ty = int.from_bytes(blob[2:4], 'big')
    if ty == 5:
        return bytes(blob[4:4 + n])
    return decode(blob[4:], n)[0]


def _cands(H, i, mask, v, full):
    """이 값을 만드는 예측기 번호들"""
    prev = H[(i - 1) & mask]; s = set()
    if v == prev: s.add(1)
    for f, d in ADD.items():
        if (prev + d) & full == v: s.add(f)
    for f, d in BACK.items():
        if H[(i - d) & mask] == v: s.add(f)
    return s


def _encode_raw(data, b1=0):
    """data → 압축 자료(bytes). b1 = 형식(원본과 같게 주는 것이 안전). 가장 작은 b0·예측기 묶음 선택, 무압축(b0=0)도 후보."""
    u = unit_of(b1); mask = MASKS[b1]; full = (1 << (8 * u)) - 1
    vals = [int.from_bytes(data[k:k + u].ljust(u, b'\0'), 'big') for k in range(0, len(data), u)]
    # 이력은 값에 따라 정해지므로(예측기 선택과 무관) 후보 집합을 미리 계산
    hist = [[0] * (mask + 1), [0] * (mask + 1)]; idx = [0, 0]; C = []
    for k, v in enumerate(vals):
        h = (k & 1) if b1 & 1 else 0
        C.append(_cands(hist[h], idx[h], mask, v, full))
        hist[h][idx[h]] = v; idx[h] = (idx[h] + 1) & mask
    best = bytes([0]) + bytes(data)
    for b0 in (1, 2, 3, 4):
        k = (1 << b0) - 1
        chosen = []
        for _ in range(k):                                  # 덜 덮인 단위를 가장 많이 덮는 예측기부터
            cov = {}
            for s in C:
                if s & set(chosen): continue
                for f in s: cov[f] = cov.get(f, 0) + 1
            if not cov: break
            chosen.append(max(cov, key=lambda f: (cov[f], -f)))
        while len(chosen) < k: chosen.append(1)
        # 지역 탐색: 한 자리씩 다른 예측기로 바꿔 «새 값이 필요한 단위 수»가 줄면 채택(2026-11-22, 한글 단추가 원래 자리를 9 B 넘어서)
        def miss(ch):
            st = set(ch); return sum(1 for c in C if not (c & st))
        cur = miss(chosen); better = True
        while better:
            better = False
            for j in range(len(chosen)):
                for f in range(1, 20):
                    if f in chosen: continue
                    t = chosen[:j] + [f] + chosen[j + 1:]; m_ = miss(t)
                    if m_ < cur: chosen, cur, better = t, m_, True
        code_of = {f: j + 1 for j, f in enumerate(chosen)}
        out = bytearray([b0, b1]) + bytes(chosen)
        cnt = 0; acc = [0, 0, 0]; slot = None
        body = bytearray()
        for kk, v in enumerate(vals):
            m = [code_of[f] for f in C[kk] if f in code_of]
            code = min(m) if m else 0
            if cnt == 0:                                    # 새 코드 바이트(들) 자리 확보 — 풀기 순서와 같게
                slot = len(body); body += bytes(3 if b0 == 3 else 1); acc = [0, 0, 0]
            if b0 == 3:
                for t in range(3): acc[t] |= ((code >> t) & 1) << cnt
                body[slot:slot + 3] = bytes(acc); cnt = (cnt + 1) & 7
            else:
                acc[0] |= code << cnt; body[slot] = acc[0]; cnt = (cnt + b0) & 7
            if code == 0:
                body += v.to_bytes(u, 'big')
        out += body
        if len(out) < len(best):
            best = bytes(out)
    dec, used = decode(best, len(data))
    assert dec == bytes(data), '압축 되풀기 불일치'
    return best


# ── 압축 결과 디스크 캐시(2026-11-22 하스피 «할 때마다 다시?») — 같은 (그림 바이트, b1) 은 한 번만 압축 ──
import hashlib as _hl, os as _os, pickle as _pk
_CACHE_P = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'work', 'bcomp_cache.pkl')
try: _CACHE = _pk.load(open(_CACHE_P, 'rb'))
except Exception: _CACHE = {}
_DIRTY = [0]


def encode(data, b1=0):
    k = (_hl.md5(bytes(data)).hexdigest(), b1)
    r = _CACHE.get(k)
    if r is None:
        r = _CACHE[k] = _encode_raw(data, b1); _DIRTY[0] += 1
        if _DIRTY[0] % 50 == 0: _save()
    return r


def _save():
    tmp = _CACHE_P + '.tmp'
    with open(tmp, 'wb') as f: _pk.dump(_CACHE, f)
    _os.replace(tmp, _CACHE_P)


import atexit as _ae
_ae.register(lambda: _DIRTY[0] and _save())
