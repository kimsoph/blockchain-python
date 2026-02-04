# -*- coding: utf-8 -*-
"""
make-map 스킬 지리 데이터 유틸리티 모듈
GeoJSON 로딩, 코드 매핑, 좌표 변환 등
"""

import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np

from utils import get_data_dir


# 캐시
_GEOJSON_CACHE: Dict[str, gpd.GeoDataFrame] = {}
_REGION_CODES: Optional[Dict] = None
_SIGUNGU_NAME_TO_CODE: Optional[Dict[str, str]] = None


def load_region_codes() -> Dict:
    """
    지역 코드 매핑 데이터를 로드한다.

    Returns:
        Dict: 지역 코드 매핑 데이터
    """
    global _REGION_CODES
    if _REGION_CODES is not None:
        return _REGION_CODES

    data_dir = get_data_dir()
    codes_path = data_dir / 'region_codes.json'

    with open(codes_path, 'r', encoding='utf-8') as f:
        _REGION_CODES = json.load(f)

    return _REGION_CODES


def load_geojson(level: str = 'sido') -> gpd.GeoDataFrame:
    """
    GeoJSON 파일을 로드한다.

    Args:
        level: 행정구역 레벨 ('sido' 또는 'sigungu')

    Returns:
        GeoDataFrame: 지역 경계 데이터
    """
    if level in _GEOJSON_CACHE:
        return _GEOJSON_CACHE[level].copy()

    data_dir = get_data_dir()

    if level == 'sido':
        geojson_path = data_dir / 'korea_sido.geojson'
    elif level == 'sigungu':
        geojson_path = data_dir / 'korea_sigungu.geojson'
    else:
        raise ValueError(f"지원하지 않는 레벨: {level}. 'sido' 또는 'sigungu'를 사용하세요.")

    if not geojson_path.exists():
        raise FileNotFoundError(f"GeoJSON 파일을 찾을 수 없습니다: {geojson_path}")

    gdf = gpd.read_file(geojson_path)
    _GEOJSON_CACHE[level] = gdf

    return gdf.copy()


def get_region_name(code: str, level: str = 'sido', short: bool = False) -> str:
    """
    지역 코드에서 이름을 반환한다.

    Args:
        code: 지역 코드
        level: 행정구역 레벨
        short: 축약명 반환 여부

    Returns:
        str: 지역 이름
    """
    codes = load_region_codes()

    if level == 'sido':
        region_info = codes.get('sido', {}).get(str(code))
        if region_info:
            return region_info.get('name_short' if short else 'name', code)

    return str(code)


def _build_sigungu_name_to_code() -> Dict[str, str]:
    """
    시군구 GeoJSON에서 이름→코드 매핑을 생성한다.
    동일 이름이 여러 시도에 있는 경우 (예: 서울 강서구, 부산 강서구),
    모든 항목을 리스트로 저장한다.

    Returns:
        Dict[str, str]: {이름: 코드} 또는 {이름: [코드1, 코드2]} 매핑
    """
    global _SIGUNGU_NAME_TO_CODE
    if _SIGUNGU_NAME_TO_CODE is not None:
        return _SIGUNGU_NAME_TO_CODE

    gdf = load_geojson('sigungu')
    _SIGUNGU_NAME_TO_CODE = {}

    for _, row in gdf.iterrows():
        name = row['name']
        code = row['code']
        # 기본 이름: 중복 시 리스트로 저장
        if name in _SIGUNGU_NAME_TO_CODE:
            existing = _SIGUNGU_NAME_TO_CODE[name]
            if isinstance(existing, list):
                existing.append(code)
            else:
                _SIGUNGU_NAME_TO_CODE[name] = [existing, code]
        else:
            _SIGUNGU_NAME_TO_CODE[name] = code

        # '구', '시', '군' 제거한 이름도 추가 (예: '강남' → '11680')
        for suffix in ['구', '시', '군']:
            if name.endswith(suffix) and len(name) > 1:
                short_name = name[:-1]
                if short_name not in _SIGUNGU_NAME_TO_CODE:
                    _SIGUNGU_NAME_TO_CODE[short_name] = code

    return _SIGUNGU_NAME_TO_CODE


def name_to_code(name: str, level: str = 'sido') -> Optional[Union[str, List[str]]]:
    """
    지역 이름에서 코드를 반환한다.

    Args:
        name: 지역 이름
        level: 행정구역 레벨 ('sido' 또는 'sigungu')

    Returns:
        str 또는 List[str]: 지역 코드 (없으면 None, 중복 시 리스트)
    """
    if level == 'sido':
        codes = load_region_codes()
        return codes.get('name_to_code', {}).get(name)

    elif level == 'sigungu':
        sigungu_map = _build_sigungu_name_to_code()
        return sigungu_map.get(name)

    return None


def kosis_to_geojson_code(kosis_code: str) -> Optional[str]:
    """
    KOSIS 코드를 GeoJSON 코드로 변환한다.

    Args:
        kosis_code: KOSIS 지역 코드

    Returns:
        str: GeoJSON 지역 코드 (없으면 None)
    """
    codes = load_region_codes()
    return codes.get('kosis_to_geojson', {}).get(str(kosis_code))


