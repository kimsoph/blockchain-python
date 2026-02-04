# Google Calendar API 사용 가이드

이 문서는 Google Calendar API의 주요 기능과 사용법을 설명합니다.

## 1. 일정 조회 (List Events)

### 1.1 기본 조회

```python
from scripts.auth import get_calendar_service
from scripts.list_events import list_events

service = get_calendar_service()
events = list_events(service, calendar_id='primary')
```

### 1.2 조회 매개변수

- **calendar_id**: 캘린더 ID
  - `'primary'`: 기본 캘린더
  - 특정 캘린더 ID (예: `'user@example.com'`)

- **time_min**: 조회 시작 시간 (ISO 8601 형식)
  - 예: `'2025-01-01T00:00:00Z'`

- **time_max**: 조회 종료 시간 (ISO 8601 형식)
  - 예: `'2025-12-31T23:59:59Z'`

- **max_results**: 최대 결과 개수 (기본값: 10)

- **query**: 검색 키워드
  - 예: `'회의'`, `'프로젝트'`

### 1.3 예제

```python
# 오늘부터 7일간의 일정 조회
from datetime import datetime, timedelta

time_min = datetime.utcnow().isoformat() + 'Z'
time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

events = list_events(
    service,
    calendar_id='primary',
    time_min=time_min,
    time_max=time_max,
    max_results=50
)

# 특정 키워드로 검색
events = list_events(
    service,
    query='팀 회의',
    max_results=20
)
```

## 2. 일정 생성 (Create Event)

### 2.1 기본 일정 생성

```python
from scripts.create_event import create_event
from datetime import datetime, timedelta

# 1시간짜리 회의 일정
start = datetime.now() + timedelta(days=1)
end = start + timedelta(hours=1)

event = create_event(
    service,
    summary='팀 회의',
    start_time=start,
    end_time=end,
    location='회의실 A',
    description='주간 팀 회의입니다.'
)
```

### 2.2 참석자가 있는 일정

```python
event = create_event(
    service,
    summary='프로젝트 킥오프 미팅',
    start_time='2025-01-15T14:00:00',
    end_time='2025-01-15T16:00:00',
    attendees=[
        'colleague1@example.com',
        'colleague2@example.com',
        'manager@example.com'
    ],
    description='새 프로젝트 시작 회의'
)
```

### 2.3 종일 일정

```python
from scripts.create_event import create_all_day_event

event = create_all_day_event(
    service,
    summary='연차',
    date='2025-01-20',
    description='개인 연차 사용'
)
```

### 2.4 반복 일정

```python
# 매주 월요일 오전 10시 회의
event = create_event(
    service,
    summary='주간 스탠드업',
    start_time='2025-01-13T10:00:00',
    end_time='2025-01-13T10:30:00',
    recurrence=[
        'RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=10'
    ]
)

# 매일 반복 (10회)
recurrence = ['RRULE:FREQ=DAILY;COUNT=10']

# 매주 월수금 반복
recurrence = ['RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=20']

# 매월 첫째 주 월요일
recurrence = ['RRULE:FREQ=MONTHLY;BYDAY=1MO;COUNT=12']
```

### 2.5 알림 설정

```python
event = create_event(
    service,
    summary='중요 회의',
    start_time='2025-01-15T15:00:00',
    end_time='2025-01-15T16:00:00',
    reminders={
        'useDefault': False,
        'overrides': [
            {'method': 'popup', 'minutes': 60},    # 1시간 전 팝업
            {'method': 'email', 'minutes': 1440},  # 1일 전 이메일
        ]
    }
)
```

## 3. 일정 수정 (Update Event)

### 3.1 기본 수정

```python
from scripts.update_event import update_event

# 일정 제목 변경
updated_event = update_event(
    service,
    event_id='abc123xyz',
    summary='수정된 회의 제목'
)

# 위치 변경
updated_event = update_event(
    service,
    event_id='abc123xyz',
    location='회의실 B'
)
```

### 3.2 일정 시간 변경

```python
from scripts.update_event import reschedule_event

rescheduled = reschedule_event(
    service,
    event_id='abc123xyz',
    new_start_time='2025-01-16T15:00:00',
    new_end_time='2025-01-16T16:00:00'
)
```

### 3.3 참석자 추가

```python
from scripts.update_event import add_attendees

updated = add_attendees(
    service,
    event_id='abc123xyz',
    new_attendees=[
        'newperson1@example.com',
        'newperson2@example.com'
    ]
)
```

## 4. 일정 삭제 (Delete Event)

### 4.1 단일 일정 삭제

```python
from scripts.delete_event import delete_event

# 모든 참석자에게 알림 전송
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

### 4.2 일정 취소 (삭제하지 않고 취소 상태로 변경)

```python
from scripts.delete_event import cancel_event

cancelled = cancel_event(
    service,
    event_id='abc123xyz'
)
```

### 4.3 조건에 맞는 일정들 삭제

```python
from scripts.delete_event import delete_events_by_query
from datetime import datetime, timedelta

