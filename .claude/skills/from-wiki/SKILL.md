# -*- coding: utf-8 -*-
---
name: from-wiki
description: Wikipedia 검색 및 문서 조회 스킬 (한글/영어 지원)
version: 1.0.0
---

## Purpose

유저의 질문에 대해 영어/한글 Wikipedia를 검색하고, 문서의 요약 또는 전문을 마크다운 형식으로 반환합니다.

## When to Use This Skill

- 특정 주제에 대한 Wikipedia 정보가 필요할 때
- 한글 또는 영어 Wikipedia 문서를 검색할 때
- Wikipedia 문서를 Obsidian 노트로 저장하고 싶을 때
- 문서의 요약만 빠르게 확인하고 싶을 때
- 문서의 전체 내용이 필요할 때

**예시 요청:**
- "인공지능에 대해 Wikipedia에서 찾아줘"
- "Python 프로그래밍 언어 영문 위키 요약 보여줘"
- "한국 역사 관련 위키 문서 검색해줘"

## Installation

```bash
# 의존성 설치
pip install Wikipedia-API requests
```

**환경 요구사항:**
- Python 3.9 이상
- requests 패키지
- Wikipedia-API 패키지

## Workflow

### Step 1: 검색 (Search)

키워드로 관련 문서 목록을 검색합니다.

```bash
python .claude/skills/from-wiki/scripts/wiki_api.py --search "인공지능" --lang ko
```

### Step 2: 요약 조회 (Summary)

특정 문서의 요약을 가져옵니다.

```bash
python .claude/skills/from-wiki/scripts/wiki_api.py --summary "인공지능" --lang ko
```

### Step 3: 전문 조회 (Full)

문서의 전체 내용을 가져옵니다.

```bash
python .claude/skills/from-wiki/scripts/wiki_api.py --full "인공지능" --lang ko
```

### Step 4: 저장 (Save)

마크다운 파일로 저장합니다.

```bash
# 기본 경로 (0_Inbox/)
python .claude/skills/from-wiki/scripts/wiki_api.py --summary "파이썬" --save

# 사용자 지정 경로
python .claude/skills/from-wiki/scripts/wiki_api.py --full "Python" --lang en --output 3_Resources/python.md
```

## Scripts Reference

### wiki_api.py

**위치:** `.claude >> skills >> from-wiki >> scripts >> wiki_api.py`

**필수 인자 (택일):**

| 옵션 | 설명 |
|------|------|
| `--search`, `-s` | 키워드로 문서 검색 |
| `--summary`, `-m` | 문서 요약 가져오기 |
| `--full`, `-f` | 문서 전문 가져오기 |
| `--sections` | 문서 섹션 구조 가져오기 |

**선택 인자:**

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--lang`, `-l` | `ko` | 언어 선택 (`ko` 한글, `en` 영어) |
| `--limit`, `-n` | `10` | 검색 결과 수 |
| `--save` | - | 기본 경로(`0_Inbox/`)에 저장 |
| `--output`, `-o` | - | 저장 경로 지정 |
| `--json` | - | JSON 형식으로 출력 |

## Examples

### 한글 Wikipedia 검색

```bash
python .claude/skills/from-wiki/scripts/wiki_api.py --search "딥러닝" --lang ko
```

출력:
```
검색 결과 (10건):

1. 딥 러닝
   인공 신경망을 기반으로 하는 기계 학습 방법론...
   https://ko.wikipedia.org/wiki/딥_러닝

2. 심층 신경망
   ...
```

### 영어 Wikipedia 요약

```bash
python .claude/skills/from-wiki/scripts/wiki_api.py --summary "Machine learning" --lang en
```

### 마크다운 저장

```bash
python .claude/skills/from-wiki/scripts/wiki_api.py --full "파이썬" --save
```

생성 파일: `0_Inbox/wiki_파이썬.md`

```markdown
---
title: "파이썬"
source: wikipedia
language: ko
url: https://ko.wikipedia.org/wiki/파이썬
retrieved: 2026-01-07 15:30:00
---

# 파이썬

## 요약

파이썬(Python)은 1991년 프로그래머인 귀도 반 로섬이 발표한...

## 전문

...

---
*출처: [Wikipedia (한글)](https://ko.wikipedia.org/wiki/파이썬)*
```

### JSON 출력

```bash
python .claude/skills/from-wiki/scripts/wiki_api.py --search "AI" --lang en --json
```

## Korean Encoding

한글 인코딩 처리를 위해 다음 조치가 적용되어 있습니다:

1. **stdout 인코딩**: Windows 콘솔에서 한글 출력을 위해 `sys.stdout.reconfigure(encoding='utf-8')` 적용
2. **API 응답**: `response.encoding = 'utf-8'` 명시적 설정
3. **파일 저장**: `encoding='utf-8'` 사용

## Error Handling

| 오류 | 원인 | 해결 |
|------|------|------|
| `문서를 찾을 수 없습니다` | 정확한 문서 제목이 아님 | `--search`로 먼저 검색 |
| `검색 오류` | 네트워크 문제 | 인터넷 연결 확인 |
| `requests 패키지가 필요합니다` | 의존성 미설치 | `pip install requests` |
| `Wikipedia-API 패키지가 필요합니다` | 의존성 미설치 | `pip install Wikipedia-API` |

## Limitations

- **검색 정확도**: 정확한 문서 제목이 필요합니다. 검색(`--search`)으로 먼저 제목을 확인하세요.
- **Rate Limit**: Wikipedia API는 과도한 요청 시 제한될 수 있습니다. 일반적인 사용에서는 문제없습니다.
- **언어 지원**: 현재 한글(`ko`)과 영어(`en`)만 지원합니다.

## Data Directory

**저장 경로:** `0_Inbox/`

파일명 규칙: `wiki_{문서제목}.md`

## Path Convention

이 문서에서 경로는 `>>` 표기법을 사용합니다:
- `.claude >> skills >> from-wiki >> scripts >> wiki_api.py`

## See Also

- [Wikipedia-API Documentation](https://wikipedia-api.readthedocs.io/)
- [MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page)
