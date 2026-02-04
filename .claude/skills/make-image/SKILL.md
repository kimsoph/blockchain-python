---
name: make-image
description: 텍스트 파일(txt, md, csv 등)이나 프롬프트를 기반으로 Gemini API를 사용해 이미지를 생성하는 스킬. 한글/영어 프롬프트를 모두 지원하며, 생성된 이미지는 9_Attachments/images/{YYYYMM}/ 폴더에 img_ 접두사가 붙은 PNG 파일로 저장되어 옵시디언 보고서에 바로 삽입할 수 있다. AI 이미지 생성, 보고서 일러스트레이션, 텍스트 기반 시각화가 필요할 때 사용.
---

# Make Image

## 버전 히스토리

### v1.1 (2026-01-06)
- **할루시네이션 방지 시스템** 추가
  - 지리/위치 관련 프롬프트 모호성 감지 및 경고
  - 프롬프트 자동 강화 (명확화 지침 추가)
  - 남북한 비교 전용 프롬프트 템플릿
- `ImageConfig` 적용 (aspect_ratio가 실제 API에 전달됨)
- 지원 비율 확장 (10가지)
- 프롬프트 절단 개선 (문장/단어 경계에서 안전하게 절단)
- prompt_templates.py 모듈 추가

### v1.0 (2026-01-02)
- 초기 버전
- Gemini 2.5 Flash/Pro 모델 지원
- 텍스트 프롬프트 이미지 생성
- 파일 기반 프롬프트 추출 및 이미지 생성
- 한글/영어 프롬프트 지원
- 다양한 가로세로 비율 및 해상도 지원
- 옵시디언 삽입 코드 자동 생성

## 개요

이 스킬은 나노바나나(Gemini) API를 사용하여 텍스트 프롬프트로 고품질 이미지를 생성한다. 텍스트 파일(.txt, .md, .csv)에서 프롬프트를 추출하여 이미지를 생성할 수도 있으며, 생성된 이미지는 옵시디언 보고서에 바로 삽입할 수 있다.

## 사용 시점

다음과 같은 상황에서 이 스킬을 사용한다:

- 보고서에 삽입할 일러스트레이션 이미지가 필요할 때
- 텍스트 설명을 시각적 이미지로 변환할 때
- 개념이나 아이디어를 이미지로 표현할 때
- 프레젠테이션용 시각 자료가 필요할 때
- 마크다운 문서 내용을 이미지로 시각화할 때

## 지원 모델

| 모델 | 코드명 | 설명 | 해상도 |
|------|--------|------|--------|
| Nano Banana | `flash` | 빠른 생성, 일반 용도 | 최대 1024px |
| Nano Banana Pro | `pro` | 고품질, 전문 자산 | 최대 4K |

## 작업 흐름

### Step 1: 클라이언트 초기화

```python
from nanobanana import NanoBananaClient

# 기본 설정 (flash 모델)
client = NanoBananaClient()

# Pro 모델 사용
client = NanoBananaClient(model='pro')
```

### Step 2: 이미지 생성

**방법 1: 직접 프롬프트**
```python
result = client.generate_image(
    prompt="귀여운 고양이가 책을 읽는 모습, 수채화 스타일",
    filename="reading_cat"
)
```

**방법 2: 파일에서 프롬프트 추출**
```python
result = client.generate_from_file(
    file_path="concept.md",
    filename="concept_image"
)
```

### Step 3: 결과 확인

```python
if result['success']:
    print(f"이미지 저장: {result['path']}")
    print(f"옵시디언 삽입: {result['obsidian_embed']}")
else:
    print(f"오류: {result['error']}")
```

### Step 4: 보고서 삽입

```markdown
![[images/202601/img_reading_cat_20260102_143025.png]]
```

## 상세 사용법

### 텍스트 프롬프트로 이미지 생성

```python
from nanobanana import NanoBananaClient

client = NanoBananaClient()

# 한글 프롬프트
result = client.generate_image(
    prompt="서울 남산타워가 보이는 야경, 네온 사이버펑크 스타일",
    filename="seoul_night",
    aspect_ratio="16:9",
    image_size="2K"
)

print(f"저장 위치: {result['path']}")
print(f"옵시디언: {result['obsidian_embed']}")
```

### 파일에서 프롬프트 추출

```python
# 마크다운 파일에서 프롬프트 추출
result = client.generate_from_file(
    file_path="project_concept.md",
    filename="project_visual",
    aspect_ratio="4:3"
)

# 텍스트 파일에서 프롬프트 추출
result = client.generate_from_file(
    file_path="idea.txt"
)
```

### 일괄 이미지 생성

