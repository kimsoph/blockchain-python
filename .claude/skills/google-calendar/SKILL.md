---
name: google-calendar
description: Google Calendar 일정을 조회, 생성, 수정, 삭제하는 종합 skill. OAuth2 인증을 통해 Google Calendar API에 접근하며, 일정 관리의 모든 기능을 제공한다. 일정 시간 변경, 참석자 추가, 반복 일정 설정, 알림 설정 등 고급 기능을 포함한다. 사용자가 "오늘 일정 보여줘", "내일 회의 추가해줘", "일정 시간 변경해줘", "취소된 일정 삭제해줘" 등의 요청을 할 때 사용한다.
---

# Google Calendar Skill

Google Calendar API를 사용하여 일정을 조회, 생성, 수정, 삭제하는 종합 skill이다.

## Purpose

이 skill은 Google Calendar의 모든 일정 관리 기능을 제공한다:
- 일정 조회 (기간별, 키워드 검색, 다중 캘린더)
- 일정 생성 (일반/종일/반복 일정, 참석자, 알림)
- 일정 수정 (시간 변경, 참석자 추가, 내용 수정)
- 일정 삭제 (단일/배치 삭제, 취소 처리)

OAuth2 인증을 통해 안전하게 Google Calendar에 접근하며, 한국 시간대와 한글을 완전히 지원한다.

## When to Use

다음과 같은 사용자 요청이 있을 때 이 skill을 사용한다:

- 일정 조회: "오늘 일정 보여줘", "이번 주 회의 목록", "다음 달 일정 확인"
- 일정 생성: "내일 오후 3시에 회의 추가", "다음 주 월요일 종일 일정 만들어줘"
- 일정 수정: "회의 시간을 오후 4시로 변경", "참석자 추가해줘", "위치 변경"
- 일정 삭제: "취소된 회의 삭제해줘", "테스트 일정 전부 지워줘"
- 반복 일정: "매주 월요일 스탠드업 미팅 만들어줘"
- 참석자 관리: "회의에 김철수님 이메일 추가", "참석자 목록 보여줘"

## Setup Requirements

### Initial Setup

사용자가 처음 이 skill을 사용하는 경우, 다음 초기 설정이 필요하다:

1. **Google Cloud Console 설정**
   - `references/setup.md` 파일을 참조하여 상세한 설정 과정 확인
   - OAuth2 credentials 생성 및 `credentials.json` 다운로드 필요
   - Google Calendar API 활성화 필요

2. **Python 환경 설정**
   - 필수 라이브러리 설치: `pip install -r requirements.txt`
   - `requirements.txt`는 skill 루트에 포함되어 있음

3. **인증 프로세스**
   - 최초 실행 시 브라우저를 통한 OAuth2 인증 필요
   - 인증 후 `token.pickle` 파일 자동 생성
   - 이후 자동으로 토큰 재사용

Setup이 필요한 경우, `references/setup.md`의 내용을 사용자에게 안내한다.

### Prerequisites

- Python 3.7 이상
- Google 계정
- 인터넷 연결

## How to Use

### 1. Authentication

모든 작업은 먼저 인증이 필요하다. `scripts/auth.py` 모듈을 사용하여 인증을 처리한다:

```python
from scripts.auth import get_calendar_service

# Google Calendar 서비스 객체 획득
service = get_calendar_service()
```

최초 실행 시:
- 브라우저가 자동으로 열림
- Google 계정 로그인 및 권한 승인
- 인증 완료 후 `token.pickle` 파일 생성
- 이후 자동으로 재사용됨

### 2. List Events (일정 조회)

`scripts/list_events.py` 모듈을 사용한다.

#### Basic Usage

```python
from scripts.list_events import list_events, format_event

# 기본 조회 (오늘부터 7일)
events = list_events(service)

# 결과 출력
for event in events:
    print(format_event(event))
```

#### Advanced Usage

```python
from datetime import datetime, timedelta

# 특정 기간 조회
time_min = datetime.utcnow().isoformat() + 'Z'
time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'

events = list_events(
    service,
    calendar_id='primary',      # 또는 특정 캘린더 ID
    time_min=time_min,
    time_max=time_max,
    max_results=50,
    query='회의'                # 키워드 검색
)
```

