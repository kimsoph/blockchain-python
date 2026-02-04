---
name: make-flowchart
description: Graphviz 기반 플로우차트 생성 스킬. DSL 또는 Python API로 플로우차트를 생성하여 PNG 이미지로 저장한다.
---

# make-flowchart 스킬

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.0 | 2026-01-08 | 최초 릴리즈: DSL/Python API, 5개 테마, 7개 노드 타입 |

## 개요

Graphviz 라이브러리를 사용하여 플로우차트를 생성하는 스킬입니다.

- **DSL 문법** 또는 **Python API** 두 가지 방식 지원
- 7가지 노드 타입 (시작, 종료, 프로세스, 결정, 입출력, 문서, 데이터베이스)
- 5가지 테마 (minimal, elegant, clean, corporate, dark)
- 메서드 체이닝 지원
- 한글 완벽 지원 (Malgun Gothic)

## 사용 시점

다음 상황에서 이 스킬을 사용합니다:

- 업무 프로세스 시각화
- 알고리즘/로직 흐름도 작성
- 의사결정 트리 다이어그램
- 시스템 아키텍처 흐름 표현
- 보고서/문서에 삽입할 다이어그램 생성

## DSL 문법 가이드

### 기본 문법

```
title: 플로우차트 제목
direction: TB

[노드타입] node_id: 라벨 텍스트

node1 -> node2
node1 -> node2: 엣지 라벨
node1 --> node2: 점선 엣지
```

### 노드 타입 (7가지)

