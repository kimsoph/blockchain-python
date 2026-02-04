# -*- coding: utf-8 -*-
---
name: make-geoviz
description: 한국 행정구역 기반 공간 데이터 시각화 스킬. 시도/시군구 레벨에서 Choropleth, Bubble Map, Marker Map을 생성하여 PNG 파일로 저장한다.
version: 1.0.0
---

# make-geoviz 스킬

## Purpose

한국 행정구역(시도/시군구) 기반 공간 데이터를 시각화합니다.

**핵심 기능:**
1. **Choropleth**: 지역별 데이터를 색상 그라데이션으로 표현
2. **Bubble Map**: 지역 중심에 크기가 다른 원으로 값 표현
3. **Marker Map**: 특정 좌표에 마커/레이블 표시
4. **KOSIS 연동**: api-kosis 스킬 데이터 직접 변환
5. **마크다운 테이블 파싱**: 테이블 데이터 자동 변환

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 시도별/시군구별 통계 데이터를 지도로 시각화할 때
- KOSIS에서 조회한 지역 통계를 지도에 표시할 때
- 지역별 비교 분석 결과를 시각적으로 표현할 때

트리거 예시:
- "시도별 인구 지도 만들어줘"
- "이 데이터로 choropleth 지도 생성해줘"
- "KOSIS 데이터를 지도로 시각화해줘"
- "시군구별 통계를 버블 맵으로 보여줘"

## Installation

### 필수 의존성
```bash
pip install geopandas matplotlib numpy shapely pyproj
```

### GeoJSON 데이터
스킬에 내장되어 있음 (2025년 4월 기준):
- `data/korea_sido.geojson`: 17개 시도 경계
- `data/korea_sigungu.geojson`: 252개 시군구 경계

## Quick Start

### 1. 기본 Choropleth
```python
from draw_map import MapDrawer

drawer = MapDrawer(level='sido', theme='blues')
drawer.set_title('시도별 인구 현황')
drawer.choropleth({
    '서울': 970,
    '경기': 1350,
    '부산': 340,
    '인천': 300,
    # ...
}, value_label='인구(만명)')
drawer.save('sido_population')
```

### 2. KOSIS 데이터 연동
```python
from scripts.kosis_api import KosisAPI
from draw_map import MapDrawer

# KOSIS 데이터 조회
api = KosisAPI()
data = api.get_stat_data(
    org_id='101',
    tbl_id='DT_1IN1502',
    prd_se='M',
    start_prd_de='202412',
    end_prd_de='202412'
)

# 지도 생성
drawer = MapDrawer(level='sido', theme='blues')
drawer.set_title('시도별 인구 현황')
drawer.from_kosis(data, value_column='DT', region_column='C1', value_label='인구(명)')
drawer.save('sido_population_kosis')
```

### 3. 마크다운 테이블 파싱
```python
table = """
| 지역 | 인구 |
|------|------|
| 서울 | 970 |
| 부산 | 340 |
| 경기 | 1350 |
"""

drawer = MapDrawer(level='sido')
drawer.set_title('시도별 인구')
drawer.from_markdown_table(table, value_label='인구(만명)')
drawer.save('table_map')
```

## API Reference

### MapDrawer 클래스

```python
class MapDrawer:
    def __init__(
        self,
        level: str = 'sido',      # 'sido' 또는 'sigungu'
        theme: str = 'blues',     # 색상 테마
        figsize: Tuple = (12, 10),
        dpi: int = 300,
        output_dir: str = None
    )
```

### 메서드

| 메서드 | 설명 |
|--------|------|
| `set_title(title, subtitle)` | 제목/부제목 설정 |
| `choropleth(data, ...)` | Choropleth 레이어 추가 |
| `bubble(data, ...)` | 버블 맵 레이어 추가 |
| `markers(points, ...)` | 마커 레이어 추가 |
| `from_kosis(kosis_data, ...)` | KOSIS 데이터 변환 |
| `from_markdown_table(table, ...)` | 마크다운 테이블 파싱 |
| `filter_sido(sido_codes)` | 특정 시도만 표시 |
| `save(filename)` | PNG 파일로 저장 |

