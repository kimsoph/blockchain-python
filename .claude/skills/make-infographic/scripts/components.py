# -*- coding: utf-8 -*-
"""
make-infographic 컴포넌트 모듈 v3.0
개별 인포그래픽 요소들의 렌더링 함수

v3.0 업데이트:
- MetricCard: 미니멀 디자인, 더 작은 폰트, 테두리 제거, 부드러운 그림자
- ChartBlock: 투명 배경, 그리드 최소화, 세련된 색상
- TextBlock: 가벼운 폰트 웨이트
- 전체적으로 더 세련되고 현대적인 디자인

v2.0 업데이트:
- MetricCard: 그림자 효과, 그라데이션 배경 옵션
- ChartBlock: 다중 시리즈 지원, 둥근 막대, 범례 자동 추가
- 새 컴포넌트: ProgressBar, Sparkline, Badge, Callout
- 전체적인 시각적 품질 향상
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch, Rectangle, Wedge
from matplotlib.collections import PolyCollection
from typing import Dict, List, Optional, Tuple, Union

try:
    from .utils import (
        get_theme,
        get_chart_color,
        get_chart_colors,
        format_number,
        format_percent,
        lighten_color,
        darken_color,
        get_alpha_color,
        hex_to_rgb,
    )
except ImportError:
    from utils import (
        get_theme,
        get_chart_color,
        get_chart_colors,
        format_number,
        format_percent,
        lighten_color,
        darken_color,
        get_alpha_color,
        hex_to_rgb,
    )


class MetricCard:
    """
    KPI/메트릭 카드 컴포넌트 v4.0
    눈에 띄는 시각적 디자인
    - 컬러 그림자 및 글로우 효과
    - 좌측 액센트 바 옵션
    - 값 하이라이트 효과
    """

    def __init__(
        self,
        value: Union[float, int, str],
        label: str,
        change: float = None,
        change_label: str = None,
        change_unit: str = '%',  # v3.1: '%' 또는 '%p' (퍼센트 포인트)
        unit: str = '',
        theme: str = 'minimal',
        format_value: bool = True,
        show_shadow: bool = True,
        gradient_bg: bool = False,
        icon: str = None,
        style: str = 'minimal',  # 'minimal', 'card', 'compact'
        accent_bar: bool = False,  # v4.0: 좌측 컬러 스트라이프
        highlight_value: bool = False,  # v4.0: 값 뒤 하이라이트 원
        accent_color: str = None,  # v4.0: 액센트 바/하이라이트 색상
    ):
        """
        MetricCard 초기화

        Args:
            value: 메인 값 (숫자 또는 문자열)
            label: 레이블 (예: '총 매출')
            change: 변화율 또는 변화량 (예: 12.5)
            change_label: 변화율 레이블 (예: '전월 대비')
            change_unit: 변화량 단위 ('%': 상대적 변화율, '%p': 퍼센트 포인트)
            unit: 단위 (예: '억원', '%')
            theme: 색상 테마
            format_value: 숫자 포맷팅 적용 여부
            show_shadow: 그림자 효과 표시 여부
            gradient_bg: 그라데이션 배경 사용 여부
            icon: 아이콘 (유니코드 또는 키)
            style: 스타일 ('minimal', 'card', 'compact')
            accent_bar: 좌측 컬러 스트라이프 표시 (v4.0)
            highlight_value: 값 뒤 하이라이트 원 표시 (v4.0)
            accent_color: 액센트 바/하이라이트 색상 (v4.0, None이면 테마 primary)
        """
        self.value = value
        self.label = label
        self.change = change
        self.change_label = change_label or ''
        self.change_unit = change_unit  # v3.1: '%' or '%p'
        self.unit = unit
        self.theme_name = theme
        self.theme = get_theme(theme)
        self.format_value = format_value
        self.show_shadow = show_shadow
        self.gradient_bg = gradient_bg
        self.icon = icon
        self.style = style
        # v4.0 새 옵션
        self.accent_bar = accent_bar
        self.highlight_value = highlight_value
        self.accent_color = accent_color or self.theme.get('primary', '#2E86AB')

    def render(self, ax: Axes, show_border: bool = True) -> None:
        """
        Axes에 메트릭 카드를 렌더링한다.

        Args:
            ax: matplotlib Axes 객체
            show_border: 테두리 표시 여부
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # v4.0: 더 눈에 띄는 그림자 (컬러 그림자 옵션 추가)
        if self.show_shadow and show_border:
            # 테마에 컬러 그림자가 있으면 사용
            shadow_base = self.theme.get('glow', '#000000')
            use_color_shadow = 'glow' in self.theme

            # 멀티 레이어 그림자 (v4.0: alpha 강화)
            for i, (offset, alpha) in enumerate([(0.03, 0.06), (0.02, 0.05), (0.012, 0.04)]):
                shadow_rect = FancyBboxPatch(
                    (0.03 + offset, 0.03 - offset), 0.94, 0.92,
                    boxstyle="round,pad=0.01,rounding_size=0.06",
                    facecolor=shadow_base if use_color_shadow else '#000000',
                    alpha=alpha,
                    edgecolor='none',
                    zorder=0
                )
                ax.add_patch(shadow_rect)

        # v3.0: 카드 배경 (테두리 없이 깔끔하게)
        if show_border:
            # 카드 배경색 (테마에 card_bg가 있으면 사용, 없으면 white)
            bg_color = self.theme.get('card_bg', self.theme['white'])

            rect = FancyBboxPatch(
                (0.03, 0.03), 0.94, 0.92,
                boxstyle="round,pad=0.01,rounding_size=0.06",
                facecolor=bg_color,
                edgecolor='none',  # v3.0: 테두리 제거
                linewidth=0,
                zorder=1
            )
            ax.add_patch(rect)

            # v4.0: 좌측 액센트 바
            if self.accent_bar:
                accent_rect = Rectangle(
                    (0.03, 0.03), 0.025, 0.92,
                    facecolor=self.accent_color,
                    edgecolor='none',
                    zorder=2
                )
                ax.add_patch(accent_rect)

        # 아이콘 (있는 경우)
        if self.icon:
            ax.text(
                0.15, 0.5,
                self.icon,
                ha='center', va='center',
                fontsize=22,  # v3.0: 더 작게
                color=self.theme['primary'],
                zorder=2
            )
            value_x = 0.58
        else:
            value_x = 0.5

        # v3.0: 메인 값 (더 작고 세련된 폰트)
        if isinstance(self.value, (int, float)) and self.format_value:
            display_value = format_number(self.value)
        else:
            display_value = str(self.value)

        if self.unit:
            display_value = f"{display_value}{self.unit}"

        # v4.0: 값 하이라이트 원 (옵션)
        if self.highlight_value:
            from matplotlib.patches import Circle
            highlight_circle = Circle(
                (value_x, 0.52), 0.18,
                facecolor=lighten_color(self.accent_color, 0.85),
                edgecolor='none',
                zorder=1.5
            )
            ax.add_patch(highlight_circle)

        ax.text(
            value_x, 0.52,
            display_value,
            ha='center', va='center',
            fontsize=26,  # v3.0: 30 → 26
            fontweight='semibold',  # v3.0: bold → semibold
            color=self.theme['dark'],
            zorder=2
        )

        # v3.0: 레이블 (더 작고 가벼움)
        ax.text(
            value_x, 0.22,
            self.label,
            ha='center', va='center',
            fontsize=10,  # v3.0: 11 → 10
            fontweight='normal',
            color=self.theme['muted'],
            zorder=2
        )

        # v3.1: 변화율 (심플하게, %p 단위 지원)
        if self.change is not None:
            change_color = self.theme['success'] if self.change >= 0 else self.theme['danger']

            # v3.1: change_unit에 따라 단위 표시 변경
            sign = '+' if self.change >= 0 else ''
            if self.change_unit == '%p':
                # 퍼센트 포인트: 절대값 그대로 표시 (예: +1.81%p, -0.35%p)
                change_text = f"{sign}{self.change:.2f}%p"
            else:
                # 기본 %: 상대적 변화율 (예: +12.3%, -5.2%)
                change_text = format_percent(self.change)

            if self.change_label:
                change_text = f"{change_text} {self.change_label}"

            # v3.0: 심플한 화살표 (작은 삼각형)
            arrow = '↑' if self.change >= 0 else '↓'
            change_text = f"{arrow} {change_text}"

            # v4.0: 배지 배경 더 선명하게 + 글로우 효과 옵션
            badge_width = len(change_text) * 0.032 + 0.06
            badge_rect = FancyBboxPatch(
                (value_x - badge_width/2, 0.76), badge_width, 0.14,
                boxstyle="round,pad=0.008,rounding_size=0.04",
                facecolor=lighten_color(change_color, 0.70),  # v4.0: 0.85 → 0.70 (더 선명)
                edgecolor='none',
                zorder=2
            )
            ax.add_patch(badge_rect)

            # v4.0: 글로우 효과가 있는 테마면 텍스트에 적용
            text_effects = None
            if 'glow' in self.theme:
                try:
                    from .utils import create_soft_glow
                except ImportError:
                    from utils import create_soft_glow
                text_effects = create_soft_glow(change_color)

            ax.text(
                value_x, 0.83,
                change_text,
                ha='center', va='center',
                fontsize=9,
                fontweight='semibold',  # v4.0: medium → semibold (더 강조)
                color=change_color,
                path_effects=text_effects,
                zorder=3
            )


