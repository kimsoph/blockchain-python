# -*- coding: utf-8 -*-
"""
make-gantt_chart 스킬 유틸리티 모듈
한글 폰트 설정, 파일명 생성, 경로 관리, 테마 정의, DSL 파싱 등
"""

import os
import platform
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional


def get_korean_font() -> str:
    """
    운영체제에 따라 적합한 한글 폰트를 반환한다.

    Returns:
        str: 폰트 이름
    """
    system = platform.system()

    if system == 'Windows':
        return 'Malgun Gothic'
    elif system == 'Darwin':  # macOS
        return 'AppleGothic'
    else:  # Linux
        return 'NanumGothic'


def setup_matplotlib_korean() -> bool:
    """
    matplotlib에서 한글을 사용할 수 있도록 설정한다.

    Returns:
        bool: 설정 성공 여부
    """
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    font_name = get_korean_font()

    # 시스템 폰트 중 한글 폰트 검색
    system = platform.system()
    font_found = False

    if system == 'Windows':
        # Windows 폰트 경로
        font_paths = [
            'C:/Windows/Fonts/malgun.ttf',
            'C:/Windows/Fonts/malgunbd.ttf',
            'C:/Windows/Fonts/NanumGothic.ttf',
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                font_found = True
                break

    # matplotlib 설정
    plt.rcParams['font.family'] = font_name
    plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

    # 폰트 캐시 확인
    try:
        font_list = [f.name for f in fm.fontManager.ttflist]
        if font_name in font_list or any(font_name.lower() in f.lower() for f in font_list):
            font_found = True
    except Exception:
        pass

    if not font_found:
        print(f"[경고] '{font_name}' 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
        return False

    return True


def generate_filename(prefix: str, ext: str = 'png') -> str:
    """
    타임스탬프가 포함된 파일명을 생성한다.

    Args:
        prefix: 파일명 접두사
        ext: 파일 확장자 (기본: 'png')

    Returns:
        str: 생성된 파일명 (예: 'gantt_project_20260112_143025.png')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에서 특수문자 제거
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))
    return f"gantt_{safe_prefix}_{timestamp}.{ext}"


def get_output_dir(base_path: str = None) -> Path:
    """
    간트차트 출력 디렉토리 경로를 반환한다.
    디렉토리가 없으면 생성한다.
    년월(YYYYMM) 서브폴더에 자동 저장된다.

    Args:
        base_path: 기본 경로 (기본: 현재 스크립트 기준 볼트 루트)

    Returns:
        Path: 출력 디렉토리 경로 (예: .../images/202601/)
    """
    # 현재 년월 (YYYYMM)
    current_ym = datetime.now().strftime('%Y%m')

    if base_path:
        output_dir = Path(base_path) / '9_Attachments' / 'images' / current_ym
    else:
        # 스크립트 위치 기준으로 볼트 루트 찾기
        current = Path(__file__).resolve()
        # .claude/skills/make-gantt_chart/scripts/ 에서 4단계 위로
        vault_root = current.parents[4]
        output_dir = vault_root / '9_Attachments' / 'images' / current_ym

    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


# 테마 정의 (5가지)
THEMES = {
    'minimal': {
        'name': 'Minimal',
        'description': '미니멀 모노톤 스타일',
        'bgcolor': '#FFFFFF',
        'fontcolor': '#1A1A2E',
        'grid_color': '#E5E5E5',
        'today_color': '#EF4444',
        'task_colors': ['#4A5568', '#718096', '#A0AEC0', '#CBD5E0', '#E2E8F0'],
        'progress_color': '#2D3748',
        'milestone_color': '#1A1A2E',
    },
    'elegant': {
        'name': 'Elegant',
        'description': '세련된 그레이 톤 + 골드 액센트',
        'bgcolor': '#F7FAFC',
        'fontcolor': '#2D3748',
        'grid_color': '#E2E8F0',
        'today_color': '#E53E3E',
        'task_colors': ['#2D3748', '#4A5568', '#718096', '#A0AEC0', '#B7950B'],
        'progress_color': '#B7950B',
        'milestone_color': '#B7950B',
    },
    'clean': {
        'name': 'Clean',
        'description': '깔끔한 블루 톤 비즈니스 스타일',
        'bgcolor': '#FFFFFF',
        'fontcolor': '#1E3A8A',
        'grid_color': '#DBEAFE',
        'today_color': '#DC2626',
        'task_colors': ['#2563EB', '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE'],
        'progress_color': '#1D4ED8',
        'milestone_color': '#1E40AF',
    },
    'corporate': {
        'name': 'Corporate',
        'description': '비즈니스/기업용 스타일',
        'bgcolor': '#F8F9FA',
        'fontcolor': '#343A40',
        'grid_color': '#DEE2E6',
        'today_color': '#DC3545',
        'task_colors': ['#2E86AB', '#17A2B8', '#20C997', '#28A745', '#FFC107'],
        'progress_color': '#1A5276',
        'milestone_color': '#17A2B8',
    },
    'dark': {
        'name': 'Dark',
        'description': '어두운 배경 테마',
        'bgcolor': '#1A1A2E',
        'fontcolor': '#E5E5E5',
        'grid_color': '#374151',
        'today_color': '#EF4444',
        'task_colors': ['#3B82F6', '#8B5CF6', '#06B6D4', '#10B981', '#F59E0B'],
        'progress_color': '#60A5FA',
        'milestone_color': '#F59E0B',
    }
}


def get_theme(name: str = 'minimal') -> Dict[str, Any]:
    """
    테마 색상 딕셔너리를 반환한다.

    Args:
        name: 테마 이름 (minimal, elegant, clean, corporate, dark)

    Returns:
        Dict: 테마 설정 딕셔너리
    """
    if name not in THEMES:
        print(f"[경고] 알 수 없는 테마 '{name}'. 'minimal' 테마를 사용합니다.")
        name = 'minimal'
    return THEMES[name]


def list_themes() -> List[str]:
    """
    사용 가능한 테마 목록을 반환한다.

    Returns:
        List[str]: 테마 이름 목록
    """
    return list(THEMES.keys())


def parse_date(date_str: str) -> Optional[datetime]:
    """
    날짜 문자열을 datetime 객체로 변환한다.
    지원 형식: YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD

    Args:
        date_str: 날짜 문자열

    Returns:
        datetime 또는 None
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # 지원 형식들
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y%m%d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def parse_progress(progress_str: str) -> int:
    """
    진행률 문자열을 정수로 변환한다.
    지원 형식: 50%, 50, [50%], [50]

    Args:
        progress_str: 진행률 문자열

    Returns:
        int: 0-100 사이의 정수
    """
    if not progress_str:
        return 0

    # 숫자만 추출
    match = re.search(r'(\d+)', progress_str)
    if match:
        value = int(match.group(1))
        return min(100, max(0, value))

    return 0


# DSL 문법 패턴
DSL_PATTERNS = {
    'title': re.compile(r'^title:\s*(.+)$', re.IGNORECASE),
    # 태스크: 이름: 시작일 ~ 종료일 [진행률%]
    'task_with_dates': re.compile(r'^(.+?):\s*(\d{4}[-/]?\d{2}[-/]?\d{2})\s*~\s*(\d{4}[-/]?\d{2}[-/]?\d{2})(?:\s*\[(\d+)%?\])?$'),
    # 태스크(순차모드): 이름 [duration=숫자]
    'task_sequential': re.compile(r'^(.+?)(?:\s*\[duration[=:]?\s*(\d+)\])?$'),
    # 마일스톤: [M] 이름: 날짜
    'milestone': re.compile(r'^\[M\]\s*(.+?):\s*(\d{4}[-/]?\d{2}[-/]?\d{2})$'),
    # 그룹/카테고리: ## 그룹명
    'group': re.compile(r'^##\s*(.+)$'),
}


def parse_dsl(text: str) -> Dict[str, Any]:
    """
    DSL 텍스트를 파싱하여 간트차트 구성요소를 반환한다.

    DSL 문법:
        title: 제목

        ## 그룹명 (선택)
        태스크명: 시작일 ~ 종료일 [진행률%]
        [M] 마일스톤명: 날짜

        # 순차 모드 (날짜 없이)
        태스크명 [duration=숫자]

    Args:
        text: DSL 텍스트

    Returns:
        Dict: {
            'title': str,
            'tasks': List[Dict],  # name, start, end, progress, group
            'milestones': List[Dict],  # name, date
            'groups': List[str],
            'is_sequential': bool  # 날짜가 없는 순차 모드 여부
        }
    """
    result = {
        'title': '',
        'tasks': [],
        'milestones': [],
        'groups': [],
        'is_sequential': True  # 기본값: 순차 모드 (날짜가 있으면 False로 변경)
    }

    current_group = None
    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') and not line.startswith('##'):
            continue

        # 타이틀 파싱
        match = DSL_PATTERNS['title'].match(line)
        if match:
            result['title'] = match.group(1).strip()
            continue

        # 그룹 파싱
        match = DSL_PATTERNS['group'].match(line)
        if match:
            current_group = match.group(1).strip()
            if current_group not in result['groups']:
                result['groups'].append(current_group)
            continue

        # 마일스톤 파싱
        match = DSL_PATTERNS['milestone'].match(line)
        if match:
            milestone_name = match.group(1).strip()
            milestone_date = parse_date(match.group(2))
            if milestone_date:
                result['milestones'].append({
                    'name': milestone_name,
                    'date': milestone_date
                })
                result['is_sequential'] = False  # 날짜가 있으면 순차 모드 아님
            continue

        # 태스크 파싱 (날짜 있음)
        match = DSL_PATTERNS['task_with_dates'].match(line)
        if match:
            task_name = match.group(1).strip()
            start_date = parse_date(match.group(2))
            end_date = parse_date(match.group(3))
            progress = int(match.group(4)) if match.group(4) else 0

            if start_date and end_date:
                result['tasks'].append({
                    'name': task_name,
                    'start': start_date,
                    'end': end_date,
                    'progress': min(100, max(0, progress)),
                    'group': current_group
                })
                result['is_sequential'] = False  # 날짜가 있으면 순차 모드 아님
            continue

        # 태스크 파싱 (순차 모드, 날짜 없음) - 그룹이나 마일스톤이 아닌 일반 텍스트
        # 마일스톤이나 그룹 패턴이 아니고, 날짜 패턴도 아닌 경우
        if not line.startswith('[M]') and not line.startswith('##'):
            match = DSL_PATTERNS['task_sequential'].match(line)
            if match:
                task_name = match.group(1).strip()
                duration = int(match.group(2)) if match.group(2) else 1

                # 빈 문자열이나 타이틀 구분자가 아닌 경우만 추가
                if task_name and ':' not in task_name:
                    result['tasks'].append({
                        'name': task_name,
                        'start': None,
                        'end': None,
                        'duration': duration,
                        'progress': 0,
                        'group': current_group
                    })

    return result


if __name__ == '__main__':
    # 테스트
    print(f"한글 폰트: {get_korean_font()}")
    print(f"파일명 예시: {generate_filename('test')}")
    print(f"출력 디렉토리: {get_output_dir()}")
    print(f"테마 목록: {list_themes()}")

    # DSL 파싱 테스트 (날짜 모드)
    test_dsl_dates = """
title: 프로젝트 일정

## 1단계
기획: 2026-01-01 ~ 2026-01-05 [100%]
개발: 2026-01-06 ~ 2026-01-20 [60%]

## 2단계
테스트: 2026-01-21 ~ 2026-01-28 [0%]

[M] 킥오프: 2026-01-01
[M] 릴리즈: 2026-01-28
    """
    result = parse_dsl(test_dsl_dates)
    print(f"\nDSL 파싱 결과 (날짜 모드):")
    print(f"  제목: {result['title']}")
    print(f"  태스크: {result['tasks']}")
    print(f"  마일스톤: {result['milestones']}")
    print(f"  그룹: {result['groups']}")
    print(f"  순차 모드: {result['is_sequential']}")

    # DSL 파싱 테스트 (순차 모드)
    test_dsl_sequential = """
title: 정책 우선순위

첫째: 국민주권 강화 [duration=3]
둘째: 성장동력 창출 [duration=5]
셋째: 균형발전 [duration=4]
    """
    result2 = parse_dsl(test_dsl_sequential)
    print(f"\nDSL 파싱 결과 (순차 모드):")
    print(f"  제목: {result2['title']}")
    print(f"  태스크: {result2['tasks']}")
    print(f"  순차 모드: {result2['is_sequential']}")
