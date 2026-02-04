# -*- coding: utf-8 -*-
"""
make-infographic 스킬 유틸리티 모듈 v3.0
한글 폰트 설정, 색상 테마, 그라데이션, 경로 관리 등

v3.0 업데이트:
- 미니멀/엘레강트 테마 추가 (minimal, elegant)
- 전체 테마 색상 세련되게 조정
- 그림자 더 부드럽게
- 차트 색상 현대적으로 업데이트

v2.0 업데이트:
- 새로운 테마 추가 (ocean, forest, sunset, modern)
- 그라데이션 유틸리티 추가
- 그림자 효과 유틸리티 추가
- 색상 조작 함수 추가
"""

import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import colorsys


# ============================================================
# 한글 폰트 설정
# ============================================================

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

    # 시스템 폰트 확인
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


# ============================================================
# 색상 테마
# ============================================================

# 기본 색상 팔레트 (Corporate 스타일)
COLORS_CORPORATE = {
    'primary': '#2E86AB',      # 메인 블루
    'secondary': '#A23B72',    # 악센트 마젠타
    'success': '#28A745',      # 상승/긍정 (녹색)
    'danger': '#DC3545',       # 하락/경고 (빨강)
    'warning': '#FFC107',      # 주의 (노랑)
    'info': '#17A2B8',         # 정보 (청록)
    'dark': '#343A40',         # 텍스트/타이틀 (어두운 회색)
    'muted': '#6C757D',        # 부제목/설명 (중간 회색)
    'light': '#F8F9FA',        # 배경 (밝은 회색)
    'white': '#FFFFFF',        # 흰색
    'border': '#DEE2E6',       # 테두리
    'gradient_start': '#2E86AB',  # 그라데이션 시작
    'gradient_end': '#A23B72',    # 그라데이션 끝
    'shadow': 'rgba(0,0,0,0.1)',  # 그림자
}

# 다크 테마
COLORS_DARK = {
    'primary': '#4FC3F7',
    'secondary': '#BA68C8',
    'success': '#66BB6A',
    'danger': '#EF5350',
    'warning': '#FFCA28',
    'info': '#26C6DA',
    'dark': '#ECEFF1',         # 텍스트 (밝은 색)
    'muted': '#90A4AE',
    'light': '#1E1E1E',        # 배경 (어두운 색)
    'white': '#2D2D2D',
    'border': '#424242',
    'gradient_start': '#4FC3F7',
    'gradient_end': '#BA68C8',
    'shadow': 'rgba(0,0,0,0.3)',
}

# 라이트 테마 (부드러운 파스텔)
COLORS_LIGHT = {
    'primary': '#5C6BC0',
    'secondary': '#7E57C2',
    'success': '#81C784',
    'danger': '#E57373',
    'warning': '#FFD54F',
    'info': '#4DD0E1',
    'dark': '#37474F',
    'muted': '#78909C',
    'light': '#FAFAFA',
    'white': '#FFFFFF',
    'border': '#E0E0E0',
    'gradient_start': '#5C6BC0',
    'gradient_end': '#7E57C2',
    'shadow': 'rgba(0,0,0,0.08)',
}

# === 새로운 테마 (v2.0) ===

# Ocean 테마 - 바다 느낌의 청록색 계열
COLORS_OCEAN = {
    'primary': '#0077B6',      # 딥 블루
    'secondary': '#00B4D8',    # 스카이 블루
    'success': '#48CAE4',      # 아쿠아
    'danger': '#FF6B6B',       # 코랄 레드
    'warning': '#FFE66D',      # 샌드 옐로우
    'info': '#90E0EF',         # 라이트 아쿠아
    'dark': '#03045E',         # 네이비
    'muted': '#0096C7',        # 미디엄 블루
    'light': '#CAF0F8',        # 아이스 블루
    'white': '#FFFFFF',
    'border': '#ADE8F4',
    'gradient_start': '#0077B6',
    'gradient_end': '#00B4D8',
    'shadow': 'rgba(0,119,182,0.15)',
}

