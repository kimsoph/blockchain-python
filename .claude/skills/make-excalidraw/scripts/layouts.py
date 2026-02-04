# -*- coding: utf-8 -*-
"""
make-excalidraw 스킬 레이아웃 알고리즘 모듈
마인드맵, 플로우차트, 개념도 등의 배치 알고리즘 구현
"""

import math
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .excalidraw_builder import ExcalidrawBuilder

from .utils import generate_id, calculate_text_dimensions, get_node_style


# ============================================================
# 마인드맵 레이아웃
# ============================================================

def layout_mindmap(
    builder: 'ExcalidrawBuilder',
    nodes: List[Dict[str, Any]],
    center: Tuple[float, float] = (500, 400),
    radius: float = 200,
    node_spacing: float = 80
) -> Dict[str, str]:
    """
    방사형 마인드맵 레이아웃을 적용한다.

    Args:
        builder: ExcalidrawBuilder 인스턴스
        nodes: 노드 데이터 리스트 [{'text': str, 'level': int, 'children': [...]}]
        center: 중심 좌표 (x, y)
        radius: 첫 번째 레벨의 반지름
        node_spacing: 노드 간 최소 간격

    Returns:
        Dict[str, str]: {text: element_id} 매핑
    """
    element_map = {}

    if not nodes:
        return element_map

    # 루트 노드 (level 0)와 가지 노드 분리
    root_nodes = [n for n in nodes if n.get('level', 0) == 0]
    branch_nodes = [n for n in nodes if n.get('level', 0) > 0]

    # 계층별 그룹화
    levels = {}
    for node in nodes:
        level = node.get('level', 0)
        if level not in levels:
            levels[level] = []
        levels[level].append(node)

    cx, cy = center

    # 루트 노드 배치 (중앙)
    for node in root_nodes:
        text = node['text']
        width, height = calculate_text_dimensions(text, 24)
        width = max(width, 150)
        height = max(height, 60)

        node_id = generate_id()
        builder.add_rectangle(
            cx - width/2, cy - height/2, width, height,
            text=text,
            id=node_id,
            backgroundColor='#DBEAFE',
            strokeColor='#3B82F6',
            strokeWidth=2,
            fontSize=24,
            fillStyle='hachure'  # 손그림 느낌의 빗금 채우기
        )
        element_map[text] = node_id

    # 레벨별 노드 배치
    for level in sorted(levels.keys()):
        if level == 0:
            continue

        level_nodes = levels[level]
        node_count = len(level_nodes)

        if node_count == 0:
            continue

        # 반지름 계산 (레벨이 높을수록 멀리)
        current_radius = radius * level

        # 각도 계산
        angle_step = 2 * math.pi / max(node_count, 1)
        start_angle = -math.pi / 2  # 12시 방향부터 시작

        for i, node in enumerate(level_nodes):
            text = node['text']
            angle = start_angle + i * angle_step

            # 위치 계산
            x = cx + current_radius * math.cos(angle)
            y = cy + current_radius * math.sin(angle)

            # 노드 크기
            width, height = calculate_text_dimensions(text, 18)
            width = max(width, 100)
            height = max(height, 40)

            # 색상 선택 (레벨별)
            colors = [
                ('#FEF3C7', '#F59E0B'),  # 노랑
                ('#D1FAE5', '#10B981'),  # 녹색
                ('#FCE7F3', '#EC4899'),  # 핑크
                ('#E0E7FF', '#6366F1'),  # 보라
                ('#FEE2E2', '#EF4444'),  # 빨강
            ]
            bg_color, stroke_color = colors[(level - 1) % len(colors)]

            node_id = generate_id()
            builder.add_rectangle(
                x - width/2, y - height/2, width, height,
                text=text,
                id=node_id,
                backgroundColor=bg_color,
                strokeColor=stroke_color,
                fontSize=18,
                fillStyle='hachure'  # 손그림 느낌의 빗금 채우기
            )
            element_map[text] = node_id

    # 연결선 추가 (부모-자식 관계)
    _add_mindmap_connections(builder, nodes, element_map, center)

    return element_map


