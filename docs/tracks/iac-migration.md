# iac-migration: IaC(Terraform) 전환

---

## 컨텍스트

현재 myblog 시스템의 인프라 현황:
- myblog_music은 GitHub Actions(`deploy.yml`) push 기반으로 Lambda에 직접 배포
- 인프라 리소스(Lambda, API Gateway, RDS, SQS 등)가 IaC로 선언되어 있지 않음
- CI에 테스트 단계 없음 — PR-5에서 단위 테스트 gate 추가 예정

PR-5(단위 테스트 CI gate)는 현재 deploy.yml 내에서 처리되며, 이후 IaC 전환 시 구조가 달라질 수 있다.

---

## 미결 질문

1. IaC 도구를 Terraform으로 확정할 것인가? 다른 도구(CDK, Pulumi 등)와 비교 검토가 필요한가?

2. 전환 범위는 어디까지인가? myblog_music만 먼저 전환하는가, 전체 서비스를 동시에 전환하는가?

3. 기존 수동 생성된 리소스를 `terraform import`로 흡수할 것인가, 새 리소스로 재생성할 것인가?

4. Terraform state를 어디에 저장할 것인가? (S3 backend, Terraform Cloud 등)

5. PR-5에서 구성하는 CI 게이트가 IaC 전환 이후에도 동일 구조로 유지 가능한가, 아니면 재작성이 필요한가?

6. 각 레포(myblog_backend, myblog_front, myblog_music, myblog_publish, myblog_worker)가 각자의 IaC를 관리하는가, 아니면 중앙 인프라 레포를 별도로 두는가?

---

## 연관 작업

- PR-5 (`myblog_music` CI 단위 테스트 gate): IaC 전환 이전에 진행. 단, 전환 시 deploy.yml 구조 변경이 수반될 수 있으므로 PR-5 작업 시 이 점을 고려해 확장 가능하게 작성한다.
