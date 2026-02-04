# -*- coding: utf-8 -*-
"""
make-excalidraw 스킬 패키지
마크다운 문서를 파싱하여 Excalidraw 다이어그램을 생성한다.
"""

from .utils import (
    generate_id,
    generate_seed,
    generate_filename,
    get_output_dir,
    get_vault_root,
    get_theme,
    list_themes,
    get_node_style,
    calculate_text_dimensions,
    THEMES,
    NODE_STYLES
)

from .excalidraw_builder import (
    ExcalidrawBuilder,
    create_mindmap,
    create_flowchart
)

from .parsers import (
    MarkdownNode,
    parse_markdown,
    parse_dsl,
    parse_file
)

from .layouts import (
    layout_mindmap,
    layout_flowchart,
    layout_concept,
    layout_tree,
    auto_layout
)

__version__ = '1.0.0'
__author__ = 'Claude Code'

__all__ = [
    # Builder
    'ExcalidrawBuilder',
    'create_mindmap',
    'create_flowchart',

    # Parsers
    'MarkdownNode',
    'parse_markdown',
    'parse_dsl',
    'parse_file',

    # Layouts
    'layout_mindmap',
    'layout_flowchart',
    'layout_concept',
    'layout_tree',
    'auto_layout',

    # Utils
    'generate_id',
    'generate_seed',
    'generate_filename',
    'get_output_dir',
    'get_vault_root',
    'get_theme',
    'list_themes',
    'get_node_style',
    'calculate_text_dimensions',
    'THEMES',
    'NODE_STYLES',
]


# 편의 함수: 마크다운 파일 → Excalidraw 변환
def from_markdown(
    file_path: str = None,
    content: str = None,
    layout_type: str = 'auto',
    theme: str = 'minimal',
    filename: str = None
) -> str:
    """
    마크다운 파일 또는 문자열을 Excalidraw 다이어그램으로 변환한다.

    Args:
        file_path: 마크다운 파일 경로 (content와 둘 중 하나 필수)
        content: 마크다운 문자열 (file_path와 둘 중 하나 필수)
        layout_type: 레이아웃 유형 (auto, mindmap, flowchart, concept, tree)
        theme: 테마 이름 (minimal, elegant, clean, corporate, dark)
        filename: 출력 파일명 (확장자 제외)

    Returns:
        str: 저장된 Excalidraw 파일 경로

    Example:
        >>> from scripts import from_markdown
        >>> path = from_markdown('my_note.md', layout_type='mindmap', theme='clean')
        >>> print(f"![[{path}]]")
    """
    if file_path:
        parsed = parse_file(file_path)
    elif content:
        parsed = parse_markdown(content)
    else:
        raise ValueError("file_path 또는 content 중 하나는 필수입니다.")

    builder = ExcalidrawBuilder(theme=theme)
    auto_layout(builder, parsed, layout_type=layout_type)

    # 파일명 결정
    if not filename:
        if file_path:
            from pathlib import Path
            filename = Path(file_path).stem
        else:
            filename = parsed.get('title', 'diagram')

    return builder.save(filename)


def from_dsl(
    dsl_text: str,
    theme: str = None,
    filename: str = None
) -> str:
    """
    DSL 텍스트를 Excalidraw 다이어그램으로 변환한다.

    Args:
        dsl_text: DSL 형식 문자열
        theme: 테마 이름 (DSL에서 지정하지 않은 경우 사용)
        filename: 출력 파일명 (확장자 제외)

    Returns:
        str: 저장된 Excalidraw 파일 경로

    Example:
        >>> from scripts import from_dsl
        >>> dsl = '''
        ... type: mindmap
        ... theme: clean
        ... center: 메인 주제
        ...
        ... - 가지 1
        ...   - 세부 1
        ... - 가지 2
        ... '''
        >>> path = from_dsl(dsl, filename='my_mindmap')
    """
    parsed = parse_dsl(dsl_text)

    # 테마 결정 (DSL > 인자 > 기본값)
    used_theme = parsed.get('theme', theme) or 'minimal'

    builder = ExcalidrawBuilder(theme=used_theme)
    layout_type = parsed.get('type', 'mindmap')
    auto_layout(builder, parsed, layout_type=layout_type)

    return builder.save(filename)
