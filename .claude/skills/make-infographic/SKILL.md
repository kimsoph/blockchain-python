---
name: make-infographic
description: Matplotlib GridSpec 기반 인포그래픽 생성 스킬. 다중 차트, 메트릭 카드, 텍스트 레이아웃을 조합하여 대시보드, 비교 분석, 보고서용 인포그래픽 이미지를 생성한다. 생성된 인포그래픽은 9_Attachments/images/{YYYYMM}/ 폴더에 info_ 접두사가 붙은 PNG 파일로 저장되며, 옵시디언 문법으로 보고서에 바로 삽입할 수 있다. 한글 폰트를 자동 설정하여 한국어 레이블을 완벽히 지원한다.
---

# Make Infographic

## 버전 히스토리

### v3.1 (2026-01-02)
- **퍼센트 포인트(%p) 단위 지원**: `change_unit` 파라미터 추가
  - `%`: 상대적 변화율 (기본값, 예: +12.3%)
  - `%p`: 절대적 변화량 (퍼센트 포인트, 예: +1.81%p)
- 금융지표 등 비율 변화를 정확히 표현 가능

### v3.0 (2026-01-02)
- **미니멀 디자인 전면 개편**: 투박한 스타일에서 세련된 미니멀 스타일로 전환
- **새로운 테마 3종 추가**: minimal (기본), elegant, clean
- **MetricCard 개선**:
  - 다중 레이어 소프트 섀도우 (3단계 그림자 중첩)
  - 테두리 제거 (깔끔한 카드 외관)
  - 폰트 크기 축소 (30→26pt), 굵기 완화 (bold→semibold)
  - 심플한 변화율 화살표 (▲/▼ → ↑/↓)
- **ChartBlock 개선**:
  - 투명 배경 (배경색 제거)
  - 그리드 기본 비활성화
  - 상단/우측 테두리 제거, 하단/좌측 얇은 테두리
  - 폰트 크기 축소 (9→8pt)
- **기본 테마 변경**: 'corporate' → 'minimal'

### v2.0 (2026-01-02)
- **새로운 테마 4종 추가**: ocean, forest, sunset, modern
- **새로운 컴포넌트 5종 추가**: ProgressBar, Sparkline, Badge, Callout, ComparisonBar
- **다중 시리즈 차트 지원**: line, bar 차트에서 여러 데이터 시리즈 동시 표시
- **시각적 개선**: 그림자 효과, 그라데이션 배경, 둥근 모서리
- **자동 범례**: 다중 시리즈 차트에 범례 자동 표시
- **영역 채우기**: line 차트에 area fill 효과 추가

### v1.0 (2026-01-02)
- 초기 버전
- 6가지 레이아웃 템플릿 (dashboard, vertical, comparison, simple, metrics_grid, report)
- 컴포넌트: MetricCard, TextBlock, ChartBlock, IconMetric, Divider
- 차트 유형: line, bar, pie, donut, hbar
- 색상 테마: corporate, dark, light
- 한글 폰트 자동 설정 (Windows/macOS/Linux)
- 메서드 체이닝 지원
- 옵시디언 삽입 코드 자동 생성

## 개요

이 스킬은 Matplotlib GridSpec을 활용하여 다양한 레이아웃의 인포그래픽을 생성한다. 메트릭 카드, 차트, 텍스트 블록 등 여러 컴포넌트를 조합하여 보고서용 시각 자료를 만들 수 있다.

## 사용 시점

다음과 같은 상황에서 이 스킬을 사용한다:

- 여러 KPI를 한눈에 보여주는 대시보드가 필요할 때
- 두 항목(A vs B)을 시각적으로 비교할 때
- 보고서 표지나 요약 이미지가 필요할 때
- 차트와 메트릭을 조합한 종합 현황판이 필요할 때
- 발표 자료용 인포그래픽 이미지가 필요할 때

## 레이아웃 템플릿

