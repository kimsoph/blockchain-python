# -*- coding: utf-8 -*-
"""
make-flowchart 스킬 메인 모듈
Graphviz 기반 플로우차트 생성 클래스
"""

from graphviz import Digraph
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

try:
    from .utils import (
        get_korean_font,
        generate_filename,
        get_output_dir,
        get_theme,
        parse_flowchart_dsl,
        NODE_TYPES,
        THEMES
    )
except ImportError:
    from utils import (
        get_korean_font,
        generate_filename,
        get_output_dir,
        get_theme,
        parse_flowchart_dsl,
        NODE_TYPES,
        THEMES
    )


class FlowchartDrawer:
    """
    Graphviz 기반 플로우차트 생성 클래스

    메서드 체이닝을 지원하며, DSL 또는 Python API로 플로우차트를 생성할 수 있다.

    사용 예시:
        # DSL 방식
        drawer = FlowchartDrawer()
        drawer.parse_dsl('''
            title: 로그인 프로세스
            [시작] start: 시작
            [프로세스] input: 아이디/비밀번호 입력
            [결정] check: 인증 성공?
            [종료] end: 종료
            start -> input
            input -> check
            check -> end: Yes
            check --> input: No
        ''')
        drawer.save('login_flow')

        # Python API 방식
        drawer = FlowchartDrawer(theme='elegant', direction='LR')
        drawer.set_title('주문 처리 프로세스')
        drawer.add_start('s', '시작')
        drawer.add_process('p1', '주문 접수')
        drawer.add_decision('d1', '재고 확인')
        drawer.add_process('p2', '출고 처리')
        drawer.add_end('e', '완료')
        drawer.connect('s', 'p1', 'p2', 'e')
        drawer.add_edge('p1', 'd1')
        drawer.add_edge('d1', 'p2', label='재고있음')
        drawer.add_edge('d1', 'p1', label='재고없음', style='dashed')
        drawer.save('order_flow')
    """

    def __init__(
        self,
        theme: str = 'minimal',
        direction: str = 'TB',
        dpi: int = 300,
        output_dir: Optional[str] = None
    ):
        """
        FlowchartDrawer 초기화

        Args:
            theme: 테마 이름 (minimal, elegant, clean, corporate, dark)
            direction: 방향 (TB: 위->아래, LR: 좌->우, BT: 아래->위, RL: 우->좌)
            dpi: 해상도 (기본: 300)
            output_dir: 출력 디렉토리 (기본: 9_Attachments/images/{YYYYMM}/)
        """
        self.theme_name = theme
        self.theme = get_theme(theme)
        self.direction = direction.upper()
        self.dpi = dpi
        self.output_dir = Path(output_dir) if output_dir else get_output_dir()
        self.font = get_korean_font()

        self.title = ''
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []

        self._graph: Optional[Digraph] = None

    def parse_dsl(self, dsl_text: str) -> 'FlowchartDrawer':
        """
        DSL 텍스트를 파싱하여 플로우차트를 구성한다.

        Args:
            dsl_text: DSL 텍스트

        Returns:
            FlowchartDrawer: 메서드 체이닝용 self 반환
        """
        parsed = parse_flowchart_dsl(dsl_text)

        if parsed['title']:
            self.title = parsed['title']

        if parsed['direction']:
            self.direction = parsed['direction']

        for node_id, label, node_type in parsed['nodes']:
            self.add_node(node_id, label, node_type)

        for from_node, to_node, label, style in parsed['edges']:
            self.add_edge(from_node, to_node, label=label, style=style)

        return self

    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str = 'process'
    ) -> 'FlowchartDrawer':
        """
        노드를 추가한다.

        Args:
            node_id: 노드 ID
            label: 노드 레이블
            node_type: 노드 타입 (start, end, process, decision, io, document, database)

        Returns:
            FlowchartDrawer: 메서드 체이닝용 self 반환
        """
        if node_type not in NODE_TYPES:
            print(f"[경고] 알 수 없는 노드 타입 '{node_type}'. 'process'로 대체합니다.")
            node_type = 'process'

        self.nodes.append({
            'id': node_id,
            'label': label,
            'type': node_type
        })
        return self

    def add_start(self, node_id: str, label: str) -> 'FlowchartDrawer':
        """시작 노드 추가"""
        return self.add_node(node_id, label, 'start')

    def add_end(self, node_id: str, label: str) -> 'FlowchartDrawer':
        """종료 노드 추가"""
        return self.add_node(node_id, label, 'end')

    def add_process(self, node_id: str, label: str) -> 'FlowchartDrawer':
        """처리 노드 추가"""
        return self.add_node(node_id, label, 'process')

    def add_decision(self, node_id: str, label: str) -> 'FlowchartDrawer':
        """결정/분기 노드 추가"""
        return self.add_node(node_id, label, 'decision')

    def add_io(self, node_id: str, label: str) -> 'FlowchartDrawer':
        """입출력 노드 추가"""
        return self.add_node(node_id, label, 'io')

    def add_document(self, node_id: str, label: str) -> 'FlowchartDrawer':
        """문서 노드 추가"""
        return self.add_node(node_id, label, 'document')

    def add_database(self, node_id: str, label: str) -> 'FlowchartDrawer':
        """데이터베이스 노드 추가"""
        return self.add_node(node_id, label, 'database')

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        label: str = '',
        style: str = 'solid'
    ) -> 'FlowchartDrawer':
        """
        엣지(연결선)를 추가한다.

        Args:
            from_node: 시작 노드 ID
            to_node: 도착 노드 ID
            label: 엣지 레이블 (옵션)
            style: 선 스타일 ('solid' 또는 'dashed')

        Returns:
            FlowchartDrawer: 메서드 체이닝용 self 반환
        """
        self.edges.append({
            'from': from_node,
            'to': to_node,
            'label': label,
            'style': style
        })
        return self

    def connect(
        self,
        *nodes: str,
        labels: Optional[List[str]] = None
    ) -> 'FlowchartDrawer':
        """
        여러 노드를 순차적으로 연결한다.

        Args:
            *nodes: 연결할 노드 ID들
            labels: 각 연결에 대한 레이블 리스트 (옵션)

        Returns:
            FlowchartDrawer: 메서드 체이닝용 self 반환

        사용 예시:
            drawer.connect('start', 'step1', 'step2', 'end')
            drawer.connect('a', 'b', 'c', labels=['처리중', '완료'])
        """
        if len(nodes) < 2:
            return self

        if labels is None:
            labels = [''] * (len(nodes) - 1)

        for i in range(len(nodes) - 1):
            label = labels[i] if i < len(labels) else ''
            self.add_edge(nodes[i], nodes[i + 1], label=label)

        return self

    def set_title(self, title: str) -> 'FlowchartDrawer':
        """
        플로우차트 제목을 설정한다.

        Args:
            title: 제목 텍스트

        Returns:
            FlowchartDrawer: 메서드 체이닝용 self 반환
        """
        self.title = title
        return self

    def set_direction(self, direction: str) -> 'FlowchartDrawer':
        """
        플로우차트 방향을 설정한다.

        Args:
            direction: 방향 (TB, LR, BT, RL)

        Returns:
            FlowchartDrawer: 메서드 체이닝용 self 반환
        """
        valid_directions = ['TB', 'LR', 'BT', 'RL']
        direction = direction.upper()
        if direction not in valid_directions:
            print(f"[경고] 유효하지 않은 방향 '{direction}'. 'TB'를 사용합니다.")
            direction = 'TB'
        self.direction = direction
        return self

    def _get_node_attributes(self, node_type: str) -> Dict[str, str]:
        """
        노드 타입에 따른 Graphviz 속성을 반환한다.

        Args:
            node_type: 노드 타입

        Returns:
            Dict: Graphviz 노드 속성
        """
        node_def = NODE_TYPES.get(node_type, NODE_TYPES['process'])
        theme_colors = self.theme.get('node_colors', {})
        color = theme_colors.get(node_type, node_def['color'])

        attrs = {
            'shape': node_def['shape'],
            'style': 'filled',
            'fillcolor': color,
            'fontcolor': node_def['fontcolor'],
            'fontname': self.font,
            'fontsize': '12',
            'penwidth': '1.5',
        }

        # 특수 스타일 추가
        if 'style' in node_def:
            attrs['style'] = f"filled,{node_def['style']}"

        # 다크 테마에서 흰색 텍스트
        if self.theme_name == 'dark':
            if node_type not in ['document']:
                attrs['fontcolor'] = 'white'

        return attrs

    def render(self) -> Digraph:
        """
        플로우차트를 렌더링한다.

        Returns:
            Digraph: Graphviz Digraph 객체
        """
        graph = Digraph(format='png')

        # 그래프 기본 속성
        graph.attr(
            rankdir=self.direction,
            dpi=str(self.dpi),
            bgcolor=self.theme['bgcolor'],
            splines='ortho',  # 직각 연결선
            nodesep='0.5',
            ranksep='0.6',
        )

        # 제목 추가
        if self.title:
            graph.attr(
                label=self.title,
                labelloc='t',
                fontname=self.font,
                fontsize='16',
                fontcolor=self.theme['fontcolor'],
            )

        # 기본 노드 속성
        graph.attr(
            'node',
            fontname=self.font,
            fontsize='12',
            margin='0.2,0.1',
        )

        # 기본 엣지 속성
        graph.attr(
            'edge',
            fontname=self.font,
            fontsize='10',
            color=self.theme['edge_color'],
            fontcolor=self.theme['fontcolor'],
            arrowsize='0.8',
        )

        # 노드 추가
        for node in self.nodes:
            attrs = self._get_node_attributes(node['type'])
            graph.node(node['id'], node['label'], **attrs)

        # 엣지 추가
        for edge in self.edges:
            edge_attrs = {}
            if edge['label']:
                edge_attrs['label'] = edge['label']
            if edge['style'] == 'dashed':
                edge_attrs['style'] = 'dashed'

            graph.edge(edge['from'], edge['to'], **edge_attrs)

        self._graph = graph
        return graph

    def save(self, filename: str = 'flowchart') -> str:
        """
        플로우차트를 이미지 파일로 저장한다.

        Args:
            filename: 파일명 (확장자 제외, 접두사 제외)

        Returns:
            str: 저장된 파일의 절대 경로
        """
        if self._graph is None:
            self.render()

        # 파일명 생성 (flow_ 접두사 포함)
        full_filename = generate_filename(filename, 'png')
        # 확장자 제거 (graphviz가 자동으로 추가)
        base_filename = full_filename.rsplit('.', 1)[0]

        output_path = self.output_dir / base_filename

        # 렌더링 및 저장
        self._graph.render(str(output_path), cleanup=True)

        final_path = str(output_path) + '.png'

        # 출력 안내
        print(f"[OK] 플로우차트 저장 완료: {final_path}")

        # 옵시디언 삽입 코드 출력
        relative_path = Path(final_path).relative_to(
            Path(final_path).parents[3]  # vault root 기준
        )
        obsidian_path = str(relative_path).replace('\\', '/')
        print(f"[INFO] 옵시디언 삽입: ![[{obsidian_path}]]")

        return final_path

    def clear(self) -> 'FlowchartDrawer':
        """
        모든 노드와 엣지를 초기화한다.

        Returns:
            FlowchartDrawer: 메서드 체이닝용 self 반환
        """
        self.nodes = []
        self.edges = []
        self.title = ''
        self._graph = None
        return self


