# update-vault-db

*버전: v1.2*
*최종 업데이트: 2026-01-07*

## 개요

ZK-PARA Vault 전체 마크다운 파일의 메타데이터를 SQLite DB로 관리하는 스킬.
YAML frontmatter를 파싱하여 통합 검색, 분석, 연결 추적을 지원한다.

## v1.2 변경사항 (2026-01-07)

- **다중 인코딩 fallback 지원**: utf-8 → utf-8-sig → cp949 → euc-kr 순서로 읽기 시도
- **비-UTF-8 파일 자동 변환**: 감지된 파일을 UTF-8로 자동 재저장 (원본 덮어쓰기)
- **검색 함수 NFC 정규화**: 모든 검색 함수에 일관된 인코딩 처리 적용
- **UTF-8 변환 결과 상세 로깅**: 변환 성공/실패/오류를 구분하여 출력
- **UTF-8 BOM 명시적 처리**: BOM 문자 자동 제거

## v1.1 변경사항 (2026-01-07)

- **한글 인코딩 완전 지원**
  - 모든 파일 경로에 NFC 유니코드 정규화 적용
  - Windows/macOS 간 한글 파일명 호환성 개선
  - SQLite UTF-8 인코딩 명시적 확인
  - Python UTF-8 환경 변수 강제 설정
- **진행 상황 표시**: `--verbose` 옵션 추가
- **오류 통계**: 동기화 완료 시 오류 건수 표시

## 핵심 원칙

- **YAML이 원본, DB는 캐시**: 불일치 시 항상 YAML이 우선
- **읽기 전용 캐시**: DB는 조회용, 수정은 마크다운 파일에서
- **동기화**: `/update_git` 실행 시 자동 갱신

## DB 위치

```
.claude/ZK-PARA.db
```

> `.claude` 폴더에 위치하는 이유: Vault 전체 메타데이터는 Claude Code의 시스템 데이터이므로, 사용자 콘텐츠 폴더(Resources 등)가 아닌 시스템 폴더에 저장

## 스키마

### notes (핵심 테이블)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | PK, 자동증가 |
| file_path | TEXT | 상대 경로 (UNIQUE) |
| file_name | TEXT | 파일명 |
| title | TEXT | 제목 (YAML 또는 첫 헤딩) |
| author | TEXT | 저자 |
| note_type | TEXT | 유형 (book, poem, speech, project 등) |
| source | TEXT | 출처 |
| status | TEXT | 상태 (읽는중, 완료, 추출완료 등) |
| created | TEXT | 생성일 |
| updated | TEXT | 수정일 |
| date_consumed | TEXT | 소비일 |
| folder_category | TEXT | 폴더 분류 (Projects, Areas, Resources 등) |
| folder_path | TEXT | 상위 폴더 경로 |
| summary | TEXT | 요약 (첫 200자) |
| word_count | INTEGER | 단어 수 |
| has_frontmatter | INTEGER | YAML 존재 여부 (0/1) |
| frontmatter_raw | TEXT | YAML 원본 (JSON) |
| indexed_at | TEXT | 인덱싱 시간 |

### tags
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | PK |
| tag_name | TEXT | 태그명 (UNIQUE) |

### note_tags (다대다)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| note_id | INTEGER | FK → notes.id |
| tag_id | INTEGER | FK → tags.id |

### links (노트 간 연결)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | PK |
| source_path | TEXT | 출발 노트 경로 |
| target_note | TEXT | 대상 노트 (위키링크 텍스트) |
| link_type | TEXT | wikilink / embed |
| display_text | TEXT | 표시 텍스트 (별칭) |

### meta_info
| 컬럼 | 타입 | 설명 |
|------|------|------|
| key | TEXT | 키 (PK) |
| value | TEXT | 값 |
| updated_at | TEXT | 갱신 시간 |

## 사용법

### 초기화 (스키마 생성)
```bash
python .claude/skills/update-vault-db/scripts/meta_db.py --init
```

### 전체 동기화 (YAML → DB)
```bash
python .claude/skills/update-vault-db/scripts/meta_db.py --sync
```

### 검색
```bash
# 키워드 검색 (title, author, summary에서)
python .claude/skills/update-vault-db/scripts/meta_db.py --search "이육사"

# 태그로 검색
python .claude/skills/update-vault-db/scripts/meta_db.py --tag "poem"

# 폴더 카테고리로 검색
python .claude/skills/update-vault-db/scripts/meta_db.py --category "Zettelkasten"
```

### 직접 쿼리
```bash
python .claude/skills/update-vault-db/scripts/meta_db.py --query "SELECT title, author FROM notes WHERE note_type='poem'"
```

### DB 통계
```bash
python .claude/skills/update-vault-db/scripts/meta_db.py --info
```

## Claude Code 활용 예시

```python
# 이육사 시인의 시가 있는지 확인
SELECT title, file_path FROM notes WHERE author = '이육사'

# 완료 상태이면서 영구노트 미추출인 Literature 노트
SELECT title, file_path FROM notes
WHERE folder_category = 'Zettelkasten'
  AND status = '완료'

# 태그별 노트 수
SELECT t.tag_name, COUNT(*) as cnt
FROM tags t
JOIN note_tags nt ON t.id = nt.tag_id
GROUP BY t.tag_name
ORDER BY cnt DESC

# 고아 노트 (연결 없는 노트) 탐지
SELECT n.file_path, n.title
FROM notes n
LEFT JOIN links l ON n.file_path = l.source_path
WHERE l.id IS NULL AND n.folder_category = 'Zettelkasten'
```

## 동기화 정책

1. **동기화 시점**: `/update_git` 실행 시
2. **동기화 방식**: 전체 재구축 (incremental 미지원)
3. **충돌 해결**: YAML이 항상 우선
4. **삭제 처리**: 파일 삭제 시 DB에서도 삭제

## 제외 대상

- `.claude/` 폴더 내 파일
- `node_modules/`, `.git/` 등 시스템 폴더
- `.obsidian/` 폴더
- 이미지, PDF 등 비-마크다운 파일

## 관련 스킬

- `document-map-generator`: 문서 인덱스 생성 (마크다운 형태)
- `md2db`: 개별 마크다운을 DB로 변환 (내용 포함)

## 차이점: update-vault-db vs md2db

| 구분 | update-vault-db | md2db |
|------|-----------------|-------|
| 대상 | Vault 전체 메타데이터 | 개별 파일 전체 내용 |
| 내용 | YAML + 요약 | 섹션/블록 전체 |
| 용도 | 검색, 통계, 연결분석 | 대용량 문서 처리 |
| 갱신 | /update_git 시 자동 | 수동 실행 |
