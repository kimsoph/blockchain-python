# -*- coding: utf-8 -*-
"""
make-flowchart 스킬 유틸리티 모듈
한글 폰트 설정, 파일명 생성, 경로 관리, DSL 파싱 등
"""

import os
import platform
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional


def setup_graphviz_path() -> bool:
    """
    Windows에서 Graphviz 실행파일 경로를 PATH에 추가한다.

    Returns:
        bool: 설정 성공 여부
    """
    if platform.system() != 'Windows':
        return True

    # 일반적인 Graphviz 설치 경로들
    graphviz_paths = [
        r'C:\Program Files\Graphviz\bin',
        r'C:\Program Files (x86)\Graphviz\bin',
        r'C:\Graphviz\bin',
    ]

    current_path = os.environ.get('PATH', '')

    for gv_path in graphviz_paths:
        if os.path.exists(gv_path) and gv_path not in current_path:
            os.environ['PATH'] = gv_path + ';' + current_path
            return True

    return False


# Graphviz 경로 자동 설정 (모듈 로드 시 실행)
setup_graphviz_path()


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


def generate_filename(prefix: str, ext: str = 'png') -> str:
    """
    타임스탬프가 포함된 파일명을 생성한다.

    Args:
        prefix: 파일명 접두사
        ext: 파일 확장자 (기본: 'png')

    Returns:
        str: 생성된 파일명 (예: 'flow_diagram_20260108_143025.png')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에서 특수문자 제거
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))
    return f"flow_{safe_prefix}_{timestamp}.{ext}"


def get_output_dir(base_path: str = None) -> Path:
    """
    플로우차트 출력 디렉토리 경로를 반환한다.
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
        # .claude/skills/make-flowchart/scripts/ 에서 4단계 위로
        vault_root = current.parents[4]
        output_dir = vault_root / '9_Attachments' / 'images' / current_ym

    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


# 노드 타입 정의 (7가지)
NODE_TYPES = {
    'start': {
        'shape': 'ellipse',
        'color': '#10B981',  # 녹색
        'fontcolor': 'white',
        'description': '시작 노드'
    },
    'end': {
        'shape': 'doublecircle',
        'color': '#EF4444',  # 빨강
        'fontcolor': 'white',
        'description': '종료 노드'
    },
    'process': {
        'shape': 'box',
        'style': 'rounded',
        'color': '#3B82F6',  # 파랑
        'fontcolor': 'white',
        'description': '처리 노드'
    },
    'decision': {
        'shape': 'diamond',
        'color': '#F59E0B',  # 노랑
        'fontcolor': 'white',
        'description': '결정/분기 노드'
    },
    'io': {
        'shape': 'parallelogram',
        'color': '#8B5CF6',  # 보라
        'fontcolor': 'white',
        'description': '입출력 노드'
    },
    'document': {
        'shape': 'note',
        'color': '#F3F4F6',  # 밝은 회색
        'fontcolor': '#374151',
        'description': '문서 노드'
    },
    'database': {
        'shape': 'cylinder',
        'color': '#06B6D4',  # 시안
        'fontcolor': 'white',
        'description': '데이터베이스 노드'
    }
}


