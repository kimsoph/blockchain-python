# -*- coding: utf-8 -*-
"""
BaseConverter: 문서 변환기 추상 클래스

모든 변환기(HWPX, PDF, DOCX)가 상속받는 기본 클래스.
공통 기능: YAML 프론트매터 생성, 파일명 메타데이터 파싱
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import re


@dataclass
class ConversionResult:
    """변환 결과 데이터클래스"""
    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    title: str = ""
    doc_type: str = ""
    doc_number: str = ""
    effective_date: str = ""
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        if self.success:
            return f"✓ {self.input_path.name} → {self.output_path.name if self.output_path else 'N/A'}"
        else:
            return f"✗ {self.input_path.name}: {self.error}"


class BaseConverter(ABC):
    """문서 변환기 추상 클래스"""

    # 법률 문서 파일명 패턴: 법률명(유형)(문서번호)(시행일).hwpx
    # 예: 소득세법(법률)(제21065호)(20260102).hwpx
    LAW_FILENAME_PATTERN = re.compile(
        r'^(.+?)'                    # 법률명 (non-greedy)
        r'\(([^)]+)\)'               # (유형) - 법률, 시행령, 시행규칙 등
        r'\(제?(\d+)호?\)'            # (제N호) 또는 (N호)
        r'\((\d{8})\)'               # (YYYYMMDD)
        r'\.(\w+)$',                 # 확장자
        re.UNICODE
    )

    # 조문 패턴 (법률 구조 인식용)
    CHAPTER_PATTERN = re.compile(r'^제\s*(\d+)\s*장\s+(.+)$')  # 제1장 총칙
    ARTICLE_PATTERN = re.compile(r'^제\s*(\d+)\s*조(\s*의\s*\d+)?\s*[\(（](.+?)[\)）]')  # 제1조(목적)
    PARAGRAPH_PATTERN = re.compile(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]')  # 항
    SUBPARAGRAPH_PATTERN = re.compile(r'^\d+\.')  # 호 (1. 2. 3.)
    ITEM_PATTERN = re.compile(r'^[가나다라마바사아자차카타파하]\.')  # 목 (가. 나. 다.)

    @abstractmethod
    def convert(self, input_path: Path, output_path: Optional[Path] = None) -> ConversionResult:
        """
        파일을 마크다운으로 변환

        Args:
            input_path: 입력 파일 경로
            output_path: 출력 파일 경로 (None이면 자동 생성)

        Returns:
            ConversionResult: 변환 결과
        """
        pass

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """
        이 변환기가 처리할 수 있는 파일인지 확인

        Args:
            file_path: 확인할 파일 경로

        Returns:
            bool: 처리 가능 여부
        """
        pass

    def generate_frontmatter(
        self,
        title: str,
        doc_type: str = "",
        doc_number: str = "",
        effective_date: str = "",
        source: str = "",
        **extra_fields
    ) -> str:
        """
        YAML 프론트매터 생성

        Args:
            title: 문서 제목
            doc_type: 문서 유형 (법률, 시행령 등)
            doc_number: 문서 번호
            effective_date: 시행일
            source: 출처
            **extra_fields: 추가 필드

        Returns:
            str: YAML 프론트매터 문자열
        """
        lines = ["---"]
        lines.append(f"title: {title}")

        if doc_type:
            lines.append(f"type: {doc_type}")
        if doc_number:
            lines.append(f"문서번호: {doc_number}")
        if effective_date:
            # YYYYMMDD → YYYY-MM-DD 포맷
            if len(effective_date) == 8 and effective_date.isdigit():
                formatted_date = f"{effective_date[:4]}-{effective_date[4:6]}-{effective_date[6:]}"
            else:
                formatted_date = effective_date
            lines.append(f"시행일: {formatted_date}")
        if source:
            lines.append(f"source: {source}")

        # 추가 필드
        for key, value in extra_fields.items():
            if value:
                lines.append(f"{key}: {value}")

        # 변환 시각
        lines.append(f"converted_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("---")

        return "\n".join(lines)

    def parse_law_filename(self, filename: str) -> dict:
        """
        법률 문서 파일명에서 메타데이터 추출

        Args:
            filename: 파일명 (예: 소득세법(법률)(제21065호)(20260102).hwpx)

        Returns:
            dict: 추출된 메타데이터
                - title: 법률명
                - doc_type: 문서 유형
                - doc_number: 문서 번호
                - effective_date: 시행일 (YYYYMMDD)
                - extension: 확장자
        """
        match = self.LAW_FILENAME_PATTERN.match(filename)

        if match:
            return {
                'title': match.group(1).strip(),
                'doc_type': match.group(2).strip(),
                'doc_number': f"제{match.group(3)}호",
                'effective_date': match.group(4),
                'extension': match.group(5)
            }
        else:
            # 패턴 매칭 실패 시 기본값
            stem = Path(filename).stem
            return {
                'title': stem,
                'doc_type': '',
                'doc_number': '',
                'effective_date': '',
                'extension': Path(filename).suffix.lstrip('.')
            }

    def generate_output_filename(self, metadata: dict, extension: str = "md") -> str:
        """
        출력 파일명 생성

        Args:
            metadata: 메타데이터 딕셔너리
            extension: 출력 파일 확장자

        Returns:
            str: 출력 파일명 (예: 소득세법_20260102.md)
        """
        title = metadata.get('title', 'untitled')
        effective_date = metadata.get('effective_date', '')

        # 파일명에 사용할 수 없는 문자 제거
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)

        if effective_date:
            return f"{safe_title}_{effective_date}.{extension}"
        else:
            return f"{safe_title}.{extension}"

    def detect_document_type(self, texts: list, filename: str) -> str:
        """
        문서 유형 자동 감지 (법률 vs 일반)

        Args:
            texts: 텍스트 리스트
            filename: 파일명

        Returns:
            str: 'law' 또는 'general'
        """
        # 1. 파일명 패턴 확인
        law_keywords = ['법률', '시행령', '시행규칙', '규정', '조례', '훈령', '고시', '예규']
        for keyword in law_keywords:
            if keyword in filename:
                return 'law'

        # 2. 텍스트 내용 확인 (개별 라인 검사)
        article_count = 0
        chapter_count = 0

        for text in texts[:50]:  # 앞부분만 확인
            if self.ARTICLE_PATTERN.match(text):
                article_count += 1
            if self.CHAPTER_PATTERN.match(text):
                chapter_count += 1
            if self.PARAGRAPH_PATTERN.match(text):
                return 'law'

        if article_count >= 3 or chapter_count >= 1:
            return 'law'

        return 'general'
