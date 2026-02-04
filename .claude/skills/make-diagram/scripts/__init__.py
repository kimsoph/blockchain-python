# -*- coding: utf-8 -*-
"""
make-diagram 스킬 패키지

Graphviz 기반 다이어그램 생성 스킬.
블록 다이어그램, 조직도, 계층 구조, 관계도를 생성할 수 있다.
"""

from .draw_diagram import (
    DiagramDrawer,
    create_block_diagram,
    create_org_chart,
    create_hierarchy_diagram,
    create_from_dsl,
)
from .utils import (
    parse_diagram_dsl,
    get_theme,
    list_themes,
    get_korean_font,
    generate_filename,
    get_output_dir,
)

__all__ = [
    # 메인 클래스
    'DiagramDrawer',
    # 편의 함수
    'create_block_diagram',
    'create_org_chart',
    'create_hierarchy_diagram',
    'create_from_dsl',
    # 유틸리티
    'parse_diagram_dsl',
    'get_theme',
    'list_themes',
    'get_korean_font',
    'generate_filename',
    'get_output_dir',
]

__version__ = '1.0.0'