```python
prompts = [
    "봄 풍경, 벚꽃이 만개한 공원",
    "여름 해변, 맑은 하늘과 파도",
    "가을 단풍, 붉은 산길",
    "겨울 설경, 눈 덮인 마을"
]

results = client.generate_batch(
    prompts=prompts,
    filename_prefix="seasons",
    aspect_ratio="16:9"
)

for r in results:
    if r['success']:
        print(r['obsidian_embed'])
```

## 파라미터

### generate_image()

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `prompt` | str | (필수) | 이미지 생성 프롬프트 |
| `filename` | str | 자동 | 저장할 파일명 |
| `aspect_ratio` | str | '1:1' | 가로세로 비율 |
| `image_size` | str | '1K' | 이미지 크기 |
| `save_image` | bool | True | 이미지 저장 여부 |

### generate_from_file()

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `file_path` | str | (필수) | 텍스트 파일 경로 |
| `filename` | str | 자동 | 저장할 파일명 |
| `aspect_ratio` | str | '1:1' | 가로세로 비율 |
| `image_size` | str | '1K' | 이미지 크기 |
| `max_prompt_length` | int | 2000 | 최대 프롬프트 길이 |

### 지원 가로세로 비율 (v1.1 확장)

| 비율 | 설명 | 추천 용도 |
|------|------|----------|
| `1:1` | 정사각형 | 아이콘, 프로필, SNS |
| `2:3` | 세로 | 인물 사진 |
| `3:2` | 가로 | 풍경 사진 |
| `3:4` | 세로 표준 | 문서 |
| `4:3` | 가로 표준 | 보고서, 발표자료 |
| `4:5` | 세로 | 인스타그램 |
| `5:4` | 가로 | 갤러리 |
| `9:16` | 세로 | 모바일, 스토리 |
| `16:9` | 와이드 | 프레젠테이션, 배너 |
| `21:9` | 울트라와이드 | 시네마틱 |

### 지원 이미지 크기

| 크기 | 해상도 | 설명 |
|------|--------|------|
| `1K` | ~1024px | 기본, 웹용 |
| `2K` | ~2048px | 고해상도 |
| `4K` | ~4096px | 최고 품질 (Pro 모델) |

## 출력 규격

| 항목 | 값 |
|------|-----|
| 파일 형식 | PNG |
| 기본 저장 위치 | `9_Attachments/images/{YYYYMM}/` |
| 파일명 패턴 | `img_{filename}_{YYYYMMDD_HHMMSS}.png` |
| 워터마크 | SynthID (자동 포함) |

## 응답 형식

```python
{
    'success': True,              # 성공 여부
    'path': '/path/to/image.png', # 저장된 파일 경로
    'filename': 'image.png',      # 파일명
    'prompt': '사용된 프롬프트',    # 원본 프롬프트
    'obsidian_embed': '![[...]]', # 옵시디언 삽입 코드
    'text_response': '...',       # API 텍스트 응답 (있는 경우)
    'source_file': '...',         # 원본 파일 (파일 기반 생성 시)
    'error': '...'                # 오류 메시지 (실패 시)
}
```

## 사용 예시

### 예시 1: 보고서 일러스트레이션

```python
from nanobanana import NanoBananaClient

client = NanoBananaClient()

# 보고서 표지 이미지 생성
result = client.generate_image(
    prompt="현대적인 사무실에서 AI와 협업하는 비즈니스 팀, 미니멀 일러스트 스타일, 파란색 톤",
    filename="report_cover",
    aspect_ratio="16:9"
)

print(result['obsidian_embed'])
# ![[images/202601/img_report_cover_20260102_143025.png]]
```

### 예시 2: 개념 시각화

```python
# 마크다운 파일의 내용을 이미지로 변환
result = client.generate_from_file(
    file_path="AI_전략_개념.md",
    filename="ai_strategy_visual",
    aspect_ratio="4:3"
)
```

### 예시 3: 프로젝트 아이콘

```python
icons = [
    ("데이터 분석", "data_analysis"),
    ("보안 시스템", "security"),
    ("고객 서비스", "customer_service")
]

for prompt, name in icons:
    result = client.generate_image(
        prompt=f"{prompt} 아이콘, 플랫 디자인, 파스텔 색상",
        filename=f"icon_{name}",
        aspect_ratio="1:1"
    )
    print(result['obsidian_embed'])
```

## 옵시디언 보고서 삽입 가이드

### 기본 삽입

```markdown
## AI 전략 개요

아래 이미지는 우리 조직의 AI 전략 방향을 시각화한 것이다.

![[images/202601/img_ai_strategy_visual_20260106_143025.png]]

핵심 전략은 세 가지 축으로 구성된다.
```

### 크기 조정

```markdown
![[images/202601/img_image.png|500]]   <!-- 너비 500px -->
![[images/202601/img_image.png|600]]   <!-- 너비 600px -->
```