| 레이아웃 | 설명 | 주요 셀 | 사용 시나리오 |
|----------|------|---------|---------------|
| `dashboard` | 대시보드 스타일 | title, metric1-4, chart_main, chart_sub1-2 | KPI + 차트 조합 |
| `vertical` | 세로 정렬 | title, metrics, chart1, chart2 | 순차적 정보 표시 |
| `comparison` | 좌우 비교 | title, left_*, right_* | A vs B 비교 분석 |
| `simple` | 단순 구조 | title, chart | 제목 + 차트 |
| `metrics_grid` | KPI 그리드 | title, metric1-6 | 6개 핵심 지표 |
| `report` | 보고서 스타일 | title, subtitle, metric1-2, chart | 정형화된 보고서 |

## 작업 흐름

### Step 1: InfographicDrawer 초기화

```python
from draw_infographic import InfographicDrawer

drawer = InfographicDrawer(
    layout='dashboard',    # 레이아웃 선택
    theme='minimal',       # 색상 테마 (v3.0 기본값)
)
```

### Step 2: 컴포넌트 추가 (메서드 체이닝)

```python
drawer.set_title("2025년 상반기 실적 현황")

drawer.add_metric('metric1', value=1234567890, label='총매출', unit='원', change=12.5)
drawer.add_metric('metric2', value=856, label='신규 고객', change=8.3)
drawer.add_metric('metric3', value=92.5, label='고객 만족도', unit='%', change=-1.2)
drawer.add_metric('metric4', value=45, label='신규 프로젝트', change=15.0)

drawer.add_chart(
    'chart_main',
    chart_type='line',
    data={'labels': ['1월', '2월', '3월'], 'values': [120, 135, 142]},
    title='월별 매출 추이'
)
```

### Step 3: 저장

```python
path = drawer.save('my_infographic')
# [OK] 인포그래픽 저장 완료: .../9_Attachments/images/202601/info_my_infographic_20260106_143025.png
# [INFO] 옵시디언 삽입: ![[images/202601/info_my_infographic_20260106_143025.png]]
```

### Step 4: 보고서 삽입

```markdown
![[images/202601/info_my_infographic_20260106_143025.png]]
```

## 컴포넌트 상세

### MetricCard (메트릭 카드)

KPI/숫자를 강조하여 표시한다.

```python
drawer.add_metric(
    cell_name='metric1',
    value=1234567890,       # 메인 값
    label='총매출',          # 레이블
    unit='원',              # 단위
    change=12.5,            # 변화율 또는 변화량
    change_label='전월 대비', # 변화율 설명
    change_unit='%',        # v3.1: '%' 또는 '%p' (퍼센트 포인트)
    format_value=True,      # 숫자 자동 포맷팅 (1234 → 1,234)
)
```

**change_unit 옵션 (v3.1)**:
| 값 | 의미 | 사용 시나리오 | 예시 |
|-----|------|---------------|------|
| `%` (기본) | 상대적 변화율 | 매출, 고객수 증감 | `+12.5%`, `-3.2%` |
| `%p` | 퍼센트 포인트 | 금융지표 (연체율, BIS비율) | `+1.81%p`, `-0.35%p` |

```python
# 금융지표 예시: 연체율 0.80% → 0.45% (절대 변화: -0.35%p)
drawer.add_metric('metric1', value=0.45, label='연체율', unit='%',
                  change=-0.35, change_unit='%p', change_label='현재 0.80%')
```

**숫자 포맷팅 규칙:**
- 1,234,567,890 → 12.3억
- 12,345 → 1.2만
- 92.5 → 92.5

### ChartBlock (차트 블록)

다양한 유형의 차트를 렌더링한다.