def _add_mindmap_connections(
    builder: 'ExcalidrawBuilder',
    nodes: List[Dict],
    element_map: Dict[str, str],
    center: Tuple[float, float]
) -> None:
    """
    마인드맵 노드 간 연결선을 추가한다.
    """
    # 계층 구조에서 부모-자식 관계 추출
    for node in nodes:
        children = node.get('children', [])
        parent_text = node['text']

        if parent_text not in element_map:
            continue

        parent_id = element_map[parent_text]
        parent_elem = builder.get_element(parent_id)

        if not parent_elem:
            continue

        for child in children:
            child_text = child['text']
            if child_text not in element_map:
                continue

            child_id = element_map[child_text]
            child_elem = builder.get_element(child_id)

            if not child_elem:
                continue

            # 연결선 시작점/끝점 계산
            p_cx = parent_elem['x'] + parent_elem['width'] / 2
            p_cy = parent_elem['y'] + parent_elem['height'] / 2
            c_cx = child_elem['x'] + child_elem['width'] / 2
            c_cy = child_elem['y'] + child_elem['height'] / 2

            builder.add_arrow(
                (p_cx, p_cy),
                (c_cx, c_cy),
                start_binding=parent_id,
                end_binding=child_id,
                strokeWidth=1,
                strokeStyle='solid'
            )


# ============================================================
# 플로우차트 레이아웃
# ============================================================

def layout_flowchart(
    builder: 'ExcalidrawBuilder',
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    direction: str = 'TB',
    spacing: Tuple[float, float] = (150, 100)
) -> Dict[str, str]:
    """
    플로우차트 레이아웃을 적용한다.

    Args:
        builder: ExcalidrawBuilder 인스턴스
        nodes: 노드 데이터 리스트 [{'text': str, 'type': str}]
        edges: 엣지 데이터 리스트 [{'from': str, 'to': str, 'label': str, 'style': str}]
        direction: 방향 (TB, LR, BT, RL)
        spacing: (수평 간격, 수직 간격)

    Returns:
        Dict[str, str]: {text: element_id} 매핑
    """
    element_map = {}

    if not nodes:
        return element_map

    h_spacing, v_spacing = spacing
    start_x, start_y = 100, 100

    # 방향에 따른 배치 계산
    is_vertical = direction in ('TB', 'BT')
    is_reversed = direction in ('BT', 'RL')

    # 노드 배치
    for i, node in enumerate(nodes):
        text = node.get('text', '')
        node_type = node.get('type', 'process')

        # 위치 계산
        if is_vertical:
            x = start_x
            y = start_y + i * v_spacing
            if is_reversed:
                y = start_y + (len(nodes) - 1 - i) * v_spacing
        else:
            x = start_x + i * h_spacing
            y = start_y
            if is_reversed:
                x = start_x + (len(nodes) - 1 - i) * h_spacing

        # 노드 크기
        width, height = calculate_text_dimensions(text, 18)
        width = max(width, 120)
        height = max(height, 50)

        # 노드 타입별 스타일
        node_id = generate_id()

        if node_type == 'start':
            builder.add_ellipse(
                x, y, width, height,
                text=text,
                id=node_id,
                backgroundColor='#D1FAE5',
                strokeColor='#10B981',
                strokeWidth=2,
                fillStyle='solid'  # 시작/종료 노드는 단색 채우기
            )
        elif node_type == 'end':
            builder.add_ellipse(
                x, y, width, height,
                text=text,
                id=node_id,
                backgroundColor='#FEE2E2',
                strokeColor='#EF4444',
                strokeWidth=2,
                fillStyle='solid'  # 시작/종료 노드는 단색 채우기
            )
        elif node_type == 'decision':
            # 마름모는 더 큰 크기 필요
            width = max(width, 150)
            height = max(height, 100)
            builder.add_diamond(
                x, y, width, height,
                text=text,
                id=node_id,
                backgroundColor='#FEF3C7',
                strokeColor='#F59E0B',
                fillStyle='cross-hatch'  # 결정 노드는 격자 빗금
            )
        else:  # process, default
            builder.add_rectangle(
                x, y, width, height,
                text=text,
                id=node_id,
                backgroundColor='#DBEAFE',
                strokeColor='#3B82F6',
                fillStyle='hachure'  # 프로세스 노드는 빗금 채우기
            )

        element_map[text] = node_id

    # 엣지 추가
    for edge in edges:
        from_text = edge.get('from', '')
        to_text = edge.get('to', '')
        label = edge.get('label', '')
        style = edge.get('style', 'solid')

        if from_text not in element_map or to_text not in element_map:
            continue

        from_id = element_map[from_text]
        to_id = element_map[to_text]

        from_elem = builder.get_element(from_id)
        to_elem = builder.get_element(to_id)

        if not from_elem or not to_elem:
            continue

        # 연결점 계산
        f_cx = from_elem['x'] + from_elem['width'] / 2
        f_cy = from_elem['y'] + from_elem['height']
        t_cx = to_elem['x'] + to_elem['width'] / 2
        t_cy = to_elem['y']

        # 수평 방향인 경우
        if not is_vertical:
            f_cx = from_elem['x'] + from_elem['width']
            f_cy = from_elem['y'] + from_elem['height'] / 2
            t_cx = to_elem['x']
            t_cy = to_elem['y'] + to_elem['height'] / 2

        builder.add_arrow(
            (f_cx, f_cy),
            (t_cx, t_cy),
            label=label if label else None,
            start_binding=from_id,
            end_binding=to_id,
            strokeStyle='dashed' if style == 'dashed' else 'solid'
        )

    return element_map


