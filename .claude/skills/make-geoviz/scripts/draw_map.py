# -*- coding: utf-8 -*-
"""
make-map 스킬 메인 모듈
한국 행정구역 기반 공간 데이터 시각화

지원 기능:
- choropleth: 지역별 데이터를 색상 그라데이션으로 표현
- bubble: 지역 중심에 크기가 다른 원으로 값 표현
- markers: 특정 좌표에 마커/레이블 표시
- from_kosis: KOSIS API 데이터 직접 변환
- from_markdown_table: 마크다운 테이블 파싱

사용법:
    from draw_map import MapDrawer

    drawer = MapDrawer(level='sido', theme='blues')
    drawer.set_title('시도별 인구 현황')
    drawer.choropleth({'서울': 9700000, '부산': 3400000, ...})
    drawer.save('sido_population')
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# 현재 스크립트 경로를 기준으로 모듈 import
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

from utils import (
    setup_matplotlib_korean,
    generate_filename,
    get_output_dir,
    get_theme,
    format_number,
    calculate_label_fontsize,
    COLOR_THEMES,
    BUBBLE_SIZE_RANGE,
)
from geo_utils import (
    load_geojson,
    merge_data_to_gdf,
    get_centroid,
    normalize_region_key,
    kosis_to_geojson_code,
    filter_gdf_by_sido,
    get_region_name,
)


class MapDrawer:
    """
    한국 행정구역 지도를 생성하는 클래스
    """

    def __init__(
        self,
        level: str = 'sido',
        theme: str = 'blues',
        figsize: Tuple[int, int] = (12, 10),
        dpi: int = 300,
        output_dir: str = None
    ):
        """
        MapDrawer 초기화

        Args:
            level: 행정구역 레벨 ('sido' 또는 'sigungu')
            theme: 색상 테마 (blues, reds, greens, oranges, purples, viridis, coolwarm, rdylgn)
            figsize: 지도 크기 (너비, 높이) 인치
            dpi: 해상도 (기본 300)
            output_dir: 출력 디렉토리
        """
        self.level = level
        self.theme = get_theme(theme)
        self.theme_name = theme
        self.figsize = figsize
        self.dpi = dpi
        self.output_dir = Path(output_dir) if output_dir else get_output_dir()

        # 한글 폰트 설정
        setup_matplotlib_korean()

        # GeoJSON 로드
        self.gdf = load_geojson(level)

        # 상태
        self.title = ''
        self.subtitle = ''
        self._layers: List[Dict] = []
        self._colorbar_added = False

    def set_title(self, title: str, subtitle: str = '') -> 'MapDrawer':
        """
        지도 제목 설정

        Args:
            title: 제목
            subtitle: 부제목

        Returns:
            self (메서드 체이닝)
        """
        self.title = title
        self.subtitle = subtitle
        return self

    def choropleth(
        self,
        data: Dict[str, float],
        value_label: str = '',
        show_labels: bool = True,
        label_column: str = 'name',
        show_values: bool = False,
        vmin: float = None,
        vmax: float = None,
        missing_label: str = '데이터 없음',
        fontsize: int = None
    ) -> 'MapDrawer':
        """
        Choropleth 지도 레이어 추가

        Args:
            data: {지역키: 값} 형태의 데이터
            value_label: 범례 레이블 (예: '인구(명)')
            show_labels: 지역명 표시 여부
            label_column: 레이블로 사용할 컬럼 ('name' 또는 'code')
            show_values: 지도 위에 값 표시 여부
            vmin: 최솟값 (자동 계산시 None)
            vmax: 최댓값 (자동 계산시 None)
            missing_label: 데이터 없는 지역 레이블
            fontsize: 레이블 폰트 크기 (None이면 지역 수 기반 자동 계산)

        Returns:
            self (메서드 체이닝)
        """
        self._layers.append({
            'type': 'choropleth',
            'data': data,
            'value_label': value_label,
            'show_labels': show_labels,
            'label_column': label_column,
            'show_values': show_values,
            'vmin': vmin,
            'vmax': vmax,
            'missing_label': missing_label,
            'fontsize': fontsize
        })
        return self

    def bubble(
        self,
        data: Dict[str, float],
        color: str = '#E74C3C',
        alpha: float = 0.6,
        size_range: Tuple[int, int] = BUBBLE_SIZE_RANGE,
        show_labels: bool = True,
        label_column: str = 'name',
        show_values: bool = True,
        fontsize: int = None
    ) -> 'MapDrawer':
        """
        버블 맵 레이어 추가

        Args:
            data: {지역키: 값} 형태의 데이터
            color: 버블 색상
            alpha: 투명도
            size_range: 버블 크기 범위 (min, max)
            show_labels: 지역명 표시 여부
            label_column: 레이블로 사용할 컬럼
            show_values: 버블 위에 값 표시 여부
            fontsize: 레이블 폰트 크기 (None이면 지역 수 기반 자동 계산)

        Returns:
            self (메서드 체이닝)
        """
        self._layers.append({
            'type': 'bubble',
            'data': data,
            'color': color,
            'alpha': alpha,
            'size_range': size_range,
            'show_labels': show_labels,
            'label_column': label_column,
            'show_values': show_values,
            'fontsize': fontsize
        })
        return self

    def markers(
        self,
        points: List[Dict],
        color: str = '#E74C3C',
        size: int = 100,
        marker: str = 'o',
        show_labels: bool = True,
        fontsize: int = None
    ) -> 'MapDrawer':
        """
        마커 레이어 추가

        Args:
            points: [{'x': lon, 'y': lat, 'label': '이름', 'value': 값}, ...]
            color: 마커 색상
            size: 마커 크기
            marker: 마커 모양 ('o', '^', 's', '*' 등)
            show_labels: 레이블 표시 여부
            fontsize: 레이블 폰트 크기 (None이면 마커 수 기반 자동 계산)

        Returns:
            self (메서드 체이닝)
        """
        self._layers.append({
            'type': 'markers',
            'points': points,
            'color': color,
            'size': size,
            'marker': marker,
            'show_labels': show_labels,
            'fontsize': fontsize
        })
        return self

    def from_kosis(
        self,
        kosis_data: List[Dict],
        value_column: str = 'DT',
        region_column: str = 'C1',
        region_name_column: str = 'C1_NM',
        **kwargs
    ) -> 'MapDrawer':
        """
        KOSIS API 데이터를 사용하여 Choropleth 생성

        Args:
            kosis_data: KOSIS API 응답 데이터 (List[Dict])
            value_column: 값 컬럼 (기본: 'DT')
            region_column: 지역 코드 컬럼 (기본: 'C1')
            region_name_column: 지역명 컬럼 (기본: 'C1_NM')
            **kwargs: choropleth() 메서드에 전달할 추가 인자

        Returns:
            self (메서드 체이닝)
        """
        data = {}
        for item in kosis_data:
            kosis_code = item.get(region_column, '')
            value = item.get(value_column, '')

            if kosis_code == '00':  # 전국 제외
                continue

            # KOSIS 코드를 GeoJSON 코드로 변환
            geojson_code = kosis_to_geojson_code(kosis_code)
            if geojson_code:
                try:
                    data[geojson_code] = float(value) if value else None
                except (ValueError, TypeError):
                    data[geojson_code] = None

        return self.choropleth(data, **kwargs)

    def from_markdown_table(
        self,
        table_text: str,
        region_column: int = 0,
        value_column: int = 1,
        skip_header: bool = True,
        **kwargs
    ) -> 'MapDrawer':
        """
        마크다운 테이블을 파싱하여 Choropleth 생성

        Args:
            table_text: 마크다운 테이블 텍스트
            region_column: 지역명 컬럼 인덱스 (0부터 시작)
            value_column: 값 컬럼 인덱스
            skip_header: 헤더 행 건너뛰기
            **kwargs: choropleth() 메서드에 전달할 추가 인자

        Returns:
            self (메서드 체이닝)
        """
        data = {}
        lines = table_text.strip().split('\n')

        start_idx = 0
        if skip_header:
            # 헤더와 구분선 건너뛰기
            for i, line in enumerate(lines):
                if re.match(r'^[\s|:-]+$', line):
                    start_idx = i + 1
                    break
            if start_idx == 0:
                start_idx = 1  # 구분선 없으면 첫 줄만 건너뛰기

        for line in lines[start_idx:]:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) > max(region_column, value_column):
                region = cells[region_column]
                value_str = cells[value_column]
                # 숫자 추출 (콤마, 단위 제거)
                value_str = re.sub(r'[^\d.\-]', '', value_str)
                try:
                    data[region] = float(value_str) if value_str else None
                except ValueError:
                    data[region] = None

        return self.choropleth(data, **kwargs)

    def _draw_choropleth(self, ax: plt.Axes, layer: Dict):
        """Choropleth 레이어 그리기"""
        data = layer['data']
        gdf = merge_data_to_gdf(self.gdf, data, self.level)
        gdf = get_centroid(gdf)

        # 값 범위 계산
        valid_values = gdf['value'].dropna()
        vmin = layer['vmin'] if layer['vmin'] is not None else valid_values.min()
        vmax = layer['vmax'] if layer['vmax'] is not None else valid_values.max()

        # 컬러맵
        cmap = plt.get_cmap(self.theme['cmap'])
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

        # 데이터 없는 지역 먼저 그리기
        missing_gdf = gdf[gdf['value'].isna()]
        if len(missing_gdf) > 0:
            missing_gdf.plot(
                ax=ax,
                color=self.theme['missing_color'],
                edgecolor=self.theme['edgecolor'],
                linewidth=0.5
            )

        # 데이터 있는 지역 그리기
        data_gdf = gdf[gdf['value'].notna()]
        if len(data_gdf) > 0:
            data_gdf.plot(
                ax=ax,
                column='value',
                cmap=self.theme['cmap'],
                edgecolor=self.theme['edgecolor'],
                linewidth=0.5,
                legend=False,
                vmin=vmin,
                vmax=vmax
            )

        # 컬러바
        if not self._colorbar_added and len(data_gdf) > 0:
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.02)
            if layer['value_label']:
                cbar.set_label(layer['value_label'], fontsize=10)
            self._colorbar_added = True

        # 레이블 표시
        if layer['show_labels'] or layer['show_values']:
            # 지역 수 기반 폰트 크기 자동 계산
            label_fontsize = calculate_label_fontsize(len(gdf), layer.get('fontsize'))

            for _, row in gdf.iterrows():
                x, y = row['centroid_x'], row['centroid_y']
                texts = []

                if layer['show_labels']:
                    label_col = layer['label_column']
                    if label_col == 'name':
                        # 시군구인 경우 시군구명만, 시도인 경우 축약명
                        if self.level == 'sigungu':
                            label = row.get('name', row['code'])
                        else:
                            label = get_region_name(row['code'], self.level, short=True)
                    else:
                        label = row[label_col]
                    texts.append(str(label))

                if layer['show_values'] and row['value'] is not None:
                    texts.append(format_number(row['value']))

                if texts:
                    ax.annotate(
                        '\n'.join(texts),
                        xy=(x, y),
                        ha='center',
                        va='center',
                        fontsize=label_fontsize,
                        fontweight='bold' if layer['show_labels'] else 'normal'
                    )

    def _draw_bubble(self, ax: plt.Axes, layer: Dict):
        """버블 맵 레이어 그리기"""
        data = layer['data']
        gdf = merge_data_to_gdf(self.gdf, data, self.level)
        gdf = get_centroid(gdf)

        # 데이터가 있는 지역만
        data_gdf = gdf[gdf['value'].notna()].copy()
        if len(data_gdf) == 0:
            return

        # 버블 크기 계산
        min_size, max_size = layer['size_range']
        values = data_gdf['value'].values
        vmin, vmax = values.min(), values.max()

        if vmax > vmin:
            sizes = ((values - vmin) / (vmax - vmin)) * (max_size - min_size) + min_size
        else:
            sizes = np.full_like(values, (min_size + max_size) / 2)

        # 버블 그리기
        ax.scatter(
            data_gdf['centroid_x'],
            data_gdf['centroid_y'],
            s=sizes,
            c=layer['color'],
            alpha=layer['alpha'],
            edgecolors='white',
            linewidth=1,
            zorder=3
        )

        # 레이블/값 표시
        if layer['show_labels'] or layer['show_values']:
            # 지역 수 기반 폰트 크기 자동 계산
            label_fontsize = calculate_label_fontsize(len(data_gdf), layer.get('fontsize'))

            for _, row in data_gdf.iterrows():
                x, y = row['centroid_x'], row['centroid_y']
                texts = []

                if layer['show_labels']:
                    label_col = layer['label_column']
                    if label_col == 'name':
                        if self.level == 'sigungu':
                            label = row.get('name', row['code'])
                        else:
                            label = get_region_name(row['code'], self.level, short=True)
                    else:
                        label = row[label_col]
                    texts.append(str(label))

                if layer['show_values']:
                    texts.append(format_number(row['value']))

                if texts:
                    ax.annotate(
                        '\n'.join(texts),
                        xy=(x, y),
                        ha='center',
                        va='center',
                        fontsize=label_fontsize,
                        fontweight='bold',
                        color='white' if layer['alpha'] > 0.5 else 'black'
                    )

    def _draw_markers(self, ax: plt.Axes, layer: Dict):
        """마커 레이어 그리기"""
        points = layer['points']
        if not points:
            return

        # 마커 수 기반 폰트 크기 자동 계산
        label_fontsize = calculate_label_fontsize(len(points), layer.get('fontsize'))

        for pt in points:
            ax.scatter(
                pt['x'], pt['y'],
                s=layer['size'],
                c=layer['color'],
                marker=layer['marker'],
                edgecolors='white',
                linewidth=1,
                zorder=4
            )

            if layer['show_labels'] and 'label' in pt:
                label_text = pt['label']
                if 'value' in pt and pt['value'] is not None:
                    label_text += f"\n{format_number(pt['value'])}"

                ax.annotate(
                    label_text,
                    xy=(pt['x'], pt['y']),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=label_fontsize,
                    ha='left',
                    va='bottom'
                )

    def _create_figure(self) -> Tuple[plt.Figure, plt.Axes]:
        """Figure와 Axes 생성"""
        fig, ax = plt.subplots(figsize=self.figsize)
        ax.set_aspect('equal')
        ax.axis('off')
        return fig, ax

    def save(self, filename: str, tight: bool = True) -> str:
        """
        지도를 PNG 파일로 저장

        Args:
            filename: 파일명 (접두사)
            tight: tight_layout 적용 여부

        Returns:
            str: 저장된 파일의 전체 경로
        """
        fig, ax = self._create_figure()

        # 기본 배경 지도 그리기 (레이어가 없을 때)
        if not self._layers:
            self.gdf.plot(
                ax=ax,
                color='#f0f0f0',
                edgecolor=self.theme['edgecolor'],
                linewidth=0.5
            )
        else:
            # choropleth가 아닌 경우 기본 배경 먼저 그리기
            has_choropleth = any(l['type'] == 'choropleth' for l in self._layers)
            if not has_choropleth:
                self.gdf.plot(
                    ax=ax,
                    color='#f0f0f0',
                    edgecolor=self.theme['edgecolor'],
                    linewidth=0.5
                )

        # 레이어 그리기
        for layer in self._layers:
            if layer['type'] == 'choropleth':
                self._draw_choropleth(ax, layer)
            elif layer['type'] == 'bubble':
                self._draw_bubble(ax, layer)
            elif layer['type'] == 'markers':
                self._draw_markers(ax, layer)

        # 제목
        if self.title:
            pad = 35 if self.subtitle else 20
            ax.set_title(self.title, fontsize=16, fontweight='bold', pad=pad)
        if self.subtitle:
            ax.text(
                0.5, 1.02, self.subtitle,
                transform=ax.transAxes,
                ha='center',
                fontsize=11,
                color='#666666'
            )

        if tight:
            fig.tight_layout()

        # 파일 저장 (geo_ 접두사 중복 방지)
        prefix = filename if filename.startswith('geo_') else f"geo_{filename}"
        full_filename = generate_filename(prefix, 'png')
        output_path = self.output_dir / full_filename

        fig.savefig(
            output_path,
            dpi=self.dpi,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none'
        )

        plt.close(fig)

        print(f"[OK] 지도 저장 완료: {output_path}")
        return str(output_path)

    def filter_sido(self, sido_codes: List[str]) -> 'MapDrawer':
        """
        특정 시도만 표시

        Args:
            sido_codes: 시도 코드 또는 이름 목록

        Returns:
            self (메서드 체이닝)
        """
        self.gdf = filter_gdf_by_sido(self.gdf, sido_codes)
        return self


def main():
    """테스트용 메인 함수"""
    print("=== MapDrawer 테스트 ===\n")

    # 1. 시도별 Choropleth 테스트
    print("1. 시도별 Choropleth 테스트")
    drawer = MapDrawer(level='sido', theme='blues')
    drawer.set_title('시도별 인구 현황', '(2024년 기준, 단위: 만명)')
    drawer.choropleth(
        {
            '서울': 970,
            '부산': 340,
            '대구': 240,
            '인천': 300,
            '광주': 145,
            '대전': 150,
            '울산': 115,
            '세종': 35,
            '경기': 1350,
            '강원': 155,
            '충북': 160,
            '충남': 215,
            '전북': 180,
            '전남': 185,
            '경북': 265,
            '경남': 335,
            '제주': 68
        },
        value_label='인구(만명)',
        show_labels=True,
        show_values=True
    )
    drawer.save('sido_population_test')

    # 2. 버블 맵 테스트
    print("\n2. 시도별 버블 맵 테스트")
    drawer2 = MapDrawer(level='sido', theme='greens')
    drawer2.set_title('시도별 GRDP')
    drawer2.bubble(
        {
            '서울': 450,
            '부산': 95,
            '경기': 520,
            '인천': 95
        },
        color='#E74C3C',
        show_labels=True,
        show_values=True
    )
    drawer2.save('sido_bubble_test')

    # 3. 마크다운 테이블 파싱 테스트
    print("\n3. 마크다운 테이블 파싱 테스트")
    table = """
| 지역 | 값 |
|------|-----|
| 서울 | 100 |
| 부산 | 80 |
| 대구 | 60 |
| 인천 | 70 |
| 경기 | 120 |
"""
    drawer3 = MapDrawer(level='sido', theme='oranges')
    drawer3.set_title('마크다운 테이블 테스트')
    drawer3.from_markdown_table(table, value_label='값')
    drawer3.save('markdown_test')

    print("\n=== 모든 테스트 완료 ===")


if __name__ == '__main__':
    main()
