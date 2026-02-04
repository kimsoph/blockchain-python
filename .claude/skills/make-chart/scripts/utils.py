# -*- coding: utf-8 -*-
"""
make-chart 스킬 유틸리티 모듈
한글 폰트 설정, 파일명 생성, 경로 관리 등
"""

import os
import platform
from datetime import datetime
from pathlib import Path


def get_korean_font():
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


def setup_matplotlib_korean():
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
        # Windows 폰트 경로
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
    plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

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
        str: 생성된 파일명 (예: 'chart_20251231_143025.png')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에서 특수문자 제거
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))
    return f"{safe_prefix}_{timestamp}.{extension}"


def get_output_dir(base_path: str = None) -> Path:
    """
    차트 출력 디렉토리 경로를 반환한다.
    디렉토리가 없으면 생성한다.
    년월(YYYYMM) 서브폴더에 자동 저장된다.

    Args:
        base_path: 기본 경로 (기본: 현재 스크립트 기준 볼트 루트)

    Returns:
        Path: 출력 디렉토리 경로 (예: .../images/202601/)
    """
    # 현재 년월 (YYYYMM)
    current_ym = datetime.now().strftime('%Y%m')

    if base_path:
        output_dir = Path(base_path) / '9_Attachments' / 'images' / current_ym
    else:
        # 스크립트 위치 기준으로 볼트 루트 찾기
        current = Path(__file__).resolve()
        # .claude/skills/make-chart/scripts/ 에서 4단계 위로
        vault_root = current.parents[4]
        output_dir = vault_root / '9_Attachments' / 'images' / current_ym

    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def ensure_output_dir(output_path: str) -> Path:
    """
    출력 경로의 디렉토리가 존재하는지 확인하고, 없으면 생성한다.

    Args:
        output_path: 출력 파일 경로

    Returns:
        Path: 출력 디렉토리 경로
    """
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# 기본 색상 팔레트
DEFAULT_COLORS = [
    '#4472C4',  # 파랑
    '#ED7D31',  # 주황
    '#A5A5A5',  # 회색
    '#FFC000',  # 노랑
    '#5B9BD5',  # 하늘
    '#70AD47',  # 초록
    '#9E480E',  # 갈색
    '#997300',  # 올리브
]


def get_color(index: int) -> str:
    """
    인덱스에 해당하는 색상을 반환한다.

    Args:
        index: 색상 인덱스 (0부터 시작)

    Returns:
        str: 색상 코드 (HEX)
    """
    return DEFAULT_COLORS[index % len(DEFAULT_COLORS)]


def format_number(value: float, precision: int = 1) -> str:
    """
    숫자를 보기 좋게 포맷팅한다.

    Args:
        value: 포맷팅할 숫자
        precision: 소수점 자릿수

    Returns:
        str: 포맷팅된 문자열
    """
    if abs(value) >= 1e9:
        return f"{value/1e9:.{precision}f}B"
    elif abs(value) >= 1e6:
        return f"{value/1e6:.{precision}f}M"
    elif abs(value) >= 1e4:
        return f"{value/1e4:.{precision}f}만"
    elif abs(value) >= 1e3:
        return f"{value/1e3:.{precision}f}천"
    else:
        return f"{value:.{precision}f}"


if __name__ == '__main__':
    # 테스트
    print(f"한글 폰트: {get_korean_font()}")
    print(f"파일명 예시: {generate_filename('test_chart')}")
    print(f"출력 디렉토리: {get_output_dir()}")
    print(f"색상 0: {get_color(0)}")
    print(f"숫자 포맷: {format_number(12345678)}")
