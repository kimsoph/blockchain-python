#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Cleaner v3.0 단위 테스트
"""

import unittest
import sys
import os

# 스크립트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from clean_markdown import MarkdownCleaner, CodeBlockExtractor


class TestCodeBlockExtractor(unittest.TestCase):
    """CodeBlockExtractor 클래스 테스트"""

    def setUp(self):
        self.extractor = CodeBlockExtractor()

    def test_extract_code_blocks(self):
        """코드 블록 추출 테스트"""
        text = """일반 텍스트
```python
def hello():
    print("world")
```
또 다른 텍스트"""

        result, blocks = self.extractor.extract_code_blocks(text)

        self.assertEqual(len(blocks), 1)
        self.assertIn('def hello():', blocks[0])
        self.assertNotIn('```python', result.replace('\x00', ''))

    def test_extract_inline_codes(self):
        """인라인 코드 추출 테스트"""
        text = "이것은 `인라인 코드`입니다. 그리고 `또 다른 코드`도 있습니다."

        result, codes = self.extractor.extract_inline_codes(text)

        self.assertEqual(len(codes), 2)
        self.assertEqual(codes[0], '`인라인 코드`')
        self.assertEqual(codes[1], '`또 다른 코드`')

    def test_restore_code_blocks(self):
        """코드 블록 복원 테스트"""
        text = """텍스트
```python
code
```
끝"""
        extracted, _ = self.extractor.extract_code_blocks(text)
        restored = self.extractor.restore_code_blocks(extracted)

        self.assertEqual(text, restored)

    def test_check_unclosed_blocks(self):
        """닫히지 않은 코드 블록 감지 테스트"""
        text = """정상 텍스트