#### Command Line Usage

```bash
# 기본 캘린더의 7일간 일정
python scripts/list_events.py

# 30일간 일정
python scripts/list_events.py primary 30

# 특정 캘린더
python scripts/list_events.py work@example.com 7
```

### 3. Create Event (일정 생성)

`scripts/create_event.py` 모듈을 사용한다.

#### Basic Event

```python
from scripts.create_event import create_event
from datetime import datetime, timedelta

start = datetime.now() + timedelta(days=1, hours=14)
end = start + timedelta(hours=1)

event = create_event(
    service,
    summary='팀 회의',
    start_time=start,
    end_time=end,
    location='회의실 A',
    description='주간 팀 회의'
)
```

#### Event with Attendees

```python
event = create_event(
    service,
    summary='프로젝트 킥오프',
    start_time='2025-01-15T14:00:00',
    end_time='2025-01-15T16:00:00',
    attendees=[
        'colleague1@example.com',
        'colleague2@example.com'
    ]
)
```

#### All-Day Event

```python
from scripts.create_event import create_all_day_event

event = create_all_day_event(
    service,
    summary='연차',
    date='2025-01-20'
)
```

#### Recurring Event

```python
# 매주 월요일 반복
event = create_event(
    service,
    summary='주간 스탠드업',
    start_time='2025-01-13T10:00:00',
    end_time='2025-01-13T10:30:00',
    recurrence=['RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=10']
)
```

#### Custom Reminders

```python
event = create_event(
    service,
    summary='중요 회의',
    start_time='2025-01-15T15:00:00',
    end_time='2025-01-15T16:00:00',
    reminders={
        'useDefault': False,
        'overrides': [
            {'method': 'popup', 'minutes': 60},
            {'method': 'email', 'minutes': 1440}
        ]
    }
)
```

#### Command Line Usage

```bash
python scripts/create_event.py "팀 회의" "2025-01-15T14:00:00" "2025-01-15T15:00:00" "회의실 A"
```

### 4. Update Event (일정 수정)

`scripts/update_event.py` 모듈을 사용한다.

#### Basic Update

```python
from scripts.update_event import update_event

# 제목 변경
event = update_event(
    service,
    event_id='abc123xyz',
    summary='변경된 제목'
)

# 위치 변경
event = update_event(
    service,
    event_id='abc123xyz',
    location='회의실 B'
)
```

#### Reschedule Event

```python
from scripts.update_event import reschedule_event

event = reschedule_event(
    service,
    event_id='abc123xyz',
    new_start_time='2025-01-16T15:00:00',
    new_end_time='2025-01-16T16:00:00'
)
```

#### Add Attendees

```python
from scripts.update_event import add_attendees

event = add_attendees(
    service,
    event_id='abc123xyz',
    new_attendees=['newperson@example.com']
)
```

#### Command Line Usage

```bash
python scripts/update_event.py abc123xyz summary "새 제목"
python scripts/update_event.py abc123xyz location "회의실 C"
```

### 5. Delete Event (일정 삭제)

`scripts/delete_event.py` 모듈을 사용한다.

#### Delete Single Event

```python
from scripts.delete_event import delete_event

# 모든 참석자에게 알림
delete_event(
    service,
    event_id='abc123xyz',
    send_updates='all'
)

# 알림 없이 삭제
delete_event(
    service,
    event_id='abc123xyz',
    send_updates='none'
)
```

#### Cancel Event (취소 처리)

```python
from scripts.delete_event import cancel_event

# 삭제하지 않고 취소 상태로 변경
event = cancel_event(
    service,
    event_id='abc123xyz'
)
```

#### Batch Delete

```python
from scripts.delete_event import delete_events_by_query

# 특정 키워드의 일정들 삭제
deleted_ids = delete_events_by_query(
    service,
    query='테스트',
    max_results=50
)
```

#### Command Line Usage

