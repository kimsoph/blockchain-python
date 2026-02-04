---
name: make-network_diagram
description: NetworkX/Matplotlib 기반 네트워크 다이어그램 생성 스킬. DSL, Python API, 마크다운 파일에서 키워드를 추출하여 네트워크 그래프를 생성한다. 4가지 레이아웃 알고리즘(spring, circular, kamada_kawai, shell)과 5가지 테마를 지원한다. 생성된 이미지는 9_Attachments/images/{YYYYMM}/ 폴더에 net_ 접두사가 붙은 PNG 파일로 저장되며, 옵시디언 문법으로 보고서에 바로 삽입할 수 있다. 키워드 관계도, 개념 네트워크, 정책 관계 시각화가 필요할 때 사용.
---

# make-network_diagram 스킬

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.0 | 2026-01-12 | 최초 릴리즈: DSL/Python API/마크다운, 5개 테마, 4개 레이아웃 |

## 개요

NetworkX와 Matplotlib를 사용하여 네트워크 다이어그램을 생성하는 스킬입니다.

- **3가지 입력 방식**: DSL 텍스트, Python API, 마크다운 파일 키워드 추출
- **4가지 레이아웃**: spring (기본), circular, kamada_kawai, shell
- **5가지 테마**: minimal, elegant, clean, corporate, dark
- **노드/엣지 커스터마이징**: 크기, 색상, 두께, 스타일 지정
- **방향 화살표**: 방향/무방향 그래프 지원
- **메서드 체이닝** 지원
- **한글** 완벽 지원 (Malgun Gothic)

## 사용 시점

다음 상황에서 이 스킬을 사용합니다:

- 키워드 간 관계를 시각화할 때
- 개념/아이디어 네트워크 표현
- 정책/전략 관계도 작성
- 문서에서 핵심 키워드 추출 및 시각화
- 연결망 분석 결과 표현
- 보고서/문서에 삽입할 네트워크 다이어그램 생성

## 설치

```bash
pip install -r requirements.txt
```

의존성:
- networkx>=2.6.0
- matplotlib>=3.5.0
- numpy>=1.20.0

## DSL 문법 가이드

### 기본 문법

```
title: 다이어그램 제목
layout: spring

# 노드 정의 (선택)
[노드1]
[노드2] size=100 color=#FF0000

# 엣지 정의
[노드1] -- [노드2]           # 무방향
[노드1] -> [노드2]           # 방향
[노드1] --> [노드2]          # 점선 방향
[노드1] -> [노드2]: 라벨     # 라벨 포함
```

### 노드 속성

| 속성 | 설명 | 예시 |
|------|------|------|
| `size` | 노드 크기 (기본: 50) | `[노드] size=100` |
| `color` | 노드 색상 | `[노드] color=#FF5500` |

### 엣지 타입

| 기호 | 설명 | 스타일 |
|------|------|--------|
| `--` | 무방향 연결 | 실선 |
| `->` | 방향 연결 | 실선 + 화살표 |
| `-->` | 방향 연결 | 점선 + 화살표 |
| `<->` | 양방향 연결 | 실선 |
| `<-->` | 양방향 연결 | 점선 |

### DSL 예제

```
title: 정책 관계도
layout: spring

[통합] size=100
[성장] size=80
[혁신] size=70
[협력] size=60

[통합] -> [성장]
[통합] -> [혁신]
[성장] -- [협력]: 파트너십
[혁신] --> [협력]
```

## Python API 사용법

### 기본 사용 (메서드 체이닝)

```python
from scripts import NetworkDrawer

drawer = NetworkDrawer(theme='minimal', layout='spring')

# 메서드 체이닝으로 네트워크 구성
(drawer
    .set_title('정책 관계도')
    .add_node('통합', size=100)
    .add_node('성장', size=80)
    .add_node('혁신', size=70)
    .add_node('협력', size=60)
    .add_edge('통합', '성장')
    .add_edge('통합', '혁신')
    .add_edge('성장', '협력')
    .add_edge('혁신', '협력', style='dashed')
    .save('정책관계도'))
```

### DSL 방식

```python
from scripts import NetworkDrawer

drawer = NetworkDrawer(theme='clean')
drawer.from_dsl('''
    title: 키워드 네트워크
    [통합] size=100
    [성장]
    [혁신]
    [통합] -> [성장]
    [통합] -> [혁신]
''')
drawer.save('keyword_network')
```

