# -*- coding: utf-8 -*-
"""
make-infographic 스킬 메인 모듈 v4.0
Matplotlib GridSpec 기반 인포그래픽 생성

v4.0 변경사항:
    - 시각적 강화: 컬러 그림자, 글로우 효과, 그라데이션 배경
    - MetricCard 개선: accent_bar, highlight_value 옵션 추가
    - ChartBlock 개선: 시리즈별 다른 라인/마커 스타일
    - 새 컴포넌트: HighlightBox, DataAnnotation
    - 새 테마: vibrant (생동감 있는 색상)

v3.0 변경사항:
    - 미니멀 디자인 리뉴얼: 테두리 제거, 부드러운 그림자, 투명 배경
    - 새로운 테마 3종: minimal, elegant, clean (추천)
    - 세련된 타이포그래피: 더 작고 가벼운 폰트
    - 차트 스타일 개선: 그리드 최소화, 깔끔한 축 처리
    - 기본 테마 변경: corporate → minimal

v2.0 변경사항:
    - 새로운 컴포넌트: ProgressBar, Sparkline, Badge, Callout, ComparisonBar
    - 새로운 테마: ocean, forest, sunset, modern (기존: corporate, dark, light)
    - 시각적 개선: 그림자 효과, 그라데이션, 둥근 모서리
    - 다중 시리즈 차트 및 영역 채우기 지원
    - 향상된 MetricCard: 아이콘, 그라데이션 배경 옵션

사용법:
    from draw_infographic import InfographicDrawer

    drawer = InfographicDrawer(layout='dashboard', theme='minimal')
    drawer.set_title("2025년 실적 현황")
    drawer.add_metric('metric1', value=1234567890, label='총매출', unit='원', change=12.5)
    drawer.add_chart('chart_main', chart_type='line', data={...})
    drawer.add_progress_bar('progress1', value=75, max_value=100, label='목표 달성률')
    drawer.add_sparkline('spark1', values=[10, 15, 12, 18, 25, 22], label='추이')
    drawer.save('my_infographic')
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple, Any

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 현재 스크립트 경로를 기준으로 모듈 import
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

try:
    from .utils import (
        setup_matplotlib_korean,
        generate_filename,
        get_output_dir,
        get_theme,
        format_number,
        format_percent,
        list_themes,
    )
    from .components import (
        MetricCard, TextBlock, ChartBlock, Divider, IconMetric,
        ProgressBar, Sparkline, Badge, Callout, ComparisonBar,
        HighlightBox, DataAnnotation,  # v4.0
    )
    from .layouts import LayoutBuilder, get_layout, list_layouts
except ImportError:
    from utils import (
        setup_matplotlib_korean,
        generate_filename,
        get_output_dir,
        get_theme,
        format_number,
        format_percent,
        list_themes,
    )
    from components import (
        MetricCard, TextBlock, ChartBlock, Divider, IconMetric,
        ProgressBar, Sparkline, Badge, Callout, ComparisonBar,
        HighlightBox, DataAnnotation,  # v4.0
    )
    from layouts import LayoutBuilder, get_layout, list_layouts


class InfographicDrawer:
    """
    인포그래픽을 생성하는 메인 클래스
    """

    def __init__(
        self,
        layout: str = 'dashboard',
        theme: str = 'minimal',  # v3.0: corporate → minimal
        dpi: int = 300,
        output_dir: str = None,
    ):
        """
        InfographicDrawer 초기화

        Args:
            layout: 레이아웃 템플릿 이름
                - 'dashboard': 대시보드 스타일 (4개 메트릭 + 차트)
                - 'vertical': 세로 정렬 스타일
                - 'comparison': 좌우 비교 스타일
                - 'simple': 단순 (제목 + 차트)
                - 'metrics_grid': 6개 KPI 그리드
                - 'report': 보고서 스타일
            theme: 색상 테마
                - v3.0 추천: 'minimal', 'elegant', 'clean'
                - 기존: 'corporate', 'dark', 'light', 'ocean', 'forest', 'sunset', 'modern'
            dpi: 출력 해상도 (기본 300)
            output_dir: 출력 디렉토리
        """
        self.layout_name = layout
        self.theme_name = theme
        self.theme = get_theme(theme)
        self.dpi = dpi
        self.output_dir = Path(output_dir) if output_dir else get_output_dir()

        # 한글 폰트 설정
        setup_matplotlib_korean()

        # 레이아웃 빌더
        self.builder = LayoutBuilder(layout=layout, theme=theme)
        self.fig = None
        self.axes = {}

        # 컴포넌트 저장
        self.components: Dict[str, Any] = {}

    def _ensure_layout(self) -> None:
        """레이아웃이 생성되지 않았으면 생성한다."""
        if self.fig is None:
            self.fig, self.axes = self.builder.build()

    def get_cell_names(self) -> List[str]:
        """
        현재 레이아웃의 셀 이름 목록을 반환한다.

        Returns:
            List[str]: 셀 이름 목록
        """
        return self.builder.get_cell_names()

    def set_title(
        self,
        text: str,
        cell_name: str = 'title',
        style: str = 'title',
    ) -> 'InfographicDrawer':
        """
        제목을 설정한다.

        Args:
            text: 제목 텍스트
            cell_name: 셀 이름 (기본: 'title')
            style: 스타일 ('title', 'subtitle')

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = TextBlock(
            text=text,
            style=style,
            align='center',
            theme=self.theme_name,
        )
        self.components[cell_name] = component
        return self

    def set_subtitle(
        self,
        text: str,
        cell_name: str = 'subtitle',
    ) -> 'InfographicDrawer':
        """
        부제목을 설정한다.

        Args:
            text: 부제목 텍스트
            cell_name: 셀 이름 (기본: 'subtitle')

        Returns:
            self (메서드 체이닝용)
        """
        return self.set_title(text, cell_name, style='subtitle')

    def add_metric(
        self,
        cell_name: str,
        value: Union[float, int, str],
        label: str,
        change: float = None,
        change_label: str = None,
        change_unit: str = '%',  # v3.1: '%' 또는 '%p'
        unit: str = '',
        format_value: bool = True,
        accent_bar: bool = False,  # v4.0
        highlight_value: bool = False,  # v4.0
        accent_color: str = None,  # v4.0
    ) -> 'InfographicDrawer':
        """
        메트릭 카드를 추가한다.

        Args:
            cell_name: 셀 이름 (예: 'metric1', 'metric2')
            value: 메인 값
            label: 레이블 (예: '총매출')
            change: 변화율 또는 변화량 (예: 12.5)
            change_label: 변화율 레이블 (예: '전월 대비')
            change_unit: 변화량 단위 ('%': 상대적 변화율, '%p': 퍼센트 포인트)
            unit: 단위 (예: '억원')
            format_value: 숫자 포맷팅 적용 여부
            accent_bar: 좌측 컬러 스트라이프 표시 (v4.0)
            highlight_value: 값 뒤 하이라이트 원 표시 (v4.0)
            accent_color: 액센트 색상 (v4.0, None이면 테마 primary)

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = MetricCard(
            value=value,
            label=label,
            change=change,
            change_label=change_label,
            change_unit=change_unit,  # v3.1
            unit=unit,
            theme=self.theme_name,
            format_value=format_value,
            accent_bar=accent_bar,  # v4.0
            highlight_value=highlight_value,  # v4.0
            accent_color=accent_color,  # v4.0
        )
        self.components[cell_name] = component
        return self

    def add_chart(
        self,
        cell_name: str,
        chart_type: str,
        data: Dict,
        title: str = '',
    ) -> 'InfographicDrawer':
        """
        차트를 추가한다.

        Args:
            cell_name: 셀 이름 (예: 'chart_main', 'chart_sub1')
            chart_type: 차트 유형 ('line', 'bar', 'pie', 'donut', 'hbar')
            data: 차트 데이터
                - line/bar: {'labels': [...], 'values': [...]}
                - pie/donut: {'labels': [...], 'values': [...]}
            title: 차트 제목

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = ChartBlock(
            chart_type=chart_type,
            data=data,
            title=title,
            theme=self.theme_name,
        )
        self.components[cell_name] = component
        return self

    def add_text(
        self,
        cell_name: str,
        text: str,
        style: str = 'body',
        align: str = 'center',
    ) -> 'InfographicDrawer':
        """
        텍스트 블록을 추가한다.

        Args:
            cell_name: 셀 이름
            text: 텍스트 내용
            style: 스타일 ('title', 'subtitle', 'body', 'caption')
            align: 정렬 ('left', 'center', 'right')

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = TextBlock(
            text=text,
            style=style,
            align=align,
            theme=self.theme_name,
        )
        self.components[cell_name] = component
        return self

    def add_icon_metric(
        self,
        cell_name: str,
        icon: str,
        value: Union[float, int, str],
        label: str = '',
    ) -> 'InfographicDrawer':
        """
        아이콘 메트릭을 추가한다.

        Args:
            cell_name: 셀 이름
            icon: 아이콘 키 또는 유니코드 (예: 'user', 'chart', '📊')
            value: 값
            label: 레이블

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = IconMetric(
            icon=icon,
            value=value,
            label=label,
            theme=self.theme_name,
        )
        self.components[cell_name] = component
        return self

    def add_progress_bar(
        self,
        cell_name: str,
        value: float,
        max_value: float = 100,
        label: str = '',
        show_percent: bool = True,
        bar_color: str = None,
        bg_color: str = None,
    ) -> 'InfographicDrawer':
        """
        프로그레스 바를 추가한다.

        Args:
            cell_name: 셀 이름
            value: 현재 값
            max_value: 최대 값 (기본 100)
            label: 레이블
            show_percent: 퍼센트 표시 여부
            bar_color: 바 색상 (None이면 테마 기본)
            bg_color: 배경 색상 (None이면 테마 기본)

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = ProgressBar(
            value=value,
            max_value=max_value,
            label=label,
            show_percent=show_percent,
            theme=self.theme_name,
            bar_color=bar_color,
            bg_color=bg_color,
        )
        self.components[cell_name] = component
        return self

    def add_sparkline(
        self,
        cell_name: str,
        values: List[float],
        label: str = '',
        show_endpoints: bool = True,
        fill: bool = True,
        line_color: str = None,
    ) -> 'InfographicDrawer':
        """
        스파크라인 차트를 추가한다.

        Args:
            cell_name: 셀 이름
            values: 데이터 값 리스트
            label: 레이블
            show_endpoints: 시작/끝 점 표시 여부
            fill: 영역 채우기 여부
            line_color: 선 색상 (None이면 테마 기본)

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = Sparkline(
            values=values,
            label=label,
            show_endpoints=show_endpoints,
            fill=fill,
            theme=self.theme_name,
            line_color=line_color,
        )
        self.components[cell_name] = component
        return self

    def add_badge(
        self,
        cell_name: str,
        text: str,
        badge_type: str = 'primary',
        size: str = 'medium',
    ) -> 'InfographicDrawer':
        """
        배지를 추가한다.

        Args:
            cell_name: 셀 이름
            text: 배지 텍스트
            badge_type: 배지 유형 ('primary', 'success', 'warning', 'danger', 'info')
            size: 크기 ('small', 'medium', 'large')

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = Badge(
            text=text,
            badge_type=badge_type,
            size=size,
            theme=self.theme_name,
        )
        self.components[cell_name] = component
        return self

    def add_callout(
        self,
        cell_name: str,
        text: str,
        title: str = '',
        callout_type: str = 'info',
        icon: str = None,
    ) -> 'InfographicDrawer':
        """
        콜아웃 박스를 추가한다.

        Args:
            cell_name: 셀 이름
            text: 본문 텍스트
            title: 제목 (선택)
            callout_type: 유형 ('info', 'success', 'warning', 'danger')
            icon: 아이콘 (선택)

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = Callout(
            text=text,
            title=title,
            callout_type=callout_type,
            icon=icon,
            theme=self.theme_name,
        )
        self.components[cell_name] = component
        return self

    def add_comparison_bar(
        self,
        cell_name: str,
        left_value: float,
        right_value: float,
        left_label: str = '',
        right_label: str = '',
        center_label: str = '',
    ) -> 'InfographicDrawer':
        """
        좌우 비교 막대를 추가한다.

        Args:
            cell_name: 셀 이름
            left_value: 왼쪽 값
            right_value: 오른쪽 값
            left_label: 왼쪽 레이블
            right_label: 오른쪽 레이블
            center_label: 중앙 레이블 (비교 제목)

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = ComparisonBar(
            left_value=left_value,
            right_value=right_value,
            left_label=left_label,
            right_label=right_label,
            center_label=center_label,
            theme=self.theme_name,
        )
        self.components[cell_name] = component
        return self

    def add_highlight_box(
        self,
        cell_name: str,
        text: str,
        highlight_type: str = 'insight',
        title: str = None,
        show_icon: bool = True,
        show_label: bool = True,
    ) -> 'InfographicDrawer':
        """
        하이라이트 박스를 추가한다. (v4.0)
        핵심 인사이트, 경고, 성공 메시지 등을 강조 표시할 때 사용.

        Args:
            cell_name: 셀 이름
            text: 본문 텍스트
            highlight_type: 타입 ('insight', 'warning', 'success', 'key', 'info', 'danger')
            title: 커스텀 제목 (None이면 타입 레이블 사용)
            show_icon: 아이콘 표시 여부
            show_label: 타입 레이블 표시 여부

        Returns:
            self (메서드 체이닝용)
        """
        self._ensure_layout()
        component = HighlightBox(
            text=text,
            highlight_type=highlight_type,
            title=title,
            theme=self.theme_name,
            show_icon=show_icon,
            show_label=show_label,
        )
        self.components[cell_name] = component
        return self

    def render(self) -> plt.Figure:
        """
        인포그래픽을 렌더링한다.

        Returns:
            Figure: matplotlib Figure 객체
        """
        self._ensure_layout()

        # 각 컴포넌트 렌더링
        for cell_name, component in self.components.items():
            if cell_name in self.axes:
                ax = self.axes[cell_name]
                component.render(ax)

        # 사용하지 않은 셀은 숨김
        for cell_name, ax in self.axes.items():
            if cell_name not in self.components:
                ax.axis('off')

        self.fig.tight_layout(rect=[0, 0, 1, 0.98])

        return self.fig

    def save(
        self,
        filename: str = 'infographic',
        show: bool = False,
    ) -> str:
        """
        인포그래픽을 파일로 저장한다.

        Args:
            filename: 파일명 접두사
            show: 저장 후 화면에 표시할지 여부

        Returns:
            str: 저장된 파일 경로
        """
        # 렌더링
        fig = self.render()

        # 파일명 생성
        # info_ 접두사 추가
        full_filename = generate_filename(f"info_{filename}", 'png')
        output_path = self.output_dir / full_filename

        # 저장
        fig.savefig(
            output_path,
            dpi=self.dpi,
            bbox_inches='tight',
            facecolor=self.theme['light'],
            edgecolor='none',
        )

        print(f"[OK] 인포그래픽 저장 완료: {output_path}")

        # 옵시디언 삽입 코드 출력 (년월 서브폴더 포함)
        from datetime import datetime
        current_ym = datetime.now().strftime('%Y%m')
        obsidian_embed = f"![[images/{current_ym}/{full_filename}]]"
        print(f"[INFO] 옵시디언 삽입: {obsidian_embed}")

        if show:
            plt.show()

        # 메모리 해제
        plt.close(fig)
        self.fig = None
        self.axes = {}
        self.components = {}

        return str(output_path)

    def preview(self) -> None:
        """
        인포그래픽을 화면에 미리보기로 표시한다.
        """
        fig = self.render()
        plt.show()
        plt.close(fig)


# ============================================================
# 편의 함수
# ============================================================

def create_dashboard(
    title: str,
    metrics: List[Dict],
    main_chart: Dict,
    sub_charts: List[Dict] = None,
    filename: str = 'dashboard',
    theme: str = 'corporate',
) -> str:
    """
    대시보드 인포그래픽을 빠르게 생성한다.

    Args:
        title: 제목
        metrics: 메트릭 목록
            [{'value': 123, 'label': '총매출', 'change': 5.2, 'unit': '억'}, ...]
        main_chart: 메인 차트 데이터
            {'type': 'line', 'title': '추이', 'data': {...}}
        sub_charts: 서브 차트 목록 (최대 2개)
        filename: 저장 파일명
        theme: 색상 테마

    Returns:
        str: 저장된 파일 경로
    """
    drawer = InfographicDrawer(layout='dashboard', theme=theme)
    drawer.set_title(title)

    # 메트릭 추가 (최대 4개)
    for i, m in enumerate(metrics[:4]):
        drawer.add_metric(
            cell_name=f'metric{i+1}',
            value=m.get('value'),
            label=m.get('label', ''),
            change=m.get('change'),
            change_label=m.get('change_label'),
            unit=m.get('unit', ''),
        )

    # 메인 차트
    if main_chart:
        drawer.add_chart(
            cell_name='chart_main',
            chart_type=main_chart.get('type', 'line'),
            data=main_chart.get('data', {}),
            title=main_chart.get('title', ''),
        )

    # 서브 차트
    if sub_charts:
        for i, sc in enumerate(sub_charts[:2]):
            drawer.add_chart(
                cell_name=f'chart_sub{i+1}',
                chart_type=sc.get('type', 'bar'),
                data=sc.get('data', {}),
                title=sc.get('title', ''),
            )

    return drawer.save(filename)


def create_comparison(
    title: str,
    left: Dict,
    right: Dict,
    filename: str = 'comparison',
    theme: str = 'corporate',
) -> str:
    """
    좌우 비교 인포그래픽을 빠르게 생성한다.

    Args:
        title: 메인 제목
        left: 왼쪽 데이터
            {'title': 'A사', 'metric': {...}, 'chart': {...}}
        right: 오른쪽 데이터
            {'title': 'B사', 'metric': {...}, 'chart': {...}}
        filename: 저장 파일명
        theme: 색상 테마

    Returns:
        str: 저장된 파일 경로
    """
    drawer = InfographicDrawer(layout='comparison', theme=theme)
    drawer.set_title(title)

    # 왼쪽
    drawer.add_text('left_title', left.get('title', ''), style='subtitle')
    if left.get('metric'):
        m = left['metric']
        drawer.add_metric(
            'left_metric',
            value=m.get('value'),
            label=m.get('label', ''),
            change=m.get('change'),
            unit=m.get('unit', ''),
        )
    if left.get('chart'):
        c = left['chart']
        drawer.add_chart(
            'left_chart',
            chart_type=c.get('type', 'bar'),
            data=c.get('data', {}),
            title=c.get('title', ''),
        )

    # 오른쪽
    drawer.add_text('right_title', right.get('title', ''), style='subtitle')
    if right.get('metric'):
        m = right['metric']
        drawer.add_metric(
            'right_metric',
            value=m.get('value'),
            label=m.get('label', ''),
            change=m.get('change'),
            unit=m.get('unit', ''),
        )
    if right.get('chart'):
        c = right['chart']
        drawer.add_chart(
            'right_chart',
            chart_type=c.get('type', 'bar'),
            data=c.get('data', {}),
            title=c.get('title', ''),
        )

    return drawer.save(filename)


# ============================================================
# 테스트
# ============================================================

def main():
    """테스트용 메인 함수"""
    print("=== make-infographic v2.0 테스트 ===\n")
    print(f"사용 가능한 레이아웃: {list_layouts()}")
    print(f"사용 가능한 테마: {list_themes()}\n")

    # 1. 대시보드 레이아웃 테스트 (corporate 테마)
    print("1. 대시보드 레이아웃 테스트 (corporate 테마)")
    drawer = InfographicDrawer(layout='dashboard', theme='corporate')

    drawer.set_title("2025년 상반기 실적 현황")

    drawer.add_metric('metric1', value=1234567890, label='총매출', unit='원', change=12.5, change_label='전년 대비')
    drawer.add_metric('metric2', value=856, label='신규 고객', change=8.3)
    drawer.add_metric('metric3', value=92.5, label='고객 만족도', unit='%', change=-1.2)
    drawer.add_metric('metric4', value=45, label='신규 프로젝트', change=15.0)

    drawer.add_chart(
        'chart_main',
        chart_type='line',
        data={
            'labels': ['1월', '2월', '3월', '4월', '5월', '6월'],
            'values': [120, 135, 142, 155, 168, 180],
        },
        title='월별 매출 추이'
    )

    drawer.add_chart(
        'chart_sub1',
        chart_type='bar',
        data={
            'labels': ['A팀', 'B팀', 'C팀', 'D팀'],
            'values': [85, 72, 95, 68],
        },
        title='팀별 실적'
    )

    drawer.add_chart(
        'chart_sub2',
        chart_type='pie',
        data={
            'labels': ['제품A', '제품B', '제품C', '기타'],
            'values': [45, 30, 15, 10],
        },
        title='제품별 비중'
    )

    path1 = drawer.save('test_dashboard_corporate')
    print(f"  → 저장: {path1}\n")

    # 2. Ocean 테마 대시보드 테스트
    print("2. 대시보드 레이아웃 테스트 (ocean 테마)")
    drawer_ocean = InfographicDrawer(layout='dashboard', theme='ocean')

    drawer_ocean.set_title("2025년 상반기 실적 현황 (Ocean)")

    drawer_ocean.add_metric('metric1', value=1234567890, label='총매출', unit='원', change=12.5)
    drawer_ocean.add_metric('metric2', value=856, label='신규 고객', change=8.3)
    drawer_ocean.add_metric('metric3', value=92.5, label='고객 만족도', unit='%', change=-1.2)
    drawer_ocean.add_metric('metric4', value=45, label='신규 프로젝트', change=15.0)

    drawer_ocean.add_chart(
        'chart_main',
        chart_type='line',
        data={
            'labels': ['1월', '2월', '3월', '4월', '5월', '6월'],
            'series': [
                {'name': 'A팀', 'values': [120, 135, 142, 155, 168, 180]},
                {'name': 'B팀', 'values': [100, 110, 125, 140, 150, 165]},
            ],
        },
        title='팀별 월별 매출 추이 (다중 시리즈)'
    )

    drawer_ocean.add_chart(
        'chart_sub1',
        chart_type='bar',
        data={
            'labels': ['A팀', 'B팀', 'C팀', 'D팀'],
            'values': [85, 72, 95, 68],
        },
        title='팀별 실적'
    )

    drawer_ocean.add_chart(
        'chart_sub2',
        chart_type='donut',
        data={
            'labels': ['제품A', '제품B', '제품C', '기타'],
            'values': [45, 30, 15, 10],
        },
        title='제품별 비중 (도넛)'
    )

    path_ocean = drawer_ocean.save('test_dashboard_ocean')
    print(f"  → 저장: {path_ocean}\n")

    # 3. 비교 레이아웃 테스트
    print("3. 비교 레이아웃 테스트 (corporate 테마)")
    drawer2 = InfographicDrawer(layout='comparison', theme='corporate')

    drawer2.set_title("용산구 vs 과천시 아파트 가격 비교")

    drawer2.add_text('left_title', '용산구', style='subtitle')
    drawer2.add_metric('left_metric', value=20.7, label='평균 매매가격', unit='억원', change=-10.2)
    drawer2.add_chart(
        'left_chart',
        chart_type='line',
        data={
            'labels': ['1월', '3월', '6월', '9월', '12월'],
            'values': [23.1, 23.3, 22.0, 17.8, 20.7],
        },
        title='월별 가격 추이'
    )

    drawer2.add_text('right_title', '과천시', style='subtitle')
    drawer2.add_metric('right_metric', value=23.7, label='평균 매매가격', unit='억원', change=32.0)
    drawer2.add_chart(
        'right_chart',
        chart_type='line',
        data={
            'labels': ['1월', '3월', '6월', '9월', '12월'],
            'values': [17.9, 19.0, 21.3, 21.1, 23.7],
        },
        title='월별 가격 추이'
    )

    path2 = drawer2.save('test_comparison')
    print(f"  → 저장: {path2}\n")

    # 4. 메트릭 그리드 테스트 (forest 테마)
    print("4. 메트릭 그리드 테스트 (forest 테마)")
    drawer3 = InfographicDrawer(layout='metrics_grid', theme='forest')

    drawer3.set_title("핵심 성과 지표 (KPI)")

    kpis = [
        (12500000000, '총자산', '억원', 5.2),
        (8900000000, '순이익', '원', 12.3),
        (95.8, 'BIS비율', '%', 0.5),
        (1.2, '연체율', '%', -0.3),
        (4250, '직원수', '명', 2.1),
        (892, '영업점수', '개', -1.5),
    ]

    for i, (value, label, unit, change) in enumerate(kpis, 1):
        drawer3.add_metric(f'metric{i}', value=value, label=label, unit=unit, change=change)

    path3 = drawer3.save('test_metrics_grid_forest')
    print(f"  → 저장: {path3}\n")

    # 5. 새로운 컴포넌트 테스트 (sunset 테마, vertical 레이아웃)
    print("5. 새로운 컴포넌트 테스트 (sunset 테마)")
    drawer4 = InfographicDrawer(layout='vertical', theme='sunset')

    drawer4.set_title("새로운 컴포넌트 데모")

    # ProgressBar, Sparkline, Badge, Callout, ComparisonBar 테스트
    # vertical 레이아웃의 셀: title, content_top, content_main, content_bottom, footer

    drawer4.add_metric('content_top', value=78.5, label='목표 달성률', unit='%', change=5.2)

    drawer4.add_chart(
        'content_main',
        chart_type='line',
        data={
            'labels': ['1월', '2월', '3월', '4월', '5월', '6월'],
            'series': [
                {'name': '실적', 'values': [65, 70, 72, 75, 78, 78.5]},
                {'name': '목표', 'values': [70, 72, 74, 76, 78, 80]},
            ],
        },
        title='목표 대비 실적 추이'
    )

    drawer4.add_text('content_bottom', '※ 상반기 목표 대비 98.1% 달성', style='caption')

    path4 = drawer4.save('test_new_components_sunset')
    print(f"  → 저장: {path4}\n")

    # 6. Modern 테마 테스트
    print("6. Simple 레이아웃 테스트 (modern 테마)")
    drawer5 = InfographicDrawer(layout='simple', theme='modern')

    drawer5.set_title("2025년 분기별 성장률")
    drawer5.add_chart(
        'chart',
        chart_type='bar',
        data={
            'labels': ['Q1', 'Q2', 'Q3', 'Q4'],
            'series': [
                {'name': '매출', 'values': [100, 120, 135, 150]},
                {'name': '비용', 'values': [80, 90, 100, 110]},
            ],
        },
        title='분기별 매출 vs 비용'
    )

    path5 = drawer5.save('test_simple_modern')
    print(f"  → 저장: {path5}\n")

    print("=" * 50)
    print("=== 모든 테스트 완료 ===")
    print(f"\n사용 가능한 레이아웃: {list_layouts()}")
    print(f"사용 가능한 테마: {list_themes()}")


if __name__ == '__main__':
    main()