### 캡션 추가

```markdown
![[images/202601/img_ai_strategy_visual.png|500]]
*그림 1: AI 전략 개념도*
```

## 프롬프트 작성 팁

### 효과적인 프롬프트 구조

```
[주제] + [스타일] + [분위기/색상] + [추가 상세]
```

### 예시

| 목적 | 프롬프트 예시 |
|------|--------------|
| 비즈니스 | "현대적 사무실, 미니멀 일러스트, 파란색 톤, 깔끔한 라인" |
| 기술 | "AI 신경망 시각화, 미래적 디자인, 네온 색상, 어두운 배경" |
| 자연 | "평화로운 호수, 일출, 수채화 스타일, 따뜻한 색감" |
| 추상 | "성장과 혁신의 개념, 추상 기하학, 그라데이션, 역동적" |

### 한글 프롬프트 팁

1. **구체적으로 작성**: "예쁜 그림" → "벚꽃이 만개한 봄 공원, 수채화 스타일"
2. **스타일 명시**: "디지털 아트", "수채화", "유화", "일러스트"
3. **색상 지정**: "파스텔 톤", "따뜻한 색감", "모노크롬"
4. **분위기 표현**: "평화로운", "역동적인", "미래적인"

## 할루시네이션 방지 가이드라인 (v1.1)

### 개요

AI 이미지 생성 시 지리/위치 관련 프롬프트에서 할루시네이션(환각)이 발생할 수 있다. 특히 한반도 관련 이미지에서 남한과 북한의 위치가 뒤바뀌거나 혼동되는 문제가 빈번하다. v1.1에서는 이를 방지하기 위한 자동 검증 및 프롬프트 강화 시스템이 추가되었다.

### 자동 감지 키워드

다음 키워드가 프롬프트에 포함되면 경고가 표시된다:

| 키워드 | 경고 내용 |
|--------|----------|
| `한국`, `korea` | "Korea"는 남/북한 구분이 모호함 |
| `한반도`, `korean peninsula` | 남/북 경계를 명확히 지정 필요 |
| `지도`, `map` | 지역 범위를 명확히 지정 필요 |
| `서울`, `평양` | 수도 위치 명확화 권장 |

### 좋은 예시 vs 나쁜 예시

#### ❌ 나쁜 예시 (모호함)

```python
# 남한/북한 구분 없음 → 할루시네이션 위험
client.generate_image(prompt="한국 지도")
client.generate_image(prompt="Korea map visualization")
client.generate_image(prompt="한반도 경제 시각화")
```

#### ✅ 좋은 예시 (명확함)

```python
# 남한만 명시
client.generate_image(
    prompt="South Korea (Republic of Korea) economic visualization. "
           "Show only the southern portion below the DMZ."
)

# 북한만 명시
client.generate_image(
    prompt="North Korea (DPRK) infrastructure map. "
           "Show only the northern portion above the DMZ."
)

# 남북 비교 (명확한 구분)
client.generate_image(
    prompt="Comparison of South Korea and North Korea. "
           "South Korea on the BOTTOM/SOUTH, North Korea on the TOP/NORTH. "
           "Clear DMZ division at 38th parallel."
)
```

### 남북한 비교 프롬프트 템플릿

남북한 비교 보고서용 이미지는 전용 함수를 사용하면 할루시네이션 방지 지침이 자동으로 추가된다:

```python
from prompt_templates import create_nk_sk_comparison_prompt

# 커버 이미지 프롬프트 생성
cover_prompt = create_nk_sk_comparison_prompt(
    image_type='cover',
    style='modern digital art, infographic style',
    color_scheme='blue (South Korea) and red (North Korea)'
)

# 이미지 유형: 'cover', 'population', 'economy', 'infrastructure', 'social', 'conclusion'
```

### 프롬프트 강화 함수

`enhance_prompt()` 함수는 지리 관련 키워드가 감지되면 자동으로 명확화 지침을 추가한다:

```python
from prompt_templates import enhance_prompt, validate_prompt_geography

# 프롬프트 검증
has_warnings, warnings = validate_prompt_geography("한국 경제 시각화")
if has_warnings:
    for w in warnings:
        print(f"[경고] {w}")

# 프롬프트 강화 (자동)
enhanced = enhance_prompt("한국 경제 시각화")
# → "한국 경제 시각화\n\n[CLARIFICATION: If this refers to Korea, please clearly distinguish..."
```

### 지리/지도 프롬프트 필수 포함 요소

지도 또는 지리 시각화 시 다음을 명시해야 한다:

1. **대상 국가 정식 명칭**
   - 남한: "South Korea" 또는 "Republic of Korea"
   - 북한: "North Korea" 또는 "DPRK"

