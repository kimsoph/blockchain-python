---
name: make-gantt_chart
description: Matplotlib 기반 간트차트 생성 스킬. DSL 또는 Python API로 프로젝트 일정, 태스크 진행률, 마일스톤을 시각화하여 PNG 이미지로 저장한다.
---

# make-gantt_chart 스킬

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.0 | 2026-01-12 | 최초 릴리즈: DSL/Python API, 5개 테마, 진행률, 마일스톤, 순차 인덱스 모드 |

## 개요

Matplotlib 라이브러리를 사용하여 간트차트를 생성하는 스킬입니다.

- **DSL 문법** 또는 **Python API** 두 가지 방식 지원
- 진행률 표시 (색상 오버레이)
- 마일스톤 마커 (다이아몬드)
- 그룹/카테고리 지원
- 오늘 날짜 라인 표시
- 5가지 테마 (minimal, elegant, clean, corporate, dark)
- 순차 인덱스 모드 (날짜 없이 우선순위/순서 표현)
- 메서드 체이닝 지원
- 한글 완벽 지원 (Malgun Gothic)

## 사용 시점

다음 상황에서 이 스킬을 사용합니다:

- 프로젝트 일정 시각화
- 업무 진행 현황 대시보드
- 마일스톤 및 데드라인 표시
- 연설문/정책 우선순위 표현 (순차 모드)
- 보고서/문서에 삽입할 일정 차트 생성

## 설치

```bash
pip install matplotlib numpy
```

또는 requirements.txt 사용:

```bash
pip install -r .claude/skills/make-gantt_chart/requirements.txt
```

## DSL 문법 가이드

### 기본 문법

```
title: 차트 제목

## 그룹명 (선택)
태스크명: 시작일 ~ 종료일 [진행률%]

[M] 마일스톤명: 날짜
```

### 날짜 형식

| 형식 | 예시 |
|------|------|
| YYYY-MM-DD | 2026-01-15 |
| YYYY/MM/DD | 2026/01/15 |
| YYYYMMDD | 20260115 |

### DSL 예제 (날짜 모드)

```
title: 프로젝트 일정

## 1단계
기획: 2026-01-01 ~ 2026-01-05 [100%]
개발: 2026-01-06 ~ 2026-01-20 [60%]

## 2단계
테스트: 2026-01-21 ~ 2026-01-28 [0%]

[M] 킥오프: 2026-01-01
[M] 릴리즈: 2026-01-28
```

### DSL 예제 (순차 모드)

날짜 없이 태스크를 나열하면 자동으로 순차 인덱스 모드가 됩니다.
X축이 날짜 대신 순차 인덱스 (1, 2, 3...)로 표시됩니다.

```
title: 정책 우선순위

첫째: 국민주권 강화 [duration=3]
둘째: 성장동력 창출 [duration=5]
셋째: 균형발전 [duration=4]
```

## Python API 사용법

### 기본 사용 (날짜 모드)

```python
from scripts import GanttDrawer

drawer = GanttDrawer(theme='minimal')
drawer.set_title('프로젝트 일정')
drawer.add_task('기획', '2026-01-01', '2026-01-05', progress=100)
drawer.add_task('개발', '2026-01-06', '2026-01-20', progress=60)
drawer.add_task('테스트', '2026-01-21', '2026-01-28', progress=0)
drawer.add_milestone('킥오프', '2026-01-01')
drawer.save('project_schedule')
# Output: gantt_project_schedule_20260112_143025.png
```

### 메서드 체이닝

```python
from scripts import GanttDrawer

(GanttDrawer(theme='elegant')
    .set_title('분기별 계획')
    .add_task('Q1 기획', '2026-01-01', '2026-03-31', progress=100)
    .add_task('Q2 개발', '2026-04-01', '2026-06-30', progress=50)
    .add_task('Q3 테스트', '2026-07-01', '2026-09-30', progress=0)
    .add_milestone('중간점검', '2026-06-15')
    .save('quarterly_plan'))
```

### 순차 인덱스 모드

날짜 없이 duration만 지정하면 X축이 순차 인덱스로 표시됩니다.

```python
from scripts import GanttDrawer

drawer = GanttDrawer(theme='clean')
drawer.set_title('정책 우선순위')
drawer.add_task('첫째: 국민주권 강화', duration=3)
drawer.add_task('둘째: 성장동력 창출', duration=5)
drawer.add_task('셋째: 균형발전', duration=4)
drawer.save('policy_priority')
# X축: 0, 1, 2, 3... (날짜 대신 인덱스)
```

### DSL 텍스트로 생성

```python
from scripts import GanttDrawer, create_gantt

# 방법 1: GanttDrawer 사용
drawer = GanttDrawer(theme='corporate')
drawer.parse_dsl_text('''
    title: 로그인 프로젝트

    기획: 2026-01-01 ~ 2026-01-05 [100%]
    개발: 2026-01-06 ~ 2026-01-20 [60%]
    테스트: 2026-01-21 ~ 2026-01-28 [0%]

    [M] 킥오프: 2026-01-01
''')
drawer.save('login_project')

# 방법 2: 편의 함수 사용
path = create_gantt(dsl_text, theme='minimal', filename='my_gantt')
```

## GanttDrawer 클래스 API

### 생성자

```python
GanttDrawer(
    theme='minimal',    # 테마: minimal, elegant, clean, corporate, dark
    dpi=300,            # 해상도
    output_dir=None,    # 출력 경로 (기본: 9_Attachments/images/{YYYYMM}/)
    show_today=True,    # 오늘 날짜 라인 표시 여부
    figsize=None        # 그림 크기 (width, height) 인치 단위
)
```