class TextBlock:
    """
    텍스트 블록 컴포넌트
    제목, 부제목, 설명 텍스트 표시
    """

    def __init__(
        self,
        text: str,
        style: str = 'title',
        align: str = 'center',
        theme: str = 'corporate',
    ):
        """
        TextBlock 초기화

        Args:
            text: 표시할 텍스트
            style: 스타일 ('title', 'subtitle', 'body', 'caption')
            align: 정렬 ('left', 'center', 'right')
            theme: 색상 테마
        """
        self.text = text
        self.style = style
        self.align = align
        self.theme = get_theme(theme)

        # 스타일별 설정
        self.styles = {
            'title': {
                'fontsize': 24,
                'fontweight': 'bold',
                'color': self.theme['dark'],
            },
            'subtitle': {
                'fontsize': 16,
                'fontweight': 'semibold',
                'color': self.theme['muted'],
            },
            'body': {
                'fontsize': 12,
                'fontweight': 'normal',
                'color': self.theme['dark'],
            },
            'caption': {
                'fontsize': 10,
                'fontweight': 'normal',
                'color': self.theme['muted'],
            },
        }

    def render(self, ax: Axes) -> None:
        """
        Axes에 텍스트 블록을 렌더링한다.

        Args:
            ax: matplotlib Axes 객체
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        style_config = self.styles.get(self.style, self.styles['body'])

        # 정렬에 따른 x 위치
        x_pos = {'left': 0.05, 'center': 0.5, 'right': 0.95}

        ax.text(
            x_pos[self.align], 0.5,
            self.text,
            ha=self.align, va='center',
            fontsize=style_config['fontsize'],
            fontweight=style_config['fontweight'],
            color=style_config['color'],
            wrap=True
        )


class ChartBlock:
    """
    차트 블록 컴포넌트 v3.0
    세련된 미니멀 차트 디자인
    - 투명 배경
    - 최소화된 그리드
    - 더 가벼운 폰트
    """

    def __init__(
        self,
        chart_type: str,
        data: Dict,
        title: str = '',
        theme: str = 'minimal',
        show_legend: bool = True,
        rounded_bars: bool = True,
        show_grid: bool = False,  # v3.0: 기본값 False
        show_values: bool = True,
    ):
        """
        ChartBlock 초기화

        Args:
            chart_type: 차트 유형 ('line', 'bar', 'pie', 'donut', 'hbar', 'area')
            data: 차트 데이터
                - 단일 시리즈: {'labels': [...], 'values': [...]}
                - 다중 시리즈: {'labels': [...], 'series': [{'name': '...', 'values': [...]}, ...]}
            title: 차트 제목
            theme: 색상 테마
            show_legend: 범례 표시 여부 (다중 시리즈 시)
            rounded_bars: 막대 모서리 둥글게 여부
            show_grid: 그리드 표시 여부 (v3.0: 기본 False)
            show_values: 값 레이블 표시 여부
        """
        self.chart_type = chart_type
        self.data = data
        self.title = title
        self.theme_name = theme
        self.theme_colors = get_theme(theme)
        self.chart_colors = get_chart_colors(theme)
        self.show_legend = show_legend
        self.rounded_bars = rounded_bars
        self.show_grid = show_grid
        self.show_values = show_values

    def render(self, ax: Axes) -> None:
        """
        Axes에 차트를 렌더링한다.

        Args:
            ax: matplotlib Axes 객체
        """
        if self.chart_type == 'line':
            self._render_line(ax)
        elif self.chart_type == 'bar':
            self._render_bar(ax)
        elif self.chart_type == 'pie':
            self._render_pie(ax)
        elif self.chart_type == 'donut':
            self._render_donut(ax)
        elif self.chart_type == 'hbar':
            self._render_hbar(ax)
        elif self.chart_type == 'area':
            self._render_area(ax)

        # v3.0: 제목 스타일 개선
        if self.title:
            ax.set_title(
                self.title,
                fontsize=11,  # v3.0: 12 → 11
                fontweight='medium',  # v3.0: bold → medium
                color=self.theme_colors['dark'],
                pad=8,
                loc='left'  # v3.0: 왼쪽 정렬
            )

    def _render_line(self, ax: Axes) -> None:
        """선 그래프 렌더링 (다중 시리즈 지원) - v4.0 스타일 다양화"""
        labels = self.data.get('labels', [])
        x = np.arange(len(labels))

        # v4.0: 시리즈별 다른 라인/마커 스타일
        LINE_STYLES = ['-', '--', '-.', ':']
        MARKER_STYLES = ['o', 's', '^', 'D', 'v', 'p']
        LINE_WIDTHS = [2.5, 2, 1.8, 1.5]  # 첫 시리즈가 가장 굵음

        # 다중 시리즈 확인
        if 'series' in self.data:
            series_list = self.data['series']
            for i, s in enumerate(series_list):
                color = self.chart_colors[i % len(self.chart_colors)]
                linestyle = LINE_STYLES[i % len(LINE_STYLES)]
                marker = MARKER_STYLES[i % len(MARKER_STYLES)]
                linewidth = LINE_WIDTHS[min(i, len(LINE_WIDTHS) - 1)]

                ax.plot(
                    x, s['values'],
                    marker=marker, markersize=6,  # v4.0: 5 → 6
                    color=color, linewidth=linewidth,
                    linestyle=linestyle,
                    label=s.get('name', f'시리즈 {i+1}'),
                    zorder=2 + i  # 첫 시리즈가 위에 표시
                )
                # v4.0: 영역 채우기 강화 (0.05 → 0.15)
                ax.fill_between(
                    x, s['values'], alpha=0.15, color=color, zorder=1
                )
            if self.show_legend and len(series_list) > 1:
                ax.legend(loc='upper left', fontsize=8, framealpha=0.95, edgecolor='none')
        else:
            # 단일 시리즈
            values = self.data.get('values', [])
            color = self.chart_colors[0]
            ax.plot(x, values, marker='o', markersize=6, color=color, linewidth=2.5, zorder=2)
            ax.fill_between(x, values, alpha=0.15, color=color, zorder=1)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)  # v3.0: 9 → 8
        ax.tick_params(axis='y', labelsize=8)

        # v3.0: 그리드 최소화
        if self.show_grid:
            ax.grid(True, linestyle='-', alpha=0.1, color=self.theme_colors['muted'], zorder=0)
        else:
            ax.grid(False)

        # v3.0: 투명 배경 + 깔끔한 스파인
        ax.set_facecolor('none')
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color(self.theme_colors['border'])
            ax.spines[spine].set_linewidth(0.5)

    def _render_bar(self, ax: Axes) -> None:
        """막대 그래프 렌더링 (다중 시리즈 지원)"""
        labels = self.data.get('labels', [])
        x = np.arange(len(labels))

        # 다중 시리즈 확인
        if 'series' in self.data:
            series_list = self.data['series']
            n_series = len(series_list)
            width = 0.7 / n_series

            for i, s in enumerate(series_list):
                color = self.chart_colors[i % len(self.chart_colors)]
                offset = (i - n_series/2 + 0.5) * width
                bars = ax.bar(
                    x + offset, s['values'],
                    width=width * 0.85,  # v3.0: 0.9 → 0.85 (더 좁게)
                    color=color,
                    edgecolor='none',  # v3.0: 테두리 제거
                    linewidth=0,
                    label=s.get('name', f'시리즈 {i+1}'),
                    zorder=2
                )
                # v3.0: 값 표시 스타일 개선
                if self.show_values:
                    for bar, val in zip(bars, s['values']):
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + max(s['values']) * 0.02,
                            format_number(val),
                            ha='center', va='bottom',
                            fontsize=7, fontweight='normal',  # v3.0: 8 bold → 7 normal
                            color=self.theme_colors['muted']
                        )

            if self.show_legend and n_series > 1:
                ax.legend(loc='upper right', fontsize=8, framealpha=0.95, edgecolor='none')
        else:
            # 단일 시리즈
            values = self.data.get('values', [])
            colors = [self.chart_colors[i % len(self.chart_colors)] for i in range(len(values))]

            bars = ax.bar(x, values, color=colors, width=0.55, edgecolor='none', zorder=2)  # v3.0: 0.6 → 0.55

            if self.show_values:
                for bar, val in zip(bars, values):
                    y_pos = bar.get_height() if val >= 0 else bar.get_height() - abs(val) * 0.15
                    va = 'bottom' if val >= 0 else 'top'
                    ax.text(
                        bar.get_x() + bar.get_width() / 2, y_pos,
                        format_number(val),
                        ha='center', va=va,
                        fontsize=7, fontweight='normal',
                        color=self.theme_colors['muted']
                    )

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.tick_params(axis='y', labelsize=8)

        # v3.0: 깔끔한 축 처리
        ax.axhline(y=0, color=self.theme_colors['border'], linewidth=0.5)
        ax.set_facecolor('none')
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color(self.theme_colors['border'])
            ax.spines[spine].set_linewidth(0.5)

    def _render_hbar(self, ax: Axes) -> None:
        """가로 막대 그래프 렌더링"""
        labels = self.data.get('labels', [])
        values = self.data.get('values', [])

        y = np.arange(len(labels))
        colors = [self.chart_colors[i % len(self.chart_colors)] for i in range(len(values))]

        bars = ax.barh(y, values, color=colors, height=0.55, edgecolor='none', zorder=2)  # v3.0

        # v3.0: 값 표시 스타일 개선
        if self.show_values:
            max_val = max(abs(v) for v in values) if values else 1
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_width() + max_val * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    format_number(val),
                    ha='left', va='center',
                    fontsize=8, fontweight='normal',  # v3.0: bold → normal
                    color=self.theme_colors['muted']
                )

        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        ax.tick_params(axis='x', labelsize=8)

        # v3.0: 투명 배경 + 깔끔한 스파인
        ax.set_facecolor('none')
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color(self.theme_colors['border'])
            ax.spines[spine].set_linewidth(0.5)

    def _render_pie(self, ax: Axes) -> None:
        """파이 차트 렌더링 (v3.0 개선)"""
        labels = self.data.get('labels', [])
        values = self.data.get('values', [])
        colors = [self.chart_colors[i % len(self.chart_colors)] for i in range(len(values))]

        # v3.0: 더 세련된 파이 차트
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, colors=colors,
            autopct='%1.0f%%', startangle=90,  # v3.0: 소수점 제거
            textprops={'fontsize': 8, 'color': self.theme_colors['dark']},  # v3.0: 더 작게
            wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}  # v3.0: 테두리 얇게
        )

        for autotext in autotexts:
            autotext.set_fontweight('medium')  # v3.0: bold → medium
            autotext.set_fontsize(8)
            autotext.set_color('white')

    def _render_donut(self, ax: Axes) -> None:
        """도넛 차트 렌더링 (v3.0 개선)"""
        labels = self.data.get('labels', [])
        values = self.data.get('values', [])
        colors = [self.chart_colors[i % len(self.chart_colors)] for i in range(len(values))]

        # v3.0: 더 세련된 도넛 차트
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, colors=colors,
            autopct='%1.0f%%', startangle=90,
            wedgeprops={'width': 0.45, 'edgecolor': 'white', 'linewidth': 1.5},  # v3.0: 더 얇은 도넛
            textprops={'fontsize': 8, 'color': self.theme_colors['dark']}
        )

        for autotext in autotexts:
            autotext.set_fontweight('medium')
            autotext.set_fontsize(8)
            autotext.set_color('white')

        # v3.0: 중앙 총계 스타일 개선
        total = sum(values)
        ax.text(
            0, 0, format_number(total),
            ha='center', va='center',
            fontsize=14, fontweight='semibold',  # v3.0: 16 bold → 14 semibold
            color=self.theme_colors['dark']
        )

    def _render_area(self, ax: Axes) -> None:
        """영역 그래프 렌더링 (v4.0 개선)"""
        labels = self.data.get('labels', [])
        x = np.arange(len(labels))

        if 'series' in self.data:
            series_list = self.data['series']
            for i, s in enumerate(series_list):
                color = self.chart_colors[i % len(self.chart_colors)]
                ax.fill_between(x, s['values'], alpha=0.25, color=color, label=s.get('name'))  # v4.0: 0.2 → 0.25
                ax.plot(x, s['values'], color=color, linewidth=2)  # v4.0: 1.5 → 2
            if self.show_legend:
                ax.legend(loc='upper left', fontsize=8, framealpha=0.95, edgecolor='none')
        else:
            values = self.data.get('values', [])
            color = self.chart_colors[0]
            ax.fill_between(x, values, alpha=0.25, color=color)
            ax.plot(x, values, color=color, linewidth=2)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)

        # v3.0: 투명 배경 + 깔끔한 스파인
        ax.set_facecolor('none')
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color(self.theme_colors['border'])
            ax.spines[spine].set_linewidth(0.5)


class Divider:
    """
    구분선 컴포넌트
    """

    def __init__(
        self,
        direction: str = 'horizontal',
        theme: str = 'corporate',
    ):
        """
        Divider 초기화

        Args:
            direction: 방향 ('horizontal', 'vertical')
            theme: 색상 테마
        """
        self.direction = direction
        self.theme = get_theme(theme)

    def render(self, ax: Axes) -> None:
        """
        Axes에 구분선을 렌더링한다.

        Args:
            ax: matplotlib Axes 객체
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        if self.direction == 'horizontal':
            ax.axhline(y=0.5, color=self.theme['border'], linewidth=1)
        else:
            ax.axvline(x=0.5, color=self.theme['border'], linewidth=1)


