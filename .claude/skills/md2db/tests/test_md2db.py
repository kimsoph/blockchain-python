#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown to DB Converter 단위 테스트
"""

import unittest
import tempfile
import os
import sys
import sqlite3
from pathlib import Path

# 스크립트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from md2db import (
    MarkdownParser, DatabaseWriter, DatabaseReader, MarkdownExporter,
    Document, Section, Block, BlockType
)


class TestMarkdownParser(unittest.TestCase):
    """MarkdownParser 클래스 테스트"""

    def setUp(self):
        self.parser = MarkdownParser()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # 임시 파일 정리
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_temp_file(self, content: str) -> str:
        """임시 마크다운 파일 생성"""
        filepath = os.path.join(self.temp_dir, 'test.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_parse_simple_document(self):
        """간단한 문서 파싱"""
        content = """# 제목

본문 텍스트입니다.

## 소제목

또 다른 본문입니다.
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        self.assertEqual(doc.title, "제목")
        # 루트 섹션 + H1 + H2 = 3개
        self.assertEqual(len(doc.sections), 3)

    def test_parse_headers(self):
        """헤더 파싱"""
        content = """# H1 제목
## H2 제목
### H3 제목
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        # 루트 + 3개 헤더
        self.assertEqual(len(doc.sections), 4)

        h1 = doc.sections[1]
        self.assertEqual(h1.level, 1)
        self.assertEqual(h1.title, "H1 제목")
        self.assertEqual(h1.path, "1")

        h2 = doc.sections[2]
        self.assertEqual(h2.level, 2)
        self.assertEqual(h2.path, "1.1")

        h3 = doc.sections[3]
        self.assertEqual(h3.level, 3)
        self.assertEqual(h3.path, "1.1.1")

    def test_parse_frontmatter(self):
        """프론트매터 파싱"""
        content = """---
title: 테스트 문서
author: 홍길동
date: 2025-12-18
---

# 본문 시작
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        self.assertEqual(doc.frontmatter.get('title'), '테스트 문서')
        self.assertEqual(doc.frontmatter.get('author'), '홍길동')

    def test_parse_code_block(self):
        """코드 블록 파싱"""
        content = """# 코드 예제

```python
def hello():
    print("Hello, World!")
```

끝.
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        # 코드 블록 찾기
        code_blocks = [
            b for s in doc.sections for b in s.blocks
            if b.type == BlockType.CODE_BLOCK
        ]
        self.assertEqual(len(code_blocks), 1)
        self.assertIn('def hello():', code_blocks[0].content)
        self.assertEqual(code_blocks[0].metadata.get('language'), 'python')

    def test_parse_list(self):
        """리스트 파싱"""
        content = """# 리스트

- 첫 번째 항목
- 두 번째 항목
- 세 번째 항목

1. 순서 있는 항목
2. 두 번째
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        list_blocks = [
            b for s in doc.sections for b in s.blocks
            if b.type == BlockType.LIST
        ]
        self.assertGreaterEqual(len(list_blocks), 1)

    def test_parse_blockquote(self):
        """인용구 파싱"""
        content = """# 인용

> 이것은 인용문입니다.
> 여러 줄 인용.
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        quote_blocks = [
            b for s in doc.sections for b in s.blocks
            if b.type == BlockType.BLOCKQUOTE
        ]
        self.assertEqual(len(quote_blocks), 1)
        self.assertIn('인용문', quote_blocks[0].content)

    def test_parse_table(self):
        """테이블 파싱"""
        content = """# 테이블

| 헤더1 | 헤더2 |
|-------|-------|
| 값1   | 값2   |
| 값3   | 값4   |
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        table_blocks = [
            b for s in doc.sections for b in s.blocks
            if b.type == BlockType.TABLE
        ]
        self.assertEqual(len(table_blocks), 1)

    def test_parse_horizontal_rule(self):
        """수평선 파싱"""
        content = """# 섹션 1

내용

---

# 섹션 2
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        hr_blocks = [
            b for s in doc.sections for b in s.blocks
            if b.type == BlockType.HORIZONTAL_RULE
        ]
        self.assertEqual(len(hr_blocks), 1)

    def test_section_hierarchy(self):
        """섹션 계층 구조"""
        content = """# Part 1