# Forest 테마 - 자연 느낌의 녹색 계열
COLORS_FOREST = {
    'primary': '#2D6A4F',      # 딥 그린
    'secondary': '#40916C',    # 포레스트 그린
    'success': '#52B788',      # 민트 그린
    'danger': '#D62828',       # 레드
    'warning': '#F4A261',      # 오렌지
    'info': '#74C69D',         # 라이트 그린
    'dark': '#1B4332',         # 다크 그린
    'muted': '#588157',        # 세이지
    'light': '#D8F3DC',        # 민트 크림
    'white': '#FFFFFF',
    'border': '#B7E4C7',
    'gradient_start': '#2D6A4F',
    'gradient_end': '#52B788',
    'shadow': 'rgba(45,106,79,0.15)',
}

# Sunset 테마 - 따뜻한 주황/분홍 계열
COLORS_SUNSET = {
    'primary': '#E76F51',      # 테라코타
    'secondary': '#F4A261',    # 샌디 오렌지
    'success': '#2A9D8F',      # 틸 그린
    'danger': '#E63946',       # 버밀리온
    'warning': '#E9C46A',      # 골든 옐로우
    'info': '#264653',         # 다크 틸
    'dark': '#6D3625',         # 다크 브라운
    'muted': '#BD8B7A',        # 더스티 로즈
    'light': '#FFF1E6',        # 피치 크림
    'white': '#FFFFFF',
    'border': '#F9DCC4',
    'gradient_start': '#E76F51',
    'gradient_end': '#F4A261',
    'shadow': 'rgba(231,111,81,0.15)',
}

# Modern 테마 - 미니멀한 모노톤 + 악센트
COLORS_MODERN = {
    'primary': '#6366F1',      # 인디고
    'secondary': '#EC4899',    # 핫 핑크
    'success': '#10B981',      # 에메랄드
    'danger': '#EF4444',       # 레드
    'warning': '#F59E0B',      # 앰버
    'info': '#3B82F6',         # 블루
    'dark': '#111827',         # 챠콜
    'muted': '#6B7280',        # 그레이
    'light': '#F9FAFB',        # 오프 화이트
    'white': '#FFFFFF',
    'border': '#E5E7EB',
    'gradient_start': '#6366F1',
    'gradient_end': '#EC4899',
    'shadow': 'rgba(99,102,241,0.15)',
}

# === v3.0 새로운 테마 ===

# Minimal 테마 - 순백색 배경, 단일 액센트 (가장 세련됨)
COLORS_MINIMAL = {
    'primary': '#1A1A2E',      # 거의 검정 (메인 텍스트/강조)
    'secondary': '#4A4E69',    # 다크 그레이 (보조)
    'success': '#2D6A4F',      # 딥 그린
    'danger': '#9B2C2C',       # 다크 레드
    'warning': '#B7791F',      # 다크 옐로우
    'info': '#2B6CB0',         # 딥 블루
    'dark': '#1A1A2E',         # 거의 검정
    'muted': '#9CA3AF',        # 라이트 그레이
    'light': '#FFFFFF',        # 순백색
    'white': '#FFFFFF',
    'border': '#F3F4F6',       # 매우 연한 테두리
    'card_bg': '#FAFBFC',      # 카드 배경 (아주 미세한 그레이)
    'gradient_start': '#1A1A2E',
    'gradient_end': '#4A4E69',
    'shadow': 'rgba(0,0,0,0.03)',  # 매우 연한 그림자
}

# Elegant 테마 - 세련된 그레이 톤 + 골드 액센트
COLORS_ELEGANT = {
    'primary': '#2D3748',      # 챠콜 그레이
    'secondary': '#B7950B',    # 골드
    'success': '#276749',      # 포레스트 그린
    'danger': '#C53030',       # 와인 레드
    'warning': '#D69E2E',      # 골든
    'info': '#2B6CB0',         # 네이비 블루
    'dark': '#1A202C',         # 다크 챠콜
    'muted': '#718096',        # 미디엄 그레이
    'light': '#F7FAFC',        # 오프 화이트
    'white': '#FFFFFF',
    'border': '#EDF2F7',       # 연한 그레이
    'card_bg': '#FFFFFF',
    'gradient_start': '#2D3748',
    'gradient_end': '#4A5568',
    'shadow': 'rgba(45,55,72,0.06)',  # 부드러운 그림자
}