class IconMetric:
    """
    아이콘 + 숫자 조합 컴포넌트
    간단한 유니코드 아이콘과 숫자를 함께 표시
    """

    # 사용 가능한 아이콘 (유니코드)
    ICONS = {
        'up': '▲',
        'down': '▼',
        'right': '▶',
        'check': '✓',
        'star': '★',
        'circle': '●',
        'diamond': '◆',
        'square': '■',
        'heart': '♥',
        'dollar': '$',
        'percent': '%',
        'target': '◎',
        'user': '👤',
        'users': '👥',
        'chart': '📊',
        'money': '💰',
        'building': '🏢',
        'calendar': '📅',
        'clock': '⏰',
        'trophy': '🏆',
        'fire': '🔥',
        'rocket': '🚀',
        'lightning': '⚡',
        'growth': '📈',
        'decline': '📉',
    }

    def __init__(
        self,
        icon: str,
        value: Union[float, int, str],
        label: str = '',
        theme: str = 'corporate',
    ):
        """
        IconMetric 초기화

        Args:
            icon: 아이콘 키 또는 유니코드 문자
            value: 표시할 값
            label: 레이블
            theme: 색상 테마
        """
        self.icon = self.ICONS.get(icon, icon)
        self.value = value
        self.label = label
        self.theme = get_theme(theme)

    def render(self, ax: Axes) -> None:
        """
        Axes에 아이콘 메트릭을 렌더링한다.

        Args:
            ax: matplotlib Axes 객체
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # 아이콘
        ax.text(
            0.15, 0.5,
            self.icon,
            ha='center', va='center',
            fontsize=24,
            color=self.theme['primary']
        )

        # 값
        display_value = format_number(self.value) if isinstance(self.value, (int, float)) else str(self.value)
        ax.text(
            0.55, 0.55,
            display_value,
            ha='left', va='center',
            fontsize=18,
            fontweight='bold',
            color=self.theme['dark']
        )

        # 레이블
        if self.label:
            ax.text(
                0.55, 0.3,
                self.label,
                ha='left', va='center',
                fontsize=10,
                color=self.theme['muted']
            )


# ============================================================
# 새로운 컴포넌트 (v2.0)
# ============================================================

class ProgressBar:
    """
    진행률 바 컴포넌트
    퍼센트 진행 상황을 시각적으로 표시
    """

    def __init__(
        self,
        value: float,
        max_value: float = 100,
        label: str = '',
        show_percent: bool = True,
        theme: str = 'corporate',
        color: str = None,
        height: float = 0.3,
    ):
        """
        ProgressBar 초기화

        Args:
            value: 현재 값
            max_value: 최대 값 (기본: 100)
            label: 레이블
            show_percent: 퍼센트 표시 여부
            theme: 색상 테마
            color: 바 색상 (None이면 테마 primary 사용)
            height: 바 높이 (0-1)
        """
        self.value = value
        self.max_value = max_value
        self.label = label
        self.show_percent = show_percent
        self.theme = get_theme(theme)
        self.color = color or self.theme['primary']
        self.height = height

    def render(self, ax: Axes) -> None:
        """
        Axes에 진행률 바를 렌더링한다.
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        percent = min(self.value / self.max_value, 1.0)

        # 레이블
        if self.label:
            ax.text(
                0.05, 0.8,
                self.label,
                ha='left', va='center',
                fontsize=11,
                fontweight='bold',
                color=self.theme['dark']
            )

        # 배경 바
        bar_y = 0.4
        bg_rect = FancyBboxPatch(
            (0.05, bar_y), 0.9, self.height,
            boxstyle="round,pad=0.01,rounding_size=0.05",
            facecolor=self.theme['border'],
            edgecolor='none'
        )
        ax.add_patch(bg_rect)

        # 진행 바
        if percent > 0:
            progress_rect = FancyBboxPatch(
                (0.05, bar_y), 0.9 * percent, self.height,
                boxstyle="round,pad=0.01,rounding_size=0.05",
                facecolor=self.color,
                edgecolor='none'
            )
            ax.add_patch(progress_rect)

        # 퍼센트 표시
        if self.show_percent:
            ax.text(
                0.95, bar_y + self.height / 2,
                f'{percent * 100:.1f}%',
                ha='right', va='center',
                fontsize=10,
                fontweight='bold',
                color=self.theme['dark']
            )


