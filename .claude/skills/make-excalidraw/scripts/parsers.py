# -*- coding: utf-8 -*-
"""
make-excalidraw 스킬 마크다운 파서 모듈
마크다운 문서를 파싱하여 구조화된 데이터로 변환
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class MarkdownNode:
    """마크다운에서 추출된 노드를 표현하는 클래스"""

    def __init__(
        self,
        text: str,
        level: int = 0,
        node_type: str = 'default',
        parent: Optional['MarkdownNode'] = None
    ):
        self.text = text.strip()
        self.level = level
        self.node_type = node_type
        self.parent = parent
        self.children: List['MarkdownNode'] = []
        self.links: List[str] = []  # 위키링크 [[...]]
        self.tags: List[str] = []   # 태그 #...

    def add_child(self, child: 'MarkdownNode') -> None:
        """자식 노드를 추가한다."""
        child.parent = self
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환한다."""
        return {
            'text': self.text,
            'level': self.level,
            'type': self.node_type,
            'links': self.links,
            'tags': self.tags,
            'children': [c.to_dict() for c in self.children]
        }


def parse_markdown(content: str) -> Dict[str, Any]:
    """
    마크다운을 구조화된 데이터로 변환한다.

    Args:
        content: 마크다운 문자열

    Returns:
        Dict: {
            'title': str,
            'nodes': List[Dict],  # 계층적 노드 구조
            'flat_nodes': List[Dict],  # 평탄화된 노드 리스트
            'links': List[Tuple[str, str]],  # (from_text, to_text) 링크 관계
            'metadata': Dict  # YAML 프론트매터
        }
    """
    result = {
        'title': '',
        'nodes': [],
        'flat_nodes': [],
        'links': [],
        'metadata': {}
    }

    lines = content.split('\n')

    # YAML 프론트매터 파싱
    metadata, start_line = _parse_frontmatter(lines)
    result['metadata'] = metadata

    # 제목 추출 (첫 번째 H1)
    title = metadata.get('title', '')
    if not title:
        for line in lines[start_line:]:
            if line.startswith('# '):
                title = line[2:].strip()
                break
    result['title'] = title

    # 헤딩과 리스트 파싱
    root_nodes, flat_nodes = _parse_structure(lines[start_line:])
    result['nodes'] = [n.to_dict() for n in root_nodes]
    result['flat_nodes'] = flat_nodes

    # 링크 관계 추출
    result['links'] = _extract_links(flat_nodes)

    return result


def _parse_frontmatter(lines: List[str]) -> Tuple[Dict[str, Any], int]:
    """
    YAML 프론트매터를 파싱한다.

    Args:
        lines: 마크다운 라인 리스트

    Returns:
        Tuple[Dict, int]: (메타데이터 딕셔너리, 본문 시작 라인 인덱스)
    """
    metadata = {}
    start_line = 0

    if lines and lines[0].strip() == '---':
        end_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                end_idx = i
                break

        if end_idx > 0:
            # 간단한 YAML 파싱 (key: value 형식만)
            for line in lines[1:end_idx]:
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    metadata[key] = value
            start_line = end_idx + 1

    return metadata, start_line