```python
열린 코드 블록
닫히지 않음"""

        warnings = self.extractor.check_unclosed_blocks(text)

        self.assertEqual(len(warnings), 1)
        self.assertIn('닫히지 않았습니다', warnings[0])


class TestMarkdownCleaner(unittest.TestCase):
    """MarkdownCleaner 클래스 테스트"""

    def setUp(self):
        self.cleaner = MarkdownCleaner()

    # === 페이지 번호 감지 테스트 ===

    def test_page_number_korean(self):
        """한글 페이지 번호 감지"""
        self.assertTrue(self.cleaner.is_likely_page_number("페이지 1"))
        self.assertTrue(self.cleaner.is_likely_page_number("  페이지 25  "))

    def test_page_number_english(self):
        """영문 페이지 번호 감지"""
        self.assertTrue(self.cleaner.is_likely_page_number("Page 1"))
        self.assertTrue(self.cleaner.is_likely_page_number("  Page 42  "))
        self.assertTrue(self.cleaner.is_likely_page_number("p. 5"))

    def test_page_number_dash(self):
        """대시 형식 페이지 번호 감지"""
        self.assertTrue(self.cleaner.is_likely_page_number("- 1 -"))
        self.assertTrue(self.cleaner.is_likely_page_number("– 15 –"))  # en-dash
        self.assertTrue(self.cleaner.is_likely_page_number("— 20 —"))  # em-dash

    def test_page_number_bracket(self):
        """괄호 형식 페이지 번호 감지"""
        self.assertTrue(self.cleaner.is_likely_page_number("[1]"))
        self.assertTrue(self.cleaner.is_likely_page_number("(25)"))
        self.assertTrue(self.cleaner.is_likely_page_number("1 / 10"))

    def test_page_number_standalone(self):
        """단독 숫자 페이지 번호 감지"""
        self.assertTrue(self.cleaner.is_likely_page_number("42"))
        self.assertTrue(self.cleaner.is_likely_page_number("100"))
        self.assertFalse(self.cleaner.is_likely_page_number("101"))  # 100 초과
        self.assertFalse(self.cleaner.is_likely_page_number("2024"))

    def test_preserve_markdown_syntax(self):
        """마크다운 문법 보존"""
        self.assertFalse(self.cleaner.is_likely_page_number("# 1. 서론"))
        self.assertFalse(self.cleaner.is_likely_page_number("1. 첫 번째 항목"))
        self.assertFalse(self.cleaner.is_likely_page_number("- 1번 항목"))
        self.assertFalse(self.cleaner.is_likely_page_number("> 인용문 1"))

    # === 리스트 문법 수정 테스트 ===

    def test_fix_bad_list_double_asterisk(self):
        """이중 별표 리스트 수정"""
        self.assertEqual(self.cleaner.fix_bad_list_syntax("- ** 텍스트"), "- 텍스트")

    def test_fix_bad_list_single_asterisk(self):
        """단일 별표 리스트 수정"""
        self.assertEqual(self.cleaner.fix_bad_list_syntax("- * 텍스트"), "- 텍스트")

    def test_fix_bad_list_double_dash(self):
        """이중 대시 리스트 수정"""
        self.assertEqual(self.cleaner.fix_bad_list_syntax("- - 텍스트"), "- 텍스트")

    def test_fix_bad_list_special_chars(self):
        """특수문자 리스트 수정"""
        self.assertEqual(self.cleaner.fix_bad_list_syntax("- ○ 항목"), "- 항목")
        self.assertEqual(self.cleaner.fix_bad_list_syntax("- ■ 항목"), "- 항목")
        self.assertEqual(self.cleaner.fix_bad_list_syntax("- ※ 항목"), "- 항목")

    # === 텍스트 강조 제거 테스트 ===

    def test_remove_bold(self):
        """볼드 제거"""
        result = self.cleaner.remove_text_emphasis("**볼드 텍스트**")
        self.assertEqual(result, "볼드 텍스트")

    def test_remove_italic(self):
        """이탤릭 제거"""
        result = self.cleaner.remove_text_emphasis("*이탤릭 텍스트*")
        self.assertEqual(result, "이탤릭 텍스트")

    def test_remove_strikethrough(self):
        """취소선 제거"""
        result = self.cleaner.remove_text_emphasis("~~취소선 텍스트~~")
        self.assertEqual(result, "취소선 텍스트")

    def test_remove_highlight(self):
        """하이라이트 제거"""
        result = self.cleaner.remove_text_emphasis("==하이라이트==")
        self.assertEqual(result, "하이라이트")

    # === 문장 병합 테스트 ===

    def test_join_broken_sentences(self):
        """끊어진 문장 병합"""
        text = "이 문장은 중간에서\n끊어졌습니다."
        result = self.cleaner.join_broken_sentences(text)
        self.assertEqual(result, "이 문장은 중간에서 끊어졌습니다.")

    def test_no_join_after_period(self):
        """마침표 후 병합 안 함"""
        text = "첫 번째 문장입니다.\n두 번째 문장입니다."
        result = self.cleaner.join_broken_sentences(text)
        self.assertEqual(result, "첫 번째 문장입니다.\n두 번째 문장입니다.")

    def test_no_join_korean_ending(self):
        """한국어 종결어미 후 병합 안 함"""
        text = "이것은 테스트입니다\n다음 줄입니다"
        result = self.cleaner.join_broken_sentences(text)
        self.assertEqual(result, "이것은 테스트입니다\n다음 줄입니다")

    def test_no_join_list_items(self):
        """리스트 항목 병합 안 함"""
        text = "- 첫 번째 항목\n- 두 번째 항목"
        result = self.cleaner.join_broken_sentences(text)
        self.assertEqual(result, "- 첫 번째 항목\n- 두 번째 항목")

    def test_no_join_headers(self):
        """헤더 병합 안 함"""
        text = "# 제목\n본문 내용"
        result = self.cleaner.join_broken_sentences(text)
        self.assertEqual(result, "# 제목\n본문 내용")

    # === 공백 정리 테스트 ===

    def test_normalize_spaces(self):
        """연속 스페이스 정리"""
        result = self.cleaner.normalize_spaces("텍스트   사이   공백")
        self.assertEqual(result, "텍스트 사이 공백")

    def test_preserve_indented_code(self):
        """들여쓰기 코드 보존"""
        result = self.cleaner.normalize_spaces("    코드    공백    보존")
        self.assertEqual(result, "    코드    공백    보존")

    def test_remove_trailing_spaces(self):
        """줄 끝 공백 제거"""
        result = self.cleaner.remove_trailing_spaces("텍스트   ")
        self.assertEqual(result, "텍스트")

    def test_preserve_markdown_line_break(self):
        """마크다운 줄바꿈 보존"""
        result = self.cleaner.remove_trailing_spaces("텍스트  ")  # 2칸 스페이스
        self.assertEqual(result, "텍스트  ")

    def test_remove_excessive_blank_lines(self):
        """과도한 빈 줄 정리"""
        text = "첫째\n\n\n\n\n둘째"
        result = self.cleaner.remove_excessive_blank_lines(text)
        self.assertEqual(result, "첫째\n\n둘째")

    # === 제어 문자 및 유니코드 테스트 ===

    def test_remove_control_characters(self):
        """제어 문자 제거"""
        text = "텍스트\x00\x07\x08중간"
        result = self.cleaner.remove_control_characters(text)
        self.assertEqual(result, "텍스트중간")

    def test_preserve_newline_tab(self):
        """줄바꿈과 탭 보존"""
        text = "첫째\n둘째\t셋째"
        result = self.cleaner.remove_control_characters(text)
        self.assertEqual(result, "첫째\n둘째\t셋째")

    def test_remove_zero_width_chars(self):
        """Zero-width 문자 제거"""
        text = "텍스트\u200b중간\ufeff끝"
        result = self.cleaner.remove_unusual_unicode(text)
        self.assertEqual(result, "텍스트중간끝")

    def test_normalize_unicode_spaces(self):
        """유니코드 공백 정규화"""
        text = "텍스트\u00a0중간\u3000끝"
        result = self.cleaner.remove_unusual_unicode(text)
        self.assertEqual(result, "텍스트 중간 끝")

    # === 전체 클리닝 테스트 ===

    def test_clean_markdown_full(self):
        """전체 클리닝 파이프라인"""
        text = """# 제목

페이지 1

**볼드** 텍스트입니다.

- * 잘못된 리스트

- 2 -

끝"""
        result = self.cleaner.clean_markdown(text)

        # 페이지 번호 제거됨
        self.assertNotIn("페이지 1", result)
        self.assertNotIn("- 2 -", result)

        # 볼드 제거됨
        self.assertNotIn("**", result)
        self.assertIn("볼드 텍스트입니다", result)

        # 리스트 수정됨
        self.assertNotIn("- *", result)

    def test_inline_code_protection(self):
        """인라인 코드 보호"""
        text = "`**코드 내부**`는 보존됩니다."
        result = self.cleaner.clean_markdown(text)

        self.assertIn("`**코드 내부**`", result)

    def test_code_block_protection(self):
        """코드 블록 보호"""
        text = """```python
