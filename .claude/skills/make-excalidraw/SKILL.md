---
name: make-excalidraw
description: 마크다운 문서를 파싱하여 Excalidraw 다이어그램(.excalidraw)을 자동 생성하는 스킬. 마인드맵, 플로우차트, 개념도, 트리 레이아웃을 지원한다.
---

# make-excalidraw 스킬

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.3 | 2026-01-19 | 접두사 `excali_` → `exc_`, 저장 폴더 `excalidraw/` → `images/` 통합 |
| v1.2 | 2026-01-19 | 트리 레이아웃 서브트리 충돌 방지 알고리즘 적용, v_spacing 기본값 60으로 조정 |
| v1.1 | 2026-01-19 | 채우기 스타일 7종, 화살표 끝점 6종, 글꼴 옵션 4종, roughness 레벨 추가 |
| v1.0 | 2026-01-19 | 최초 릴리즈: 마크다운/DSL 파싱, 4가지 레이아웃, 5개 테마 |

## 개요

마크다운 문서나 DSL을 파싱하여 Excalidraw 다이어그램을 자동 생성하는 스킬입니다.

- **마크다운 파싱**: 헤딩, 리스트 구조를 자동 추출
- **4가지 레이아웃**: 마인드맵, 플로우차트, 개념도, 트리
- **5가지 테마**: minimal, elegant, clean, corporate, dark
- **Obsidian 호환**: `.excalidraw` 파일로 저장하여 Obsidian에서 편집 가능
- **한글 완벽 지원**

## 사용 시점

다음 상황에서 이 스킬을 사용합니다:

- 마크다운 노트를 시각화하고 싶을 때
- 마인드맵으로 아이디어를 정리할 때
- 프로세스 흐름을 다이어그램으로 표현할 때
- 개념 간 관계를 시각화할 때
- Obsidian에서 편집 가능한 다이어그램이 필요할 때

## 다이어그램 유형

| 유형 | 레이아웃 | 용도 |
|------|----------|------|
| `mindmap` | 방사형 트리 | 중심에서 가지가 뻗어나가는 구조 |
| `flowchart` | 계층적 DAG | 위→아래 또는 좌→우 흐름 |
| `concept` | Force-directed | 노드 간 관계를 자연스럽게 배치 |
| `tree` | 수직/수평 트리 | 계층적 조직도 스타일 |

## Python API 사용법

### 기본 사용: 마크다운 파일 → Excalidraw

```python
from scripts import from_markdown

# 마크다운 파일을 마인드맵으로 변환
path = from_markdown(
    file_path='my_note.md',
    layout_type='mindmap',
    theme='clean'
)
print(f"![[{path}]]")
```

### 마크다운 문자열 변환

```python
from scripts import from_markdown

content = """
# 프로젝트 계획

## 1단계: 기획
- 요구사항 분석
- 일정 수립

## 2단계: 개발
- 백엔드
- 프론트엔드

## 3단계: 테스트
- 단위 테스트
- 통합 테스트
"""

path = from_markdown(
    content=content,
    layout_type='mindmap',
    theme='elegant',
    filename='project_plan'
)
```

### DSL 방식

```python
from scripts import from_dsl

dsl = """
type: mindmap
theme: clean
center: 메인 주제

- 가지 1
  - 세부 1-1
  - 세부 1-2
- 가지 2
  - 세부 2-1
- 가지 3
---
가지 1 -> 가지 2: 관련
가지 2 --> 가지 3
"""

path = from_dsl(dsl, filename='my_mindmap')
```

### ExcalidrawBuilder 직접 사용 (고급)

