# -*- coding: utf-8 -*-
"""
APT 데이터 DB 관리
국토교통부 아파트 실거래가 API - 거래 데이터 저장/조회

Author: Claude Code
Version: 2.0.0
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# 한글 출력 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
DATA_DB_PATH = PROJECT_ROOT / '3_Resources' / 'R-DB' / 'apt.db'


class AptDataDB:
    """APT 데이터 DB 관리 클래스"""

    # DB 스키마
    SCHEMA = """
    -- 아파트 매매 거래
    CREATE TABLE IF NOT EXISTS apt_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sgg_cd TEXT NOT NULL,
        umd_cd TEXT,
        umd_nm TEXT,
        jibun TEXT,
        apt_seq TEXT,
        apt_nm TEXT NOT NULL,
        apt_dong TEXT,
        build_year INTEGER,
        deal_year INTEGER NOT NULL,
        deal_month INTEGER NOT NULL,
        deal_day INTEGER,
        deal_amount TEXT,
        deal_amount_num INTEGER,
        exclu_use_ar REAL,
        floor INTEGER,
        dealing_gbn TEXT,
        buyer_gbn TEXT,
        sler_gbn TEXT,
        road_nm TEXT,
        road_nm_bonbun TEXT,
        road_nm_bubun TEXT,
        cdeal_day TEXT,
        cdeal_type TEXT,
        land_leasehold_gbn TEXT,
        rgst_date TEXT,
        estate_agent_sgg_nm TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(apt_seq, deal_year, deal_month, deal_day, floor, exclu_use_ar)
    );

    -- 아파트 전월세 거래
    CREATE TABLE IF NOT EXISTS apt_rents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sgg_cd TEXT NOT NULL,
        umd_nm TEXT,
        jibun TEXT,
        apt_nm TEXT NOT NULL,
        build_year INTEGER,
        deal_year INTEGER NOT NULL,
        deal_month INTEGER NOT NULL,
        deal_day INTEGER,
        deposit INTEGER,
        monthly_rent INTEGER,
        exclu_use_ar REAL,
        floor INTEGER,
        contract_term TEXT,
        contract_type TEXT,
        use_rr_right TEXT,
        pre_deposit INTEGER,
        pre_monthly_rent INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(sgg_cd, apt_nm, deal_year, deal_month, deal_day, floor, exclu_use_ar, deposit, monthly_rent)
    );

    -- 매매 동기화 상태
    CREATE TABLE IF NOT EXISTS sync_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sgg_cd TEXT NOT NULL,
        deal_ym TEXT NOT NULL,
        total_count INTEGER,
        synced_count INTEGER,
        synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(sgg_cd, deal_ym)
    );

    -- 전월세 동기화 상태
    CREATE TABLE IF NOT EXISTS rent_sync_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sgg_cd TEXT NOT NULL,
        deal_ym TEXT NOT NULL,
        total_count INTEGER,
        synced_count INTEGER,
        synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(sgg_cd, deal_ym)
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_apt_sgg ON apt_trades(sgg_cd);
    CREATE INDEX IF NOT EXISTS idx_apt_name ON apt_trades(apt_nm);
    CREATE INDEX IF NOT EXISTS idx_apt_deal_date ON apt_trades(deal_year, deal_month);
    CREATE INDEX IF NOT EXISTS idx_apt_umd ON apt_trades(umd_nm);
    CREATE INDEX IF NOT EXISTS idx_apt_amount ON apt_trades(deal_amount_num DESC);

    CREATE INDEX IF NOT EXISTS idx_rent_sgg ON apt_rents(sgg_cd);
    CREATE INDEX IF NOT EXISTS idx_rent_name ON apt_rents(apt_nm);
    CREATE INDEX IF NOT EXISTS idx_rent_deal_date ON apt_rents(deal_year, deal_month);
    CREATE INDEX IF NOT EXISTS idx_rent_umd ON apt_rents(umd_nm);
    CREATE INDEX IF NOT EXISTS idx_rent_deposit ON apt_rents(deposit DESC);
    """

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            DATA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            db_path = str(DATA_DB_PATH)

        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _init_db(self):
        """DB 초기화 (스키마 생성)"""
        conn = self.connect()
        conn.executescript(self.SCHEMA)
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

    # ==================== 매매 거래 ====================

    def insert_trades(self, trades: List[Dict[str, Any]]) -> int:
        """매매 거래 데이터 삽입"""
        conn = self.connect()
        inserted = 0

        for tx in trades:
            try:
                # 거래금액 숫자 변환
                amount_str = tx.get('deal_amount', '0') or '0'
                amount_num = int(amount_str.replace(',', '').strip()) if amount_str.strip() else 0

                conn.execute('''
                    INSERT OR IGNORE INTO apt_trades (
                        sgg_cd, umd_cd, umd_nm, jibun,
                        apt_seq, apt_nm, apt_dong, build_year,
                        deal_year, deal_month, deal_day, deal_amount, deal_amount_num,
                        exclu_use_ar, floor, dealing_gbn,
                        buyer_gbn, sler_gbn,
                        road_nm, road_nm_bonbun, road_nm_bubun,
                        cdeal_day, cdeal_type,
                        land_leasehold_gbn, rgst_date, estate_agent_sgg_nm
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tx.get('sgg_cd'), tx.get('umd_cd'), tx.get('umd_nm'), tx.get('jibun'),
                    tx.get('apt_seq'), tx.get('apt_nm'), tx.get('apt_dong'), tx.get('build_year'),
                    tx.get('deal_year'), tx.get('deal_month'), tx.get('deal_day'),
                    tx.get('deal_amount'), amount_num,
                    tx.get('exclu_use_ar'), tx.get('floor'), tx.get('dealing_gbn'),
                    tx.get('buyer_gbn'), tx.get('sler_gbn'),
                    tx.get('road_nm'), tx.get('road_nm_bonbun'), tx.get('road_nm_bubun'),
                    tx.get('cdeal_day'), tx.get('cdeal_type'),
                    tx.get('land_leasehold_gbn'), tx.get('rgst_date'), tx.get('estate_agent_sgg_nm')
                ))
                if conn.total_changes > inserted:
                    inserted = conn.total_changes
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def search(self, keyword: str, sgg_cd: str = None, limit: int = 100) -> List[Dict]:
        """매매 아파트명/법정동 검색"""
        conn = self.connect()

        query = '''
            SELECT * FROM apt_trades
            WHERE (apt_nm LIKE ? OR umd_nm LIKE ?)
        '''
        params = [f'%{keyword}%', f'%{keyword}%']

        if sgg_cd:
            query += ' AND sgg_cd = ?'
            params.append(sgg_cd)

        query += ' ORDER BY deal_year DESC, deal_month DESC, deal_day DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_top_trades(self, limit: int = 20, sgg_cd: str = None, deal_ym: str = None) -> List[Dict]:
        """고가 매매 TOP N 조회"""
        conn = self.connect()

        query = 'SELECT * FROM apt_trades WHERE deal_amount_num > 0'
        params = []

        if sgg_cd:
            query += ' AND sgg_cd = ?'
            params.append(sgg_cd)

        if deal_ym:
            year = int(deal_ym[:4])
            month = int(deal_ym[4:6])
            query += ' AND deal_year = ? AND deal_month = ?'
            params.extend([year, month])

        query += ' ORDER BY deal_amount_num DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_sync_status(self, sgg_cd: str, deal_ym: str, total_count: int, synced_count: int):
        """매매 동기화 상태 업데이트"""
        conn = self.connect()
        conn.execute('''
            INSERT OR REPLACE INTO sync_status (sgg_cd, deal_ym, total_count, synced_count, synced_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (sgg_cd, deal_ym, total_count, synced_count))
        conn.commit()

    def is_synced(self, sgg_cd: str, deal_ym: str) -> bool:
        """매매 동기화 여부 확인"""
        conn = self.connect()
        cursor = conn.execute('''
            SELECT COUNT(*) FROM sync_status
            WHERE sgg_cd = ? AND deal_ym = ?
        ''', (sgg_cd, deal_ym))
        return cursor.fetchone()[0] > 0

    def query_trades(
        self,
        sgg_cd: str,
        start_ym: str,
        end_ym: str,
        apt_name: Optional[str] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        min_amount: Optional[int] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """매매 데이터 기간별 조회 (DB-First용)"""
        conn = self.connect()

        # 날짜 파싱
        start_year, start_month = int(start_ym[:4]), int(start_ym[4:6])
        end_year, end_month = int(end_ym[:4]), int(end_ym[4:6])

        query = '''
            SELECT * FROM apt_trades
            WHERE sgg_cd = ?
            AND ((deal_year > ? OR (deal_year = ? AND deal_month >= ?))
            AND (deal_year < ? OR (deal_year = ? AND deal_month <= ?)))
        '''
        params: List[Any] = [sgg_cd, start_year, start_year, start_month, end_year, end_year, end_month]

        if apt_name:
            query += ' AND apt_nm LIKE ?'
            params.append(f'%{apt_name}%')

        if min_area:
            query += ' AND exclu_use_ar >= ?'
            params.append(min_area)

        if max_area:
            query += ' AND exclu_use_ar <= ?'
            params.append(max_area)

        if min_amount:
            query += ' AND deal_amount_num >= ?'
            params.append(min_amount)

        query += ' ORDER BY deal_year DESC, deal_month DESC, deal_day DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 전월세 거래 ====================

    def insert_rents(self, rents: List[Dict[str, Any]]) -> int:
        """전월세 거래 데이터 삽입"""
        conn = self.connect()
        inserted = 0

        for tx in rents:
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO apt_rents (
                        sgg_cd, umd_nm, jibun, apt_nm, build_year,
                        deal_year, deal_month, deal_day,
                        deposit, monthly_rent, exclu_use_ar, floor,
                        contract_term, contract_type, use_rr_right,
                        pre_deposit, pre_monthly_rent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tx.get('sgg_cd'), tx.get('umd_nm'), tx.get('jibun'), tx.get('apt_nm'),
                    tx.get('build_year'),
                    tx.get('deal_year'), tx.get('deal_month'), tx.get('deal_day'),
                    tx.get('deposit'), tx.get('monthly_rent'),
                    tx.get('exclu_use_ar'), tx.get('floor'),
                    tx.get('contract_term'), tx.get('contract_type'), tx.get('use_rr_right'),
                    tx.get('pre_deposit'), tx.get('pre_monthly_rent')
                ))
                if conn.total_changes > inserted:
                    inserted = conn.total_changes
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def search_rents(self, keyword: str, sgg_cd: str = None, limit: int = 100) -> List[Dict]:
        """전월세 아파트명/법정동 검색"""
        conn = self.connect()

        query = '''
            SELECT * FROM apt_rents
            WHERE (apt_nm LIKE ? OR umd_nm LIKE ?)
        '''
        params = [f'%{keyword}%', f'%{keyword}%']

        if sgg_cd:
            query += ' AND sgg_cd = ?'
            params.append(sgg_cd)

        query += ' ORDER BY deal_year DESC, deal_month DESC, deal_day DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_top_rents(self, limit: int = 20, sgg_cd: str = None, deal_ym: str = None, rent_type: str = None) -> List[Dict]:
        """고가 전월세 TOP N 조회

        Args:
            rent_type: 'jeonse' (전세), 'monthly' (월세), None (전체)
        """
        conn = self.connect()

        query = 'SELECT * FROM apt_rents WHERE deposit > 0'
        params = []

        if sgg_cd:
            query += ' AND sgg_cd = ?'
            params.append(sgg_cd)

        if deal_ym:
            year = int(deal_ym[:4])
            month = int(deal_ym[4:6])
            query += ' AND deal_year = ? AND deal_month = ?'
            params.extend([year, month])

        if rent_type == 'jeonse':
            query += ' AND (monthly_rent IS NULL OR monthly_rent = 0)'
        elif rent_type == 'monthly':
            query += ' AND monthly_rent > 0'

        query += ' ORDER BY deposit DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_rent_sync_status(self, sgg_cd: str, deal_ym: str, total_count: int, synced_count: int):
        """전월세 동기화 상태 업데이트"""
        conn = self.connect()
        conn.execute('''
            INSERT OR REPLACE INTO rent_sync_status (sgg_cd, deal_ym, total_count, synced_count, synced_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (sgg_cd, deal_ym, total_count, synced_count))
        conn.commit()

    def is_rent_synced(self, sgg_cd: str, deal_ym: str) -> bool:
        """전월세 동기화 여부 확인"""
        conn = self.connect()
        cursor = conn.execute('''
            SELECT COUNT(*) FROM rent_sync_status
            WHERE sgg_cd = ? AND deal_ym = ?
        ''', (sgg_cd, deal_ym))
        return cursor.fetchone()[0] > 0

    def query_rents(
        self,
        sgg_cd: str,
        start_ym: str,
        end_ym: str,
        apt_name: Optional[str] = None,
        rent_type: Optional[str] = None,
        min_deposit: Optional[int] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """전월세 데이터 기간별 조회 (DB-First용)

        Args:
            rent_type: 'jeonse' (전세), 'monthly' (월세), None (전체)
        """
        conn = self.connect()

        # 날짜 파싱
        start_year, start_month = int(start_ym[:4]), int(start_ym[4:6])
        end_year, end_month = int(end_ym[:4]), int(end_ym[4:6])

        query = '''
            SELECT * FROM apt_rents
            WHERE sgg_cd = ?
            AND ((deal_year > ? OR (deal_year = ? AND deal_month >= ?))
            AND (deal_year < ? OR (deal_year = ? AND deal_month <= ?)))
        '''
        params: List[Any] = [sgg_cd, start_year, start_year, start_month, end_year, end_year, end_month]

        if apt_name:
            query += ' AND apt_nm LIKE ?'
            params.append(f'%{apt_name}%')

        if rent_type == 'jeonse':
            query += ' AND (monthly_rent IS NULL OR monthly_rent = 0)'
        elif rent_type == 'monthly':
            query += ' AND monthly_rent > 0'

        if min_deposit:
            query += ' AND deposit >= ?'
            params.append(min_deposit)

        query += ' ORDER BY deal_year DESC, deal_month DESC, deal_day DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 통계 ====================

    def get_stats(self) -> Dict:
        """매매 DB 통계"""
        conn = self.connect()

        # 총 거래 건수
        cursor = conn.execute('SELECT COUNT(*) FROM apt_trades')
        total_count = cursor.fetchone()[0]

        # 지역별 건수
        cursor = conn.execute('''
            SELECT sgg_cd, COUNT(*) as cnt
            FROM apt_trades
            GROUP BY sgg_cd
            ORDER BY cnt DESC
            LIMIT 10
        ''')
        by_region = cursor.fetchall()

        # 년월별 건수
        cursor = conn.execute('''
            SELECT deal_year, deal_month, COUNT(*) as cnt
            FROM apt_trades
            GROUP BY deal_year, deal_month
            ORDER BY deal_year DESC, deal_month DESC
            LIMIT 12
        ''')
        by_month = cursor.fetchall()

        # 동기화 상태
        cursor = conn.execute('''
            SELECT sgg_cd, deal_ym, total_count, synced_count, synced_at
            FROM sync_status
            ORDER BY synced_at DESC
            LIMIT 10
        ''')
        sync_status = cursor.fetchall()

        return {
            'total_count': total_count,
            'by_region': by_region,
            'by_month': by_month,
            'sync_status': sync_status
        }

    def get_rent_stats(self) -> Dict:
        """전월세 DB 통계"""
        conn = self.connect()

        # 총 거래 건수
        cursor = conn.execute('SELECT COUNT(*) FROM apt_rents')
        total_count = cursor.fetchone()[0]

        # 전세/월세 비율
        cursor = conn.execute('SELECT COUNT(*) FROM apt_rents WHERE monthly_rent IS NULL OR monthly_rent = 0')
        jeonse_count = cursor.fetchone()[0]
        monthly_count = total_count - jeonse_count

        # 지역별 건수
        cursor = conn.execute('''
            SELECT sgg_cd, COUNT(*) as cnt
            FROM apt_rents
            GROUP BY sgg_cd
            ORDER BY cnt DESC
            LIMIT 10
        ''')
        by_region = cursor.fetchall()

        # 년월별 건수
        cursor = conn.execute('''
            SELECT deal_year, deal_month, COUNT(*) as cnt
            FROM apt_rents
            GROUP BY deal_year, deal_month
            ORDER BY deal_year DESC, deal_month DESC
            LIMIT 12
        ''')
        by_month = cursor.fetchall()

        return {
            'total_count': total_count,
            'jeonse_count': jeonse_count,
            'monthly_count': monthly_count,
            'by_region': by_region,
            'by_month': by_month
        }


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='APT 데이터 DB 관리')
    parser.add_argument('--stats', action='store_true', help='매매 DB 통계')
    parser.add_argument('--rent-stats', action='store_true', help='전월세 DB 통계')
    parser.add_argument('--search', '-s', type=str, help='매매 검색')
    parser.add_argument('--search-rent', type=str, help='전월세 검색')
    parser.add_argument('--top', type=int, help='고가 매매 TOP N')
    parser.add_argument('--top-rent', type=int, help='고가 전월세 TOP N')
    parser.add_argument('--region', '-r', type=str, help='지역코드 필터')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    db = AptDataDB(args.db)

    try:
        if args.stats:
            stats = db.get_stats()
            print(f"\n=== 매매 데이터 통계 ===")
            print(f"총 거래 건수: {stats['total_count']:,}건")

            if stats['by_region']:
                print("\n지역별 건수 (TOP 10):")
                for sgg_cd, cnt in stats['by_region']:
                    print(f"  {sgg_cd}: {cnt:,}건")

            if stats['by_month']:
                print("\n년월별 건수 (최근 12개월):")
                for year, month, cnt in stats['by_month']:
                    print(f"  {year}년 {month:02d}월: {cnt:,}건")

        elif args.rent_stats:
            stats = db.get_rent_stats()
            print(f"\n=== 전월세 데이터 통계 ===")
            print(f"총 거래 건수: {stats['total_count']:,}건")
            print(f"  - 전세: {stats['jeonse_count']:,}건")
            print(f"  - 월세: {stats['monthly_count']:,}건")

            if stats['by_region']:
                print("\n지역별 건수 (TOP 10):")
                for sgg_cd, cnt in stats['by_region']:
                    print(f"  {sgg_cd}: {cnt:,}건")

        elif args.search:
            results = db.search(args.search, sgg_cd=args.region)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            for tx in results[:20]:
                deal_date = f"{tx['deal_year']}-{tx['deal_month']:02d}-{tx['deal_day'] or 0:02d}"
                print(f"{tx['apt_nm']:<20} {tx['umd_nm'] or '':<10} {tx['deal_amount'] or ''}만원 {deal_date}")

        elif args.search_rent:
            results = db.search_rents(args.search_rent, sgg_cd=args.region)
            print(f"\n=== '{args.search_rent}' 전월세 검색 결과 ({len(results)}건) ===")
            for tx in results[:20]:
                deal_date = f"{tx['deal_year']}-{tx['deal_month']:02d}-{tx['deal_day'] or 0:02d}"
                deposit = tx['deposit'] or 0
                monthly = tx['monthly_rent'] or 0
                rent_type = '전세' if monthly == 0 else '월세'
                print(f"{tx['apt_nm']:<20} {tx['umd_nm'] or '':<10} {deposit:,}/{monthly:,} {deal_date} [{rent_type}]")

        elif args.top:
            results = db.get_top_trades(args.top, sgg_cd=args.region)
            print(f"\n=== 고가 매매 TOP {args.top} ({len(results)}건) ===")
            for i, tx in enumerate(results, 1):
                deal_date = f"{tx['deal_year']}-{tx['deal_month']:02d}-{tx['deal_day'] or 0:02d}"
                print(f"{i:>2}. {tx['apt_nm']:<20} {tx['umd_nm'] or '':<10} {tx['deal_amount'] or ''}만원 {deal_date}")

        elif args.top_rent:
            results = db.get_top_rents(args.top_rent, sgg_cd=args.region)
            print(f"\n=== 고가 전월세 TOP {args.top_rent} ({len(results)}건) ===")
            for i, tx in enumerate(results, 1):
                deal_date = f"{tx['deal_year']}-{tx['deal_month']:02d}-{tx['deal_day'] or 0:02d}"
                deposit = tx['deposit'] or 0
                monthly = tx['monthly_rent'] or 0
                rent_type = '전세' if monthly == 0 else '월세'
                print(f"{i:>2}. {tx['apt_nm']:<20} {tx['umd_nm'] or '':<10} {deposit:,}/{monthly:,} {deal_date} [{rent_type}]")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
