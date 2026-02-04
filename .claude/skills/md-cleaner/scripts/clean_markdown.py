#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Cleaner Script v3.3
마크다운 파일을 클리닝하여 불필요한 요소를 제거하고 문법을 정리합니다.

v3.3 업데이트 (2026-02-04):
- HWPX 아티팩트 제거: 법제처 국가법령정보센터 HWPX 변환 시 발생하는 아티팩트 처리
  - ^1., ^2., ^3) 등 각주/미주 마커 제거
  - {이미지파일목록}, {국가법령이미지로고목록} 등 플레이스홀더 제거

v3.2 업데이트 (2026-01-30):
- 대문자 로마숫자 인식: I., II., III., IV., V. 등 헤더 줄바꿈 보존
- OCR 아티팩트 정리: 일본어 히라가나 'へ' → 화살표 '→' 교정

v3.1 업데이트 (2026-01-06):
- 로깅 시스템: logging 모듈 도입, --quiet/--verbose 옵션
- 페이지번호 옵션: --page-max로 감지 범위 조정 가능
- HTML 엔티티 처리: &nbsp;, &lt; 등 자동 디코딩
- 링크/이미지 보호: [text](url), ![alt](url) 내부 텍스트 보존
- 테이블 정렬: --align-tables 옵션으로 열 너비 정렬
- 커스텀 패턴: --extra-pattern으로 추가 제거 패턴 지정
- requirements.txt 추가 (chardet 의존성 명시)

