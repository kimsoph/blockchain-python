#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Calendar 일정 생성 스크립트
"""

import sys
import json
from datetime import datetime, timedelta
from auth import get_calendar_service

def create_event(service, calendar_id='primary', summary=None, start_time=None,
                end_time=None, location=None, description=None, attendees=None,
                recurrence=None, reminders=None, timezone='Asia/Seoul'):
    """
    Google Calendar에 새 일정을 생성합니다.

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID (기본값: 'primary')
        summary: 일정 제목 (필수)
        start_time: 시작 시간 (datetime 객체 또는 ISO 8601 문자열)
        end_time: 종료 시간 (datetime 객체 또는 ISO 8601 문자열)
        location: 위치
        description: 설명
        attendees: 참석자 이메일 리스트
        recurrence: 반복 규칙 (RRULE 형식 리스트)
        reminders: 알림 설정 (dict)
        timezone: 타임존 (기본값: 'Asia/Seoul')

    Returns:
        생성된 일정 객체 (dict)
    """
    if not summary:
        raise ValueError("일정 제목(summary)은 필수입니다.")

    # 기본값: 지금부터 1시간
    if not start_time:
        start_time = datetime.now()
    if not end_time:
        end_time = start_time + timedelta(hours=1)

    # datetime을 ISO 8601 문자열로 변환
    if isinstance(start_time, datetime):
        start_time = start_time.isoformat()
    if isinstance(end_time, datetime):
        end_time = end_time.isoformat()

    # 일정 객체 구성
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time,
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': timezone,
        },
    }

    if location:
        event['location'] = location

    if description:
        event['description'] = description

    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]

    if recurrence:
        event['recurrence'] = recurrence

    if reminders:
        event['reminders'] = reminders
    else:
        # 기본 알림: 30분 전 팝업
        event['reminders'] = {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 30},
            ],
        }

    # 일정 생성
    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()

    return created_event

def create_all_day_event(service, calendar_id='primary', summary=None, date=None,
                         location=None, description=None):
    """
    종일 일정을 생성합니다.

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID
        summary: 일정 제목
        date: 날짜 (YYYY-MM-DD 형식 문자열)
        location: 위치
        description: 설명

    Returns:
        생성된 일정 객체 (dict)
    """
    if not summary:
        raise ValueError("일정 제목(summary)은 필수입니다.")

    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    event = {
        'summary': summary,
        'start': {
            'date': date,
        },
        'end': {
            'date': date,
        },
    }

    if location:
        event['location'] = location

    if description:
        event['description'] = description

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()

    return created_event

def main():
    """
    명령줄에서 실행할 때의 메인 함수

    사용법:
        python create_event.py <제목> <시작시간> <종료시간> [위치] [설명]

    예제:
        python create_event.py "팀 회의" "2025-01-15T14:00:00" "2025-01-15T15:00:00" "회의실 A"
        python create_event.py "프로젝트 마감" "2025-01-20T09:00:00" "2025-01-20T18:00:00"
    """
    if len(sys.argv) < 4:
        print("사용법: python create_event.py <제목> <시작시간> <종료시간> [위치] [설명]")
        print("예제: python create_event.py \"팀 회의\" \"2025-01-15T14:00:00\" \"2025-01-15T15:00:00\"")
        sys.exit(1)

    summary = sys.argv[1]
    start_time = sys.argv[2]
    end_time = sys.argv[3]
    location = sys.argv[4] if len(sys.argv) > 4 else None
    description = sys.argv[5] if len(sys.argv) > 5 else None

    service = get_calendar_service()

    event = create_event(
        service,
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        location=location,
        description=description
    )

    print(f"일정이 생성되었습니다:")
    print(f"  제목: {event['summary']}")
    print(f"  시작: {event['start']['dateTime']}")
    print(f"  종료: {event['end']['dateTime']}")
    print(f"  링크: {event['htmlLink']}")

if __name__ == '__main__':
    main()
