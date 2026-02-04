# -*- coding: utf-8 -*-
"""
make-geoviz 스킬 유틸리티 모듈
한글 폰트 설정, 파일명 생성, 경로 관리, 색상 테마 등
"""

import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_korean_font() -> str:
    """
    운영체제에 따라 적합한 한글 폰트를 반환한다.

    Returns:
        str: 폰트 이름
    """
    system = platform.system()

    if system == 'Windows':
        return 'Malgun Gothic'
    elif system == 'Darwin':  # macOS
        return 'AppleGothic'
    else:  # Linux
        return 'NanumGothic'


def setup_matplotlib_korean() -> bool:
    """
    matplotlib에서 한글을 사용할 수 있도록 설정한다.

    Returns:
        bool: 설정 성공 여부
    """
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    font_name = get_korean_font()

    # 시스템 폰트 중 한글 폰트 검색
    system = platform.system()
    font_found = False

    if system == 'Windows':
        font_paths = [
            'C:/Windows/Fonts/malgun.ttf',
            'C:/Windows/Fonts/malgunbd.ttf',
            'C:/Windows/Fonts/NanumGothic.ttf',
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                font_found = True
                break

    # matplotlib 설정
    plt.rcParams['font.family'] = font_name
    plt.rcParams['axes.unicode_minus'] = False

    # 폰트 캐시 확인
    try:
        font_list = [f.name for f in fm.fontManager.ttflist]
        if font_name in font_list or any(font_name.lower() in f.lower() for f in font_list):
            font_found = True
    except Exception:
        pass

    if not font_found:
        print(f"[경고] '{font_name}' 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
        return False

    return True


def generate_filename(prefix: str, extension: str = 'png') -> str:
    """
    타임스탬프가 포함된 파일명을 생성한다.

    Args:
        prefix: 파일명 접두사
        extension: 파일 확장자 (기본: 'png')

    Returns:
        str: 생성된 파일명 (예: 'geo_sido_20260122_143025.png')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))
    return f"{safe_prefix}_{timestamp}.{extension}"


def get_output_dir(base_path: str = None) -> Path:
    """
    지도 출력 디렉토리 경로를 반환한다.
    디렉토리가 없으면 생성한다.
    년월(YYYYMM) 서브폴더에 자동 저장된다.

    Args:
        base_path: 기본 경로 (기본: 현재 스크립트 기준 볼트 루트)

    Returns:
        Path: 출력 디렉토리 경로 (예: .../images/202601/)
    """
    current_ym = datetime.now().strftime('%Y%m')

    if base_path:
        output_dir = Path(base_path) / '9_Attachments' / 'images' / current_ym
    else:
        current = Path(__file__).resolve()
        # .claude/skills/make-geoviz/scripts/ 에서 4단계 위로
        vault_root = current.parents[4]
        output_dir = vault_root / '9_Attachments' / 'images' / current_ym

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_data_dir() -> Path:
    """
    스킬 데이터 디렉토리 경로를 반환한다.

    Returns:
        Path: 데이터 디렉토리 경로
    """
    current = Path(__file__).resolve()
    return current.parents[1] / 'data'


# 색상 테마 정의
COLOR_THEMES: Dict[str, Dict] = {
    'blues': {
        'cmap': 'Blues',
        'edgecolor': '#333333',
        'missing_color': '#f0f0f0',
        'description': '파란색 계열 (기본)'
    },
    'reds': {
        'cmap': 'Reds',
        'edgecolor': '#333333',
        'missing_color': '#f0f0f0',
        'description': '빨간색 계열'
    },
    'greens': {
        'cmap': 'Greens',
        'edgecolor': '#333333',
        'missing_color': '#f0f0f0',
        'description': '초록색 계열'
    },
    'oranges': {
        'cmap': 'Oranges',
        'edgecolor': '#333333',
        'missing_color': '#f0f0f0',
        'description': '주황색 계열'
    },
    'purples': {
        'cmap': 'Purples',
        'edgecolor': '#333333',
        'missing_color': '#f0f0f0',
        'description': '보라색 계열'
    },
    'viridis': {
        'cmap': 'viridis',
        'edgecolor': '#333333',
        'missing_color': '#f0f0f0',
        'description': '다색 (저-고)'
    },
    'coolwarm': {
        'cmap': 'coolwarm',
        'edgecolor': '#333333',
        'missing_color': '#f0f0f0',
        'description': '파랑-빨강 (양극)'
    },
    'rdylgn': {
        'cmap': 'RdYlGn',
        'edgecolor': '#333333',
        'missing_color': '#f0f0f0',
        'description': '빨강-노랑-초록'
    }
}


def get_theme(theme_name: str) -> Dict:
    """
    테마 설정을 반환한다.

    Args:
        theme_name: 테마 이름

    Returns:
        Dict: 테마 설정
    """
    return COLOR_THEMES.get(theme_name, COLOR_THEMES['blues'])


def format_number(value: float, precision: int = 1) -> str:
    """
    숫자를 보기 좋게 포맷팅한다.

    Args:
        value: 포맷팅할 숫자
        precision: 소수점 자릿수

    Returns:
        str: 포맷팅된 문자열
    """
    if value is None:
        return '-'
    # NaN 체크
    try:
        if value != value:  # NaN check
            return '-'
    except (TypeError, ValueError):
        return '-'
    if abs(value) >= 1e9:
        return f"{value/1e9:.{precision}f}B"
    elif abs(value) >= 1e6:
        return f"{value/1e6:.{precision}f}M"
    elif abs(value) >= 1e4:
        return f"{value/1e4:.{precision}f}만"
    elif abs(value) >= 1e3:
        return f"{value/1e3:.{precision}f}천"
    else:
        if value == int(value):
            return str(int(value))
        return f"{value:.{precision}f}"


def calculate_label_fontsize(
    region_count: int,
    user_fontsize: Optional[int] = None,
    min_fontsize: int = 5,
    max_fontsize: int = 12
) -> int:
    """
    지역 수에 따라 적절한 레이블 폰트 크기를 계산한다.

    사용자가 명시적으로 폰트 크기를 지정한 경우 해당 값을 반환하고,
    그렇지 않으면 지역 수 기반으로 자동 계산한다.

    Args:
        region_count: 표시할 지역 수
        user_fontsize: 사용자 지정 폰트 크기 (None이면 자동 계산)
        min_fontsize: 최소 폰트 크기 (기본: 5)
        max_fontsize: 최대 폰트 크기 (기본: 12)

    Returns:
        int: 계산된 폰트 크기

    폰트 크기 계산 기준:
        | 지역 수 | 폰트 크기 | 대표 케이스 |
        |---------|----------|-------------|
        | 1-10    | 12       | 특정 시도 1-2개 |
        | 11-17   | 10       | 시도 전체 (17개) |
        | 18-30   | 9        | 서울 25개 구 |
        | 31-50   | 8        | 경기도 시군구 |
        | 51-100  | 7        | 수도권 전체 |
        | 101-150 | 6        | 영남+수도권 |
        | 151+    | 5        | 전국 시군구 |
    """
    # 사용자 지정 폰트 크기가 있으면 그대로 반환
    if user_fontsize is not None:
        return max(min_fontsize, min(max_fontsize, user_fontsize))

    # 지역 수 기반 자동 계산
    if region_count <= 10:
        fontsize = 12
    elif region_count <= 17:
        fontsize = 10
    elif region_count <= 30:
        fontsize = 9
    elif region_count <= 50:
        fontsize = 8
    elif region_count <= 100:
        fontsize = 7
    elif region_count <= 150:
        fontsize = 6
    else:
        fontsize = 5

    return max(min_fontsize, min(max_fontsize, fontsize))


# 버블 크기 기본 범위
BUBBLE_SIZE_RANGE: Tuple[int, int] = (50, 500)


if __name__ == '__main__':
    print(f"한글 폰트: {get_korean_font()}")
    print(f"파일명 예시: {generate_filename('geo_test')}")
    print(f"출력 디렉토리: {get_output_dir()}")
    print(f"데이터 디렉토리: {get_data_dir()}")
    print(f"사용 가능 테마: {list(COLOR_THEMES.keys())}")
