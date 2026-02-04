# -*- coding: utf-8 -*-
"""
make-gantt_chart 스킬 메인 모듈
matplotlib 기반 간트차트 생성 클래스
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import numpy as np

from utils import (
    setup_matplotlib_korean,
    generate_filename,
    get_output_dir,
    get_theme,
    parse_dsl,
    parse_date,
)


class GanttDrawer:
    """
    간트차트 생성 클래스.
    matplotlib의 barh를 사용하여 간트차트를 생성한다.

    Features:
        - DSL 또는 Python API로 태스크/마일스톤 정의
        - 진행률 표시 (색상 오버레이)
        - 마일스톤 마커 (다이아몬드)
        - 그룹/카테고리 지원
        - 오늘 날짜 라인
        - 5가지 테마 지원
        - 순차 인덱스 모드 (날짜 없이 1, 2, 3...)

    Example:
        >>> drawer = GanttDrawer(theme='minimal')
        >>> drawer.set_title('프로젝트 일정')
        >>> drawer.add_task('기획', '2026-01-01', '2026-01-05', progress=100)
        >>> drawer.add_task('개발', '2026-01-06', '2026-01-20', progress=60)
        >>> drawer.add_milestone('킥오프', '2026-01-01')
        >>> drawer.save('project_schedule')
    """

    def __init__(
        self,
        theme: str = 'minimal',
        dpi: int = 300,
        output_dir: str = None,
        show_today: bool = True,
        figsize: Tuple[float, float] = None
    ):
        """
        GanttDrawer 초기화.

        Args:
            theme: 테마 이름 (minimal, elegant, clean, corporate, dark)
            dpi: 출력 해상도 (기본: 300)
            output_dir: 출력 디렉토리 (기본: 9_Attachments/images/{YYYYMM}/)
            show_today: 오늘 날짜 라인 표시 여부
            figsize: 그림 크기 (width, height) 인치 단위
        """
        # 한글 폰트 설정
        setup_matplotlib_korean()

        self.theme_name = theme
        self.theme = get_theme(theme)
        self.dpi = dpi
        self.output_dir = output_dir
        self.show_today = show_today
        self.figsize = figsize

        # 데이터 저장소
        self.title = ''
        self.tasks: List[Dict[str, Any]] = []
        self.milestones: List[Dict[str, Any]] = []
        self.groups: List[str] = []
        self.is_sequential = False  # 순차 모드 여부

    def set_title(self, title: str) -> 'GanttDrawer':
        """
        차트 제목을 설정한다.

        Args:
            title: 제목 문자열

        Returns:
            self (메서드 체이닝)
        """
        self.title = title
        return self

    def add_task(
        self,
        name: str,
        start: Union[str, datetime, None] = None,
        end: Union[str, datetime, None] = None,
        progress: int = 0,
        group: str = None,
        duration: int = 1
    ) -> 'GanttDrawer':
        """
        태스크를 추가한다.

        Args:
            name: 태스크 이름
            start: 시작일 (문자열 또는 datetime, 순차모드시 None)
            end: 종료일 (문자열 또는 datetime, 순차모드시 None)
            progress: 진행률 (0-100)
            group: 그룹/카테고리 (선택)
            duration: 순차 모드에서 기간 (기본: 1)

        Returns:
            self (메서드 체이닝)
        """
        # 날짜 파싱
        start_date = parse_date(start) if isinstance(start, str) else start
        end_date = parse_date(end) if isinstance(end, str) else end

        # 순차 모드 판별
        if start_date is None and end_date is None:
            self.is_sequential = True

        # 그룹 등록
        if group and group not in self.groups:
            self.groups.append(group)

        self.tasks.append({
            'name': name,
            'start': start_date,
            'end': end_date,
            'progress': min(100, max(0, progress)),
            'group': group,
            'duration': duration
        })

        return self

    def add_milestone(
        self,
        name: str,
        date: Union[str, datetime]
    ) -> 'GanttDrawer':
        """
        마일스톤을 추가한다.

        Args:
            name: 마일스톤 이름
            date: 날짜 (문자열 또는 datetime)

        Returns:
            self (메서드 체이닝)
        """
        milestone_date = parse_date(date) if isinstance(date, str) else date

        if milestone_date:
            self.milestones.append({
                'name': name,
                'date': milestone_date
            })
            self.is_sequential = False  # 마일스톤이 있으면 순차 모드 아님

        return self

    def parse_dsl_text(self, dsl_text: str) -> 'GanttDrawer':
        """
        DSL 텍스트를 파싱하여 태스크와 마일스톤을 설정한다.

        Args:
            dsl_text: DSL 텍스트

        Returns:
            self (메서드 체이닝)
        """
        parsed = parse_dsl(dsl_text)

        if parsed['title']:
            self.title = parsed['title']

        self.groups = parsed['groups']
        self.is_sequential = parsed['is_sequential']

        for task in parsed['tasks']:
            self.tasks.append(task)

        for milestone in parsed['milestones']:
            self.milestones.append(milestone)

        return self

    def _prepare_sequential_data(self) -> Tuple[List[str], List[float], List[float]]:
        """
        순차 모드용 데이터를 준비한다.
        X축은 순차 인덱스 (1, 2, 3...)

        Returns:
            (task_names, start_positions, durations)
        """
        names = []
        starts = []
        durations = []

        current_pos = 0
        for task in self.tasks:
            names.append(task['name'])
            starts.append(current_pos)
            dur = task.get('duration', 1)
            durations.append(dur)
            current_pos += dur

        return names, starts, durations

    def _prepare_date_data(self) -> Tuple[List[str], List[datetime], List[float], datetime, datetime]:
        """
        날짜 모드용 데이터를 준비한다.

        Returns:
            (task_names, start_dates, durations_days, min_date, max_date)
        """
        names = []
        start_dates = []
        durations = []

        min_date = None
        max_date = None

        for task in self.tasks:
            names.append(task['name'])
            start_dates.append(task['start'])

            # 기간 계산 (일 단위)
            delta = task['end'] - task['start']
            durations.append(delta.days + 1)  # 종료일 포함

            # 최소/최대 날짜 갱신
            if min_date is None or task['start'] < min_date:
                min_date = task['start']
            if max_date is None or task['end'] > max_date:
                max_date = task['end']

        # 마일스톤 날짜도 고려
        for milestone in self.milestones:
            if min_date is None or milestone['date'] < min_date:
                min_date = milestone['date']
            if max_date is None or milestone['date'] > max_date:
                max_date = milestone['date']

        return names, start_dates, durations, min_date, max_date

    def render(self) -> plt.Figure:
        """
        간트차트를 렌더링한다.

        Returns:
            matplotlib Figure 객체
        """
        if not self.tasks:
            raise ValueError("태스크가 없습니다. add_task() 또는 parse_dsl_text()를 먼저 호출하세요.")

        theme = self.theme

        # 그림 크기 결정
        num_tasks = len(self.tasks)
        if self.figsize:
            figsize = self.figsize
        else:
            # 태스크 수에 따라 자동 조정
            figsize = (12, max(4, num_tasks * 0.6 + 2))

        fig, ax = plt.subplots(figsize=figsize, facecolor=theme['bgcolor'])
        ax.set_facecolor(theme['bgcolor'])

        if self.is_sequential:
            self._render_sequential(ax, theme)
        else:
            self._render_dated(ax, theme)

        # 제목
        if self.title:
            ax.set_title(
                self.title,
                fontsize=14,
                fontweight='bold',
                color=theme['fontcolor'],
                pad=20
            )

        # 레이아웃 조정
        plt.tight_layout()

        return fig

    def _render_sequential(self, ax: plt.Axes, theme: Dict[str, Any]) -> None:
        """
        순차 모드 차트를 렌더링한다.
        X축은 순차 인덱스 (1, 2, 3...)
        """
        names, starts, durations = self._prepare_sequential_data()

        # Y축 위치 (위에서 아래로)
        y_positions = list(range(len(names) - 1, -1, -1))

        # 태스크 바 그리기
        colors = theme['task_colors']
        for i, (y, start, dur, task) in enumerate(zip(y_positions, starts, durations, self.tasks)):
            color = colors[i % len(colors)]

            # 배경 바
            ax.barh(
                y,
                dur,
                left=start,
                height=0.6,
                color=color,
                alpha=0.8,
                edgecolor='white',
                linewidth=1
            )

            # 진행률 오버레이
            progress = task.get('progress', 0)
            if progress > 0:
                progress_width = dur * (progress / 100)
                ax.barh(
                    y,
                    progress_width,
                    left=start,
                    height=0.6,
                    color=theme['progress_color'],
                    alpha=0.9,
                    edgecolor='none'
                )

            # 태스크 라벨 (바 안에 표시)
            label_x = start + dur / 2
            ax.text(
                label_x, y,
                names[i],
                ha='center',
                va='center',
                fontsize=10,
                color='white',
                fontweight='bold'
            )

        # X축 설정 (정수 인덱스)
        total_duration = sum(durations)
        ax.set_xlim(-0.5, total_duration + 0.5)
        ax.set_xticks(range(0, total_duration + 1))
        ax.set_xticklabels([str(i) for i in range(0, total_duration + 1)])
        ax.set_xlabel('순서 (Index)', color=theme['fontcolor'])

        # Y축 설정
        ax.set_yticks(y_positions)
        ax.set_yticklabels(names)
        ax.set_ylim(-0.5, len(names) - 0.5)

        # 그리드
        ax.grid(True, axis='x', alpha=0.3, color=theme['grid_color'], linestyle='--')

        # 축 스타일
        ax.tick_params(colors=theme['fontcolor'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(theme['grid_color'])
        ax.spines['bottom'].set_color(theme['grid_color'])

    def _render_dated(self, ax: plt.Axes, theme: Dict[str, Any]) -> None:
        """
        날짜 모드 차트를 렌더링한다.
        X축은 날짜
        """
        names, start_dates, durations, min_date, max_date = self._prepare_date_data()

        # Y축 위치 (위에서 아래로)
        y_positions = list(range(len(names) - 1, -1, -1))

        # 태스크 바 그리기
        colors = theme['task_colors']
        for i, (y, start, dur, task) in enumerate(zip(y_positions, start_dates, durations, self.tasks)):
            color = colors[i % len(colors)]

            # 배경 바
            ax.barh(
                y,
                dur,
                left=start,
                height=0.6,
                color=color,
                alpha=0.8,
                edgecolor='white',
                linewidth=1
            )

            # 진행률 오버레이
            progress = task.get('progress', 0)
            if progress > 0:
                progress_width = dur * (progress / 100)
                ax.barh(
                    y,
                    progress_width,
                    left=start,
                    height=0.6,
                    color=theme['progress_color'],
                    alpha=0.9,
                    edgecolor='none'
                )

        # 마일스톤 마커
        for milestone in self.milestones:
            # 다이아몬드 마커
            ax.scatter(
                [milestone['date']],
                [len(self.tasks) - 0.3],  # 상단에 표시
                marker='D',
                s=150,
                c=theme['milestone_color'],
                zorder=5,
                edgecolors='white',
                linewidths=1.5
            )
            # 마일스톤 라벨
            ax.annotate(
                milestone['name'],
                xy=(milestone['date'], len(self.tasks) - 0.3),
                xytext=(0, 15),
                textcoords='offset points',
                ha='center',
                va='bottom',
                fontsize=9,
                color=theme['fontcolor'],
                fontweight='bold'
            )

        # 오늘 날짜 라인
        if self.show_today:
            today = datetime.now()
            if min_date <= today <= max_date + timedelta(days=7):
                ax.axvline(
                    x=today,
                    color=theme['today_color'],
                    linestyle='--',
                    linewidth=2,
                    alpha=0.7,
                    label='오늘'
                )

        # X축 설정 (날짜)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, (max_date - min_date).days // 10)))

        # 날짜 범위에 여유 추가
        margin = timedelta(days=1)
        ax.set_xlim(min_date - margin, max_date + margin)

        # Y축 설정
        ax.set_yticks(y_positions)
        ax.set_yticklabels(names)
        ax.set_ylim(-0.5, len(names) + 0.5)  # 마일스톤 공간 확보

        # 그리드
        ax.grid(True, axis='x', alpha=0.3, color=theme['grid_color'], linestyle='--')

        # 축 스타일
        ax.tick_params(colors=theme['fontcolor'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(theme['grid_color'])
        ax.spines['bottom'].set_color(theme['grid_color'])

        # X축 레이블 회전
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    def save(self, filename: str = 'gantt') -> str:
        """
        간트차트를 PNG 파일로 저장한다.

        Args:
            filename: 파일명 (확장자 제외, 타임스탬프 자동 추가)

        Returns:
            str: 저장된 파일의 전체 경로
        """
        # 렌더링
        fig = self.render()

        # 출력 경로
        output_dir = get_output_dir(self.output_dir)
        full_filename = generate_filename(filename)
        output_path = output_dir / full_filename

        # 저장
        fig.savefig(
            output_path,
            dpi=self.dpi,
            bbox_inches='tight',
            facecolor=self.theme['bgcolor'],
            edgecolor='none'
        )
        plt.close(fig)

        # 출력 정보
        print(f"[OK] 간트차트 저장 완료: {output_path}")

        # 옵시디언 삽입 코드 출력
        relative_path = f"9_Attachments/images/{datetime.now().strftime('%Y%m')}/{full_filename}"
        print(f"[INFO] 옵시디언 삽입: ![[{relative_path}]]")

        return str(output_path)

    def clear(self) -> 'GanttDrawer':
        """
        모든 태스크, 마일스톤, 그룹을 초기화한다.

        Returns:
            self (메서드 체이닝)
        """
        self.title = ''
        self.tasks = []
        self.milestones = []
        self.groups = []
        self.is_sequential = False
        return self

    def show(self) -> None:
        """
        간트차트를 화면에 표시한다.
        """
        fig = self.render()
        plt.show()


def create_gantt(
    dsl_text: str,
    theme: str = 'minimal',
    filename: str = 'gantt',
    show_today: bool = True
) -> str:
    """
    DSL 텍스트로 간트차트를 생성하는 편의 함수.

    Args:
        dsl_text: DSL 텍스트
        theme: 테마 이름
        filename: 파일명 (확장자 제외)
        show_today: 오늘 날짜 라인 표시 여부

    Returns:
        str: 저장된 파일의 전체 경로
    """
    drawer = GanttDrawer(theme=theme, show_today=show_today)
    drawer.parse_dsl_text(dsl_text)
    return drawer.save(filename)


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(
        description='간트차트 생성 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # DSL 파일로 간트차트 생성
  python -m scripts.draw_gantt input.txt -o project_schedule

  # 테마 지정
  python -m scripts.draw_gantt input.txt -t corporate -o schedule

  # 오늘 날짜 라인 숨기기
  python -m scripts.draw_gantt input.txt --no-today -o schedule
        """
    )

    parser.add_argument(
        'input',
        nargs='?',
        help='DSL 파일 경로 (없으면 stdin에서 읽음)'
    )
    parser.add_argument(
        '-o', '--output',
        default='gantt',
        help='출력 파일명 (기본: gantt)'
    )
    parser.add_argument(
        '-t', '--theme',
        default='minimal',
        choices=['minimal', 'elegant', 'clean', 'corporate', 'dark'],
        help='테마 (기본: minimal)'
    )
    parser.add_argument(
        '--no-today',
        action='store_true',
        help='오늘 날짜 라인 숨기기'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='출력 해상도 (기본: 300)'
    )

    args = parser.parse_args()

    # DSL 텍스트 읽기
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            dsl_text = f.read()
    else:
        import sys
        dsl_text = sys.stdin.read()

    # 간트차트 생성
    drawer = GanttDrawer(
        theme=args.theme,
        dpi=args.dpi,
        show_today=not args.no_today
    )
    drawer.parse_dsl_text(dsl_text)
    output_path = drawer.save(args.output)

    print(f"\n완료: {output_path}")


if __name__ == '__main__':
    main()
