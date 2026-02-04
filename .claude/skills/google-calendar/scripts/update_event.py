#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Calendar 일정 수정 스크립트
"""

import sys
import json
from auth import get_calendar_service

def update_event(service, calendar_id='primary', event_id=None, **kwargs):
    """
    Google Calendar 일정을 수정합니다.

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID (기본값: 'primary')
        event_id: 수정할 일정의 ID (필수)
        **kwargs: 수정할 필드들
            - summary: 제목
            - start_time: 시작 시간 (ISO 8601 문자열)
            - end_time: 종료 시간 (ISO 8601 문자열)
            - location: 위치
            - description: 설명
            - attendees: 참석자 이메일 리스트
            - recurrence: 반복 규칙
            - reminders: 알림 설정

    Returns:
        수정된 일정 객체 (dict)
    """
    if not event_id:
        raise ValueError("일정 ID(event_id)는 필수입니다.")

    # 기존 일정 조회
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    # 필드 업데이트
    if 'summary' in kwargs:
        event['summary'] = kwargs['summary']

    if 'start_time' in kwargs:
        if 'dateTime' in event['start']:
            event['start']['dateTime'] = kwargs['start_time']
        else:
            event['start']['date'] = kwargs['start_time']

    if 'end_time' in kwargs:
        if 'dateTime' in event['end']:
            event['end']['dateTime'] = kwargs['end_time']
        else:
            event['end']['date'] = kwargs['end_time']

    if 'location' in kwargs:
        event['location'] = kwargs['location']

    if 'description' in kwargs:
        event['description'] = kwargs['description']

    if 'attendees' in kwargs:
        event['attendees'] = [{'email': email} for email in kwargs['attendees']]

    if 'recurrence' in kwargs:
        event['recurrence'] = kwargs['recurrence']

    if 'reminders' in kwargs:
        event['reminders'] = kwargs['reminders']

    # 일정 업데이트
    updated_event = service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=event
    ).execute()

    return updated_event

def reschedule_event(service, calendar_id='primary', event_id=None,
                     new_start_time=None, new_end_time=None):
    """
    일정의 시간을 변경합니다.

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID
        event_id: 일정 ID
        new_start_time: 새 시작 시간 (ISO 8601 문자열)
        new_end_time: 새 종료 시간 (ISO 8601 문자열)

    Returns:
        수정된 일정 객체 (dict)
    """
    return update_event(
        service,
        calendar_id=calendar_id,
        event_id=event_id,
        start_time=new_start_time,
        end_time=new_end_time
    )

def add_attendees(service, calendar_id='primary', event_id=None, new_attendees=None):
    """
    일정에 참석자를 추가합니다.

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID
        event_id: 일정 ID
        new_attendees: 추가할 참석자 이메일 리스트

    Returns:
        수정된 일정 객체 (dict)
    """
    if not new_attendees:
        raise ValueError("추가할 참석자 목록이 필요합니다.")

    # 기존 일정 조회
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    # 기존 참석자 가져오기
    existing_attendees = event.get('attendees', [])
    existing_emails = {a['email'] for a in existing_attendees}

    # 새 참석자 추가 (중복 제거)
    for email in new_attendees:
        if email not in existing_emails:
            existing_attendees.append({'email': email})

    event['attendees'] = existing_attendees

    # 업데이트
    updated_event = service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=event,
        sendUpdates='all'  # 모든 참석자에게 알림
    ).execute()

    return updated_event

def main():
    """
    명령줄에서 실행할 때의 메인 함수

    사용법:
        python update_event.py <event_id> <필드> <값>

    예제:
        python update_event.py abc123 summary "새 회의 제목"
        python update_event.py abc123 location "회의실 B"
        python update_event.py abc123 start_time "2025-01-16T15:00:00"
    """
    if len(sys.argv) < 4:
        print("사용법: python update_event.py <event_id> <필드> <값>")
        print("예제: python update_event.py abc123 summary \"새 회의 제목\"")
        sys.exit(1)

    event_id = sys.argv[1]
    field = sys.argv[2]
    value = sys.argv[3]

    service = get_calendar_service()

    kwargs = {field: value}
    event = update_event(service, event_id=event_id, **kwargs)

    print(f"일정이 수정되었습니다:")
    print(f"  제목: {event.get('summary', '(없음)')}")
    if 'start' in event:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(f"  시작: {start}")
    if 'end' in event:
        end = event['end'].get('dateTime', event['end'].get('date'))
        print(f"  종료: {end}")
    print(f"  링크: {event['htmlLink']}")

if __name__ == '__main__':
    main()
