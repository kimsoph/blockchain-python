# -*- coding: utf-8 -*-
"""
Markdown Parser for md2db v2

마크다운 파일을 파싱하여 구조화된 데이터로 변환합니다.

v2 개선사항:
- YamlParser: PyYAML 기반 고급 YAML 파싱
- 단어/문자 수 계산
- Obsidian 특화 블록 지원 (callout, math, mermaid)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from core.models import BlockType, Block, Section, Document
from core.utils import EncodingDetector, count_words, count_chars

# PyYAML 선택적 임포트
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class YamlParser:
    """YAML 프론트매터 파서 (PyYAML 기반)

    지원 형식:
    - 단순 key: value
    - 배열: key: [item1, item2] 또는 key:\\n  - item1
    - 중첩 객체: key:\\n  subkey: value
    - 멀티라인 문자열: key: |\\n  line1\\n  line2
    - 주석: # 이후 내용 무시
    """

    def parse(self, content: str) -> Dict[str, Any]:
        """YAML 문자열을 딕셔너리로 파싱

        Args:
            content: YAML 프론트매터 내용 (--- 태그 제외)

        Returns:
            파싱된 딕셔너리
        """
        if not content or not content.strip():
            return {}

        if HAS_YAML:
            try:
                result = yaml.safe_load(content)
                return result if isinstance(result, dict) else {}
            except yaml.YAMLError:
                # 폴백: 기존 단순 파싱
                return self._fallback_simple_parse(content)
        else:
            return self._fallback_simple_parse(content)

    def _fallback_simple_parse(self, content: str) -> Dict[str, str]:
        """기존 호환성을 위한 단순 파싱 (key: value 형식만)"""
        result = {}
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip().strip('"\'')
                if key:
                    result[key] = value
        return result

    def parse_with_raw(self, content: str) -> Tuple[Dict[str, Any], str]:
        """파싱 결과와 원본 YAML 함께 반환

        Args:
            content: YAML 프론트매터 내용

        Returns:
            (파싱된 딕셔너리, 원본 YAML 문자열) 튜플
        """
        parsed = self.parse(content)
        return parsed, content


class MarkdownParser:
    """마크다운 파일을 파싱하여 구조화된 데이터로 변환"""

    def __init__(self, yaml_parser: Optional[YamlParser] = None):
        """
        Args:
            yaml_parser: YamlParser 인스턴스 (None이면 자동 생성)
        """
        self.yaml_parser = yaml_parser or YamlParser()

        # 정규식 패턴 사전 컴파일
        self.patterns = {
            'header': re.compile(r'^(#{1,6})\s+(.+)$'),
            'frontmatter_start': re.compile(r'^---\s*$'),
            'code_block_fence': re.compile(r'^(`{3,}|~{3,})(\w*)?'),
            'list_item': re.compile(r'^(\s*)([-*+]|\d+\.)\s+(.*)$'),
            'blockquote': re.compile(r'^(\s*>\s*)(.*)$'),
            'table_row': re.compile(r'^\s*\|(.+)\|\s*$'),
            'horizontal_rule': re.compile(r'^(\s*)([-*_])\s*\2\s*\2\s*$'),
            'image': re.compile(r'^!\[([^\]]*)\]\(([^)]+)\)'),
            # v2: Obsidian 특화
            'image_wikilink': re.compile(r'^!\[\[([^\]|]+)(?:\|([^\]]*))?\]\]'),  # ![[path|size]]
            'callout': re.compile(r'^>\s*\[!(\w+)\]([+-]?)(.*)$'),
            'math_block': re.compile(r'^\$\$\s*$'),
            'mermaid': re.compile(r'^```mermaid\s*$', re.IGNORECASE),
        }

    def parse_file(self, filepath: str) -> Document:
        """마크다운 파일을 파싱

        Args:
            filepath: 파일 경로

        Returns:
            Document 객체
        """
        filepath = Path(filepath)

        # 인코딩 감지 및 파일 읽기
        content, encoding = EncodingDetector.read_file(str(filepath))
        lines = content.split('\n')

        # 문서 객체 생성
        doc = Document(
            filename=filepath.name,
            file_size=filepath.stat().st_size,
            encoding=encoding
        )

        # 파싱 실행
        self._parse_content(lines, doc)

        # 총 단어 수 계산
        doc.total_words = sum(
            sum(b.word_count for b in s.blocks)
            for s in doc.sections
        )

        return doc

    def parse_content(self, content: str, filename: str = "untitled.md") -> Document:
        """문자열 내용을 직접 파싱

        Args:
            content: 마크다운 문자열
            filename: 가상 파일명

        Returns:
            Document 객체
        """
        lines = content.split('\n')

        doc = Document(
            filename=filename,
            file_size=len(content.encode('utf-8')),
            encoding='utf-8'
        )

        self._parse_content(lines, doc)

        doc.total_words = sum(
            sum(b.word_count for b in s.blocks)
            for s in doc.sections
        )

        return doc

    def _parse_content(self, lines: List[str], doc: Document) -> None:
        """라인 기반 파싱"""
        i = 0
        n = len(lines)

        # 프론트매터 처리
        if i < n and self.patterns['frontmatter_start'].match(lines[i]):
            i = self._parse_frontmatter(lines, i, doc)

        # 루트 섹션 생성 (헤더 없는 콘텐츠용)
        root_section = Section(
            level=0,
            title="(root)",
            path="0",
            position=0,
            start_line=i + 1
        )
        doc.sections.append(root_section)

        # 섹션 스택 (계층 구조 추적용)
        section_stack: List[Section] = [root_section]
        section_counters: Dict[int, int] = {0: 0}  # level -> count
        current_section = root_section

        # 블록 버퍼
        block_lines: List[Tuple[int, str]] = []
        block_start = i + 1

        while i < n:
            line = lines[i]
            line_num = i + 1  # 1-based

            # 헤더 감지
            header_match = self.patterns['header'].match(line)
            if header_match:
                # 이전 블록 저장
                if block_lines:
                    self._flush_block(block_lines, block_start, current_section)
                    block_lines = []

                # 헤더 레벨과 제목
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # 경로 계산
                section_counters[level] = section_counters.get(level, 0) + 1
                # 하위 레벨 카운터 리셋
                for l in list(section_counters.keys()):
                    if l > level:
                        section_counters[l] = 0

                path_parts = []
                for l in range(1, level + 1):
                    path_parts.append(str(section_counters.get(l, 0)))
                path = '.'.join(path_parts) if path_parts else str(section_counters[level])

                # 부모 섹션 찾기
                while section_stack and section_stack[-1].level >= level:
                    popped = section_stack.pop()
                    popped.end_line = line_num - 1
                    # has_subsections 업데이트
                    if section_stack:
                        section_stack[-1].has_subsections = True

                parent = section_stack[-1] if section_stack else None

                # 새 섹션 생성
                new_section = Section(
                    level=level,
                    title=title,
                    path=path,
                    position=len(doc.sections),
                    start_line=line_num,
                    parent_id=doc.sections.index(parent) if parent else None
                )
                doc.sections.append(new_section)
                section_stack.append(new_section)
                current_section = new_section

                # 헤더 블록 추가
                header_block = Block(
                    type=BlockType.HEADER,
                    content=title,
                    raw_markdown=line,
                    start_line=line_num,
                    end_line=line_num,
                    metadata={'level': level},
                    word_count=count_words(title),
                    char_count=count_chars(title)
                )
                current_section.blocks.append(header_block)

                block_start = line_num + 1
                i += 1
                continue

            # 코드 블록 감지
            code_match = self.patterns['code_block_fence'].match(line)
            if code_match:
                # 이전 블록 저장
                if block_lines:
                    self._flush_block(block_lines, block_start, current_section)
                    block_lines = []

                fence = code_match.group(1)
                lang = code_match.group(2) or ''
                code_lines = [line]
                code_start = line_num
                i += 1

                # 닫는 펜스 찾기
                while i < n:
                    code_lines.append(lines[i])
                    if lines[i].strip().startswith(fence[0] * len(fence)):
                        break
                    i += 1

                code_content = '\n'.join(code_lines[1:-1]) if len(code_lines) > 2 else ''
                raw_md = '\n'.join(code_lines)

                # Mermaid 다이어그램 특별 처리
                block_type = BlockType.MERMAID if lang.lower() == 'mermaid' else BlockType.CODE_BLOCK

                code_block = Block(
                    type=block_type,
                    content=code_content,
                    raw_markdown=raw_md,
                    start_line=code_start,
                    end_line=i + 1,
                    metadata={'language': lang, 'fence': fence},
                    word_count=count_words(code_content),
                    char_count=count_chars(code_content)
                )
                current_section.blocks.append(code_block)

                block_start = i + 2
                i += 1
                continue

            # 수학 블록 감지 ($$...$$)
            if self.patterns['math_block'].match(line):
                if block_lines:
                    self._flush_block(block_lines, block_start, current_section)
                    block_lines = []

                math_lines = [line]
                math_start = line_num
                i += 1

                while i < n:
                    math_lines.append(lines[i])
                    if self.patterns['math_block'].match(lines[i]):
                        break
                    i += 1

                math_content = '\n'.join(math_lines[1:-1]) if len(math_lines) > 2 else ''
                raw_md = '\n'.join(math_lines)

                math_block = Block(
                    type=BlockType.MATH_BLOCK,
                    content=math_content,
                    raw_markdown=raw_md,
                    start_line=math_start,
                    end_line=i + 1,
                    metadata={'format': 'latex'},
                    word_count=0,
                    char_count=count_chars(math_content)
                )
                current_section.blocks.append(math_block)

                block_start = i + 2
                i += 1
                continue

            # 테이블 감지
            if self.patterns['table_row'].match(line):
                # 이전 블록 저장
                if block_lines:
                    self._flush_block(block_lines, block_start, current_section)
                    block_lines = []

                table_lines = [line]
                table_start = line_num
                i += 1

                # 테이블 행 수집
                while i < n and (self.patterns['table_row'].match(lines[i]) or
                                 re.match(r'^\s*\|[-:|\s]+\|\s*$', lines[i])):
                    table_lines.append(lines[i])
                    i += 1

                table_content = self._extract_table_content(table_lines)
                raw_md = '\n'.join(table_lines)

                # 테이블 메타데이터
                row_count = len([l for l in table_lines if not re.match(r'^\s*\|[-:|\s]+\|\s*$', l)])
                col_count = len(table_lines[0].strip('|').split('|')) if table_lines else 0

                table_block = Block(
                    type=BlockType.TABLE,
                    content=table_content,
                    raw_markdown=raw_md,
                    start_line=table_start,
                    end_line=i,
                    metadata={
                        'row_count': row_count,
                        'col_count': col_count,
                        'has_header': len(table_lines) > 1
                    },
                    word_count=count_words(table_content),
                    char_count=count_chars(table_content)
                )
                current_section.blocks.append(table_block)

                block_start = i + 1
                continue

            # Callout 감지 (Obsidian 특화)
            callout_match = self.patterns['callout'].match(line)
            if callout_match:
                if block_lines:
                    self._flush_block(block_lines, block_start, current_section)
                    block_lines = []

                callout_type = callout_match.group(1)
                collapsible = callout_match.group(2)
                callout_title = callout_match.group(3).strip()

                callout_lines = [line]
                callout_start = line_num
                i += 1

                # callout 내용 수집 (> 로 시작하는 라인들)
                while i < n and lines[i].startswith('>'):
                    callout_lines.append(lines[i])
                    i += 1

                callout_content = '\n'.join(
                    l.lstrip('>').strip() for l in callout_lines[1:]
                )
                raw_md = '\n'.join(callout_lines)

                callout_block = Block(
                    type=BlockType.CALLOUT,
                    content=callout_content,
                    raw_markdown=raw_md,
                    start_line=callout_start,
                    end_line=i,
                    metadata={
                        'type': callout_type,
                        'title': callout_title,
                        'collapsible': collapsible == '+' or collapsible == '-',
                        'collapsed': collapsible == '-'
                    },
                    word_count=count_words(callout_content),
                    char_count=count_chars(callout_content)
                )
                current_section.blocks.append(callout_block)

                block_start = i + 1
                continue

            # 수평선 감지
            if self.patterns['horizontal_rule'].match(line):
                # 이전 블록 저장
                if block_lines:
                    self._flush_block(block_lines, block_start, current_section)
                    block_lines = []

                hr_block = Block(
                    type=BlockType.HORIZONTAL_RULE,
                    content='---',
                    raw_markdown=line,
                    start_line=line_num,
                    end_line=line_num,
                    word_count=0,
                    char_count=3
                )
                current_section.blocks.append(hr_block)

                block_start = line_num + 1
                i += 1
                continue

            # 일반 라인은 버퍼에 추가
            block_lines.append((line_num, line))
            i += 1

        # 남은 블록 저장
        if block_lines:
            self._flush_block(block_lines, block_start, current_section)

        # 마지막 섹션들 종료 라인 설정
        for section in section_stack:
            if section.end_line == -1:
                section.end_line = n

        # 섹션별 단어 수 계산
        for section in doc.sections:
            section.word_count = sum(b.word_count for b in section.blocks)

        # 문서 제목 설정 (첫 번째 H1 또는 프론트매터)
        if doc.frontmatter.get('title'):
            doc.title = doc.frontmatter['title']
        else:
            for section in doc.sections:
                if section.level == 1:
                    doc.title = section.title
                    break

    def _parse_frontmatter(self, lines: List[str], start: int, doc: Document) -> int:
        """YAML 프론트매터 파싱 (v2: YamlParser 사용)"""
        i = start + 1
        fm_lines = []

        while i < len(lines):
            if self.patterns['frontmatter_start'].match(lines[i]):
                break
            fm_lines.append(lines[i])
            i += 1

        # v2: YamlParser 사용
        fm_content = '\n'.join(fm_lines)
        doc.frontmatter = self.yaml_parser.parse(fm_content)

        return i + 1

    def _flush_block(self, block_lines: List[Tuple[int, str]],
                     start_line: int, section: Section) -> None:
        """버퍼의 라인들을 블록으로 변환하여 저장"""
        if not block_lines:
            return

        # 빈 라인으로 블록 분리
        current_block: List[Tuple[int, str]] = []

        for line_num, line in block_lines:
            if line.strip() == '':
                if current_block:
                    self._create_block(current_block, section)
                    current_block = []
            else:
                current_block.append((line_num, line))

        if current_block:
            self._create_block(current_block, section)

    def _create_block(self, lines: List[Tuple[int, str]], section: Section) -> None:
        """라인들로부터 블록 생성"""
        if not lines:
            return

        start_line = lines[0][0]
        end_line = lines[-1][0]
        raw_text = '\n'.join(line for _, line in lines)
        first_line = lines[0][1]

        # 블록 타입 판별
        metadata = {}
        if self.patterns['list_item'].match(first_line):
            block_type = BlockType.LIST
            content = self._extract_list_content(lines)
        elif self.patterns['blockquote'].match(first_line):
            block_type = BlockType.BLOCKQUOTE
            content = self._extract_blockquote_content(lines)
        elif self.patterns['image'].match(first_line.strip()):
            # 표준 마크다운 이미지: ![alt](path)
            block_type = BlockType.IMAGE
            match = self.patterns['image'].match(first_line.strip())
            content = match.group(1) if match else ''
            metadata = {
                'format': 'markdown',
                'path': match.group(2) if match else '',
                'alt': match.group(1) if match else ''
            }
        elif self.patterns['image_wikilink'].match(first_line.strip()):
            # Obsidian wikilink 이미지: ![[path|size]]
            block_type = BlockType.IMAGE
            match = self.patterns['image_wikilink'].match(first_line.strip())
            path = match.group(1) if match else ''
            size_or_alt = match.group(2) if match and match.group(2) else ''
            content = path
            metadata = {
                'format': 'wikilink',
                'path': path,
                'size': size_or_alt if size_or_alt.isdigit() or 'x' in size_or_alt.lower() else '',
                'alt': size_or_alt if not (size_or_alt.isdigit() or 'x' in size_or_alt.lower()) else ''
            }
        else:
            block_type = BlockType.PARAGRAPH
            content = ' '.join(line.strip() for _, line in lines)

        block = Block(
            type=block_type,
            content=content,
            raw_markdown=raw_text,
            start_line=start_line,
            end_line=end_line,
            word_count=count_words(content),
            char_count=count_chars(content),
            metadata=metadata if metadata else None
        )
        section.blocks.append(block)

    def _extract_list_content(self, lines: List[Tuple[int, str]]) -> str:
        """리스트에서 텍스트 추출"""
        items = []
        for _, line in lines:
            match = self.patterns['list_item'].match(line)
            if match:
                items.append(match.group(3))
            else:
                items.append(line.strip())
        return '\n'.join(items)

    def _extract_blockquote_content(self, lines: List[Tuple[int, str]]) -> str:
        """인용구에서 텍스트 추출"""
        content_lines = []
        for _, line in lines:
            match = self.patterns['blockquote'].match(line)
            if match:
                content_lines.append(match.group(2))
            else:
                content_lines.append(line.strip())
        return ' '.join(content_lines)

    def _extract_table_content(self, lines: List[str]) -> str:
        """테이블에서 텍스트 추출 (구분선 제외)"""
        content_lines = []
        for line in lines:
            if not re.match(r'^\s*\|[-:|\s]+\|\s*$', line):
                cells = [c.strip() for c in line.strip('|').split('|')]
                content_lines.append(' | '.join(cells))
        return '\n'.join(content_lines)
