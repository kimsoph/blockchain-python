# -*- coding: utf-8 -*-
"""
make-excalidraw 스킬 유틸리티 모듈
ID 생성, 파일명 생성, 경로 관리, 테마 정의 등
"""

import random
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


# ============================================================
# 스타일 상수 (v1.1 추가)
# ============================================================

# 채우기 스타일 (7가지)
FILL_STYLES = [
    'hachure',      # 빗금 채우기 (Excalidraw 기본, 손그림 느낌)
    'cross-hatch',  # 격자 빗금
    'solid',        # 단색 채우기
    'zigzag',       # 지그재그 패턴
    'dots',         # 점 패턴
    'dashed',       # 대시 패턴
    'zigzag-line'   # 지그재그 선
]

# 화살표 끝점 타입 (6가지)
ARROWHEAD_TYPES = {
    'none': None,           # 끝점 없음
    'arrow': 'arrow',       # 기본 화살표
    'triangle': 'triangle', # 채워진 삼각형
    'circle': 'dot',        # 원형 끝점 (Excalidraw에서 'dot')
    'bar': 'bar',           # 직선 막대
    'diamond': 'diamond'    # 마름모 끝점
}

# 글꼴 패밀리 (4가지)
FONT_FAMILIES = {
    'hand': 1,      # Virgil (손글씨, Excalidraw 기본)
    'normal': 2,    # 시스템 기본 폰트
    'comic': 3,     # Comic Shanns (만화 스타일)
    'code': 4       # Cascadia (코드/모노스페이스)
}

# 글꼴 크기 프리셋
FONT_SIZES = {
    'small': 16,
    'medium': 20,   # 기본값
    'large': 28,
    'xlarge': 36
}

# 선 스타일/roughness (손그림 정도)
ROUGHNESS_LEVELS = {
    'architect': 0,   # 깔끔한 직선
    'artist': 1,      # 약간의 손그림 느낌 (기본)
    'cartoonist': 2   # 강한 손그림 느낌
}

# 기본 fillStyle (Excalidraw 원본 기본값)
DEFAULT_FILL_STYLE = 'hachure'


def generate_id(length: int = 8) -> str:
    """
    Excalidraw 요소용 고유 ID를 생성한다.

    Args:
        length: ID 길이 (기본: 8)

    Returns:
        str: 영숫자로 구성된 랜덤 ID
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def generate_seed() -> int:
    """
    Excalidraw 요소용 랜덤 seed 값을 생성한다.

    Returns:
        int: 랜덤 seed (1 ~ 2^31-1)
    """
    return random.randint(1, 2147483647)


def generate_filename(prefix: str = '') -> str:
    """
    타임스탬프가 포함된 파일명을 생성한다.

    Args:
        prefix: 파일명 접두사 (선택)

    Returns:
        str: 생성된 파일명 (예: 'exc_mindmap_20260119_143025.excalidraw')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에서 특수문자 제거
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))
    if safe_prefix:
        return f"exc_{safe_prefix}_{timestamp}.excalidraw"
    return f"exc_{timestamp}.excalidraw"


def get_output_dir(base_path: str = None) -> Path:
    """
    Excalidraw 출력 디렉토리 경로를 반환한다.
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
        # .claude/skills/make-excalidraw/scripts/ 에서 4단계 위로
        vault_root = current.parents[4]
        output_dir = vault_root / '9_Attachments' / 'images' / current_ym

    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def get_vault_root() -> Path:
    """
    볼트 루트 디렉토리 경로를 반환한다.

    Returns:
        Path: 볼트 루트 경로
    """
    current = Path(__file__).resolve()
    return current.parents[4]


# 테마 정의 (5가지)
THEMES = {
    'minimal': {
        'name': 'Minimal',
        'description': '미니멀 모노톤 스타일',
        'background': '#FFFFFF',
        'strokeColor': '#1A1A2E',
        'backgroundColor': 'transparent',
        'textColor': '#1A1A2E',
        'arrowColor': '#333333',
    },
    'elegant': {
        'name': 'Elegant',
        'description': '세련된 그레이 톤',
        'background': '#F7FAFC',
        'strokeColor': '#2D3748',
        'backgroundColor': '#EDF2F7',
        'textColor': '#2D3748',
        'arrowColor': '#4A5568',
    },
    'clean': {
        'name': 'Clean',
        'description': '깔끔한 블루 톤 비즈니스 스타일',
        'background': '#FFFFFF',
        'strokeColor': '#3B82F6',
        'backgroundColor': '#DBEAFE',
        'textColor': '#1E3A8A',
        'arrowColor': '#60A5FA',
    },
    'corporate': {
        'name': 'Corporate',
        'description': '비즈니스/기업용 파란색 톤',
        'background': '#F8F9FA',
        'strokeColor': '#1E40AF',
        'backgroundColor': '#E0E7FF',
        'textColor': '#1E3A5F',
        'arrowColor': '#3B82F6',
    },
    'dark': {
        'name': 'Dark',
        'description': '어두운 배경 테마',
        'background': '#1A1A2E',
        'strokeColor': '#E2E8F0',
        'backgroundColor': '#374151',
        'textColor': '#E2E8F0',
        'arrowColor': '#94A3B8',
    }
}


def get_theme(name: str = 'minimal') -> Dict[str, Any]:
    """
    테마 설정 딕셔너리를 반환한다.

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