# ============================================================
# 개념도/관계도 레이아웃 (Force-directed)
# ============================================================

def layout_concept(
    builder: 'ExcalidrawBuilder',
    nodes: List[Dict[str, Any]],
    links: List[Tuple[str, str]],
    center: Tuple[float, float] = (500, 400),
    iterations: int = 50
) -> Dict[str, str]:
    """
    Force-directed 알고리즘으로 개념도를 배치한다.

    Args:
        builder: ExcalidrawBuilder 인스턴스
        nodes: 노드 데이터 리스트 [{'text': str}]
        links: 링크 리스트 [(from_text, to_text), ...]
        center: 중심 좌표
        iterations: 시뮬레이션 반복 횟수

    Returns:
        Dict[str, str]: {text: element_id} 매핑
    """
    element_map = {}

    if not nodes:
        return element_map

    # 초기 위치 (원형 배치)
    positions = {}
    node_count = len(nodes)
    cx, cy = center

    for i, node in enumerate(nodes):
        text = node['text']
        angle = 2 * math.pi * i / node_count
        radius = 200
        positions[text] = [cx + radius * math.cos(angle), cy + radius * math.sin(angle)]

    # Force-directed 시뮬레이션
    positions = _force_directed_layout(nodes, links, positions, iterations)

    # 노드 생성
    for node in nodes:
        text = node['text']
        x, y = positions[text]

        width, height = calculate_text_dimensions(text, 18)
        width = max(width, 100)
        height = max(height, 50)

        node_id = generate_id()
        builder.add_rectangle(
            x - width/2, y - height/2, width, height,
            text=text,
            id=node_id,
            backgroundColor='#E0E7FF',
            strokeColor='#6366F1',
            fillStyle='hachure'  # 개념 노드는 빗금 채우기
        )
        element_map[text] = node_id

    # 연결선 추가
    for from_text, to_text in links:
        if from_text not in element_map or to_text not in element_map:
            continue

        from_id = element_map[from_text]
        to_id = element_map[to_text]

        from_pos = positions[from_text]
        to_pos = positions[to_text]

        builder.add_arrow(
            (from_pos[0], from_pos[1]),
            (to_pos[0], to_pos[1]),
            start_binding=from_id,
            end_binding=to_id,
            strokeWidth=1
        )

    return element_map


