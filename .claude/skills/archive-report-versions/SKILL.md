---
name: archive-report-versions
description: R-reports 폴더에서 이전 버전 보고서를 자동으로 아카이빙하는 스킬. suffix 번호가 높을수록 최신 버전으로 인식하며, 이전 버전 파일을 4_Archive/Resources/R-reports/로 이동한다. 프론트매터에 아카이빙 정보(archived, archived_date, archived_reason, original_path)를 자동 추가한다.
---

# archive-report-versions

*버전: v1.0*
*최종 업데이트: 2026-01-16*

## 개요

R-reports 폴더의 이전 버전 보고서를 자동으로 아카이빙하는 스킬.
파일명에서 버전 정보를 감지하여 최신 버전만 남기고 이전 버전은 Archive로 이동한다.

## 버전 규칙

> **CRITICAL**: suffix 번호가 높을수록 최신 버전이다.

```
버전 순서: _v3.0 > _v2.5 > _v1 > suffix 없음

예시:
  20260114_IBK_분석_v2.5.md  → 최신 (유지)
  20260114_IBK_분석_v1.md    → 이전 버전 (아카이브)
  20260114_IBK_분석.md       → 초기 버전 (아카이브)
```

| 파일명 패턴 | 의미 | 처리 |
|------------|------|------|
| `YYYYMMDD_제목_v{N}.md` | 버전 N | 가장 높은 N만 유지 |
| `YYYYMMDD_제목.md` | 초기 버전 (v0) | 다른 버전 있으면 아카이브 |

## 사용법

### 자동 실행 (권장)
새 보고서를 R-reports에 저장하면 자동으로 이전 버전 감지 및 아카이빙 제안.

### 수동 실행
```bash
# 전체 스캔 및 아카이빙
python .claude/skills/archive-report-versions/scripts/archive_report_versions.py

# 미리보기 (실제 이동 없이 대상 확인)
python .claude/skills/archive-report-versions/scripts/archive_report_versions.py --dry-run

# 특정 파일만 처리
python .claude/skills/archive-report-versions/scripts/archive_report_versions.py --file "20260114_IBK_임금수준_적정성_분석.md"

# 상세 로그 출력
python .claude/skills/archive-report-versions/scripts/archive_report_versions.py --verbose
```

## 아카이빙 프로세스

1. **스캔**: R-reports 폴더의 모든 .md 파일 스캔
2. **그룹화**: (날짜, 제목) 기준으로 버전 그룹화
3. **비교**: suffix 버전 번호 비교 (suffix 없음 = v0)
4. **감지**: 가장 높은 버전 외 나머지 = 이전 버전
5. **이동**: `4_Archive/Resources/R-reports/`로 이동
6. **메타데이터**: 프론트매터에 아카이빙 정보 추가

## 프론트매터 변경사항

아카이빙 시 다음 필드가 자동 추가됨:

```yaml
archived: true
archived_date: 2026-01-16
archived_reason: "구버전"
original_path: "3_Resources/R-reports/파일명.md"
```

## 출력 예시

```
[스캔] R-reports 폴더: 16개 파일 발견
[그룹화] 2개 버전 그룹 감지

[아카이브 대상]
  1. 20260114_IBK_임금수준_적정성_분석.md (v0)
     → 최신 버전: 20260114_IBK_임금수준_적정성_분석_v2.5.md 존재 ✓

  2. 20260113_IBK_중소기업대출_시장점유율_분석.md (v0)
     → 최신 버전: 20260113_IBK_중소기업대출_시장점유율_분석_v1.md 존재 ✓

[실행] 2개 파일 아카이빙 완료
  → 4_Archive/Resources/R-reports/20260114_IBK_임금수준_적정성_분석.md
  → 4_Archive/Resources/R-reports/20260113_IBK_중소기업대출_시장점유율_분석.md
```

## 에러 처리

| 상황 | 처리 |
|------|------|
| 버전 그룹에 파일 1개만 | 아카이브 건너뜀 (유일한 버전) |
| 대상 경로에 파일 존재 | 타임스탬프 suffix 추가 |
| 프론트매터 없음 | 새로 생성 |
| 인코딩 오류 | UTF-8 fallback + 경고 |

## 관련 스킬

- `update-vault-db`: 아카이빙 후 메타DB 동기화 권장
- `md-cleaner`: 보고서 정리 후 아카이빙 권장

## 파일 구조

```
archive-report-versions/
├── SKILL.md                           # 이 문서
├── scripts/
│   └── archive_report_versions.py     # 메인 스크립트
└── tests/
    └── test_archive_report_versions.py # 단위 테스트
```

## 주의사항

1. **한글 인코딩**: UTF-8 인코딩 사용, 다른 인코딩 자동 감지
2. **원본 보존**: 아카이브로 이동하므로 원본은 삭제되지 않음
3. **프론트매터**: 아카이빙 정보가 자동 추가되므로 추적 가능
4. **dry-run 권장**: 처음 사용 시 `--dry-run`으로 대상 확인 권장
