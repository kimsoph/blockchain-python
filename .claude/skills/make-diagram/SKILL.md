# make-diagram

---
name: make-diagram
description: Graphviz 기반 다이어그램 생성 스킬. 블록 다이어그램, 조직도, 계층 구조, 관계도를 생성한다.
---

## 버전 히스토리

| 버전 | 날짜 | 변경 사항 |
|------|------|-----------|
| v1.0 | 2026-01-08 | 초기 버전 출시. DSL 파싱, 테마 시스템, 다이어그램 타입별 레이아웃 지원 |

## 개요

`make-diagram` 스킬은 Graphviz를 사용하여 다양한 종류의 다이어그램을 생성한다. DSL(Domain Specific Language) 문법으로 간편하게 다이어그램을 정의하거나, Python API를 통해 프로그래밍 방식으로 생성할 수 있다.

## 사용 시점

- 시스템 아키텍처 다이어그램이 필요할 때
- 조직도를 작성할 때
- 계층 구조나 분류 체계를 시각화할 때
- 엔티티 간 관계를 표현할 때
- 프로세스 흐름도가 필요할 때

## 다이어그램 타입

| 타입 | 설명 | 레이아웃 엔진 | 방향 |
|------|------|---------------|------|
| `block` | 블록 다이어그램 (기본) | dot | TB (위→아래) |
| `org` | 조직도 | dot | TB (위→아래) |
| `hierarchy` | 계층 구조 | dot | TB (위→아래) |
| `relation` | 관계도 (무방향) | neato/fdp | 없음 |

## DSL 문법 가이드

### 기본 구조

```
title: 다이어그램 제목
type: block

# 주석은 #으로 시작

group 그룹명 {
    [노드1]
    [노드2]
}

[노드A] -> [노드B]
[노드A] <-> [노드B]: 양방향 연결
[노드A] --> [노드B]: 점선 연결
```

### 문법 요소

| 문법 | 설명 | 예시 |
|------|------|------|
| `title:` | 다이어그램 제목 | `title: 시스템 아키텍처` |
| `type:` | 다이어그램 타입 | `type: block` |
| `group { }` | 노드 그룹 | `group Backend { [API] [DB] }` |
| `[노드]` | 노드 정의 | `[Web Server]` |
| `->` | 단방향 연결 | `[A] -> [B]` |
| `<->` | 양방향 연결 | `[A] <-> [B]` |
| `-->` | 점선 연결 | `[A] --> [B]` |
| `: 라벨` | 엣지 라벨 | `[A] -> [B]: HTTP` |

### DSL 예시

```
title: 마이크로서비스 아키텍처
type: block

group Frontend {
    [Web App]
    [Mobile App]
}

group Backend {
    [API Gateway]
    [User Service]
    [Order Service]
}

group Data {
    [PostgreSQL]
    [Redis Cache]
}

[Web App] -> [API Gateway]
[Mobile App] -> [API Gateway]
[API Gateway] -> [User Service]
[API Gateway] -> [Order Service]
[User Service] <-> [PostgreSQL]: CRUD
[Order Service] <-> [PostgreSQL]: CRUD
[User Service] --> [Redis Cache]: 캐시
```

## Python API 사용법

### 기본 사용

```python
import sys
sys.path.insert(0, 'D:/_Obsidian/ZK-PARA/.claude/skills/make-diagram/scripts')

from draw_diagram import DiagramDrawer

# 1. DiagramDrawer 인스턴스 생성
drawer = DiagramDrawer(diagram_type='block', theme='minimal', dpi=300)

# 2. 제목 설정
drawer.set_title('시스템 아키텍처')

# 3. 그룹 추가 (선택)
drawer.add_group('frontend', 'Frontend')
drawer.add_group('backend', 'Backend')

# 4. 노드 추가
drawer.add_node('web', 'Web App', group='Frontend')
drawer.add_node('api', 'API Server', group='Backend')
drawer.add_node('db', 'Database')

# 5. 엣지 추가
drawer.add_edge('web', 'api')
drawer.add_edge('api', 'db', bidirectional=True, label='CRUD')

# 6. 저장
saved_path = drawer.save('architecture')
print(f"저장됨: {saved_path}")
```

### DSL로 생성

