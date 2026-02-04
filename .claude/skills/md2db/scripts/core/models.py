# -*- coding: utf-8 -*-
"""
Data models for md2db v2

- BlockType: 블록 유형 열거형
- Block: 콘텐츠 블록
- Section: 문서 섹션 (헤더 기반)
- Document: 문서 메타데이터
- SourceFile: 원본 파일 정보 (v2 신규)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class BlockType(Enum):
    """블록 유형 열거형"""
    FRONTMATTER = "frontmatter"
    HEADER = "header"
    PARAGRAPH = "paragraph"
    LIST = "list"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    TABLE = "table"
    HORIZONTAL_RULE = "horizontal_rule"
    IMAGE = "image"
    CALLOUT = "callout"          # v2: Obsidian callout 지원
    MATH_BLOCK = "math_block"    # v2: 수식 블록
    MERMAID = "mermaid"          # v2: Mermaid 다이어그램
    EMPTY = "empty"


@dataclass
class Block:
    """콘텐츠 블록"""
    type: BlockType
    content: str           # 텍스트 내용 (마크다운 제거)
    raw_markdown: str      # 원본 마크다운
    start_line: int
    end_line: int
    metadata: Dict = field(default_factory=dict)
    word_count: int = 0    # v2: 단어 수
    char_count: int = 0    # v2: 문자 수


@dataclass
class Section:
    """문서 섹션 (헤더 기반)"""
    level: int             # 헤더 레벨 (0=루트, 1-6)
    title: str             # 헤더 텍스트
    path: str              # 계층 경로 (예: "1.2.3")
    position: int          # 문서 내 순서
    start_line: int
    end_line: int = -1
    parent_id: Optional[int] = None
    blocks: List[Block] = field(default_factory=list)
    word_count: int = 0           # v2: 섹션 내 단어 수
    has_subsections: bool = False  # v2: 하위 섹션 존재 여부


@dataclass
class Document:
    """문서 메타데이터"""
    filename: str
    title: str = ""
    file_size: int = 0
    encoding: str = "utf-8"
    frontmatter: Dict = field(default_factory=dict)
    sections: List[Section] = field(default_factory=list)
    total_words: int = 0   # v2: 총 단어 수


@dataclass
class SourceFile:
    """원본 파일 정보 (v2 신규 - 중복/변경 감지용)"""
    filepath: str           # 절대 경로
    filename: str           # 파일명
    file_hash: str          # SHA256 해시
    file_size: int          # 바이트
    encoding: str = "utf-8"
    status: str = "pending"  # pending, processed, error, deleted
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    document_id: Optional[int] = None  # 연결된 문서 ID
