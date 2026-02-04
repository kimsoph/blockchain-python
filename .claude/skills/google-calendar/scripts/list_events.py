#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Calendar 일정 조회 스크립트
"""

import sys
from datetime import datetime, timedelta
from auth import get_calendar_service
import pytz

def list_events(service, calendar_id='primary', time_min=None, time_max=None,
                max_results=10, query=None):
    """
    Google Calendar 일정을 조회합니다.

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID (기본값: 'primary')
        time_min: 조회 시작 시간 (ISO 8601 형식)
        time_max: 조회 종료 시간 (ISO 8601 형식)
        max_results: 최대 결과 개수
        query: 검색 키워드

    Returns:
        일정 목록 (list of dict)
    """
    # 기본값: 오늘부터 7일간
    if not time_min:
        time_min = datetime.utcnow().isoformat() + 'Z'
    if not time_max:
        time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime',
        q=query
    ).execute()

    events = events_result.get('items', [])
    return events

def format_event(event):
    """
    일정 정보를 사람이 읽기 쉬운 형식으로 포맷합니다.

    Args:
        event: 일정 객체 (dict)

    Returns:
        포맷된 문자열
    """
    start = event['start'].get('dateTime', event['start'].get('date'))
    end = event['end'].get('dateTime', event['end'].get('date'))

    result = f"제목: {event.get('summary', '(제목 없음)')}\n"
    result += f"시작: {start}\n"
    result += f"종료: {end}\n"

    if 'location' in event:
        result += f"위치: {event['location']}\n"

    if 'description' in event:
        result += f"설명: {event['description']}\n"

    if 'attendees' in event:
        attendees = [a['email'] for a in event['attendees']]
        result += f"참석자: {', '.join(attendees)}\n"

    result += f"ID: {event['id']}\n"

    return result

def main():
    """
    명령줄에서 실행할 때의 메인 함수

    사용법:
        python list_events.py [calendar_id] [days]

    예제:
        python list_events.py primary 7
        python list_events.py work@example.com 30
    """
    calendar_id = sys.argv[1] if len(sys.argv) > 1 else 'primary'
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    service = get_calendar_service()

    time_min = datetime.utcnow().isoformat() + 'Z'
    time_max = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'

    events = list_events(service, calendar_id, time_min, time_max, max_results=50)

    if not events:
        print(f'앞으로 {days}일간 예정된 일정이 없습니다.')
    else:
        print(f'{len(events)}개의 일정을 찾았습니다:\n')
        for i, event in enumerate(events, 1):
            print(f"[{i}]")
            print(format_event(event))
            print("-" * 60)

if __name__ == '__main__':
    main()