def get_centroid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    각 지역의 중심점을 계산한다.
    WGS84 좌표계에서의 centroid 경고는 억제됨 (한국 지도에서는 무시 가능).

    Args:
        gdf: GeoDataFrame

    Returns:
        GeoDataFrame: 중심점이 추가된 데이터
    """
    gdf = gdf.copy()
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='.*geographic CRS.*')
        gdf['centroid'] = gdf.geometry.centroid
        gdf['centroid_x'] = gdf.centroid.x
        gdf['centroid_y'] = gdf.centroid.y
    return gdf


def normalize_region_key(key: str, level: str = 'sido') -> Union[str, List[str]]:
    """
    지역 키를 정규화한다.
    이름이면 코드로, 코드면 그대로 반환.
    동일 이름이 여러 시도에 있는 경우 리스트로 반환.

    Args:
        key: 지역 이름 또는 코드
        level: 행정구역 레벨

    Returns:
        str 또는 List[str]: 정규화된 코드 (중복 시 리스트)
    """
    # 숫자로만 이루어진 경우 코드로 간주
    if key.isdigit():
        return key

    # 이름인 경우 코드로 변환
    code = name_to_code(key, level)
    if code:
        return code

    # 변환 실패시 원본 반환
    return key


def merge_data_to_gdf(
    gdf: gpd.GeoDataFrame,
    data: Dict[str, float],
    level: str = 'sido',
    value_column: str = 'value'
) -> gpd.GeoDataFrame:
    """
    데이터를 GeoDataFrame에 병합한다.

    Args:
        gdf: GeoDataFrame
        data: {지역키: 값} 형태의 데이터
        level: 행정구역 레벨
        value_column: 값 컬럼명

    Returns:
        GeoDataFrame: 데이터가 병합된 GeoDataFrame
    """
    gdf = gdf.copy()

    # 키 정규화 (중복 이름 처리)
    normalized_data = {}
    for key, value in data.items():
        normalized_key = normalize_region_key(key, level)
        # 중복 이름인 경우 리스트의 모든 코드에 값 할당
        if isinstance(normalized_key, list):
            for code in normalized_key:
                normalized_data[code] = value
        else:
            normalized_data[normalized_key] = value

    # 데이터 병합
    gdf[value_column] = gdf['code'].map(normalized_data)

    return gdf


def filter_gdf_by_sido(gdf: gpd.GeoDataFrame, sido_codes: List[str]) -> gpd.GeoDataFrame:
    """
    특정 시도만 필터링한다.

    Args:
        gdf: GeoDataFrame
        sido_codes: 시도 코드 목록

    Returns:
        GeoDataFrame: 필터링된 데이터
    """
    # 시도 코드 정규화
    normalized_codes = [normalize_region_key(c, 'sido') for c in sido_codes]

    # 시군구 GeoDataFrame인 경우
    if 'sido_code' in gdf.columns:
        return gdf[gdf['sido_code'].isin(normalized_codes)].copy()
    # 시도 GeoDataFrame인 경우
    else:
        return gdf[gdf['code'].isin(normalized_codes)].copy()


def simplify_geometry(gdf: gpd.GeoDataFrame, tolerance: float = 0.001) -> gpd.GeoDataFrame:
    """
    지오메트리를 단순화한다 (파일 크기 감소).

    Args:
        gdf: GeoDataFrame
        tolerance: 단순화 허용치

    Returns:
        GeoDataFrame: 단순화된 데이터
    """
    gdf = gdf.copy()
    gdf['geometry'] = gdf.geometry.simplify(tolerance, preserve_topology=True)
    return gdf


def get_bounds(gdf: gpd.GeoDataFrame) -> Tuple[float, float, float, float]:
    """
    GeoDataFrame의 경계를 반환한다.

    Args:
        gdf: GeoDataFrame

    Returns:
        Tuple: (minx, miny, maxx, maxy)
    """
    return tuple(gdf.total_bounds)


def calculate_scale_range(
    values: List[float],
    min_size: float = 50,
    max_size: float = 500
) -> Tuple[float, float]:
    """
    버블 크기 스케일 범위를 계산한다.

    Args:
        values: 값 목록
        min_size: 최소 크기
        max_size: 최대 크기

    Returns:
        Tuple: (min_val, max_val)
    """
    valid_values = [v for v in values if v is not None and not np.isnan(v)]
    if not valid_values:
        return (0, 1)
    return (min(valid_values), max(valid_values))


if __name__ == '__main__':
    # 테스트
    print("=== GeoJSON 로딩 테스트 ===")
    sido_gdf = load_geojson('sido')
    print(f"시도 개수: {len(sido_gdf)}")

    sigungu_gdf = load_geojson('sigungu')
    print(f"시군구 개수: {len(sigungu_gdf)}")

    print("\n=== 코드 매핑 테스트 ===")
    print(f"서울 → 코드: {name_to_code('서울')}")
    print(f"11 → 이름: {get_region_name('11')}")
    print(f"KOSIS 21 → GeoJSON: {kosis_to_geojson_code('21')}")

    print("\n=== 데이터 병합 테스트 ===")
    test_data = {'서울': 100, '부산': 80, '대구': 60}
    merged = merge_data_to_gdf(sido_gdf, test_data, value_column='population')
    print(merged[['code', 'name', 'population']].head())
