# -*- coding: utf-8 -*-
"""
make-diagram 스킬 메인 모듈
Graphviz를 사용하여 다이어그램을 생성한다.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

try:
    import graphviz
except ImportError:
    raise ImportError(
        "graphviz 패키지가 설치되어 있지 않습니다.\n"
        "설치: pip install graphviz\n"
        "또한 시스템에 Graphviz가 설치되어 있어야 합니다.\n"
        "Windows: https://graphviz.org/download/ 에서 다운로드"
    )

try:
    from .utils import (
        get_korean_font,
        generate_filename,
        get_output_dir,
        get_theme,
        parse_diagram_dsl,
        get_layout_engine,
        get_rankdir,
    )
except ImportError:
    from utils import (
        get_korean_font,
        generate_filename,
        get_output_dir,
        get_theme,
        parse_diagram_dsl,
        get_layout_engine,
        get_rankdir,
    )


class DiagramDrawer:
    """
    Graphviz 기반 다이어그램 생성 클래스

    다이어그램 타입:
        - block: 블록 다이어그램 (기본)
        - org: 조직도
        - hierarchy: 계층 구조
        - relation: 관계도

    사용 예시:
        drawer = DiagramDrawer(diagram_type='block', theme='minimal')
        drawer.set_title('시스템 아키텍처')
        drawer.add_group('frontend', 'Frontend')
        drawer.add_node('web', 'Web App', group='frontend')
        drawer.add_node('api', 'API Server')
        drawer.add_edge('web', 'api')
        drawer.save('architecture')
    """

    def __init__(
        self,
        diagram_type: str = 'block',
        theme: str = 'minimal',
        dpi: int = 300,
        output_dir: str = None,
    ):
        """
        DiagramDrawer 초기화

        Args:
            diagram_type: 다이어그램 타입 (block, org, hierarchy, relation)
            theme: 테마 이름 (minimal, elegant, clean, corporate, dark)
            dpi: 해상도 (기본: 300)
            output_dir: 출력 디렉토리 (기본: 자동 설정)
        """
        self.diagram_type = diagram_type
        self.theme_name = theme
        self.theme = get_theme(theme)
        self.dpi = dpi
        self.output_dir = Path(output_dir) if output_dir else get_output_dir()

        self.title = ''
        self.nodes: Dict[str, Dict[str, Any]] = {}  # node_id -> node_info
        self.groups: Dict[str, Dict[str, Any]] = {}  # group_id -> group_info
        self.edges: List[Dict[str, Any]] = []

        self._graph = None

    def set_title(self, title: str) -> 'DiagramDrawer':
        """
        다이어그램 제목을 설정한다.

        Args:
            title: 제목 문자열

        Returns:
            self (메서드 체이닝용)
        """
        self.title = title
        return self

    def set_type(self, diagram_type: str) -> 'DiagramDrawer':
        """
        다이어그램 타입을 설정한다.

        Args:
            diagram_type: 다이어그램 타입 (block, org, hierarchy, relation)

        Returns:
            self (메서드 체이닝용)
        """
        if diagram_type in ('block', 'org', 'hierarchy', 'relation'):
            self.diagram_type = diagram_type
        else:
            print(f"[경고] '{diagram_type}'은 지원하지 않는 타입입니다. 'block'을 사용합니다.")
            self.diagram_type = 'block'
        return self

    def add_node(
        self,
        node_id: str,
        label: str,
        group: str = None,
        **kwargs
    ) -> 'DiagramDrawer':
        """
        노드를 추가한다.

        Args:
            node_id: 노드 ID (고유 식별자)
            label: 노드 라벨 (표시 텍스트)
            group: 소속 그룹 ID (선택)
            **kwargs: 추가 속성 (shape, style, fillcolor 등)

        Returns:
            self (메서드 체이닝용)
        """
        self.nodes[node_id] = {
            'id': node_id,
            'label': label,
            'group': group,
            'attrs': kwargs,
        }
        return self

    def add_group(
        self,
        group_id: str,
        label: str = '',
        style: str = 'box',
    ) -> 'DiagramDrawer':
        """
        그룹(서브그래프/클러스터)을 추가한다.

        Args:
            group_id: 그룹 ID
            label: 그룹 라벨 (표시 텍스트)
            style: 그룹 스타일 (box, rounded 등)

        Returns:
            self (메서드 체이닝용)
        """
        self.groups[group_id] = {
            'id': group_id,
            'label': label if label else group_id,
            'style': style,
        }
        return self

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        label: str = '',
        bidirectional: bool = False,
        style: str = 'solid',
    ) -> 'DiagramDrawer':
        """
        엣지(연결선)를 추가한다.

        Args:
            from_node: 시작 노드 ID
            to_node: 끝 노드 ID
            label: 엣지 라벨 (선택)
            bidirectional: 양방향 여부 (True면 <->)
            style: 선 스타일 ('solid' 또는 'dashed')

        Returns:
            self (메서드 체이닝용)
        """
        self.edges.append({
            'from': from_node,
            'to': to_node,
            'label': label,
            'bidirectional': bidirectional,
            'style': style,
        })
        return self

    def parse_dsl(self, dsl_text: str) -> 'DiagramDrawer':
        """
        DSL 텍스트를 파싱하여 다이어그램을 구성한다.

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
            dsl_text: DSL 텍스트

        Returns:
            self (메서드 체이닝용)
        """
        parsed = parse_diagram_dsl(dsl_text)

        # 제목 설정
        if parsed['title']:
            self.title = parsed['title']

        # 타입 설정
        if parsed['type']:
            self.diagram_type = parsed['type']

        # 그룹 추가
        for group_data in parsed['groups']:
            self.add_group(
                group_id=group_data['id'],
                label=group_data['label'],
            )

        # 노드 추가
        for node_data in parsed['nodes']:
            self.add_node(
                node_id=node_data['id'],
                label=node_data['label'],
                group=node_data['group'],
            )

        # 엣지 추가
        for edge_data in parsed['edges']:
            self.add_edge(
                from_node=edge_data['from'],
                to_node=edge_data['to'],
                label=edge_data['label'],
                bidirectional=edge_data['bidirectional'],
                style=edge_data['style'],
            )

        return self

    def create_org_chart(self, hierarchy: dict) -> 'DiagramDrawer':
        """
        조직도를 생성한다.

        Args:
            hierarchy: 계층 구조 딕셔너리
                예: {
                    'CEO': {
                        'CTO': ['개발1팀', '개발2팀'],
                        'CFO': ['재무팀', '회계팀'],
                    }
                }

        Returns:
            self (메서드 체이닝용)
        """
        self.diagram_type = 'org'
        node_counter = [0]  # mutable counter

        def _add_nodes_recursive(parent: str, children: Union[dict, list], parent_id: str = None):
            # 현재 노드 추가
            if parent_id is None:
                node_id = f"node_{node_counter[0]}"
                node_counter[0] += 1
                self.add_node(node_id, parent)
                parent_id = node_id

            if isinstance(children, dict):
                for child_name, grandchildren in children.items():
                    child_id = f"node_{node_counter[0]}"
                    node_counter[0] += 1
                    self.add_node(child_id, child_name)
                    self.add_edge(parent_id, child_id)
                    _add_nodes_recursive(child_name, grandchildren, child_id)
            elif isinstance(children, list):
                for child_name in children:
                    child_id = f"node_{node_counter[0]}"
                    node_counter[0] += 1
                    self.add_node(child_id, child_name)
                    self.add_edge(parent_id, child_id)

        for root_name, children in hierarchy.items():
            _add_nodes_recursive(root_name, children)

        return self

    def create_hierarchy(self, root: str, children: list) -> 'DiagramDrawer':
        """
        단순 계층 구조를 생성한다.

        Args:
            root: 루트 노드 라벨
            children: 자식 노드 라벨 리스트

        Returns:
            self (메서드 체이닝용)
        """
        self.diagram_type = 'hierarchy'

        root_id = 'root'
        self.add_node(root_id, root)

        for i, child in enumerate(children):
            child_id = f"child_{i}"
            self.add_node(child_id, child)
            self.add_edge(root_id, child_id)

        return self

    def render(self) -> graphviz.Digraph:
        """
        다이어그램을 Graphviz 객체로 렌더링한다.

        Returns:
            graphviz.Digraph: Graphviz 다이어그램 객체
        """
        # 레이아웃 엔진 선택
        engine = get_layout_engine(self.diagram_type)
        rankdir = get_rankdir(self.diagram_type)

        # relation 타입은 무방향 그래프
        if self.diagram_type == 'relation':
            graph = graphviz.Graph(format='png', engine=engine)
        else:
            graph = graphviz.Digraph(format='png', engine=engine)

        # 그래프 속성 설정
        graph.attr(
            dpi=str(self.dpi),
            bgcolor=self.theme['bgcolor'],
            fontname=self.theme['font_name'],
            fontsize='14',
            pad='0.5',
            nodesep='0.5',
            ranksep='0.75',
        )

        if rankdir:
            graph.attr(rankdir=rankdir)

        # 제목 설정
        if self.title:
            graph.attr(
                label=self.title,
                labelloc='t',
                fontsize='18',
                fontcolor=self.theme['title_color'],
            )

        # 기본 노드 속성
        graph.attr(
            'node',
            shape='box',
            style='filled,rounded',
            fillcolor=self.theme['node_fillcolor'],
            color=self.theme['node_color'],
            fontcolor=self.theme['node_fontcolor'],
            fontname=self.theme['font_name'],
            fontsize='12',
            margin='0.3,0.2',
        )

        # 기본 엣지 속성
        graph.attr(
            'edge',
            color=self.theme['edge_color'],
            fontcolor=self.theme['edge_fontcolor'],
            fontname=self.theme['font_name'],
            fontsize='10',
            arrowsize='0.8',
        )

        # 그룹(클러스터) 생성 및 노드 배치
        group_nodes = {g_id: [] for g_id in self.groups}
        ungrouped_nodes = []

        for node_id, node_info in self.nodes.items():
            group = node_info.get('group')
            if group:
                # 그룹 ID 찾기 (그룹 라벨로 매핑)
                matched_group_id = None
                for g_id, g_info in self.groups.items():
                    if g_info['label'] == group or g_id == group:
                        matched_group_id = g_id
                        break
                if matched_group_id:
                    group_nodes[matched_group_id].append(node_info)
                else:
                    ungrouped_nodes.append(node_info)
            else:
                ungrouped_nodes.append(node_info)

        # 그룹 서브그래프 생성
        for group_id, group_info in self.groups.items():
            with graph.subgraph(name=f'cluster_{group_id}') as c:
                c.attr(
                    label=group_info['label'],
                    style='rounded',
                    bgcolor=self.theme['group_bgcolor'],
                    color=self.theme['group_color'],
                    fontcolor=self.theme['group_fontcolor'],
                    fontname=self.theme['font_name'],
                    fontsize='12',
                    margin='16',
                )
                for node_info in group_nodes.get(group_id, []):
                    node_attrs = {
                        'label': node_info['label'],
                    }
                    node_attrs.update(node_info.get('attrs', {}))
                    c.node(node_info['id'], **node_attrs)

        # 그룹에 속하지 않은 노드 추가
        for node_info in ungrouped_nodes:
            node_attrs = {
                'label': node_info['label'],
            }
            node_attrs.update(node_info.get('attrs', {}))
            graph.node(node_info['id'], **node_attrs)

        # 엣지 추가
        for edge_info in self.edges:
            edge_attrs = {}

            if edge_info['label']:
                edge_attrs['label'] = edge_info['label']

            if edge_info['bidirectional']:
                edge_attrs['dir'] = 'both'

            if edge_info['style'] == 'dashed':
                edge_attrs['style'] = 'dashed'

            graph.edge(edge_info['from'], edge_info['to'], **edge_attrs)

        self._graph = graph
        return graph

    def save(self, filename: str = 'diagram') -> str:
        """
        다이어그램을 파일로 저장한다.

        Args:
            filename: 파일명 (확장자 제외, 접두사 자동 추가)

        Returns:
            str: 저장된 파일의 전체 경로
        """
        if self._graph is None:
            self.render()

        # 파일명 생성
        full_filename = generate_filename(filename, 'png')
        # 확장자 제거 (graphviz가 자동으로 붙임)
        base_filename = full_filename.rsplit('.', 1)[0]
        output_path = self.output_dir / base_filename

        # 렌더링 및 저장
        try:
            self._graph.render(str(output_path), cleanup=True)
            final_path = str(output_path) + '.png'
            print(f"[OK] 다이어그램 저장 완료: {final_path}")

            # 옵시디언 삽입 코드 출력
            relative_path = f"images/{self.output_dir.name}/{base_filename}.png"
            print(f"[INFO] 옵시디언 삽입: ![[{relative_path}]]")

            return final_path
        except Exception as e:
            print(f"[ERROR] 다이어그램 저장 실패: {e}")
            raise

    def get_source(self) -> str:
        """
        Graphviz DOT 소스 코드를 반환한다.

        Returns:
            str: DOT 소스 코드
        """
        if self._graph is None:
            self.render()
        return self._graph.source


# ============================================================
# 편의 함수
# ============================================================

def create_block_diagram(
    title: str,
    nodes: List[Dict[str, str]],
    edges: List[Dict[str, str]],
    groups: List[Dict[str, Any]] = None,
    theme: str = 'minimal',
    filename: str = 'block_diagram',
) -> str:
    """
    블록 다이어그램을 빠르게 생성한다.

    Args:
        title: 다이어그램 제목
        nodes: 노드 리스트 [{'id': 'n1', 'label': 'Node 1', 'group': 'g1'}, ...]
        edges: 엣지 리스트 [{'from': 'n1', 'to': 'n2', 'label': ''}, ...]
        groups: 그룹 리스트 [{'id': 'g1', 'label': 'Group 1'}, ...]
        theme: 테마 이름
        filename: 저장 파일명

    Returns:
        str: 저장된 파일 경로
    """
    drawer = DiagramDrawer(diagram_type='block', theme=theme)
    drawer.set_title(title)

    # 그룹 추가
    if groups:
        for group in groups:
            drawer.add_group(
                group_id=group.get('id', group.get('label', '')),
                label=group.get('label', ''),
            )

    # 노드 추가
    for node in nodes:
        drawer.add_node(
            node_id=node['id'],
            label=node.get('label', node['id']),
            group=node.get('group'),
        )

    # 엣지 추가
    for edge in edges:
        drawer.add_edge(
            from_node=edge['from'],
            to_node=edge['to'],
            label=edge.get('label', ''),
            bidirectional=edge.get('bidirectional', False),
            style=edge.get('style', 'solid'),
        )

    return drawer.save(filename)


def create_org_chart(
    title: str,
    hierarchy: dict,
    theme: str = 'minimal',
    filename: str = 'org_chart',
) -> str:
    """
    조직도를 빠르게 생성한다.

    Args:
        title: 다이어그램 제목
        hierarchy: 계층 구조 딕셔너리
        theme: 테마 이름
        filename: 저장 파일명

    Returns:
        str: 저장된 파일 경로
    """
    drawer = DiagramDrawer(diagram_type='org', theme=theme)
    drawer.set_title(title)
    drawer.create_org_chart(hierarchy)
    return drawer.save(filename)


def create_hierarchy_diagram(
    title: str,
    root: str,
    children: List[str],
    theme: str = 'minimal',
    filename: str = 'hierarchy',
) -> str:
    """
    단순 계층 구조 다이어그램을 빠르게 생성한다.

    Args:
        title: 다이어그램 제목
        root: 루트 노드 라벨
        children: 자식 노드 라벨 리스트
        theme: 테마 이름
        filename: 저장 파일명

    Returns:
        str: 저장된 파일 경로
    """
    drawer = DiagramDrawer(diagram_type='hierarchy', theme=theme)
    drawer.set_title(title)
    drawer.create_hierarchy(root, children)
    return drawer.save(filename)


def create_from_dsl(
    dsl_text: str,
    theme: str = 'minimal',
    filename: str = 'diagram',
) -> str:
    """
    DSL 텍스트로부터 다이어그램을 생성한다.

    Args:
        dsl_text: DSL 텍스트
        theme: 테마 이름
        filename: 저장 파일명

    Returns:
        str: 저장된 파일 경로
    """
    drawer = DiagramDrawer(theme=theme)
    drawer.parse_dsl(dsl_text)
    return drawer.save(filename)


if __name__ == '__main__':
    # 테스트
    print("=== DiagramDrawer 테스트 ===\n")

    # 1. 기본 블록 다이어그램
    print("1. 기본 블록 다이어그램 생성")
    drawer = DiagramDrawer(diagram_type='block', theme='minimal')
    drawer.set_title('시스템 아키텍처')

    drawer.add_group('frontend', 'Frontend')
    drawer.add_group('backend', 'Backend')

    drawer.add_node('web', 'Web App', group='Frontend')
    drawer.add_node('mobile', 'Mobile App', group='Frontend')
    drawer.add_node('api', 'API Server', group='Backend')
    drawer.add_node('worker', 'Worker', group='Backend')
    drawer.add_node('db', 'Database')

    drawer.add_edge('web', 'api')
    drawer.add_edge('mobile', 'api')
    drawer.add_edge('api', 'worker', style='dashed', label='async')
    drawer.add_edge('api', 'db', bidirectional=True)

    print(f"DOT 소스:\n{drawer.get_source()}\n")

    # 2. DSL 파싱 테스트
    print("2. DSL 파싱 테스트")
    dsl_text = """