# Clean 테마 - 깔끔한 블루 톤 (비즈니스용)
COLORS_CLEAN = {
    'primary': '#2563EB',      # 비비드 블루
    'secondary': '#7C3AED',    # 바이올렛
    'success': '#059669',      # 에메랄드
    'danger': '#DC2626',       # 레드
    'warning': '#D97706',      # 앰버
    'info': '#0891B2',         # 시안
    'dark': '#1E293B',         # 슬레이트
    'muted': '#64748B',        # 슬레이트 그레이
    'light': '#F8FAFC',        # 스노우
    'white': '#FFFFFF',
    'border': '#E2E8F0',       # 라이트 슬레이트
    'card_bg': '#FFFFFF',
    'gradient_start': '#2563EB',
    'gradient_end': '#7C3AED',
    'shadow': 'rgba(37,99,235,0.05)',
}

# === v4.0 새로운 테마 ===

# Vibrant 테마 - 생동감 있는 색상 팔레트 (눈에 확 띄는)
COLORS_VIBRANT = {
    'primary': '#FF6B6B',      # 코랄 레드
    'secondary': '#4ECDC4',    # 틸
    'success': '#45B7D1',      # 스카이 블루
    'danger': '#FF8E72',       # 피치
    'warning': '#F7DC6F',      # 골드
    'info': '#BB8FCE',         # 라벤더
    'dark': '#2C3E50',         # 다크 블루그레이
    'muted': '#95A5A6',        # 그레이
    'light': '#FDFEFE',        # 오프화이트
    'white': '#FFFFFF',
    'border': '#E8E8E8',
    'card_bg': '#FFFFFF',
    'gradient_start': '#FF6B6B',
    'gradient_end': '#4ECDC4',
    'shadow': 'rgba(255,107,107,0.12)',  # 컬러 그림자
    'glow': '#FF6B6B',         # 글로우 색상
}

# 차트용 시리즈 색상 (v3.0 업데이트 - 더 세련된 색상)
CHART_COLORS = [
    '#3B82F6',  # 블루
    '#8B5CF6',  # 바이올렛
    '#10B981',  # 에메랄드
    '#F59E0B',  # 앰버
    '#EF4444',  # 레드
    '#06B6D4',  # 시안
    '#EC4899',  # 핑크
    '#84CC16',  # 라임
]

# 테마별 차트 색상 팔레트 (v3.0 업데이트)
CHART_COLORS_BY_THEME = {
    'corporate': ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#06B6D4'],
    'dark': ['#60A5FA', '#A78BFA', '#34D399', '#FBBF24', '#F87171', '#22D3EE'],
    'light': ['#6366F1', '#A855F7', '#14B8A6', '#F59E0B', '#F43F5E', '#0EA5E9'],
    'ocean': ['#0284C7', '#0891B2', '#06B6D4', '#22D3EE', '#67E8F9', '#A5F3FC'],
    'forest': ['#166534', '#15803D', '#22C55E', '#4ADE80', '#86EFAC', '#BBF7D0'],
    'sunset': ['#C2410C', '#EA580C', '#F97316', '#FB923C', '#FDBA74', '#FED7AA'],
    'modern': ['#6366F1', '#8B5CF6', '#A855F7', '#D946EF', '#EC4899', '#F43F5E'],
    # v3.0 새 테마 차트 색상
    'minimal': ['#1A1A2E', '#4A4E69', '#9CA3AF', '#D1D5DB', '#E5E7EB', '#F3F4F6'],
    'elegant': ['#2D3748', '#4A5568', '#718096', '#A0AEC0', '#CBD5E0', '#E2E8F0'],
    'clean': ['#2563EB', '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE', '#DBEAFE'],
    # v4.0 vibrant 테마 차트 색상
    'vibrant': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F7DC6F', '#BB8FCE', '#82E0AA', '#F1948A', '#85C1E9'],
}