def create_flowchart(
    dsl_text: str,
    theme: str = 'minimal',
    filename: str = 'flowchart'
) -> str:
    """
    DSL 텍스트로 빠르게 플로우차트를 생성하는 편의 함수

    Args:
        dsl_text: DSL 텍스트
        theme: 테마 이름
        filename: 저장할 파일명

    Returns:
        str: 저장된 파일 경로
    """
    drawer = FlowchartDrawer(theme=theme)
    drawer.parse_dsl(dsl_text)
    return drawer.save(filename)


if __name__ == '__main__':
    # 테스트: DSL 방식
    print("=== DSL 방식 테스트 ===")
    dsl = """
title: 사용자 인증 프로세스
direction: TB
[시작] start: 시작
[입출력] input: ID/PW 입력
[프로세스] validate: 입력값 검증
[결정] check: 인증 성공?
[프로세스] login: 로그인 처리
[데이터베이스] log: 로그 기록
[종료] end: 완료
start -> input
input -> validate
validate -> check
check -> login: Yes
check --> input: No (재시도)
login -> log
log -> end
    """

    drawer = FlowchartDrawer(theme='clean')
    drawer.parse_dsl(dsl)
    # drawer.save('auth_flow')

    # 테스트: Python API 방식
    print("\n=== Python API 방식 테스트 ===")
    drawer2 = FlowchartDrawer(theme='elegant', direction='LR')
    drawer2.set_title('주문 처리 흐름')
    drawer2.add_start('s', '주문 시작')
    drawer2.add_io('i1', '주문 정보 입력')
    drawer2.add_database('db1', '재고 확인')
    drawer2.add_decision('d1', '재고 있음?')
    drawer2.add_process('p1', '결제 처리')
    drawer2.add_document('doc', '주문서 생성')
    drawer2.add_end('e', '주문 완료')

    drawer2.connect('s', 'i1', 'db1', 'd1')
    drawer2.add_edge('d1', 'p1', label='Yes')
    drawer2.add_edge('d1', 's', label='No', style='dashed')
    drawer2.connect('p1', 'doc', 'e')

    # drawer2.save('order_flow')

    print("\n[테스트 완료] 저장 기능은 주석 처리되어 있습니다.")