title: 데이터 파이프라인
type: block

group Source {
    [API]
    [File]
}

group Processing {
    [ETL]
    [Validation]
}

[API] -> [ETL]
[File] -> [ETL]
[ETL] -> [Validation]
[Validation] --> [Storage]: 비동기
"""

    drawer2 = DiagramDrawer(theme='clean')
    drawer2.parse_dsl(dsl_text)
    print(f"제목: {drawer2.title}")
    print(f"타입: {drawer2.diagram_type}")
    print(f"노드 수: {len(drawer2.nodes)}")
    print(f"그룹 수: {len(drawer2.groups)}")
    print(f"엣지 수: {len(drawer2.edges)}\n")

    # 3. 조직도 테스트
    print("3. 조직도 테스트")
    hierarchy = {
        'CEO': {
            'CTO': ['개발1팀', '개발2팀', 'QA팀'],
            'CFO': ['재무팀', '회계팀'],
            'COO': ['운영팀', '고객지원팀'],
        }
    }

    drawer3 = DiagramDrawer(theme='corporate')
    drawer3.set_title('조직도')
    drawer3.create_org_chart(hierarchy)
    print(f"노드 수: {len(drawer3.nodes)}")
    print(f"엣지 수: {len(drawer3.edges)}\n")

    print("=== 테스트 완료 ===")