```python
from draw_diagram import DiagramDrawer

dsl_text = """
title: 데이터 파이프라인
type: block

group Source {
    [API]
    [File]
}

[API] -> [ETL]
[File] -> [ETL]
[ETL] --> [Storage]: 비동기
"""

drawer = DiagramDrawer(theme='clean')
drawer.parse_dsl(dsl_text)
drawer.save('pipeline')
```

### 조직도 생성

```python
from draw_diagram import DiagramDrawer

hierarchy = {
    'CEO': {
        'CTO': ['개발1팀', '개발2팀', 'QA팀'],
        'CFO': ['재무팀', '회계팀'],
        'COO': ['운영팀', '고객지원팀'],
    }
}

drawer = DiagramDrawer(theme='corporate')
drawer.set_title('회사 조직도')
drawer.create_org_chart(hierarchy)
drawer.save('org_chart')
```

### 계층 구조 생성

```python
from draw_diagram import DiagramDrawer

drawer = DiagramDrawer(theme='elegant')
drawer.set_title('자산 분류')
drawer.create_hierarchy('자산', ['유동자산', '비유동자산', '투자자산', '무형자산'])
drawer.save('asset_hierarchy')
```

### 편의 함수 사용

```python
from draw_diagram import create_block_diagram, create_org_chart, create_from_dsl

# 블록 다이어그램
create_block_diagram(
    title='서비스 구조',
    nodes=[
        {'id': 'web', 'label': 'Web', 'group': 'frontend'},
        {'id': 'api', 'label': 'API', 'group': 'backend'},
    ],
    edges=[
        {'from': 'web', 'to': 'api'},
    ],
    groups=[
        {'id': 'frontend', 'label': 'Frontend'},
        {'id': 'backend', 'label': 'Backend'},
    ],
    theme='minimal',
    filename='service_structure',
)

# 조직도
create_org_chart(
    title='팀 구성',
    hierarchy={'팀장': ['파트장A', '파트장B']},
    theme='corporate',
    filename='team_org',
)

# DSL로 생성
create_from_dsl(dsl_text, theme='clean', filename='from_dsl')
```

### 메서드 체이닝

모든 설정 메서드는 `self`를 반환하여 메서드 체이닝이 가능하다:

```python
drawer = (DiagramDrawer(theme='dark')
    .set_title('시스템 구조')
    .add_group('services', 'Services')
    .add_node('api', 'API', group='Services')
    .add_node('db', 'Database')
    .add_edge('api', 'db'))

drawer.save('chained')
```

## 출력 규격

| 항목 | 값 |
|------|-----|
| 파일 형식 | PNG |
| 해상도 | 300 DPI (기본) |
| 파일명 접두사 | `diag_` |
| 저장 경로 | `9_Attachments/images/{YYYYMM}/` |
| 파일명 예시 | `diag_architecture_20260108_143025.png` |

### 옵시디언 삽입

저장 후 출력되는 삽입 코드를 사용:

```markdown
![[images/202601/diag_architecture_20260108_143025.png]]
```

## 테마

| 테마 | 설명 | 배경색 | 노드색 |
|------|------|--------|--------|
| `minimal` | 깔끔한 미니멀 스타일 | #FFFFFF | #F8FAFC |
| `elegant` | 골드 액센트의 고급스러운 스타일 | #F7FAFC | #FFFFFF |
| `clean` | 비비드 블루 비즈니스 스타일 | #FFFFFF | #EFF6FF |
| `corporate` | 기업용 표준 블루 스타일 | #F8F9FA | #E3F2FD |
| `dark` | 어두운 배경의 모던 스타일 | #1A1A2E | #16213E |

테마 목록 조회:

```python
from utils import list_themes, get_theme

print(list_themes())  # ['minimal', 'elegant', 'clean', 'corporate', 'dark']
print(get_theme('dark'))  # 테마 색상 딕셔너리
```

## Graphviz 레퍼런스

### 기본 노드/엣지 생성

```python
import graphviz

g = graphviz.Digraph('G', format='png')
g.node('A', 'Node A')
g.node('B', 'Node B')
g.edge('A', 'B')
g.render('output', cleanup=True)
```

### 서브그래프(클러스터) 문법

클러스터는 `cluster_` 접두사가 필수:

```python
g = graphviz.Digraph()

with g.subgraph(name='cluster_0') as c:
    c.attr(label='Group 1', style='rounded', bgcolor='#F0F0F0')
    c.node('a0', 'Node A0')
    c.node('a1', 'Node A1')

with g.subgraph(name='cluster_1') as c:
    c.attr(label='Group 2', color='blue')
    c.node('b0', 'Node B0')
    c.node('b1', 'Node B1')

g.edge('a1', 'b0')
```

### 레이아웃 엔진

| 엔진 | 용도 | 특징 |
|------|------|------|
| `dot` | 계층적 다이어그램 | 방향성 그래프, TB/LR 배치 |
| `neato` | 무방향 관계도 | 스프링 모델 기반 배치 |
| `fdp` | 대규모 무방향 그래프 | 힘-방향 알고리즘 |
| `circo` | 원형 배치 | 순환 구조에 적합 |
| `twopi` | 방사형 배치 | 중심에서 바깥으로 확산 |

```python
g = graphviz.Digraph(engine='dot')  # 또는 neato, fdp, circo, twopi
```

### 양방향 엣지

```python
g.edge('A', 'B', dir='both')  # <-> 양방향 화살표
g.edge('A', 'B', dir='none')  # 화살표 없음
g.edge('A', 'B', dir='forward')  # -> 기본값
g.edge('A', 'B', dir='back')  # <-
```

### 클러스터 스타일링

```python
c.attr(
    label='그룹명',           # 클러스터 라벨
    style='rounded',          # rounded, filled, dashed, bold
    bgcolor='#E8E8E8',        # 배경색
    color='#333333',          # 테두리 색
    fontcolor='#000000',      # 라벨 글자색
    fontname='Malgun Gothic', # 폰트
    fontsize='12',            # 폰트 크기
    margin='16',              # 내부 여백
)
```

### 노드 정렬 (rank=same)

같은 레벨에 노드 배치:

```python
g = graphviz.Digraph()

with g.subgraph() as s:
    s.attr(rank='same')
    s.node('B')
    s.node('C')
    s.node('D')

g.node('A')
g.edge('A', 'B')
g.edge('A', 'C')
g.edge('A', 'D')
```

### 주요 속성

**그래프 속성:**
- `rankdir`: TB, BT, LR, RL (방향)
- `nodesep`: 같은 rank 노드 간격
- `ranksep`: rank 간 간격
- `splines`: true, false, ortho, curved (엣지 형태)
- `bgcolor`: 배경색
- `dpi`: 해상도

**노드 속성:**
- `shape`: box, ellipse, circle, diamond, record, plaintext
- `style`: filled, rounded, dashed, bold
- `fillcolor`, `color`, `fontcolor`
- `fontname`, `fontsize`
- `width`, `height`, `margin`

**엣지 속성:**
- `style`: solid, dashed, dotted, bold
- `color`, `fontcolor`
- `arrowhead`, `arrowtail`: normal, dot, diamond, box, none
- `arrowsize`: 화살표 크기 (기본 1.0)
- `label`: 엣지 라벨
- `dir`: forward, back, both, none

## 주의사항

1. **Graphviz 설치 필요**
   - Python 패키지: `pip install graphviz`
   - 시스템 설치: https://graphviz.org/download/ 에서 다운로드
   - Windows: 설치 후 PATH에 bin 폴더 추가 필요

2. **한글 폰트**
   - Windows: Malgun Gothic (기본 제공)
   - macOS: AppleGothic
   - Linux: NanumGothic (설치 필요)

3. **클러스터 이름**
   - 서브그래프가 클러스터로 표시되려면 이름이 `cluster_`로 시작해야 함

4. **레이아웃 엔진 선택**
   - 계층 구조: `dot` 사용
   - 관계도: `neato` 또는 `fdp` 사용
   - `relation` 타입은 자동으로 `neato` 사용

## 파일 구조

```
.claude/skills/make-diagram/
├── SKILL.md              # 이 문서
└── scripts/
    ├── __init__.py       # 패키지 초기화 및 export
    ├── utils.py          # 유틸리티 함수 (폰트, 테마, DSL 파싱)
    └── draw_diagram.py   # DiagramDrawer 클래스 및 편의 함수
```
