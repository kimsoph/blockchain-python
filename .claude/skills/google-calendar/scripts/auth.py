#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Calendar API 인증 처리 모듈
OAuth2 인증을 통해 Google Calendar API에 접근합니다.
"""

import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Calendar API 읽기/쓰기 권한
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Skill 루트 디렉토리 (scripts의 상위 폴더)
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_calendar_service(
    credentials_path=os.path.join(SKILL_DIR, 'credentials.json'),
    token_path=os.path.join(SKILL_DIR, 'token.pickle')
):
    """
    Google Calendar API 서비스 객체를 반환합니다.

    Args:
        credentials_path: OAuth2 credentials JSON 파일 경로
        token_path: 저장된 토큰 파일 경로

    Returns:
        Google Calendar API 서비스 객체
    """
    creds = None

    # 기존 토큰이 있으면 로드
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # 토큰이 없거나 유효하지 않으면 새로 생성
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"credentials.json 파일을 찾을 수 없습니다: {credentials_path}\n"
                    "Google Cloud Console에서 OAuth2 credentials를 다운로드하세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # 토큰 저장
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    # Calendar API 서비스 빌드
    service = build('calendar', 'v3', credentials=creds)
    return service

def list_calendars(service):
    """
    사용 가능한 모든 캘린더 목록을 반환합니다.

    Args:
        service: Google Calendar API 서비스 객체

    Returns:
        캘린더 목록 (list of dict)
    """
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get('items', [])
    return calendars

if __name__ == '__main__':
    # 테스트: 인증 및 캘린더 목록 조회
    service = get_calendar_service()
    calendars = list_calendars(service)

    print("사용 가능한 캘린더:")
    for calendar in calendars:
        print(f"  - {calendar['summary']} (ID: {calendar['id']})")
