# -*- coding: utf-8 -*-
"""
HWPXConverter: HWPX 파일 → 마크다운 변환기

HWPX는 ZIP 형식의 한글 문서로, 내부에 XML 파일들이 포함됨.
주요 콘텐츠: Contents/section0.xml
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import re
import chardet

from .base import BaseConverter, ConversionResult


class HWPXConverter(BaseConverter):
    """HWPX 파일을 마크다운으로 변환 (ZIP + XML 파싱)"""

    # HWPX XML 네임스페이스
    NAMESPACES = {
        'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
        'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
        'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    }

    def __init__(self, doc_type: str = 'auto'):
        """
        Args:
            doc_type:
              - 'auto': 파일명/내용 패턴으로 자동 감지 (기본값)
              - 'law': 법률 문서 (장/조/항/호 구조)
              - 'general': 일반 문서 (단순 텍스트 추출)
        """
        self.doc_type = doc_type

    def can_handle(self, file_path: Path) -> bool:
        """HWPX 파일인지 확인"""
        return file_path.suffix.lower() == '.hwpx'

    def convert(self, input_path: Path, output_path: Optional[Path] = None) -> ConversionResult:
        """
        HWPX 파일을 마크다운으로 변환

        Args:
            input_path: HWPX 파일 경로
            output_path: 출력 마크다운 파일 경로 (None이면 자동 생성)

        Returns:
            ConversionResult: 변환 결과
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return ConversionResult(
                success=False,
                input_path=input_path,
                error=f"파일을 찾을 수 없습니다: {input_path}"
            )

        try:
            # 1. 파일명에서 메타데이터 추출
            metadata = self.parse_law_filename(input_path.name)

            # 2. HWPX 파일 열기 및 XML 추출
            texts = self._extract_texts_from_hwpx(input_path)

            if not texts:
                return ConversionResult(
                    success=False,
                    input_path=input_path,
                    error="텍스트를 추출할 수 없습니다"
                )

            # 3. 문서 유형 결정
            if self.doc_type == 'auto':
                detected_type = self.detect_document_type(texts, input_path.name)
            else:
                detected_type = self.doc_type

            # 4. 마크다운 포맷팅
            if detected_type == 'law':
                markdown_content = self._format_law_markdown(texts, metadata)
            else:
                markdown_content = self._format_general_markdown(texts, metadata)

            # 5. 출력 경로 결정
            if output_path is None:
                output_filename = self.generate_output_filename(metadata)
                output_path = input_path.parent / output_filename
            else:
                output_path = Path(output_path)

            # 6. 파일 저장
            output_path.write_text(markdown_content, encoding='utf-8')

            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                title=metadata.get('title', ''),
                doc_type=metadata.get('doc_type', ''),
                doc_number=metadata.get('doc_number', ''),
                effective_date=metadata.get('effective_date', ''),
                metadata=metadata
            )

        except zipfile.BadZipFile:
            return ConversionResult(
                success=False,
                input_path=input_path,
                error="유효하지 않은 HWPX 파일입니다 (ZIP 형식 오류)"
            )
        except ET.ParseError as e:
            return ConversionResult(
                success=False,
                input_path=input_path,
                error=f"XML 파싱 오류: {e}"
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                input_path=input_path,
                error=f"변환 중 오류 발생: {e}"
            )

    def _extract_texts_from_hwpx(self, hwpx_path: Path) -> list:
        """
        HWPX 파일에서 텍스트 추출

        Args:
            hwpx_path: HWPX 파일 경로

        Returns:
            list: 추출된 텍스트 리스트 (단락별)
        """
        texts = []

        with zipfile.ZipFile(hwpx_path, 'r') as zf:
            # section 파일들 찾기 (section0.xml, section1.xml, ...)
            section_files = sorted([
                f for f in zf.namelist()
                if f.startswith('Contents/section') and f.endswith('.xml')
            ])

            for section_file in section_files:
                xml_content = zf.read(section_file)

                # 인코딩 감지
                detected = chardet.detect(xml_content)
                encoding = detected.get('encoding', 'utf-8')

                try:
                    xml_str = xml_content.decode(encoding)
                except UnicodeDecodeError:
                    xml_str = xml_content.decode('utf-8', errors='replace')

                # XML 파싱
                section_texts = self._parse_section_xml(xml_str)
                texts.extend(section_texts)

        return texts

    def _parse_section_xml(self, xml_str: str) -> list:
        """
        섹션 XML에서 텍스트 추출

        Args:
            xml_str: XML 문자열

        Returns:
            list: 추출된 텍스트 리스트
        """
        texts = []

        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError:
            # 네임스페이스 문제 시 재시도
            # 네임스페이스 선언 추가
            if 'xmlns:hp' not in xml_str:
                xml_str = xml_str.replace(
                    '<hs:sec',
                    '<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
                )
            root = ET.fromstring(xml_str)

        # hp:t 태그에서 텍스트 추출
        for t_elem in root.iter():
            # 태그 이름에서 네임스페이스 제거하고 확인
            tag_name = t_elem.tag.split('}')[-1] if '}' in t_elem.tag else t_elem.tag

            if tag_name == 't' and t_elem.text:
                text = t_elem.text.strip()
                if text:
                    texts.append(text)

        # 텍스트가 없으면 모든 텍스트 노드 추출 시도
        if not texts:
            texts = self._extract_all_text(root)

        return texts

    def _extract_all_text(self, element: ET.Element) -> list:
        """
        엘리먼트에서 모든 텍스트 추출 (fallback)

        Args:
            element: XML 엘리먼트

        Returns:
            list: 추출된 텍스트 리스트
        """
        texts = []

        def extract_recursive(elem):
            if elem.text and elem.text.strip():
                texts.append(elem.text.strip())
            for child in elem:
                extract_recursive(child)
            if elem.tail and elem.tail.strip():
                texts.append(elem.tail.strip())

        extract_recursive(element)
        return texts

    def _is_header_artifact(self, text: str, title: str) -> bool:
        """
        법제처 HWPX 헤더 아티팩트인지 확인

        Args:
            text: 검사할 텍스트
            title: 문서 제목

        Returns:
            bool: 아티팩트 여부
        """
        text = text.strip()

        # 빈 문자열
        if not text:
            return True

        # 제목과 동일 (중복)
        if text == title:
            return True

        # 약칭 포함
        if text.startswith('( 약칭:') or text.startswith('(약칭:'):
            return True

        # 단일 문자 아티팩트
        if text in ['-', '/', '·', '|']:
            return True

        # 법제처 관련
        if text in ['법제처', '국가법령정보센터']:
            return True

        # [시행 YYYY. M. D.] 패턴 (본문에 이미 포함)
        if text.startswith('[시행') and ']' in text:
            return True

        # 소관부처 전화번호 패턴 (예: "금융위원회(산업금융과) 02-2100-2864")
        if re.search(r'\d{2,3}-\d{3,4}-\d{4}$', text):
            return True

        # 소관부처만 있는 경우 (예: "기획재정부(공공정책총괄과)")
        if re.match(r'^[가-힣]+\([가-힣]+\)$', text):
            return True

        return False

    def _format_law_markdown(self, texts: list, metadata: dict) -> str:
        """
        법률 텍스트를 마크다운으로 포맷팅 (장/조/항/호/목 구조)

        Args:
            texts: 텍스트 리스트
            metadata: 메타데이터

        Returns:
            str: 마크다운 문자열
        """
        lines = []

        # 프론트매터
        frontmatter = self.generate_frontmatter(
            title=metadata.get('title', '제목 없음'),
            doc_type=metadata.get('doc_type', ''),
            doc_number=metadata.get('doc_number', ''),
            effective_date=metadata.get('effective_date', ''),
            source='법제처 국가법령정보센터'
        )
        lines.append(frontmatter)
        lines.append("")

        # 제목
        title = metadata.get('title', '제목 없음')
        lines.append(f"# {title}")
        lines.append("")

        # 시행정보 블록
        effective_date = metadata.get('effective_date', '')
        doc_number = metadata.get('doc_number', '')
        if effective_date and doc_number:
            formatted_date = f"{effective_date[:4]}. {int(effective_date[4:6])}. {int(effective_date[6:])}."
            doc_type = metadata.get('doc_type', '법률')
            lines.append(f"> [시행 {formatted_date}] [{doc_type} {doc_number}]")
            lines.append("")

        # 본문 처리
        current_chapter = None
        current_article = None
        in_paragraph = False
        body_started = False  # 본문 시작 여부

        for text in texts:
            text = text.strip()
            if not text:
                continue

            # 장 제목 (## 제1장 총칙)
            chapter_match = self.CHAPTER_PATTERN.match(text)
            if chapter_match:
                body_started = True
                if in_paragraph:
                    lines.append("")
                    in_paragraph = False
                lines.append("")
                lines.append(f"## 제{chapter_match.group(1)}장 {chapter_match.group(2)}")
                lines.append("")
                current_chapter = chapter_match.group(1)
                continue

            # 조 제목 (### 제1조(목적))
            article_match = self.ARTICLE_PATTERN.match(text)
            if article_match:
                body_started = True
                if in_paragraph:
                    lines.append("")
                    in_paragraph = False
                lines.append("")
                # 전체 조 텍스트 포맷팅
                article_num = article_match.group(1)
                article_suffix = article_match.group(2) or ""
                article_title = article_match.group(3)
                lines.append(f"### 제{article_num}조{article_suffix}({article_title})")
                lines.append("")
                current_article = article_num
                # 조 제목 뒤의 내용 처리
                remaining = text[article_match.end():].strip()
                if remaining:
                    lines.append(remaining)
                    lines.append("")
                continue

            # 전문 (헌법 등)
            if text == '전문':
                body_started = True
                lines.append("")
                lines.append("## 전문")
                lines.append("")
                continue

            # 본문 시작 전에는 헤더 아티팩트 건너뛰기
            if not body_started:
                if self._is_header_artifact(text, title):
                    continue

            # 항 (① ② ③ ...)
            if self.PARAGRAPH_PATTERN.match(text):
                body_started = True
                if in_paragraph:
                    lines.append("")
                lines.append(text)
                in_paragraph = True
                continue

            # 호 (1. 2. 3. ...)
            if self.SUBPARAGRAPH_PATTERN.match(text):
                # 들여쓰기
                lines.append(f"   {text}")
                continue

            # 목 (가. 나. 다. ...)
            if self.ITEM_PATTERN.match(text):
                # 더 깊은 들여쓰기
                lines.append(f"      {text}")
                continue

            # 일반 텍스트
            if text:
                lines.append(text)
                in_paragraph = True

        return '\n'.join(lines)

    def _format_general_markdown(self, texts: list, metadata: dict) -> str:
        """
        일반 텍스트를 마크다운으로 포맷팅 (단순 단락)

        Args:
            texts: 텍스트 리스트
            metadata: 메타데이터

        Returns:
            str: 마크다운 문자열
        """
        lines = []

        # 프론트매터
        frontmatter = self.generate_frontmatter(
            title=metadata.get('title', '제목 없음'),
            source='HWPX 변환'
        )
        lines.append(frontmatter)
        lines.append("")

        # 제목
        title = metadata.get('title', '제목 없음')
        lines.append(f"# {title}")
        lines.append("")

        # 본문 - 연속된 텍스트를 단락으로 그룹화
        current_paragraph = []

        for text in texts:
            text = text.strip()
            if not text:
                if current_paragraph:
                    lines.append(' '.join(current_paragraph))
                    lines.append("")
                    current_paragraph = []
                continue

            # 짧은 텍스트는 이전 단락에 합치기
            if len(text) < 20 and current_paragraph:
                current_paragraph.append(text)
            else:
                if current_paragraph:
                    lines.append(' '.join(current_paragraph))
                    lines.append("")
                current_paragraph = [text]

        # 마지막 단락 처리
        if current_paragraph:
            lines.append(' '.join(current_paragraph))

        return '\n'.join(lines)


def get_converter(file_path: Path) -> BaseConverter:
    """
    파일 확장자 기반으로 적절한 변환기 반환

    Args:
        file_path: 파일 경로

    Returns:
        BaseConverter: 적절한 변환기 인스턴스

    Raises:
        ValueError: 지원하지 않는 포맷
    """
    converters = [HWPXConverter()]

    for conv in converters:
        if conv.can_handle(file_path):
            return conv

    raise ValueError(f"지원하지 않는 포맷: {file_path.suffix}")
