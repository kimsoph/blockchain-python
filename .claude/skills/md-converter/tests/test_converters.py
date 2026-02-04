# -*- coding: utf-8 -*-
"""
md-converter 테스트 모듈

테스트 실행:
    cd .claude/skills/md-converter
    python -m pytest tests/ -v
"""

import sys
from pathlib import Path
import tempfile

# 상위 디렉토리를 Python 경로에 추가
SCRIPT_DIR = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from converters.base import BaseConverter, ConversionResult
from converters.hwpx import HWPXConverter


class TestConversionResult:
    """ConversionResult 테스트"""

    def test_success_result_str(self):
        """성공 결과 문자열 테스트"""
        result = ConversionResult(
            success=True,
            input_path=Path("test.hwpx"),
            output_path=Path("test.md"),
            title="테스트"
        )
        assert "✓" in str(result)
        assert "test.hwpx" in str(result)
        assert "test.md" in str(result)

    def test_failure_result_str(self):
        """실패 결과 문자열 테스트"""
        result = ConversionResult(
            success=False,
            input_path=Path("test.hwpx"),
            error="파일을 찾을 수 없습니다"
        )
        assert "✗" in str(result)
        assert "파일을 찾을 수 없습니다" in str(result)


class TestBaseConverter:
    """BaseConverter 테스트"""

    def test_parse_law_filename_full(self):
        """법률 파일명 파싱 테스트 - 전체 패턴"""
        converter = HWPXConverter()  # BaseConverter는 추상 클래스이므로 구체 클래스 사용

        metadata = converter.parse_law_filename("소득세법(법률)(제21065호)(20260102).hwpx")

        assert metadata['title'] == '소득세법'
        assert metadata['doc_type'] == '법률'
        assert metadata['doc_number'] == '제21065호'
        assert metadata['effective_date'] == '20260102'
        assert metadata['extension'] == 'hwpx'

    def test_parse_law_filename_short_number(self):
        """법률 파일명 파싱 테스트 - 짧은 번호"""
        converter = HWPXConverter()

        metadata = converter.parse_law_filename("은행법(법률)(1234호)(20250101).hwpx")

        assert metadata['title'] == '은행법'
        assert metadata['doc_number'] == '제1234호'

    def test_parse_law_filename_no_match(self):
        """법률 파일명 파싱 테스트 - 패턴 불일치"""
        converter = HWPXConverter()

        metadata = converter.parse_law_filename("일반문서.hwpx")

        assert metadata['title'] == '일반문서'
        assert metadata['doc_type'] == ''
        assert metadata['doc_number'] == ''

    def test_generate_frontmatter(self):
        """프론트매터 생성 테스트"""
        converter = HWPXConverter()

        frontmatter = converter.generate_frontmatter(
            title="소득세법",
            doc_type="법률",
            doc_number="제21065호",
            effective_date="20260102",
            source="법제처"
        )

        assert "---" in frontmatter
        assert "title: 소득세법" in frontmatter
        assert "type: 법률" in frontmatter
        assert "시행일: 2026-01-02" in frontmatter  # 포맷 변환 확인

    def test_generate_output_filename(self):
        """출력 파일명 생성 테스트"""
        converter = HWPXConverter()

        metadata = {
            'title': '소득세법',
            'effective_date': '20260102'
        }

        filename = converter.generate_output_filename(metadata)
        assert filename == '소득세법_20260102.md'

    def test_generate_output_filename_no_date(self):
        """출력 파일명 생성 테스트 - 날짜 없음"""
        converter = HWPXConverter()

        metadata = {'title': '일반문서'}

        filename = converter.generate_output_filename(metadata)
        assert filename == '일반문서.md'

    def test_detect_document_type_by_filename(self):
        """문서 유형 감지 테스트 - 파일명 기반"""
        converter = HWPXConverter()

        # 법률 키워드 포함
        assert converter.detect_document_type([], "소득세법(법률).hwpx") == 'law'
        assert converter.detect_document_type([], "시행령_test.hwpx") == 'law'
        assert converter.detect_document_type([], "규정_2024.hwpx") == 'law'

        # 일반 문서
        assert converter.detect_document_type([], "보고서.hwpx") == 'general'

    def test_detect_document_type_by_content(self):
        """문서 유형 감지 테스트 - 내용 기반"""
        converter = HWPXConverter()

        # 조문 패턴 포함
        law_texts = [
            "제1조(목적) 이 법은...",
            "제2조(정의) 이 법에서...",
            "제3조(적용범위) 이 법은..."
        ]
        assert converter.detect_document_type(law_texts, "document.hwpx") == 'law'

        # 장 패턴 포함
        chapter_texts = ["제1장 총칙", "제2장 본론"]
        assert converter.detect_document_type(chapter_texts, "document.hwpx") == 'law'

        # 일반 텍스트
        general_texts = ["안녕하세요", "이것은 일반 문서입니다"]
        assert converter.detect_document_type(general_texts, "document.hwpx") == 'general'


class TestHWPXConverter:
    """HWPXConverter 테스트"""

    def test_can_handle_hwpx(self):
        """HWPX 파일 처리 가능 여부 테스트"""
        converter = HWPXConverter()

        assert converter.can_handle(Path("test.hwpx")) is True
        assert converter.can_handle(Path("test.HWPX")) is True
        assert converter.can_handle(Path("test.pdf")) is False
        assert converter.can_handle(Path("test.docx")) is False

    def test_convert_nonexistent_file(self):
        """존재하지 않는 파일 변환 테스트"""
        converter = HWPXConverter()

        result = converter.convert(Path("/nonexistent/path/file.hwpx"))

        assert result.success is False
        assert "찾을 수 없습니다" in result.error

    def test_format_law_markdown_structure(self):
        """법률 마크다운 포맷팅 구조 테스트"""
        converter = HWPXConverter()

        texts = [
            "제1장 총칙",
            "제1조(목적) 이 법은 목적을 규정한다.",
            "① 제1항 내용",
            "② 제2항 내용",
            "1. 제1호 내용",
            "2. 제2호 내용"
        ]

        metadata = {
            'title': '테스트법',
            'doc_type': '법률',
            'doc_number': '제1호',
            'effective_date': '20260101'
        }

        result = converter._format_law_markdown(texts, metadata)

        assert "# 테스트법" in result
        assert "## 제1장 총칙" in result
        assert "### 제1조(목적)" in result
        assert "① 제1항 내용" in result

    def test_format_general_markdown_structure(self):
        """일반 마크다운 포맷팅 구조 테스트"""
        converter = HWPXConverter()

        texts = [
            "첫 번째 문장입니다.",
            "두 번째 문장입니다.",
            "세 번째 문장입니다."
        ]

        metadata = {'title': '일반 문서'}

        result = converter._format_general_markdown(texts, metadata)

        assert "# 일반 문서" in result
        assert "source: HWPX 변환" in result


class TestIntegration:
    """통합 테스트"""

    def test_full_conversion_pipeline(self):
        """전체 변환 파이프라인 테스트 (모의 HWPX 파일 필요)"""
        # 실제 HWPX 파일이 있는 경우에만 테스트
        # 이 테스트는 실제 파일로 수동 실행 권장
        pass


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