v3.0 업데이트 (2025-12-18):
- 인라인 코드 보호: 백틱(`) 내부 텍스트 보존
- 코드 블록 불일치 경고: 열린 코드 블록 감지
- 정규식 사전 컴파일: 성능 최적화
- --dry-run 옵션: 변경사항 미리보기
- --diff 옵션: 원본과 결과 비교
- --backup 옵션: 원본 파일 백업
- 배치 처리: 디렉토리 내 모든 .md 파일 처리
- 코드 블록 감지 로직 통합 리팩토링
- 문장 내 줄바꿈 삭제 강화 (한국어 종결어미 확장)

v2.0 업데이트 (2025-12-05):
- 페이지번호 삭제 강화 (- N - 패턴 등)
- 마크다운 문법 오류 수정 (- *, - -, - ** 등)
- 불필요한 문자강조 제거 (볼드, 이탤릭, 밑줄)
- 문장 중간 줄바꿈 수정 (문장 이어붙이기)
"""

import re
import sys
import os
import shutil
import argparse
import logging
import html
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class CleaningResult:
    """클리닝 결과를 담는 데이터 클래스"""
    input_path: str
    output_path: str
    original_size: int
    cleaned_size: int
    reduction: int
    encoding_used: str
    warnings: List[str]


class CodeBlockExtractor:
    """코드 블록, 인라인 코드, 링크/이미지를 추출하고 복원하는 클래스"""

    def __init__(self):
        self.code_blocks: List[str] = []
        self.inline_codes: List[str] = []
        self.markdown_links: List[str] = []
        self.yaml_frontmatter: Optional[str] = None
        # 플레이스홀더는 제어문자 제거에 영향받지 않는 유니코드 사용
        self.code_block_placeholder = "\uE000CODE_BLOCK_{}\uE001"
        self.inline_code_placeholder = "\uE000INLINE_CODE_{}\uE001"
        self.link_placeholder = "\uE002LINK_{}\uE003"
        self.yaml_placeholder = "\uE000YAML_FRONTMATTER\uE001"

    def extract_code_blocks(self, text: str) -> Tuple[str, List[str]]:
        """코드 블록을 추출하고 플레이스홀더로 대체"""
        self.code_blocks = []

        # 코드 블록 패턴: ```로 시작하고 ```로 끝남
        pattern = re.compile(r'```[^\n]*\n.*?```', re.DOTALL)

        def replace_block(match):
            idx = len(self.code_blocks)
            self.code_blocks.append(match.group(0))
            return self.code_block_placeholder.format(idx)

        result = pattern.sub(replace_block, text)
        return result, self.code_blocks

    def extract_inline_codes(self, text: str) -> Tuple[str, List[str]]:
        """인라인 코드를 추출하고 플레이스홀더로 대체"""
        self.inline_codes = []

        # 인라인 코드 패턴: `...` (백틱 내부에 백틱 없음)
        pattern = re.compile(r'`[^`\n]+`')

        def replace_inline(match):
            idx = len(self.inline_codes)
            self.inline_codes.append(match.group(0))
            return self.inline_code_placeholder.format(idx)

        result = pattern.sub(replace_inline, text)
        return result, self.inline_codes

    def restore_code_blocks(self, text: str) -> str:
        """플레이스홀더를 원래 코드 블록으로 복원"""
        for idx, block in enumerate(self.code_blocks):
            text = text.replace(self.code_block_placeholder.format(idx), block)
        return text

    def restore_inline_codes(self, text: str) -> str:
        """플레이스홀더를 원래 인라인 코드로 복원"""
        for idx, code in enumerate(self.inline_codes):
            text = text.replace(self.inline_code_placeholder.format(idx), code)
        return text

    def check_unclosed_blocks(self, text: str) -> List[str]:
        """닫히지 않은 코드 블록 감지"""
        warnings = []
        lines = text.split('\n')
        in_code_block = False
        block_start_line = 0

        for i, line in enumerate(lines, 1):
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    block_start_line = i
                else:
                    in_code_block = False

        if in_code_block:
            warnings.append(f"경고: {block_start_line}번 줄에서 시작된 코드 블록이 닫히지 않았습니다.")

        return warnings

    def extract_markdown_links(self, text: str) -> Tuple[str, List[str]]:
        """마크다운 링크와 이미지를 추출하고 플레이스홀더로 대체 (v3.1)"""
        self.markdown_links = []

        # 이미지: ![alt](url) 와 링크: [text](url) 패턴
        # 이미지를 먼저 처리해야 ![...](...) 가 [...](...) 로 잘못 매칭되지 않음
        pattern = re.compile(r'!?\[[^\]]*\]\([^)]+\)')

        def replace_link(match):
            idx = len(self.markdown_links)
            self.markdown_links.append(match.group(0))
            return self.link_placeholder.format(idx)

        result = pattern.sub(replace_link, text)
        return result, self.markdown_links

    def restore_markdown_links(self, text: str) -> str:
        """플레이스홀더를 원래 링크/이미지로 복원 (v3.1)"""
        for idx, link in enumerate(self.markdown_links):
            text = text.replace(self.link_placeholder.format(idx), link)
        return text

    def extract_yaml_frontmatter(self, text: str) -> Tuple[str, Optional[str]]:
        """YAML 프론트매터를 추출하고 플레이스홀더로 대체"""
        self.yaml_frontmatter = None
        if not text.startswith('---'):
            return text, None
        match = re.match(r'^---\n.*?\n---[ \t]*\n', text, re.DOTALL)
        if match:
            self.yaml_frontmatter = match.group(0)
            return self.yaml_placeholder + '\n' + text[match.end():], self.yaml_frontmatter
        return text, None

    def restore_yaml_frontmatter(self, text: str) -> str:
        """플레이스홀더를 원래 YAML 프론트매터로 복원"""
        if self.yaml_frontmatter is not None:
            text = text.replace(self.yaml_placeholder, self.yaml_frontmatter.rstrip('\n'))
        return text


class MarkdownCleaner:
    """마크다운 클리닝을 수행하는 클래스"""

    def __init__(self, page_number_max: int = 100,
                 extra_patterns: List[str] = None,
                 align_tables: bool = False,
                 log_level: int = logging.INFO):
        """
        Args:
            page_number_max: 페이지 번호로 간주할 최대 숫자 (기본: 100)
            extra_patterns: 추가로 제거할 정규식 패턴 리스트
            align_tables: 테이블 열 정렬 수행 여부
            log_level: 로깅 레벨 (기본: INFO)
        """
        self.code_extractor = CodeBlockExtractor()
        self.warnings: List[str] = []
        self.page_number_max = page_number_max
        self.extra_patterns = [re.compile(p) for p in (extra_patterns or [])]
        self.do_align_tables = align_tables

        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)

        # 페이지 번호 패턴들 (사전 컴파일)
        self.page_patterns = [
            re.compile(r'^\s*페이지\s*\d+\s*$', re.IGNORECASE),
            re.compile(r'^\s*Page\s*\d+\s*$', re.IGNORECASE),
            re.compile(r'^\s*p\.\s*\d+\s*$', re.IGNORECASE),
            re.compile(r'^\s*pp\.\s*\d+[-–—]\d+\s*$', re.IGNORECASE),
            re.compile(r'^\s*\d+\s*쪽\s*$'),
            re.compile(r'^\s*제\s*\d+\s*쪽\s*$'),
            re.compile(r'^\s*\d+\s*/\s*\d+\s*$'),
            re.compile(r'^\s*\(\s*\d+\s*/\s*\d+\s*\)\s*$'),
            re.compile(r'^\s*\[\s*\d+\s*\]\s*$'),
            re.compile(r'^\s*\(\s*\d+\s*\)\s*$'),
            re.compile(r'^\s*-\s*\d+\s*-\s*$'),
            re.compile(r'^\s*–\s*\d+\s*–\s*$'),
            re.compile(r'^\s*—\s*\d+\s*—\s*$'),
            re.compile(r'^\s*\d+\s*$'),  # 단독 숫자 (신중하게 처리)
        ]

        # 보존해야 할 마크다운 문법 요소 (사전 컴파일)
        self.preserve_patterns = [
            re.compile(r'^#{1,6}\s'),
            re.compile(r'^\s*\d+\.\s'),
            re.compile(r'^\s*[-*+]\s+\S'),
            re.compile(r'^\s*>\s'),
            re.compile(r'^\s*```'),
            re.compile(r'^\s*\|'),
            re.compile(r'^\s*---\s*$'),
        ]

        # 잘못된 리스트 시작 패턴 (사전 컴파일)
        self.bad_list_patterns = [
            (re.compile(r'^(\s*)-\s*\*\*\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*\*\s+'), r'\1- '),
            (re.compile(r'^(\s*)-\s*-\s+'), r'\1- '),
            (re.compile(r'^(\s*)-\s*·\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*▶\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*■\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*□\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*○\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*●\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*◆\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*◇\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*△\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*▷\s*'), r'\1- '),
            (re.compile(r'^(\s*)-\s*※\s*'), r'\1- '),
        ]

        # 문장 종결 패턴 (한국어 종결어미 확장)
        self.sentence_end_pattern = re.compile(
            r'[.!?。！？][\s"\'」』）\)]*$|'  # 마침표, 느낌표, 물음표
            r'[\)）\]」』]\s*$|'              # 닫는 괄호로 끝남
            r'다\s*$|요\s*$|음\s*$|함\s*$|'  # 한국어 종결어미
            r'임\s*$|됨\s*$|것\s*$|수\s*$|'  # 한국어 종결어미
            r'니다\s*$|습니다\s*$|'          # 존칭 종결어미
            r'세요\s*$|시오\s*$|'            # 청유/명령형
            r'랍니다\s*$|답니다\s*$|'        # 설명형
            r'네요\s*$|군요\s*$|'            # 감탄형
            r'지요\s*$|죠\s*$|'              # 확인형
            r'거든요\s*$|잖아요\s*$|'        # 이유/강조형
            r'\d+[%％]\s*$|'                  # 퍼센트로 끝남
            r'\d+[조억만천백]\s*원?\s*$|'     # 금액으로 끝남
            r'등\s*$|'                        # '등'으로 끝남
            r'[:：]\s*$'                      # 콜론으로 끝남
        )

        # 문장 이어붙이기 제외 패턴 (사전 컴파일)
        self.no_join_start_pattern = re.compile(
            r'^\s*[-*+]\s|'
            r'^\s*\d+[.)]\s|'
            r'^\s*#{1,6}\s|'
            r'^\s*>\s|'
            r'^\s*```|'
            r'^\s*\||'
            r'^\s*---\s*$|'
            r'^\s*$|'
            r'^\s*[□■○●▶◆◇△▷▲]\s|'
            r'^\s*[①②③④⑤⑥⑦⑧⑨⑩]|'
            r'^\s*[ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ]|'
            r'^\s*[IVXLCDM]+\.\s|'  # 대문자 로마숫자 (I., II., III., IV., V., ...)
            r'^\s*[가나다라마바사아자차카타파하]\.|'
            r'^\s*\([가나다라마바사아자차카타파하]\)|'
            r'^\s*\(\d+\)|'
            r'^\s*<'
        )

        # 텍스트 강조 패턴 (사전 컴파일)
        self.bold_pattern = re.compile(r'\*\*([^*]+)\*\*')
        self.bold_underscore_pattern = re.compile(r'__([^_]+)__')
        self.italic_pattern = re.compile(r'(?<!\w)\*([^*\n]+)\*(?!\w)')
        self.italic_underscore_pattern = re.compile(r'(?<![a-zA-Z0-9_])_([^_\n]+)_(?![a-zA-Z0-9_])')
        self.strikethrough_pattern = re.compile(r'~~([^~]+)~~')
        self.highlight_pattern = re.compile(r'==([^=]+)==')

    def is_likely_page_number(self, line: str) -> bool:
        """라인이 페이지 번호일 가능성이 있는지 확인"""
        stripped = line.strip()

        if not stripped:
            return False

        # 페이지 번호 패턴 먼저 체크 (- N - 형식 등)
        for pattern in self.page_patterns:
            if pattern.match(stripped):
                # 단독 숫자는 추가 검증 (page_number_max 이하만)
                if pattern.pattern == r'^\s*\d+\s*$':
                    try:
                        num = int(stripped)
                        if num <= self.page_number_max:
                            return True
                    except ValueError:
                        pass
                else:
                    return True

        # 커스텀 패턴 체크 (v3.1)
        for pattern in self.extra_patterns:
            if pattern.match(stripped):
                return True

        # 마크다운 문법 요소가 있으면 페이지 번호가 아님
        for pattern in self.preserve_patterns:
            if pattern.match(line):
                return False

        return False

    def fix_bad_list_syntax(self, line: str) -> str:
        """잘못된 리스트 문법 수정"""
        for pattern, replacement in self.bad_list_patterns:
            line = pattern.sub(replacement, line)
        return line

    def remove_text_emphasis(self, text: str) -> str:
        """불필요한 텍스트 강조 제거 (인라인 코드는 이미 추출됨)"""
        # 볼드 제거
        text = self.bold_pattern.sub(r'\1', text)
        text = self.bold_underscore_pattern.sub(r'\1', text)

        # 이탤릭 제거
        text = self.italic_pattern.sub(r'\1', text)
        text = self.italic_underscore_pattern.sub(r'\1', text)

        # 취소선 제거
        text = self.strikethrough_pattern.sub(r'\1', text)

        # 하이라이트 제거
        text = self.highlight_pattern.sub(r'\1', text)

        return text

    def should_join_lines(self, prev_line: str, curr_line: str) -> bool:
        """두 줄을 이어붙여야 하는지 판단"""
        prev_stripped = prev_line.strip()
        curr_stripped = curr_line.strip()

        if not prev_stripped or not curr_stripped:
            return False

        if self.no_join_start_pattern.match(curr_line):
            return False

        if self.sentence_end_pattern.search(prev_stripped):
            return False

        # 이전 줄이 헤더면 이어붙이지 않음
        if re.match(r'^\s*#{1,6}\s', prev_line):
            return False

        # 테이블 행이면 이어붙이지 않음
        if '|' in prev_stripped:
            return False

        # 리스트 아이템이고 다음 줄 들여쓰기 없으면 이어붙이지 않음
        if re.match(r'^\s*[-*+]\s', prev_line) and not curr_line.startswith(' '):
            return False

        return True

    def join_broken_sentences(self, text: str) -> str:
        """문장 중간에 끊긴 줄바꿈을 수정"""
        lines = text.split('\n')
        result_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 다음 줄과 이어붙이기 검사
            while i + 1 < len(lines):
                next_line = lines[i + 1]

                if self.should_join_lines(line, next_line):
                    line = line.rstrip() + ' ' + next_line.strip()
                    i += 1
                else:
                    break

            result_lines.append(line)
            i += 1

        return '\n'.join(result_lines)

    def remove_excessive_blank_lines(self, text: str) -> str:
        """3개 이상의 연속된 빈 줄을 2개로 줄임"""
        return re.sub(r'\n{3,}', '\n\n', text)

    def remove_trailing_spaces(self, text: str) -> str:
        """각 줄의 끝 공백 제거 (마크다운 줄바꿈용 정확히 2개 스페이스만 보존)"""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            stripped = line.rstrip()
            # 원본이 정확히 2개 스페이스로 끝나면 보존
            if line.endswith('  ') and not line.endswith('   '):
                cleaned_lines.append(stripped + '  ')
            else:
                cleaned_lines.append(stripped)

        return '\n'.join(cleaned_lines)

    def normalize_spaces(self, text: str) -> str:
        """연속된 스페이스를 하나로 정리"""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # 들여쓰기된 코드 블록(4칸 들여쓰기)은 보존
            if line.startswith('    '):
                cleaned_lines.append(line)
            else:
                cleaned_line = re.sub(r' {2,}', ' ', line)
                cleaned_lines.append(cleaned_line)

        return '\n'.join(cleaned_lines)

    def remove_control_characters(self, text: str) -> str:
        """제어 문자 제거 (줄바꿈, 탭은 보존)"""
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    def remove_unusual_unicode(self, text: str) -> str:
        """이상한 유니코드 문자 정리"""
        # Zero-width 문자 제거
        text = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text)

        # 일반적이지 않은 화이트스페이스 정규화
        text = re.sub(r'[\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]', ' ', text)

        # OCR 아티팩트 정리: 일본 히라가나 'へ'(U+3078) → 화살표 오인식 교정
        text = re.sub(r'へ\s*(\d+)', r'→ \1', text)  # へ 117 → → 117

        return text

    def is_hwpx_artifact_line(self, line: str) -> bool:
        """HWPX 변환 아티팩트 라인인지 확인 (v3.3)

        법제처 국가법령정보센터 HWPX 파일 변환 시 발생하는 아티팩트:
        - ^1., ^2., ^3) 등 각주/미주 마커
        - {이미지파일목록}, {국가법령이미지로고목록} 등 플레이스홀더
        """
        stripped = line.strip()
        if not stripped:
            return False

        # ^숫자. 또는 ^숫자) 패턴 (각주/미주 마커)
        if re.match(r'^\^[\d]+[\.\)]\s*$', stripped):
            return True

        # {플레이스홀더} 패턴 (이미지, 로고 등)
        if re.match(r'^\{[가-힣\w]+\}\s*$', stripped):
            return True

        return False

    def decode_html_entities(self, text: str) -> str:
        """HTML 엔티티를 일반 텍스트로 변환 (v3.1)

        PDF/OCR 변환 시 남은 &nbsp;, &lt;, &gt;, &amp; 등을 처리
        """
        return html.unescape(text)

    def _get_display_width(self, text: str) -> int:
        """문자열의 표시 너비 계산 (한글은 2칸)"""
        width = 0
        for char in text:
            # 한글, 한자, 일본어 등 동아시아 문자는 2칸
            if '\uac00' <= char <= '\ud7a3':  # 한글 완성형
                width += 2
            elif '\u4e00' <= char <= '\u9fff':  # 한자
                width += 2
            elif '\u3040' <= char <= '\u30ff':  # 히라가나/가타카나
                width += 2
            else:
                width += 1
        return width

    def _align_table_columns(self, rows: List[str]) -> List[str]:
        """테이블 열 너비를 정렬 (v3.1)"""
        if not rows:
            return rows

        # 각 행을 셀로 분리
        parsed_rows = []
        for row in rows:
            # 앞뒤 | 제거 후 분리
            cells = row.strip().strip('|').split('|')
            cells = [cell.strip() for cell in cells]
            parsed_rows.append(cells)

        if not parsed_rows:
            return rows

        # 최대 열 수 확인
        max_cols = max(len(row) for row in parsed_rows)

        # 각 열의 최대 너비 계산
        col_widths = [0] * max_cols
        for row in parsed_rows:
            for i, cell in enumerate(row):
                if i < max_cols:
                    width = self._get_display_width(cell)
                    col_widths[i] = max(col_widths[i], width)

        # 정렬된 테이블 생성
        aligned_rows = []
        for row_idx, row in enumerate(parsed_rows):
            aligned_cells = []
            for i in range(max_cols):
                cell = row[i] if i < len(row) else ''
                # 구분선 행인지 확인
                if row_idx > 0 and all(c in '-:|' for c in cell.replace(' ', '')):
                    # 구분선은 '-'로 채움
                    if ':' in cell:
                        # 정렬 정보 보존
                        aligned_cells.append(cell)
                    else:
                        aligned_cells.append('-' * col_widths[i])
                else:
                    # 일반 셀: 패딩 추가
                    current_width = self._get_display_width(cell)
                    padding = col_widths[i] - current_width
                    aligned_cells.append(cell + ' ' * padding)

            aligned_rows.append('| ' + ' | '.join(aligned_cells) + ' |')

        return aligned_rows

    def align_tables(self, text: str) -> str:
        """마크다운 테이블 열 정렬 (v3.1)"""
        lines = text.split('\n')
        result = []
        table_buffer = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            # 테이블 행 감지 (|로 시작하거나 |를 포함)
            is_table_line = stripped.startswith('|') or (
                '|' in stripped and
                not stripped.startswith('```') and
                stripped.count('|') >= 2
            )

            if is_table_line:
                if not in_table:
                    in_table = True
                table_buffer.append(line)
            elif in_table:
                # 테이블 종료
                if table_buffer:
                    aligned = self._align_table_columns(table_buffer)
                    result.extend(aligned)
                table_buffer = []
                in_table = False
                result.append(line)
            else:
                result.append(line)

        # 마지막 테이블 처리
        if table_buffer:
            aligned = self._align_table_columns(table_buffer)
            result.extend(aligned)

        return '\n'.join(result)

    def clean_markdown(self, text: str) -> str:
        """마크다운 텍스트를 클리닝"""
        # 0. YAML 프론트매터 추출 (보호)
        text, _ = self.code_extractor.extract_yaml_frontmatter(text)

        # 0.5 코드 블록 불일치 체크
        self.warnings.extend(self.code_extractor.check_unclosed_blocks(text))

        # 1. 코드 블록 추출 (보호)
        text, _ = self.code_extractor.extract_code_blocks(text)

        # 2. 인라인 코드 추출 (보호)
        text, _ = self.code_extractor.extract_inline_codes(text)

        # 2.5 마크다운 링크/이미지 추출 (보호) (v3.1)
        text, _ = self.code_extractor.extract_markdown_links(text)

        # 3. 제어 문자 및 이상한 유니코드 제거
        text = self.remove_control_characters(text)
        text = self.remove_unusual_unicode(text)

        # 3.5 HTML 엔티티 처리 (v3.1)
        text = self.decode_html_entities(text)

        # 4. 줄 단위로 처리 (페이지 번호 제거, 잘못된 리스트 문법 수정)
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            if self.is_likely_page_number(line):
                self.logger.debug(f"페이지 번호 제거: {line.strip()}")
                continue
            if self.is_hwpx_artifact_line(line):
                self.logger.debug(f"HWPX 아티팩트 제거: {line.strip()}")
                continue
            line = self.fix_bad_list_syntax(line)
            cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)

        # 5. 불필요한 텍스트 강조 제거
        text = self.remove_text_emphasis(text)

        # 6. 문장 중간 줄바꿈 수정
        text = self.join_broken_sentences(text)

        # 7. 공백 정리
        text = self.normalize_spaces(text)
        text = self.remove_trailing_spaces(text)

        # 8. 과도한 빈 줄 정리
        text = self.remove_excessive_blank_lines(text)

        # 8.5 테이블 정렬 (v3.1, 옵션)
        if self.do_align_tables:
            text = self.align_tables(text)

        # 9. 마크다운 링크/이미지 복원 (v3.1)
        text = self.code_extractor.restore_markdown_links(text)

        # 10. 인라인 코드 복원
        text = self.code_extractor.restore_inline_codes(text)

        # 11. 코드 블록 복원
        text = self.code_extractor.restore_code_blocks(text)

        # 11.5 YAML 프론트매터 복원
        text = self.code_extractor.restore_yaml_frontmatter(text)

        # 12. 파일 시작/끝의 불필요한 빈 줄 제거
        text = text.strip() + '\n'

        return text

    def process_file(self, input_path: str, output_path: str = None,
                     dry_run: bool = False, backup: bool = False) -> CleaningResult:
        """파일을 클리닝하여 저장"""
        self.warnings = []  # 경고 초기화
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {input_path}")

        # 출력 경로 결정
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
        else:
            output_path = Path(output_path)

        # 파일 읽기 (UTF-8 인코딩)
        encoding_used = 'utf-8'
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                import chardet
                with open(input_path, 'rb') as f:
                    raw_data = f.read()
                    detected = chardet.detect(raw_data)
                    encoding_used = detected['encoding']

                with open(input_path, 'r', encoding=encoding_used) as f:
                    content = f.read()

                self.warnings.append(f"경고: {encoding_used} 인코딩으로 읽었습니다. UTF-8로 저장됩니다.")
            except ImportError:
                encoding_used = 'cp949'
                with open(input_path, 'r', encoding='cp949') as f:
                    content = f.read()
                self.warnings.append("경고: cp949 인코딩으로 읽었습니다. UTF-8로 저장됩니다.")

        original_size = len(content)

        # 클리닝 수행
        cleaned_content = self.clean_markdown(content)
        cleaned_size = len(cleaned_content)

        # dry-run 모드면 저장하지 않음
        if not dry_run:
            # 백업 옵션
            if backup and output_path.exists():
                backup_path = output_path.with_suffix('.md.bak')
                shutil.copy2(output_path, backup_path)
                self.warnings.append(f"백업 생성: {backup_path}")

            # 파일 쓰기 (UTF-8 인코딩)
            with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(cleaned_content)

        result = CleaningResult(
            input_path=str(input_path),
            output_path=str(output_path),
            original_size=original_size,
            cleaned_size=cleaned_size,
            reduction=original_size - cleaned_size,
            encoding_used=encoding_used,
            warnings=self.warnings.copy()
        )

        return result

    def process_directory(self, dir_path: str, recursive: bool = False,
                          dry_run: bool = False, backup: bool = False) -> List[CleaningResult]:
        """디렉토리 내 모든 .md 파일을 클리닝"""
        dir_path = Path(dir_path)
        results = []

        if not dir_path.is_dir():
            raise NotADirectoryError(f"디렉토리가 아닙니다: {dir_path}")

        # 패턴 설정
        pattern = '**/*.md' if recursive else '*.md'

        for md_file in dir_path.glob(pattern):
            # _clean.md 파일은 건너뜀
            if md_file.stem.endswith('_clean'):
                continue

            try:
                result = self.process_file(str(md_file), dry_run=dry_run, backup=backup)
                results.append(result)
            except Exception as e:
                print(f"오류 ({md_file}): {e}", file=sys.stderr)

        return results