**볼드**  연속공백  보존
```"""
        result = self.cleaner.clean_markdown(text)

        self.assertIn("**볼드**", result)
        self.assertIn("연속공백  보존", result)


class TestShouldJoinLines(unittest.TestCase):
    """should_join_lines 메서드 상세 테스트"""

    def setUp(self):
        self.cleaner = MarkdownCleaner()

    def test_join_incomplete_sentence(self):
        """불완전 문장 병합"""
        self.assertTrue(self.cleaner.should_join_lines("이것은 중간에서", "끊어진 문장입니다"))

    def test_no_join_empty_lines(self):
        """빈 줄 병합 안 함"""
        self.assertFalse(self.cleaner.should_join_lines("", "다음 줄"))
        self.assertFalse(self.cleaner.should_join_lines("이전 줄", ""))

    def test_no_join_list_start(self):
        """리스트 시작 병합 안 함"""
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "- 리스트"))
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "* 리스트"))
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "1. 순서 리스트"))

    def test_no_join_header_start(self):
        """헤더 시작 병합 안 함"""
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "# 제목"))
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "## 소제목"))

    def test_no_join_quote_start(self):
        """인용구 시작 병합 안 함"""
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "> 인용문"))

    def test_no_join_table_row(self):
        """테이블 행 병합 안 함"""
        self.assertFalse(self.cleaner.should_join_lines("| 셀1 | 셀2 |", "| 셀3 | 셀4 |"))

    def test_no_join_special_list_markers(self):
        """특수 리스트 마커 병합 안 함"""
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "① 첫 번째"))
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "가. 항목"))
        self.assertFalse(self.cleaner.should_join_lines("텍스트", "(1) 항목"))


# ============================================================
# v3.1 새 테스트 클래스
# ============================================================

class TestHTMLEntityDecoding(unittest.TestCase):
    """HTML 엔티티 디코딩 테스트 (v3.1)"""

    def setUp(self):
        self.cleaner = MarkdownCleaner()

    def test_decode_nbsp(self):
        """&nbsp; 디코딩"""
        result = self.cleaner.decode_html_entities("텍스트&nbsp;사이&nbsp;공백")
        self.assertNotIn("&nbsp;", result)
        # &nbsp;는 \xa0 (non-breaking space)로 디코딩됨
        # remove_unusual_unicode에서 일반 스페이스로 변환됨
        self.assertIn("\xa0", result)

    def test_decode_lt_gt(self):
        """&lt; &gt; 디코딩"""
        result = self.cleaner.decode_html_entities("&lt;tag&gt;")
        self.assertEqual(result, "<tag>")

    def test_decode_amp(self):
        """&amp; 디코딩"""
        result = self.cleaner.decode_html_entities("A &amp; B")
        self.assertEqual(result, "A & B")

    def test_decode_numeric_entity(self):
        """숫자 엔티티 디코딩"""
        result = self.cleaner.decode_html_entities("&#60;&#62;")
        self.assertEqual(result, "<>")

    def test_html_entity_in_pipeline(self):
        """전체 파이프라인에서 HTML 엔티티 처리"""
        text = "텍스트&nbsp;사이&nbsp;공백"
        result = self.cleaner.clean_markdown(text)
        self.assertNotIn("&nbsp;", result)


class TestMarkdownLinkProtection(unittest.TestCase):
    """마크다운 링크 보호 테스트 (v3.1)"""

    def setUp(self):
        self.extractor = CodeBlockExtractor()
        self.cleaner = MarkdownCleaner()

    def test_extract_simple_link(self):
        """일반 링크 추출"""
        text = "이것은 [링크](https://example.com) 입니다."
        result, links = self.extractor.extract_markdown_links(text)
        self.assertEqual(len(links), 1)
        self.assertIn("[링크](https://example.com)", links)

    def test_extract_image(self):
        """이미지 링크 추출"""
        text = "![이미지](image.png)"
        result, links = self.extractor.extract_markdown_links(text)
        self.assertEqual(len(links), 1)
        self.assertIn("![이미지](image.png)", links)

    def test_restore_links(self):
        """링크 복원"""
        text = "이것은 [링크](https://example.com) 입니다."
        extracted, _ = self.extractor.extract_markdown_links(text)
        restored = self.extractor.restore_markdown_links(extracted)
        self.assertEqual(restored, text)

    def test_link_protection_in_pipeline(self):
        """파이프라인에서 링크 보호 확인"""
        text = "[**볼드 링크**](https://example.com)"
        result = self.cleaner.clean_markdown(text)
        # 링크가 보존되어야 함
        self.assertIn("[**볼드 링크**](https://example.com)", result)

    def test_multiple_links(self):
        """여러 링크 추출 및 복원"""
        text = "[링크1](url1) 텍스트 [링크2](url2)"
        extracted, links = self.extractor.extract_markdown_links(text)
        self.assertEqual(len(links), 2)
        restored = self.extractor.restore_markdown_links(extracted)
        self.assertEqual(restored, text)

    def test_image_and_link_mixed(self):
        """이미지와 링크 혼합"""
        text = "![img](pic.png) 과 [link](url)"
        extracted, links = self.extractor.extract_markdown_links(text)
        self.assertEqual(len(links), 2)


class TestPageNumberCustomMax(unittest.TestCase):
    """커스텀 페이지 번호 범위 테스트 (v3.1)"""

    def test_default_max_100(self):
        """기본값 100 테스트"""
        cleaner = MarkdownCleaner()
        self.assertTrue(cleaner.is_likely_page_number("100"))
        self.assertFalse(cleaner.is_likely_page_number("101"))

    def test_custom_max_50(self):
        """커스텀 max=50 테스트"""
        cleaner = MarkdownCleaner(page_number_max=50)
        self.assertTrue(cleaner.is_likely_page_number("50"))
        self.assertFalse(cleaner.is_likely_page_number("51"))

    def test_custom_max_200(self):
        """커스텀 max=200 테스트"""
        cleaner = MarkdownCleaner(page_number_max=200)
        self.assertTrue(cleaner.is_likely_page_number("150"))
        self.assertFalse(cleaner.is_likely_page_number("201"))

    def test_custom_max_in_pipeline(self):
        """파이프라인에서 커스텀 max 적용"""
        cleaner = MarkdownCleaner(page_number_max=30)
        text = "내용\n25\n내용\n35\n"
        result = cleaner.clean_markdown(text)
        self.assertNotIn("\n25\n", result)
        self.assertIn("35", result)


class TestExtraPatterns(unittest.TestCase):
    """커스텀 패턴 테스트 (v3.1)"""

    def test_extra_pattern_simple(self):
        """단순 커스텀 패턴"""
        cleaner = MarkdownCleaner(extra_patterns=[r'^\s*\[제거\]\s*$'])
        self.assertTrue(cleaner.is_likely_page_number("[제거]"))
        self.assertFalse(cleaner.is_likely_page_number("[보존]"))

    def test_extra_pattern_regex(self):
        """정규식 커스텀 패턴"""
        cleaner = MarkdownCleaner(extra_patterns=[r'^\s*===+\s*$'])
        self.assertTrue(cleaner.is_likely_page_number("========"))
        self.assertFalse(cleaner.is_likely_page_number("== 텍스트 =="))

    def test_multiple_extra_patterns(self):
        """여러 커스텀 패턴"""
        cleaner = MarkdownCleaner(extra_patterns=[
            r'^\s*\[END\]\s*$',
            r'^\s*\[START\]\s*$'
        ])
        self.assertTrue(cleaner.is_likely_page_number("[END]"))
        self.assertTrue(cleaner.is_likely_page_number("[START]"))


class TestTableAlignment(unittest.TestCase):
    """테이블 정렬 테스트 (v3.1)"""

    def setUp(self):
        self.cleaner = MarkdownCleaner(align_tables=True)

    def test_simple_table_alignment(self):
        """단순 테이블 정렬"""
        table = "| 짧 | 긴 텍스트 |\n|---|---|\n| A | B |"
        result = self.cleaner.align_tables(table)
        lines = result.split('\n')
        self.assertEqual(len(lines), 3)

    def test_korean_width_calculation(self):
        """한글 너비 계산"""
        width = self.cleaner._get_display_width("한글")
        self.assertEqual(width, 4)  # 한글 2글자 = 4칸

    def test_mixed_width_calculation(self):
        """혼합 너비 계산"""
        width = self.cleaner._get_display_width("AB한글")
        self.assertEqual(width, 6)  # A(1) + B(1) + 한(2) + 글(2)

    def test_align_tables_disabled(self):
        """테이블 정렬 비활성화"""
        cleaner = MarkdownCleaner(align_tables=False)
        table = "| A | B |\n|---|---|\n| C | D |"
        result = cleaner.clean_markdown(table)
        # 정렬 안 함 (원본 유지)
        self.assertIn("| A | B |", result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