```bash
python scripts/delete_event.py abc123xyz
python scripts/delete_event.py abc123xyz none  # 알림 없이
```

## Finding Event IDs

일정을 수정하거나 삭제하려면 event_id가 필요하다. 다음 방법으로 찾는다:

```python
# 제목으로 검색
events = list_events(service, query='회의 제목')
if events:
    event_id = events[0]['id']
    print(f"Event ID: {event_id}")

# 특정 날짜의 모든 일정 조회
from datetime import datetime
today = datetime.now().replace(hour=0, minute=0, second=0)
events = list_events(
    service,
    time_min=today.isoformat() + 'Z',
    time_max=(today + timedelta(days=1)).isoformat() + 'Z'
)
```

## Working with Multiple Calendars

```python
from scripts.auth import list_calendars

# 사용 가능한 모든 캘린더 조회
calendars = list_calendars(service)
for cal in calendars:
    print(f"{cal['summary']}: {cal['id']}")

# 특정 캘린더에 일정 추가
event = create_event(
    service,
    calendar_id='work@example.com',
    summary='업무 회의',
    start_time='2025-01-15T10:00:00',
    end_time='2025-01-15T11:00:00'
)
```

## Advanced Features

더 상세한 API 사용법, 고급 기능, 예제는 `references/api_guide.md`를 참조한다:

- 시간대 처리
- 일정 색상 설정
- 첨부파일 추가
- 복잡한 반복 규칙
- 일정 객체 전체 구조
- 에러 처리 패턴

## Common Patterns

### 오늘 일정 조회

```python
from datetime import datetime, timedelta

today_start = datetime.now().replace(hour=0, minute=0, second=0)
today_end = today_start + timedelta(days=1)

events = list_events(
    service,
    time_min=today_start.isoformat() + 'Z',
    time_max=today_end.isoformat() + 'Z'
)
```

### 내일 오후 2시 회의 추가

```python
from datetime import datetime, timedelta

tomorrow_2pm = datetime.now().replace(hour=14, minute=0, second=0) + timedelta(days=1)

event = create_event(
    service,
    summary='회의',
    start_time=tomorrow_2pm,
    end_time=tomorrow_2pm + timedelta(hours=1)
)
```

### 이번 주 모든 회의 찾기

```python
from datetime import datetime, timedelta

# 이번 주 월요일
today = datetime.now()
monday = today - timedelta(days=today.weekday())
sunday = monday + timedelta(days=7)

events = list_events(
    service,
    time_min=monday.isoformat() + 'Z',
    time_max=sunday.isoformat() + 'Z',
    query='회의'
)
```

## Error Handling

API 호출 실패 시 적절한 에러 메시지를 사용자에게 제공한다:

```python
from googleapiclient.errors import HttpError

try:
    event = create_event(service, summary='테스트')
except HttpError as error:
    print(f"API 에러 발생: {error.resp.status}")
    print(f"상세: {error.content}")
except ValueError as error:
    print(f"입력값 에러: {error}")
```

## Security Notes

- `credentials.json`과 `token.pickle` 파일은 민감 정보를 포함
- 이 파일들을 Git에 커밋하거나 외부에 공유하지 말 것
- `.gitignore`에 추가 권장

## Troubleshooting

일반적인 문제와 해결 방법은 `references/setup.md`의 "문제 해결" 섹션을 참조한다:

- credentials.json not found
- 인증 실패
- 권한 오류
- API 활성화 문제

## Summary

이 skill을 사용하면 Google Calendar의 모든 기능을 Python 코드로 제어할 수 있다:

1. **인증**: `auth.py`로 OAuth2 인증
2. **조회**: `list_events.py`로 일정 검색 및 조회
3. **생성**: `create_event.py`로 새 일정 추가
4. **수정**: `update_event.py`로 기존 일정 변경
5. **삭제**: `delete_event.py`로 일정 제거

각 스크립트는 독립적으로 실행 가능하며, Python 모듈로 import하여 사용할 수도 있다. 사용자 요청에 따라 적절한 스크립트와 함수를 선택하여 작업을 수행한다.
