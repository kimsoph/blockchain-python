# -*- coding: utf-8 -*-
"""
FRED 메타데이터 DB 관리
미국 연방준비제도 FRED API 시리즈 정보를 SQLite로 관리

Author: Claude Code
Version: 1.0.0
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# 한글 출력 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    print("requests 패키지 필요: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


class FredMetaDB:
    """FRED 메타데이터 DB 관리 클래스"""

    BASE_URL = "https://api.stlouisfed.org/fred"

    SCHEMA = """
    -- 시리즈 목록
    CREATE TABLE IF NOT EXISTS series (
        id INTEGER PRIMARY KEY,
        series_id TEXT UNIQUE NOT NULL,
        title TEXT,
        frequency TEXT,
        frequency_short TEXT,
        units TEXT,
        seasonal_adjustment TEXT,
        observation_start TEXT,
        observation_end TEXT,
        popularity INTEGER,
        notes TEXT,
        last_updated TEXT,
        updated_at TEXT
    );

    -- 카테고리
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY,
        category_id INTEGER UNIQUE NOT NULL,
        name TEXT,
        parent_id INTEGER,
        updated_at TEXT
    );

    -- 인기 시리즈 (빠른 접근용)
    CREATE TABLE IF NOT EXISTS popular_series (
        id INTEGER PRIMARY KEY,
        series_id TEXT UNIQUE NOT NULL,
        title TEXT,
        category TEXT,
        description_kr TEXT,
        updated_at TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_series_id ON series(series_id);
    CREATE INDEX IF NOT EXISTS idx_series_title ON series(title);
    CREATE INDEX IF NOT EXISTS idx_series_popularity ON series(popularity DESC);
    CREATE INDEX IF NOT EXISTS idx_popular_series_id ON popular_series(series_id);
    CREATE INDEX IF NOT EXISTS idx_popular_category ON popular_series(category);

    -- FTS5 전문검색
    CREATE VIRTUAL TABLE IF NOT EXISTS series_fts USING fts5(
        title, notes, units,
        content='series',
        content_rowid='id'
    );

    -- FTS 트리거 (series)
    CREATE TRIGGER IF NOT EXISTS series_ai AFTER INSERT ON series BEGIN
        INSERT INTO series_fts(rowid, title, notes, units)
        VALUES (new.id, new.title, new.notes, new.units);
    END;

    CREATE TRIGGER IF NOT EXISTS series_ad AFTER DELETE ON series BEGIN
        INSERT INTO series_fts(series_fts, rowid, title, notes, units)
        VALUES ('delete', old.id, old.title, old.notes, old.units);
    END;

    CREATE TRIGGER IF NOT EXISTS series_au AFTER UPDATE ON series BEGIN
        INSERT INTO series_fts(series_fts, rowid, title, notes, units)
        VALUES ('delete', old.id, old.title, old.notes, old.units);
        INSERT INTO series_fts(rowid, title, notes, units)
        VALUES (new.id, new.title, new.notes, new.units);
    END;
    """

    # 기본 검색 키워드
    DEFAULT_KEYWORDS = [
        'treasury', 'interest rate', 'unemployment', 'inflation',
        'GDP', 'exchange rate', 'federal funds', 'CPI', 'PCE',
        'employment', 'retail sales', 'housing', 'S&P 500'
    ]

    # 주요 카테고리
    MAIN_CATEGORIES = {
        32991: 'Interest Rates',
        10: 'Population, Employment, & Labor Markets',
        32455: 'Prices',
        18: 'National Accounts',
        32992: 'Exchange Rates',
        32145: 'Money, Banking, & Finance',
    }

    # 인기 시리즈 (하드코딩)
    POPULAR_SERIES = {
        'DGS1': ('1-Year Treasury Constant Maturity Rate', '금리', '1년 국채 금리'),
        'DGS2': ('2-Year Treasury Constant Maturity Rate', '금리', '2년 국채 금리'),
        'DGS3': ('3-Year Treasury Constant Maturity Rate', '금리', '3년 국채 금리'),
        'DGS5': ('5-Year Treasury Constant Maturity Rate', '금리', '5년 국채 금리'),
        'DGS7': ('7-Year Treasury Constant Maturity Rate', '금리', '7년 국채 금리'),
        'DGS10': ('10-Year Treasury Constant Maturity Rate', '금리', '10년 국채 금리'),
        'DGS20': ('20-Year Treasury Constant Maturity Rate', '금리', '20년 국채 금리'),
        'DGS30': ('30-Year Treasury Constant Maturity Rate', '금리', '30년 국채 금리'),
        'FEDFUNDS': ('Federal Funds Effective Rate', '금리', '연방기금금리'),
        'DFEDTARU': ('Federal Funds Target Range - Upper Limit', '금리', '연방기금 목표금리 상한'),
        'DFEDTARL': ('Federal Funds Target Range - Lower Limit', '금리', '연방기금 목표금리 하한'),
        'T10Y2Y': ('10-Year Treasury Constant Maturity Minus 2-Year', '금리', '10년-2년 금리 스프레드'),
        'T10Y3M': ('10-Year Treasury Constant Maturity Minus 3-Month', '금리', '10년-3개월 금리 스프레드'),
        'UNRATE': ('Unemployment Rate', '고용', '실업률'),
        'PAYEMS': ('All Employees, Total Nonfarm', '고용', '비농업 고용자 수'),
        'ICSA': ('Initial Claims', '고용', '실업수당 청구건수'),
        'CPIAUCSL': ('Consumer Price Index for All Urban Consumers', '물가', '소비자물가지수(CPI)'),
        'CPILFESL': ('CPI Less Food and Energy', '물가', '근원 CPI'),
        'PCEPI': ('Personal Consumption Expenditures: Chain-type Price Index', '물가', 'PCE 물가지수'),
        'PCEPILFE': ('PCE Excluding Food and Energy', '물가', '근원 PCE'),
        'GDP': ('Gross Domestic Product', 'GDP', '명목 GDP'),
        'GDPC1': ('Real Gross Domestic Product', 'GDP', '실질 GDP'),
        'A191RL1Q225SBEA': ('Real GDP Growth Rate', 'GDP', '실질 GDP 성장률(분기)'),
        'DEXKOUS': ('South Korean Won to U.S. Dollar Spot Exchange Rate', '환율', '원/달러 환율'),
        'DEXJPUS': ('Japanese Yen to U.S. Dollar Spot Exchange Rate', '환율', '엔/달러 환율'),
        'DEXUSEU': ('U.S. Dollars to Euro Spot Exchange Rate', '환율', '유로/달러 환율'),
        'DEXCHUS': ('Chinese Yuan to U.S. Dollar Spot Exchange Rate', '환율', '위안/달러 환율'),
        'SP500': ('S&P 500', '주식', 'S&P 500 지수'),
        'NASDAQCOM': ('NASDAQ Composite Index', '주식', '나스닥 종합지수'),
        'VIXCLS': ('CBOE Volatility Index: VIX', '주식', 'VIX 변동성 지수'),
        'M2SL': ('M2', '통화', 'M2 통화량'),
        'WALCL': ('Assets: Total Assets: Total Assets', '통화', '연준 총자산'),
        'HOUST': ('Housing Starts: Total', '주택', '주택착공건수'),
        'HSN1F': ('New One Family Houses Sold', '주택', '신규주택판매'),
        'RSAFS': ('Advance Retail Sales: Retail Trade', '소비', '소매판매'),
        'UMCSENT': ('University of Michigan: Consumer Sentiment', '심리', '미시간대 소비자심리지수'),
    }

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent / 'data'
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / 'fred_meta.db')

        self.db_path = db_path
        self.conn = None
        self.api_key = self._load_api_key()

    def _load_api_key(self) -> str:
        """API 키 로드"""
        env_paths = [
            Path('.claude/.env'),
            Path('.env'),
        ]
        if load_dotenv:
            for p in env_paths:
                if p.exists():
                    load_dotenv(p)
                    break
        return os.getenv('FRED_API_KEY', '')

    def connect(self) -> sqlite3.Connection:
        """DB 연결"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_db(self):
        """DB 초기화 (스키마 생성)"""
        conn = self.connect()
        conn.executescript(self.SCHEMA)
        conn.commit()
        print(f"DB 초기화 완료: {self.db_path}")
        return True

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any] = None
    ) -> Dict:
        """
        FRED API 요청

        Args:
            endpoint: API 엔드포인트 (series/search, series 등)
            params: 요청 파라미터

        Returns:
            API 응답 데이터
        """
        if not self.api_key:
            return {'error': 'API 키가 설정되지 않았습니다.'}

        url = f"{self.BASE_URL}/{endpoint}"

        request_params = {
            'api_key': self.api_key,
            'file_type': 'json'
        }
        if params:
            request_params.update(params)

        try:
            response = requests.get(url, params=request_params, timeout=30)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'error': f'HTTP {response.status_code}',
                    'message': response.text[:500]
                }
        except requests.exceptions.Timeout:
            return {'error': 'TIMEOUT', 'message': '요청 시간 초과'}
        except requests.exceptions.RequestException as e:
            return {'error': 'REQUEST_ERROR', 'message': str(e)}
        except Exception as e:
            return {'error': 'ERROR', 'message': str(e)}

    def sync_series_by_search(self, keyword: str, force: bool = False) -> int:
        """
        키워드 기반 시리즈 동기화

        Args:
            keyword: 검색 키워드
            force: 강제 동기화 여부

        Returns:
            저장된 시리즈 수
        """
        if not self.api_key:
            print("FRED_API_KEY가 설정되지 않았습니다.")
            return 0

        self.init_db()
        conn = self.connect()

        print(f"'{keyword}' 시리즈 검색 중...")

        # API 호출
        result = self._make_request('series/search', {
            'search_text': keyword,
            'limit': 1000,
            'order_by': 'popularity',
            'sort_order': 'desc'
        })

        if 'error' in result:
            print(f"API 오류: {result.get('error')} - {result.get('message', '')}")
            return 0

        seriess = result.get('seriess', [])
        if not seriess:
            print(f"'{keyword}' 검색 결과가 없습니다.")
            return 0

        now = datetime.now().isoformat()
        saved_count = 0

        for item in seriess:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO series
                    (series_id, title, frequency, frequency_short, units,
                     seasonal_adjustment, observation_start, observation_end,
                     popularity, notes, last_updated, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('id', ''),
                    item.get('title', ''),
                    item.get('frequency', ''),
                    item.get('frequency_short', ''),
                    item.get('units', ''),
                    item.get('seasonal_adjustment', ''),
                    item.get('observation_start', ''),
                    item.get('observation_end', ''),
                    item.get('popularity', 0),
                    item.get('notes', ''),
                    item.get('last_updated', ''),
                    now
                ))
                saved_count += 1
            except Exception as e:
                print(f"  저장 실패 [{item.get('id')}]: {e}")

        conn.commit()
        print(f"'{keyword}': {saved_count}개 시리즈 저장")
        return saved_count

    def sync_popular_series(self, force: bool = False) -> int:
        """
        인기 시리즈 동기화 (하드코딩 목록)

        Args:
            force: 강제 동기화 여부

        Returns:
            저장된 시리즈 수
        """
        if not self.api_key:
            print("FRED_API_KEY가 설정되지 않았습니다.")
            return 0

        self.init_db()
        conn = self.connect()

        # 마지막 업데이트 확인
        if not force:
            try:
                cursor = conn.execute(
                    "SELECT MAX(updated_at) FROM popular_series"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    last_update = datetime.fromisoformat(row[0])
                    if datetime.now() - last_update < timedelta(days=1):
                        print("인기 시리즈 목록이 최신 상태입니다 (1일 이내 업데이트)")
                        cursor = conn.execute("SELECT COUNT(*) FROM popular_series")
                        return cursor.fetchone()[0]
            except Exception:
                pass

        print("인기 시리즈 동기화 중...")
        now = datetime.now().isoformat()
        saved_count = 0

        # 기존 데이터 삭제
        conn.execute("DELETE FROM popular_series")

        for series_id, (title, category, desc_kr) in self.POPULAR_SERIES.items():
            # API에서 최신 정보 가져오기
            result = self._make_request('series', {'series_id': series_id})

            if 'seriess' in result and result['seriess']:
                api_info = result['seriess'][0]
                title = api_info.get('title', title)

            conn.execute("""
                INSERT OR REPLACE INTO popular_series
                (series_id, title, category, description_kr, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (series_id, title, category, desc_kr, now))

            # 시리즈 테이블에도 추가
            if 'seriess' in result and result['seriess']:
                api_info = result['seriess'][0]
                conn.execute("""
                    INSERT OR REPLACE INTO series
                    (series_id, title, frequency, frequency_short, units,
                     seasonal_adjustment, observation_start, observation_end,
                     popularity, notes, last_updated, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    api_info.get('id', series_id),
                    api_info.get('title', title),
                    api_info.get('frequency', ''),
                    api_info.get('frequency_short', ''),
                    api_info.get('units', ''),
                    api_info.get('seasonal_adjustment', ''),
                    api_info.get('observation_start', ''),
                    api_info.get('observation_end', ''),
                    api_info.get('popularity', 0),
                    api_info.get('notes', ''),
                    api_info.get('last_updated', ''),
                    now
                ))

            saved_count += 1

        conn.commit()
        print(f"인기 시리즈 {saved_count}개 저장 완료")
        return saved_count

    def sync_all(self, force: bool = False) -> Dict[str, int]:
        """
        전체 동기화 (기본 키워드 + 인기 시리즈)

        Args:
            force: 강제 동기화 여부

        Returns:
            동기화 결과 {keyword: count, ...}
        """
        results = {}

        # 인기 시리즈 먼저
        results['popular'] = self.sync_popular_series(force=force)

        # 기본 키워드별 동기화
        for keyword in self.DEFAULT_KEYWORDS:
            count = self.sync_series_by_search(keyword, force=force)
            results[keyword] = count

        total = sum(results.values())
        print(f"\n전체 동기화 완료: 총 {total}개 시리즈")
        return results

    def search_series(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        LIKE 검색으로 시리즈 검색

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT series_id, title, frequency_short, units, popularity,
                   observation_start, observation_end
            FROM series
            WHERE series_id LIKE ? OR title LIKE ? OR notes LIKE ?
            ORDER BY popularity DESC
            LIMIT ?
        """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit))

        return [dict(row) for row in cursor.fetchall()]

    def search_series_fts(self, query: str, limit: int = 50) -> List[Dict]:
        """
        FTS5 전문 검색으로 시리즈 검색

        Args:
            query: 검색 쿼리
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        try:
            cursor = conn.execute("""
                SELECT s.series_id, s.title, s.frequency_short, s.units,
                       s.popularity, s.observation_start, s.observation_end
                FROM series_fts f
                JOIN series s ON f.rowid = s.id
                WHERE series_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return self.search_series(query, limit=limit)

    def get_series_info(self, series_id: str) -> Optional[Dict]:
        """
        시리즈 정보 조회

        Args:
            series_id: 시리즈 ID

        Returns:
            시리즈 정보
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT * FROM series WHERE series_id = ?
        """, (series_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_popular_series(self, category: str = None) -> List[Dict]:
        """
        인기 시리즈 목록 조회

        Args:
            category: 카테고리 필터 (선택)

        Returns:
            인기 시리즈 목록
        """
        conn = self.connect()

        if category:
            cursor = conn.execute("""
                SELECT series_id, title, category, description_kr
                FROM popular_series
                WHERE category = ?
                ORDER BY series_id
            """, (category,))
        else:
            cursor = conn.execute("""
                SELECT series_id, title, category, description_kr
                FROM popular_series
                ORDER BY category, series_id
            """)

        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """DB 통계 조회"""
        conn = self.connect()

        stats = {}

        cursor = conn.execute("SELECT COUNT(*) FROM series")
        stats['series'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM popular_series")
        stats['popular_series'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM categories")
        stats['categories'] = cursor.fetchone()[0]

        # 빈도별 시리즈 수
        cursor = conn.execute("""
            SELECT frequency_short, COUNT(*) as cnt FROM series
            WHERE frequency_short IS NOT NULL AND frequency_short != ''
            GROUP BY frequency_short
            ORDER BY cnt DESC
        """)
        stats['by_frequency'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 카테고리별 인기 시리즈 수
        cursor = conn.execute("""
            SELECT category, COUNT(*) as cnt FROM popular_series
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY cnt DESC
        """)
        stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 마지막 업데이트
        cursor = conn.execute("SELECT MAX(updated_at) FROM series")
        row = cursor.fetchone()
        stats['series_updated'] = row[0] if row else None

        cursor = conn.execute("SELECT MAX(updated_at) FROM popular_series")
        row = cursor.fetchone()
        stats['popular_updated'] = row[0] if row else None

        return stats


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='FRED 메타데이터 DB 관리')
    parser.add_argument('--init', action='store_true', help='DB 초기화')
    parser.add_argument('--sync-search', type=str, metavar='KEYWORD',
                        help='키워드 기반 동기화')
    parser.add_argument('--sync-popular', action='store_true',
                        help='인기 시리즈 동기화')
    parser.add_argument('--sync-all', action='store_true',
                        help='전체 동기화 (기본 키워드 + 인기 시리즈)')
    parser.add_argument('--force', action='store_true',
                        help='강제 동기화')
    parser.add_argument('--search', type=str, metavar='KEYWORD',
                        help='LIKE 검색')
    parser.add_argument('--search-fts', type=str, metavar='QUERY',
                        help='FTS5 전문 검색')
    parser.add_argument('--info', type=str, metavar='SERIES_ID',
                        help='시리즈 정보 조회')
    parser.add_argument('--popular', action='store_true',
                        help='인기 시리즈 목록')
    parser.add_argument('--category', type=str,
                        help='인기 시리즈 카테고리 필터')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    db = FredMetaDB(args.db)

    try:
        if args.init:
            db.init_db()

        elif args.sync_all:
            db.sync_all(force=args.force)

        elif args.sync_popular:
            db.sync_popular_series(force=args.force)

        elif args.sync_search:
            db.sync_series_by_search(args.sync_search, force=args.force)

        elif args.search:
            results = db.search_series(args.search)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            print(f"{'시리즈ID':<15} {'제목':<50} {'빈도':<6} {'인기도':<6}")
            print("-" * 80)
            for s in results[:30]:
                sid = s['series_id'][:13]
                title = s['title'][:48] if s['title'] else '-'
                freq = s['frequency_short'] or '-'
                pop = s['popularity'] or 0
                print(f"{sid:<15} {title:<50} {freq:<6} {pop:<6}")

        elif args.search_fts:
            results = db.search_series_fts(args.search_fts)
            print(f"\n=== '{args.search_fts}' FTS 검색 결과 ({len(results)}건) ===")
            print(f"{'시리즈ID':<15} {'제목':<50} {'빈도':<6} {'인기도':<6}")
            print("-" * 80)
            for s in results[:30]:
                sid = s['series_id'][:13]
                title = s['title'][:48] if s['title'] else '-'
                freq = s['frequency_short'] or '-'
                pop = s['popularity'] or 0
                print(f"{sid:<15} {title:<50} {freq:<6} {pop:<6}")

        elif args.info:
            info = db.get_series_info(args.info)
            if info:
                print(f"\n=== 시리즈 정보: {args.info} ===")
                print(f"시리즈 ID: {info['series_id']}")
                print(f"제목: {info['title']}")
                print(f"빈도: {info['frequency']} ({info['frequency_short']})")
                print(f"단위: {info['units']}")
                print(f"계절조정: {info['seasonal_adjustment']}")
                print(f"기간: {info['observation_start']} ~ {info['observation_end']}")
                print(f"인기도: {info['popularity']}")
                if info['notes']:
                    notes = info['notes'][:300] + '...' if len(info['notes']) > 300 else info['notes']
                    print(f"설명: {notes}")
            else:
                print(f"시리즈 '{args.info}'를 찾을 수 없습니다.")

        elif args.popular:
            results = db.get_popular_series(category=args.category)
            if not results:
                db.sync_popular_series(force=True)
                results = db.get_popular_series(category=args.category)

            cat_filter = f" [{args.category}]" if args.category else ""
            print(f"\n=== 인기 시리즈{cat_filter} ({len(results)}건) ===")
            print(f"{'시리즈ID':<15} {'카테고리':<10} {'한글명':<25} {'제목':<35}")
            print("-" * 90)
            for s in results:
                sid = s['series_id'][:13]
                cat = s['category'][:8] if s['category'] else '-'
                desc_kr = s['description_kr'][:23] if s['description_kr'] else '-'
                title = s['title'][:33] if s['title'] else '-'
                print(f"{sid:<15} {cat:<10} {desc_kr:<25} {title:<35}")

        elif args.stats:
            stats = db.get_stats()
            print("\n=== FRED 메타DB 통계 ===")
            print(f"시리즈: {stats['series']:,}개")
            print(f"인기 시리즈: {stats['popular_series']:,}개")
            print(f"카테고리: {stats['categories']:,}개")

            if stats.get('by_frequency'):
                freq_names = {
                    'D': 'Daily', 'W': 'Weekly', 'BW': 'Biweekly',
                    'M': 'Monthly', 'Q': 'Quarterly', 'SA': 'Semiannual', 'A': 'Annual'
                }
                print("\n빈도별 시리즈:")
                for code, cnt in list(stats['by_frequency'].items())[:10]:
                    name = freq_names.get(code, code)
                    print(f"  - {name}({code}): {cnt:,}개")

            if stats.get('by_category'):
                print("\n카테고리별 인기 시리즈:")
                for cat, cnt in stats['by_category'].items():
                    print(f"  - {cat}: {cnt}개")

            if stats.get('series_updated'):
                print(f"\n시리즈 업데이트: {stats['series_updated'][:19]}")
            if stats.get('popular_updated'):
                print(f"인기 시리즈 업데이트: {stats['popular_updated'][:19]}")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