```python
# 선 그래프
drawer.add_chart(
    'chart_main',
    chart_type='line',
    data={'labels': ['1월', '2월', '3월'], 'values': [100, 120, 140]},
    title='월별 추이'
)

# 막대 그래프
drawer.add_chart(
    'chart_sub1',
    chart_type='bar',
    data={'labels': ['A팀', 'B팀', 'C팀'], 'values': [85, 72, 95]},
    title='팀별 실적'
)

# 파이 차트
drawer.add_chart(
    'chart_sub2',
    chart_type='pie',
    data={'labels': ['제품A', '제품B', '기타'], 'values': [45, 35, 20]},
    title='제품별 비중'
)

# 도넛 차트
drawer.add_chart(
    'chart_main',
    chart_type='donut',
    data={'labels': ['완료', '진행중', '대기'], 'values': [60, 25, 15]},
    title='프로젝트 현황'
)

# 가로 막대 그래프
drawer.add_chart(
    'chart_main',
    chart_type='hbar',
    data={'labels': ['항목A', '항목B', '항목C'], 'values': [150, 120, 90]},
    title='항목별 비교'
)
```

### TextBlock (텍스트 블록)

제목, 부제목, 설명 텍스트를 표시한다.

```python
drawer.set_title("메인 제목")
drawer.set_subtitle("부제목 텍스트")
drawer.add_text('left_title', 'A사', style='subtitle')
drawer.add_text('caption', '* 데이터 기준일: 2025-12-31', style='caption', align='right')
```

**스타일 옵션:**
- `title`: 큰 굵은 글씨 (24pt)
- `subtitle`: 중간 크기 (16pt)
- `body`: 본문 (12pt)
- `caption`: 작은 글씨 (10pt)

### IconMetric (아이콘 메트릭)

아이콘과 숫자를 함께 표시한다.

```python
drawer.add_icon_metric('metric1', icon='user', value=1250, label='총 사용자')
drawer.add_icon_metric('metric2', icon='chart', value='+15%', label='성장률')
drawer.add_icon_metric('metric3', icon='💰', value=8.5, label='매출(억)')
```

**사용 가능한 아이콘:**
`up`, `down`, `check`, `star`, `circle`, `diamond`, `user`, `chart`, `money`, `building`, `calendar`, `users`, `clock`, `trophy`, `fire`, `rocket`, `lightning`, `growth`, `decline`

### ProgressBar (v2.0 추가)

진행률/달성률을 시각적으로 표시한다.

```python
drawer.add_progress_bar(
    cell_name='progress1',
    value=75,           # 현재 값
    max_value=100,      # 최대 값
    label='목표 달성률',
    show_percent=True,  # 퍼센트 표시
)
```

### Sparkline (v2.0 추가)

작은 추세선 차트 (미니 차트)를 표시한다.

```python
drawer.add_sparkline(
    cell_name='spark1',
    values=[10, 15, 12, 18, 25, 22, 28],  # 데이터
    label='주간 추이',
    show_endpoints=True,  # 시작/끝 점 강조
    fill=True,            # 영역 채우기
)
```

### Badge (v2.0 추가)

상태나 카테고리를 나타내는 배지를 표시한다.

```python
drawer.add_badge(
    cell_name='badge1',
    text='완료',
    badge_type='success',  # primary, success, warning, danger, info
    size='medium',         # small, medium, large
)
```

### Callout (v2.0 추가)

강조 박스/알림 영역을 표시한다.

```python
drawer.add_callout(
    cell_name='callout1',
    text='중요: 목표 대비 120% 달성하였습니다.',
    title='알림',
    callout_type='info',  # info, success, warning, danger
)
```

### ComparisonBar (v2.0 추가)

두 값을 좌우로 비교하는 막대를 표시한다.

```python
drawer.add_comparison_bar(
    cell_name='compare1',
    left_value=20.7,
    right_value=23.7,
    left_label='용산구',
    right_label='과천시',
    center_label='평균 매매가격(억원)',
)
```

## 다중 시리즈 차트 (v2.0 추가)

line, bar 차트에서 여러 데이터 시리즈를 동시에 표시할 수 있다.

