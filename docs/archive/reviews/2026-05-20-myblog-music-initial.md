# myblog_music 초기 리뷰 — 2026-05-20

리뷰어: planner agent (코드 직접 분석)
대상 레포: myblog_music
커밋 기준: main (최신, 스키마 수정 및 split search 구현 이후)

---

## 요약

핵심 설계(DB-first 검색 / 비동기 SQS enqueue) 방향은 올바르다.
그러나 프로덕션 투입 전 반드시 처리해야 할 정확성 버그와 디버그 코드 잔재가 존재한다.

---

## 발견 항목

### [BUG-1] schema.sql 문법 오류 — artists 테이블 괄호 중복
- 위치: `db/schema.sql` 라인 90~91
- 내용: `CONSTRAINT chk_artists_views_nonneg ...` 뒤에 `)` 가 한 줄 더 있어 `);\n);` 형태로 DDL 실행 시 오류 발생
- 심각도: 높음 (신규 환경 DB 초기화 불가)

### [BUG-2] album_service.py — 미임포트 심벌 사용
- 위치: `app/services/album_service.py` 라인 29~30
- 내용: `get_primary_artist_map` 메서드 내에서 `AlbumArtist`, `Artist`, `select`를 사용하나 파일 상단에 임포트 없음. 해당 메서드 호출 시 `NameError` 발생
- 심각도: 높음 (런타임 오류)

### [BUG-3] Track 모델 — spotify_id UNIQUE 제약 누락
- 위치: `app/domain/models.py` 라인 197
- 내용: `Track.spotify_id`가 `unique=True` 없이 선언됨. schema.sql에는 `UNIQUE` 있음. Worker의 upsert가 `spotify_id` 기준으로 동작하므로 모델-스키마 불일치가 잠재적 중복 삽입 위험을 만듦
- 심각도: 중간 (데이터 정합성)

### [DEBT-1] 프로덕션 print 남용
- 위치: `app/repositories/album_repo.py` (get_existing_spotify_ids), `app/clients/sqs_client.py`, `app/services/cadidate_search_service.py`
- 내용: 디버그용 `print` 문이 프로덕션 코드 경로에 다수 존재. CloudWatch 비용 증가 및 시크릿 노출 위험 (SQS URL, album_ids 등이 로그에 출력됨)
- 심각도: 중간

### [DEBT-2] album_repo.py — 클래스 본문 내 import 문
- 위치: `app/repositories/album_repo.py` 라인 128~129
- 내용: `import time`, `from typing import Iterable, List, Set` 가 클래스 메서드 사이에 삽입됨. 파일 상단에 이미 일부 임포트 존재. 실행은 되나 Python 관례 위반으로 가독성 저해
- 심각도: 낮음

### [DEBT-3] cadidate_search_service.py — 파일명 오타
- 위치: `app/services/cadidate_search_service.py`
- 내용: `candidate` → `cadidate` 오타. 라우터, 서비스 파일명 모두 동일 오타 적용되어 동작은 하나, 장기적으로 혼란 유발
- 심각도: 낮음

### [DEBT-4] get_existing_spotify_ids — 과도한 타이밍/디버그 로직
- 위치: `app/repositories/album_repo.py` 라인 131~170
- 내용: `time.perf_counter`, `conn = self.db.connection()` (커넥션 강제 획득), 대규모 print 블록이 정상 경로에 포함. 프로덕션 Lambda에서 매 요청마다 실행됨
- 심각도: 중간

### [DESIGN-1] /candidates 엔드포인트 — 인증 없음
- 위치: `app/api/routers/search.py` 라인 47~66
- 내용: Spotify API를 직접 호출하고 SQS에 메시지를 넣는 `/candidates` 엔드포인트에 인증이 없음. 외부에서 반복 호출 시 Spotify rate limit 소진 및 SQS 비용 발생 가능
- 심각도: 높음 (보안)

### [DESIGN-2] SingleFlight — 실제 사용처 없음
- 위치: `app/core/singleflight.py`
- 내용: SingleFlight 구현체가 있으나 어떤 서비스/핸들러에서도 사용되지 않음. Lambda는 단일 스레드 환경이므로 효과 없음. 데드 코드 또는 미완성 구현
- 심각도: 낮음

### [DESIGN-3] SpotifyClient — 모듈 레벨 싱글턴 + Lambda cold start
- 위치: `app/clients/spotify_client.py` 라인 120 (`spotify = SpotifyClient()`)
- 내용: 모듈 레벨에서 싱글턴 생성. Lambda warm 재사용 시 토큰이 유지되는 것은 의도적이나, cold start에서 토큰을 즉시 요청하지는 않아 첫 실제 요청 지연이 발생함. 현재 구조는 허용 가능하나 문서화 필요
- 심각도: 낮음 (정보)

### [INFRA-1] deploy.yml — CI 테스트 단계 없음
- 위치: `.github/workflows/deploy.yml`
- 내용: push → 즉시 Lambda 배포. 테스트 실행 단계가 없어 BUG-2와 같은 NameError가 배포 후에야 발견됨
- 심각도: 중간