def _force_directed_layout(
    nodes: List[Dict],
    links: List[Tuple[str, str]],
    positions: Dict[str, List[float]],
    iterations: int = 50
) -> Dict[str, List[float]]:
    """
    간단한 Force-directed 레이아웃 알고리즘.
    """
    # 파라미터
    k = 100  # 이상적인 거리
    c_rep = 5000  # 반발력 상수
    c_att = 0.1  # 인력 상수
    damping = 0.9  # 감쇠 계수

    node_texts = [n['text'] for n in nodes]
    velocities = {text: [0.0, 0.0] for text in node_texts}

    for _ in range(iterations):
        forces = {text: [0.0, 0.0] for text in node_texts}

        # 반발력 (모든 노드 쌍)
        for i, text1 in enumerate(node_texts):
            for text2 in node_texts[i+1:]:
                pos1 = positions[text1]
                pos2 = positions[text2]

                dx = pos1[0] - pos2[0]
                dy = pos1[1] - pos2[1]
                dist = max(math.sqrt(dx*dx + dy*dy), 1)

                force = c_rep / (dist * dist)

                fx = force * dx / dist
                fy = force * dy / dist

                forces[text1][0] += fx
                forces[text1][1] += fy
                forces[text2][0] -= fx
                forces[text2][1] -= fy

        # 인력 (연결된 노드)
        for from_text, to_text in links:
            if from_text not in positions or to_text not in positions:
                continue

            pos1 = positions[from_text]
            pos2 = positions[to_text]

            dx = pos2[0] - pos1[0]
            dy = pos2[1] - pos1[1]
            dist = max(math.sqrt(dx*dx + dy*dy), 1)

            force = c_att * (dist - k)

            fx = force * dx / dist
            fy = force * dy / dist

            forces[from_text][0] += fx
            forces[from_text][1] += fy
            forces[to_text][0] -= fx
            forces[to_text][1] -= fy

        # 위치 업데이트
        for text in node_texts:
            velocities[text][0] = (velocities[text][0] + forces[text][0]) * damping
            velocities[text][1] = (velocities[text][1] + forces[text][1]) * damping

            # 속도 제한
            max_vel = 50
            vel = math.sqrt(velocities[text][0]**2 + velocities[text][1]**2)
            if vel > max_vel:
                velocities[text][0] *= max_vel / vel
                velocities[text][1] *= max_vel / vel

            positions[text][0] += velocities[text][0]
            positions[text][1] += velocities[text][1]

    return positions


# ============================================================
# 트리 레이아웃 (v1.2: 서브트리 충돌 방지 알고리즘)
# ============================================================