def get_theme(theme_name: str = 'minimal') -> Dict[str, str]:
    """
    테마 색상 딕셔너리를 반환한다.

    Args:
        theme_name: 테마 이름
            - v3.0 추천: 'minimal', 'elegant', 'clean'
            - 기존: 'corporate', 'dark', 'light', 'ocean', 'forest', 'sunset', 'modern'

    Returns:
        Dict[str, str]: 색상 딕셔너리
    """
    themes = {
        # v3.0 새 테마 (세련됨)
        'minimal': COLORS_MINIMAL,
        'elegant': COLORS_ELEGANT,
        'clean': COLORS_CLEAN,
        # v4.0 새 테마 (눈에 띄는)
        'vibrant': COLORS_VIBRANT,
        # 기존 테마
        'corporate': COLORS_CORPORATE,
        'dark': COLORS_DARK,
        'light': COLORS_LIGHT,
        'ocean': COLORS_OCEAN,
        'forest': COLORS_FOREST,
        'sunset': COLORS_SUNSET,
        'modern': COLORS_MODERN,
    }
    return themes.get(theme_name, COLORS_MINIMAL)


def list_themes() -> List[str]:
    """사용 가능한 테마 목록을 반환한다."""
    return ['minimal', 'elegant', 'clean', 'vibrant', 'corporate', 'dark', 'light', 'ocean', 'forest', 'sunset', 'modern']


def get_chart_color(index: int, theme: str = 'corporate') -> str:
    """
    차트 시리즈용 색상을 반환한다.

    Args:
        index: 색상 인덱스 (0부터)
        theme: 테마 이름

    Returns:
        str: HEX 색상 코드
    """
    colors = CHART_COLORS_BY_THEME.get(theme, CHART_COLORS)
    return colors[index % len(colors)]


def get_chart_colors(theme: str = 'corporate') -> List[str]:
    """테마에 해당하는 차트 색상 팔레트를 반환한다."""
    return CHART_COLORS_BY_THEME.get(theme, CHART_COLORS)