```python
from scripts import ExcalidrawBuilder, generate_id

builder = ExcalidrawBuilder(theme='corporate')

# 노드 생성
node1_id = generate_id()
node2_id = generate_id()
node3_id = generate_id()

(builder
    .add_rectangle(100, 100, 150, 60, text='시작', id=node1_id,
                   backgroundColor='#D1FAE5', strokeColor='#10B981')
    .add_rectangle(100, 250, 150, 60, text='처리', id=node2_id,
                   backgroundColor='#DBEAFE', strokeColor='#3B82F6')
    .add_rectangle(100, 400, 150, 60, text='종료', id=node3_id,
                   backgroundColor='#FEE2E2', strokeColor='#EF4444')
    .add_arrow((175, 160), (175, 250),
               start_binding=node1_id, end_binding=node2_id)
    .add_arrow((175, 310), (175, 400),
               start_binding=node2_id, end_binding=node3_id))

path = builder.save('custom_diagram')
```

### 레이아웃 함수 직접 사용

```python
from scripts import (
    ExcalidrawBuilder,
    layout_mindmap,
    layout_flowchart,
    layout_concept,
    layout_tree
)

# 마인드맵
builder = ExcalidrawBuilder(theme='minimal')
nodes = [
    {'text': '중심', 'level': 0, 'children': [
        {'text': '가지1', 'level': 1, 'children': []},
        {'text': '가지2', 'level': 1, 'children': []},
    ]}
]
layout_mindmap(builder, nodes, center=(500, 400))
builder.save('mindmap')

# 플로우차트
builder = ExcalidrawBuilder(theme='clean')
nodes = [
    {'text': '시작', 'type': 'start'},
    {'text': '처리', 'type': 'process'},
    {'text': '결정', 'type': 'decision'},
    {'text': '종료', 'type': 'end'}
]
edges = [
    {'from': '시작', 'to': '처리'},
    {'from': '처리', 'to': '결정'},
    {'from': '결정', 'to': '종료', 'label': 'Yes'}
]
layout_flowchart(builder, nodes, edges, direction='TB')
builder.save('flowchart')
```

## DSL 문법

### 메타데이터

```
type: mindmap|flowchart|concept
theme: minimal|elegant|clean|corporate|dark
direction: TB|LR|BT|RL
center: 중심 노드 텍스트
```

### 노드 정의 (리스트 형식)

```
- 노드 텍스트
  - 하위 노드 1
  - 하위 노드 2
    - 하위-하위 노드
```

### 엣지 정의 (구분선 이후)

```
---
노드1 -> 노드2
노드1 -> 노드2: 라벨
노드1 --> 노드2: 점선
```

### DSL 전체 예시

```
type: flowchart
theme: elegant
direction: TB

- 시작
- 입력 받기
- 유효성 검사
- 처리
- 결과 출력
- 종료
---
시작 -> 입력 받기
입력 받기 -> 유효성 검사
유효성 검사 -> 처리: 성공
유효성 검사 --> 입력 받기: 실패
처리 -> 결과 출력
결과 출력 -> 종료
```

## ExcalidrawBuilder API

### 생성자

```python
ExcalidrawBuilder(theme='minimal')
```

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `theme` | str | 'minimal' | 테마 이름 |

### 도형 추가 메서드

| 메서드 | 설명 |
|--------|------|
| `add_rectangle(x, y, width, height, text=None, **style)` | 사각형 추가 |
| `add_ellipse(x, y, width, height, text=None, **style)` | 타원 추가 |
| `add_diamond(x, y, width, height, text=None, **style)` | 마름모 추가 |
| `add_text(x, y, text, **style)` | 독립 텍스트 추가 |

### 연결 추가 메서드

| 메서드 | 설명 |
|--------|------|
| `add_arrow(start, end, label=None, **style)` | 화살표 추가 |
| `add_line(start, end, **style)` | 선 추가 |

### 그룹/프레임 메서드

| 메서드 | 설명 |
|--------|------|
| `add_group(element_ids)` | 요소들을 그룹화, 그룹 ID 반환 |
| `add_frame(x, y, width, height, name)` | 프레임 추가, 프레임 ID 반환 |