```python
# 다중 시리즈 선 그래프
drawer.add_chart(
    'chart_main',
    chart_type='line',
    data={
        'labels': ['1월', '2월', '3월', '4월', '5월', '6월'],
        'series': [
            {'name': 'A팀', 'values': [120, 135, 142, 155, 168, 180]},
            {'name': 'B팀', 'values': [100, 110, 125, 140, 150, 165]},
        ],
    },
    title='팀별 월별 매출 추이'
)

# 다중 시리즈 막대 그래프
drawer.add_chart(
    'chart_sub1',
    chart_type='bar',
    data={
        'labels': ['Q1', 'Q2', 'Q3', 'Q4'],
        'series': [
            {'name': '매출', 'values': [100, 120, 135, 150]},
            {'name': '비용', 'values': [80, 90, 100, 110]},
        ],
    },
    title='분기별 매출 vs 비용'
)
```

**참고**: 다중 시리즈 차트는 자동으로 범례를 표시하며, 각 시리즈별로 다른 색상이 적용된다.

## 색상 테마

10가지 색상 테마를 지원한다. `list_themes()`로 확인 가능.

### minimal (v3.0 기본)
미니멀 모노톤 (가장 세련됨, 순백색 배경 + 단일 액센트)
- 메인: `#1A1A2E` (거의 검정)
- 배경: `#FFFFFF` (순백색)
- 카드: `#FAFBFC` (미세한 그레이)
- 그림자: `rgba(0,0,0,0.03)` (매우 연함)

### elegant (v3.0 추가)
세련된 그레이 톤 + 골드 액센트 (고급스러움)
- 메인: `#2D3748` (챠콜 그레이)
- 액센트: `#B7950B` (골드)
- 배경: `#F7FAFC` (매우 연한 그레이)

### clean (v3.0 추가)
깔끔한 블루 톤 (비즈니스 프레젠테이션용)
- 메인: `#2563EB` (비비드 블루)
- 배경: `#FFFFFF` (순백색)
- 그림자: `rgba(37,99,235,0.04)` (블루 틴트)

### corporate
비즈니스/기업용 파란색 톤

| 색상 | 용도 |
|------|------|
| `#2E86AB` | 메인 (파랑) |
| `#A23B72` | 악센트 (마젠타) |
| `#28A745` | 상승/긍정 (녹색) |
| `#DC3545` | 하락/경고 (빨강) |
| `#343A40` | 텍스트 (어두운 회색) |
| `#F8F9FA` | 배경 (밝은 회색) |

### dark
어두운 배경 테마 (데이터 시각화, 대시보드)

### light
부드러운 파스텔 톤

### ocean (v2.0 추가)
시원한 바다색 톤 (청량감, 신뢰감)
- 메인: `#0077B6` (딥 블루)
- 배경: `#CAF0F8` (연한 하늘색)

### forest (v2.0 추가)
자연 친화적 녹색 톤 (ESG, 친환경)
- 메인: `#2D6A4F` (짙은 녹색)
- 배경: `#D8F3DC` (연한 녹색)

### sunset (v2.0 추가)
따뜻한 석양 톤 (열정, 에너지)
- 메인: `#F77F00` (오렌지)
- 배경: `#FFF3E0` (크림색)

### modern (v2.0 추가)
세련된 보라색 톤 (현대적, 창의적)
- 메인: `#5E60CE` (보라)
- 배경: `#F3E8FF` (연한 보라)

```python
# 테마 목록 확인
from utils import list_themes
print(list_themes())  # ['minimal', 'elegant', 'clean', 'corporate', 'dark', 'light', 'ocean', 'forest', 'sunset', 'modern']

# 테마 적용
drawer = InfographicDrawer(layout='dashboard', theme='elegant')
```

## 출력 규격

| 항목 | 값 |
|------|-----|
| 파일 형식 | PNG |
| 해상도 | 300 DPI |
| 기본 크기 | 레이아웃별 상이 (12x8 ~ 14x10 인치) |
| 저장 위치 | `9_Attachments/images/{YYYYMM}/` |
| 파일명 패턴 | `info_{filename}_{YYYYMMDD_HHMMSS}.png` |

## 편의 함수

### create_dashboard()

대시보드를 빠르게 생성한다.

