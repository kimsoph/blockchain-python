# -*- coding: utf-8 -*-
"""
make-network_diagram 스킬 메인 모듈
NetworkX/Matplotlib 기반 네트워크 다이어그램 생성 클래스
"""

import argparse
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple

try:
    from .utils import (
        get_korean_font,
        generate_filename,
        get_output_dir,
        get_theme,
        parse_dsl,
        extract_keywords_from_markdown,
        build_network_from_keywords,
        build_semantic_network,
        assign_node_colors,
        THEMES,
        COLORMAPS
    )
except ImportError:
    from utils import (
        get_korean_font,
        generate_filename,
        get_output_dir,
        get_theme,
        parse_dsl,
        extract_keywords_from_markdown,
        build_network_from_keywords,
        build_semantic_network,
        assign_node_colors,
        THEMES,
        COLORMAPS
    )


class NetworkDrawer:
    """
    NetworkX/Matplotlib 기반 네트워크 다이어그램 생성 클래스

    메서드 체이닝을 지원하며, DSL, Python API, 마크다운 파일에서
    네트워크 다이어그램을 생성할 수 있다.

    사용 예시:
        # Python API 방식
        drawer = NetworkDrawer(theme='minimal', layout='spring')
        drawer.add_node('통합', size=100)
        drawer.add_node('성장', size=80)
        drawer.add_edge('통합', '성장')
        drawer.save('정책관계도')

        # DSL 방식
        drawer = NetworkDrawer()
        drawer.from_dsl('''
            title: 키워드 네트워크
            [통합] size=100
            [성장]
            [통합] -> [성장]
        ''')
        drawer.save('keyword_network')

        # 마크다운 파일에서 키워드 추출
        drawer = NetworkDrawer()
        drawer.from_markdown('취임사.md')
        drawer.save('취임사_네트워크')
    """

    # 레이아웃 알고리즘 매핑
    LAYOUTS = {
        'spring': nx.spring_layout,
        'circular': nx.circular_layout,
        'kamada_kawai': nx.kamada_kawai_layout,
        'shell': nx.shell_layout,
        'spectral': nx.spectral_layout,
        'random': nx.random_layout,
    }

    def __init__(
        self,
        theme: str = 'minimal',
        layout: str = 'spring',
        dpi: int = 300,
        figsize: Tuple[int, int] = (12, 10),
        output_dir: Optional[str] = None
    ):
        """
        NetworkDrawer 초기화

        Args:
            theme: 테마 이름 (minimal, elegant, clean, corporate, dark)
            layout: 레이아웃 알고리즘 (spring, circular, kamada_kawai, shell)
            dpi: 해상도 (기본: 300)
            figsize: 그림 크기 (기본: (12, 10))
            output_dir: 출력 디렉토리 (기본: 9_Attachments/images/{YYYYMM}/)
        """
        self.theme_name = theme
        self.theme = get_theme(theme)
        self.layout_name = layout
        self.dpi = dpi
        self.figsize = figsize
        self.output_dir = Path(output_dir) if output_dir else get_output_dir()
        self.font = get_korean_font()

        self.title: Optional[str] = None
        self.graph = nx.Graph()  # 기본은 무방향 그래프
        self._use_directed = False  # 방향 그래프 사용 여부

        self._node_sizes: Dict[str, float] = {}
        self._node_colors: Dict[str, str] = {}
        self._edge_weights: Dict[Tuple[str, str], float] = {}
        self._edge_styles: Dict[Tuple[str, str], str] = {}
        self._edge_labels: Dict[Tuple[str, str], str] = {}

        # 한글 폰트 설정
        self._setup_font()

    def _setup_font(self):
        """matplotlib 한글 폰트 설정"""
        plt.rcParams['font.family'] = self.font
        plt.rcParams['axes.unicode_minus'] = False

    def set_title(self, title: str) -> 'NetworkDrawer':
        """
        다이어그램 제목을 설정한다.

        Args:
            title: 제목 텍스트

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        self.title = title
        return self

    def set_layout(self, layout: str) -> 'NetworkDrawer':
        """
        레이아웃 알고리즘을 설정한다.

        Args:
            layout: 레이아웃 이름 (spring, circular, kamada_kawai, shell)

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        if layout not in self.LAYOUTS:
            print(f"[경고] 알 수 없는 레이아웃 '{layout}'. 'spring'을 사용합니다.")
            layout = 'spring'
        self.layout_name = layout
        return self

    def add_node(
        self,
        node: str,
        size: float = 50,
        color: Optional[str] = None,
        **attrs
    ) -> 'NetworkDrawer':
        """
        노드를 추가한다.

        Args:
            node: 노드 이름 (레이블)
            size: 노드 크기 (기본: 50)
            color: 노드 색상 (옵션, 미지정시 테마 기본색)
            **attrs: 추가 속성

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        self.graph.add_node(node, **attrs)
        self._node_sizes[node] = size
        if color:
            self._node_colors[node] = color
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        style: str = 'solid',
        label: Optional[str] = None,
        directed: bool = False,
        **attrs
    ) -> 'NetworkDrawer':
        """
        엣지(연결선)를 추가한다.

        Args:
            source: 시작 노드
            target: 도착 노드
            weight: 엣지 가중치/두께 (기본: 1.0)
            style: 선 스타일 ('solid' 또는 'dashed')
            label: 엣지 레이블 (옵션)
            directed: 방향 화살표 표시 여부
            **attrs: 추가 속성

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        # 노드가 없으면 자동 추가
        if source not in self.graph:
            self.add_node(source)
        if target not in self.graph:
            self.add_node(target)

        self.graph.add_edge(source, target, **attrs)

        edge_key = (source, target)
        self._edge_weights[edge_key] = weight
        self._edge_styles[edge_key] = style
        if label:
            self._edge_labels[edge_key] = label

        if directed:
            self._use_directed = True

        return self

    def connect(self, *nodes: str, **kwargs) -> 'NetworkDrawer':
        """
        여러 노드를 순차적으로 연결한다.

        Args:
            *nodes: 연결할 노드들
            **kwargs: add_edge에 전달할 옵션

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        for i in range(len(nodes) - 1):
            self.add_edge(nodes[i], nodes[i + 1], **kwargs)
        return self

    def from_dsl(self, dsl_text: str) -> 'NetworkDrawer':
        """
        DSL 텍스트를 파싱하여 네트워크를 구성한다.

        Args:
            dsl_text: DSL 텍스트

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        parsed = parse_dsl(dsl_text)

        if parsed['title']:
            self.title = parsed['title']

        if parsed['layout']:
            self.set_layout(parsed['layout'])

        # 노드 추가
        for node_name, attrs in parsed['nodes']:
            size = attrs.get('size', 50)
            color = attrs.get('color', None)
            self.add_node(node_name, size=size, color=color)

        # 엣지 추가
        for from_node, to_node, attrs in parsed['edges']:
            style = attrs.get('style', 'solid')
            directed = attrs.get('directed', False)
            label = attrs.get('label', None)
            bidirectional = attrs.get('bidirectional', False)

            self.add_edge(
                from_node,
                to_node,
                style=style,
                label=label,
                directed=directed
            )

            # 양방향 연결
            if bidirectional:
                self.add_edge(
                    to_node,
                    from_node,
                    style=style,
                    directed=directed
                )

        return self

    def from_dsl_file(self, file_path: str) -> 'NetworkDrawer':
        """
        DSL 파일을 읽어서 네트워크를 구성한다.

        Args:
            file_path: DSL 파일 경로

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"DSL 파일을 찾을 수 없습니다: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            dsl_text = f.read()

        return self.from_dsl(dsl_text)

    def from_markdown(
        self,
        file_path: str,
        center_node: Optional[str] = None,
        use_semantic: bool = False,
        min_freq: int = 2,
        max_keywords: int = 30,
        min_cooccurrence: int = 2,
        max_edges: int = 50,
        window_type: str = 'sentence',
        colormap: Optional[str] = None
    ) -> 'NetworkDrawer':
        """
        마크다운 파일에서 키워드를 추출하여 네트워크를 구성한다.

        v3.0: 의미연결망(Semantic Network) 분석 모드 추가
        v3.1: 컬러맵 기반 노드 색상 다양화 추가

        Args:
            file_path: 마크다운 파일 경로
            center_node: 중심 노드 이름 (옵션, 지정시 star 형태, 기존 모드만)
            use_semantic: 의미연결망 분석 모드 사용 여부 (v3.0)
            min_freq: 최소 키워드 빈도 (의미연결망 모드)
            max_keywords: 최대 키워드 개수 (의미연결망 모드)
            min_cooccurrence: 최소 동시출현 빈도 (의미연결망 모드)
            max_edges: 최대 엣지 개수 (의미연결망 모드)
            window_type: 동시출현 분석 단위 ('sentence' 또는 'paragraph')
            colormap: 노드 색상 컬러맵 (v3.1, None이면 테마 기본색)
                옵션: viridis, plasma, coolwarm, blues, greens, oranges, rainbow, pastel, ibk, warm

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"마크다운 파일을 찾을 수 없습니다: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if use_semantic:
            # v3.0: 의미연결망 분석 모드
            print(f"[INFO] 의미연결망 분석 모드: min_freq={min_freq}, max_keywords={max_keywords}")
            network_data = build_semantic_network(
                content,
                min_freq=min_freq,
                max_keywords=max_keywords,
                min_cooccurrence=min_cooccurrence,
                max_edges=max_edges,
                window_type=window_type
            )

            if not network_data['nodes']:
                print("[경고] 키워드를 찾을 수 없습니다. min_freq 값을 낮춰보세요.")
                return self

            if not network_data['edges']:
                print("[경고] 동시출현 관계를 찾을 수 없습니다. min_cooccurrence 값을 낮춰보세요.")
                return self

            print(f"[INFO] 추출된 키워드: {len(network_data['nodes'])}개, 관계: {len(network_data['edges'])}개")
        else:
            # 기존 해시태그 기반 모드
            keywords = extract_keywords_from_markdown(content)

            if not keywords:
                print("[경고] 키워드를 찾을 수 없습니다.")
                return self

            network_data = build_network_from_keywords(keywords, center_node)

        if network_data['title']:
            self.title = network_data['title']

        # v3.1: 컬러맵 기반 노드 색상 할당
        node_color_map = {}
        if colormap and colormap in COLORMAPS:
            node_color_map = assign_node_colors(network_data['nodes'], colormap, reverse=True)
            print(f"[INFO] 컬러맵 적용: {colormap}")

        # 노드 추가 (색상 포함)
        for node_name, attrs in network_data['nodes']:
            size = attrs.get('size', 50)
            # 컬러맵 색상 우선, 없으면 None (테마 기본색 사용)
            color = node_color_map.get(node_name, None)
            self.add_node(node_name, size=size, color=color, **{k: v for k, v in attrs.items() if k not in ('size', 'color')})

        # 엣지 추가
        for from_node, to_node, attrs in network_data['edges']:
            weight = attrs.get('weight', 1.0)
            style = attrs.get('style', 'solid')
            directed = attrs.get('directed', False)
            self.add_edge(from_node, to_node, weight=weight, style=style, directed=directed)

        # 파일명에서 제목 추출
        if not self.title:
            if use_semantic:
                self.title = path.stem + ' 의미연결망'
            else:
                self.title = path.stem + ' 키워드 네트워크'

        return self

    def _get_layout_positions(self) -> Dict[str, np.ndarray]:
        """레이아웃 알고리즘으로 노드 위치를 계산한다."""
        layout_func = self.LAYOUTS.get(self.layout_name, nx.spring_layout)

        if self.layout_name == 'spring':
            return layout_func(self.graph, k=2, iterations=50, seed=42)
        elif self.layout_name == 'kamada_kawai':
            return layout_func(self.graph)
        else:
            return layout_func(self.graph)

    def _normalize_node_sizes(self, raw_sizes: List[float]) -> List[float]:
        """
        노드 크기를 최소-최대 범위로 정규화한다.

        Args:
            raw_sizes: 원본 크기 리스트

        Returns:
            정규화된 크기 리스트 (400 ~ 2000 범위)
        """
        MIN_SIZE, MAX_SIZE = 400, 2000

        if not raw_sizes:
            return []

        s_min, s_max = min(raw_sizes), max(raw_sizes)

        # 모든 크기가 동일한 경우
        if s_max == s_min:
            return [MIN_SIZE + (MAX_SIZE - MIN_SIZE) / 2] * len(raw_sizes)

        return [
            MIN_SIZE + (s - s_min) / (s_max - s_min) * (MAX_SIZE - MIN_SIZE)
            for s in raw_sizes
        ]

    def _get_dynamic_fontsize(self, node: str, normalized_size: float) -> int:
        """
        노드 크기에 비례하는 폰트 크기를 반환한다.

        Args:
            node: 노드 이름
            normalized_size: 정규화된 노드 크기 (400~2000)

        Returns:
            폰트 크기 (9 ~ 14pt)
        """
        MIN_FONT, MAX_FONT = 9, 14
        MIN_SIZE, MAX_SIZE = 400, 2000

        # 정규화된 크기 기반으로 폰트 크기 계산
        normalized = (normalized_size - MIN_SIZE) / (MAX_SIZE - MIN_SIZE)
        fontsize = int(MIN_FONT + normalized * (MAX_FONT - MIN_FONT))

        return max(MIN_FONT, min(MAX_FONT, fontsize))

    def _add_node_shadows(
        self,
        ax: plt.Axes,
        pos: Dict[str, np.ndarray],
        node_sizes_dict: Dict[str, float]
    ):
        """
        노드 아래에 그림자 효과를 추가한다.

        Args:
            ax: matplotlib Axes 객체
            pos: 노드 위치 딕셔너리
            node_sizes_dict: 노드별 크기 딕셔너리
        """
        from matplotlib.patches import Circle

        shadow_color = self.theme.get('node_shadow_color', '#00000020')

        # 좌표 범위 계산 (그림자 오프셋을 위해)
        x_coords = [p[0] for p in pos.values()]
        y_coords = [p[1] for p in pos.values()]
        x_range = max(x_coords) - min(x_coords) if x_coords else 1
        y_range = max(y_coords) - min(y_coords) if y_coords else 1
        offset_scale = max(x_range, y_range) * 0.012  # 오프셋 감소

        for node, (x, y) in pos.items():
            size = node_sizes_dict.get(node, 800)
            # matplotlib의 노드 크기는 포인트^2 단위이므로 반지름 계산
            # 더 정확한 스케일 조정 (axes 좌표계 기준)
            radius = np.sqrt(size / np.pi) / 85  # 스케일 감소

            shadow = Circle(
                (x + offset_scale, y - offset_scale),
                radius * 1.08,  # 노드보다 살짝만 크게
                color=shadow_color,
                zorder=0  # 가장 뒤에
            )
            ax.add_patch(shadow)

    def _draw_labels_with_background(
        self,
        ax: plt.Axes,
        pos: Dict[str, np.ndarray],
        node_sizes_dict: Dict[str, float]
    ):
        """
        배경 박스가 있는 노드 레이블을 그린다.

        Args:
            ax: matplotlib Axes 객체
            pos: 노드 위치 딕셔너리
            node_sizes_dict: 노드별 크기 딕셔너리
        """
        label_bg_color = self.theme.get('label_bg_color', '#FFFFFFEE')
        label_border_color = self.theme.get('label_border_color', '#666666')
        font_color = self.theme['font_color']

        for node, (x, y) in pos.items():
            size = node_sizes_dict.get(node, 800)
            fontsize = self._get_dynamic_fontsize(node, size)

            text = ax.text(
                x, y, node,
                ha='center', va='center',
                fontsize=fontsize,
                fontweight='bold',
                fontfamily=self.font,
                color=font_color,
                zorder=10  # 가장 앞에
            )

            # 배경 박스 추가
            bbox = dict(
                boxstyle='round,pad=0.4',
                facecolor=label_bg_color,
                edgecolor=label_border_color,
                linewidth=1.2,
                alpha=0.95
            )
            text.set_bbox(bbox)

    def render(self) -> plt.Figure:
        """
        네트워크 다이어그램을 렌더링한다.

        v2.0: 노드 크기 정규화, 그림자 효과, 라벨 배경 박스 추가

        Returns:
            Figure: matplotlib Figure 객체
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        fig.patch.set_facecolor(self.theme['background'])
        ax.set_facecolor(self.theme['background'])

        # 노드 위치 계산
        pos = self._get_layout_positions()

        # 노드 크기 및 색상 준비 (v2.0: 정규화 적용)
        node_list = list(self.graph.nodes())
        raw_sizes = [self._node_sizes.get(n, 50) for n in node_list]
        node_sizes = self._normalize_node_sizes(raw_sizes)

        # 노드별 크기 딕셔너리 (그림자, 라벨용)
        node_sizes_dict = {n: s for n, s in zip(node_list, node_sizes)}

        node_colors = [
            self._node_colors.get(n, self.theme['node_color'])
            for n in node_list
        ]

        # 엣지 스타일 준비
        edge_list = list(self.graph.edges())
        edge_widths = [
            self._edge_weights.get((u, v), 1.0) * 1.5
            for u, v in edge_list
        ]
        edge_styles = [
            self._edge_styles.get((u, v), 'solid')
            for u, v in edge_list
        ]

        # 점선과 실선 분리
        solid_edges = [(u, v) for u, v in edge_list
                       if self._edge_styles.get((u, v), 'solid') == 'solid']
        dashed_edges = [(u, v) for u, v in edge_list
                        if self._edge_styles.get((u, v), 'solid') == 'dashed']

        solid_widths = [self._edge_weights.get((u, v), 1.0) * 1.5
                        for u, v in solid_edges]
        dashed_widths = [self._edge_weights.get((u, v), 1.0) * 1.5
                         for u, v in dashed_edges]

        # v2.0: 노드 그림자 먼저 그리기 (가장 뒤)
        self._add_node_shadows(ax, pos, node_sizes_dict)

        # 엣지 그리기 (실선)
        if solid_edges:
            edge_kwargs = {
                'edgelist': solid_edges,
                'edge_color': self.theme['edge_color'],
                'width': solid_widths if solid_widths else 1.5,
                'alpha': 0.7,
                'arrows': self._use_directed,
                'arrowsize': 20,
                'arrowstyle': '-|>',
                'ax': ax
            }
            if self._use_directed:
                edge_kwargs['connectionstyle'] = 'arc3,rad=0.1'
            nx.draw_networkx_edges(self.graph, pos, **edge_kwargs)

        # 엣지 그리기 (점선)
        if dashed_edges:
            nx.draw_networkx_edges(
                self.graph,
                pos,
                edgelist=dashed_edges,
                edge_color=self.theme['edge_color'],
                width=dashed_widths if dashed_widths else 1.5,
                alpha=0.5,
                style='dashed',
                arrows=self._use_directed,
                arrowsize=20,
                arrowstyle='-|>',
                ax=ax
            )

        # 노드 그리기
        nx.draw_networkx_nodes(
            self.graph,
            pos,
            nodelist=node_list,
            node_size=node_sizes,
            node_color=node_colors,
            edgecolors=self.theme['node_edge_color'],
            linewidths=2.5,  # v2.0: 테두리 두께 증가
            alpha=0.95,      # v2.0: 불투명도 증가
            ax=ax
        )

        # v2.0: 배경 박스가 있는 노드 레이블 그리기
        self._draw_labels_with_background(ax, pos, node_sizes_dict)

        # 엣지 레이블 그리기
        if self._edge_labels:
            nx.draw_networkx_edge_labels(
                self.graph,
                pos,
                edge_labels=self._edge_labels,
                font_size=9,
                font_family=self.font,
                font_color=self.theme['font_color'],
                ax=ax
            )

        # 제목 추가
        if self.title:
            ax.set_title(
                self.title,
                fontsize=16,
                fontweight='bold',
                color=self.theme['title_color'],
                pad=20
            )

        ax.axis('off')
        plt.tight_layout()

        return fig

    def save(self, name: str = 'network') -> str:
        """
        네트워크 다이어그램을 이미지 파일로 저장한다.

        Args:
            name: 파일명 (확장자 제외, 접두사 제외)

        Returns:
            str: 저장된 파일의 절대 경로
        """
        fig = self.render()

        # 파일명 생성 (net_ 접두사 포함)
        filename = generate_filename(name, 'net')
        output_path = self.output_dir / filename

        # 저장
        fig.savefig(
            output_path,
            dpi=self.dpi,
            facecolor=self.theme['background'],
            edgecolor='none',
            bbox_inches='tight',
            pad_inches=0.2
        )
        plt.close(fig)

        final_path = str(output_path)

        # 출력 안내
        print(f"[OK] 네트워크 다이어그램 저장 완료: {final_path}")

        # 옵시디언 삽입 코드 출력
        try:
            relative_path = Path(final_path).relative_to(
                Path(final_path).parents[3]  # vault root 기준
            )
            obsidian_path = str(relative_path).replace('\\', '/')
            print(f"[INFO] 옵시디언 삽입: ![[{obsidian_path}]]")
        except ValueError:
            pass

        return final_path

    def clear(self) -> 'NetworkDrawer':
        """
        모든 노드와 엣지를 초기화한다.

        Returns:
            NetworkDrawer: 메서드 체이닝용 self 반환
        """
        self.graph.clear()
        self.title = None
        self._node_sizes.clear()
        self._node_colors.clear()
        self._edge_weights.clear()
        self._edge_styles.clear()
        self._edge_labels.clear()
        self._use_directed = False
        return self


def create_network(
    dsl_text: str,
    theme: str = 'minimal',
    layout: str = 'spring',
    filename: str = 'network'
) -> str:
    """
    DSL 텍스트로 빠르게 네트워크 다이어그램을 생성하는 편의 함수

    Args:
        dsl_text: DSL 텍스트
        theme: 테마 이름
        layout: 레이아웃 알고리즘
        filename: 저장할 파일명

    Returns:
        str: 저장된 파일 경로
    """
    drawer = NetworkDrawer(theme=theme, layout=layout)
    drawer.from_dsl(dsl_text)
    return drawer.save(filename)


def main():
    """CLI 진입점"""
    parser = argparse.ArgumentParser(
        description='네트워크 다이어그램 생성기 (v3.0: 의미연결망 지원)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python draw_network.py --dsl network.txt --name "관계도"
  python draw_network.py --file 취임사.md --name "키워드네트워크"
  python draw_network.py --file 취임사.md --semantic --name "의미연결망"
  python draw_network.py --file 취임사.md --semantic --min-freq 3 --max-keywords 20
        """
    )

    parser.add_argument(
        '--dsl',
        type=str,
        help='DSL 파일 경로'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='마크다운 파일 경로 (키워드 자동 추출)'
    )
    parser.add_argument(
        '--name',
        type=str,
        default='network',
        help='출력 파일명 (기본: network)'
    )
    parser.add_argument(
        '--theme',
        type=str,
        default='minimal',
        choices=['minimal', 'elegant', 'clean', 'corporate', 'dark'],
        help='테마 (기본: minimal)'
    )
    parser.add_argument(
        '--layout',
        type=str,
        default='spring',
        choices=['spring', 'circular', 'kamada_kawai', 'shell'],
        help='레이아웃 알고리즘 (기본: spring)'
    )
    parser.add_argument(
        '--center',
        type=str,
        help='중심 노드 (마크다운 모드에서 star 형태 생성, 기존 모드만)'
    )
    # v3.0: 의미연결망 옵션들
    parser.add_argument(
        '--semantic',
        action='store_true',
        help='의미연결망 분석 모드 사용 (MeCab 기반 명사 추출, 동시출현 분석)'
    )
    parser.add_argument(
        '--min-freq',
        type=int,
        default=2,
        help='최소 키워드 빈도 (기본: 2, 의미연결망 모드)'
    )
    parser.add_argument(
        '--max-keywords',
        type=int,
        default=30,
        help='최대 키워드 개수 (기본: 30, 의미연결망 모드)'
    )
    parser.add_argument(
        '--min-cooccurrence',
        type=int,
        default=2,
        help='최소 동시출현 빈도 (기본: 2, 의미연결망 모드)'
    )
    parser.add_argument(
        '--max-edges',
        type=int,
        default=50,
        help='최대 엣지 개수 (기본: 50, 의미연결망 모드)'
    )
    parser.add_argument(
        '--window',
        type=str,
        default='sentence',
        choices=['sentence', 'paragraph'],
        help='동시출현 분석 단위 (기본: sentence, 의미연결망 모드)'
    )
    # v3.1: 컬러맵 옵션
    parser.add_argument(
        '--colormap', '-c',
        type=str,
        default=None,
        choices=['viridis', 'plasma', 'coolwarm', 'blues', 'greens', 'oranges', 'rainbow', 'pastel', 'ibk', 'warm'],
        help='노드 색상 컬러맵 (v3.1, 빈도 기반 그라데이션)'
    )

    args = parser.parse_args()

    if not args.dsl and not args.file:
        parser.print_help()
        print("\n[오류] --dsl 또는 --file 옵션 중 하나를 지정해야 합니다.")
        return

    drawer = NetworkDrawer(theme=args.theme, layout=args.layout)

    try:
        if args.dsl:
            drawer.from_dsl_file(args.dsl)
        elif args.file:
            drawer.from_markdown(
                args.file,
                center_node=args.center,
                use_semantic=args.semantic,
                min_freq=args.min_freq,
                max_keywords=args.max_keywords,
                min_cooccurrence=args.min_cooccurrence,
                max_edges=args.max_edges,
                window_type=args.window,
                colormap=args.colormap
            )

        path = drawer.save(args.name)
        print(f"\n[완료] 파일 저장됨: {path}")

    except FileNotFoundError as e:
        print(f"[오류] {e}")
    except Exception as e:
        print(f"[오류] 다이어그램 생성 실패: {e}")
        raise