| 타입 | DSL 키워드 | 모양 | 색상 | 용도 |
|------|-----------|------|------|------|
| 시작 | `[시작]`, `[start]` | 타원 (ellipse) | 녹색 (#10B981) | 프로세스 시작점 |
| 종료 | `[종료]`, `[end]` | 이중 원 (doublecircle) | 빨강 (#EF4444) | 프로세스 종료점 |
| 프로세스 | `[프로세스]`, `[process]` | 둥근 박스 (box, rounded) | 파랑 (#3B82F6) | 일반 처리/작업 |
| 결정 | `[결정]`, `[decision]` | 마름모 (diamond) | 노랑 (#F59E0B) | 조건 분기 |
| 입출력 | `[입출력]`, `[io]` | 평행사변형 (parallelogram) | 보라 (#8B5CF6) | 데이터 입출력 |
| 문서 | `[문서]`, `[document]` | 노트 (note) | 밝은 회색 (#F3F4F6) | 문서/보고서 |
| 데이터베이스 | `[데이터베이스]`, `[database]` | 실린더 (cylinder) | 시안 (#06B6D4) | DB 조회/저장 |

### 방향 설정

| 값 | 설명 |
|----|------|
| `TB` | Top to Bottom (위에서 아래, 기본값) |
| `LR` | Left to Right (왼쪽에서 오른쪽) |
| `BT` | Bottom to Top (아래에서 위) |
| `RL` | Right to Left (오른쪽에서 왼쪽) |

### DSL 예제

```
title: 로그인 프로세스
direction: TB

[시작] start: 시작
[입출력] input: ID/PW 입력
[프로세스] validate: 입력값 검증
[결정] check: 인증 성공?
[프로세스] login: 로그인 처리
[데이터베이스] log: 로그 기록
[종료] end: 완료

start -> input
input -> validate
validate -> check
check -> login: Yes
check --> input: No (재시도)
login -> log
log -> end
```

## Python API 사용법

### 기본 사용

```python
from scripts import FlowchartDrawer

# DSL 방식
drawer = FlowchartDrawer(theme='clean')
drawer.parse_dsl('''
    title: 로그인 프로세스
    [시작] start: 시작
    [프로세스] input: 입력
    [종료] end: 종료
    start -> input -> end
''')
path = drawer.save('login')
```

### Python API 방식 (메서드 체이닝)

```python
from scripts import FlowchartDrawer

drawer = FlowchartDrawer(theme='elegant', direction='LR')

# 메서드 체이닝으로 플로우차트 구성
(drawer
    .set_title('주문 처리 프로세스')
    .add_start('s', '주문 시작')
    .add_io('i1', '주문 정보 입력')
    .add_database('db1', '재고 확인')
    .add_decision('d1', '재고 있음?')
    .add_process('p1', '결제 처리')
    .add_document('doc', '주문서 생성')
    .add_end('e', '주문 완료')
    .connect('s', 'i1', 'db1', 'd1')
    .add_edge('d1', 'p1', label='Yes')
    .add_edge('d1', 's', label='No', style='dashed')
    .connect('p1', 'doc', 'e')
    .save('order_flow'))
```

### FlowchartDrawer 클래스 API

#### 생성자

```python
FlowchartDrawer(
    theme='minimal',    # 테마: minimal, elegant, clean, corporate, dark
    direction='TB',     # 방향: TB, LR, BT, RL
    dpi=300,            # 해상도
    output_dir=None     # 출력 경로 (기본: 9_Attachments/images/{YYYYMM}/)
)
```

#### 노드 추가 메서드

| 메서드 | 설명 |
|--------|------|
| `add_node(node_id, label, node_type='process')` | 일반 노드 추가 |
| `add_start(node_id, label)` | 시작 노드 추가 |
| `add_end(node_id, label)` | 종료 노드 추가 |
| `add_process(node_id, label)` | 프로세스 노드 추가 |
| `add_decision(node_id, label)` | 결정 노드 추가 |
| `add_io(node_id, label)` | 입출력 노드 추가 |
| `add_document(node_id, label)` | 문서 노드 추가 |
| `add_database(node_id, label)` | 데이터베이스 노드 추가 |

#### 엣지 추가 메서드

| 메서드 | 설명 |
|--------|------|
| `add_edge(from_node, to_node, label='', style='solid')` | 엣지 추가 |
| `connect(*nodes, labels=None)` | 여러 노드 순차 연결 |

#### 설정 메서드

| 메서드 | 설명 |
|--------|------|
| `set_title(title)` | 제목 설정 |
| `set_direction(direction)` | 방향 설정 (TB, LR, BT, RL) |
| `parse_dsl(dsl_text)` | DSL 텍스트 파싱 |

#### 출력 메서드

| 메서드 | 설명 |
|--------|------|
| `render()` | Graphviz Digraph 객체 반환 |
| `save(filename)` | PNG 파일 저장, 경로 반환 |
| `clear()` | 모든 노드/엣지 초기화 |

### 편의 함수

```python
from scripts import create_flowchart

# 한 줄로 DSL → 이미지 저장
path = create_flowchart(dsl_text, theme='clean', filename='my_flow')
```

## 출력 규격

| 항목 | 값 |
|------|-----|
| 포맷 | PNG |
| 해상도 | 300 DPI |
| 파일명 접두사 | `flow_` |
| 저장 경로 | `9_Attachments/images/{YYYYMM}/` |
| 파일명 예시 | `flow_login_20260108_143025.png` |

### 옵시디언 삽입

저장 시 콘솔에 옵시디언 삽입 코드가 출력됩니다:

```
[OK] 플로우차트 저장 완료: D:\_Obsidian\ZK-PARA\9_Attachments\images\202601\flow_login_20260108_143025.png
[INFO] 옵시디언 삽입: ![[9_Attachments/images/202601/flow_login_20260108_143025.png]]
```

## 테마 목록

| 테마 | 설명 | 배경색 |
|------|------|--------|
| `minimal` | 미니멀 모노톤 스타일 | 흰색 |
| `elegant` | 세련된 그레이 톤 + 골드 액센트 | #F7FAFC |
| `clean` | 깔끔한 블루 톤 비즈니스 스타일 | 흰색 |
| `corporate` | 비즈니스/기업용 파란색 톤 | #F8F9FA |
| `dark` | 어두운 배경 테마 | #1A1A2E |

## Graphviz 레퍼런스

### 기본 노드/엣지 생성

```python
from graphviz import Digraph

g = Digraph()
g.node('A', 'Node A')
g.node('B', 'Node B')
g.edge('A', 'B')
```

### 주요 속성

| 속성 | 설명 | 예시 |
|------|------|------|
| `shape` | 노드 모양 | `box`, `ellipse`, `diamond` |
| `style` | 스타일 | `filled`, `rounded`, `dashed` |
| `fillcolor` | 채우기 색상 | `#3B82F6`, `lightblue` |
| `fontname` | 폰트 | `Malgun Gothic` |
| `fontsize` | 폰트 크기 | `12` |
| `fontcolor` | 폰트 색상 | `white`, `#374151` |
| `penwidth` | 테두리 두께 | `1.5` |
| `label` | 레이블 텍스트 | `처리 단계` |

### 노드 모양 종류

| 모양 | 설명 | 용도 |
|------|------|------|
| `box` | 사각형 | 일반 프로세스 |
| `ellipse` | 타원 | 시작/종료 |
| `circle` | 원 | 상태 |
| `doublecircle` | 이중 원 | 최종 상태 |
| `diamond` | 마름모 | 결정/분기 |
| `parallelogram` | 평행사변형 | 입출력 |
| `cylinder` | 실린더 | 데이터베이스 |
| `note` | 노트/문서 | 문서 |
| `folder` | 폴더 | 디렉토리 |
| `component` | 컴포넌트 | 모듈 |

### 엣지 스타일

| 스타일 | 설명 | 사용법 |
|--------|------|--------|
| `solid` | 실선 (기본) | `style='solid'` |
| `dashed` | 점선 | `style='dashed'` |
| `dotted` | 점점선 | `style='dotted'` |
| `bold` | 굵은 선 | `style='bold'` |

### 방향 설정 (rankdir)

```python
g.attr(rankdir='TB')  # Top to Bottom (기본)
g.attr(rankdir='LR')  # Left to Right
g.attr(rankdir='BT')  # Bottom to Top
g.attr(rankdir='RL')  # Right to Left
```

### 그래프 속성

```python
g.attr(
    rankdir='TB',       # 방향
    dpi='300',          # 해상도
    bgcolor='white',    # 배경색
    splines='ortho',    # 연결선 스타일 (ortho: 직각)
    nodesep='0.5',      # 노드 간격 (가로)
    ranksep='0.6',      # 랭크 간격 (세로)
)
```

## 주의사항

### Graphviz 설치 필요

이 스킬은 Graphviz 라이브러리가 필요합니다:

```bash
# Python 패키지
pip install graphviz

# 시스템 Graphviz (Windows)
# https://graphviz.org/download/ 에서 설치
# 또는 chocolatey: choco install graphviz
# 또는 winget: winget install graphviz

# macOS
brew install graphviz

# Linux (Ubuntu/Debian)
sudo apt install graphviz
```

### 한글 폰트

- Windows: `Malgun Gothic` (기본 설치됨)
- macOS: `AppleGothic` (기본 설치됨)
- Linux: `NanumGothic` (별도 설치 필요)

한글이 깨지는 경우:
1. 시스템에 한글 폰트가 설치되어 있는지 확인
2. Graphviz가 올바르게 설치되어 있는지 확인

### 파일 인코딩

모든 소스 파일은 UTF-8 인코딩을 사용합니다.
DSL 텍스트도 UTF-8로 작성해야 합니다.