class Sparkline:
    """
    스파크라인 (미니 차트) 컴포넌트
    작은 공간에 추세를 보여주는 간단한 선 그래프
    """

    def __init__(
        self,
        values: List[float],
        label: str = '',
        show_endpoints: bool = True,
        theme: str = 'corporate',
        color: str = None,
        fill: bool = True,
    ):
        """
        Sparkline 초기화

        Args:
            values: 데이터 값 목록
            label: 레이블
            show_endpoints: 시작/끝점 표시 여부
            theme: 색상 테마
            color: 선 색상
            fill: 영역 채우기 여부
        """
        self.values = values
        self.label = label
        self.show_endpoints = show_endpoints
        self.theme = get_theme(theme)
        self.color = color or self.theme['primary']
        self.fill = fill

    def render(self, ax: Axes) -> None:
        """
        Axes에 스파크라인을 렌더링한다.
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        if not self.values:
            return

        # 레이블
        if self.label:
            ax.text(
                0.05, 0.85,
                self.label,
                ha='left', va='center',
                fontsize=10,
                color=self.theme['muted']
            )

        # 데이터 정규화
        min_val = min(self.values)
        max_val = max(self.values)
        val_range = max_val - min_val if max_val != min_val else 1

        x = np.linspace(0.05, 0.95, len(self.values))
        y = [(v - min_val) / val_range * 0.5 + 0.15 for v in self.values]

        # 영역 채우기
        if self.fill:
            ax.fill_between(x, [0.15] * len(x), y, alpha=0.2, color=self.color)

        # 선
        ax.plot(x, y, color=self.color, linewidth=2)

        # 끝점 표시
        if self.show_endpoints:
            ax.plot(x[0], y[0], 'o', color=self.color, markersize=6)
            ax.plot(x[-1], y[-1], 'o', color=self.color, markersize=6)

            # 끝값 표시
            ax.text(
                x[-1] + 0.02, y[-1],
                format_number(self.values[-1]),
                ha='left', va='center',
                fontsize=9,
                fontweight='bold',
                color=self.theme['dark']
            )


class Badge:
    """
    배지 컴포넌트
    상태나 카테고리를 표시하는 작은 라벨
    """

    BADGE_COLORS = {
        'success': 'success',
        'danger': 'danger',
        'warning': 'warning',
        'info': 'info',
        'primary': 'primary',
        'secondary': 'secondary',
    }

    def __init__(
        self,
        text: str,
        badge_type: str = 'primary',
        theme: str = 'corporate',
    ):
        """
        Badge 초기화

        Args:
            text: 배지 텍스트
            badge_type: 배지 유형 ('success', 'danger', 'warning', 'info', 'primary', 'secondary')
            theme: 색상 테마
        """
        self.text = text
        self.badge_type = badge_type
        self.theme = get_theme(theme)

    def render(self, ax: Axes) -> None:
        """
        Axes에 배지를 렌더링한다.
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        color_key = self.BADGE_COLORS.get(self.badge_type, 'primary')
        bg_color = self.theme.get(color_key, self.theme['primary'])

        # 배지 배경
        badge_width = len(self.text) * 0.05 + 0.1
        badge_rect = FancyBboxPatch(
            (0.5 - badge_width/2, 0.35), badge_width, 0.3,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=bg_color,
            edgecolor='none'
        )
        ax.add_patch(badge_rect)

        # 텍스트
        ax.text(
            0.5, 0.5,
            self.text,
            ha='center', va='center',
            fontsize=11,
            fontweight='bold',
            color='white'
        )


