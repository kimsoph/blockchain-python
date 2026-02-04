#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Calendar 일정 삭제 스크립트
"""

import sys
from auth import get_calendar_service

def delete_event(service, calendar_id='primary', event_id=None, send_updates='all'):
    """
    Google Calendar 일정을 삭제합니다.

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID (기본값: 'primary')
        event_id: 삭제할 일정의 ID (필수)
        send_updates: 알림 전송 설정
            - 'all': 모든 참석자에게 알림
            - 'externalOnly': 외부 참석자에게만 알림
            - 'none': 알림 없음

    Returns:
        None (삭제 성공 시 아무것도 반환하지 않음)
    """
    if not event_id:
        raise ValueError("일정 ID(event_id)는 필수입니다.")

    # 일정 삭제
    service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
        sendUpdates=send_updates
    ).execute()

    return True

def cancel_event(service, calendar_id='primary', event_id=None):
    """
    일정을 취소로 표시합니다 (삭제하지 않고 상태만 변경).

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID
        event_id: 일정 ID

    Returns:
        취소된 일정 객체 (dict)
    """
    if not event_id:
        raise ValueError("일정 ID(event_id)는 필수입니다.")

    # 기존 일정 조회
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    # 상태를 취소로 변경
    event['status'] = 'cancelled'

    # 업데이트
    cancelled_event = service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=event,
        sendUpdates='all'
    ).execute()

    return cancelled_event

def delete_events_by_query(service, calendar_id='primary', query=None,
                           time_min=None, time_max=None, max_results=10):
    """
    검색 조건에 맞는 일정들을 삭제합니다.

    Args:
        service: Google Calendar API 서비스 객체
        calendar_id: 캘린더 ID
        query: 검색 키워드
        time_min: 조회 시작 시간
        time_max: 조회 종료 시간
        max_results: 최대 삭제 개수

    Returns:
        삭제된 일정 ID 리스트
    """
    # 일정 검색
    events_result = service.events().list(
        calendarId=calendar_id,
        q=query,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True
    ).execute()

    events = events_result.get('items', [])
    deleted_ids = []

    for event in events:
        try:
            delete_event(service, calendar_id, event['id'], send_updates='none')
            deleted_ids.append(event['id'])
            print(f"삭제됨: {event.get('summary', '(제목 없음)')} (ID: {event['id']})")
        except Exception as e:
            print(f"삭제 실패: {event.get('summary', '(제목 없음)')} - {e}")

    return deleted_ids

def main():
    """
    명령줄에서 실행할 때의 메인 함수

    사용법:
        python delete_event.py <event_id> [send_updates]

    예제:
        python delete_event.py abc123
        python delete_event.py abc123 all
        python delete_event.py abc123 none
    """
    if len(sys.argv) < 2:
        print("사용법: python delete_event.py <event_id> [send_updates]")
        print("예제: python delete_event.py abc123")
        sys.exit(1)

    event_id = sys.argv[1]
    send_updates = sys.argv[2] if len(sys.argv) > 2 else 'all'

    service = get_calendar_service()

    # 삭제 전 일정 정보 조회
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        summary = event.get('summary', '(제목 없음)')
    except Exception as e:
        print(f"일정을 찾을 수 없습니다: {e}")
        sys.exit(1)

    # 일정 삭제
    try:
        delete_event(service, event_id=event_id, send_updates=send_updates)
        print(f"일정이 삭제되었습니다: {summary}")
        print(f"알림 전송: {send_updates}")
    except Exception as e:
        print(f"삭제 실패: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
