# -*- coding: utf-8 -*-
"""
Yahoo Finance 메타데이터 DB 관리
종목 코드-이름 매핑을 SQLite로 관리

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


class YahooMetaDB:
    """Yahoo Finance 메타데이터 DB 관리 클래스"""

    SCHEMA = """
    -- 종목 정보 (글로벌 + 한국)
    CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY,
        stock_code TEXT NOT NULL,           -- 종목코드 (005930)
        yahoo_ticker TEXT UNIQUE NOT NULL,  -- Yahoo 티커 (005930.KS)
        stock_name TEXT NOT NULL,           -- 종목명 (삼성전자)
        stock_name_eng TEXT,                -- 영문명 (Samsung Electronics)
        market TEXT NOT NULL,               -- 시장 (kospi/kosdaq/nasdaq/nyse)
        sector TEXT,                        -- 섹터
        industry TEXT,                      -- 산업
        country TEXT DEFAULT 'KR',          -- 국가
        currency TEXT DEFAULT 'KRW',        -- 통화
        is_active INTEGER DEFAULT 1,        -- 활성 여부
        updated_at TEXT
    );

    -- 시장 정보
    CREATE TABLE IF NOT EXISTS markets (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        suffix TEXT,                        -- Yahoo 접미사 (.KS, .KQ)
        country TEXT,
        timezone TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_stock_code ON stocks(stock_code);
    CREATE INDEX IF NOT EXISTS idx_stock_name ON stocks(stock_name);
    CREATE INDEX IF NOT EXISTS idx_market ON stocks(market);
    CREATE INDEX IF NOT EXISTS idx_country ON stocks(country);

    -- FTS5 전문 검색
    CREATE VIRTUAL TABLE IF NOT EXISTS stock_fts USING fts5(
        stock_name,
        stock_name_eng,
        content='stocks',
        content_rowid='id'
    );

    -- FTS 트리거
    CREATE TRIGGER IF NOT EXISTS stock_ai AFTER INSERT ON stocks BEGIN
        INSERT INTO stock_fts(rowid, stock_name, stock_name_eng)
        VALUES (new.id, new.stock_name, new.stock_name_eng);
    END;

    CREATE TRIGGER IF NOT EXISTS stock_ad AFTER DELETE ON stocks BEGIN
        INSERT INTO stock_fts(stock_fts, rowid, stock_name, stock_name_eng)
        VALUES ('delete', old.id, old.stock_name, old.stock_name_eng);
    END;

    CREATE TRIGGER IF NOT EXISTS stock_au AFTER UPDATE ON stocks BEGIN
        INSERT INTO stock_fts(stock_fts, rowid, stock_name, stock_name_eng)
        VALUES ('delete', old.id, old.stock_name, old.stock_name_eng);
        INSERT INTO stock_fts(rowid, stock_name, stock_name_eng)
        VALUES (new.id, new.stock_name, new.stock_name_eng);
    END;
    """

    # 시장 정보
    MARKETS = [
        ('kospi', '코스피', '.KS', 'KR', 'Asia/Seoul'),
        ('kosdaq', '코스닥', '.KQ', 'KR', 'Asia/Seoul'),
        ('nasdaq', 'NASDAQ', '', 'US', 'America/New_York'),
        ('nyse', 'NYSE', '', 'US', 'America/New_York'),
        ('amex', 'AMEX', '', 'US', 'America/New_York'),
    ]

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent / 'data'
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / 'yahoo_meta.db')

        self.db_path = db_path
        self.conn = None

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

        # 시장 정보 삽입
        conn.executemany("""
            INSERT OR IGNORE INTO markets (code, name, suffix, country, timezone)
            VALUES (?, ?, ?, ?, ?)
        """, self.MARKETS)

        conn.commit()
        print(f"DB 초기화 완료: {self.db_path}")
        return True

    def upsert_stock(
        self,
        stock_code: str,
        yahoo_ticker: str,
        stock_name: str,
        market: str,
        stock_name_eng: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        country: str = 'KR',
        currency: str = 'KRW'
    ) -> bool:
        """
        종목 정보 추가/수정 (UPSERT)

        Args:
            stock_code: 종목코드 (005930)
            yahoo_ticker: Yahoo 티커 (005930.KS)
            stock_name: 종목명 (삼성전자)
            market: 시장 (kospi/kosdaq)
            stock_name_eng: 영문명
            sector: 섹터
            industry: 산업
            country: 국가
            currency: 통화

        Returns:
            성공 여부
        """
        try:
            now = datetime.now().isoformat()
            self.conn.execute("""
                INSERT INTO stocks (
                    stock_code, yahoo_ticker, stock_name, stock_name_eng,
                    market, sector, industry, country, currency, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(yahoo_ticker) DO UPDATE SET
                    stock_name = excluded.stock_name,
                    stock_name_eng = excluded.stock_name_eng,
                    market = excluded.market,
                    sector = excluded.sector,
                    industry = excluded.industry,
                    updated_at = excluded.updated_at
            """, (
                stock_code, yahoo_ticker, stock_name, stock_name_eng,
                market, sector, industry, country, currency, now
            ))
            return True
        except Exception as e:
            print(f"종목 저장 실패 [{stock_code}]: {e}")
            return False

    def sync_korean_stocks(self, force: bool = False) -> int:
        """
        한국 주식 목록 동기화 (DART 메타DB 연동)

        Args:
            force: 강제 동기화

        Returns:
            동기화된 종목 수
        """
        # DART 메타DB 경로 탐색
        dart_db_paths = [
            Path(__file__).parent.parent.parent / 'api-dart' / 'data' / 'dart_meta.db',
        ]

        dart_db_path = None
        for path in dart_db_paths:
            if path.exists():
                dart_db_path = path
                break

        if dart_db_path is None:
            print("DART 메타DB를 찾을 수 없습니다.")
            print("먼저 api-dart 스킬의 메타DB를 동기화해주세요:")
            print("  python .claude/skills/api-dart/scripts/dart_meta_db.py --sync")
            return 0

        # DB 초기화
        self.init_db()
        conn = self.connect()

        # 마지막 업데이트 확인
        if not force:
            try:
                cursor = conn.execute(
                    "SELECT MAX(updated_at) FROM stocks WHERE country = 'KR'"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    last_update = datetime.fromisoformat(row[0])
                    if datetime.now() - last_update < timedelta(days=1):
                        cursor = conn.execute(
                            "SELECT COUNT(*) FROM stocks WHERE country = 'KR'"
                        )
                        count = cursor.fetchone()[0]
                        print(f"한국 종목 DB가 최신 상태입니다 ({count}개, 1일 이내 업데이트)")
                        return count
            except Exception:
                pass

        print(f"DART 메타DB 연동 중: {dart_db_path}")

        try:
            dart_conn = sqlite3.connect(str(dart_db_path))
            dart_conn.row_factory = sqlite3.Row

            # 상장사만 조회 (stock_code가 있는 기업)
            query = """
            SELECT corp_code, corp_name, corp_name_eng, stock_code, corp_cls
            FROM corporations
            WHERE stock_code IS NOT NULL AND stock_code != ''
            """

            rows = dart_conn.execute(query).fetchall()
            dart_conn.close()

            count = 0
            for row in rows:
                corp_cls = row['corp_cls']

                # 시장 판별 (Y=KOSPI, K=KOSDAQ)
                if corp_cls == 'Y':
                    market = 'kospi'
                    suffix = '.KS'
                elif corp_cls == 'K':
                    market = 'kosdaq'
                    suffix = '.KQ'
                else:
                    # N=KONEX, E=기타는 제외
                    continue

                yahoo_ticker = f"{row['stock_code']}{suffix}"

                self.upsert_stock(
                    stock_code=row['stock_code'],
                    yahoo_ticker=yahoo_ticker,
                    stock_name=row['corp_name'],
                    stock_name_eng=row['corp_name_eng'],
                    market=market,
                    country='KR',
                    currency='KRW'
                )
                count += 1

            conn.commit()
            print(f"DART 연동 완료: {count}개 한국 종목")
            return count

        except Exception as e:
            print(f"DART 연동 오류: {e}")
            return 0

    def search_stock(
        self,
        keyword: str,
        market: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        종목 검색

        Args:
            keyword: 검색어 (종목명 또는 코드)
            market: 시장 필터 (kospi/kosdaq/nasdaq/nyse)
            country: 국가 필터 (KR/US)
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        # 숫자면 종목코드로 검색
        if keyword.isdigit():
            query = "SELECT * FROM stocks WHERE stock_code LIKE ?"
            params = [f"{keyword}%"]
        else:
            # FTS 검색 시도
            try:
                query = """
                SELECT s.* FROM stocks s
                JOIN stock_fts f ON s.id = f.rowid
                WHERE stock_fts MATCH ?
                """
                params = [keyword]

                if market:
                    query += " AND s.market = ?"
                    params.append(market)

                if country:
                    query += " AND s.country = ?"
                    params.append(country)

                query += f" LIMIT {limit}"
                rows = conn.execute(query, params).fetchall()

                if rows:
                    return [dict(row) for row in rows]
            except sqlite3.OperationalError:
                pass  # FTS가 비어있는 경우 일반 검색

            # 일반 LIKE 검색 (폴백)
            query = """
            SELECT * FROM stocks
            WHERE stock_name LIKE ? OR stock_name_eng LIKE ?
            """
            params = [f'%{keyword}%', f'%{keyword}%']

        if market:
            query += " AND market = ?"
            params.append(market)

        if country:
            query += " AND country = ?"
            params.append(country)

        query += f" ORDER BY LENGTH(stock_name) LIMIT {limit}"
        rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def get_market_type(self, stock_code: str) -> str:
        """
        종목코드로 시장 조회

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            시장 코드 (kospi/kosdaq) 또는 기본값 kospi
        """
        conn = self.connect()

        cursor = conn.execute(
            "SELECT market FROM stocks WHERE stock_code = ?",
            (stock_code,)
        )
        row = cursor.fetchone()

        return row['market'] if row else 'kospi'

    def get_yahoo_ticker(self, stock_code: str) -> Optional[str]:
        """
        종목코드로 Yahoo 티커 조회

        Args:
            stock_code: 종목코드

        Returns:
            Yahoo 티커 (예: 005930.KS) 또는 None
        """
        conn = self.connect()

        cursor = conn.execute(
            "SELECT yahoo_ticker FROM stocks WHERE stock_code = ?",
            (stock_code,)
        )
        row = cursor.fetchone()

        return row['yahoo_ticker'] if row else None

    def get_stock_by_name(self, name: str) -> Optional[Dict]:
        """
        종목명으로 종목 정보 조회

        Args:
            name: 종목명

        Returns:
            종목 정보 딕셔너리 또는 None
        """
        conn = self.connect()

        # 정확한 매칭
        cursor = conn.execute(
            "SELECT * FROM stocks WHERE stock_name = ?",
            (name,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        # 부분 매칭
        cursor = conn.execute("""
            SELECT * FROM stocks
            WHERE stock_name LIKE ?
            ORDER BY LENGTH(stock_name)
            LIMIT 1
        """, (f'%{name}%',))

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_stats(self) -> Dict:
        """DB 통계 조회"""
        conn = self.connect()

        stats = {}

        # 전체 종목 수
        cursor = conn.execute("SELECT COUNT(*) FROM stocks")
        stats['total'] = cursor.fetchone()[0]

        # 국가별 통계
        cursor = conn.execute("""
            SELECT country, COUNT(*) as cnt FROM stocks
            GROUP BY country
        """)
        stats['by_country'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 시장별 통계
        cursor = conn.execute("""
            SELECT market, COUNT(*) as cnt FROM stocks
            GROUP BY market
        """)
        stats['by_market'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 마지막 업데이트
        cursor = conn.execute("SELECT MAX(updated_at) FROM stocks")
        row = cursor.fetchone()
        stats['last_update'] = row[0] if row else None

        return stats

    def add_us_stock(
        self,
        ticker: str,
        name: str,
        name_eng: Optional[str] = None,
        market: str = 'nasdaq',
        sector: Optional[str] = None,
        industry: Optional[str] = None
    ) -> bool:
        """
        미국 주식 수동 추가

        Args:
            ticker: 티커 심볼 (AAPL)
            name: 종목명
            name_eng: 영문명
            market: 시장 (nasdaq/nyse/amex)
            sector: 섹터
            industry: 산업

        Returns:
            성공 여부
        """
        return self.upsert_stock(
            stock_code=ticker,
            yahoo_ticker=ticker.upper(),
            stock_name=name,
            stock_name_eng=name_eng or name,
            market=market,
            sector=sector,
            industry=industry,
            country='US',
            currency='USD'
        )


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Yahoo Finance 메타데이터 DB 관리',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # DB 초기화
  python yahoo_meta_db.py --init

  # 한국 종목 동기화 (DART 연동)
  python yahoo_meta_db.py --sync-kr

  # 강제 동기화
  python yahoo_meta_db.py --sync-kr --force

  # 종목 검색
  python yahoo_meta_db.py --search "삼성"

  # 특정 시장 검색
  python yahoo_meta_db.py --search "카카오" --market kosdaq

  # 미국 종목 추가
  python yahoo_meta_db.py --add-us AAPL "Apple Inc."

  # DB 통계
  python yahoo_meta_db.py --stats
        """
    )

    parser.add_argument('--init', action='store_true',
                        help='DB 초기화')
    parser.add_argument('--sync-kr', action='store_true',
                        help='한국 종목 동기화 (DART 메타DB 연동)')
    parser.add_argument('--force', action='store_true',
                        help='강제 동기화')
    parser.add_argument('--search', type=str, metavar='KEYWORD',
                        help='종목 검색')
    parser.add_argument('--market', type=str,
                        choices=['kospi', 'kosdaq', 'nasdaq', 'nyse'],
                        help='시장 필터')
    parser.add_argument('--add-us', nargs=2, metavar=('TICKER', 'NAME'),
                        help='미국 종목 추가')
    parser.add_argument('--stats', action='store_true',
                        help='DB 통계')
    parser.add_argument('--db', type=str,
                        help='DB 파일 경로')

    args = parser.parse_args()

    db = YahooMetaDB(args.db)

    try:
        if args.init:
            db.init_db()

        elif args.sync_kr:
            db.sync_korean_stocks(force=args.force)

        elif args.search:
            results = db.search_stock(args.search, market=args.market)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            print(f"{'종목명':<20} {'코드':<10} {'티커':<12} {'시장':<8}")
            print("-" * 55)
            for s in results[:30]:
                name = s['stock_name'][:18]
                code = s['stock_code']
                ticker = s['yahoo_ticker']
                market = s['market']
                print(f"{name:<20} {code:<10} {ticker:<12} {market:<8}")

        elif args.add_us:
            ticker, name = args.add_us
            db.init_db()
            if db.add_us_stock(ticker, name):
                db.conn.commit()
                print(f"미국 종목 추가: {ticker} ({name})")
            else:
                print(f"추가 실패: {ticker}")

        elif args.stats:
            stats = db.get_stats()
            print("\n=== Yahoo 메타DB 통계 ===")
            print(f"전체 종목: {stats['total']:,}개")

            if stats.get('by_country'):
                print("\n국가별:")
                country_names = {'KR': '한국', 'US': '미국'}
                for code, cnt in stats['by_country'].items():
                    name = country_names.get(code, code)
                    print(f"  - {name}: {cnt:,}개")

            if stats.get('by_market'):
                print("\n시장별:")
                market_names = {
                    'kospi': '코스피', 'kosdaq': '코스닥',
                    'nasdaq': 'NASDAQ', 'nyse': 'NYSE', 'amex': 'AMEX'
                }
                for code, cnt in stats['by_market'].items():
                    name = market_names.get(code, code)
                    print(f"  - {name}: {cnt:,}개")

            if stats['last_update']:
                print(f"\n마지막 업데이트: {stats['last_update'][:19]}")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