# ============================================================
# 색상 조작 유틸리티 (v2.0)
# ============================================================

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """HEX 색상을 RGB 튜플로 변환한다."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """RGB 튜플을 HEX 색상으로 변환한다."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """
    색상을 밝게 만든다.

    Args:
        hex_color: HEX 색상 코드
        factor: 밝기 증가 비율 (0-1)

    Returns:
        str: 밝아진 HEX 색상
    """
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return rgb_to_hex((r, g, b))


def darken_color(hex_color: str, factor: float = 0.2) -> str:
    """
    색상을 어둡게 만든다.

    Args:
        hex_color: HEX 색상 코드
        factor: 어둡기 증가 비율 (0-1)

    Returns:
        str: 어두워진 HEX 색상
    """
    r, g, b = hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return rgb_to_hex((r, g, b))


def create_gradient_colors(start_color: str, end_color: str, steps: int = 10) -> List[str]:
    """
    두 색상 사이의 그라데이션 색상 목록을 생성한다.

    Args:
        start_color: 시작 HEX 색상
        end_color: 끝 HEX 색상
        steps: 단계 수

    Returns:
        List[str]: 그라데이션 HEX 색상 목록
    """
    start_rgb = hex_to_rgb(start_color)
    end_rgb = hex_to_rgb(end_color)

    colors = []
    for i in range(steps):
        ratio = i / (steps - 1) if steps > 1 else 0
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        colors.append(rgb_to_hex((r, g, b)))

    return colors


def get_alpha_color(hex_color: str, alpha: float = 0.5) -> Tuple[float, float, float, float]:
    """
    HEX 색상을 RGBA 튜플로 변환한다 (matplotlib 호환).

    Args:
        hex_color: HEX 색상 코드
        alpha: 투명도 (0-1)

    Returns:
        Tuple[float, float, float, float]: RGBA 값 (0-1 범위)
    """
    r, g, b = hex_to_rgb(hex_color)
    return (r/255, g/255, b/255, alpha)


# ============================================================
# 그라데이션 및 효과 (v2.0)
# ============================================================

def create_gradient_image(ax, direction: str = 'vertical',
                          start_color: str = '#FFFFFF',
                          end_color: str = '#F0F0F0') -> None:
    """
    Axes에 그라데이션 배경을 적용한다.

    Args:
        ax: matplotlib Axes 객체
        direction: 방향 ('vertical', 'horizontal', 'diagonal')
        start_color: 시작 색상
        end_color: 끝 색상
    """
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    # 그라데이션 생성
    if direction == 'vertical':
        gradient = np.linspace(0, 1, 256).reshape(-1, 1)
    elif direction == 'horizontal':
        gradient = np.linspace(0, 1, 256).reshape(1, -1)
    else:  # diagonal
        x = np.linspace(0, 1, 256)
        y = np.linspace(0, 1, 256)
        X, Y = np.meshgrid(x, y)
        gradient = (X + Y) / 2

    # 커스텀 컬러맵 생성
    start_rgb = [c/255 for c in hex_to_rgb(start_color)]
    end_rgb = [c/255 for c in hex_to_rgb(end_color)]

    cmap = LinearSegmentedColormap.from_list('custom', [start_rgb, end_rgb])

    # 배경에 적용
    ax.imshow(gradient, aspect='auto', cmap=cmap,
              extent=[0, 1, 0, 1], zorder=-1)


def add_shadow_effect(ax, rect_bounds: Tuple[float, float, float, float],
                     shadow_color: str = '#000000',
                     shadow_alpha: float = 0.1,
                     offset: Tuple[float, float] = (0.02, -0.02)) -> None:
    """
    사각형에 그림자 효과를 추가한다.

    Args:
        ax: matplotlib Axes 객체
        rect_bounds: (x, y, width, height)
        shadow_color: 그림자 색상
        shadow_alpha: 그림자 투명도
        offset: 그림자 오프셋 (x, y)
    """
    import matplotlib.patches as mpatches

    x, y, w, h = rect_bounds
    shadow_rect = mpatches.FancyBboxPatch(
        (x + offset[0], y + offset[1]), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        facecolor=shadow_color,
        alpha=shadow_alpha,
        edgecolor='none',
        zorder=0
    )
    ax.add_patch(shadow_rect)


# ============================================================
# 글로우 및 네온 효과 (v4.0)
# ============================================================

def create_glow_effect(color: str, intensity: int = 3) -> List:
    """
    텍스트/도형에 글로우 효과를 주는 PathEffects 반환.

    Args:
        color: 글로우 색상 (HEX)
        intensity: 글로우 강도 (1-5)

    Returns:
        List[PathEffect]: matplotlib patheffects 리스트
    """
    from matplotlib.patheffects import Normal, Stroke

    effects = []
    base_width = 4 * intensity

    for i in range(intensity, 0, -1):
        effects.append(
            Stroke(
                linewidth=base_width * (i / intensity),
                foreground=lighten_color(color, 0.3 + 0.1 * i),
                alpha=0.15 * i
            )
        )
    effects.append(Normal())
    return effects


def create_neon_effect(color: str) -> List:
    """
    네온 사인 스타일 효과를 반환한다.

    Args:
        color: 네온 색상 (HEX)

    Returns:
        List[PathEffect]: 네온 효과
    """
    from matplotlib.patheffects import Normal, Stroke

    return [
        Stroke(linewidth=10, foreground=lighten_color(color, 0.85), alpha=0.3),
        Stroke(linewidth=7, foreground=lighten_color(color, 0.7), alpha=0.4),
        Stroke(linewidth=5, foreground=lighten_color(color, 0.5), alpha=0.5),
        Stroke(linewidth=3, foreground=lighten_color(color, 0.3), alpha=0.7),
        Stroke(linewidth=1.5, foreground=color, alpha=1.0),
        Normal(),
    ]


def create_soft_glow(color: str) -> List:
    """
    부드러운 글로우 효과 (배지, 아이콘용).

    Args:
        color: 글로우 색상 (HEX)

    Returns:
        List[PathEffect]: 부드러운 글로우 효과
    """
    from matplotlib.patheffects import Normal, Stroke

    return [
        Stroke(linewidth=6, foreground=lighten_color(color, 0.7), alpha=0.3),
        Stroke(linewidth=3, foreground=lighten_color(color, 0.5), alpha=0.5),
        Normal(),
    ]


# ============================================================
# 파일/경로 관리
# ============================================================

def generate_filename(prefix: str, extension: str = 'png') -> str:
    """
    타임스탬프가 포함된 파일명을 생성한다.

    Args:
        prefix: 파일명 접두사
        extension: 파일 확장자 (기본: 'png')

    Returns:
        str: 생성된 파일명 (예: 'infographic_20260102_143025.png')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에서 특수문자 제거
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))
    return f"{safe_prefix}_{timestamp}.{extension}"


