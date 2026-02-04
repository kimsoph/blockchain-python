# -*- coding: utf-8 -*-
"""
FSC 메타데이터 DB 관리
금융위원회 국내은행정보 API - 은행 마스터 및 코드 참조 관리

Author: Claude Code
Version: 1.0.0
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


class FscMetaDB:
    """FSC 메타데이터 DB 관리 클래스"""

    # DB 스키마
    SCHEMA = """
    -- 은행 마스터
    CREATE TABLE IF NOT EXISTS banks (
        id INTEGER PRIMARY KEY,
        bank_cd TEXT UNIQUE,        -- 은행코드 (API에서 제공 시)
        bank_nm TEXT NOT NULL,      -- 은행명
        bank_type TEXT,             -- 은행유형 (시중/지방/특수/외국계)
        group_nm TEXT,              -- 소속 금융지주
        crno TEXT,                  -- 법인등록번호
        updated_at TEXT
    );

    -- 데이터 유형 참조
    CREATE TABLE IF NOT EXISTS data_types (
        code TEXT PRIMARY KEY,      -- general/finance/metrics/business
        name TEXT NOT NULL,         -- 일반현황/재무현황/경영지표/영업활동
        operation TEXT NOT NULL,    -- API 오퍼레이션명
        description TEXT
    );

    -- 경영지표 코드 참조
    CREATE TABLE IF NOT EXISTS metric_codes (
        code TEXT PRIMARY KEY,      -- ROA/ROE/NIM/BIS/NPL/LDR
        name TEXT NOT NULL,         -- 총자산순이익률/자기자본순이익률/...
        unit TEXT,                  -- % 등
        description TEXT
    );

    -- 동기화 로그
    CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY,
        sync_type TEXT NOT NULL,    -- banks/data
        target TEXT,                -- 동기화 대상
        count INTEGER,              -- 동기화 건수
        synced_at TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_bank_nm ON banks(bank_nm);
    CREATE INDEX IF NOT EXISTS idx_bank_type ON banks(bank_type);
    """

    # 은행 마스터 데이터 (하드코딩)
    BANKS = [
        # 시중은행
        ('B001', 'KB국민은행', '시중은행', 'KB금융지주', None),
        ('B002', '신한은행', '시중은행', '신한금융지주', None),
        ('B003', '하나은행', '시중은행', '하나금융지주', None),
        ('B004', '우리은행', '시중은행', '우리금융지주', None),
        ('B005', 'SC제일은행', '시중은행', None, None),
        ('B006', '한국씨티은행', '시중은행', None, None),
        # 특수은행
        ('B101', 'IBK기업은행', '특수은행', None, None),
        ('B102', 'NH농협은행', '특수은행', '농협금융지주', None),
        ('B103', 'KDB산업은행', '특수은행', None, None),
        ('B104', '한국수출입은행', '특수은행', None, None),
        ('B105', 'SH수협은행', '특수은행', None, None),
        # 지방은행
        ('B201', 'DGB대구은행', '지방은행', 'DGB금융지주', None),
        ('B202', 'BNK부산은행', '지방은행', 'BNK금융지주', None),
        ('B203', 'BNK경남은행', '지방은행', 'BNK금융지주', None),
        ('B204', '광주은행', '지방은행', 'JB금융지주', None),
        ('B205', '전북은행', '지방은행', 'JB금융지주', None),
        ('B206', '제주은행', '지방은행', '신한금융지주', None),
        # 인터넷전문은행
        ('B301', '카카오뱅크', '인터넷전문', None, None),
        ('B302', '케이뱅크', '인터넷전문', None, None),
        ('B303', '토스뱅크', '인터넷전문', None, None),
    ]

    # 데이터 유형
    DATA_TYPES = [
        ('general', '일반현황', 'getDomeBankGeneInfo', '설립년도, 점포수, 임직원수 등'),
        ('finance', '재무현황', 'getDomeBankFinaInfo', '자산, 부채, 자본 등'),
        ('metrics', '경영지표', 'getDomeBankKeyManaIndi', 'ROA, ROE, NIM, BIS비율 등'),
        ('business', '영업활동', 'getDomeBankMajoBusiActi', '대출금, 예수금, 유가증권 등'),
    ]

    # 경영지표 코드
    METRIC_CODES = [
        ('ROA', '총자산순이익률', '%', 'Return on Assets'),
        ('ROE', '자기자본순이익률', '%', 'Return on Equity'),
        ('NIM', '순이자마진', '%', 'Net Interest Margin'),
        ('BIS', 'BIS자기자본비율', '%', 'BIS Capital Ratio'),
        ('NPL', '고정이하여신비율', '%', 'Non-Performing Loan Ratio'),
        ('LDR', '예대율', '%', 'Loan to Deposit Ratio'),
        ('CIR', '영업이익경비율', '%', 'Cost to Income Ratio'),
    ]

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent / 'data'
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / 'fsc_meta.db')

        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _init_db(self):
        """DB 초기화 (스키마 및 기본 데이터 생성)"""
        conn = self.connect()
        conn.executescript(self.SCHEMA)

        # 은행 마스터 삽입
        now = datetime.now().isoformat()
        conn.executemany("""
            INSERT OR IGNORE INTO banks (bank_cd, bank_nm, bank_type, group_nm, crno, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(b[0], b[1], b[2], b[3], b[4], now) for b in self.BANKS])

        # 데이터 유형 삽입
        conn.executemany("""
            INSERT OR IGNORE INTO data_types (code, name, operation, description)
            VALUES (?, ?, ?, ?)
        """, self.DATA_TYPES)

        # 경영지표 코드 삽입
        conn.executemany("""
            INSERT OR IGNORE INTO metric_codes (code, name, unit, description)
            VALUES (?, ?, ?, ?)
        """, self.METRIC_CODES)

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

    # ==================== 은행 관련 ====================

    def get_bank(self, bank_nm: str) -> Optional[Dict]:
        """은행 정보 조회 (정확한 이름 매칭)"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT bank_cd, bank_nm, bank_type, group_nm
            FROM banks
            WHERE bank_nm = ?
        """, (bank_nm,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_banks(self, keyword: str, limit: int = 20) -> List[Dict]:
        """은행 검색 (부분 매칭)"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT bank_cd, bank_nm, bank_type, group_nm
            FROM banks
            WHERE bank_nm LIKE ? OR group_nm LIKE ?
            ORDER BY bank_type, bank_nm
            LIMIT ?
        """, (f'%{keyword}%', f'%{keyword}%', limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_all_banks(self, bank_type: Optional[str] = None) -> List[Dict]:
        """전체 은행 목록 조회"""
        conn = self.connect()
        if bank_type:
            cursor = conn.execute("""
                SELECT bank_cd, bank_nm, bank_type, group_nm
                FROM banks
                WHERE bank_type = ?
                ORDER BY bank_nm
            """, (bank_type,))
        else:
            cursor = conn.execute("""
                SELECT bank_cd, bank_nm, bank_type, group_nm
                FROM banks
                ORDER BY bank_type, bank_nm
            """)
        return [dict(row) for row in cursor.fetchall()]

    def get_bank_types(self) -> List[str]:
        """은행 유형 목록"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT DISTINCT bank_type FROM banks ORDER BY bank_type
        """)
        return [row[0] for row in cursor.fetchall()]

    # ==================== 데이터 유형 관련 ====================

    def get_data_type(self, code: str) -> Optional[Dict]:
        """데이터 유형 정보 조회"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT code, name, operation, description
            FROM data_types
            WHERE code = ?
        """, (code,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_data_types(self) -> List[Dict]:
        """전체 데이터 유형 목록"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT code, name, operation, description FROM data_types
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_operation(self, code: str) -> Optional[str]:
        """데이터 유형 코드로 API 오퍼레이션명 조회"""
        dtype = self.get_data_type(code)
        return dtype['operation'] if dtype else None

    # ==================== 경영지표 관련 ====================

    def get_metric(self, code: str) -> Optional[Dict]:
        """경영지표 정보 조회"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT code, name, unit, description
            FROM metric_codes
            WHERE code = ?
        """, (code.upper(),))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_metrics(self) -> List[Dict]:
        """전체 경영지표 목록"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT code, name, unit, description FROM metric_codes
        """)
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 동기화 로그 ====================

    def log_sync(self, sync_type: str, target: Optional[str], count: int):
        """동기화 로그 기록"""
        conn = self.connect()
        conn.execute("""
            INSERT INTO sync_log (sync_type, target, count, synced_at)
            VALUES (?, ?, ?, ?)
        """, (sync_type, target, count, datetime.now().isoformat()))
        conn.commit()

    def get_last_sync(self, sync_type: str, target: Optional[str] = None) -> Optional[Dict]:
        """마지막 동기화 정보 조회"""
        conn = self.connect()
        if target:
            cursor = conn.execute("""
                SELECT sync_type, target, count, synced_at
                FROM sync_log
                WHERE sync_type = ? AND target = ?
                ORDER BY synced_at DESC
                LIMIT 1
            """, (sync_type, target))
        else:
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

        cursor = conn.execute("SELECT COUNT(*) FROM banks")
        stats['banks'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM data_types")
        stats['data_types'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM metric_codes")
        stats['metrics'] = cursor.fetchone()[0]

        # 은행 유형별 수
        cursor = conn.execute("""
            SELECT bank_type, COUNT(*) as cnt FROM banks
            GROUP BY bank_type
        """)
        stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 마지막 동기화
        cursor = conn.execute("""
            SELECT sync_type, MAX(synced_at) as last_sync
            FROM sync_log
            GROUP BY sync_type
        """)
        stats['last_syncs'] = {row[0]: row[1] for row in cursor.fetchall()}

        return stats


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='FSC 메타데이터 DB 관리')
    parser.add_argument('--banks', action='store_true', help='은행 목록')
    parser.add_argument('--bank-type', type=str, help='은행 유형 필터')
    parser.add_argument('--search', '-s', type=str, help='은행 검색')
    parser.add_argument('--types', action='store_true', help='데이터 유형 목록')
    parser.add_argument('--metrics', action='store_true', help='경영지표 목록')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    db = FscMetaDB(args.db)

    try:
        if args.banks:
            banks = db.get_all_banks(args.bank_type)
            print(f"\n=== 은행 목록 ({len(banks)}개) ===")
            print(f"{'은행코드':<8} {'은행명':<20} {'유형':<12} {'금융지주':<15}")
            print("-" * 60)
            for b in banks:
                print(f"{b['bank_cd']:<8} {b['bank_nm']:<20} {b['bank_type']:<12} {b['group_nm'] or '-':<15}")

        elif args.search:
            results = db.search_banks(args.search)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            for b in results:
                print(f"  {b['bank_nm']} ({b['bank_type']})")

        elif args.types:
            types = db.get_all_data_types()
            print("\n=== 데이터 유형 ===")
            for t in types:
                print(f"  {t['code']:<10} {t['name']:<10} → {t['operation']}")
                print(f"             {t['description']}")

        elif args.metrics:
            metrics = db.get_all_metrics()
            print("\n=== 경영지표 코드 ===")
            print(f"{'코드':<6} {'지표명':<20} {'단위':<5} {'설명':<25}")
            print("-" * 60)
            for m in metrics:
                print(f"{m['code']:<6} {m['name']:<20} {m['unit']:<5} {m['description']:<25}")

        elif args.stats:
            stats = db.get_stats()
            print("\n=== FSC 메타DB 통계 ===")
            print(f"등록 은행: {stats['banks']}개")
            print(f"데이터 유형: {stats['data_types']}개")
            print(f"경영지표: {stats['metrics']}개")
            print("\n은행 유형별:")
            for btype, cnt in stats['by_type'].items():
                print(f"  {btype}: {cnt}개")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