# 노드 스타일 정의 (다이어그램 유형별)
NODE_STYLES = {
    'mindmap': {
        'root': {
            'backgroundColor': '#DBEAFE',
            'strokeColor': '#3B82F6',
            'strokeWidth': 2,
            'roughness': 1,
        },
        'branch': {
            'backgroundColor': '#FEF3C7',
            'strokeColor': '#F59E0B',
            'strokeWidth': 1,
            'roughness': 1,
        },
        'leaf': {
            'backgroundColor': '#D1FAE5',
            'strokeColor': '#10B981',
            'strokeWidth': 1,
            'roughness': 1,
        }
    },
    'flowchart': {
        'start': {
            'backgroundColor': '#D1FAE5',
            'strokeColor': '#10B981',
            'strokeWidth': 2,
        },
        'end': {
            'backgroundColor': '#FEE2E2',
            'strokeColor': '#EF4444',
            'strokeWidth': 2,
        },
        'process': {
            'backgroundColor': '#DBEAFE',
            'strokeColor': '#3B82F6',
            'strokeWidth': 1,
        },
        'decision': {
            'backgroundColor': '#FEF3C7',
            'strokeColor': '#F59E0B',
            'strokeWidth': 1,
        }
    },
    'concept': {
        'concept': {
            'backgroundColor': '#E0E7FF',
            'strokeColor': '#6366F1',
            'strokeWidth': 1,
        },
        'example': {
            'backgroundColor': '#FCE7F3',
            'strokeColor': '#EC4899',
            'strokeWidth': 1,
        }
    }
}


def get_node_style(diagram_type: str, node_type: str) -> Dict[str, Any]:
    """
    노드 스타일을 반환한다.

    Args:
        diagram_type: 다이어그램 유형 (mindmap, flowchart, concept)
        node_type: 노드 유형

    Returns:
        Dict: 노드 스타일 딕셔너리
    """
    if diagram_type in NODE_STYLES:
        styles = NODE_STYLES[diagram_type]
        if node_type in styles:
            return styles[node_type]
    # 기본 스타일 반환
    return {
        'backgroundColor': '#FFFFFF',
        'strokeColor': '#1A1A2E',
        'strokeWidth': 1,
        'roughness': 1,
    }


def calculate_text_dimensions(text: str, font_size: int = 20) -> Tuple[int, int]:
    """
    텍스트의 대략적인 너비와 높이를 계산한다.
    (정확한 계산은 폰트 렌더링이 필요하므로 근사치)

    Args:
        text: 텍스트 문자열
        font_size: 폰트 크기

    Returns:
        Tuple[int, int]: (width, height)
    """
    # 한글은 대략 1.5배, 영문/숫자는 0.6배 너비로 계산
    width = 0
    for char in text:
        if ord(char) > 127:  # 한글 등 비ASCII
            width += font_size * 1.0
        else:
            width += font_size * 0.6

    # 최소 너비 보장 및 여백 추가
    width = max(width, 60) + 40
    height = font_size + 30

    return int(width), int(height)


if __name__ == '__main__':
    # 테스트
    print(f"ID 예시: {generate_id()}")
    print(f"Seed 예시: {generate_seed()}")
    print(f"파일명 예시: {generate_filename('mindmap')}")
    print(f"출력 디렉토리: {get_output_dir()}")
    print(f"테마 목록: {list_themes()}")
    print(f"텍스트 크기 (한글): {calculate_text_dimensions('테스트 텍스트')}")
    print(f"텍스트 크기 (영문): {calculate_text_dimensions('Test Text')}")
