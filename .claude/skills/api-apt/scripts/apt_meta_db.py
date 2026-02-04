# -*- coding: utf-8 -*-
"""
APT 메타데이터 DB 관리
국토교통부 아파트 실거래가 API - 지역코드 및 코드 참조 관리

Author: Claude Code
Version: 2.0.0
"""

import os
import sys
import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# 한글 출력 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


class AptMetaDB:
    """APT 메타데이터 DB 관리 클래스"""

    # DB 스키마
    SCHEMA = """
    -- 지역코드 마스터
    CREATE TABLE IF NOT EXISTS region_codes (
        region_cd TEXT PRIMARY KEY,   -- 5자리 법정동코드
        region_nm TEXT NOT NULL,      -- 구/시 명칭
        sido_nm TEXT,                 -- 시/도 명칭
        sido_cd TEXT,                 -- 시/도 코드 (2자리)
        region_type TEXT,             -- 서울/경기/광역시/도/세종
        updated_at TEXT
    );

    -- 거래유형 코드
    CREATE TABLE IF NOT EXISTS dealing_codes (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL
    );

    -- 동기화 로그
    CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY,
        sync_type TEXT NOT NULL,      -- regions/codes
        target TEXT,
        count INTEGER,
        synced_at TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_region_nm ON region_codes(region_nm);
    CREATE INDEX IF NOT EXISTS idx_sido_nm ON region_codes(sido_nm);
    CREATE INDEX IF NOT EXISTS idx_region_type ON region_codes(region_type);
    """

    # 거래유형 코드
    DEALING_CODES = [
        ('중개거래', '중개거래'),
        ('직거래', '직거래'),
    ]

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent / 'data'
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / 'apt_meta.db')

        self.db_path = db_path
        self.csv_path = Path(__file__).parent.parent / 'data' / 'region_codes.csv'
        self.conn = None
        self._init_db()

    def _init_db(self):
        """DB 초기화 (스키마 생성)"""
        conn = self.connect()
        conn.executescript(self.SCHEMA)

        # 거래유형 코드 삽입
        conn.executemany("""
            INSERT OR IGNORE INTO dealing_codes (code, name)
            VALUES (?, ?)
        """, self.DEALING_CODES)

        conn.commit()

    def connect(self) -> sqlite3.Connection:
        """DB 연결"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None

    # ==================== 지역코드 관련 ====================

    def load_regions_from_csv(self, csv_path: Optional[str] = None) -> int:
        """CSV에서 지역코드 로드"""
        if csv_path is None:
            csv_path = self.csv_path

        if not Path(csv_path).exists():
            print(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
            return 0

        conn = self.connect()
        now = datetime.now().isoformat()

        # 기존 데이터 삭제
        conn.execute("DELETE FROM region_codes")

        count = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute("""
                    INSERT OR REPLACE INTO region_codes
                    (region_cd, region_nm, sido_nm, sido_cd, region_type, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row['region_cd'],
                    row['region_nm'],
                    row['sido_nm'],
                    row['sido_cd'],
                    row['region_type'],
                    now
                ))
                count += 1

        conn.commit()

        # 동기화 로그
        self._log_sync('regions', 'csv', count)

        return count

    def get_region(self, region_cd: str) -> Optional[Dict]:
        """지역코드 정보 조회"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT region_cd, region_nm, sido_nm, sido_cd, region_type
            FROM region_codes
            WHERE region_cd = ?
        """, (region_cd,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_region_name(self, region_cd: str) -> str:
        """지역코드로 지역명 조회 (시도 구 형식)"""
        region = self.get_region(region_cd)
        if region:
            sido = region['sido_nm'] or ''
            sgg = region['region_nm'] or ''
            return f'{sido} {sgg}'.strip()
        return region_cd

    def search_regions(self, keyword: str, limit: int = 50) -> List[Dict]:
        """지역 검색 (부분 매칭)"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT region_cd, region_nm, sido_nm, sido_cd, region_type
            FROM region_codes
            WHERE region_nm LIKE ? OR sido_nm LIKE ?
            ORDER BY sido_cd, region_cd
            LIMIT ?
        """, (f'%{keyword}%', f'%{keyword}%', limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_all_regions(self, sido: Optional[str] = None, region_type: Optional[str] = None) -> List[Dict]:
        """전체 지역코드 조회"""
        conn = self.connect()

        query = "SELECT region_cd, region_nm, sido_nm, sido_cd, region_type FROM region_codes WHERE 1=1"
        params = []

        if sido:
            query += " AND sido_nm = ?"
            params.append(sido)

        if region_type:
            query += " AND region_type = ?"
            params.append(region_type)

        query += " ORDER BY sido_cd, region_cd"

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_sidos(self) -> List[Dict]:
        """시/도 목록 조회"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT DISTINCT sido_nm, sido_cd, region_type,
                   COUNT(*) as region_count
            FROM region_codes
            GROUP BY sido_nm, sido_cd, region_type
            ORDER BY sido_cd
        """)
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 동기화 로그 ====================

    def _log_sync(self, sync_type: str, target: Optional[str], count: int):
        """동기화 로그 기록"""
        conn = self.connect()
        conn.execute("""
            INSERT INTO sync_log (sync_type, target, count, synced_at)
            VALUES (?, ?, ?, ?)
        """, (sync_type, target, count, datetime.now().isoformat()))
        conn.commit()

    def get_last_sync(self, sync_type: str) -> Optional[Dict]:
        """마지막 동기화 정보 조회"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT sync_type, target, count, synced_at
            FROM sync_log
            WHERE sync_type = ?
            ORDER BY synced_at DESC
            LIMIT 1
        """, (sync_type,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ==================== 통계 ====================

    def get_stats(self) -> Dict:
        """메타DB 통계"""
        conn = self.connect()
        stats = {}

        cursor = conn.execute("SELECT COUNT(*) FROM region_codes")
        stats['regions'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM dealing_codes")
        stats['dealing_codes'] = cursor.fetchone()[0]

        # 시도별 수
        cursor = conn.execute("""
            SELECT sido_nm, COUNT(*) as cnt FROM region_codes
            GROUP BY sido_nm
            ORDER BY sido_cd
        """)
        stats['by_sido'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 유형별 수
        cursor = conn.execute("""
            SELECT region_type, COUNT(*) as cnt FROM region_codes
            GROUP BY region_type
        """)
        stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 마지막 동기화
        last_sync = self.get_last_sync('regions')
        stats['last_sync'] = last_sync['synced_at'] if last_sync else None

        return stats


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='APT 메타데이터 DB 관리')
    parser.add_argument('--load-csv', action='store_true', help='CSV에서 지역코드 로드')
    parser.add_argument('--regions', action='store_true', help='지역코드 목록')
    parser.add_argument('--sido', type=str, help='시도 필터')
    parser.add_argument('--type', type=str, help='유형 필터 (서울/경기/광역시/도/세종)')
    parser.add_argument('--search', '-s', type=str, help='지역 검색')
    parser.add_argument('--sidos', action='store_true', help='시/도 목록')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    db = AptMetaDB(args.db)

    try:
        if args.load_csv:
            count = db.load_regions_from_csv()
            print(f"지역코드 {count}개 로드 완료")

        elif args.search:
            results = db.search_regions(args.search)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            print(f"{'코드':<8} {'지역명':<15} {'시도':<8} {'유형':<8}")
            print("-" * 45)
            for r in results:
                print(f"{r['region_cd']:<8} {r['region_nm']:<15} {r['sido_nm']:<8} {r['region_type']:<8}")

        elif args.regions:
            regions = db.get_all_regions(sido=args.sido, region_type=args.type)
            title = "지역코드 목록"
            if args.sido:
                title += f" ({args.sido})"
            if args.type:
                title += f" [{args.type}]"
            print(f"\n=== {title} ({len(regions)}개) ===")
            print(f"{'코드':<8} {'지역명':<15} {'시도':<8} {'유형':<8}")
            print("-" * 45)
            for r in regions:
                print(f"{r['region_cd']:<8} {r['region_nm']:<15} {r['sido_nm']:<8} {r['region_type']:<8}")

        elif args.sidos:
            sidos = db.get_sidos()
            print(f"\n=== 시/도 목록 ({len(sidos)}개) ===")
            print(f"{'시도코드':<8} {'시도명':<10} {'유형':<8} {'지역수':<8}")
            print("-" * 40)
            for s in sidos:
                print(f"{s['sido_cd']:<8} {s['sido_nm']:<10} {s['region_type']:<8} {s['region_count']:<8}")

        elif args.stats:
            stats = db.get_stats()
            print("\n=== APT 메타DB 통계 ===")
            print(f"등록 지역: {stats['regions']}개")
            print(f"거래유형 코드: {stats['dealing_codes']}개")

            if stats.get('by_sido'):
                print("\n시도별 지역 수:")
                for sido, cnt in stats['by_sido'].items():
                    print(f"  {sido}: {cnt}개")

            if stats.get('by_type'):
                print("\n유형별 지역 수:")
                for rtype, cnt in stats['by_type'].items():
                    print(f"  {rtype}: {cnt}개")

            if stats.get('last_sync'):
                print(f"\n마지막 동기화: {stats['last_sync'][:19]}")

        else:
            # 기본: 지역코드가 없으면 CSV 로드
            stats = db.get_stats()
            if stats['regions'] == 0:
                print("지역코드가 없습니다. CSV에서 로드합니다...")
                count = db.load_regions_from_csv()
                print(f"지역코드 {count}개 로드 완료")
            else:
                parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