### 설정 메서드

| 메서드 | 설명 | 반환 |
|--------|------|------|
| `set_title(title)` | 제목 설정 | self |
| `parse_dsl_text(dsl_text)` | DSL 텍스트 파싱 | self |
| `clear()` | 모든 데이터 초기화 | self |

### 태스크/마일스톤 추가 메서드

| 메서드 | 설명 | 반환 |
|--------|------|------|
| `add_task(name, start, end, progress, group, duration)` | 태스크 추가 | self |
| `add_milestone(name, date)` | 마일스톤 추가 | self |

#### add_task() 파라미터

| 파라미터 | 타입 | 설명 | 기본값 |
|----------|------|------|--------|
| name | str | 태스크 이름 | (필수) |
| start | str/datetime/None | 시작일 | None |
| end | str/datetime/None | 종료일 | None |
| progress | int | 진행률 (0-100) | 0 |
| group | str | 그룹/카테고리 | None |
| duration | int | 순차 모드 기간 | 1 |

### 출력 메서드

| 메서드 | 설명 | 반환 |
|--------|------|------|
| `render()` | matplotlib Figure 객체 반환 | Figure |
| `save(filename)` | PNG 파일 저장, 경로 반환 | str |
| `show()` | 화면에 표시 | None |

## CLI 사용법

```bash
# DSL 파일로 간트차트 생성
python -m scripts.draw_gantt input.txt -o project_schedule

# 테마 지정
python -m scripts.draw_gantt input.txt -t corporate -o schedule

# 오늘 날짜 라인 숨기기
python -m scripts.draw_gantt input.txt --no-today -o schedule

# 해상도 지정
python -m scripts.draw_gantt input.txt --dpi 150 -o schedule

# stdin에서 읽기
echo "title: 테스트\n기획: 2026-01-01 ~ 2026-01-05" | python -m scripts.draw_gantt -o test
```

### CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `input` | DSL 파일 경로 (없으면 stdin) | - |
| `-o, --output` | 출력 파일명 | gantt |
| `-t, --theme` | 테마 | minimal |
| `--no-today` | 오늘 날짜 라인 숨기기 | False |
| `--dpi` | 출력 해상도 | 300 |

## 출력 규격

| 항목 | 값 |
|------|-----|
| 포맷 | PNG |
| 해상도 | 300 DPI |
| 파일명 접두사 | `gantt_` |
| 저장 경로 | `9_Attachments/images/{YYYYMM}/` |
| 파일명 예시 | `gantt_project_schedule_20260112_143025.png` |

### 옵시디언 삽입

저장 시 콘솔에 옵시디언 삽입 코드가 출력됩니다:

```
[OK] 간트차트 저장 완료: D:\_Obsidian\ZK-PARA\9_Attachments\images\202601\gantt_project_20260112_143025.png
[INFO] 옵시디언 삽입: ![[9_Attachments/images/202601/gantt_project_20260112_143025.png]]
```

## 테마 목록

| 테마 | 설명 | 배경색 | 특징 |
|------|------|--------|------|
| `minimal` | 미니멀 모노톤 스타일 | 흰색 | 깔끔한 그레이 톤 |
| `elegant` | 세련된 그레이 + 골드 | #F7FAFC | 고급스러운 느낌 |
| `clean` | 블루 톤 비즈니스 | 흰색 | 청량한 파란색 |
| `corporate` | 기업용 스타일 | #F8F9FA | 다채로운 색상 |
| `dark` | 어두운 배경 | #1A1A2E | 다크 모드용 |

## 순차 인덱스 모드 상세

### 사용 목적

날짜가 아닌 **우선순위**나 **순서**를 표현할 때 사용합니다:

- 연설문의 정책 우선순위
- 프로젝트 단계별 중요도
- 작업의 상대적 규모 비교

### 동작 방식

1. `add_task()`에서 `start`와 `end`를 생략하면 순차 모드 활성화
2. X축이 날짜 대신 정수 인덱스 (0, 1, 2, 3...)로 표시
3. `duration` 파라미터로 각 태스크의 상대적 크기 지정
4. 마일스톤은 순차 모드에서 사용 불가

### 예시

```python
# 연설문 정책 우선순위 시각화
drawer = GanttDrawer(theme='corporate')
drawer.set_title('정권 100일 핵심 정책')
drawer.add_task('첫째: 국민주권 강화', duration=3)
drawer.add_task('둘째: 경제성장동력 창출', duration=5)
drawer.add_task('셋째: 지역균형발전', duration=4)
drawer.add_task('넷째: 외교안보 강화', duration=3)
drawer.save('policy_100days')
```

## 주의사항

### 한글 폰트

- Windows: `Malgun Gothic` (기본 설치됨)
- macOS: `AppleGothic` (기본 설치됨)
- Linux: `NanumGothic` (별도 설치 필요)

한글이 깨지는 경우:
1. 시스템에 한글 폰트가 설치되어 있는지 확인
2. matplotlib 폰트 캐시 갱신: `matplotlib.font_manager._rebuild()`

### 파일 인코딩

모든 소스 파일과 DSL 텍스트는 UTF-8 인코딩을 사용합니다.

### 날짜 범위

- 시작일이 종료일보다 늦으면 안 됩니다
- 모든 태스크의 날짜가 합리적인 범위 내에 있어야 합니다
- 오늘 날짜 라인은 차트 범위 내에 있을 때만 표시됩니다
