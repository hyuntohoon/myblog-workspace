# ADR-0002: PR-5, PR-6 보류

날짜: 2026-05-22
상태: Paused

## 배경

PR-5(CI 단위 테스트 게이트)와 PR-6(Track spotify_id UNIQUE 마이그레이션)은 `docs/plan.md`에 계획된 후속 작업이다.

- **PR-5**: CI gate 구조(`deploy.yml` + `requirements-test.txt` + `pytest.ini`)는 브랜치 `ci/PR-5-test-gate`에 작성 완료됐으나, 실제로 gate에 걸릴 단위 테스트가 아직 0개다. 게이트 구조만 있고 검증할 테스트가 없는 상태로 머지하는 것은 실질적 가치가 낮다.
- **PR-6**: `CREATE UNIQUE INDEX CONCURRENTLY`를 실행하려면 기존 DB의 중복 `spotify_id` 데이터를 먼저 정리해야 하고, Jack의 명시적 승인이 필요하다. 현재 프로덕션 DB 접근 및 검토 일정이 확정되지 않은 상태다.

## 결정

두 PR 모두 **설계/검증 작업이 완료될 때까지 보류**한다.

- PR-5는 단위 테스트가 최소 1개 이상 작성된 이후 재개한다. 테스트 작성은 별도 작업으로 분리한다.
- PR-6은 DB 중복 데이터 확인 및 Jack 승인 이후 재개한다.

현재 작업 우선순위: 시스템 전체 설계 검증(architect 작업) → 이후 PR-5, PR-6 재평가.

## 영향

- `docs/plan.md`의 PR-5, PR-6 섹션에 ⏸️ 보류 표시 추가.
- `ci/PR-5-test-gate` 브랜치는 유지하되 머지하지 않음.
- 보류 해제 조건이 충족되면 이 ADR의 상태를 `Accepted` 또는 `Superseded`로 갱신한다.