class Callout:
    """
    콜아웃 컴포넌트
    강조하고 싶은 텍스트를 박스 안에 표시
    """

    def __init__(
        self,
        text: str,
        title: str = '',
        callout_type: str = 'info',
        theme: str = 'corporate',
    ):
        """
        Callout 초기화

        Args:
            text: 본문 텍스트
            title: 제목 (선택)
            callout_type: 유형 ('info', 'success', 'warning', 'danger')
            theme: 색상 테마
        """
        self.text = text
        self.title = title
        self.callout_type = callout_type
        self.theme = get_theme(theme)

        self.icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'danger': '❌',
        }

    def render(self, ax: Axes) -> None:
        """
        Axes에 콜아웃을 렌더링한다.
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        color_key = self.callout_type
        accent_color = self.theme.get(color_key, self.theme['info'])
        bg_color = lighten_color(accent_color, 0.85)

        # 배경
        bg_rect = FancyBboxPatch(
            (0.02, 0.05), 0.96, 0.9,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=bg_color,
            edgecolor=accent_color,
            linewidth=2
        )
        ax.add_patch(bg_rect)

        # 왼쪽 강조선
        left_line = Rectangle(
            (0.02, 0.05), 0.02, 0.9,
            facecolor=accent_color,
            edgecolor='none'
        )
        ax.add_patch(left_line)

        # 아이콘
        icon = self.icons.get(self.callout_type, 'ℹ️')
        ax.text(
            0.08, 0.75,
            icon,
            ha='left', va='center',
            fontsize=16
        )

        # 제목
        if self.title:
            ax.text(
                0.14, 0.75,
                self.title,
                ha='left', va='center',
                fontsize=12,
                fontweight='bold',
                color=self.theme['dark']
            )
            text_y = 0.4
        else:
            text_y = 0.5

        # 본문
        ax.text(
            0.08, text_y,
            self.text,
            ha='left', va='center',
            fontsize=10,
            color=self.theme['dark'],
            wrap=True
        )


class ComparisonBar:
    """
    비교 바 컴포넌트
    두 값을 좌우로 비교 표시
    """

    def __init__(
        self,
        left_value: float,
        right_value: float,
        left_label: str = '',
        right_label: str = '',
        center_label: str = '',
        theme: str = 'corporate',
    ):
        """
        ComparisonBar 초기화

        Args:
            left_value: 왼쪽 값
            right_value: 오른쪽 값
            left_label: 왼쪽 레이블
            right_label: 오른쪽 레이블
            center_label: 중앙 레이블
            theme: 색상 테마
        """
        self.left_value = left_value
        self.right_value = right_value
        self.left_label = left_label
        self.right_label = right_label
        self.center_label = center_label
        self.theme = get_theme(theme)
        self.colors = get_chart_colors(theme)

    def render(self, ax: Axes) -> None:
        """
        Axes에 비교 바를 렌더링한다.
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        total = self.left_value + self.right_value
        if total == 0:
            left_ratio = 0.5
        else:
            left_ratio = self.left_value / total

        bar_y = 0.4
        bar_height = 0.2

        # 왼쪽 바
        left_rect = FancyBboxPatch(
            (0.05, bar_y), left_ratio * 0.9, bar_height,
            boxstyle="round,pad=0.01,rounding_size=0.03",
            facecolor=self.colors[0],
            edgecolor='none'
        )
        ax.add_patch(left_rect)

        # 오른쪽 바
        right_rect = FancyBboxPatch(
            (0.05 + left_ratio * 0.9, bar_y), (1 - left_ratio) * 0.9, bar_height,
            boxstyle="round,pad=0.01,rounding_size=0.03",
            facecolor=self.colors[1],
            edgecolor='none'
        )
        ax.add_patch(right_rect)

        # 레이블
        if self.left_label:
            ax.text(
                0.05, 0.75,
                f'{self.left_label}: {format_number(self.left_value)}',
                ha='left', va='center',
                fontsize=10,
                fontweight='bold',
                color=self.colors[0]
            )

        if self.right_label:
            ax.text(
                0.95, 0.75,
                f'{self.right_label}: {format_number(self.right_value)}',
                ha='right', va='center',
                fontsize=10,
                fontweight='bold',
                color=self.colors[1]
            )

        if self.center_label:
            ax.text(
                0.5, 0.15,
                self.center_label,
                ha='center', va='center',
                fontsize=9,
                color=self.theme['muted']
            )