def _calculate_subtree_size(
    node: Dict[str, Any],
    sizes: Dict[str, Tuple[float, float]],
    direction: str,
    h_spacing: float,
    v_spacing: float
) -> Tuple[float, float]:
    """
    서브트리가 차지하는 총 크기를 재귀적으로 계산한다. (Bottom-up)

    Args:
        node: 노드 데이터 {'text': str, 'children': [...]}
        sizes: 계산된 크기를 저장할 딕셔너리 {text: (width, height)}
        direction: 방향 ('TB' 또는 'LR')
        h_spacing: 수평 간격
        v_spacing: 수직 간격

    Returns:
        (width, height): 서브트리 전체가 차지하는 크기
    """
    text = node.get('text', '')
    children = node.get('children', [])

    # 노드 자체 크기
    node_width, node_height = calculate_text_dimensions(text, 18)
    node_width = max(node_width, 100)
    node_height = max(node_height, 40)

    if not children:
        # 리프 노드
        sizes[text] = (node_width, node_height)
        return sizes[text]

    # 자식들의 서브트리 크기 먼저 계산 (재귀)
    child_sizes = []
    for child in children:
        child_size = _calculate_subtree_size(child, sizes, direction, h_spacing, v_spacing)
        child_sizes.append(child_size)

    if direction == 'LR':
        # LR: 자식들은 세로로 배치
        total_height = sum(s[1] for s in child_sizes) + (len(children) - 1) * v_spacing
        total_height = max(total_height, node_height)
        max_child_width = max(s[0] for s in child_sizes) if child_sizes else 0
        total_width = node_width + h_spacing + max_child_width
    else:  # TB
        # TB: 자식들은 가로로 배치
        total_width = sum(s[0] for s in child_sizes) + (len(children) - 1) * h_spacing
        total_width = max(total_width, node_width)
        max_child_height = max(s[1] for s in child_sizes) if child_sizes else 0
        total_height = node_height + v_spacing + max_child_height

    sizes[text] = (total_width, total_height)
    return sizes[text]


def _place_tree_node(
    builder: 'ExcalidrawBuilder',
    node: Dict[str, Any],
    x: float,
    y: float,
    level: int,
    element_map: Dict[str, str],
    subtree_sizes: Dict[str, Tuple[float, float]],
    direction: str,
    h_spacing: float,
    v_spacing: float
) -> None:
    """
    노드를 실제로 배치하고 자식 노드들을 재귀적으로 배치한다. (Top-down)

    Args:
        builder: ExcalidrawBuilder 인스턴스
        node: 노드 데이터
        x, y: 노드의 좌상단 좌표
        level: 현재 레벨 (0부터 시작)
        element_map: {text: element_id} 매핑
        subtree_sizes: 사전 계산된 서브트리 크기
        direction: 방향 ('TB' 또는 'LR')
        h_spacing: 수평 간격
        v_spacing: 수직 간격
    """
    text = node.get('text', '')
    children = node.get('children', [])

    # 노드 크기 계산
    node_width, node_height = calculate_text_dimensions(text, 18)
    node_width = max(node_width, 100)
    node_height = max(node_height, 40)

    # 색상 (레벨별)
    colors = [
        ('#DBEAFE', '#3B82F6'),  # 파랑
        ('#FEF3C7', '#F59E0B'),  # 노랑
        ('#D1FAE5', '#10B981'),  # 녹색
        ('#FCE7F3', '#EC4899'),  # 핑크
    ]
    bg_color, stroke_color = colors[level % len(colors)]

    # 노드 생성
    node_id = generate_id()
    builder.add_rectangle(
        x, y, node_width, node_height,
        text=text,
        id=node_id,
        backgroundColor=bg_color,
        strokeColor=stroke_color,
        fillStyle='hachure'
    )
    element_map[text] = node_id

    if not children:
        return

    if direction == 'LR':
        # LR: 자식들은 세로로 배치, 서브트리 높이 기반 간격 계산
        child_x = x + node_width + h_spacing

        # 자식들의 서브트리 높이 목록
        child_subtree_heights = [subtree_sizes[c['text']][1] for c in children]
        total_children_height = sum(child_subtree_heights) + (len(children) - 1) * v_spacing

        # 현재 노드 중심에서 자식들의 전체 높이를 중앙 정렬
        current_y = y + node_height / 2 - total_children_height / 2

        for child in children:
            child_text = child.get('text', '')
            child_subtree_height = subtree_sizes[child_text][1]

            # 자식 노드 자체의 높이
            child_node_width, child_node_height = calculate_text_dimensions(child_text, 18)
            child_node_height = max(child_node_height, 40)

            # 서브트리 영역 중앙에 노드 배치
            child_y = current_y + child_subtree_height / 2 - child_node_height / 2

            # 재귀 배치
            _place_tree_node(
                builder, child, child_x, child_y, level + 1,
                element_map, subtree_sizes, direction, h_spacing, v_spacing
            )

            # 연결선 추가
            child_elem = builder.get_element(element_map[child_text])
            if child_elem:
                builder.add_arrow(
                    (x + node_width, y + node_height / 2),
                    (child_elem['x'], child_elem['y'] + child_elem['height'] / 2),
                    start_binding=node_id,
                    end_binding=element_map[child_text],
                    strokeWidth=1
                )

            # 다음 자식의 Y 위치 업데이트
            current_y += child_subtree_height + v_spacing

    else:  # TB
        # TB: 자식들은 가로로 배치, 서브트리 너비 기반 간격 계산
        child_y = y + node_height + v_spacing

        # 자식들의 서브트리 너비 목록
        child_subtree_widths = [subtree_sizes[c['text']][0] for c in children]
        total_children_width = sum(child_subtree_widths) + (len(children) - 1) * h_spacing

        # 현재 노드 중심에서 자식들의 전체 너비를 중앙 정렬
        current_x = x + node_width / 2 - total_children_width / 2

        for child in children:
            child_text = child.get('text', '')
            child_subtree_width = subtree_sizes[child_text][0]

            # 자식 노드 자체의 너비
            child_node_width, child_node_height = calculate_text_dimensions(child_text, 18)
            child_node_width = max(child_node_width, 100)

            # 서브트리 영역 중앙에 노드 배치
            child_x = current_x + child_subtree_width / 2 - child_node_width / 2

            # 재귀 배치
            _place_tree_node(
                builder, child, child_x, child_y, level + 1,
                element_map, subtree_sizes, direction, h_spacing, v_spacing
            )

            # 연결선 추가
            child_elem = builder.get_element(element_map[child_text])
            if child_elem:
                builder.add_arrow(
                    (x + node_width / 2, y + node_height),
                    (child_elem['x'] + child_elem['width'] / 2, child_elem['y']),
                    start_binding=node_id,
                    end_binding=element_map[child_text],
                    strokeWidth=1
                )

            # 다음 자식의 X 위치 업데이트
            current_x += child_subtree_width + h_spacing