### 유틸리티 메서드

| 메서드 | 설명 |
|--------|------|
| `get_element(element_id)` | ID로 요소 조회 |
| `clear()` | 모든 요소 초기화 |
| `to_json()` | JSON 딕셔너리 반환 |
| `save(filename, output_dir)` | 파일 저장, 경로 반환 |

### 스타일 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `id` | str | 요소 ID (자동 생성) |
| `strokeColor` | str | 테두리 색상 (예: '#3B82F6') |
| `backgroundColor` | str | 배경 색상 |
| `strokeWidth` | int | 테두리 두께 (기본: 2) |
| `strokeStyle` | str | 선 스타일 ('solid', 'dashed', 'dotted') |
| `fillStyle` | str | 채우기 스타일 (기본: 'hachure') |
| `roughness` | int | 손그림 느낌 (0: 깔끔, 1: 약간, 2: 강함) |
| `opacity` | int | 불투명도 (0-100) |
| `fontSize` | int | 텍스트 크기 (기본: 20) |
| `fontFamily` | int | 글꼴 (1: 손글씨, 2: 시스템, 3: 만화, 4: 코드) |
| `textColor` | str | 텍스트 색상 |

### 채우기 스타일 (fillStyle)

| 스타일 | 설명 |
|--------|------|
| `hachure` | 빗금 채우기 (기본, 손그림 느낌) |
| `cross-hatch` | 격자 빗금 |
| `solid` | 단색 채우기 |
| `zigzag` | 지그재그 패턴 |
| `dots` | 점 패턴 |
| `dashed` | 대시 패턴 |
| `zigzag-line` | 지그재그 선 |

### 화살표 끝점 (arrowhead)

| 타입 | 설명 |
|------|------|
| `None` | 끝점 없음 |
| `arrow` | 기본 화살표 (기본값) |
| `triangle` | 채워진 삼각형 |
| `dot` | 원형 끝점 |
| `bar` | 직선 막대 |
| `diamond` | 마름모 끝점 |

```python
# 화살표 예시
builder.add_arrow(
    (100, 100), (200, 100),
    startArrowhead='dot',      # 시작점: 원형
    endArrowhead='triangle'    # 끝점: 삼각형
)
```

### 글꼴 패밀리 (fontFamily)

| 값 | 이름 | 설명 |
|----|------|------|
| 1 | Virgil | 손글씨 스타일 (기본) |
| 2 | 시스템 | 시스템 기본 폰트 |
| 3 | Comic Shanns | 만화 스타일 |
| 4 | Cascadia | 코드/모노스페이스 |

### 글꼴 크기 프리셋

| 이름 | 크기 |
|------|------|
| `small` | 16 |
| `medium` | 20 (기본) |
| `large` | 28 |
| `xlarge` | 36 |

### Roughness 레벨

| 값 | 이름 | 설명 |
|----|------|------|
| 0 | Architect | 깔끔한 직선 |
| 1 | Artist | 약간의 손그림 느낌 (기본) |
| 2 | Cartoonist | 강한 손그림 느낌 |

## 출력 규격

| 항목 | 값 |
|------|-----|
| 포맷 | `.excalidraw` (JSON) |
| 파일명 접두사 | `exc_` |
| 저장 경로 | `9_Attachments/images/{YYYYMM}/` |
| 파일명 예시 | `exc_mindmap_20260119_143025.excalidraw` |

### 옵시디언 삽입

저장 시 콘솔에 옵시디언 삽입 코드가 출력됩니다:

```
[OK] Excalidraw 저장 완료: D:\_Obsidian\ZK-PARA\9_Attachments\images\202601\exc_mindmap_20260119_143025.excalidraw
[INFO] 옵시디언 삽입: ![[9_Attachments/images/202601/exc_mindmap_20260119_143025.excalidraw]]
```

## 테마 목록