```python
from draw_infographic import create_dashboard

path = create_dashboard(
    title="2025년 실적 현황",
    metrics=[
        {'value': 1234567890, 'label': '총매출', 'unit': '원', 'change': 12.5},
        {'value': 856, 'label': '신규 고객', 'change': 8.3},
        {'value': 92.5, 'label': '만족도', 'unit': '%', 'change': -1.2},
        {'value': 45, 'label': '프로젝트', 'change': 15.0},
    ],
    main_chart={
        'type': 'line',
        'title': '월별 추이',
        'data': {'labels': ['1월', '2월', '3월'], 'values': [100, 120, 140]},
    },
    sub_charts=[
        {'type': 'bar', 'title': '팀별', 'data': {...}},
        {'type': 'pie', 'title': '제품별', 'data': {...}},
    ],
    filename='dashboard',
)
```

### create_comparison()

좌우 비교 인포그래픽을 빠르게 생성한다.

```python
from draw_infographic import create_comparison

path = create_comparison(
    title="A사 vs B사 비교",
    left={
        'title': 'A사',
        'metric': {'value': 1200, 'label': '매출', 'unit': '억', 'change': 5.2},
        'chart': {'type': 'line', 'data': {...}},
    },
    right={
        'title': 'B사',
        'metric': {'value': 980, 'label': '매출', 'unit': '억', 'change': 12.1},
        'chart': {'type': 'line', 'data': {...}},
    },
    filename='comparison',
)
```

## 사용 예시

### 예시 1: 대시보드 인포그래픽

```python
from draw_infographic import InfographicDrawer

drawer = InfographicDrawer(layout='dashboard')

drawer.set_title("IBK기업은행 2025년 상반기 현황")

drawer.add_metric('metric1', value=3850000, label='총자산', unit='억원', change=5.2)
drawer.add_metric('metric2', value=28500, label='당기순이익', unit='억원', change=12.3)
drawer.add_metric('metric3', value=14.8, label='BIS비율', unit='%', change=0.5)
drawer.add_metric('metric4', value=0.42, label='연체율', unit='%', change=-0.08)

drawer.add_chart(
    'chart_main',
    chart_type='line',
    data={
        'labels': ['2020', '2021', '2022', '2023', '2024', '2025H1'],
        'values': [320, 345, 360, 375, 385, 385],
    },
    title='총자산 추이 (조원)'
)

drawer.add_chart(
    'chart_sub1',
    chart_type='bar',
    data={
        'labels': ['국민', '신한', '하나', 'IBK'],
        'values': [420, 510, 390, 385],
    },
    title='시중은행 총자산 비교'
)

drawer.add_chart(
    'chart_sub2',
    chart_type='donut',
    data={
        'labels': ['기업대출', '가계대출', '기타'],
        'values': [65, 25, 10],
    },
    title='대출 포트폴리오'
)

drawer.save('ibk_dashboard')
```

### 예시 2: 비교 분석 인포그래픽

```python
drawer = InfographicDrawer(layout='comparison')

drawer.set_title("용산구 vs 과천시 아파트 가격 비교 (2025)")

drawer.add_text('left_title', '용산구', style='subtitle')
drawer.add_metric('left_metric', value=20.7, label='평균 매매가', unit='억원', change=-10.2)
drawer.add_chart(
    'left_chart',
    chart_type='line',
    data={
        'labels': ['1월', '4월', '7월', '10월', '12월'],
        'values': [23.1, 21.4, 21.5, 21.1, 20.7],
    },
    title='월별 가격 추이'
)

drawer.add_text('right_title', '과천시', style='subtitle')
drawer.add_metric('right_metric', value=23.7, label='평균 매매가', unit='억원', change=32.0)
drawer.add_chart(
    'right_chart',
    chart_type='line',
    data={
        'labels': ['1월', '4월', '7월', '10월', '12월'],
        'values': [17.9, 19.5, 20.0, 24.3, 23.7],
    },
    title='월별 가격 추이'
)

drawer.save('yongsan_vs_gwacheon')
```

### 예시 3: KPI 그리드

