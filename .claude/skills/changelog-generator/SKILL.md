# changelog-generator

*최종 업데이트: 2026-01-13*

Git 커밋 메시지를 기반으로 `_Docs/CHANGELOG.md`를 자동 갱신하는 스킬

## 핵심 기능

- Git 커밋 메시지 파싱 (subject + body)
- 커밋 타입별 CHANGELOG 엔트리 생성
- 날짜별 섹션 자동 병합
- 중복 방지 (처리된 커밋 추적)

## 사용법

```bash
# 단독 실행
python .claude/skills/changelog-generator/scripts/generate_changelog.py

# /update_git 명령에 통합됨 (4번 단계)
```

## 커밋 타입 필터링

| 타입 | 포함 | 설명 |
|------|------|------|
| feat | ✓ | 신규 기능/스킬 |
| refactor | ✓ | 구조 변경/재구성 |
| docs | ✓ | 문서화 |
| fix | ✓ | 버그 수정 |
| chore | ❌ | 자동 생성 파일 동기화 (제외) |

## 변환 예시

**입력 (Git 커밋):**
```
refactor: file-move-tracker 스킬 완전 제거

Git이 이미 모든 파일 이동/삭제를 영구 기록하므로 중복 기능 제거.

삭제:
- .claude/skills/file-move-tracker/
- _Docs/file_move_history.md
```

**출력 (CHANGELOG 엔트리):**
```markdown
## 2026-01-13

- **file-move-tracker 스킬 완전 제거**
  - Git이 이미 모든 파일 이동/삭제를 영구 기록하므로 중복 기능 제거
```

## 파일 구조

```
.claude/skills/changelog-generator/
├── SKILL.md                    # 이 파일
├── data/
│   └── changelog_tracking.yml  # 처리된 커밋 추적 파일
└── scripts/
    └── generate_changelog.py   # 메인 스크립트

_Docs/CHANGELOG.md              # 출력 대상
```

## 추적 파일 형식

`data/changelog_tracking.yml`:
```yaml
last_processed_commit: "3e702b6"
last_update_date: "2026-01-13"
```

## 관련 스킬

- `document-map-generator`: 문서 인덱스 자동 생성
- `update-vault-db`: 메타데이터 DB 동기화
- `update-claude-files`: CLAUDE.md 점검
