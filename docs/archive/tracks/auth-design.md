# auth-design: /candidates 인증 설계

---

## 컨텍스트

`/candidates` 엔드포인트는 사용자 호출로 확정되었다. 이 엔드포인트는 Spotify API를 직접 호출하고 SQS에 메시지를 enqueue하므로, 인증 없이 외부에 노출될 경우 Spotify rate limit 소진 및 SQS 비용이 발생한다.

현재 상태:
- `/candidates` (`app/api/routers/search.py` L47-66)에 인증 게이트 없음
- myblog_music은 FastAPI + Mangum(Lambda) 구성
- 회원 시스템 도입 여부 미결정

---

## 미결 질문

1. 회원 시스템을 도입할 것인가? 도입한다면 어떤 방식인가?

2. `/candidates`를 호출하는 주체는 누구인가? 일반 사용자인가, 특정 역할을 가진 사용자(예: 관리자)인가?

3. 인증 토큰을 발급하는 주체는 myblog_backend인가, 별도 인증 서비스인가?

4. myblog_music이 토큰을 직접 검증하는가, 아니면 myblog_backend로 검증 요청을 프록시하는가?

5. 인증 레이어를 Lambda 함수 내부(FastAPI Depends)에서 처리할 것인가, API Gateway 레벨에서 처리할 것인가?

6. myblog_front가 `/candidates`를 직접 호출하는 구조인가?

---

## Decision (2026-05-23)

Cognito JWT validation only for now. Larger architecture questions (user system, API Gateway authorizer, token proxy) deferred.

- `/candidates` validates a Cognito Bearer token via JWKS (RS256).
- `COGNITO_USER_POOL_ID` empty → auth bypassed in `local`/`dev`.
- `ENV=prod` with `COGNITO_USER_POOL_ID` set → full validation enforced.
- Caller: admin/owner only for now. General-user access deferred.

## 연관 PR

- PR-4: `/candidates` 인증 게이트 추가 ✅ Done (2026-05-23)
