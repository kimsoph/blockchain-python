# -*- coding: utf-8 -*-
"""
from-wiki 스킬 테스트
한글 인코딩 테스트 포함

실행: pytest .claude/skills/from-wiki/tests/test_wiki_api.py -v
"""

import sys
import os

# 스크립트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from wiki_api import WikipediaClient


class TestWikipediaClient:
    """WikipediaClient 클래스 테스트"""

    @pytest.fixture
    def client_ko(self):
        """한글 Wikipedia 클라이언트"""
        return WikipediaClient(lang='ko')

    @pytest.fixture
    def client_en(self):
        """영어 Wikipedia 클라이언트"""
        return WikipediaClient(lang='en')

    def test_init_korean(self, client_ko):
        """한글 클라이언트 초기화"""
        assert client_ko.lang == 'ko'
        assert client_ko.wiki is not None

    def test_init_english(self, client_en):
        """영어 클라이언트 초기화"""
        assert client_en.lang == 'en'
        assert client_en.wiki is not None

    def test_set_language(self, client_ko):
        """언어 변경"""
        client_ko.set_language('en')
        assert client_ko.lang == 'en'

    def test_search_korean(self, client_ko):
        """한글 검색 테스트"""
        results = client_ko.search("파이썬", limit=5)
        assert isinstance(results, list)
        # 결과가 있으면 구조 확인
        if results:
            assert 'title' in results[0]
            assert 'url' in results[0]
            # 한글이 포함되어 있는지 확인
            print(f"한글 검색 결과: {results[0]['title']}")

    def test_search_english(self, client_en):
        """영어 검색 테스트"""
        results = client_en.search("Python programming", limit=5)
        assert isinstance(results, list)
        if results:
            assert 'title' in results[0]

    def test_get_summary_korean(self, client_ko):
        """한글 요약 테스트"""
        summary = client_ko.get_summary("파이썬")
        # 문서가 존재하면 내용 확인
        if summary:
            assert isinstance(summary, str)
            assert len(summary) > 0
            print(f"한글 요약 (앞 100자): {summary[:100]}...")

    def test_get_summary_english(self, client_en):
        """영어 요약 테스트"""
        summary = client_en.get_summary("Python (programming language)")
        if summary:
            assert isinstance(summary, str)
            assert len(summary) > 0

    def test_get_summary_not_found(self, client_ko):
        """존재하지 않는 문서"""
        summary = client_ko.get_summary("이건절대존재하지않는문서제목12345")
        assert summary is None

    def test_to_markdown_korean(self, client_ko):
        """한글 마크다운 변환 테스트"""
        md = client_ko.to_markdown("파이썬", include_full=False)
        if md:
            assert "---" in md  # YAML frontmatter
            assert "source: wikipedia" in md
            assert "language: ko" in md
            assert "## 요약" in md
            print(f"마크다운 생성 성공 (길이: {len(md)})")

    def test_to_markdown_with_full(self, client_ko):
        """전문 포함 마크다운"""
        md = client_ko.to_markdown("파이썬", include_full=True)
        if md:
            assert "## 전문" in md

    def test_korean_encoding_in_search(self, client_ko):
        """한글 인코딩 테스트 - 검색"""
        # 다양한 한글 키워드 테스트
        korean_keywords = ["인공지능", "대한민국", "서울"]
        for keyword in korean_keywords:
            results = client_ko.search(keyword, limit=3)
            assert isinstance(results, list)
            print(f"'{keyword}' 검색: {len(results)}건")

    def test_korean_encoding_in_title(self, client_ko):
        """한글 인코딩 테스트 - 제목"""
        # 한글 제목으로 페이지 조회
        page = client_ko.get_page("대한민국")
        if page:
            assert "대한민국" in page.title or "한국" in page.title
            print(f"페이지 제목: {page.title}")
            print(f"URL: {page.fullurl}")


class TestCLI:
    """CLI 테스트"""

    def test_help(self):
        """도움말 출력"""
        import subprocess
        result = subprocess.run(
            [sys.executable,
             os.path.join(os.path.dirname(__file__), '..', 'scripts', 'wiki_api.py'),
             '--help'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        assert result.returncode == 0
        assert '--search' in result.stdout
        assert '--summary' in result.stdout
        assert '--lang' in result.stdout


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