def generate_diff(original: str, cleaned: str) -> str:
    """원본과 클리닝 결과의 차이를 생성"""
    try:
        import difflib
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            cleaned.splitlines(keepends=True),
            fromfile='original',
            tofile='cleaned',
            lineterm=''
        )
        return ''.join(diff)
    except Exception:
        return "diff 생성 실패"


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='Markdown Cleaner v3.1 - 마크다운 파일 클리닝 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python clean_markdown.py document.md              # 기본 클리닝
  python clean_markdown.py document.md output.md    # 출력 파일 지정
  python clean_markdown.py --dry-run document.md    # 미리보기
  python clean_markdown.py --diff document.md       # 차이 확인
  python clean_markdown.py --batch ./docs/          # 디렉토리 일괄 처리
  python clean_markdown.py --batch -r ./docs/       # 재귀적 일괄 처리
  python clean_markdown.py --page-max 50 doc.md     # 페이지번호 범위 조정
  python clean_markdown.py --align-tables doc.md    # 테이블 정렬
        """
    )

    parser.add_argument('input', nargs='?', help='입력 파일 또는 디렉토리')
    parser.add_argument('output', nargs='?', help='출력 파일 (선택사항)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='실제 파일 수정 없이 결과만 미리보기')
    parser.add_argument('--diff', '-d', action='store_true',
                        help='원본과 클리닝 결과의 차이 출력')
    parser.add_argument('--backup', '-b', action='store_true',
                        help='기존 파일 백업 (.md.bak)')
    parser.add_argument('--batch', action='store_true',
                        help='디렉토리 내 모든 .md 파일 일괄 처리')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='하위 디렉토리까지 재귀적으로 처리 (--batch와 함께 사용)')
    parser.add_argument('--version', '-v', action='version', version='Markdown Cleaner v3.2')

    # v3.1 새 옵션
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='경고만 출력 (정보 메시지 숨김)')
    parser.add_argument('--verbose', action='store_true',
                        help='상세 로그 출력 (디버그 정보 포함)')
    parser.add_argument('--page-max', type=int, default=100,
                        help='페이지 번호로 간주할 최대 숫자 (기본: 100)')
    parser.add_argument('--align-tables', action='store_true',
                        help='마크다운 테이블 열 너비 정렬')
    parser.add_argument('--extra-pattern', action='append', default=[],
                        help='추가로 제거할 정규식 패턴 (여러 번 사용 가능)')

    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        sys.exit(1)

    # 로그 레벨 설정
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    cleaner = MarkdownCleaner(
        page_number_max=args.page_max,
        extra_patterns=args.extra_pattern,
        align_tables=args.align_tables,
        log_level=log_level
    )

    try:
        if args.batch:
            # 배치 처리 모드
            results = cleaner.process_directory(
                args.input,
                recursive=args.recursive,
                dry_run=args.dry_run,
                backup=args.backup
            )

            print(f"\n{'=' * 50}")
            print(f"배치 처리 완료: {len(results)}개 파일")
            print(f"{'=' * 50}")

            total_original = sum(r.original_size for r in results)
            total_cleaned = sum(r.cleaned_size for r in results)

            for result in results:
                status = "[DRY-RUN]" if args.dry_run else "[OK]"
                print(f"{status} {result.input_path}")
                print(f"    {result.original_size:,} → {result.cleaned_size:,} bytes "
                      f"(-{result.reduction:,})")
                for warning in result.warnings:
                    print(f"    {warning}")

            print(f"\n총 원본: {total_original:,} bytes")
            print(f"총 클리닝 후: {total_cleaned:,} bytes")
            print(f"총 감소: {total_original - total_cleaned:,} bytes "
                  f"({(1 - total_cleaned/total_original)*100:.1f}%)")
        else:
            # 단일 파일 처리
            if args.diff:
                # diff 모드: 원본 읽고 클리닝 후 차이 출력
                with open(args.input, 'r', encoding='utf-8') as f:
                    original = f.read()
                cleaned = cleaner.clean_markdown(original)
                diff_output = generate_diff(original, cleaned)
                print(diff_output if diff_output else "변경사항 없음")
            else:
                result = cleaner.process_file(
                    args.input,
                    args.output,
                    dry_run=args.dry_run,
                    backup=args.backup
                )

                status = "[DRY-RUN]" if args.dry_run else "[OK]"
                print(f"{status} 클리닝 완료: {result.output_path}")
                print(f"  원본 크기: {result.original_size:,} bytes")
                print(f"  클리닝 후: {result.cleaned_size:,} bytes")
                print(f"  감소: {result.reduction:,} bytes "
                      f"({(result.reduction/result.original_size)*100:.1f}%)")

                for warning in result.warnings:
                    print(f"  {warning}")

    except Exception as e:
        print(f"오류 발생: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
