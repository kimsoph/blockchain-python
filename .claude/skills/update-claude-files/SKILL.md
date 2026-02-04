# update-claude-files

*버전: v1.2*
*최종 업데이트: 2026-01-29*

## 개요

ZK-PARA Vault 내 모든 CLAUDE.md 파일의 품질을 점검하고 리포트를 생성하는 스킬.
구조적 일관성, 링크 유효성, 통계 정보 정확성을 자동으로 검증한다.

## 핵심 기능

1. **구조 점검**: 필수 섹션 존재 여부 검증
2. **링크 검증**: 내부 링크([[]])  유효성 검사
3. **날짜 검증**: 최종 업데이트 날짜 현행화 여부
4. **통계 검증**: Root CLAUDE.md 통계 정보와 실제 현황 비교
5. **분류별 스킬 검증**: `### 분류명 (N개)` 헤더와 실제 테이블 행 수 일치 여부 (v1.1)
6. **리포트 생성**: 점검 결과를 마크다운 리포트로 출력
7. **통계 자동 수정**: `--fix` 옵션으로 Root CLAUDE.md 통계 불일치 자동 수정 (v1.2)

## 점검 항목

### 필수 섹션 (모든 CLAUDE.md)

| 패턴 | 설명 |
|------|------|
| `*최종 업데이트:` | 날짜 메타 정보 |
| `## 목적과 역할` / `## 개요` / `## 주제 설명` | 목적 섹션 |
| `공통 지침` | 공통 지침 참조 링크 |

### 링크 유효성

- `[[path|text]]` 형식 추출
- 실제 파일/폴더 존재 여부 확인
- `.md` 확장자 자동 처리

### 통계 정보 검증 (Root만)

| 항목 | 비교 대상 |
|------|----------|
| 스킬 개수 | `.claude/skills/` 폴더 수 |
| 에이전트 개수 | `.claude/agents/` 폴더 수 |
| 활성 프로젝트 | `1_Projects/P-*` 폴더 수 |
| 활성 영역 | `2_Areas/A-*` 폴더 수 |
| 리소스 | `3_Resources/R-*` 폴더 수 |

### 분류별 스킬 검증 (Root만, v1.1)

`### 분류명 (N개)` 형식의 헤더와 실제 테이블 내 스킬 수를 비교:

| 분류 | 검증 방식 |
|------|----------|
| 문서 처리 | 헤더 숫자 vs 테이블 행 수 |
| API 연동 | 헤더 숫자 vs 테이블 행 수 |
| 시각화 | 헤더 숫자 vs 테이블 행 수 |
| 시스템 | 헤더 숫자 vs 테이블 행 수 |
| 기타 | 헤더 숫자 vs 테이블 행 수 |

## 사용법

### 전체 점검
```bash
python .claude/skills/update-claude-files/scripts/check_claude_files.py
```

### 특정 파일만 점검
```bash
python .claude/skills/update-claude-files/scripts/check_claude_files.py --file CLAUDE.md
```

### 상세 출력
```bash
python .claude/skills/update-claude-files/scripts/check_claude_files.py --verbose
```

### 통계 불일치 자동 수정 (v1.2)
```bash
python .claude/skills/update-claude-files/scripts/check_claude_files.py --fix
```
- Root CLAUDE.md의 스킬/에이전트/프로젝트/영역/리소스 개수가 실제와 불일치하면 자동 수정
- 수정 시 최종 업데이트 날짜도 함께 갱신

## 출력

### 콘솔 출력
```
=== CLAUDE.md 점검 시작 ===
[INFO] 발견된 파일: 44개
[OK] CLAUDE.md - 모든 점검 통과
[WARN] 0_Inbox/CLAUDE.md - 날짜 업데이트 필요 (7일 경과)
[ERR] ... - 링크 오류: [[invalid_path]]
...
=== 점검 완료: 42 정상, 2 이슈 ===
```

### 리포트 파일
`_Docs/claude-files-report.md`에 상세 리포트 생성

## 리포트 형식

```markdown
# CLAUDE.md 점검 리포트

*생성일: 2026-01-09 17:30*

## 요약
- 점검 파일: 44개
- 정상: 42개
- Critical: 0개
- Warning: 2개

## 이슈 목록

### Critical
(없음)

### Warning
| 파일 | 문제 | 권장 조치 |
|------|------|----------|
| 0_Inbox/CLAUDE.md | 날짜 7일 경과 | 최신 업데이트 필요 |

## 통계 검증
| 항목 | 문서 기재 | 실제 | 상태 |
|------|----------|------|------|
| 스킬 | 32개 | 32개 | OK |
| 에이전트 | 1개 | 1개 | OK |
| 프로젝트 | 1개 | 1개 | OK |
| 영역 | 3개 | 3개 | OK |
| 리소스 | 6개 | 6개 | OK |

## 분류별 스킬 검증
| 분류 | 문서 기재 | 실제 | 상태 |
|------|----------|------|------|
| 문서 처리 | 4개 | 4개 | OK |
| API 연동 | 8개 | 8개 | OK |
| 시각화 | 10개 | 10개 | OK |
| 시스템 | 7개 | 7개 | OK |
| 기타 | 3개 | 3개 | OK |

## 전체 파일 목록
(44개 파일 상세 정보)
```

## 동기화 정책

- **실행 시점**: `/update_git` 명령 실행 시 자동 호출
- **수동 실행**: 언제든 직접 실행 가능
- **리포트 갱신**: 실행 시마다 덮어쓰기

## 이슈 분류

| 레벨 | 설명 | 예시 |
|------|------|------|
| Critical | 즉시 수정 필요 | 링크 오류, 필수 섹션 누락 |
| Warning | 권장 수정 | 날짜 7일+ 경과, 통계 불일치 |
| Info | 참고 정보 | 파일 목록, 구조 정보 |

## 파일 구조

```
.claude/skills/update-claude-files/
├── SKILL.md                    # 이 문서
└── scripts/
    └── check_claude_files.py   # 메인 점검 스크립트
```

## 관련 스킬

- `update-vault-db`: Vault 전체 메타데이터 DB 관리
- `document-map-generator`: 문서 인덱스 생성