def get_output_dir(base_path: str = None) -> Path:
    """
    인포그래픽 출력 디렉토리 경로를 반환한다.
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
        # .claude/skills/make-infographic/scripts/ 에서 4단계 위로
        vault_root = current.parents[4]
        output_dir = vault_root / '9_Attachments' / 'images' / current_ym

    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


# ============================================================
# 숫자 포맷팅
# ============================================================

def format_number(value: float, precision: int = 1,
                   use_korean: bool = True) -> str:
    """
    숫자를 보기 좋게 포맷팅한다.

    Args:
        value: 포맷팅할 숫자
        precision: 소수점 자릿수
        use_korean: 한글 단위 사용 여부

    Returns:
        str: 포맷팅된 문자열
    """
    if use_korean:
        if abs(value) >= 1e12:
            return f"{value/1e12:.{precision}f}조"
        elif abs(value) >= 1e8:
            return f"{value/1e8:.{precision}f}억"
        elif abs(value) >= 1e4:
            return f"{value/1e4:.{precision}f}만"
        elif abs(value) >= 1e3:
            return f"{value/1e3:.{precision}f}천"
        else:
            return f"{value:.{precision}f}"
    else:
        if abs(value) >= 1e12:
            return f"{value/1e12:.{precision}f}T"
        elif abs(value) >= 1e9:
            return f"{value/1e9:.{precision}f}B"
        elif abs(value) >= 1e6:
            return f"{value/1e6:.{precision}f}M"
        elif abs(value) >= 1e3:
            return f"{value/1e3:.{precision}f}K"
        else:
            return f"{value:.{precision}f}"


def format_percent(value: float, precision: int = 1,
                   show_sign: bool = True) -> str:
    """
    퍼센트 형식으로 포맷팅한다.

    Args:
        value: 퍼센트 값 (예: 12.5 = 12.5%)
        precision: 소수점 자릿수
        show_sign: 양수일 때 + 기호 표시

    Returns:
        str: 포맷팅된 문자열 (예: '+12.5%', '-3.2%')
    """
    if show_sign and value > 0:
        return f"+{value:.{precision}f}%"
    else:
        return f"{value:.{precision}f}%"


# ============================================================
# 텍스트 유틸리티
# ============================================================

def wrap_text(text: str, max_width: int = 20) -> str:
    """
    텍스트를 지정된 너비로 줄바꿈한다.

    Args:
        text: 원본 텍스트
        max_width: 한 줄 최대 글자 수

    Returns:
        str: 줄바꿈된 텍스트
    """
    import textwrap
    return '\n'.join(textwrap.wrap(text, width=max_width))


# ============================================================
# 테스트
# ============================================================

if __name__ == '__main__':
    print("=== make-infographic utils v2.0 테스트 ===\n")

    print(f"한글 폰트: {get_korean_font()}")
    print(f"파일명 예시: {generate_filename('infographic')}")
    print(f"출력 디렉토리: {get_output_dir()}")

    print(f"\n사용 가능한 테마: {list_themes()}")

    print(f"\n숫자 포맷:")
    print(f"  12345 → {format_number(12345)}")
    print(f"  123456789 → {format_number(123456789)}")
    print(f"  1234567890123 → {format_number(1234567890123)}")

    print(f"\n퍼센트 포맷:")
    print(f"  12.5 → {format_percent(12.5)}")
    print(f"  -3.2 → {format_percent(-3.2)}")

    print(f"\n색상 조작:")
    print(f"  원본: #2E86AB")
    print(f"  밝게: {lighten_color('#2E86AB', 0.3)}")
    print(f"  어둡게: {darken_color('#2E86AB', 0.3)}")

    print(f"\n그라데이션 (5단계):")
    gradient = create_gradient_colors('#2E86AB', '#A23B72', 5)
    for i, c in enumerate(gradient):
        print(f"  {i}: {c}")

    print(f"\n테마 색상 (ocean):")
    theme = get_theme('ocean')
    for key, color in list(theme.items())[:5]:
        print(f"  {key}: {color}")
