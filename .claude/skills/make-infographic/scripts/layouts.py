# -*- coding: utf-8 -*-
"""
make-infographic 레이아웃 모듈 v4.0
GridSpec 기반 레이아웃 템플릿

v4.0 업데이트:
- Figure 배경에 그라데이션 효과 추가
- lighten_color 유틸리티 활용
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from typing import Dict, List, Tuple, Optional
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap

try:
    from .utils import get_theme, lighten_color
except ImportError:
    from utils import get_theme, lighten_color


class LayoutConfig:
    """레이아웃 설정을 저장하는 클래스"""

    def __init__(
        self,
        name: str,
        rows: int,
        cols: int,
        cell_specs: List[Dict],
        figsize: Tuple[int, int] = (12, 8),
        description: str = '',
    ):
        """
        LayoutConfig 초기화

        Args:
            name: 레이아웃 이름
            rows: 그리드 행 수
            cols: 그리드 열 수
            cell_specs: 셀 스펙 목록
                [{'name': 'title', 'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 2}, ...]
            figsize: Figure 크기 (너비, 높이) 인치
            description: 레이아웃 설명
        """
        self.name = name
        self.rows = rows
        self.cols = cols
        self.cell_specs = cell_specs
        self.figsize = figsize
        self.description = description


# ============================================================
# 레이아웃 템플릿 정의
# ============================================================

LAYOUT_VERTICAL = LayoutConfig(
    name='vertical',
    rows=6,
    cols=1,
    cell_specs=[
        {'name': 'title', 'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'metrics', 'row': 1, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'chart1', 'row': 2, 'col': 0, 'rowspan': 2, 'colspan': 1},
        {'name': 'chart2', 'row': 4, 'col': 0, 'rowspan': 2, 'colspan': 1},
    ],
    figsize=(10, 14),
    description='세로 정렬 레이아웃: 제목 → 메트릭 → 차트1 → 차트2'
)

LAYOUT_DASHBOARD = LayoutConfig(
    name='dashboard',
    rows=4,
    cols=4,
    cell_specs=[
        {'name': 'title', 'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 4},
        {'name': 'metric1', 'row': 1, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric2', 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric3', 'row': 1, 'col': 2, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric4', 'row': 1, 'col': 3, 'rowspan': 1, 'colspan': 1},
        {'name': 'chart_main', 'row': 2, 'col': 0, 'rowspan': 2, 'colspan': 2},
        {'name': 'chart_sub1', 'row': 2, 'col': 2, 'rowspan': 1, 'colspan': 2},
        {'name': 'chart_sub2', 'row': 3, 'col': 2, 'rowspan': 1, 'colspan': 2},
    ],
    figsize=(14, 10),
    description='대시보드 레이아웃: 상단 메트릭 4개 + 메인 차트 + 서브 차트 2개'
)

LAYOUT_COMPARISON = LayoutConfig(
    name='comparison',
    rows=4,
    cols=2,
    cell_specs=[
        {'name': 'title', 'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 2},
        {'name': 'left_title', 'row': 1, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'right_title', 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 1},
        {'name': 'left_metric', 'row': 2, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'right_metric', 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 1},
        {'name': 'left_chart', 'row': 3, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'right_chart', 'row': 3, 'col': 1, 'rowspan': 1, 'colspan': 1},
    ],
    figsize=(14, 10),
    description='좌우 비교 레이아웃: A vs B 형태'
)

LAYOUT_SIMPLE = LayoutConfig(
    name='simple',
    rows=3,
    cols=1,
    cell_specs=[
        {'name': 'title', 'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'chart', 'row': 1, 'col': 0, 'rowspan': 2, 'colspan': 1},
    ],
    figsize=(10, 8),
    description='단순 레이아웃: 제목 + 차트'
)

LAYOUT_METRICS_GRID = LayoutConfig(
    name='metrics_grid',
    rows=3,
    cols=3,
    cell_specs=[
        {'name': 'title', 'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 3},
        {'name': 'metric1', 'row': 1, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric2', 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric3', 'row': 1, 'col': 2, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric4', 'row': 2, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric5', 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric6', 'row': 2, 'col': 2, 'rowspan': 1, 'colspan': 1},
    ],
    figsize=(12, 8),
    description='메트릭 그리드: 제목 + 6개 KPI 카드'
)

LAYOUT_REPORT = LayoutConfig(
    name='report',
    rows=5,
    cols=2,
    cell_specs=[
        {'name': 'title', 'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 2},
        {'name': 'subtitle', 'row': 1, 'col': 0, 'rowspan': 1, 'colspan': 2},
        {'name': 'metric1', 'row': 2, 'col': 0, 'rowspan': 1, 'colspan': 1},
        {'name': 'metric2', 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 1},
        {'name': 'chart', 'row': 3, 'col': 0, 'rowspan': 2, 'colspan': 2},
    ],
    figsize=(12, 10),
    description='보고서 레이아웃: 제목 + 부제목 + 2개 메트릭 + 차트'
)


# 모든 레이아웃 등록
LAYOUTS: Dict[str, LayoutConfig] = {
    'vertical': LAYOUT_VERTICAL,
    'dashboard': LAYOUT_DASHBOARD,
    'comparison': LAYOUT_COMPARISON,
    'simple': LAYOUT_SIMPLE,
    'metrics_grid': LAYOUT_METRICS_GRID,
    'report': LAYOUT_REPORT,
}


def get_layout(name: str) -> LayoutConfig:
    """
    레이아웃 설정을 반환한다.

    Args:
        name: 레이아웃 이름

    Returns:
        LayoutConfig: 레이아웃 설정
    """
    if name not in LAYOUTS:
        raise ValueError(f"Unknown layout: {name}. Available: {list(LAYOUTS.keys())}")
    return LAYOUTS[name]


def list_layouts() -> List[str]:
    """
    사용 가능한 레이아웃 목록을 반환한다.

    Returns:
        List[str]: 레이아웃 이름 목록
    """
    return list(LAYOUTS.keys())


class LayoutBuilder:
    """
    GridSpec 기반 레이아웃을 생성하는 클래스 v4.0
    """

    def __init__(
        self,
        layout: str = 'dashboard',
        theme: str = 'corporate',
        gradient_bg: bool = True,  # v4.0: 그라데이션 배경 옵션
    ):
        """
        LayoutBuilder 초기화

        Args:
            layout: 레이아웃 이름
            theme: 색상 테마
            gradient_bg: 그라데이션 배경 사용 여부 (v4.0)
        """
        self.config = get_layout(layout)
        self.theme = get_theme(theme)
        self.theme_name = theme
        self.gradient_bg = gradient_bg
        self.fig: Optional[Figure] = None
        self.axes: Dict[str, plt.Axes] = {}

    def build(self) -> Tuple[Figure, Dict[str, plt.Axes]]:
        """
        레이아웃을 생성한다.

        Returns:
            Tuple[Figure, Dict[str, Axes]]: Figure와 Axes 딕셔너리
        """
        # Figure 생성
        self.fig = plt.figure(figsize=self.config.figsize)

        # v4.0: 그라데이션 배경 적용
        if self.gradient_bg and 'primary' in self.theme:
            self._apply_gradient_background()
        else:
            self.fig.patch.set_facecolor(self.theme['light'])

        # GridSpec 생성
        gs = gridspec.GridSpec(
            self.config.rows,
            self.config.cols,
            figure=self.fig,
            hspace=0.3,
            wspace=0.3,
        )

        # 각 셀에 대해 Axes 생성
        for spec in self.config.cell_specs:
            name = spec['name']
            row = spec['row']
            col = spec['col']
            rowspan = spec.get('rowspan', 1)
            colspan = spec.get('colspan', 1)

            ax = self.fig.add_subplot(
                gs[row:row + rowspan, col:col + colspan]
            )
            self.axes[name] = ax

        return self.fig, self.axes

    def _apply_gradient_background(self) -> None:
        """
        v4.0: Figure 배경에 미세한 세로 그라데이션 적용
        상단은 theme['light'], 하단은 primary 색상을 아주 연하게 적용
        """
        # 배경색 계산
        light_color = self.theme.get('light', '#F8F9FA')
        primary_color = self.theme.get('primary', '#2E86AB')

        # primary 색상을 매우 연하게 (95% lighten)
        gradient_end = lighten_color(primary_color, 0.95)

        # Figure 전체에 그라데이션 이미지 추가
        gradient = np.linspace(0, 1, 256).reshape(256, 1)
        gradient = np.hstack([gradient] * 256)

        # 그라데이션 axes 생성 (Figure 전체 덮음)
        gradient_ax = self.fig.add_axes([0, 0, 1, 1], zorder=-1)
        gradient_ax.set_xlim(0, 1)
        gradient_ax.set_ylim(0, 1)
        gradient_ax.axis('off')

        # 커스텀 컬러맵 생성 (상단 light → 하단 연한 primary)
        from matplotlib.colors import to_rgba
        colors = [to_rgba(light_color), to_rgba(gradient_end)]
        cmap = LinearSegmentedColormap.from_list('bg_gradient', colors)

        gradient_ax.imshow(
            gradient,
            aspect='auto',
            cmap=cmap,
            extent=[0, 1, 0, 1],
            origin='upper'
        )

    def get_cell_names(self) -> List[str]:
        """
        레이아웃의 셀 이름 목록을 반환한다.

        Returns:
            List[str]: 셀 이름 목록
        """
        return [spec['name'] for spec in self.config.cell_specs]


def preview_layout(layout_name: str, output_path: str = None) -> None:
    """
    레이아웃을 미리보기로 표시한다.

    Args:
        layout_name: 레이아웃 이름
        output_path: 저장 경로 (없으면 화면에 표시)
    """
    builder = LayoutBuilder(layout=layout_name)
    fig, axes = builder.build()

    # 각 셀에 이름 표시
    for name, ax in axes.items():
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(
            0.5, 0.5, name,
            ha='center', va='center',
            fontsize=12, fontweight='bold',
            color='#666666'
        )
        ax.set_facecolor('#f0f0f0')
        for spine in ax.spines.values():
            spine.set_color('#cccccc')
            spine.set_linewidth(2)
        ax.set_xticks([])
        ax.set_yticks([])

    fig.suptitle(
        f"Layout: {layout_name}",
        fontsize=14, fontweight='bold',
        y=0.98
    )

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"[OK] 레이아웃 미리보기 저장: {output_path}")
    else:
        plt.show()

    plt.close(fig)


# ============================================================
# 테스트
# ============================================================

if __name__ == '__main__':
    print("=== 사용 가능한 레이아웃 ===\n")
    for name in list_layouts():
        config = get_layout(name)
        print(f"- {name}: {config.description}")
        print(f"  크기: {config.figsize}, 그리드: {config.rows}x{config.cols}")
        print(f"  셀: {[s['name'] for s in config.cell_specs]}")
        print()
