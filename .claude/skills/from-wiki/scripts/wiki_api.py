# -*- coding: utf-8 -*-
"""
Wikipedia API Client for Claude Code
영어/한글 Wikipedia 검색 및 문서 조회 스킬

Author: Claude Code
Version: 1.0.0
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# 한글 출력을 위한 인코딩 설정 (Windows 콘솔)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    print("requests 패키지가 필요합니다: pip install requests")
    sys.exit(1)

try:
    import wikipediaapi
except ImportError:
    print("Wikipedia-API 패키지가 필요합니다: pip install Wikipedia-API")
    sys.exit(1)


class WikipediaClient:
    """Wikipedia API 클라이언트

    검색: MediaWiki OpenSearch API (requests)
    요약/전문: Wikipedia-API 라이브러리
    """

    SEARCH_URL = "https://{lang}.wikipedia.org/w/api.php"
    USER_AGENT = "from-wiki-skill/1.0 (claude-code; https://github.com/anthropics/claude-code)"

    # 기본 저장 경로 (Vault 기준)
    DEFAULT_OUTPUT_DIR = "0_Inbox"

    def __init__(self, lang: str = 'ko', vault_path: Optional[str] = None):
        """
        Args:
            lang: 언어 코드 ('ko' 한글, 'en' 영어)
            vault_path: Obsidian Vault 경로 (기본: 스크립트 상위 4단계)
        """
        self.lang = lang

        # Wikipedia-API 초기화
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=self.USER_AGENT,
            language=lang
        )

        # requests 세션 초기화 (검색용)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json',
            'Accept-Charset': 'utf-8'
        })

        # Vault 경로 설정
        if vault_path:
            self.vault_path = Path(vault_path)
        else:
            # 스크립트 위치에서 Vault 루트 추정
            # .claude/skills/from-wiki/scripts/wiki_api.py → 4단계 상위
            self.vault_path = Path(__file__).parent.parent.parent.parent.parent

        self.output_dir = self.vault_path / self.DEFAULT_OUTPUT_DIR

    def set_language(self, lang: str) -> None:
        """언어 변경"""
        self.lang = lang
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=self.USER_AGENT,
            language=lang
        )

    def search(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """키워드 검색 → 문서 목록

        MediaWiki OpenSearch API 사용

        Args:
            query: 검색 키워드
            limit: 최대 결과 수 (기본 10)

        Returns:
            [{'title': '제목', 'description': '설명', 'url': 'URL'}, ...]
        """
        url = self.SEARCH_URL.format(lang=self.lang)
        params = {
            'action': 'opensearch',
            'search': query,
            'limit': limit,
            'namespace': 0,
            'format': 'json'
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.encoding = 'utf-8'
            response.raise_for_status()

            # OpenSearch 응답: [query, [titles], [descriptions], [urls]]
            data = response.json()

            if len(data) < 4:
                return []

            titles = data[1]
            descriptions = data[2]
            urls = data[3]

            results = []
            for i in range(len(titles)):
                results.append({
                    'title': titles[i],
                    'description': descriptions[i] if i < len(descriptions) else '',
                    'url': urls[i] if i < len(urls) else ''
                })

            return results

        except requests.exceptions.RequestException as e:
            print(f"검색 오류: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return []

    def get_page(self, title: str) -> Optional[wikipediaapi.WikipediaPage]:
        """페이지 객체 반환

        Args:
            title: 문서 제목 (정확한 제목)

        Returns:
            WikipediaPage 객체 또는 None
        """
        page = self.wiki.page(title)
        if page.exists():
            return page
        return None

    def get_summary(self, title: str) -> Optional[str]:
        """문서 요약 반환

        Args:
            title: 문서 제목

        Returns:
            요약 텍스트 또는 None
        """
        page = self.get_page(title)
        if page:
            return page.summary
        return None

    def get_full_text(self, title: str) -> Optional[str]:
        """문서 전문 반환

        Args:
            title: 문서 제목

        Returns:
            전체 텍스트 또는 None
        """
        page = self.get_page(title)
        if page:
            return page.text
        return None

    def get_sections(self, title: str) -> List[Dict[str, Any]]:
        """문서 섹션 구조 반환

        Args:
            title: 문서 제목

        Returns:
            [{'title': '섹션명', 'level': 레벨, 'text': '내용'}, ...]
        """
        page = self.get_page(title)
        if not page:
            return []

        def extract_sections(sections, level=1):
            result = []
            for section in sections:
                result.append({
                    'title': section.title,
                    'level': level,
                    'text': section.text
                })
                # 하위 섹션 재귀 처리
                result.extend(extract_sections(section.sections, level + 1))
            return result

        return extract_sections(page.sections)

    def to_markdown(
        self,
        title: str,
        include_full: bool = False,
        include_sections: bool = False
    ) -> Optional[str]:
        """마크다운 형식으로 변환

        Args:
            title: 문서 제목
            include_full: 전문 포함 여부
            include_sections: 섹션 구조 포함 여부

        Returns:
            마크다운 문자열 또는 None
        """
        page = self.get_page(title)
        if not page:
            return None

        # YAML Frontmatter
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lang_name = '한글' if self.lang == 'ko' else '영어' if self.lang == 'en' else self.lang

        md_parts = [
            "---",
            f"title: \"{page.title}\"",
            "source: wikipedia",
            f"language: {self.lang}",
            f"url: {page.fullurl}",
            f"retrieved: {now}",
            "---",
            "",
            f"# {page.title}",
            "",
            "## 요약",
            "",
            page.summary,
            ""
        ]

        # 전문 또는 섹션 구조 포함
        if include_full:
            md_parts.extend([
                "## 전문",
                "",
                page.text,
                ""
            ])
        elif include_sections:
            sections = self.get_sections(title)
            if sections:
                md_parts.extend([
                    "## 목차",
                    ""
                ])
                for section in sections:
                    indent = "  " * (section['level'] - 1)
                    md_parts.append(f"{indent}- {section['title']}")
                md_parts.append("")

                md_parts.extend([
                    "## 상세 내용",
                    ""
                ])
                for section in sections:
                    header_level = "#" * (section['level'] + 1)
                    md_parts.append(f"{header_level} {section['title']}")
                    md_parts.append("")
                    if section['text']:
                        md_parts.append(section['text'])
                        md_parts.append("")

        # 출처
        md_parts.extend([
            "---",
            f"*출처: [Wikipedia ({lang_name})]({page.fullurl})*"
        ])

        return "\n".join(md_parts)

    def save_markdown(
        self,
        title: str,
        output_path: Optional[str] = None,
        include_full: bool = False,
        include_sections: bool = False
    ) -> Optional[str]:
        """마크다운 파일로 저장

        Args:
            title: 문서 제목
            output_path: 저장 경로 (None이면 기본 경로 사용)
            include_full: 전문 포함 여부
            include_sections: 섹션 구조 포함 여부

        Returns:
            저장된 파일 경로 또는 None
        """
        content = self.to_markdown(title, include_full, include_sections)
        if not content:
            print(f"문서를 찾을 수 없습니다: {title}")
            return None

        # 파일 경로 결정
        if output_path:
            file_path = Path(output_path)
            # 상대 경로면 Vault 기준으로 변환
            if not file_path.is_absolute():
                file_path = self.vault_path / file_path
        else:
            # 기본 경로: 0_Inbox/wiki_{제목}.md
            safe_title = title.replace('/', '_').replace('\\', '_').replace(':', '_')
            filename = f"wiki_{safe_title}.md"
            file_path = self.output_dir / filename

        # 디렉토리 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 파일 저장
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"저장 완료: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"저장 실패: {e}")
            return None


def print_search_results(results: List[Dict[str, str]]) -> None:
    """검색 결과 출력"""
    if not results:
        print("검색 결과가 없습니다.")
        return

    print(f"\n검색 결과 ({len(results)}건):\n")
    for i, item in enumerate(results, 1):
        print(f"{i}. {item['title']}")
        if item['description']:
            print(f"   {item['description'][:80]}...")
        print(f"   {item['url']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Wikipedia 검색 및 문서 조회 스킬',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 한글 위키 검색
  python wiki_api.py --search "인공지능"

  # 영어 위키 요약
  python wiki_api.py --summary "Artificial intelligence" --lang en

  # 전문 가져오기 + 저장
  python wiki_api.py --full "파이썬" --save

  # 사용자 지정 경로로 저장
  python wiki_api.py --summary "Python" --lang en --output 3_Resources/python.md
"""
    )

    # 작업 선택 (상호 배타적)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--search', '-s', metavar='QUERY',
                        help='키워드로 문서 검색')
    action.add_argument('--summary', '-m', metavar='TITLE',
                        help='문서 요약 가져오기')
    action.add_argument('--full', '-f', metavar='TITLE',
                        help='문서 전문 가져오기')
    action.add_argument('--sections', metavar='TITLE',
                        help='문서 섹션 구조 가져오기')

    # 옵션
    parser.add_argument('--lang', '-l', default='ko', choices=['ko', 'en'],
                        help='언어 선택 (기본: ko)')
    parser.add_argument('--limit', '-n', type=int, default=10,
                        help='검색 결과 수 (기본: 10)')
    parser.add_argument('--save', action='store_true',
                        help='기본 경로(0_Inbox/)에 마크다운 저장')
    parser.add_argument('--output', '-o', metavar='PATH',
                        help='저장 경로 지정')
    parser.add_argument('--json', action='store_true',
                        help='JSON 형식으로 출력')

    args = parser.parse_args()

    # 클라이언트 초기화
    client = WikipediaClient(lang=args.lang)

    # 검색
    if args.search:
        results = client.search(args.search, limit=args.limit)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print_search_results(results)

    # 요약
    elif args.summary:
        if args.save or args.output:
            path = client.save_markdown(
                args.summary,
                output_path=args.output,
                include_full=False
            )
            if not path:
                sys.exit(1)
        else:
            summary = client.get_summary(args.summary)
            if summary:
                if args.json:
                    print(json.dumps({'title': args.summary, 'summary': summary},
                                     ensure_ascii=False, indent=2))
                else:
                    print(f"\n# {args.summary}\n")
                    print(summary)
            else:
                print(f"문서를 찾을 수 없습니다: {args.summary}")
                sys.exit(1)

    # 전문
    elif args.full:
        if args.save or args.output:
            path = client.save_markdown(
                args.full,
                output_path=args.output,
                include_full=True
            )
            if not path:
                sys.exit(1)
        else:
            content = client.to_markdown(args.full, include_full=True)
            if content:
                print(content)
            else:
                print(f"문서를 찾을 수 없습니다: {args.full}")
                sys.exit(1)

    # 섹션
    elif args.sections:
        if args.save or args.output:
            path = client.save_markdown(
                args.sections,
                output_path=args.output,
                include_sections=True
            )
            if not path:
                sys.exit(1)
        else:
            sections = client.get_sections(args.sections)
            if sections:
                if args.json:
                    print(json.dumps(sections, ensure_ascii=False, indent=2))
                else:
                    print(f"\n# {args.sections} - 섹션 구조\n")
                    for section in sections:
                        indent = "  " * (section['level'] - 1)
                        print(f"{indent}- {section['title']}")
            else:
                print(f"문서를 찾을 수 없습니다: {args.sections}")
                sys.exit(1)


if __name__ == '__main__':
    main()
