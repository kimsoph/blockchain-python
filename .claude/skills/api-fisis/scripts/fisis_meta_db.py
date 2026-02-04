# -*- coding: utf-8 -*-
"""
FISIS 메타데이터 DB 관리
통계표 코드, 금융회사 코드, 파라미터 형식 등을 SQLite로 관리

Author: Claude Code
Version: 1.0.0
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime
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


class FisisMetaDB:
    """FISIS 메타데이터 DB 관리 클래스"""

    SCHEMA = """
    -- 금융권역
    CREATE TABLE IF NOT EXISTS sectors (
        id INTEGER PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,        -- 'bank', 'insurance_life' 등
        part_div TEXT NOT NULL,           -- API partDiv 파라미터 (A, H, I 등)
        lrg_div TEXT,                     -- API lrgDiv 파라미터 (일부 API용)
        name TEXT NOT NULL,               -- '국내은행', '생명보험' 등
        description TEXT,
        company_count INTEGER DEFAULT 0,
        updated_at TEXT
    );

    -- 금융회사
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY,
        finance_cd TEXT UNIQUE NOT NULL,  -- FISIS 금융회사 코드
        name TEXT NOT NULL,               -- 금융회사명
        name_short TEXT,                  -- 약칭
        sector_code TEXT,                 -- 권역 코드 (FK)
        finance_path TEXT,                -- 분류 경로
        is_active INTEGER DEFAULT 1,      -- 현재 영업 중 여부
        updated_at TEXT,
        FOREIGN KEY (sector_code) REFERENCES sectors(code)
    );

    -- 통계표
    CREATE TABLE IF NOT EXISTS stat_tables (
        id INTEGER PRIMARY KEY,
        list_no TEXT UNIQUE NOT NULL,     -- 통계표 코드 (SA001, SA021 등)
        list_nm TEXT NOT NULL,            -- 통계표명
        sector_code TEXT,                 -- 권역 코드
        category TEXT,                    -- 분류 (일반현황, 재무현황, 주요경영지표 등)
        term_format TEXT DEFAULT 'YYYYMM', -- term 파라미터 형식
        term_start TEXT,                  -- 조회 가능 시작 기간
        term_end TEXT,                    -- 조회 가능 종료 기간
        requires_finance_cd INTEGER DEFAULT 1,  -- financeCd 필수 여부
        updated_at TEXT,
        FOREIGN KEY (sector_code) REFERENCES sectors(code)
    );

    -- 통계 항목 (선택적)
    CREATE TABLE IF NOT EXISTS stat_items (
        id INTEGER PRIMARY KEY,
        list_no TEXT NOT NULL,            -- 통계표 코드
        item_cd TEXT,                     -- 항목 코드
        item_nm TEXT NOT NULL,            -- 항목명
        unit TEXT,                        -- 단위 (%, 억원 등)
        description TEXT,
        FOREIGN KEY (list_no) REFERENCES stat_tables(list_no)
    );

    -- 유효 기간 캐시
    CREATE TABLE IF NOT EXISTS valid_terms (
        id INTEGER PRIMARY KEY,
        list_no TEXT NOT NULL,
        term TEXT NOT NULL,               -- 유효한 term 값
        UNIQUE(list_no, term),
        FOREIGN KEY (list_no) REFERENCES stat_tables(list_no)
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);
    CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector_code);
    CREATE INDEX IF NOT EXISTS idx_stat_tables_sector ON stat_tables(sector_code);
    CREATE INDEX IF NOT EXISTS idx_stat_items_list ON stat_items(list_no);
    """

    # 기본 권역 데이터
    DEFAULT_SECTORS = [
        ('bank', 'A', 'A', '국내은행', '시중은행, 지방은행, 특수은행'),
        ('bank_foreign', 'J', 'J', '외은지점', '외국은행 국내지점'),
        ('insurance_life', 'H', 'H', '생명보험', '생명보험사'),
        ('insurance_nonlife', 'I', 'I', '손해보험', '손해보험사'),
        ('securities', 'F', 'F', '증권사', '증권회사'),
        ('asset_mgmt', 'G', 'G', '자산운용', '자산운용사'),
        ('savings', 'E', 'E', '저축은행', '저축은행'),
        ('card', 'C', 'C', '신용카드', '신용카드사'),
        ('lease', 'K', 'K', '리스', '리스사'),
        ('installment', 'T', 'T', '할부금융', '할부금융사'),
        ('holding', 'L', 'L', '금융지주', '금융지주회사'),
        ('credit_union', 'O', 'O', '신협', '신용협동조합'),
        ('nacf', 'Q', 'Q', '농협', '농업협동조합'),
        ('nffc', 'P', 'P', '수협', '수협단위조합'),
        ('futures', 'W', 'W', '선물사', '선물회사'),
        ('advisory', 'X', 'X', '투자자문', '투자자문사'),
    ]

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            # 기본 경로: .claude/skills/api-fisis/data/fisis_meta.db
            base_dir = Path(__file__).parent.parent / 'data'
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / 'fisis_meta.db')

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
        return os.getenv('FISIS_API_KEY', '')

    def connect(self):
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

        # 기본 권역 데이터 삽입
        now = datetime.now().isoformat()
        conn.executemany("""
            INSERT OR IGNORE INTO sectors (code, part_div, lrg_div, name, description, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(s[0], s[1], s[2], s[3], s[4], now) for s in self.DEFAULT_SECTORS])

        conn.commit()
        print(f"DB 초기화 완료: {self.db_path}")
        return True

    def fetch_companies(self, sector_code: str = 'bank') -> int:
        """API에서 금융회사 목록 가져와서 DB에 저장"""
        if not self.api_key:
            print("API 키가 설정되지 않았습니다.")
            return 0

        conn = self.connect()

        # 권역 정보 조회
        cursor = conn.execute(
            "SELECT part_div FROM sectors WHERE code = ?", (sector_code,)
        )
        row = cursor.fetchone()
        if not row:
            print(f"알 수 없는 권역: {sector_code}")
            return 0

        part_div = row['part_div']

        # API 호출
        url = "http://fisis.fss.or.kr/openapi/companySearch.json"
        params = {
            'auth': self.api_key,
            'lang': 'kr',
            'partDiv': part_div
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.encoding = 'utf-8'
            data = resp.json()

            if 'result' not in data or 'list' not in data['result']:
                print(f"API 오류: {data.get('result', {}).get('err_msg', 'Unknown')}")
                return 0

            companies = data['result']['list']
            now = datetime.now().isoformat()

            # DB에 저장
            for co in companies:
                is_active = 0 if '[폐]' in co.get('finance_nm', '') else 1
                name_short = co.get('finance_nm', '').replace('주식회사 ', '').replace('(주)', '')

                conn.execute("""
                    INSERT OR REPLACE INTO companies
                    (finance_cd, name, name_short, sector_code, finance_path, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    co.get('finance_cd'),
                    co.get('finance_nm'),
                    name_short,
                    sector_code,
                    co.get('finance_path'),
                    is_active,
                    now
                ))

            # 권역의 회사 수 업데이트
            conn.execute("""
                UPDATE sectors SET company_count = ?, updated_at = ?
                WHERE code = ?
            """, (len(companies), now, sector_code))

            conn.commit()
            print(f"{sector_code}: {len(companies)}개 금융회사 저장")
            return len(companies)

        except Exception as e:
            print(f"API 호출 실패: {e}")
            return 0

    def fetch_stat_tables(self, sector_code: str = 'bank') -> int:
        """API에서 통계표 목록 가져와서 DB에 저장"""
        if not self.api_key:
            print("API 키가 설정되지 않았습니다.")
            return 0

        conn = self.connect()

        # 권역 정보 조회
        cursor = conn.execute(
            "SELECT lrg_div FROM sectors WHERE code = ?", (sector_code,)
        )
        row = cursor.fetchone()
        if not row:
            print(f"알 수 없는 권역: {sector_code}")
            return 0

        lrg_div = row['lrg_div']

        # API 호출
        url = "http://fisis.fss.or.kr/openapi/statisticsListSearch.json"
        params = {
            'auth': self.api_key,
            'lang': 'kr',
            'lrgDiv': lrg_div
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.encoding = 'utf-8'
            data = resp.json()

            if 'result' not in data or 'list' not in data['result']:
                print(f"API 오류: {data.get('result', {}).get('err_msg', 'Unknown')}")
                return 0

            tables = data['result']['list']
            now = datetime.now().isoformat()

            # DB에 저장
            for tbl in tables:
                conn.execute("""
                    INSERT OR REPLACE INTO stat_tables
                    (list_no, list_nm, sector_code, category, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    tbl.get('list_no'),
                    tbl.get('list_nm'),
                    sector_code,
                    tbl.get('sml_div_nm'),
                    now
                ))

            conn.commit()
            print(f"{sector_code}: {len(tables)}개 통계표 저장")
            return len(tables)

        except Exception as e:
            print(f"API 호출 실패: {e}")
            return 0

    def get_company_code(self, name: str) -> Optional[str]:
        """회사명으로 finance_cd 조회"""
        conn = self.connect()

        # 정확한 매칭 시도
        cursor = conn.execute(
            "SELECT finance_cd FROM companies WHERE name = ? AND is_active = 1",
            (name,)
        )
        row = cursor.fetchone()
        if row:
            return row['finance_cd']

        # 부분 매칭 시도
        cursor = conn.execute(
            "SELECT finance_cd, name FROM companies WHERE name LIKE ? AND is_active = 1",
            (f'%{name}%',)
        )
        row = cursor.fetchone()
        if row:
            return row['finance_cd']

        return None

    def get_stat_table(self, keyword: str) -> Optional[Dict]:
        """키워드로 통계표 조회"""
        conn = self.connect()

        cursor = conn.execute("""
            SELECT list_no, list_nm, category, term_format
            FROM stat_tables
            WHERE list_nm LIKE ? OR list_no = ?
        """, (f'%{keyword}%', keyword))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def search_companies(self, keyword: str, sector: str = None) -> List[Dict]:
        """회사 검색"""
        conn = self.connect()

        if sector:
            cursor = conn.execute("""
                SELECT finance_cd, name, sector_code, is_active
                FROM companies
                WHERE (name LIKE ? OR name_short LIKE ?) AND sector_code = ?
                ORDER BY is_active DESC, name
            """, (f'%{keyword}%', f'%{keyword}%', sector))
        else:
            cursor = conn.execute("""
                SELECT finance_cd, name, sector_code, is_active
                FROM companies
                WHERE name LIKE ? OR name_short LIKE ?
                ORDER BY is_active DESC, name
            """, (f'%{keyword}%', f'%{keyword}%'))

        return [dict(row) for row in cursor.fetchall()]

    def get_db_stats(self) -> Dict:
        """DB 통계 조회"""
        conn = self.connect()

        stats = {}

        cursor = conn.execute("SELECT COUNT(*) FROM sectors")
        stats['sectors'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM companies")
        stats['companies'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM companies WHERE is_active = 1")
        stats['active_companies'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM stat_tables")
        stats['stat_tables'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM stat_items")
        stats['stat_items'] = cursor.fetchone()[0]

        return stats

    def fetch_stat_items(self, list_no: str, sector_code: str = 'bank') -> int:
        """통계표의 항목 목록을 API에서 가져와 저장"""
        if not self.api_key:
            print("API 키가 설정되지 않았습니다.")
            return 0

        conn = self.connect()

        # 해당 권역의 첫 번째 활성 회사 코드 가져오기
        cursor = conn.execute("""
            SELECT finance_cd FROM companies
            WHERE sector_code = ? AND is_active = 1
            LIMIT 1
        """, (sector_code,))
        row = cursor.fetchone()
        if not row:
            print(f"활성 회사 없음: {sector_code}")
            return 0

        finance_cd = row['finance_cd']

        # API 호출 (최근 연도 데이터)
        import datetime
        year = datetime.datetime.now().year - 1  # 작년 데이터
        url = "http://fisis.fss.or.kr/openapi/statisticsInfoSearch.json"
        params = {
            'auth': self.api_key,
            'lang': 'kr',
            'listNo': list_no,
            'financeCd': finance_cd,
            'term': 'Y',
            'startBaseMm': f'{year}01',
            'endBaseMm': f'{year}12',
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.encoding = 'utf-8'
            data = resp.json()

            if 'result' not in data or data['result'].get('err_cd') != '000':
                err = data.get('result', {}).get('err_msg', 'Unknown')
                print(f"API 오류 ({list_no}): {err}")
                return 0

            items = data['result'].get('list', [])
            if not items:
                print(f"항목 없음: {list_no}")
                return 0

            # 중복 제거하며 항목 저장
            seen = set()
            count = 0
            unit = data['result'].get('unit', '')

            for item in items:
                item_cd = item.get('account_cd', item.get('itm_cd', ''))
                item_nm = item.get('account_nm', item.get('itm_nm', ''))

                if not item_nm or item_nm in seen:
                    continue
                seen.add(item_nm)

                conn.execute("""
                    INSERT OR REPLACE INTO stat_items (list_no, item_cd, item_nm, unit)
                    VALUES (?, ?, ?, ?)
                """, (list_no, item_cd, item_nm, unit))
                count += 1

            conn.commit()
            print(f"{list_no}: {count}개 항목 저장")
            return count

        except Exception as e:
            print(f"API 호출 실패 ({list_no}): {e}")
            return 0

    def fetch_common_stat_items(self) -> int:
        """주요 통계표의 항목 수집"""
        # 자주 사용하는 통계표 목록 (실제 API 코드 기준)
        common_tables = [
            # 은행 (SA)
            ('SA003', 'bank'),  # 요약재무상태표(자산)
            ('SA004', 'bank'),  # 요약재무상태표(부채/자본)
            ('SA021', 'bank'),  # 요약손익계산서
            ('SA017', 'bank'),  # 수익성지표
            # 증권 (SF)
            ('SF003', 'securities'),  # 요약재무상태표(자산)
            ('SF004', 'securities'),  # 요약재무상태표(부채/자본)
            ('SF007', 'securities'),  # 요약손익계산서
            # 생명보험 (SH)
            ('SH001', 'insurance_life'),  # 요약재무상태표
            ('SH003', 'insurance_life'),  # 요약손익계산서
            # 손해보험 (SI)
            ('SI001', 'insurance_nonlife'),  # 요약재무상태표
            ('SI003', 'insurance_nonlife'),  # 요약손익계산서
            # 금융지주 (SL)
            ('SL003', 'holding'),  # 연결재무상태표(자산)
            ('SL004', 'holding'),  # 연결재무상태표(부채/자본)
            ('SL006', 'holding'),  # 연결손익계산서
        ]

        total = 0
        for list_no, sector in common_tables:
            count = self.fetch_stat_items(list_no, sector)
            total += count

        return total


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='FISIS 메타데이터 DB 관리')
    parser.add_argument('--init', action='store_true', help='DB 초기화')
    parser.add_argument('--fetch-companies', type=str, metavar='SECTOR',
                        help='금융회사 목록 가져오기 (권역 코드)')
    parser.add_argument('--fetch-all-companies', action='store_true',
                        help='모든 권역의 금융회사 가져오기 (16개 권역)')
    parser.add_argument('--fetch-tables', type=str, metavar='SECTOR',
                        help='통계표 목록 가져오기 (권역 코드)')
    parser.add_argument('--fetch-all-tables', action='store_true',
                        help='모든 권역의 통계표 가져오기 (16개 권역)')
    parser.add_argument('--sync-all', action='store_true',
                        help='전체 동기화 (금융회사 + 통계표, 16개 권역)')
    parser.add_argument('--fetch-items', action='store_true',
                        help='주요 통계표 항목 수집 (은행, 증권, 보험, 금융지주)')
    parser.add_argument('--search', type=str, metavar='KEYWORD',
                        help='회사 검색')
    parser.add_argument('--get-code', type=str, metavar='NAME',
                        help='회사 코드 조회')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    db = FisisMetaDB(args.db)

    try:
        if args.init:
            db.init_db()

        elif args.fetch_companies:
            db.fetch_companies(args.fetch_companies)

        elif args.fetch_all_companies:
            db.init_db()
            # 모든 16개 권역 동기화
            all_sectors = [
                'bank', 'bank_foreign', 'insurance_life', 'insurance_nonlife',
                'securities', 'asset_mgmt', 'savings', 'card', 'lease',
                'installment', 'holding', 'credit_union', 'nacf', 'nffc',
                'futures', 'advisory'
            ]
            for sector in all_sectors:
                db.fetch_companies(sector)

        elif args.fetch_tables:
            db.fetch_stat_tables(args.fetch_tables)

        elif args.fetch_all_tables:
            db.init_db()
            # 모든 16개 권역 통계표 동기화
            all_sectors = [
                'bank', 'bank_foreign', 'insurance_life', 'insurance_nonlife',
                'securities', 'asset_mgmt', 'savings', 'card', 'lease',
                'installment', 'holding', 'credit_union', 'nacf', 'nffc',
                'futures', 'advisory'
            ]
            for sector in all_sectors:
                db.fetch_stat_tables(sector)

        elif args.sync_all:
            print("=== 전체 동기화 시작 ===")
            db.init_db()
            all_sectors = [
                'bank', 'bank_foreign', 'insurance_life', 'insurance_nonlife',
                'securities', 'asset_mgmt', 'savings', 'card', 'lease',
                'installment', 'holding', 'credit_union', 'nacf', 'nffc',
                'futures', 'advisory'
            ]
            print("\n[1/2] 금융회사 동기화")
            for sector in all_sectors:
                db.fetch_companies(sector)
            print("\n[2/2] 통계표 동기화")
            for sector in all_sectors:
                db.fetch_stat_tables(sector)
            print("\n=== 전체 동기화 완료 ===")

        elif args.fetch_items:
            print("=== 주요 통계표 항목 수집 ===")
            total = db.fetch_common_stat_items()
            print(f"\n총 {total}개 항목 저장 완료")

        elif args.search:
            results = db.search_companies(args.search)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            for co in results[:20]:
                status = '' if co['is_active'] else ' [폐업]'
                print(f"  {co['finance_cd']}: {co['name']}{status}")

        elif args.get_code:
            code = db.get_company_code(args.get_code)
            if code:
                print(f"{args.get_code} → {code}")
            else:
                print(f"'{args.get_code}'를 찾을 수 없습니다.")

        elif args.stats:
            stats = db.get_db_stats()
            print("\n=== DB 통계 ===")
            print(f"권역: {stats['sectors']}개")
            print(f"금융회사: {stats['companies']}개 (영업중: {stats['active_companies']}개)")
            print(f"통계표: {stats['stat_tables']}개")
            print(f"통계항목: {stats['stat_items']}개")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