### choropleth() 파라미터

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `data` | Dict[str, float] | {지역키: 값} |
| `value_label` | str | 범례 레이블 |
| `show_labels` | bool | 지역명 표시 |
| `show_values` | bool | 값 표시 |
| `vmin`, `vmax` | float | 값 범위 지정 |
| `fontsize` | int | 레이블 폰트 크기 (None이면 지역 수 기반 자동 계산) |

### bubble() 파라미터

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `data` | Dict[str, float] | {지역키: 값} |
| `color` | str | 버블 색상 |
| `alpha` | float | 투명도 (0-1) |
| `size_range` | Tuple | 버블 크기 범위 |
| `fontsize` | int | 레이블 폰트 크기 (None이면 지역 수 기반 자동 계산) |

### markers() 파라미터

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `points` | List[Dict] | [{'x': lon, 'y': lat, 'label': '이름', 'value': 값}, ...] |
| `color` | str | 마커 색상 |
| `size` | int | 마커 크기 |
| `marker` | str | 마커 모양 ('o', '^', 's', '*' 등) |
| `show_labels` | bool | 레이블 표시 여부 |
| `fontsize` | int | 레이블 폰트 크기 (None이면 마커 수 기반 자동 계산) |

## 폰트 크기 자동 계산

지역 수에 따라 폰트 크기가 자동으로 계산됩니다:

| 지역 수 | 폰트 크기 | 대표 케이스 |
|---------|----------|-------------|
| 1-10 | 12 | 특정 시도 1-2개 |
| 11-17 | 10 | 시도 전체 (17개) |
| 18-30 | 9 | 서울 25개 구 |
| 31-50 | 8 | 경기도 시군구 |
| 51-100 | 7 | 수도권 전체 |
| 101-150 | 6 | 영남+수도권 |
| 151+ | 5 | 전국 시군구 |

`fontsize` 파라미터를 명시적으로 지정하면 자동 계산 대신 지정값을 사용합니다.

## 지역 키 형식

데이터의 키는 다음 형식을 지원합니다:

| 형식 | 예시 | 설명 |
|------|------|------|
| 코드 | `'11'`, `'26'` | GeoJSON 코드 |
| 풀네임 | `'서울특별시'` | 전체 이름 |
| 축약명 | `'서울'`, `'부산'` | 짧은 이름 |

## 색상 테마

| 테마 | 설명 |
|------|------|
| `blues` | 파란색 계열 (기본) |
| `reds` | 빨간색 계열 |
| `greens` | 초록색 계열 |
| `oranges` | 주황색 계열 |
| `purples` | 보라색 계열 |
| `viridis` | 다색 (저-고) |
| `coolwarm` | 파랑-빨강 (양극) |
| `rdylgn` | 빨강-노랑-초록 |

## 출력 규격

| 항목 | 값 |
|------|-----|
| 파일 형식 | PNG |
| 해상도 | 300 DPI |
| 저장 위치 | `9_Attachments/images/{YYYYMM}/` |
| 파일명 패턴 | `geo_{filename}_{timestamp}.png` |

## 시도 코드 매핑

| GeoJSON | 이름 | KOSIS |
|---------|------|-------|
| 11 | 서울특별시 | 11 |
| 26 | 부산광역시 | 21 |
| 27 | 대구광역시 | 22 |
| 28 | 인천광역시 | 23 |
| 29 | 광주광역시 | 24 |
| 30 | 대전광역시 | 25 |
| 31 | 울산광역시 | 26 |
| 36 | 세종특별자치시 | 29 |
| 41 | 경기도 | 31 |
| 43 | 충청북도 | 33 |
| 44 | 충청남도 | 34 |
| 46 | 전라남도 | 36 |
| 47 | 경상북도 | 37 |
| 48 | 경상남도 | 38 |
| 50 | 제주특별자치도 | 39 |
| 51 | 강원특별자치도 | 32 |
| 52 | 전북특별자치도 | 35 |