# "테스트"라는 단어가 포함된 일정들 삭제
deleted_ids = delete_events_by_query(
    service,
    query='테스트',
    time_min=datetime.now().isoformat() + 'Z',
    time_max=(datetime.now() + timedelta(days=30)).isoformat() + 'Z',
    max_results=50
)
```

## 5. 고급 기능

### 5.1 여러 캘린더 사용

```python
from scripts.auth import list_calendars

# 모든 캘린더 조회
calendars = list_calendars(service)
for cal in calendars:
    print(f"{cal['summary']}: {cal['id']}")

# 특정 캘린더에 일정 추가
event = create_event(
    service,
    calendar_id='work@example.com',  # 업무용 캘린더
    summary='업무 회의',
    start_time='2025-01-15T10:00:00',
    end_time='2025-01-15T11:00:00'
)
```

### 5.2 시간대 처리

```python
import pytz
from datetime import datetime

# 한국 시간대
kst = pytz.timezone('Asia/Seoul')
start_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=kst)

event = create_event(
    service,
    summary='회의',
    start_time=start_time.isoformat(),
    end_time=(start_time + timedelta(hours=1)).isoformat(),
    timezone='Asia/Seoul'
)
```

### 5.3 일정 색상 설정

```python
# 일정 생성 시 색상 지정
event = {
    'summary': '중요 마감일',
    'start': {'dateTime': '2025-01-20T23:59:00', 'timeZone': 'Asia/Seoul'},
    'end': {'dateTime': '2025-01-20T23:59:00', 'timeZone': 'Asia/Seoul'},
    'colorId': '11'  # 빨간색
}

created = service.events().insert(calendarId='primary', body=event).execute()
```

**색상 ID:**
- 1: 라벤더
- 2: 세이지
- 3: 포도
- 4: 플라밍고
- 5: 바나나
- 6: 귤
- 7: 피콕
- 8: 그래파이트
- 9: 블루베리
- 10: 바질
- 11: 토마토

### 5.4 첨부파일

```python
event = create_event(
    service,
    summary='문서 검토',
    start_time='2025-01-15T14:00:00',
    end_time='2025-01-15T15:00:00'
)

# 첨부파일 추가 (Google Drive 파일만 지원)
event['attachments'] = [
    {
        'fileUrl': 'https://drive.google.com/file/d/FILE_ID',
        'title': '회의 자료.pdf'
    }
]

updated = service.events().update(
    calendarId='primary',
    eventId=event['id'],
    body=event,
    supportsAttachments=True
).execute()
```

## 6. 일정 객체 구조

### 6.1 기본 필드

```python
event = {
    'id': 'abc123xyz',                    # 일정 고유 ID
    'summary': '일정 제목',                # 제목
    'description': '일정 설명',            # 설명
    'location': '회의실 A',                # 위치
    'start': {                             # 시작 시간
        'dateTime': '2025-01-15T14:00:00',
        'timeZone': 'Asia/Seoul'
    },
    'end': {                               # 종료 시간
        'dateTime': '2025-01-15T15:00:00',
        'timeZone': 'Asia/Seoul'
    },
    'attendees': [                         # 참석자
        {
            'email': 'user@example.com',
            'responseStatus': 'accepted'
        }
    ],
    'recurrence': [                        # 반복 규칙
        'RRULE:FREQ=WEEKLY;BYDAY=MO'
    ],
    'reminders': {                         # 알림
        'useDefault': False,
        'overrides': [
            {'method': 'popup', 'minutes': 30}
        ]
    },
    'status': 'confirmed',                 # 상태 (confirmed/tentative/cancelled)
    'visibility': 'default',               # 공개 설정 (default/public/private/confidential)
    'htmlLink': 'https://...',            # 웹 링크
    'created': '2025-01-01T00:00:00Z',   # 생성 시간
    'updated': '2025-01-02T00:00:00Z'    # 수정 시간
}
```

## 7. 에러 처리

```python
from googleapiclient.errors import HttpError

try:
    event = create_event(service, summary='테스트 일정')
except HttpError as error:
    print(f'HTTP 에러: {error.resp.status} - {error.content}')
except ValueError as error:
    print(f'값 에러: {error}')
except Exception as error:
    print(f'일반 에러: {error}')
```

## 8. 유용한 팁

### 8.1 일정 ID 찾기

일정을 수정/삭제하려면 일정 ID가 필요합니다:

```python
events = list_events(service, query='찾을 일정 제목')
if events:
    event_id = events[0]['id']
    print(f"일정 ID: {event_id}")
```

### 8.2 배치 처리

여러 일정을 한 번에 처리:

```python
from datetime import datetime, timedelta

# 여러 일정 생성
for i in range(5):
    start = datetime.now() + timedelta(days=i+1, hours=14)
    create_event(
        service,
        summary=f'회의 {i+1}',
        start_time=start,
        end_time=start + timedelta(hours=1)
    )
```

### 8.3 특정 기간의 모든 일정 조회

```python
from datetime import datetime, timedelta

# 이번 달 모든 일정
start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0)
end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

events = list_events(
    service,
    time_min=start_of_month.isoformat() + 'Z',
    time_max=end_of_month.isoformat() + 'Z',
    max_results=250
)
```
