# -*- coding: utf-8 -*-
"""
make-diagram 스킬 유틸리티 모듈
한글 폰트 설정, 파일명 생성, 경로 관리, 테마, DSL 파싱 등
"""

import os
import platform
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


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
        str: 생성된 파일명 (예: 'diag_diagram_20251231_143025.png')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에서 특수문자 제거
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))
    return f"diag_{safe_prefix}_{timestamp}.{ext}"


def get_output_dir(base_path: str = None) -> Path:
    """
    다이어그램 출력 디렉토리 경로를 반환한다.
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
        # .claude/skills/make-diagram/scripts/ 에서 4단계 위로
        vault_root = current.parents[4]
        output_dir = vault_root / '9_Attachments' / 'images' / current_ym

    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


# ============================================================
# 테마 정의
# ============================================================

THEMES = {
    'minimal': {
        'name': 'Minimal',
        'description': '깔끔한 미니멀 스타일',
        'bgcolor': '#FFFFFF',
        'node_fillcolor': '#F8FAFC',
        'node_fontcolor': '#1A1A2E',
        'node_color': '#E2E8F0',
        'edge_color': '#94A3B8',
        'edge_fontcolor': '#64748B',
        'group_bgcolor': '#F1F5F9',
        'group_color': '#CBD5E1',
        'group_fontcolor': '#475569',
        'title_color': '#1A1A2E',
        'font_name': get_korean_font(),
    },
    'elegant': {
        'name': 'Elegant',
        'description': '골드 액센트의 고급스러운 스타일',
        'bgcolor': '#F7FAFC',
        'node_fillcolor': '#FFFFFF',
        'node_fontcolor': '#2D3748',
        'node_color': '#B7950B',
        'edge_color': '#718096',
        'edge_fontcolor': '#4A5568',
        'group_bgcolor': '#EDF2F7',
        'group_color': '#B7950B',
        'group_fontcolor': '#2D3748',
        'title_color': '#2D3748',
        'font_name': get_korean_font(),
    },
    'clean': {
        'name': 'Clean',
        'description': '비비드 블루 비즈니스 스타일',
        'bgcolor': '#FFFFFF',
        'node_fillcolor': '#EFF6FF',
        'node_fontcolor': '#1E3A8A',
        'node_color': '#2563EB',
        'edge_color': '#3B82F6',
        'edge_fontcolor': '#1E40AF',
        'group_bgcolor': '#DBEAFE',
        'group_color': '#2563EB',
        'group_fontcolor': '#1E3A8A',
        'title_color': '#1E3A8A',
        'font_name': get_korean_font(),
    },
    'corporate': {
        'name': 'Corporate',
        'description': '기업용 표준 블루 스타일',
        'bgcolor': '#F8F9FA',
        'node_fillcolor': '#E3F2FD',
        'node_fontcolor': '#1565C0',
        'node_color': '#2E86AB',
        'edge_color': '#2E86AB',
        'edge_fontcolor': '#1565C0',
        'group_bgcolor': '#BBDEFB',
        'group_color': '#1976D2',
        'group_fontcolor': '#0D47A1',
        'title_color': '#0D47A1',
        'font_name': get_korean_font(),
    },
    'dark': {
        'name': 'Dark',
        'description': '어두운 배경의 모던 스타일',
        'bgcolor': '#1A1A2E',
        'node_fillcolor': '#16213E',
        'node_fontcolor': '#E8E8E8',
        'node_color': '#0F3460',
        'edge_color': '#E94560',
        'edge_fontcolor': '#AAAAAA',
        'group_bgcolor': '#0F3460',
        'group_color': '#E94560',
        'group_fontcolor': '#E8E8E8',
        'title_color': '#E8E8E8',
        'font_name': get_korean_font(),
    },
}


def get_theme(name: str = 'minimal') -> Dict[str, str]:
    """
    테마 색상 딕셔너리를 반환한다.

    Args:
        name: 테마 이름 (minimal, elegant, clean, corporate, dark)

    Returns:
        Dict[str, str]: 테마 색상 딕셔너리
    """
    if name not in THEMES:
        print(f"[경고] '{name}' 테마를 찾을 수 없습니다. 'minimal' 테마를 사용합니다.")
        name = 'minimal'
    return THEMES[name].copy()


def list_themes() -> List[str]:
    """
    사용 가능한 테마 목록을 반환한다.

    Returns:
        List[str]: 테마 이름 리스트
    """
    return list(THEMES.keys())


# ============================================================
# DSL 파싱
# ============================================================

def parse_diagram_dsl(text: str) -> Dict[str, Any]:
    """
    다이어그램 DSL 텍스트를 파싱하여 구조화된 데이터로 변환한다.

    DSL 문법:
        title: 제목
        type: block

        group GroupName {
            [Node Label]
            [Another Node]
        }

        [Node A] -> [Node B]
        [Node A] <-> [Node B]: 양방향
        [Node A] --> [Node B]: 점선

    Args:
        text: DSL 텍스트

    Returns:
        Dict[str, Any]: 파싱된 다이어그램 데이터
            - title: str
            - type: str
            - nodes: List[Dict] - {'id': str, 'label': str, 'group': str or None}
            - groups: List[Dict] - {'id': str, 'label': str, 'nodes': List[str]}
            - edges: List[Dict] - {'from': str, 'to': str, 'label': str, 'bidirectional': bool, 'style': str}
    """
    result = {
        'title': '',
        'type': 'block',
        'nodes': [],
        'groups': [],
        'edges': [],
    }

    lines = text.strip().split('\n')
    node_ids = {}  # label -> id 매핑
    node_counter = 0
    current_group = None
    current_group_nodes = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # title: 제목
        if line.lower().startswith('title:'):
            result['title'] = line[6:].strip()
            continue

        # type: block/org/hierarchy/relation
        if line.lower().startswith('type:'):
            diagram_type = line[5:].strip().lower()
            if diagram_type in ('block', 'org', 'hierarchy', 'relation'):
                result['type'] = diagram_type
            continue

        # group GroupName {
        group_start = re.match(r'^group\s+(.+?)\s*\{', line, re.IGNORECASE)
        if group_start:
            current_group = group_start.group(1).strip()
            current_group_nodes = []
            continue

        # } (그룹 종료)
        if line == '}' and current_group:
            group_id = f"group_{len(result['groups'])}"
            result['groups'].append({
                'id': group_id,
                'label': current_group,
                'nodes': current_group_nodes.copy(),
            })
            current_group = None
            current_group_nodes = []
            continue

        # 노드 정의 (그룹 내부): [Node Label]
        if current_group:
            node_match = re.match(r'^\[(.+?)\]$', line)
            if node_match:
                label = node_match.group(1).strip()
                if label not in node_ids:
                    node_id = f"node_{node_counter}"
                    node_counter += 1
                    node_ids[label] = node_id
                    result['nodes'].append({
                        'id': node_id,
                        'label': label,
                        'group': current_group,
                    })
                current_group_nodes.append(node_ids[label])
            continue

        # 엣지 정의: [A] -> [B] 또는 [A] <-> [B] 또는 [A] --> [B]
        # 패턴: [from] (->|<->|-->) [to] (: label)?
        edge_match = re.match(r'^\[(.+?)\]\s*(-->|<->|->)\s*\[(.+?)\](?:\s*:\s*(.+))?$', line)
        if edge_match:
            from_label = edge_match.group(1).strip()
            arrow = edge_match.group(2)
            to_label = edge_match.group(3).strip()
            edge_label = edge_match.group(4).strip() if edge_match.group(4) else ''

            # 노드가 없으면 추가
            for label in [from_label, to_label]:
                if label not in node_ids:
                    node_id = f"node_{node_counter}"
                    node_counter += 1
                    node_ids[label] = node_id
                    result['nodes'].append({
                        'id': node_id,
                        'label': label,
                        'group': None,
                    })

            # 엣지 추가
            bidirectional = (arrow == '<->')
            style = 'dashed' if arrow == '-->' else 'solid'

            result['edges'].append({
                'from': node_ids[from_label],
                'to': node_ids[to_label],
                'from_label': from_label,
                'to_label': to_label,
                'label': edge_label,
                'bidirectional': bidirectional,
                'style': style,
            })
            continue

        # 단독 노드 정의: [Node Label]
        node_match = re.match(r'^\[(.+?)\]$', line)
        if node_match:
            label = node_match.group(1).strip()
            if label not in node_ids:
                node_id = f"node_{node_counter}"
                node_counter += 1
                node_ids[label] = node_id
                result['nodes'].append({
                    'id': node_id,
                    'label': label,
                    'group': None,
                })
            continue

    return result


def get_layout_engine(diagram_type: str) -> str:
    """
    다이어그램 타입에 따른 레이아웃 엔진을 반환한다.

    Args:
        diagram_type: 다이어그램 타입 (block, org, hierarchy, relation)

    Returns:
        str: Graphviz 레이아웃 엔진 이름
    """
    engines = {
        'block': 'dot',
        'org': 'dot',
        'hierarchy': 'dot',
        'relation': 'neato',
    }
    return engines.get(diagram_type, 'dot')


def get_rankdir(diagram_type: str) -> str:
    """
    다이어그램 타입에 따른 방향을 반환한다.

    Args:
        diagram_type: 다이어그램 타입

    Returns:
        str: Graphviz rankdir (TB, LR 등)
    """
    # block, org, hierarchy는 모두 TB (위에서 아래)
    # relation은 방향 없음 (neato 사용)
    if diagram_type == 'relation':
        return None
    return 'TB'


if __name__ == '__main__':
    # 테스트
    print(f"한글 폰트: {get_korean_font()}")
    print(f"파일명 예시: {generate_filename('test_diagram')}")
    print(f"출력 디렉토리: {get_output_dir()}")
    print(f"테마 목록: {list_themes()}")
    print(f"minimal 테마: {get_theme('minimal')}")

    # DSL 파싱 테스트
    dsl_text = """
title: 시스템 아키텍처
type: block

group Frontend {
    [Web App]
    [Mobile App]
}

group Backend {
    [API Server]
    [Worker]
}

[Web App] -> [API Server]
[Mobile App] -> [API Server]
[API Server] --> [Worker]: 비동기
[API Server] <-> [Database]: 양방향
"""

    parsed = parse_diagram_dsl(dsl_text)
    print(f"\n파싱 결과:")
    print(f"  제목: {parsed['title']}")
    print(f"  타입: {parsed['type']}")
    print(f"  노드 수: {len(parsed['nodes'])}")
    print(f"  그룹 수: {len(parsed['groups'])}")
    print(f"  엣지 수: {len(parsed['edges'])}")