## Examples

### Example 1: 시도별 인구 Choropleth
```python
drawer = MapDrawer(level='sido', theme='blues')
drawer.set_title('시도별 인구 현황', '(2024년 12월 기준)')
drawer.choropleth(
    {
        '서울': 9700000,
        '부산': 3400000,
        '대구': 2400000,
        '인천': 3000000,
        '광주': 1450000,
        '대전': 1500000,
        '울산': 1150000,
        '세종': 350000,
        '경기': 13500000,
        '강원': 1550000,
        '충북': 1600000,
        '충남': 2150000,
        '전북': 1800000,
        '전남': 1850000,
        '경북': 2650000,
        '경남': 3350000,
        '제주': 680000
    },
    value_label='인구(명)',
    show_labels=True,
    show_values=False
)
drawer.save('sido_population')
```

### Example 2: 시군구 버블 맵 (수도권)
```python
drawer = MapDrawer(level='sigungu', theme='greens')
drawer.filter_sido(['서울', '경기', '인천'])
drawer.set_title('수도권 시군구별 아파트 거래량')
drawer.bubble(
    {
        '11110': 500,  # 종로구
        '11140': 800,  # 중구
        '11680': 1200,  # 강남구
        # ...
    },
    color='#3498DB',
    alpha=0.7,
    show_values=True
)
drawer.save('seoul_apartment_bubble')
```

### Example 3: 복합 레이어
```python
drawer = MapDrawer(level='sido')
drawer.set_title('시도별 경제 지표')

# Choropleth 배경
drawer.choropleth(
    {'서울': 100, '경기': 90, '부산': 70, ...},
    value_label='GRDP 지수',
    show_labels=False
)

# 주요 도시 마커
drawer.markers([
    {'x': 126.978, 'y': 37.567, 'label': '서울', 'value': 450},
    {'x': 129.076, 'y': 35.180, 'label': '부산', 'value': 95},
])

drawer.save('composite_map')
```

## 폴더 구조

```
.claude/skills/make-geoviz/
├── SKILL.md
├── requirements.txt
├── data/
│   ├── korea_sido.geojson      # 17개 시도 경계
│   ├── korea_sigungu.geojson   # 252개 시군구 경계
│   ├── korea_raw.geojson       # 원본 행정동 데이터
│   └── region_codes.json       # 코드 매핑
└── scripts/
    ├── __init__.py
    ├── utils.py                # 유틸리티
    ├── geo_utils.py            # 지리 데이터 처리
    └── draw_map.py             # MapDrawer 클래스
```

## Korean Encoding

모든 파일은 UTF-8 인코딩을 사용합니다.

```python
# 파일 읽기/쓰기
with open(file, 'r', encoding='utf-8') as f:
    data = f.read()
```

## Path Convention

경로 표시 시 `>>` 사용:
- 스크립트: `.claude >> skills >> make-geoviz >> scripts >> draw_map.py`
- 데이터: `.claude >> skills >> make-geoviz >> data >> korea_sido.geojson`

## Limitations

- 행정구역 레벨: 시도(17개), 시군구(252개)만 지원
- 읍면동 레벨은 미지원 (원본 데이터는 있으나 처리 시간 문제)
- 출력 형식: PNG만 지원 (HTML 인터랙티브 미지원)
- 지도 투영: WGS84 (EPSG:4326)

## Data Source

GeoJSON 데이터 출처:
- [vuski/admdongkor](https://github.com/vuski/admdongkor) (ver20250401)
- 대한민국 행정구역(법정동) 경계
- WGS84 좌표계, UTF-8 인코딩

## See Also

- `api-kosis` 스킬: KOSIS 국가통계 조회
- `make-chart` 스킬: 일반 차트 생성
- `make-infographic` 스킬: 인포그래픽 생성
