# -*- coding: utf-8 -*-
"""
ECOS 메타데이터 DB 관리
한국은행 경제통계시스템 통계표/항목 정보를 SQLite로 관리

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


class EcosMetaDB:
    """ECOS 메타데이터 DB 관리 클래스"""

    BASE_URL = "http://ecos.bok.or.kr/api"

    SCHEMA = """
    -- 통계표 목록
    CREATE TABLE IF NOT EXISTS stat_tables (
        id INTEGER PRIMARY KEY,
        p_stat_code TEXT,           -- 상위통계표코드
        stat_code TEXT UNIQUE,      -- 통계표코드
        stat_name TEXT,             -- 통계명
        cycle TEXT,                 -- 주기 (A/S/Q/M/SM/D)
        srch_yn TEXT,               -- 검색가능여부 (Y/N)
        org_name TEXT,              -- 출처
        updated_at TEXT
    );

    -- 통계 항목 목록
    CREATE TABLE IF NOT EXISTS stat_items (
        id INTEGER PRIMARY KEY,
        stat_code TEXT,             -- 통계표코드
        grp_code TEXT,              -- 항목그룹코드
        grp_name TEXT,              -- 항목그룹명
        item_code TEXT,             -- 통계항목코드
        item_name TEXT,             -- 통계항목명
        start_time TEXT,            -- 수록시작일자
        end_time TEXT,              -- 수록종료일자
        data_cnt INTEGER,           -- 자료수
        unit_name TEXT,             -- 단위
        weight TEXT,                -- 가중치
        updated_at TEXT,
        UNIQUE(stat_code, item_code)
    );

    -- 100대 통계지표
    CREATE TABLE IF NOT EXISTS key_statistics (
        id INTEGER PRIMARY KEY,
        class_code TEXT,            -- 분류코드
        class_name TEXT,            -- 분류명
        key_stat_code TEXT,         -- 통계표코드 (KeyStatisticList용)
        stat_code TEXT,             -- 통계표코드
        stat_name TEXT,             -- 통계명
        item_code TEXT,             -- 항목코드
        item_name TEXT,             -- 항목명
        cycle TEXT,                 -- 주기
        data_value TEXT,            -- 최신값
        unit_name TEXT,             -- 단위
        time TEXT,                  -- 시점
        updated_at TEXT
    );

    -- 주기 코드
    CREATE TABLE IF NOT EXISTS cycles (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_stat_code ON stat_tables(stat_code);
    CREATE INDEX IF NOT EXISTS idx_stat_name ON stat_tables(stat_name);
    CREATE INDEX IF NOT EXISTS idx_item_stat_code ON stat_items(stat_code);
    CREATE INDEX IF NOT EXISTS idx_item_name ON stat_items(item_name);
    CREATE INDEX IF NOT EXISTS idx_key_class ON key_statistics(class_code);

    -- FTS5 전문 검색
    CREATE VIRTUAL TABLE IF NOT EXISTS stat_tables_fts USING fts5(
        stat_name, org_name,
        content='stat_tables',
        content_rowid='id'
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS stat_items_fts USING fts5(
        grp_name, item_name,
        content='stat_items',
        content_rowid='id'
    );

    -- FTS 트리거 (stat_tables)
    CREATE TRIGGER IF NOT EXISTS stat_tables_ai AFTER INSERT ON stat_tables BEGIN
        INSERT INTO stat_tables_fts(rowid, stat_name, org_name)
        VALUES (new.id, new.stat_name, new.org_name);
    END;

    CREATE TRIGGER IF NOT EXISTS stat_tables_ad AFTER DELETE ON stat_tables BEGIN
        INSERT INTO stat_tables_fts(stat_tables_fts, rowid, stat_name, org_name)
        VALUES ('delete', old.id, old.stat_name, old.org_name);
    END;

    CREATE TRIGGER IF NOT EXISTS stat_tables_au AFTER UPDATE ON stat_tables BEGIN
        INSERT INTO stat_tables_fts(stat_tables_fts, rowid, stat_name, org_name)
        VALUES ('delete', old.id, old.stat_name, old.org_name);
        INSERT INTO stat_tables_fts(rowid, stat_name, org_name)
        VALUES (new.id, new.stat_name, new.org_name);
    END;

    -- FTS 트리거 (stat_items)
    CREATE TRIGGER IF NOT EXISTS stat_items_ai AFTER INSERT ON stat_items BEGIN
        INSERT INTO stat_items_fts(rowid, grp_name, item_name)
        VALUES (new.id, new.grp_name, new.item_name);
    END;

    CREATE TRIGGER IF NOT EXISTS stat_items_ad AFTER DELETE ON stat_items BEGIN
        INSERT INTO stat_items_fts(stat_items_fts, rowid, grp_name, item_name)
        VALUES ('delete', old.id, old.grp_name, old.item_name);
    END;

    CREATE TRIGGER IF NOT EXISTS stat_items_au AFTER UPDATE ON stat_items BEGIN
        INSERT INTO stat_items_fts(stat_items_fts, rowid, grp_name, item_name)
        VALUES ('delete', old.id, old.grp_name, old.item_name);
        INSERT INTO stat_items_fts(rowid, grp_name, item_name)
        VALUES (new.id, new.grp_name, new.item_name);
    END;
    """

    # 주기 코드
    CYCLES = [
        ('A', '년', '연간 데이터'),
        ('S', '반년', '반기 데이터'),
        ('Q', '분기', '분기 데이터'),
        ('M', '월', '월간 데이터'),
        ('SM', '반월', '반월 데이터'),
        ('D', '일', '일간 데이터'),
    ]

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent / 'data'
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / 'ecos_meta.db')

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
        return os.getenv('ECOS_API_KEY', '')

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

        # 주기 코드 삽입
        conn.executemany("""
            INSERT OR IGNORE INTO cycles (code, name, description)
            VALUES (?, ?, ?)
        """, self.CYCLES)

        conn.commit()
        print(f"DB 초기화 완료: {self.db_path}")
        return True

    def _make_request(
        self,
        service: str,
        params: List[str] = None,
        start: int = 1,
        end: int = 1000
    ) -> Dict:
        """
        ECOS API 요청

        Args:
            service: 서비스명 (StatisticTableList, StatisticItemList, etc.)
            params: 추가 파라미터 리스트
            start: 시작 건수
            end: 종료 건수

        Returns:
            API 응답 데이터
        """
        if not self.api_key:
            return {'RESULT': {'CODE': 'ERROR', 'MESSAGE': 'API 키가 설정되지 않았습니다.'}}

        # URL 구성: /서비스명/인증키/요청타입/언어/시작/종료/[파라미터들]
        url_parts = [
            self.BASE_URL,
            service,
            self.api_key,
            'json',
            'kr',
            str(start),
            str(end)
        ]

        if params:
            url_parts.extend(params)

        url = '/'.join(url_parts)

        try:
            response = requests.get(url, timeout=30)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'RESULT': {
                        'CODE': str(response.status_code),
                        'MESSAGE': f'HTTP {response.status_code}'
                    }
                }
        except requests.exceptions.Timeout:
            return {'RESULT': {'CODE': 'TIMEOUT', 'MESSAGE': '요청 시간 초과'}}
        except requests.exceptions.RequestException as e:
            return {'RESULT': {'CODE': 'ERROR', 'MESSAGE': str(e)}}
        except Exception as e:
            return {'RESULT': {'CODE': 'ERROR', 'MESSAGE': str(e)}}

    def sync_stat_tables(self, force: bool = False) -> int:
        """
        통계표 목록 동기화

        Args:
            force: 강제 동기화 여부

        Returns:
            저장된 통계표 수
        """
        if not self.api_key:
            print("ECOS_API_KEY가 설정되지 않았습니다.")
            return 0

        self.init_db()
        conn = self.connect()

        # 마지막 업데이트 확인
        if not force:
            try:
                cursor = conn.execute(
                    "SELECT MAX(updated_at) FROM stat_tables"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    last_update = datetime.fromisoformat(row[0])
                    if datetime.now() - last_update < timedelta(days=1):
                        print("통계표 목록이 최신 상태입니다 (1일 이내 업데이트)")
                        cursor = conn.execute("SELECT COUNT(*) FROM stat_tables")
                        return cursor.fetchone()[0]
            except Exception:
                pass

        print("ECOS 통계표 목록 동기화 중...")

        # API 호출 (전체 목록)
        result = self._make_request('StatisticTableList', start=1, end=10000)

        if 'StatisticTableList' not in result:
            error = result.get('RESULT', {})
            print(f"API 오류: [{error.get('CODE')}] {error.get('MESSAGE')}")
            return 0

        items = result['StatisticTableList'].get('row', [])
        if not items:
            print("조회된 통계표가 없습니다.")
            return 0

        now = datetime.now().isoformat()

        # 기존 데이터 삭제
        conn.execute("DELETE FROM stat_tables")

        # 배치 처리
        batch = []
        for item in items:
            batch.append((
                item.get('P_STAT_CODE', ''),
                item.get('STAT_CODE', ''),
                item.get('STAT_NAME', ''),
                item.get('CYCLE', ''),
                item.get('SRCH_YN', ''),
                item.get('ORG_NAME', ''),
                now
            ))

        conn.executemany("""
            INSERT INTO stat_tables
            (p_stat_code, stat_code, stat_name, cycle, srch_yn, org_name, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch)

        conn.commit()
        print(f"총 {len(batch)}개 통계표 저장 완료")
        return len(batch)

    def sync_stat_items(self, stat_code: str, force: bool = False) -> int:
        """
        특정 통계표의 항목 목록 동기화

        Args:
            stat_code: 통계표 코드
            force: 강제 동기화 여부

        Returns:
            저장된 항목 수
        """
        if not self.api_key:
            print("ECOS_API_KEY가 설정되지 않았습니다.")
            return 0

        self.init_db()
        conn = self.connect()

        # 마지막 업데이트 확인
        if not force:
            try:
                cursor = conn.execute(
                    "SELECT MAX(updated_at) FROM stat_items WHERE stat_code = ?",
                    (stat_code,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    last_update = datetime.fromisoformat(row[0])
                    if datetime.now() - last_update < timedelta(days=1):
                        print(f"[{stat_code}] 항목 목록이 최신 상태입니다")
                        cursor = conn.execute(
                            "SELECT COUNT(*) FROM stat_items WHERE stat_code = ?",
                            (stat_code,)
                        )
                        return cursor.fetchone()[0]
            except Exception:
                pass

        print(f"[{stat_code}] 항목 목록 동기화 중...")

        # API 호출
        result = self._make_request('StatisticItemList', [stat_code], start=1, end=10000)

        if 'StatisticItemList' not in result:
            error = result.get('RESULT', {})
            print(f"API 오류: [{error.get('CODE')}] {error.get('MESSAGE')}")
            return 0

        items = result['StatisticItemList'].get('row', [])
        if not items:
            print(f"[{stat_code}] 조회된 항목이 없습니다.")
            return 0

        now = datetime.now().isoformat()

        # 해당 통계표의 기존 항목 삭제
        conn.execute("DELETE FROM stat_items WHERE stat_code = ?", (stat_code,))

        # 배치 처리
        batch = []
        for item in items:
            batch.append((
                stat_code,
                item.get('GRP_CODE', ''),
                item.get('GRP_NAME', ''),
                item.get('ITEM_CODE', ''),
                item.get('ITEM_NAME', ''),
                item.get('START_TIME', ''),
                item.get('END_TIME', ''),
                int(item.get('DATA_CNT', 0) or 0),
                item.get('UNIT_NAME', ''),
                item.get('WEIGHT', ''),
                now
            ))

        conn.executemany("""
            INSERT OR REPLACE INTO stat_items
            (stat_code, grp_code, grp_name, item_code, item_name,
             start_time, end_time, data_cnt, unit_name, weight, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

        conn.commit()
        print(f"[{stat_code}] 총 {len(batch)}개 항목 저장 완료")
        return len(batch)

    def sync_key_statistics(self, force: bool = False) -> int:
        """
        100대 통계지표 동기화

        Args:
            force: 강제 동기화 여부

        Returns:
            저장된 지표 수
        """
        if not self.api_key:
            print("ECOS_API_KEY가 설정되지 않았습니다.")
            return 0

        self.init_db()
        conn = self.connect()

        # 마지막 업데이트 확인
        if not force:
            try:
                cursor = conn.execute(
                    "SELECT MAX(updated_at) FROM key_statistics"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    last_update = datetime.fromisoformat(row[0])
                    if datetime.now() - last_update < timedelta(hours=6):
                        print("100대 지표가 최신 상태입니다 (6시간 이내 업데이트)")
                        cursor = conn.execute("SELECT COUNT(*) FROM key_statistics")
                        return cursor.fetchone()[0]
            except Exception:
                pass

        print("100대 통계지표 동기화 중...")

        # API 호출
        result = self._make_request('KeyStatisticList', start=1, end=500)

        if 'KeyStatisticList' not in result:
            error = result.get('RESULT', {})
            print(f"API 오류: [{error.get('CODE')}] {error.get('MESSAGE')}")
            return 0

        items = result['KeyStatisticList'].get('row', [])
        if not items:
            print("조회된 지표가 없습니다.")
            return 0

        now = datetime.now().isoformat()

        # 기존 데이터 삭제
        conn.execute("DELETE FROM key_statistics")

        # 배치 처리
        # API 응답 필드:
        # - CLASS_NAME: 분류명 (예: 시장금리)
        # - KEYSTAT_NAME: 지표명 (예: 한국은행 기준금리)
        # - DATA_VALUE: 값
        # - CYCLE: 시점 (예: 20251220)
        # - UNIT_NAME: 단위
        batch = []
        for item in items:
            # KEYSTAT_NAME을 item_name으로 매핑 (핵심 수정)
            keystat_name = item.get('KEYSTAT_NAME', '')
            cycle_time = item.get('CYCLE', '')  # CYCLE이 실제 시점 정보

            batch.append((
                item.get('CLASS_CODE', ''),
                item.get('CLASS_NAME', ''),
                item.get('KEYSTAT_CODE', '') or '',  # 없을 수 있음
                item.get('STAT_CODE', '') or '',     # 없을 수 있음
                item.get('STAT_NAME', '') or '',     # 없을 수 있음
                item.get('ITEM_CODE', '') or '',     # 없을 수 있음
                keystat_name,                        # KEYSTAT_NAME → item_name
                cycle_time,                          # CYCLE → cycle (시점 포함)
                item.get('DATA_VALUE', ''),
                item.get('UNIT_NAME', ''),
                cycle_time,                          # CYCLE → time (시점)
                now
            ))

        conn.executemany("""
            INSERT INTO key_statistics
            (class_code, class_name, key_stat_code, stat_code, stat_name,
             item_code, item_name, cycle, data_value, unit_name, time, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

        conn.commit()
        print(f"총 {len(batch)}개 지표 저장 완료")
        return len(batch)

    def search_tables(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        통계표 검색

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT stat_code, stat_name, cycle, org_name, srch_yn
            FROM stat_tables
            WHERE stat_name LIKE ? OR org_name LIKE ?
            ORDER BY stat_name
            LIMIT ?
        """, (f'%{keyword}%', f'%{keyword}%', limit))

        return [dict(row) for row in cursor.fetchall()]

    def search_tables_fts(self, query: str, limit: int = 50) -> List[Dict]:
        """
        FTS5 전문 검색으로 통계표 검색

        Args:
            query: 검색 쿼리
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        try:
            cursor = conn.execute("""
                SELECT t.stat_code, t.stat_name, t.cycle, t.org_name, t.srch_yn
                FROM stat_tables_fts f
                JOIN stat_tables t ON f.rowid = t.id
                WHERE stat_tables_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return self.search_tables(query, limit=limit)

    def get_table_info(self, stat_code: str) -> Optional[Dict]:
        """
        통계표 정보 조회

        Args:
            stat_code: 통계표 코드

        Returns:
            통계표 정보
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT * FROM stat_tables WHERE stat_code = ?
        """, (stat_code,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_items(self, stat_code: str) -> List[Dict]:
        """
        통계표 항목 목록 조회

        Args:
            stat_code: 통계표 코드

        Returns:
            항목 목록
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT grp_code, grp_name, item_code, item_name,
                   start_time, end_time, data_cnt, unit_name
            FROM stat_items
            WHERE stat_code = ?
            ORDER BY grp_code, item_code
        """, (stat_code,))

        return [dict(row) for row in cursor.fetchall()]

    def search_items(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        항목 검색

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT stat_code, grp_name, item_code, item_name, unit_name
            FROM stat_items
            WHERE item_name LIKE ? OR grp_name LIKE ?
            ORDER BY stat_code, item_name
            LIMIT ?
        """, (f'%{keyword}%', f'%{keyword}%', limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_key_statistics(self, class_code: str = None) -> List[Dict]:
        """
        100대 통계지표 조회

        Args:
            class_code: 분류코드 (선택)

        Returns:
            지표 목록
        """
        conn = self.connect()

        if class_code:
            cursor = conn.execute("""
                SELECT class_name, stat_name, item_name, data_value, unit_name, time, cycle
                FROM key_statistics
                WHERE class_code = ?
                ORDER BY key_stat_code
            """, (class_code,))
        else:
            cursor = conn.execute("""
                SELECT class_name, stat_name, item_name, data_value, unit_name, time, cycle
                FROM key_statistics
                ORDER BY class_code, key_stat_code
            """)

        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """DB 통계 조회"""
        conn = self.connect()

        stats = {}

        cursor = conn.execute("SELECT COUNT(*) FROM stat_tables")
        stats['tables'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM stat_items")
        stats['items'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM key_statistics")
        stats['key_stats'] = cursor.fetchone()[0]

        # 주기별 통계표 수
        cursor = conn.execute("""
            SELECT cycle, COUNT(*) as cnt FROM stat_tables
            WHERE cycle IS NOT NULL AND cycle != ''
            GROUP BY cycle
        """)
        stats['by_cycle'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 마지막 업데이트
        cursor = conn.execute("SELECT MAX(updated_at) FROM stat_tables")
        row = cursor.fetchone()
        stats['tables_updated'] = row[0] if row else None

        cursor = conn.execute("SELECT MAX(updated_at) FROM key_statistics")
        row = cursor.fetchone()
        stats['key_stats_updated'] = row[0] if row else None

        return stats


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='ECOS 메타데이터 DB 관리')
    parser.add_argument('--init', action='store_true', help='DB 초기화')
    parser.add_argument('--sync-tables', action='store_true',
                        help='통계표 목록 동기화')
    parser.add_argument('--sync-items', type=str, metavar='CODE',
                        help='특정 통계표 항목 동기화')
    parser.add_argument('--sync-key', action='store_true',
                        help='100대 통계지표 동기화')
    parser.add_argument('--sync-all', action='store_true',
                        help='전체 동기화 (통계표 + 100대 지표)')
    parser.add_argument('--force', action='store_true',
                        help='강제 동기화')
    parser.add_argument('--search', type=str, metavar='KEYWORD',
                        help='통계표 검색')
    parser.add_argument('--search-items', type=str, metavar='KEYWORD',
                        help='항목 검색')
    parser.add_argument('--items', type=str, metavar='CODE',
                        help='통계표 항목 목록 조회')
    parser.add_argument('--info', type=str, metavar='CODE',
                        help='통계표 정보 조회')
    parser.add_argument('--key-stats', action='store_true',
                        help='100대 통계지표 조회')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    db = EcosMetaDB(args.db)

    try:
        if args.init:
            db.init_db()

        elif args.sync_all:
            db.sync_stat_tables(force=args.force)
            db.sync_key_statistics(force=args.force)

        elif args.sync_tables:
            db.sync_stat_tables(force=args.force)

        elif args.sync_items:
            db.sync_stat_items(args.sync_items, force=args.force)

        elif args.sync_key:
            db.sync_key_statistics(force=args.force)

        elif args.search:
            results = db.search_tables(args.search)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            print(f"{'통계코드':<12} {'통계명':<40} {'주기':<4} {'출처':<20}")
            print("-" * 80)
            for t in results[:30]:
                code = t['stat_code']
                name = t['stat_name'][:38]
                cycle = t['cycle'] or '-'
                org = (t['org_name'] or '-')[:18]
                print(f"{code:<12} {name:<40} {cycle:<4} {org:<20}")

        elif args.search_items:
            results = db.search_items(args.search_items)
            print(f"\n=== '{args.search_items}' 항목 검색 결과 ({len(results)}건) ===")
            print(f"{'통계코드':<12} {'항목코드':<15} {'항목명':<40} {'단위':<10}")
            print("-" * 80)
            for item in results[:30]:
                stat = item['stat_code']
                code = item['item_code'][:13]
                name = item['item_name'][:38]
                unit = (item['unit_name'] or '-')[:8]
                print(f"{stat:<12} {code:<15} {name:<40} {unit:<10}")

        elif args.items:
            # 항목이 없으면 동기화 시도
            items = db.get_items(args.items)
            if not items:
                db.sync_stat_items(args.items, force=True)
                items = db.get_items(args.items)

            if items:
                table_info = db.get_table_info(args.items)
                table_name = table_info['stat_name'] if table_info else args.items
                print(f"\n=== [{args.items}] {table_name} 항목 목록 ({len(items)}건) ===")
                print(f"{'항목코드':<15} {'항목명':<40} {'단위':<10} {'자료수':<8}")
                print("-" * 75)
                for item in items:
                    code = item['item_code'][:13]
                    name = item['item_name'][:38]
                    unit = (item['unit_name'] or '-')[:8]
                    cnt = item['data_cnt'] or 0
                    print(f"{code:<15} {name:<40} {unit:<10} {cnt:<8}")
            else:
                print(f"[{args.items}] 항목을 찾을 수 없습니다.")

        elif args.info:
            info = db.get_table_info(args.info)
            if info:
                print(f"\n=== 통계표 정보 ===")
                print(f"통계코드: {info['stat_code']}")
                print(f"통계명: {info['stat_name']}")
                print(f"상위코드: {info['p_stat_code'] or '-'}")
                print(f"주기: {info['cycle'] or '-'}")
                print(f"검색가능: {info['srch_yn'] or '-'}")
                print(f"출처: {info['org_name'] or '-'}")
            else:
                print(f"통계코드 '{args.info}'를 찾을 수 없습니다.")

        elif args.key_stats:
            stats = db.get_key_statistics()
            if not stats:
                db.sync_key_statistics(force=True)
                stats = db.get_key_statistics()

            print(f"\n=== 100대 통계지표 ({len(stats)}건) ===")
            print(f"{'분류':<15} {'지표명':<35} {'값':<15} {'단위':<10} {'시점':<10}")
            print("-" * 90)
            for s in stats:
                cls = s['class_name'][:13]
                name = s['item_name'][:33]
                value = s['data_value'][:13] if s['data_value'] else '-'
                unit = (s['unit_name'] or '-')[:8]
                time = s['time'] or '-'
                print(f"{cls:<15} {name:<35} {value:<15} {unit:<10} {time:<10}")

        elif args.stats:
            stats = db.get_stats()
            print("\n=== ECOS 메타DB 통계 ===")
            print(f"통계표: {stats['tables']:,}개")
            print(f"통계항목: {stats['items']:,}개")
            print(f"100대 지표: {stats['key_stats']:,}개")

            if stats.get('by_cycle'):
                cycle_names = {'A': '년', 'S': '반년', 'Q': '분기', 'M': '월', 'SM': '반월', 'D': '일'}
                print("\n주기별 통계표:")
                for code, cnt in sorted(stats['by_cycle'].items()):
                    name = cycle_names.get(code, code)
                    print(f"  - {name}({code}): {cnt:,}개")

            if stats.get('tables_updated'):
                print(f"\n통계표 업데이트: {stats['tables_updated'][:19]}")
            if stats.get('key_stats_updated'):
                print(f"100대 지표 업데이트: {stats['key_stats_updated'][:19]}")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