# 테마 정의 (5가지)
THEMES = {
    'minimal': {
        'name': 'Minimal',
        'description': '미니멀 모노톤 스타일',
        'bgcolor': 'white',
        'fontcolor': '#1A1A2E',
        'edge_color': '#6B7280',
        'node_colors': {
            'start': '#10B981',
            'end': '#EF4444',
            'process': '#1A1A2E',
            'decision': '#6B7280',
            'io': '#9CA3AF',
            'document': '#F3F4F6',
            'database': '#374151'
        }
    },
    'elegant': {
        'name': 'Elegant',
        'description': '세련된 그레이 톤 + 골드 액센트',
        'bgcolor': '#F7FAFC',
        'fontcolor': '#2D3748',
        'edge_color': '#4A5568',
        'node_colors': {
            'start': '#48BB78',
            'end': '#E53E3E',
            'process': '#2D3748',
            'decision': '#B7950B',
            'io': '#805AD5',
            'document': '#EDF2F7',
            'database': '#4A5568'
        }
    },
    'clean': {
        'name': 'Clean',
        'description': '깔끔한 블루 톤 비즈니스 스타일',
        'bgcolor': 'white',
        'fontcolor': '#1E3A8A',
        'edge_color': '#3B82F6',
        'node_colors': {
            'start': '#10B981',
            'end': '#EF4444',
            'process': '#2563EB',
            'decision': '#F59E0B',
            'io': '#8B5CF6',
            'document': '#E5E7EB',
            'database': '#0891B2'
        }
    },
    'corporate': {
        'name': 'Corporate',
        'description': '비즈니스/기업용 파란색 톤',
        'bgcolor': '#F8F9FA',
        'fontcolor': '#343A40',
        'edge_color': '#495057',
        'node_colors': {
            'start': '#28A745',
            'end': '#DC3545',
            'process': '#2E86AB',
            'decision': '#FFC107',
            'io': '#A23B72',
            'document': '#E9ECEF',
            'database': '#17A2B8'
        }
    },
    'dark': {
        'name': 'Dark',
        'description': '어두운 배경 테마',
        'bgcolor': '#1A1A2E',
        'fontcolor': '#E5E5E5',
        'edge_color': '#6B7280',
        'node_colors': {
            'start': '#10B981',
            'end': '#EF4444',
            'process': '#3B82F6',
            'decision': '#F59E0B',
            'io': '#8B5CF6',
            'document': '#374151',
            'database': '#06B6D4'
        }
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


# DSL 문법 패턴
DSL_PATTERNS = {
    'title': re.compile(r'^title:\s*(.+)$', re.IGNORECASE),
    'direction': re.compile(r'^direction:\s*(TB|LR|BT|RL)$', re.IGNORECASE),
    'node_start': re.compile(r'^\[시작\]\s*(\w+):\s*(.+)$'),
    'node_end': re.compile(r'^\[종료\]\s*(\w+):\s*(.+)$'),
    'node_process': re.compile(r'^\[프로세스\]\s*(\w+):\s*(.+)$'),
    'node_decision': re.compile(r'^\[결정\]\s*(\w+):\s*(.+)$'),
    'node_io': re.compile(r'^\[입출력\]\s*(\w+):\s*(.+)$'),
    'node_document': re.compile(r'^\[문서\]\s*(\w+):\s*(.+)$'),
    'node_database': re.compile(r'^\[데이터베이스\]\s*(\w+):\s*(.+)$'),
    'edge_solid_label': re.compile(r'^(\w+)\s*->\s*(\w+):\s*(.+)$'),
    'edge_solid': re.compile(r'^(\w+)\s*->\s*(\w+)$'),
    'edge_dashed_label': re.compile(r'^(\w+)\s*-->\s*(\w+):\s*(.+)$'),
    'edge_dashed': re.compile(r'^(\w+)\s*-->\s*(\w+)$'),
}

# 영문 노드 타입 매핑
DSL_NODE_ENGLISH = {
    'start': re.compile(r'^\[start\]\s*(\w+):\s*(.+)$', re.IGNORECASE),
    'end': re.compile(r'^\[end\]\s*(\w+):\s*(.+)$', re.IGNORECASE),
    'process': re.compile(r'^\[process\]\s*(\w+):\s*(.+)$', re.IGNORECASE),
    'decision': re.compile(r'^\[decision\]\s*(\w+):\s*(.+)$', re.IGNORECASE),
    'io': re.compile(r'^\[io\]\s*(\w+):\s*(.+)$', re.IGNORECASE),
    'document': re.compile(r'^\[document\]\s*(\w+):\s*(.+)$', re.IGNORECASE),
    'database': re.compile(r'^\[database\]\s*(\w+):\s*(.+)$', re.IGNORECASE),
}


def parse_flowchart_dsl(text: str) -> Dict[str, Any]:
    """
    DSL 텍스트를 파싱하여 플로우차트 구성요소를 반환한다.

    DSL 문법:
        title: 제목
        direction: TB (또는 LR, BT, RL)
        [시작] node_id: 라벨
        [프로세스] node_id: 라벨
        [결정] node_id: 라벨
        [입출력] node_id: 라벨
        [문서] node_id: 라벨
        [데이터베이스] node_id: 라벨
        [종료] node_id: 라벨
        node1 -> node2
        node1 -> node2: 라벨
        node1 --> node2: 점선

    Args:
        text: DSL 텍스트

    Returns:
        Dict: {
            'title': str,
            'direction': str,
            'nodes': List[Tuple[node_id, label, node_type]],
            'edges': List[Tuple[from_node, to_node, label, style]]
        }
    """
    result = {
        'title': '',
        'direction': 'TB',
        'nodes': [],
        'edges': []
    }

    # 한글 -> 영문 노드 타입 매핑
    korean_to_type = {
        'node_start': 'start',
        'node_end': 'end',
        'node_process': 'process',
        'node_decision': 'decision',
        'node_io': 'io',
        'node_document': 'document',
        'node_database': 'database',
    }

    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # 타이틀 파싱
        match = DSL_PATTERNS['title'].match(line)
        if match:
            result['title'] = match.group(1).strip()
            continue

        # 방향 파싱
        match = DSL_PATTERNS['direction'].match(line)
        if match:
            result['direction'] = match.group(1).upper()
            continue

        # 한글 노드 파싱
        node_matched = False
        for pattern_name, pattern in DSL_PATTERNS.items():
            if pattern_name.startswith('node_'):
                match = pattern.match(line)
                if match:
                    node_id = match.group(1)
                    label = match.group(2).strip()
                    node_type = korean_to_type[pattern_name]
                    result['nodes'].append((node_id, label, node_type))
                    node_matched = True
                    break

        if node_matched:
            continue

        # 영문 노드 파싱
        for node_type, pattern in DSL_NODE_ENGLISH.items():
            match = pattern.match(line)
            if match:
                node_id = match.group(1)
                label = match.group(2).strip()
                result['nodes'].append((node_id, label, node_type))
                node_matched = True
                break

        if node_matched:
            continue

        # 엣지 파싱 (점선 + 라벨)
        match = DSL_PATTERNS['edge_dashed_label'].match(line)
        if match:
            from_node = match.group(1)
            to_node = match.group(2)
            label = match.group(3).strip()
            result['edges'].append((from_node, to_node, label, 'dashed'))
            continue

        # 엣지 파싱 (점선)
        match = DSL_PATTERNS['edge_dashed'].match(line)
        if match:
            from_node = match.group(1)
            to_node = match.group(2)
            result['edges'].append((from_node, to_node, '', 'dashed'))
            continue

        # 엣지 파싱 (실선 + 라벨)
        match = DSL_PATTERNS['edge_solid_label'].match(line)
        if match:
            from_node = match.group(1)
            to_node = match.group(2)
            label = match.group(3).strip()
            result['edges'].append((from_node, to_node, label, 'solid'))
            continue

        # 엣지 파싱 (실선)
        match = DSL_PATTERNS['edge_solid'].match(line)
        if match:
            from_node = match.group(1)
            to_node = match.group(2)
            result['edges'].append((from_node, to_node, '', 'solid'))
            continue

    return result


if __name__ == '__main__':
    # 테스트
    print(f"한글 폰트: {get_korean_font()}")
    print(f"파일명 예시: {generate_filename('test')}")
    print(f"출력 디렉토리: {get_output_dir()}")
    print(f"테마 목록: {list_themes()}")
    print(f"노드 타입: {list(NODE_TYPES.keys())}")

    # DSL 파싱 테스트
    test_dsl = """
title: 테스트 플로우차트
direction: TB
[시작] start: 시작
[프로세스] proc1: 처리 1
[결정] dec1: 조건?
[종료] end: 종료
start -> proc1
proc1 -> dec1
dec1 -> end: Yes
dec1 --> start: No
    """
    result = parse_flowchart_dsl(test_dsl)
    print(f"\nDSL 파싱 결과:")
    print(f"  제목: {result['title']}")
    print(f"  방향: {result['direction']}")
    print(f"  노드: {result['nodes']}")
    print(f"  엣지: {result['edges']}")