def _parse_structure(lines: List[str]) -> Tuple[List[MarkdownNode], List[Dict]]:
    """
    헤딩과 리스트 구조를 파싱한다.

    Args:
        lines: 마크다운 라인 리스트

    Returns:
        Tuple[List[MarkdownNode], List[Dict]]: (루트 노드 리스트, 평탄화된 노드 리스트)
    """
    root_nodes: List[MarkdownNode] = []
    flat_nodes: List[Dict] = []

    # 현재 헤딩 스택 (level -> node)
    heading_stack: Dict[int, MarkdownNode] = {}

    # 현재 리스트 컨텍스트
    current_list_parent: Optional[MarkdownNode] = None
    list_indent_stack: List[Tuple[int, MarkdownNode]] = []  # (indent, node)

    for line in lines:
        stripped = line.rstrip()

        # 빈 줄은 건너뜀
        if not stripped:
            continue

        # 헤딩 파싱 (# ~ ######)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()

            node = MarkdownNode(text, level=level, node_type='heading')
            _extract_inline_elements(node)

            # 부모 찾기 (더 낮은 레벨의 가장 가까운 헤딩)
            parent = None
            for i in range(level - 1, 0, -1):
                if i in heading_stack:
                    parent = heading_stack[i]
                    break

            if parent:
                parent.add_child(node)
            else:
                root_nodes.append(node)

            heading_stack[level] = node
            # 더 깊은 레벨은 제거
            for i in list(heading_stack.keys()):
                if i > level:
                    del heading_stack[i]

            current_list_parent = node
            list_indent_stack = []

            flat_nodes.append({
                'text': text,
                'level': level,
                'type': 'heading',
                'links': node.links,
                'tags': node.tags
            })
            continue

        # 리스트 아이템 파싱 (-, *, 1.)
        list_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.+)$', stripped)
        if list_match:
            indent = len(list_match.group(1))
            marker = list_match.group(2)
            text = list_match.group(3).strip()

            list_type = 'ordered' if marker[0].isdigit() else 'unordered'

            # 리스트 레벨 계산 (들여쓰기 2칸 = 1레벨)
            list_level = indent // 2 + 1

            node = MarkdownNode(text, level=list_level, node_type=f'list_{list_type}')
            _extract_inline_elements(node)

            # 부모 찾기
            while list_indent_stack and list_indent_stack[-1][0] >= indent:
                list_indent_stack.pop()

            if list_indent_stack:
                parent = list_indent_stack[-1][1]
                parent.add_child(node)
            elif current_list_parent:
                current_list_parent.add_child(node)
            else:
                root_nodes.append(node)

            list_indent_stack.append((indent, node))

            flat_nodes.append({
                'text': text,
                'level': list_level,
                'type': f'list_{list_type}',
                'links': node.links,
                'tags': node.tags
            })
            continue

        # 일반 텍스트 (볼드, 태그 등 추출)
        if stripped and not stripped.startswith('```'):
            node = MarkdownNode(stripped, level=0, node_type='text')
            _extract_inline_elements(node)

            if node.links or node.tags:
                flat_nodes.append({
                    'text': stripped,
                    'level': 0,
                    'type': 'text',
                    'links': node.links,
                    'tags': node.tags
                })

    return root_nodes, flat_nodes


def _extract_inline_elements(node: MarkdownNode) -> None:
    """
    텍스트에서 인라인 요소를 추출한다.

    Args:
        node: MarkdownNode 객체
    """
    # 위키링크 추출 [[...]]
    wiki_links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', node.text)
    node.links = wiki_links

    # 태그 추출 #...
    tags = re.findall(r'#([a-zA-Z가-힣][a-zA-Z0-9가-힣_/-]*)', node.text)
    node.tags = tags


def _extract_links(flat_nodes: List[Dict]) -> List[Tuple[str, str]]:
    """
    노드들 간의 링크 관계를 추출한다.

    Args:
        flat_nodes: 평탄화된 노드 리스트

    Returns:
        List[Tuple[str, str]]: (from_text, to_text) 튜플 리스트
    """
    links = []

    # 텍스트에서 링크 이름 추출 (위키링크 대상)
    node_texts = set(n['text'] for n in flat_nodes)

    for node in flat_nodes:
        for link in node.get('links', []):
            # 링크 대상이 노드 목록에 있으면 관계 추가
            if link in node_texts:
                links.append((node['text'], link))
            else:
                # 없으면 그냥 링크로 추가
                links.append((node['text'], link))

    return links