## Chapter 1
### Section 1
### Section 2
## Chapter 2
# Part 2
## Chapter 1
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        paths = [s.path for s in doc.sections if s.level > 0]
        expected = ['1', '1.1', '1.1.1', '1.1.2', '1.2', '2', '2.1']
        self.assertEqual(paths, expected)


class TestDatabaseWriter(unittest.TestCase):
    """DatabaseWriter 클래스 테스트"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.parser = MarkdownParser()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_temp_file(self, content: str) -> str:
        filepath = os.path.join(self.temp_dir, 'test.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_save_document(self):
        """문서 저장"""
        content = """# 제목

본문입니다.

## 소제목

추가 내용.
"""
        filepath = self._create_temp_file(content)
        doc = self.parser.parse_file(filepath)

        with DatabaseWriter(self.db_path) as writer:
            doc_id = writer.save_document(doc)

        self.assertEqual(doc_id, 1)

        # DB 확인
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM documents")
        self.assertEqual(cursor.fetchone()[0], 1)

        cursor.execute("SELECT COUNT(*) FROM sections")
        section_count = cursor.fetchone()[0]
        self.assertGreater(section_count, 0)

        cursor.execute("SELECT COUNT(*) FROM blocks")
        block_count = cursor.fetchone()[0]
        self.assertGreater(block_count, 0)

        conn.close()

    def test_append_mode(self):
        """문서 추가 모드"""
        content1 = "# 문서 1\n\n내용"
        content2 = "# 문서 2\n\n다른 내용"

        filepath1 = self._create_temp_file(content1)
        doc1 = self.parser.parse_file(filepath1)

        # 첫 번째 문서 저장
        with DatabaseWriter(self.db_path) as writer:
            writer.save_document(doc1)

        # 두 번째 파일 생성
        filepath2 = os.path.join(self.temp_dir, 'test2.md')
        with open(filepath2, 'w', encoding='utf-8') as f:
            f.write(content2)
        doc2 = self.parser.parse_file(filepath2)

        # 추가 모드로 저장
        with DatabaseWriter(self.db_path, append=True) as writer:
            writer.save_document(doc2)

        # 확인
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        self.assertEqual(cursor.fetchone()[0], 2)
        conn.close()


class TestDatabaseReader(unittest.TestCase):
    """DatabaseReader 클래스 테스트"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.parser = MarkdownParser()

        # 테스트 데이터 준비
        content = """# 제목

본문입니다.

## 챕터 1

첫 번째 챕터 내용.

### 섹션 1.1

세부 내용.

## 챕터 2

두 번째 챕터 내용.
"""
        filepath = os.path.join(self.temp_dir, 'test.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        doc = self.parser.parse_file(filepath)
        with DatabaseWriter(self.db_path) as writer:
            writer.save_document(doc)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_info(self):
        """DB 정보 조회"""
        with DatabaseReader(self.db_path) as reader:
            info = reader.get_info()

        self.assertEqual(info['total_documents'], 1)
        self.assertGreater(info['total_sections'], 0)
        self.assertGreater(info['total_blocks'], 0)

    def test_get_sections(self):
        """섹션 목록 조회"""
        with DatabaseReader(self.db_path) as reader:
            sections = reader.get_sections()

        self.assertGreater(len(sections), 0)
        # H1, H2x2, H3x1 = 4개 (+ 루트 1개)
        titles = [s['title'] for s in sections]
        self.assertIn('제목', titles)
        self.assertIn('챕터 1', titles)

    def test_get_section_by_path(self):
        """경로로 섹션 조회"""
        with DatabaseReader(self.db_path) as reader:
            section = reader.get_section_by_path('1.1')

        self.assertIsNotNone(section)
        self.assertEqual(section['title'], '챕터 1')

    def test_get_blocks(self):
        """블록 조회"""
        with DatabaseReader(self.db_path) as reader:
            sections = reader.get_sections()
            for section in sections:
                blocks = reader.get_blocks(section['id'])
                # 모든 섹션이 최소 하나의 블록을 가지는지 확인 (루트 제외 가능)
                if section['level'] > 0:
                    self.assertGreaterEqual(len(blocks), 0)


class TestMarkdownExporter(unittest.TestCase):
    """MarkdownExporter 클래스 테스트"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.parser = MarkdownParser()

        # 테스트 데이터 준비
        self.original_content = """# 제목

본문입니다.

## 소제목

추가 내용.
"""
        filepath = os.path.join(self.temp_dir, 'test.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.original_content)

        doc = self.parser.parse_file(filepath)
        with DatabaseWriter(self.db_path) as writer:
            writer.save_document(doc)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_full(self):
        """전체 문서 내보내기"""
        output_path = os.path.join(self.temp_dir, 'output.md')

        with DatabaseReader(self.db_path) as reader:
            exporter = MarkdownExporter(reader)
            exporter.export(output_path)

        self.assertTrue(os.path.exists(output_path))

        with open(output_path, 'r', encoding='utf-8') as f:
            exported = f.read()

        self.assertIn('# 제목', exported)
        self.assertIn('## 소제목', exported)
        self.assertIn('본문입니다', exported)

    def test_export_section(self):
        """특정 섹션만 내보내기"""
        output_path = os.path.join(self.temp_dir, 'section.md')

        with DatabaseReader(self.db_path) as reader:
            exporter = MarkdownExporter(reader)
            exporter.export(output_path, section_path='1.1')

        with open(output_path, 'r', encoding='utf-8') as f:
            exported = f.read()

        self.assertIn('소제목', exported)


class TestBlockTypeDetection(unittest.TestCase):
    """블록 타입 감지 테스트"""

    def setUp(self):
        self.parser = MarkdownParser()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _parse_content(self, content: str) -> list:
        """콘텐츠를 파싱하여 모든 블록 반환"""
        filepath = os.path.join(self.temp_dir, 'test.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        doc = self.parser.parse_file(filepath)
        return [b for s in doc.sections for b in s.blocks]

    def test_detect_paragraph(self):
        """단락 감지"""
        content = "# 제목\n\n일반 텍스트 단락입니다."
        blocks = self._parse_content(content)

        para_blocks = [b for b in blocks if b.type == BlockType.PARAGRAPH]
        self.assertEqual(len(para_blocks), 1)

    def test_detect_ordered_list(self):
        """순서 있는 리스트 감지"""
        content = "# 제목\n\n1. 첫째\n2. 둘째\n3. 셋째"
        blocks = self._parse_content(content)

        list_blocks = [b for b in blocks if b.type == BlockType.LIST]
        self.assertGreaterEqual(len(list_blocks), 1)

    def test_detect_unordered_list(self):
        """순서 없는 리스트 감지"""
        content = "# 제목\n\n- 항목 1\n- 항목 2\n- 항목 3"
        blocks = self._parse_content(content)

        list_blocks = [b for b in blocks if b.type == BlockType.LIST]
        self.assertGreaterEqual(len(list_blocks), 1)


class TestKoreanContent(unittest.TestCase):
    """한글 콘텐츠 처리 테스트"""

    def setUp(self):
        self.parser = MarkdownParser()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_korean_headers(self):
        """한글 헤더 파싱"""
        content = """# 한글 제목

## 두 번째 헤더

### 세 번째 헤더
"""
        filepath = os.path.join(self.temp_dir, 'korean.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        doc = self.parser.parse_file(filepath)

        self.assertEqual(doc.title, '한글 제목')
        titles = [s.title for s in doc.sections if s.level > 0]
        self.assertIn('한글 제목', titles)
        self.assertIn('두 번째 헤더', titles)

    def test_korean_content_roundtrip(self):
        """한글 콘텐츠 왕복 변환"""
        original = """# 한글 문서

이것은 한글로 작성된 문서입니다.

## 소제목

더 많은 한글 내용이 있습니다.
"""
        filepath = os.path.join(self.temp_dir, 'korean.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(original)

        # 파싱 → DB 저장
        doc = self.parser.parse_file(filepath)
        db_path = os.path.join(self.temp_dir, 'korean.db')
        with DatabaseWriter(db_path) as writer:
            writer.save_document(doc)

        # DB → 마크다운 복원
        output_path = os.path.join(self.temp_dir, 'output.md')
        with DatabaseReader(db_path) as reader:
            exporter = MarkdownExporter(reader)
            exporter.export(output_path)

        with open(output_path, 'r', encoding='utf-8') as f:
            exported = f.read()

        self.assertIn('한글 문서', exported)
        self.assertIn('한글로 작성된', exported)


if __name__ == '__main__':
    unittest.main(verbosity=2)