### 마크다운 파일에서 키워드 추출

```python
from scripts import NetworkDrawer

drawer = NetworkDrawer(theme='elegant')
drawer.from_markdown('취임사.md')
drawer.save('취임사_키워드네트워크')

# 중심 노드 지정 (star 형태)
drawer2 = NetworkDrawer()
drawer2.from_markdown('문서.md', center_node='통합')
drawer2.save('star_network')
```

### NetworkDrawer 클래스 API

#### 생성자

```python
NetworkDrawer(
    theme='minimal',      # 테마: minimal, elegant, clean, corporate, dark
    layout='spring',      # 레이아웃: spring, circular, kamada_kawai, shell
    dpi=300,              # 해상도
    figsize=(12, 10),     # 그림 크기
    output_dir=None       # 출력 경로 (기본: 9_Attachments/images/{YYYYMM}/)
)
```

#### 노드 추가 메서드

| 메서드 | 설명 |
|--------|------|
| `add_node(node, size=50, color=None)` | 노드 추가 |
| `set_title(title)` | 제목 설정 |
| `set_layout(layout)` | 레이아웃 변경 |

#### 엣지 추가 메서드

| 메서드 | 설명 |
|--------|------|
| `add_edge(source, target, weight=1.0, style='solid', label=None, directed=False)` | 엣지 추가 |
| `connect(*nodes, **kwargs)` | 여러 노드 순차 연결 |

#### 입력 메서드

| 메서드 | 설명 |
|--------|------|
| `from_dsl(dsl_text)` | DSL 텍스트 파싱 |
| `from_dsl_file(file_path)` | DSL 파일 로드 |
| `from_markdown(file_path, center_node=None)` | 마크다운에서 키워드 추출 |

#### 출력 메서드

| 메서드 | 설명 |
|--------|------|
| `render()` | matplotlib Figure 객체 반환 |
| `save(filename)` | PNG 파일 저장, 경로 반환 |
| `clear()` | 모든 노드/엣지 초기화 |

### 편의 함수

```python
from scripts import create_network

# 한 줄로 DSL -> 이미지 저장
path = create_network(dsl_text, theme='clean', layout='spring', filename='my_network')
```

## CLI 사용법

### DSL 파일에서 생성

```bash
python draw_network.py --dsl network.txt --name "관계도"
python draw_network.py --dsl network.txt --theme elegant --layout circular
```

### 마크다운 파일에서 키워드 추출

```bash
python draw_network.py --file 취임사.md --name "키워드네트워크"
python draw_network.py --file 문서.md --center "통합" --name "중심네트워크"
```

### CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--dsl` | DSL 파일 경로 | - |
| `--file` | 마크다운 파일 경로 | - |
| `--name` | 출력 파일명 | network |
| `--theme` | 테마 | minimal |
| `--layout` | 레이아웃 알고리즘 | spring |
| `--center` | 중심 노드 (마크다운 모드) | - |

## 출력 규격

| 항목 | 값 |
|------|-----|
| 포맷 | PNG |
| 해상도 | 300 DPI |
| 파일명 접두사 | `net_` |
| 저장 경로 | `9_Attachments/images/{YYYYMM}/` |
| 파일명 예시 | `net_정책관계도_20260112_143025.png` |

### 옵시디언 삽입

저장 시 콘솔에 옵시디언 삽입 코드가 출력됩니다:

```
[OK] 네트워크 다이어그램 저장 완료: D:\_Obsidian\ZK-PARA\9_Attachments\images\202601\net_정책관계도_20260112_143025.png
[INFO] 옵시디언 삽입: ![[9_Attachments/images/202601/net_정책관계도_20260112_143025.png]]
```

## 레이아웃 알고리즘

| 레이아웃 | 설명 | 적합한 상황 |
|----------|------|-------------|
| `spring` | 스프링 물리 시뮬레이션 (기본) | 일반적인 네트워크, 클러스터 시각화 |
| `circular` | 원형 배치 | 순환 관계, 균등 분포 강조 |
| `kamada_kawai` | 에너지 최소화 | 거리 관계 정확한 표현 |
| `shell` | 동심원 배치 | 계층/레벨 구조 |

## 테마 목록