def layout_tree(
    builder: 'ExcalidrawBuilder',
    nodes: List[Dict[str, Any]],
    direction: str = 'TB',
    root_pos: Tuple[float, float] = (400, 50),
    h_spacing: float = 150,
    v_spacing: float = 60
) -> Dict[str, str]:
    """
    수직/수평 트리 레이아웃을 적용한다. (v1.2: 서브트리 충돌 방지)

    Args:
        builder: ExcalidrawBuilder 인스턴스
        nodes: 계층적 노드 데이터 [{'text': str, 'children': [...]}]
        direction: 방향 (TB: 위→아래, LR: 왼→오른)
        root_pos: 루트 노드 위치
        h_spacing: 수평 간격
        v_spacing: 수직 간격 (기본값: 60, v1.1 이전은 100)

    Returns:
        Dict[str, str]: {text: element_id} 매핑
    """
    element_map = {}

    if not nodes:
        return element_map

    # 1단계: 각 서브트리 크기 계산 (bottom-up)
    subtree_sizes = {}
    for node in nodes:
        _calculate_subtree_size(node, subtree_sizes, direction, h_spacing, v_spacing)

    # 2단계: 좌표 할당 및 노드 생성 (top-down)
    x, y = root_pos
    for node in nodes:
        _place_tree_node(
            builder, node, x, y, 0,
            element_map, subtree_sizes, direction, h_spacing, v_spacing
        )

    return element_map


# ============================================================
# 통합 레이아웃 함수
# ============================================================

