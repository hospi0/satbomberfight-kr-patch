# 새턴 봄버맨 파이트!! (세가 새턴 일본판) 한글 패치

- 원본: `Saturn Bomberman Fight!! (Japan)` (17트랙, 트랙 01 에만 패치, 트랙 02부터 17까지와 cue 는 그대로)
- 배포 파일은 릴리즈의 zip(xdelta + 적용 bat + readme)을 쓰세요.
- 대사·엔딩·HOW TO PLAY: `data/ko.tsv` → `tools/build_text.py`(대본·글꼴)
- 그림 글자: `tools/gfx_plates.py` · `tools/gfx_result.py`
- 동영상 자막: `tools/moviesub.py`(`data/movie_subs.tsv`)
- 엔딩 그림 장면 음성 자막(원본에는 자막 없음): `tools/endsub.py`
- 빌드 `tools/build.py` → 배포 `tools/make_dist.py`
- 조사·결정 기록: `docs/00_초기조사.md`