| 테마 | 설명 | 배경색 |
|------|------|--------|
| `minimal` | 미니멀 모노톤 스타일 | 흰색 |
| `elegant` | 베이지/브라운 세련된 스타일 | #FFFEF5 |
| `clean` | 깔끔한 블루 톤 | 흰색 |
| `corporate` | 비즈니스용 네이비 톤 | #F5F5F5 |
| `dark` | 어두운 배경 테마 | #1A1A1A |

## 마크다운 키워드 추출 규칙

`from_markdown()` 메서드는 다음 방식으로 키워드를 추출합니다:

1. **## 키워드 섹션** 파싱
   ```markdown
   ## 키워드
   #통합 #성장 #혁신
   ```

2. **해시태그** 추출
   ```markdown
   본문에서 #핵심단어 형태의 해시태그를 추출합니다.
   ```

추출된 키워드로 네트워크 생성:
- `center_node` 지정시: 별(star) 형태
- 미지정시: 인접 키워드 원형 연결

## 사용 예시

### 예시 1: 정책 관계도

```python
from scripts import NetworkDrawer

drawer = NetworkDrawer(theme='clean', layout='spring')
(drawer
    .set_title('경제정책 관계도')
    .add_node('성장', size=100, color='#4CAF50')
    .add_node('안정', size=90, color='#2196F3')
    .add_node('혁신', size=80)
    .add_node('분배', size=70)
    .add_node('고용', size=60)
    .add_edge('성장', '안정', weight=2)
    .add_edge('성장', '혁신')
    .add_edge('안정', '분배')
    .add_edge('혁신', '고용')
    .add_edge('분배', '고용', style='dashed')
    .save('경제정책_관계도'))
```

### 예시 2: 키워드 네트워크

```python
from scripts import create_network

dsl = """
title: 취임사 키워드 분석
layout: circular

[통합] size=100
[미래] size=80
[협력] size=70
[혁신] size=70
[성장] size=60

[통합] -> [미래]
[통합] -> [협력]
[미래] -> [혁신]
[혁신] -> [성장]
[협력] -- [성장]
"""

path = create_network(dsl, theme='elegant', filename='취임사_키워드')
```

### 예시 3: 문서 분석

```python
from scripts import NetworkDrawer

drawer = NetworkDrawer(theme='corporate', layout='kamada_kawai')
drawer.from_markdown('연구보고서.md')
drawer.save('연구보고서_개념도')
```

## 주의사항

### 한글 폰트

- Windows: `Malgun Gothic` (기본 설치됨)
- macOS: `AppleGothic` (기본 설치됨)
- Linux: `NanumGothic` (별도 설치 필요)

한글이 깨지는 경우:
1. 시스템에 한글 폰트가 설치되어 있는지 확인
2. matplotlib 폰트 캐시 삭제 후 재시작

### 파일 인코딩

모든 소스 파일과 DSL 파일은 **UTF-8 인코딩**을 사용해야 합니다.

### 출력 경로

> **CRITICAL: 출력 경로 관련**
> - **절대 `output_dir` 파라미터를 직접 지정하지 말 것**
> - `NetworkDrawer()`를 파라미터 없이 호출하면 자동으로 올바른 경로로 저장됨
> - 올바른 경로: `9_Attachments/images/{YYYYMM}/net_*.png`

### 노드 수 제한

- 50개 이상의 노드는 가독성이 떨어질 수 있음
- 많은 노드의 경우 `shell` 레이아웃 권장

## 참고 자료

### scripts >> draw_network.py

네트워크 다이어그램 생성을 수행하는 메인 Python 모듈:
- `NetworkDrawer` 클래스: 네트워크 생성 로직
- `add_node()`: 노드 추가
- `add_edge()`: 엣지 추가
- `from_dsl()`: DSL 파싱
- `from_markdown()`: 마크다운 키워드 추출
- `render()`: matplotlib Figure 생성
- `save()`: PNG 저장

### scripts >> utils.py

유틸리티 함수:
- `get_korean_font()`: OS별 한글 폰트 반환
- `get_output_dir()`: 출력 디렉토리 반환
- `generate_filename()`: 타임스탬프 기반 파일명 생성
- `get_theme()`: 테마 설정 반환
- `parse_dsl()`: DSL 텍스트 파싱
- `extract_keywords_from_markdown()`: 마크다운 키워드 추출
- `build_network_from_keywords()`: 키워드 네트워크 구조 생성