```python
drawer = InfographicDrawer(layout='metrics_grid')

drawer.set_title("핵심 성과 지표 (KPI) 현황")

kpis = [
    (385000000000000, '총자산', '원', 5.2),
    (2850000000000, '당기순이익', '원', 12.3),
    (14.8, 'BIS비율', '%', 0.5),
    (0.42, '연체율', '%', -0.08),
    (15230, '직원수', '명', -1.2),
    (623, '영업점수', '개', -2.1),
]

for i, (value, label, unit, change) in enumerate(kpis, 1):
    drawer.add_metric(f'metric{i}', value=value, label=label, unit=unit, change=change)

drawer.save('kpi_grid')
```

## 옵시디언 보고서 삽입 가이드

### 기본 삽입

```markdown
## 2025년 상반기 현황

아래 인포그래픽은 주요 경영지표 현황을 보여준다.

![[images/202601/info_ibk_dashboard_20260106_143025.png]]

상반기 총자산은 전년 대비 5.2% 증가했으며...
```

### 크기 조정

```markdown
![[images/202601/info_infographic.png|600]]   <!-- 너비 600px -->
![[images/202601/info_infographic.png|800]]   <!-- 너비 800px -->
```

### 캡션 추가

```markdown
![[images/202601/info_ibk_dashboard.png|700]]
*그림 1: IBK기업은행 2025년 상반기 경영현황*
```

## 참고 자료

### scripts 폴더 구조

```
scripts/
├── __init__.py         # 패키지 초기화
├── utils.py            # 유틸리티 (폰트, 색상, 경로)
├── components.py       # 컴포넌트 클래스
├── layouts.py          # 레이아웃 템플릿
└── draw_infographic.py # 메인 클래스
```

### 주요 클래스

| 클래스 | 파일 | 설명 |
|--------|------|------|
| `InfographicDrawer` | draw_infographic.py | 메인 클래스 |
| `MetricCard` | components.py | 메트릭 카드 |
| `TextBlock` | components.py | 텍스트 블록 |
| `ChartBlock` | components.py | 차트 블록 |
| `IconMetric` | components.py | 아이콘 메트릭 |
| `LayoutBuilder` | layouts.py | 레이아웃 생성기 |

## 주의사항

1. **의존성**:
   - matplotlib, numpy 패키지 필요
   - 설치: `pip install matplotlib numpy`

2. **한글 폰트**:
   - 시스템에 한글 폰트가 설치되어 있어야 함
   - Windows: 맑은 고딕 (기본 설치됨)
   - macOS: AppleGothic (기본 설치됨)
   - Linux: `apt install fonts-nanum` 필요할 수 있음

3. **레이아웃 셀 이름**:
   - 레이아웃별로 사용 가능한 셀 이름이 다름
   - `drawer.get_cell_names()`로 확인 가능

4. **메모리**:
   - `save()` 호출 후 자동으로 메모리 해제
   - 대량 생성 시에도 안전함

5. **파일명**:
   - 특수문자, 공백 사용 자제
   - 영문/숫자/언더스코어 권장

## 문제 해결

### 한글이 깨지는 경우

**증상**: 인포그래픽에서 한글이 네모(□)로 표시됨

**해결**:
1. 한글 폰트 설치 확인
2. matplotlib 폰트 캐시 삭제:
   ```python
   import matplotlib
   print(matplotlib.get_cachedir())
   # 해당 디렉토리의 *.json 파일 삭제
   ```
3. 스크립트 재실행

### 레이아웃 셀을 찾을 수 없는 경우

**증상**: "Unknown cell name" 오류

**해결**:
1. 레이아웃에서 지원하는 셀 이름 확인:
   ```python
   print(drawer.get_cell_names())
   ```
2. 올바른 셀 이름 사용

### 차트가 비어있는 경우

**증상**: 차트 영역이 빈 상태

**해결**:
1. data 딕셔너리에 'labels'와 'values' 키가 있는지 확인
2. values 리스트가 비어있지 않은지 확인

## 관련 스킬

- `make-chart`: 단일 차트 생성 (선, 막대, 파이, 복합)
- `make-image`: AI 기반 이미지 생성 (Gemini API)