# ============================================================
# 새로운 컴포넌트 (v4.0)
# ============================================================

class HighlightBox:
    """
    핵심 인사이트 강조 박스 v4.0
    좌측 액센트 바 + 아이콘 + 텍스트로 구성된 강조 박스
    """

    # 타입별 색상 및 아이콘
    HIGHLIGHT_TYPES = {
        'insight': {'color': '#5C6BC0', 'icon': '💡', 'label': 'INSIGHT'},      # 인디고
        'warning': {'color': '#FFA726', 'icon': '⚠️', 'label': 'WARNING'},      # 앰버
        'success': {'color': '#66BB6A', 'icon': '✅', 'label': 'SUCCESS'},       # 에메랄드
        'key': {'color': '#EC407A', 'icon': '🔑', 'label': 'KEY POINT'},        # 핑크
        'info': {'color': '#29B6F6', 'icon': 'ℹ️', 'label': 'INFO'},             # 라이트 블루
        'danger': {'color': '#EF5350', 'icon': '🚨', 'label': 'ALERT'},         # 레드
    }

    def __init__(
        self,
        text: str,
        highlight_type: str = 'insight',
        title: str = None,
        theme: str = 'minimal',
        show_icon: bool = True,
        show_label: bool = True,
    ):
        """
        HighlightBox 초기화

        Args:
            text: 본문 텍스트
            highlight_type: 타입 ('insight', 'warning', 'success', 'key', 'info', 'danger')
            title: 커스텀 제목 (None이면 타입 레이블 사용)
            theme: 색상 테마
            show_icon: 아이콘 표시 여부
            show_label: 타입 레이블 표시 여부
        """
        self.text = text
        self.highlight_type = highlight_type
        self.theme = get_theme(theme)

        type_config = self.HIGHLIGHT_TYPES.get(highlight_type, self.HIGHLIGHT_TYPES['insight'])
        self.accent_color = type_config['color']
        self.icon = type_config['icon'] if show_icon else ''
        self.title = title or (type_config['label'] if show_label else '')

    def render(self, ax: Axes) -> None:
        """
        Axes에 하이라이트 박스를 렌더링한다.
        """
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # 배경
        bg_color = lighten_color(self.accent_color, 0.90)
        bg_rect = FancyBboxPatch(
            (0.02, 0.05), 0.96, 0.9,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=bg_color,
            edgecolor='none',
            zorder=1
        )
        ax.add_patch(bg_rect)

        # 좌측 액센트 바
        accent_bar = Rectangle(
            (0.02, 0.05), 0.02, 0.9,
            facecolor=self.accent_color,
            edgecolor='none',
            zorder=2
        )
        ax.add_patch(accent_bar)

        # 아이콘
        if self.icon:
            ax.text(
                0.08, 0.7,
                self.icon,
                ha='left', va='center',
                fontsize=16,
                zorder=3
            )
            text_start_x = 0.14
        else:
            text_start_x = 0.08

        # 제목/레이블
        if self.title:
            ax.text(
                text_start_x, 0.7,
                self.title,
                ha='left', va='center',
                fontsize=10,
                fontweight='bold',
                color=self.accent_color,
                zorder=3
            )
            text_y = 0.35
        else:
            text_y = 0.5

        # 본문
        ax.text(
            0.08, text_y,
            self.text,
            ha='left', va='center',
            fontsize=10,
            color=self.theme['dark'],
            wrap=True,
            zorder=3
        )