def parse_dsl(content: str) -> Dict[str, Any]:
    """
    DSL 형식을 파싱한다.

    DSL 문법:
        type: mindmap|flowchart|concept
        theme: minimal|elegant|clean|corporate|dark
        direction: TB|LR|BT|RL
        center: 중심 노드 텍스트

        - 노드 텍스트
          - 하위 노드
        ---
        노드1 -> 노드2
        노드1 --> 노드2: 라벨

    Args:
        content: DSL 문자열

    Returns:
        Dict: {
            'type': str,
            'theme': str,
            'direction': str,
            'center': str,
            'nodes': List[Dict],
            'edges': List[Tuple]
        }
    """
    result = {
        'type': 'mindmap',
        'theme': 'minimal',
        'direction': 'TB',
        'center': '',
        'nodes': [],
        'edges': []
    }

    lines = content.strip().split('\n')
    in_edge_section = False

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith('#'):
            continue

        # 구분선 (엣지 섹션 시작)
        if stripped == '---':
            in_edge_section = True
            continue

        # 메타데이터 파싱
        meta_match = re.match(r'^(type|theme|direction|center):\s*(.+)$', stripped, re.IGNORECASE)
        if meta_match:
            key = meta_match.group(1).lower()
            value = meta_match.group(2).strip()
            result[key] = value
            continue

        # 엣지 섹션
        if in_edge_section:
            # 점선 + 라벨
            edge_match = re.match(r'^(.+?)\s*-->\s*(.+?):\s*(.+)$', stripped)
            if edge_match:
                result['edges'].append({
                    'from': edge_match.group(1).strip(),
                    'to': edge_match.group(2).strip(),
                    'label': edge_match.group(3).strip(),
                    'style': 'dashed'
                })
                continue

            # 점선
            edge_match = re.match(r'^(.+?)\s*-->\s*(.+)$', stripped)
            if edge_match:
                result['edges'].append({
                    'from': edge_match.group(1).strip(),
                    'to': edge_match.group(2).strip(),
                    'label': '',
                    'style': 'dashed'
                })
                continue

            # 실선 + 라벨
            edge_match = re.match(r'^(.+?)\s*->\s*(.+?):\s*(.+)$', stripped)
            if edge_match:
                result['edges'].append({
                    'from': edge_match.group(1).strip(),
                    'to': edge_match.group(2).strip(),
                    'label': edge_match.group(3).strip(),
                    'style': 'solid'
                })
                continue

            # 실선
            edge_match = re.match(r'^(.+?)\s*->\s*(.+)$', stripped)
            if edge_match:
                result['edges'].append({
                    'from': edge_match.group(1).strip(),
                    'to': edge_match.group(2).strip(),
                    'label': '',
                    'style': 'solid'
                })
                continue

        # 노드 파싱 (리스트 형식)
        else:
            list_match = re.match(r'^(\s*)([-*])\s+(.+)$', line)
            if list_match:
                indent = len(list_match.group(1))
                text = list_match.group(3).strip()
                level = indent // 2  # 2칸 들여쓰기 = 1레벨

                result['nodes'].append({
                    'text': text,
                    'level': level
                })

    return result


def parse_file(file_path: str) -> Dict[str, Any]:
    """
    마크다운 파일을 파싱한다.

    Args:
        file_path: 파일 경로

    Returns:
        Dict: 파싱된 구조 데이터
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    content = path.read_text(encoding='utf-8')
    return parse_markdown(content)


if __name__ == '__main__':
    # 테스트
    test_md = """---
title: 테스트 문서
tags: [test, sample]
---

# 메인 제목

## 첫 번째 섹션

- 항목 1
  - 하위 항목 1-1
  - 하위 항목 1-2
- 항목 2 [[링크]]
- 항목 3 #태그

## 두 번째 섹션

1. 순서 1
2. 순서 2

[[관련 문서]] 참조
"""

    result = parse_markdown(test_md)
    print(f"제목: {result['title']}")
    print(f"메타데이터: {result['metadata']}")
    print(f"노드 수: {len(result['flat_nodes'])}")
    print(f"링크: {result['links']}")
    print()

    # DSL 테스트
    test_dsl = """
type: mindmap
theme: clean
center: 중심 주제

- 가지 1
  - 세부 1-1
  - 세부 1-2
- 가지 2
  - 세부 2-1
- 가지 3
---
가지 1 -> 가지 2: 관련
가지 2 --> 가지 3
"""

    dsl_result = parse_dsl(test_dsl)
    print(f"DSL 타입: {dsl_result['type']}")
    print(f"DSL 테마: {dsl_result['theme']}")
    print(f"DSL 노드: {dsl_result['nodes']}")
    print(f"DSL 엣지: {dsl_result['edges']}")