2. **위치/방향 명시**
   - 남한: "southern part", "below DMZ", "bottom of peninsula"
   - 북한: "northern part", "above DMZ", "top of peninsula"

3. **경계선 표시 (비교 시)**
   - "DMZ (Demilitarized Zone)"
   - "38th parallel"
   - "clearly marked border"

### 템플릿 목록

`prompt_templates.py`에서 제공하는 템플릿:

| 템플릿명 | 용도 |
|----------|------|
| `korea_comparison_cover` | 남북한 비교 표지 |
| `korea_south_only` | 남한만 시각화 |
| `korea_north_only` | 북한만 시각화 |
| `business_report_cover` | 비즈니스 보고서 표지 |
| `concept_visualization` | 개념 시각화 |
| `infrastructure_comparison` | 인프라 비교 |
| `statistics_visualization` | 통계 시각화 |

```python
from prompt_templates import fill_template

# 템플릿 사용 예시
prompt = fill_template(
    'business_report_cover',
    topic='2026 AI Strategy',
    elements='AI icons, data flows, digital transformation'
)
```

## 설정

### 환경 변수

`.claude/.env` 파일에 API 키 설정:

```
GEMINI_API_KEY="your_api_key_here"
```

### 의존성 설치

```bash
pip install google-genai Pillow
```

## 참고 자료

### scripts >> nanobanana.py

이미지 생성을 수행하는 메인 Python 모듈:
- `NanoBananaClient` 클래스: API 클라이언트
- `generate_image()`: 텍스트 프롬프트로 이미지 생성
- `generate_from_file()`: 파일에서 프롬프트 추출 후 생성
- `generate_batch()`: 일괄 이미지 생성

### scripts >> utils.py

유틸리티 함수:
- `get_gemini_api_key()`: API 키 로드
- `generate_filename()`: 타임스탬프 기반 파일명 생성
- `get_output_dir()`: 출력 디렉토리 관리
- `parse_prompt_from_file()`: 파일에서 프롬프트 추출
- `sanitize_prompt()`: 프롬프트 정제
- `truncate_prompt_safely()`: 문장/단어 경계에서 안전한 절단 (v1.1)

### scripts >> prompt_templates.py (v1.1 신규)

할루시네이션 방지 및 프롬프트 템플릿:
- `validate_prompt_geography()`: 지리 관련 프롬프트 모호성 검사
- `has_blocked_content()`: 차단 콘텐츠 검사
- `enhance_prompt()`: 프롬프트 자동 강화 (명확화 지침 추가)
- `enhance_prompt_for_comparison()`: 비교 시각화 프롬프트 강화
- `get_template()`: 템플릿 조회
- `fill_template()`: 템플릿에 값 채우기
- `create_nk_sk_comparison_prompt()`: 남북한 비교 전용 프롬프트 생성

## 주의사항

1. **API 키**:
   - GEMINI_API_KEY가 `.claude/.env`에 설정되어 있어야 함
   - API 사용량에 따른 비용 발생 가능

2. **이미지 제한**:
   - 모든 생성 이미지에 SynthID 워터마크 포함
   - 성인 콘텐츠, 폭력적 이미지 생성 제한
   - API 일일 호출 제한 있음

3. **프롬프트**:
   - 너무 긴 프롬프트는 자동으로 잘림 (2000자 제한)
   - 구체적이고 명확한 프롬프트가 더 좋은 결과 생성

4. **파일 인코딩**:
   - 한글 파일은 UTF-8 인코딩 권장
   - CP949, EUC-KR도 자동 감지하여 처리

5. **네트워크**:
   - API 호출에는 인터넷 연결 필요
   - 이미지 크기에 따라 생성 시간 다름

## 문제 해결

### API 키 오류

**증상**: "GEMINI_API_KEY가 설정되지 않았습니다."

**해결**:
1. `.claude/.env` 파일 확인
2. `GEMINI_API_KEY="..."` 형식으로 설정
3. 따옴표 안에 API 키 입력

### 이미지 생성 실패

**증상**: "이미지를 생성하지 못했습니다."

**해결**:
1. 프롬프트 내용 확인 (금지된 콘텐츠 여부)
2. 네트워크 연결 확인
3. API 사용량 한도 확인

### 한글 깨짐

**증상**: 파일 읽기 시 한글이 깨짐

**해결**:
1. 파일을 UTF-8로 저장
2. 또는 UTF-8-BOM으로 저장
3. 스킬이 자동으로 여러 인코딩 시도함

### 저장 경로 오류

**증상**: 이미지가 저장되지 않음

**해결**:
1. `9_Attachments/images/{YYYYMM}/` 폴더 존재 확인 (자동 생성됨)
2. 쓰기 권한 확인
3. 디스크 공간 확인
