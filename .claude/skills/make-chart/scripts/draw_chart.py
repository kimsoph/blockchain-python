# -*- coding: utf-8 -*-
"""
make-chart 스킬 메인 모듈
다양한 유형의 차트를 생성하고 PNG 파일로 저장한다.

지원 차트 유형:
- line: 선 그래프 (시간에 따른 추이)
- bar: 막대 그래프 (항목 간 비교)
- time_series: 시계열 그래프 (날짜 기반)
- pie: 파이 차트 (비율/구성)
- combo: 복합 차트 (막대 + 선)
- scatter: 산점도 (두 변수 간 관계)
- heatmap: 히트맵 (2D 매트릭스 색상 시각화)
- radar: 레이더 차트 (다차원 지표 방사형 시각화)

사용법:
    from draw_chart import ChartDrawer

    drawer = ChartDrawer()
    drawer.draw_line(
        labels=['1월', '2월', '3월'],
        series=[{'name': '용산구', 'values': [23.1, 25.4, 23.3]}],
        title='월별 가격 추이',
        filename='price_trend'
    )
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union, Tuple

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 현재 스크립트 경로를 기준으로 utils 모듈 import
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

from utils import (
    get_korean_font,
    setup_matplotlib_korean,
    generate_filename,
    get_output_dir,
    get_color,
    DEFAULT_COLORS,
)


class ChartDrawer:
    """
    다양한 유형의 차트를 생성하는 클래스
    """

    def __init__(
        self,
        figsize: Tuple[int, int] = (10, 6),
        dpi: int = 300,
        output_dir: str = None
    ):
        """
        ChartDrawer 초기화

        Args:
            figsize: 차트 크기 (너비, 높이) 인치
            dpi: 해상도 (기본 300)
            output_dir: 출력 디렉토리 (기본: 9_Attachments/charts/AI_generates/)
        """
        self.figsize = figsize
        self.dpi = dpi
        self.output_dir = Path(output_dir) if output_dir else get_output_dir()
        self.colors = DEFAULT_COLORS

        # 한글 폰트 설정
        setup_matplotlib_korean()

    def _create_figure(self) -> Tuple[plt.Figure, plt.Axes]:
        """새 Figure와 Axes 생성"""
        fig, ax = plt.subplots(figsize=self.figsize)
        return fig, ax

    def _save_chart(
        self,
        fig: plt.Figure,
        filename: str,
        tight: bool = True
    ) -> str:
        """
        차트를 PNG 파일로 저장

        Args:
            fig: matplotlib Figure 객체
            filename: 파일명 (접두사)
            tight: tight_layout 적용 여부

        Returns:
            str: 저장된 파일의 전체 경로
        """
        if tight:
            fig.tight_layout()

        # 파일명 생성 (cht_ 접두사 추가)
        full_filename = generate_filename(f"cht_{filename}", 'png')
        output_path = self.output_dir / full_filename

        # 저장
        fig.savefig(
            output_path,
            dpi=self.dpi,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none'
        )

        # 메모리 해제
        plt.close(fig)

        print(f"[OK] 차트 저장 완료: {output_path}")
        return str(output_path)

    def draw_line(
        self,
        labels: List[str],
        series: List[Dict[str, Union[str, List[float]]]],
        title: str = '',
        xlabel: str = '',
        ylabel: str = '',
        filename: str = 'line_chart',
        markers: bool = True,
        grid: bool = True,
        legend_loc: str = 'best'
    ) -> str:
        """
        선 그래프를 생성한다.

        Args:
            labels: X축 레이블 목록
            series: 시리즈 목록 [{'name': '이름', 'values': [값들]}]
            title: 차트 제목
            xlabel: X축 레이블
            ylabel: Y축 레이블
            filename: 저장할 파일명 (접두사)
            markers: 데이터 포인트에 마커 표시
            grid: 그리드 표시
            legend_loc: 범례 위치

        Returns:
            str: 저장된 파일 경로
        """
        fig, ax = self._create_figure()

        x = np.arange(len(labels))

        for i, s in enumerate(series):
            marker = 'o' if markers else None
            ax.plot(
                x, s['values'],
                label=s['name'],
                color=get_color(i),
                marker=marker,
                markersize=6,
                linewidth=2
            )

        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)

        if grid:
            ax.grid(True, linestyle='--', alpha=0.7)

        if len(series) > 1:
            ax.legend(loc=legend_loc)

        return self._save_chart(fig, filename)

    def draw_bar(
        self,
        labels: List[str],
        series: List[Dict[str, Union[str, List[float]]]],
        title: str = '',
        xlabel: str = '',
        ylabel: str = '',
        filename: str = 'bar_chart',
        horizontal: bool = False,
        stacked: bool = False,
        bar_width: float = 0.35,
        show_values: bool = True
    ) -> str:
        """
        막대 그래프를 생성한다.

        Args:
            labels: 카테고리 레이블 목록
            series: 시리즈 목록 [{'name': '이름', 'values': [값들]}]
            title: 차트 제목
            xlabel: X축 레이블
            ylabel: Y축 레이블
            filename: 저장할 파일명 (접두사)
            horizontal: 가로 막대 그래프
            stacked: 누적 막대 그래프
            bar_width: 막대 너비
            show_values: 막대 위에 값 표시

        Returns:
            str: 저장된 파일 경로
        """
        fig, ax = self._create_figure()

        x = np.arange(len(labels))
        n_series = len(series)

        if stacked:
            # 누적 막대 그래프
            bottom = np.zeros(len(labels))
            for i, s in enumerate(series):
                if horizontal:
                    bars = ax.barh(
                        x, s['values'],
                        left=bottom,
                        label=s['name'],
                        color=get_color(i)
                    )
                else:
                    bars = ax.bar(
                        x, s['values'],
                        bottom=bottom,
                        label=s['name'],
                        color=get_color(i)
                    )
                bottom += np.array(s['values'])
        else:
            # 그룹 막대 그래프
            width = bar_width
            offset = width * (n_series - 1) / 2

            for i, s in enumerate(series):
                pos = x - offset + i * width
                if horizontal:
                    bars = ax.barh(
                        pos, s['values'],
                        height=width,
                        label=s['name'],
                        color=get_color(i)
                    )
                    if show_values:
                        for bar in bars:
                            width_val = bar.get_width()
                            ax.annotate(
                                f'{width_val:.1f}',
                                xy=(width_val, bar.get_y() + bar.get_height()/2),
                                xytext=(3, 0),
                                textcoords='offset points',
                                ha='left', va='center',
                                fontsize=9
                            )
                else:
                    bars = ax.bar(
                        pos, s['values'],
                        width=width,
                        label=s['name'],
                        color=get_color(i)
                    )
                    if show_values:
                        for bar in bars:
                            height = bar.get_height()
                            ax.annotate(
                                f'{height:.1f}',
                                xy=(bar.get_x() + bar.get_width()/2, height),
                                xytext=(0, 3),
                                textcoords='offset points',
                                ha='center', va='bottom',
                                fontsize=9
                            )

        if horizontal:
            ax.set_yticks(x)
            ax.set_yticklabels(labels)
            ax.set_xlabel(ylabel, fontsize=11)
            ax.set_ylabel(xlabel, fontsize=11)
        else:
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.set_xlabel(xlabel, fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, axis='y' if not horizontal else 'x', linestyle='--', alpha=0.7)

        if n_series > 1:
            ax.legend()

        return self._save_chart(fig, filename)

    def draw_time_series(
        self,
        dates: List[str],
        series: List[Dict[str, Union[str, List[float]]]],
        title: str = '',
        xlabel: str = '',
        ylabel: str = '',
        filename: str = 'time_series',
        date_format: str = '%Y-%m',
        date_rotation: int = 45,
        markers: bool = True,
        grid: bool = True
    ) -> str:
        """
        시계열 그래프를 생성한다.

        Args:
            dates: 날짜 문자열 목록 (예: ['2025-01-01', '2025-02-01'])
            series: 시리즈 목록 [{'name': '이름', 'values': [값들]}]
            title: 차트 제목
            xlabel: X축 레이블
            ylabel: Y축 레이블
            filename: 저장할 파일명 (접두사)
            date_format: X축 날짜 표시 형식
            date_rotation: X축 레이블 회전 각도
            markers: 데이터 포인트에 마커 표시
            grid: 그리드 표시

        Returns:
            str: 저장된 파일 경로
        """
        import matplotlib.dates as mdates
        from datetime import datetime

        fig, ax = self._create_figure()

        # 날짜 파싱
        date_objects = []
        for d in dates:
            if isinstance(d, str):
                # 다양한 형식 지원
                for fmt in ['%Y-%m-%d', '%Y-%m', '%Y/%m/%d', '%Y/%m']:
                    try:
                        date_objects.append(datetime.strptime(d, fmt))
                        break
                    except ValueError:
                        continue
            else:
                date_objects.append(d)

        for i, s in enumerate(series):
            marker = 'o' if markers else None
            ax.plot(
                date_objects, s['values'],
                label=s['name'],
                color=get_color(i),
                marker=marker,
                markersize=6,
                linewidth=2
            )

        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

        # 날짜 포맷 설정
        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
        plt.xticks(rotation=date_rotation)

        if grid:
            ax.grid(True, linestyle='--', alpha=0.7)

        if len(series) > 1:
            ax.legend()

        return self._save_chart(fig, filename)

    def draw_pie(
        self,
        labels: List[str],
        values: List[float],
        title: str = '',
        filename: str = 'pie_chart',
        explode: List[float] = None,
        autopct: str = '%1.1f%%',
        startangle: int = 90,
        show_legend: bool = True
    ) -> str:
        """
        파이 차트를 생성한다.

        Args:
            labels: 조각 레이블 목록
            values: 각 조각의 값
            title: 차트 제목
            filename: 저장할 파일명 (접두사)
            explode: 조각 분리 정도 목록 (예: [0.1, 0, 0])
            autopct: 비율 표시 형식
            startangle: 시작 각도
            show_legend: 범례 표시

        Returns:
            str: 저장된 파일 경로
        """
        fig, ax = self._create_figure()

        colors = [get_color(i) for i in range(len(values))]

        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels if not show_legend else None,
            explode=explode,
            autopct=autopct,
            startangle=startangle,
            colors=colors,
            pctdistance=0.75
        )

        # 텍스트 스타일
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')

        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

        if show_legend:
            ax.legend(
                wedges, labels,
                title="",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1)
            )

        return self._save_chart(fig, filename)

    def draw_combo(
        self,
        labels: List[str],
        bar_series: Dict[str, Union[str, List[float]]],
        line_series: Dict[str, Union[str, List[float]]],
        title: str = '',
        xlabel: str = '',
        filename: str = 'combo_chart',
        bar_color: str = '#4472C4',
        line_color: str = '#ED7D31',
        bar_width: float = 0.6,
        show_values: bool = True
    ) -> str:
        """
        복합 차트 (막대 + 선)를 생성한다.

        Args:
            labels: X축 레이블 목록
            bar_series: 막대 시리즈 {'name': '이름', 'values': [값들]}
            line_series: 선 시리즈 {'name': '이름', 'values': [값들]}
            title: 차트 제목
            xlabel: X축 레이블
            filename: 저장할 파일명 (접두사)
            bar_color: 막대 색상
            line_color: 선 색상
            bar_width: 막대 너비
            show_values: 값 표시 여부

        Returns:
            str: 저장된 파일 경로
        """
        fig, ax1 = self._create_figure()

        x = np.arange(len(labels))

        # 막대 그래프 (왼쪽 Y축)
        bars = ax1.bar(
            x, bar_series['values'],
            width=bar_width,
            color=bar_color,
            alpha=0.7,
            label=bar_series['name']
        )

        ax1.set_xlabel(xlabel, fontsize=11)
        ax1.set_ylabel(bar_series['name'], fontsize=11, color=bar_color)
        ax1.tick_params(axis='y', labelcolor=bar_color)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)

        # 막대 위에 값 표시
        if show_values:
            for bar in bars:
                height = bar.get_height()
                ax1.annotate(
                    f'{height:.1f}',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3),
                    textcoords='offset points',
                    ha='center', va='bottom',
                    fontsize=9,
                    color=bar_color
                )

        # 선 그래프 (오른쪽 Y축)
        ax2 = ax1.twinx()

        line = ax2.plot(
            x, line_series['values'],
            color=line_color,
            marker='o',
            markersize=8,
            linewidth=2.5,
            label=line_series['name']
        )

        ax2.set_ylabel(line_series['name'], fontsize=11, color=line_color)
        ax2.tick_params(axis='y', labelcolor=line_color)

        # 선 위에 값 표시
        if show_values:
            for i, v in enumerate(line_series['values']):
                ax2.annotate(
                    f'{v:.1f}',
                    xy=(x[i], v),
                    xytext=(0, 8),
                    textcoords='offset points',
                    ha='center', va='bottom',
                    fontsize=9,
                    color=line_color
                )

        ax1.set_title(title, fontsize=14, fontweight='bold', pad=15)

        # 범례 통합
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        ax1.grid(True, axis='y', linestyle='--', alpha=0.7)

        return self._save_chart(fig, filename)

    def draw_scatter(
        self,
        x_values: List[float],
        y_values: List[float],
        labels: List[str],
        title: str = '',
        xlabel: str = '',
        ylabel: str = '',
        filename: str = 'scatter_chart',
        highlight: List[str] = None,
        highlight_color: str = '#E74C3C',
        default_color: str = '#4472C4',
        show_labels: bool = True,
        show_ratio_lines: List[float] = None,
        grid: bool = True,
        size: int = 100,
        highlight_size: int = 150
    ) -> str:
        """
        산점도를 생성한다.

        Args:
            x_values: X축 값 목록
            y_values: Y축 값 목록
            labels: 각 점의 레이블 목록
            title: 차트 제목
            xlabel: X축 레이블
            ylabel: Y축 레이블
            filename: 저장할 파일명 (접두사)
            highlight: 강조할 레이블 목록 (예: ['IBK기업은행'])
            highlight_color: 강조 점 색상
            default_color: 기본 점 색상
            show_labels: 레이블 표시 여부
            show_ratio_lines: 비율선 표시 (예: [1, 2, 3]은 y/x=1,2,3 선 표시)
            grid: 그리드 표시
            size: 기본 점 크기
            highlight_size: 강조 점 크기

        Returns:
            str: 저장된 파일 경로
        """
        fig, ax = self._create_figure()

        highlight = highlight or []

        # 각 점 플로팅
        for i, (x, y, label) in enumerate(zip(x_values, y_values, labels)):
            is_highlight = label in highlight
            color = highlight_color if is_highlight else default_color
            s = highlight_size if is_highlight else size
            alpha = 0.8 if is_highlight else 0.6

            ax.scatter(
                x, y,
                c=color,
                s=s,
                alpha=alpha,
                edgecolors='white',
                linewidth=1.5,
                zorder=3 if is_highlight else 2
            )

            # 레이블 표시
            if show_labels:
                # 레이블 위치 조정 (겹침 방지)
                offset_y = 0.15 * (max(y_values) - min(y_values))
                va = 'bottom'

                # Y값이 매우 큰 경우 아래에 표시
                if y > (max(y_values) - min(y_values)) * 0.8 + min(y_values):
                    offset_y = -offset_y * 0.5
                    va = 'top'

                ax.annotate(
                    label,
                    (x, y),
                    xytext=(0, 8 if va == 'bottom' else -8),
                    textcoords='offset points',
                    ha='center',
                    va=va,
                    fontsize=9,
                    fontweight='bold' if is_highlight else 'normal'
                )

        # 비율선 표시 (y/x = ratio)
        if show_ratio_lines:
            x_min, x_max = min(x_values) * 0.9, max(x_values) * 1.1
            for ratio in show_ratio_lines:
                y_line = [x_min * ratio, x_max * ratio]
                ax.plot(
                    [x_min, x_max], y_line,
                    '--', alpha=0.3, color='gray', linewidth=1, zorder=1
                )
                # 비율 레이블
                ax.annotate(
                    f'{ratio}배',
                    (x_max * 0.98, x_max * 0.98 * ratio),
                    fontsize=8, color='gray', alpha=0.7,
                    ha='right'
                )

        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

        if grid:
            ax.grid(True, linestyle='--', alpha=0.3, zorder=0)

        # 범례 (강조 항목이 있는 경우)
        if highlight:
            ax.scatter([], [], c=highlight_color, s=100, label=', '.join(highlight), alpha=0.8)
            ax.scatter([], [], c=default_color, s=100, label='기타', alpha=0.6)
            ax.legend(loc='upper right')

        # 여백 조정
        x_margin = (max(x_values) - min(x_values)) * 0.1
        y_margin = (max(y_values) - min(y_values)) * 0.1
        ax.set_xlim(min(x_values) - x_margin, max(x_values) + x_margin)
        ax.set_ylim(min(y_values) - y_margin, max(y_values) + y_margin * 2)

        return self._save_chart(fig, filename)

    def draw_heatmap(
        self,
        data: List[List[float]],
        row_labels: List[str],
        col_labels: List[str],
        title: str = '',
        xlabel: str = '',
        ylabel: str = '',
        filename: str = 'heatmap',
        cmap: str = 'YlOrRd',
        show_values: bool = True,
        fmt: str = '.1f',
        vmin: float = None,
        vmax: float = None
    ) -> str:
        """
        히트맵을 생성한다. 2D 데이터를 색상 매트릭스로 시각화한다.

        Args:
            data: 2D 값 배열 (행 × 열)
            row_labels: Y축 레이블 (예: 그룹명)
            col_labels: X축 레이블 (예: 직급)
            title: 차트 제목
            xlabel: X축 레이블
            ylabel: Y축 레이블
            filename: 저장할 파일명 (접두사)
            cmap: 컬러맵 (기본: 'YlOrRd', 승진률에 적합한 노랑→빨강)
            show_values: 셀에 값 표시
            fmt: 값 포맷 (기본: '.1f')
            vmin: 최소값 (None이면 자동)
            vmax: 최대값 (None이면 자동)

        Returns:
            str: 저장된 파일 경로
        """
        arr = np.array(data, dtype=float)

        # 행 수에 따라 figsize 동적 조정
        n_rows = len(row_labels)
        n_cols = len(col_labels)
        fig_height = max(6, n_rows * 0.5 + 2)
        fig_width = max(10, n_cols * 1.2 + 2)
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        # 히트맵 그리기
        im = ax.imshow(
            arr,
            cmap=cmap,
            aspect='auto',
            vmin=vmin,
            vmax=vmax
        )

        # 축 레이블 설정
        ax.set_xticks(np.arange(n_cols))
        ax.set_yticks(np.arange(n_rows))
        ax.set_xticklabels(col_labels, fontsize=10)
        ax.set_yticklabels(row_labels, fontsize=10)

        # X축 레이블을 상단에도 표시
        ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

        # 셀에 값 표시
        if show_values:
            # 밝은/어두운 배경에 따라 텍스트 색상 자동 전환
            norm_arr = (arr - (vmin if vmin is not None else np.nanmin(arr))) / \
                       ((vmax if vmax is not None else np.nanmax(arr)) -
                        (vmin if vmin is not None else np.nanmin(arr)) + 1e-10)

            for i in range(n_rows):
                for j in range(n_cols):
                    val = arr[i, j]
                    if np.isnan(val):
                        continue
                    # 밝은 배경→검정, 어두운 배경→흰색
                    text_color = 'white' if norm_arr[i, j] > 0.6 else 'black'
                    ax.text(
                        j, i, f'{val:{fmt}}',
                        ha='center', va='center',
                        color=text_color, fontsize=9, fontweight='bold'
                    )

        # colorbar
        cbar = fig.colorbar(im, ax=ax, shrink=0.8)

        if xlabel:
            ax.set_xlabel(xlabel, fontsize=11)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=11)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

        return self._save_chart(fig, filename)

    def draw_radar(
        self,
        categories: List[str],
        series: List[Dict[str, Union[str, List[float]]]],
        title: str = '',
        filename: str = 'radar_chart',
        fill: bool = True,
        fill_alpha: float = 0.25,
        ylim: Tuple[float, float] = None,
        show_legend: bool = True
    ) -> str:
        """
        레이더 차트를 생성한다. 다차원 지표를 방사형으로 시각화한다.

        Args:
            categories: 축 레이블 (예: ['세대교체', '그룹강화', ...])
            series: 시리즈 목록 [{'name': '이번', 'values': [3, 2, 4, ...]}, ...]
            title: 차트 제목
            filename: 저장할 파일명 (접두사)
            fill: 영역 채우기 (기본: True)
            fill_alpha: 채우기 투명도 (기본: 0.25)
            ylim: Y축(반경) 범위 (min, max) (None이면 자동)
            show_legend: 범례 표시

        Returns:
            str: 저장된 파일 경로
        """
        n = len(categories)

        # 각 축의 각도 계산 (균등 분할)
        angles = [i / float(n) * 2 * np.pi for i in range(n)]
        angles += angles[:1]  # 닫힌 다각형을 위해 첫 값 반복

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

        # 시작 각도를 상단(12시)으로 설정
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        # 축 레이블 설정
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11)

        # Y축 범위 설정
        if ylim:
            ax.set_ylim(ylim)

        # 각 시리즈 플로팅
        for i, s in enumerate(series):
            values = s['values'] + s['values'][:1]  # 닫힌 다각형
            color = get_color(i)

            ax.plot(
                angles, values,
                'o-', linewidth=2, markersize=6,
                label=s['name'],
                color=color
            )

            if fill:
                ax.fill(angles, values, alpha=fill_alpha, color=color)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=25, y=1.08)

        if show_legend and len(series) > 1:
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

        return self._save_chart(fig, filename)


def main():
    """테스트용 메인 함수"""
    drawer = ChartDrawer()

    # 테스트 데이터: 용산구 vs 과천시 월별 평균가격
    labels = ['1월', '2월', '3월', '4월', '5월', '6월',
              '7월', '8월', '9월', '10월', '11월', '12월']

    yongsan = [23.1, 25.4, 23.3, 21.4, 20.2, 22.0,
               21.5, 18.3, 17.8, 21.1, 20.5, 20.7]

    gwacheon = [17.9, 18.5, 19.0, 19.5, 20.6, 21.3,
                20.0, 21.5, 21.1, 24.3, 25.0, 23.7]

    # 1. 선 그래프 테스트
    print("\n=== 선 그래프 테스트 ===")
    drawer.draw_line(
        labels=labels,
        series=[
            {'name': '용산구', 'values': yongsan},
            {'name': '과천시', 'values': gwacheon}
        ],
        title='2025년 용산구 vs 과천시 월별 평균 매매가격',
        ylabel='평균가격(억원)',
        xlabel='월',
        filename='test_line'
    )

    # 2. 막대 그래프 테스트
    print("\n=== 막대 그래프 테스트 ===")
    drawer.draw_bar(
        labels=['절대가격', '평당가격', '전세'],
        series=[
            {'name': '용산구', 'values': [-10.2, 3.0, 6.9]},
            {'name': '과천시', 'values': [32.0, 15.1, 15.8]}
        ],
        title='2025년 연간 상승률 비교',
        ylabel='상승률(%)',
        filename='test_bar'
    )

    # 3. 파이 차트 테스트
    print("\n=== 파이 차트 테스트 ===")
    drawer.draw_pie(
        labels=['래미안슈르', '과천위버필드', '과천자이', '푸르지오써밋', '기타'],
        values=[197, 115, 91, 81, 305],
        title='과천시 주요 아파트 거래 비중',
        filename='test_pie'
    )

    # 4. 복합 차트 테스트
    print("\n=== 복합 차트 테스트 ===")
    drawer.draw_combo(
        labels=['1월', '2월', '3월', '4월', '5월', '6월'],
        bar_series={'name': '평균가격(억원)', 'values': gwacheon[:6]},
        line_series={'name': '1월대비 상승률(%)', 'values': [0, 3.4, 6.2, 9.0, 15.1, 19.1]},
        title='과천시 상반기 가격 및 상승률',
        filename='test_combo'
    )

    # 5. 산점도 테스트
    print("\n=== 산점도 테스트 ===")
    drawer.draw_scatter(
        x_values=[1.07, 1.42, 1.39, 1.29, 1.48, 1.23, 1.08, 1.01],
        y_values=[3.53, 4.03, 3.86, 4.23, 2.89, 2.20, 4.65, 9.34],
        labels=['IBK기업은행', '국민은행', '신한은행', '하나은행', '우리은행', '농협은행', '산업은행', '수출입은행'],
        title='PPOP 기준 생산성 vs 급여 산점도 (2025E)',
        xlabel='1인당 연봉 (억원)',
        ylabel='1인당 PPOP (억원)',
        highlight=['IBK기업은행'],
        show_ratio_lines=[2, 3, 4],
        filename='test_scatter'
    )

    print("\n=== 모든 테스트 완료 ===")


if __name__ == '__main__':
    main()