| 테마 | 설명 | 배경색 | 선 색상 |
|------|------|--------|---------|
| `minimal` | 미니멀 모노톤 스타일 | #FFFFFF | #1A1A2E |
| `elegant` | 세련된 그레이 톤 | #F7FAFC | #2D3748 |
| `clean` | 깔끔한 블루 톤 비즈니스 스타일 | #FFFFFF | #3B82F6 |
| `corporate` | 비즈니스/기업용 파란색 톤 | #F8F9FA | #1E40AF |
| `dark` | 어두운 배경 테마 | #1A1A2E | #E2E8F0 |

## 마크다운 파싱 규칙

### 지원하는 구조

| 요소 | 설명 |
|------|------|
| 헤딩 (`# ~ ######`) | 계층적 노드로 변환, 레벨별 색상 적용 |
| 리스트 (`-`, `*`, `1.`) | 하위 노드로 변환, 들여쓰기로 계층 판단 |
| 위키링크 (`[[...]]`) | 노드 간 연결 관계로 추출 |
| 태그 (`#...`) | 메타데이터로 추출 |

### YAML 프론트매터

```yaml
---
title: 문서 제목
tags: [tag1, tag2]
---
```

- `title`은 다이어그램 파일명에 사용
- 기타 메타데이터는 무시

## 레이아웃 알고리즘

### 마인드맵 (layout_mindmap)

- 중심 노드를 중앙에 배치
- 자식 노드를 방사형으로 배치
- 레벨별로 색상 자동 지정

```python
layout_mindmap(
    builder,
    nodes,
    center=(500, 400),  # 중심 좌표
    radius=200,         # 첫 레벨 반지름
    node_spacing=80     # 노드 간 간격
)
```

### 플로우차트 (layout_flowchart)

- 노드를 순서대로 배치
- 방향 지원: TB (위→아래), LR (왼→오른), BT, RL
- 노드 타입별 모양: start/end(타원), decision(마름모), process(사각형)

```python
layout_flowchart(
    builder,
    nodes,
    edges,
    direction='TB',        # 방향
    spacing=(150, 100)     # (수평, 수직) 간격
)
```

### 개념도 (layout_concept)

- Force-directed 알고리즘 사용
- 연결된 노드끼리 가깝게, 연결 안 된 노드끼리 멀게 배치
- 복잡한 관계망 시각화에 적합

```python
layout_concept(
    builder,
    nodes,
    links,                 # [(from, to), ...]
    center=(500, 400),
    iterations=50          # 시뮬레이션 반복 횟수
)
```

### 트리 (layout_tree)

- 계층적 트리 구조
- 조직도, 분류 체계에 적합
- v1.2: 서브트리 충돌 방지 알고리즘 적용

```python
layout_tree(
    builder,
    nodes,                 # 계층적 구조
    direction='TB',        # TB 또는 LR
    root_pos=(400, 50),
    h_spacing=150,
    v_spacing=60           # v1.2: 60 (이전 100)
)
```

## 주의사항

### Obsidian Excalidraw 플러그인

- 이 스킬로 생성한 `.excalidraw` 파일을 열려면 Obsidian Excalidraw 플러그인이 필요합니다
- 플러그인 설치: Community plugins에서 "Excalidraw" 검색

### 파일 인코딩

- 모든 소스 파일은 UTF-8 인코딩을 사용합니다
- 한글 텍스트가 포함된 마크다운도 UTF-8로 저장해야 합니다

### 외부 의존성 없음

- 이 스킬은 외부 Python 패키지 의존성이 없습니다
- 표준 라이브러리만 사용합니다

## 참고 자료

- [Excalidraw JSON Schema](https://docs.excalidraw.com/docs/codebase/json-schema)
- [Obsidian Excalidraw Plugin](https://github.com/zsviczian/obsidian-excalidraw-plugin)
- 기존 스킬: `.claude/skills/make-flowchart/`, `.claude/skills/make-diagram/`