if __name__ == '__main__':
    # CLI 모드
    import sys
    if len(sys.argv) > 1:
        main()
    else:
        # 테스트 모드
        print("=== Python API 방식 테스트 ===")
        drawer = NetworkDrawer(theme='minimal', layout='spring')
        drawer.set_title('정책 관계도')
        drawer.add_node('통합', size=100)
        drawer.add_node('성장', size=80)
        drawer.add_node('혁신', size=70)
        drawer.add_node('협력', size=60)
        drawer.add_edge('통합', '성장')
        drawer.add_edge('통합', '혁신')
        drawer.add_edge('성장', '협력')
        drawer.add_edge('혁신', '협력')
        # drawer.save('정책관계도')
        print("[테스트 완료] 저장 기능은 주석 처리되어 있습니다.")

        print("\n=== DSL 방식 테스트 ===")
        dsl = """
title: 키워드 네트워크
layout: spring

[통합] size=100
[성장] size=80
[혁신] size=70

[통합] -> [성장]
[통합] -> [혁신]
[성장] -- [혁신]
        """
        drawer2 = NetworkDrawer(theme='clean')
        drawer2.from_dsl(dsl)
        # drawer2.save('keyword_network')
        print("[테스트 완료] 저장 기능은 주석 처리되어 있습니다.")
