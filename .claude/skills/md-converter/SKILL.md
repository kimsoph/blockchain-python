# md-converter

다양한 문서 포맷(HWPX, PDF, DOCX)을 마크다운으로 변환하는 통합 스킬.

## 버전

v1.0.0 - HWPX 지원

## 파이프라인 위치

```
[원본 문서] → md-converter → md-cleaner → md2db → [SQLite DB]
             (포맷 변환)    (클리닝)     (DB 저장)
```

## 지원 포맷

| 포맷 | 상태 | 구현 방법 |
|------|------|----------|
| HWPX | ✅ v1.0 | zipfile + ElementTree (직접 파싱) |
| PDF | 🔜 v1.1 | markitdown CLI 래핑 |
| DOCX | 🔜 v1.2 | markitdown CLI 래핑 |

## 사용법

### 단일 파일 변환

```bash
# 기본 변환 (자동 감지)
python .claude/skills/md-converter/scripts/convert.py input.hwpx

# 출력 경로 지정
python .claude/skills/md-converter/scripts/convert.py input.hwpx -o output.md

# 문서 유형 지정
python .claude/skills/md-converter/scripts/convert.py --doc-type law input.hwpx
python .claude/skills/md-converter/scripts/convert.py --doc-type general input.hwpx
```

### 배치 변환

```bash
# 폴더 내 모든 파일 변환
python .claude/skills/md-converter/scripts/convert.py --batch ./folder/

# 재귀적으로 하위 폴더까지
python .claude/skills/md-converter/scripts/convert.py --batch -r ./folder/
```

### 옵션

```bash
# 미리보기 (파일 생성 안 함)
python .claude/skills/md-converter/scripts/convert.py --dry-run input.hwpx

# 상세 로그
python .claude/skills/md-converter/scripts/convert.py -v input.hwpx

# 기존 파일 덮어쓰기
python .claude/skills/md-converter/scripts/convert.py --overwrite input.hwpx
```

## 문서 유형

### law (법률 문서)

법률, 시행령, 시행규칙 등 조문 구조가 있는 문서:
- 장/조/항/호/목 구조 인식
- YAML 프론트매터에 문서번호, 시행일 포함

**자동 감지 조건:**
- 파일명에 '법률', '시행령', '시행규칙', '규정', '조례', '훈령', '고시', '예규' 포함
- 본문에 조문 패턴 (제1조, 제2장 등) 3개 이상

### general (일반 문서)

보고서, 메모 등 일반적인 텍스트 문서:
- 단순 단락 분리
- 기본 프론트매터

## 입출력 예시

### 입력 파일명

```
소득세법(법률)(제21065호)(20260102).hwpx
```

### 출력 파일명

```
소득세법_20260102.md
```

### 출력 형식 (법률 문서)

```markdown
---
title: 소득세법
type: 법률
문서번호: 제21065호
시행일: 2026-01-02
source: 법제처 국가법령정보센터
converted_at: 2026-02-04 15:30:00
---
# 소득세법

> [시행 2026. 1. 2.] [법률 제21065호]

## 제1장 총칙

### 제1조(목적)

이 법은 개인의 소득에 대하여 소득의 성격과 납세자의 부담능력 등에 따라 적정하게 과세함으로써 조세부담의 형평을 도모하고 재정수입의 원활한 조달에 이바지함을 목적으로 한다.

### 제2조(정의)

① 이 법에서 사용하는 용어의 뜻은 다음과 같다.
   1. "거주자"란 국내에 주소를 두거나 183일 이상의 거소를 둔 개인을 말한다.
   2. "비거주자"란 거주자가 아닌 개인을 말한다.
```

### 출력 형식 (일반 문서)

```markdown
---
title: 보고서 제목
source: HWPX 변환
converted_at: 2026-02-04 15:30:00
---
# 보고서 제목

첫 번째 단락 내용입니다.

두 번째 단락 내용입니다.
```

## 파일 구조

```
.claude/skills/md-converter/
├── SKILL.md                    # 이 문서
├── requirements.txt            # 의존성 (chardet)
├── scripts/
│   ├── convert.py              # CLI 진입점
│   └── converters/
│       ├── __init__.py
│       ├── base.py             # BaseConverter 추상 클래스
│       └── hwpx.py             # HWPXConverter
└── tests/
    └── test_converters.py      # 단위 테스트
```

## 의존성

```
chardet>=5.0.0  # 인코딩 감지
```

## 전체 파이프라인 예시

```bash
# 1. HWPX → 마크다운 변환
python .claude/skills/md-converter/scripts/convert.py \
  "3_Resources/R-regulations/법률등/소득세법(법률)(제21065호)(20260102).hwpx"

# 2. 마크다운 클리닝 (옵션)
python .claude/skills/md-cleaner/scripts/clean_markdown.py \
  "3_Resources/R-regulations/법률등/소득세법_20260102.md"

# 3. SQLite DB 저장 (옵션)
python .claude/skills/md2db/scripts/md2db.py \
  "3_Resources/R-regulations/법률등/소득세법_20260102.md" \
  "3_Resources/R-DB/gov_regulation.db"
```

## HWPX 파일 구조 참고

HWPX는 ZIP 형식의 한글 문서:
```
file.hwpx (ZIP)
├── Contents/
│   ├── section0.xml    # 본문 (주요 콘텐츠)
│   ├── section1.xml    # 추가 섹션 (있는 경우)
│   └── ...
├── META-INF/
└── mimetype
```

주요 XML 태그:
- `hp:t`: 텍스트 내용
- `hp:p`: 단락
- `hp:secPr`: 섹션 속성

## 테스트

```bash
cd .claude/skills/md-converter
python -m pytest tests/ -v
```

## 향후 계획

- **v1.1**: PDF 지원 (markitdown 래핑)
- **v1.2**: DOCX 지원 (markitdown 래핑)
- **v1.3**: 표(table) 추출 개선
- **v2.0**: 이미지 추출 및 첨부