class DataAnnotation:
    """
    데이터 포인트 주석 v4.0
    차트 위에 화살표와 텍스트로 특정 포인트를 강조
    """

    def __init__(
        self,
        x: float,
        y: float,
        text: str,
        arrow_direction: str = 'up',  # 'up', 'down', 'left', 'right'
        theme: str = 'minimal',
        color: str = None,
    ):
        """
        DataAnnotation 초기화

        Args:
            x: X 좌표 (0-1)
            y: Y 좌표 (0-1)
            text: 주석 텍스트
            arrow_direction: 화살표 방향
            theme: 색상 테마
            color: 주석 색상 (None이면 테마 primary)
        """
        self.x = x
        self.y = y
        self.text = text
        self.arrow_direction = arrow_direction
        self.theme = get_theme(theme)
        self.color = color or self.theme.get('primary', '#2E86AB')

    def render(self, ax: Axes) -> None:
        """
        Axes에 주석을 렌더링한다.
        """
        # 화살표 방향에 따른 오프셋
        offsets = {
            'up': (0, 0.08),
            'down': (0, -0.08),
            'left': (-0.08, 0),
            'right': (0.08, 0),
        }
        dx, dy = offsets.get(self.arrow_direction, (0, 0.08))

        ax.annotate(
            self.text,
            xy=(self.x, self.y),
            xytext=(self.x + dx, self.y + dy),
            fontsize=9,
            fontweight='bold',
            color=self.color,
            ha='center', va='bottom' if dy > 0 else 'top',
            arrowprops=dict(
                arrowstyle='->',
                color=self.color,
                lw=1.5,
                connectionstyle='arc3,rad=0.1'
            ),
            zorder=10
        )
