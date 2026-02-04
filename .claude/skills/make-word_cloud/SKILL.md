# make-word_cloud

마크다운 문서에서 핵심 키워드를 추출하여 워드클라우드 이미지를 생성하는 스킬

## 버전

- **v1.0.0** (2026-01-12): 초기 버전

## 목적

텍스트 문서(취임사, 보고서, 논문 등)에서 핵심 키워드를 시각적으로 표현하는 워드클라우드를 생성한다. 한글 형태소 분석(Mecab)을 통해 정확한 명사/동사 추출을 지원한다.

## 사용 시점

- 취임사, 연설문 등에서 핵심 키워드를 시각화할 때
- 문서의 주요 주제를 한눈에 파악하고 싶을 때
- 보고서나 논문의 키워드 분포를 분석할 때
- 텍스트 데이터의 빈도 분석 결과를 시각화할 때

## 설치

### 1. Python 패키지 설치

```bash
pip install wordcloud konlpy matplotlib numpy Pillow
```

### 2. Mecab 설치 (Windows)

한글 형태소 분석을 위해 Mecab이 필요하다.

**이미 설치된 경로**: `C:\mecab`

Mecab이 설치되지 않은 경우:
1. [mecab-ko-msvc](https://github.com/Pusnow/mecab-ko-msvc/releases) 다운로드
2. `C:\mecab`에 압축 해제
3. 환경변수 PATH에 `C:\mecab` 추가

> **Note**: Mecab이 없어도 동작하지만, 공백 분리 방식으로 대체되어 정확도가 낮아진다.

## 사용법

### Python API

#### 기본 사용법

```python
from draw_wordcloud import WordCloudDrawer

# 파일에서 워드클라우드 생성
drawer = WordCloudDrawer()
drawer.from_file('취임사.md')
drawer.save('이재명취임사')
# 출력: wc_이재명취임사_20260112_143025.png
```

#### 텍스트 직접 입력

```python
drawer = WordCloudDrawer()
drawer.from_text('대한민국 국민 여러분 감사합니다 통합 성장 평화')
drawer.save('테스트')
```

#### 딕셔너리로 가중치 지정

```python
drawer = WordCloudDrawer()
drawer.from_dict({
    '통합': 100,
    '성장': 80,
    '평화': 70,
    '민주주의': 60,
    '국민': 50
})
drawer.set_title('정책 키워드')
drawer.save('정책키워드')
```

#### 메서드 체이닝

```python
(WordCloudDrawer(max_words=50, colormap='plasma')
    .from_file('취임사.md')
    .set_title('제21대 대통령 취임사 키워드')
    .save('이재명취임사'))
```

#### 커스터마이징

```python
drawer = WordCloudDrawer(
    max_words=100,          # 최대 단어 수
    width=1600,             # 이미지 너비
    height=900,             # 이미지 높이
    background_color='black',  # 배경색
    colormap='plasma',      # 컬러맵
    dpi=300,                # 해상도
)
drawer.from_file('document.md')
drawer.save('custom_cloud')
```

#### 마스크 이미지 사용

```python
drawer = WordCloudDrawer()
drawer.from_file('취임사.md')
drawer.set_mask('korea_map.png')  # 한반도 모양 마스크
drawer.save('korea_wordcloud')
```

#### 상위 단어 확인

```python
drawer = WordCloudDrawer()
drawer.from_file('취임사.md')

# 상위 20개 단어 출력
for word, freq in drawer.get_top_words(20):
    print(f'{word}: {freq}')
```

### CLI 사용법

```bash
# 기본 사용
python scripts/draw_wordcloud.py --file "취임사.md" --name "이재명취임사"

# 텍스트 직접 입력
python scripts/draw_wordcloud.py --text "단어1 단어2 단어3" --name "테스트"

# 옵션 지정
python scripts/draw_wordcloud.py \
    --file "취임사.md" \
    --name "취임사분석" \
    --title "제21대 대통령 취임사" \
    --max-words 50 \
    --colormap plasma \
    --background white

# 상위 단어 확인
python scripts/draw_wordcloud.py --file "취임사.md" --name "분석" --top-words 20

# 불용어 제거 비활성화
python scripts/draw_wordcloud.py --file "취임사.md" --name "전체" --no-stopwords
```

## 파라미터

### WordCloudDrawer 생성자

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `max_words` | int | 100 | 최대 단어 수 |
| `width` | int | 1200 | 이미지 너비 (픽셀) |
| `height` | int | 800 | 이미지 높이 (픽셀) |
| `background_color` | str | 'white' | 배경색 |
| `colormap` | str | 'viridis' | matplotlib 컬러맵 |
| `dpi` | int | 300 | 출력 해상도 |
| `min_font_size` | int | 10 | 최소 폰트 크기 |
| `max_font_size` | int | 150 | 최대 폰트 크기 |

### 컬러맵 옵션

- `viridis` (기본): 파랑→초록→노랑
- `plasma`: 보라→분홍→노랑
- `Blues`: 파랑 계열
- `Reds`: 빨강 계열
- `Greens`: 초록 계열
- `YlOrRd`: 노랑→주황→빨강
- `coolwarm`: 파랑↔빨강
- `RdYlBu`: 빨강→노랑→파랑

### CLI 옵션

| 옵션 | 단축 | 설명 |
|------|------|------|
| `--file` | `-f` | 입력 마크다운 파일 경로 |
| `--text` | `-t` | 직접 텍스트 입력 |
| `--name` | `-n` | 출력 파일명 (필수) |
| `--title` | | 워드클라우드 제목 |
| `--max-words` | | 최대 단어 수 |
| `--width` | | 이미지 너비 |
| `--height` | | 이미지 높이 |
| `--colormap` | | 컬러맵 |
| `--background` | | 배경색 |
| `--mask` | | 마스크 이미지 경로 |
| `--no-stopwords` | | 불용어 제거 비활성화 |
| `--output-dir` | `-o` | 출력 디렉토리 |
| `--top-words` | | 상위 N개 단어 출력 |

## 출력

- **경로**: `9_Attachments/images/{YYYYMM}/`
- **파일명**: `wc_{name}_{YYYYMMDD_HHMMSS}.png`
- **해상도**: 300 DPI

### Obsidian 삽입

```markdown
![[images/202601/wc_이재명취임사_20260112_143025.png]]
```

## 한글 처리

### 형태소 분석 (Mecab)

Mecab이 설치된 경우:
- 명사(NN*): 일반명사, 고유명사, 의존명사 등
- 동사(VV): 동사 어간
- 형용사(VA): 형용사 어간

### 불용어 제거

기본 불용어 목록:
- 조사: 이, 가, 은, 는, 을, 를, 의, 에, 에서 등
- 어미/접사: 하다, 되다, 있다, 없다 등
- 대명사: 나, 너, 우리, 그, 이것 등
- 부사/접속사: 매우, 아주, 그리고, 그러나 등

연설문 추가 불용어:
- 존경, 국민, 여러분, 감사, 오늘, 우리, 대한민국, 나라

### 불용어 커스터마이징

```python
from utils import KOREAN_STOPWORDS

# 불용어 추가
custom_stopwords = KOREAN_STOPWORDS.copy()
custom_stopwords.add('특정단어')
```

## 디렉토리 구조

```
.claude/skills/make-word_cloud/
├── SKILL.md              # 이 문서
├── requirements.txt      # Python 의존성
└── scripts/
    ├── __init__.py       # 패키지 초기화
    ├── draw_wordcloud.py # WordCloudDrawer 클래스
    └── utils.py          # 유틸리티 함수
```

## 예시

### 취임사 워드클라우드

```python
from draw_wordcloud import WordCloudDrawer

drawer = WordCloudDrawer(max_words=80, colormap='Blues')
drawer.from_file('5_Zettelkasten/2_Literature/Speeches/제21대 대통령 취임사 - 이재명 - 2025.md')
drawer.set_title('제21대 대통령 취임사 키워드')
drawer.save('이재명취임사_2025')
```

### 여러 문서 비교

```python
from draw_wordcloud import WordCloudDrawer

files = [
    ('제21대 대통령 취임사 - 이재명 - 2025.md', '이재명'),
    ('제20대 대통령 취임사 - 윤석열 - 2022.md', '윤석열'),
    ('제19대 대통령 취임사 - 문재인 - 2017.md', '문재인'),
]

for file, name in files:
    drawer = WordCloudDrawer(max_words=50)
    drawer.from_file(f'5_Zettelkasten/2_Literature/Speeches/{file}')
    drawer.set_title(f'{name} 대통령 취임사')
    drawer.save(f'{name}취임사')
```

## 문제 해결

### Mecab 로드 실패

```
[WARN] Mecab 로드 실패, 공백 분리 방식 사용
```

**해결**:
1. `C:\mecab` 폴더에 Mecab이 설치되어 있는지 확인
2. 환경변수 PATH에 `C:\mecab` 추가
3. Python 재시작

### 한글 폰트 깨짐

**해결**:
1. Windows: `C:\Windows\Fonts\malgun.ttf` 존재 확인
2. 폰트 경로 직접 지정: `utils.py`의 `get_korean_font_path()` 수정

### 메모리 부족

대용량 문서 처리 시:
```python
drawer = WordCloudDrawer(max_words=50, width=800, height=600)
```

## 관련 스킬

- `make-chart`: 차트 이미지 생성
- `make-infographic`: 인포그래픽 생성
- `make-network_diagram`: 네트워크 다이어그램 생성