def auto_layout(
    builder: 'ExcalidrawBuilder',
    parsed_data: Dict[str, Any],
    layout_type: str = 'auto'
) -> Dict[str, str]:
    """
    파싱된 데이터를 기반으로 자동 레이아웃을 적용한다.

    Args:
        builder: ExcalidrawBuilder 인스턴스
        parsed_data: parse_markdown() 또는 parse_dsl()의 결과
        layout_type: 레이아웃 유형 (auto, mindmap, flowchart, concept, tree)

    Returns:
        Dict[str, str]: {text: element_id} 매핑
    """
    # DSL 데이터인 경우
    if 'type' in parsed_data and parsed_data['type'] in ('mindmap', 'flowchart', 'concept'):
        layout_type = parsed_data['type']

    # 자동 감지
    if layout_type == 'auto':
        nodes = parsed_data.get('nodes', []) or parsed_data.get('flat_nodes', [])
        edges = parsed_data.get('edges', [])
        links = parsed_data.get('links', [])

        # 엣지가 있으면 플로우차트
        if edges:
            layout_type = 'flowchart'
        # 링크가 많으면 개념도
        elif len(links) > len(nodes) / 2:
            layout_type = 'concept'
        # 기본은 마인드맵
        else:
            layout_type = 'mindmap'

    # 레이아웃 적용
    if layout_type == 'mindmap':
        nodes = parsed_data.get('nodes', [])
        if not nodes:
            # flat_nodes를 계층 구조로 변환
            flat_nodes = parsed_data.get('flat_nodes', [])
            nodes = _flat_to_hierarchical(flat_nodes)
        return layout_mindmap(builder, nodes)

    elif layout_type == 'flowchart':
        nodes = parsed_data.get('nodes', parsed_data.get('flat_nodes', []))
        edges = parsed_data.get('edges', [])
        direction = parsed_data.get('direction', 'TB')
        return layout_flowchart(builder, nodes, edges, direction=direction)

    elif layout_type == 'concept':
        nodes = parsed_data.get('flat_nodes', parsed_data.get('nodes', []))
        links = parsed_data.get('links', [])
        return layout_concept(builder, nodes, links)

    elif layout_type == 'tree':
        nodes = parsed_data.get('nodes', [])
        if not nodes:
            flat_nodes = parsed_data.get('flat_nodes', [])
            nodes = _flat_to_hierarchical(flat_nodes)
        return layout_tree(builder, nodes)

    return {}


def _flat_to_hierarchical(flat_nodes: List[Dict]) -> List[Dict]:
    """
    평탄화된 노드 리스트를 계층 구조로 변환한다.
    """
    if not flat_nodes:
        return []

    result = []
    stack = []  # (level, node)

    for node in flat_nodes:
        level = node.get('level', 0)
        new_node = {
            'text': node['text'],
            'level': level,
            'children': []
        }

        # 스택에서 현재 레벨보다 낮거나 같은 것들 제거
        while stack and stack[-1][0] >= level:
            stack.pop()

        if stack:
            # 부모에 자식으로 추가
            stack[-1][1]['children'].append(new_node)
        else:
            # 루트 레벨
            result.append(new_node)

        stack.append((level, new_node))

    return result


if __name__ == '__main__':
    # 테스트
    from .excalidraw_builder import ExcalidrawBuilder

    # 마인드맵 테스트
    builder = ExcalidrawBuilder(theme='clean')
    nodes = [
        {
            'text': '중심 주제',
            'level': 0,
            'children': [
                {'text': '가지 1', 'level': 1, 'children': [
                    {'text': '세부 1-1', 'level': 2, 'children': []},
                    {'text': '세부 1-2', 'level': 2, 'children': []}
                ]},
                {'text': '가지 2', 'level': 1, 'children': []},
                {'text': '가지 3', 'level': 1, 'children': []}
            ]
        }
    ]

    element_map = layout_mindmap(builder, nodes)
    print(f"생성된 요소: {len(element_map)}")

    # 저장 테스트
    # path = builder.save('mindmap_test')
    # print(f"저장됨: {path}")
