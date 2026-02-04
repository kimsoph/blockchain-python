# -*- coding: utf-8 -*-
"""
금융위원회 국내은행정보 API 클라이언트

Usage:
    # 데이터 동기화
    python fsc_api.py --sync --type metrics --ym 202412
    python fsc_api.py --sync --type finance --bank "IBK기업은행" --ym 202412

    # 조회
    python fsc_api.py --metrics --bank "신한은행" --ym 202412
    python fsc_api.py --finance --bank "IBK기업은행" --ym 202412

    # 은행간 비교
    python fsc_api.py --compare --metric ROE --ym 202412

    # DB 통계
    python fsc_api.py --stats

Author: Claude Code
Version: 1.0.0
"""

import os
import sys
import json
import csv
import sqlite3
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# 한글 출력 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# 경로 설정
SKILL_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = SKILL_ROOT.parent.parent.parent
ENV_PATH = PROJECT_ROOT / '.claude' / '.env'

if load_dotenv:
    load_dotenv(ENV_PATH)

# 메타DB 임포트
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
from fsc_meta_db import FscMetaDB

# API 설정
API_KEY = os.getenv('FSC_API_KEY')
BASE_URL = os.getenv('FSC_END_POINT', 'https://apis.data.go.kr/1160100/service/GetDomeBankInfoService')

# 데이터DB 경로
DATA_DB_PATH = PROJECT_ROOT / '3_Resources' / 'R-DB' / 'fsc.db'


class FscDataDB:
    """FSC 데이터 DB 관리 클래스"""

    SCHEMA = """
    -- 일반현황
    CREATE TABLE IF NOT EXISTS bank_general (
        id INTEGER PRIMARY KEY,
        bas_ym TEXT NOT NULL,
        bank_nm TEXT NOT NULL,
        estb_year INTEGER,
        branch_cnt INTEGER,
        atm_cnt INTEGER,
        employee_cnt INTEGER,
        capital REAL,
        created_at TEXT,
        UNIQUE(bas_ym, bank_nm)
    );

    -- 재무현황
    CREATE TABLE IF NOT EXISTS bank_finance (
        id INTEGER PRIMARY KEY,
        bas_ym TEXT NOT NULL,
        bank_nm TEXT NOT NULL,
        total_assets REAL,
        total_liab REAL,
        total_equity REAL,
        loans REAL,
        deposits REAL,
        securities REAL,
        created_at TEXT,
        UNIQUE(bas_ym, bank_nm)
    );

    -- 경영지표
    CREATE TABLE IF NOT EXISTS bank_metrics (
        id INTEGER PRIMARY KEY,
        bas_ym TEXT NOT NULL,
        bank_nm TEXT NOT NULL,
        roa REAL,
        roe REAL,
        nim REAL,
        bis_ratio REAL,
        npl_ratio REAL,
        ldr REAL,
        cir REAL,
        created_at TEXT,
        UNIQUE(bas_ym, bank_nm)
    );

    -- 영업활동
    CREATE TABLE IF NOT EXISTS bank_business (
        id INTEGER PRIMARY KEY,
        bas_ym TEXT NOT NULL,
        bank_nm TEXT NOT NULL,
        loan_amt REAL,
        deposit_amt REAL,
        fx_deposit_amt REAL,
        securities_amt REAL,
        net_interest_income REAL,
        fee_income REAL,
        created_at TEXT,
        UNIQUE(bas_ym, bank_nm)
    );

    -- 동기화 상태
    CREATE TABLE IF NOT EXISTS data_sync_status (
        id INTEGER PRIMARY KEY,
        data_type TEXT NOT NULL,
        bas_ym TEXT NOT NULL,
        total_count INTEGER,
        synced_at TEXT,
        UNIQUE(data_type, bas_ym)
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_general_ym ON bank_general(bas_ym);
    CREATE INDEX IF NOT EXISTS idx_general_bank ON bank_general(bank_nm);
    CREATE INDEX IF NOT EXISTS idx_finance_ym ON bank_finance(bas_ym);
    CREATE INDEX IF NOT EXISTS idx_finance_bank ON bank_finance(bank_nm);
    CREATE INDEX IF NOT EXISTS idx_metrics_ym ON bank_metrics(bas_ym);
    CREATE INDEX IF NOT EXISTS idx_metrics_bank ON bank_metrics(bank_nm);
    CREATE INDEX IF NOT EXISTS idx_business_ym ON bank_business(bas_ym);
    CREATE INDEX IF NOT EXISTS idx_business_bank ON bank_business(bank_nm);
    """

    def __init__(self, db_path: Path = DATA_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """DB 스키마 초기화"""
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

    # ==================== INSERT 메서드 ====================

    def insert_general(self, items: List[Dict]) -> int:
        """일반현황 삽입 (피봇된 데이터)"""
        conn = self.connect()
        now = datetime.now().isoformat()
        inserted = 0

        for item in items:
            bas_ym = item.get('bas_ym')
            bank_nm = item.get('bank_nm')
            if not bas_ym or not bank_nm:
                continue

            try:
                conn.execute("""
                    INSERT OR REPLACE INTO bank_general (
                        bas_ym, bank_nm, estb_year, branch_cnt, atm_cnt,
                        employee_cnt, capital, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bas_ym,
                    bank_nm,
                    None,  # 설립년도는 별도 테이블
                    item.get('branch_cnt'),
                    item.get('atm_cnt'),
                    item.get('employee_cnt'),
                    None,  # 자본금은 재무현황에서
                    now
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def insert_finance(self, items: List[Dict]) -> int:
        """재무현황 삽입 (피봇된 데이터)"""
        conn = self.connect()
        now = datetime.now().isoformat()
        inserted = 0

        for item in items:
            bas_ym = item.get('bas_ym')
            bank_nm = item.get('bank_nm')
            if not bas_ym or not bank_nm:
                continue

            try:
                conn.execute("""
                    INSERT OR REPLACE INTO bank_finance (
                        bas_ym, bank_nm, total_assets, total_liab, total_equity,
                        loans, deposits, securities, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bas_ym,
                    bank_nm,
                    item.get('total_assets'),
                    item.get('total_liab'),
                    item.get('total_equity'),
                    item.get('loans'),
                    item.get('deposits'),
                    item.get('securities'),
                    now
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def insert_metrics(self, items: List[Dict]) -> int:
        """경영지표 삽입 (피봇된 데이터)"""
        conn = self.connect()
        now = datetime.now().isoformat()
        inserted = 0

        for item in items:
            bas_ym = item.get('bas_ym')
            bank_nm = item.get('bank_nm')
            if not bas_ym or not bank_nm:
                continue

            try:
                conn.execute("""
                    INSERT OR REPLACE INTO bank_metrics (
                        bas_ym, bank_nm, roa, roe, nim, bis_ratio,
                        npl_ratio, ldr, cir, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bas_ym,
                    bank_nm,
                    item.get('roa'),
                    item.get('roe'),
                    item.get('nim'),
                    item.get('bis_ratio'),
                    item.get('npl_ratio'),
                    item.get('ldr'),
                    item.get('cir'),
                    now
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def insert_business(self, items: List[Dict]) -> int:
        """영업활동 삽입 (피봇된 데이터)"""
        conn = self.connect()
        now = datetime.now().isoformat()
        inserted = 0

        for item in items:
            bas_ym = item.get('bas_ym')
            bank_nm = item.get('bank_nm')
            if not bas_ym or not bank_nm:
                continue

            try:
                conn.execute("""
                    INSERT OR REPLACE INTO bank_business (
                        bas_ym, bank_nm, loan_amt, deposit_amt, fx_deposit_amt,
                        securities_amt, net_interest_income, fee_income, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bas_ym,
                    bank_nm,
                    item.get('loan_amt'),
                    item.get('deposit_amt'),
                    item.get('fx_deposit_amt'),
                    item.get('securities_amt'),
                    item.get('net_interest_income'),
                    item.get('fee_income'),
                    now
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def _parse_int(self, value) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(str(value).replace(',', ''))
        except ValueError:
            return None

    def _parse_float(self, value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(str(value).replace(',', ''))
        except ValueError:
            return None

    def _parse_ratio(self, value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(str(value).replace('%', '').replace(',', ''))
        except ValueError:
            return None

    # ==================== 조회 메서드 ====================

    def get_metrics(self, bank_nm: Optional[str] = None, bas_ym: Optional[str] = None) -> List[Dict]:
        """경영지표 조회"""
        conn = self.connect()
        query = "SELECT * FROM bank_metrics WHERE 1=1"
        params = []

        if bank_nm:
            query += " AND bank_nm LIKE ?"
            params.append(f'%{bank_nm}%')
        if bas_ym:
            query += " AND bas_ym = ?"
            params.append(bas_ym)

        query += " ORDER BY bas_ym DESC, bank_nm"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_finance(self, bank_nm: Optional[str] = None, bas_ym: Optional[str] = None) -> List[Dict]:
        """재무현황 조회"""
        conn = self.connect()
        query = "SELECT * FROM bank_finance WHERE 1=1"
        params = []

        if bank_nm:
            query += " AND bank_nm LIKE ?"
            params.append(f'%{bank_nm}%')
        if bas_ym:
            query += " AND bas_ym = ?"
            params.append(bas_ym)

        query += " ORDER BY bas_ym DESC, bank_nm"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_general(self, bank_nm: Optional[str] = None, bas_ym: Optional[str] = None) -> List[Dict]:
        """일반현황 조회"""
        conn = self.connect()
        query = "SELECT * FROM bank_general WHERE 1=1"
        params = []

        if bank_nm:
            query += " AND bank_nm LIKE ?"
            params.append(f'%{bank_nm}%')
        if bas_ym:
            query += " AND bas_ym = ?"
            params.append(bas_ym)

        query += " ORDER BY bas_ym DESC, bank_nm"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_business(self, bank_nm: Optional[str] = None, bas_ym: Optional[str] = None) -> List[Dict]:
        """영업활동 조회"""
        conn = self.connect()
        query = "SELECT * FROM bank_business WHERE 1=1"
        params = []

        if bank_nm:
            query += " AND bank_nm LIKE ?"
            params.append(f'%{bank_nm}%')
        if bas_ym:
            query += " AND bas_ym = ?"
            params.append(bas_ym)

        query += " ORDER BY bas_ym DESC, bank_nm"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def compare_banks(self, metric: str, bas_ym: str) -> List[Dict]:
        """은행간 지표 비교"""
        conn = self.connect()
        metric_col = {
            'ROA': 'roa', 'ROE': 'roe', 'NIM': 'nim',
            'BIS': 'bis_ratio', 'NPL': 'npl_ratio', 'LDR': 'ldr', 'CIR': 'cir'
        }.get(metric.upper())

        if not metric_col:
            return []

        cursor = conn.execute(f"""
            SELECT bank_nm, {metric_col} as value
            FROM bank_metrics
            WHERE bas_ym = ? AND {metric_col} IS NOT NULL
            ORDER BY {metric_col} DESC
        """, (bas_ym,))
        return [dict(row) for row in cursor.fetchall()]

    def get_top_banks(self, limit: int, by: str, bas_ym: str) -> List[Dict]:
        """상위 N개 은행 조회"""
        conn = self.connect()
        col_map = {
            'assets': 'total_assets',
            'equity': 'total_equity',
            'loans': 'loans',
            'deposits': 'deposits'
        }
        column = col_map.get(by, 'total_assets')

        cursor = conn.execute(f"""
            SELECT bank_nm, {column} as value
            FROM bank_finance
            WHERE bas_ym = ? AND {column} IS NOT NULL
            ORDER BY {column} DESC
            LIMIT ?
        """, (bas_ym, limit))
        return [dict(row) for row in cursor.fetchall()]

    def update_sync_status(self, data_type: str, bas_ym: str, total_count: int):
        """동기화 상태 업데이트"""
        conn = self.connect()
        conn.execute("""
            INSERT OR REPLACE INTO data_sync_status (data_type, bas_ym, total_count, synced_at)
            VALUES (?, ?, ?, ?)
        """, (data_type, bas_ym, total_count, datetime.now().isoformat()))
        conn.commit()

    def get_stats(self) -> Dict:
        """DB 통계"""
        conn = self.connect()
        stats = {}

        for table in ['bank_general', 'bank_finance', 'bank_metrics', 'bank_business']:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]

        # 은행 수
        cursor = conn.execute("SELECT COUNT(DISTINCT bank_nm) FROM bank_metrics")
        stats['bank_count'] = cursor.fetchone()[0]

        # 기간 범위
        cursor = conn.execute("SELECT MIN(bas_ym), MAX(bas_ym) FROM bank_metrics")
        row = cursor.fetchone()
        stats['date_range'] = (row[0], row[1]) if row and row[0] else (None, None)

        # 최근 동기화
        cursor = conn.execute("""
            SELECT data_type, bas_ym, total_count, synced_at
            FROM data_sync_status
            ORDER BY synced_at DESC
            LIMIT 5
        """)
        stats['recent_syncs'] = [dict(row) for row in cursor.fetchall()]

        return stats


class FscAPI:
    """금융위원회 국내은행정보 API 클라이언트"""

    OPERATIONS = {
        'general': 'getDomeBankGeneInfo',
        'finance': 'getDomeBankFinaInfo',
        'metrics': 'getDomeBankKeyManaIndi',
        'business': 'getDomeBankMajoBusiActi',
    }

    def __init__(self, api_key: str = API_KEY):
        self.api_key = api_key
        self.base_url = BASE_URL
        self.meta_db = FscMetaDB()
        self.data_db = FscDataDB()
        self.session = requests.Session()

    def _make_request(
        self,
        operation: str,
        params: Optional[Dict] = None,
        result_type: str = 'json'
    ) -> Dict[str, Any]:
        """API 요청 실행"""
        if not self.api_key:
            raise Exception('API 키가 설정되지 않았습니다. .env 파일의 FSC_API_KEY를 확인하세요.')

        url = f"{self.base_url}/{operation}"

        request_params = {
            'serviceKey': self.api_key,
            'resultType': result_type,
            'pageNo': '1',
            'numOfRows': '100',
        }

        if params:
            request_params.update(params)

        try:
            response = self.session.get(url, params=request_params, timeout=30)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                raise Exception(f'HTTP {response.status_code}')

            if result_type == 'json':
                return response.json()
            else:
                return {'raw': response.text}

        except requests.exceptions.Timeout:
            raise Exception('요청 시간 초과')
        except requests.exceptions.RequestException as e:
            raise Exception(f'요청 오류: {e}')

    def _extract_items(self, result: Dict, table_filter: Optional[str] = None) -> List[Dict]:
        """API 응답에서 항목 추출 (tableList 구조 지원)"""
        if 'response' not in result:
            return []

        body = result['response'].get('body', {})

        # tableList 구조 처리 (FSC API 표준)
        table_list = body.get('tableList', [])
        if table_list:
            all_items = []
            for table in table_list:
                title = table.get('title', '')
                # 특정 테이블 필터링
                if table_filter and table_filter not in title:
                    continue

                items = table.get('items', {})
                if isinstance(items, dict):
                    item_list = items.get('item', [])
                    if isinstance(item_list, list):
                        # 테이블 제목 추가
                        for item in item_list:
                            item['_table'] = title
                        all_items.extend(item_list)
                    elif isinstance(item_list, dict):
                        item_list['_table'] = title
                        all_items.append(item_list)
            return all_items

        # 일반 items 구조 (fallback)
        items = body.get('items', {})
        if isinstance(items, dict):
            item_list = items.get('item', [])
            if isinstance(item_list, list):
                return item_list
            elif isinstance(item_list, dict):
                return [item_list]
        return []

    def _pivot_metrics(self, items: List[Dict]) -> List[Dict]:
        """경영지표 데이터를 은행별로 피봇"""
        from collections import defaultdict

        bank_data = defaultdict(lambda: {'bas_ym': None, 'bank_nm': None})

        for item in items:
            bank_nm = item.get('fncoNm')
            bas_ym = item.get('basYm')
            if not bank_nm:
                continue

            key = (bank_nm, bas_ym)
            bank_data[key]['bas_ym'] = bas_ym
            bank_data[key]['bank_nm'] = bank_nm

            # 수익성 지표 (ROA, ROE)
            if 'pfbtItemDcd' in item:
                code = item.get('pfbtItemDcd')
                val = item.get('pfbtItemClsfVal')
                if code == 'A6':  # ROA
                    bank_data[key]['roa'] = self._parse_ratio_val(val)
                elif code == 'A7':  # ROE
                    bank_data[key]['roe'] = self._parse_ratio_val(val)
                elif code == 'A9':  # NIM
                    bank_data[key]['nim'] = self._parse_ratio_val(val)

            # 자본적정성 지표 (BIS)
            if 'cpaqItemDcd' in item:
                code = item.get('cpaqItemDcd')
                val = item.get('cpaqItemClsfVal')
                if code == 'A':  # BIS 자기자본비율
                    bank_data[key]['bis_ratio'] = self._parse_ratio_val(val)

            # 여신건전성 지표 (NPL)
            if 'cdlSdnsItemDcd' in item:
                code = item.get('cdlSdnsItemDcd')
                val = item.get('cdlSdnsItemClsfVal')
                if code == 'A':  # 고정이하여신비율
                    bank_data[key]['npl_ratio'] = self._parse_ratio_val(val)

        return list(bank_data.values())

    def _parse_ratio_val(self, val) -> Optional[float]:
        """비율 값 파싱"""
        if val is None:
            return None
        try:
            return float(str(val).replace('%', '').replace(',', ''))
        except ValueError:
            return None

    def _pivot_general(self, items: List[Dict]) -> List[Dict]:
        """일반현황 데이터를 은행별로 피봇 (18.12월 이후)"""
        from collections import defaultdict

        bank_data = defaultdict(lambda: {'bas_ym': None, 'bank_nm': None})

        for item in items:
            bank_nm = item.get('fncoNm')
            bas_ym = item.get('basYm')
            table = item.get('_table', '')
            if not bank_nm:
                continue

            key = (bank_nm, bas_ym)
            bank_data[key]['bas_ym'] = bas_ym
            bank_data[key]['bank_nm'] = bank_nm

            # 임직원현황(18.12월이후)
            if '임직원현황' in table and '18.12' in table:
                code = item.get('xcsmDcd')
                val = item.get('xcsmCnt')
                if code == 'A':  # 임원
                    bank_data[key]['exec_cnt'] = self._parse_int_val(val)
                elif code == 'B':  # 직원
                    bank_data[key]['staff_cnt'] = self._parse_int_val(val)

            # 영업점포현황
            if '영업점포' in table:
                code = item.get('bzopStrDcd')
                val = item.get('bzopStrCnt')
                if code == 'A':  # 합계
                    bank_data[key]['branch_cnt'] = self._parse_int_val(val)

            # 자동화기기 설치현황
            if '자동화기기' in table:
                code = item.get('atmnMctlDcd')
                val = item.get('atmnMctlCnt')
                if code == 'B':  # ATM
                    bank_data[key]['atm_cnt'] = self._parse_int_val(val)

        # 임직원수 합산
        for key in bank_data:
            exec_cnt = bank_data[key].get('exec_cnt') or 0
            staff_cnt = bank_data[key].get('staff_cnt') or 0
            if exec_cnt or staff_cnt:
                bank_data[key]['employee_cnt'] = exec_cnt + staff_cnt

        return list(bank_data.values())

    def _pivot_finance(self, items: List[Dict]) -> List[Dict]:
        """재무현황 데이터를 은행별로 피봇"""
        from collections import defaultdict

        bank_data = defaultdict(lambda: {'bas_ym': None, 'bank_nm': None})

        for item in items:
            bank_nm = item.get('fncoNm')
            bas_ym = item.get('basYm')
            table = item.get('_table', '')
            if not bank_nm:
                continue

            key = (bank_nm, bas_ym)
            bank_data[key]['bas_ym'] = bas_ym
            bank_data[key]['bank_nm'] = bank_nm

            # 요약재무상태표(자산-은행)
            if '자산-은행' in table:
                code = item.get('bnkAstItemAcitCd')
                val = item.get('bnkAstItemAcitAmt')
                if code == 'A':  # 자산총계
                    bank_data[key]['total_assets'] = self._parse_float_val(val)

            # 요약재무상태표(부채및자본-은행)
            if '부채및자본-은행' in table:
                code = item.get('bnkDebtCptlItemAcitCd')
                val = item.get('bnkDebtCptlItemAcitAmt')
                if code == 'A1':  # 부채총계
                    bank_data[key]['total_liab'] = self._parse_float_val(val)
                elif code == 'A2':  # 자본총계
                    bank_data[key]['total_equity'] = self._parse_float_val(val)

        return list(bank_data.values())

    def _parse_int_val(self, val) -> Optional[int]:
        """정수 값 파싱"""
        if val is None:
            return None
        try:
            return int(str(val).replace(',', ''))
        except ValueError:
            return None

    def _parse_float_val(self, val) -> Optional[float]:
        """실수 값 파싱"""
        if val is None:
            return None
        try:
            return float(str(val).replace(',', ''))
        except ValueError:
            return None

    def _pivot_business(self, items: List[Dict]) -> List[Dict]:
        """영업활동 데이터를 은행별로 피봇"""
        from collections import defaultdict

        bank_data = defaultdict(lambda: {'bas_ym': None, 'bank_nm': None})

        for item in items:
            bank_nm = item.get('fncoNm')
            bas_ym = item.get('basYm')
            table = item.get('_table', '')
            if not bank_nm:
                continue

            key = (bank_nm, bas_ym)
            bank_data[key]['bas_ym'] = bas_ym
            bank_data[key]['bank_nm'] = bank_nm

            # 영업규모
            if '영업규모' in table:
                code = item.get('bzopSclItemDcd')
                val = item.get('bzopSclItemAmt')
                if code == 'A':  # 대출금
                    bank_data[key]['loan_amt'] = self._parse_float_val(val)
                elif code == 'B':  # 유가증권
                    bank_data[key]['securities_amt'] = self._parse_float_val(val)
                elif code == 'D':  # 총수신(예수금)
                    bank_data[key]['deposit_amt'] = self._parse_float_val(val)

            # 형태별예수금
            if '형태별예수금' in table:
                code = item.get('rcavAmFrmtItemCd')
                val = item.get('rcavAmFrmtItemAmt')
                if code == 'B':  # 외화예수금
                    bank_data[key]['fx_deposit_amt'] = self._parse_float_val(val)

        return list(bank_data.values())

    # ==================== 조회 메서드 ====================

    def get_general(self, bank_nm: Optional[str] = None, bas_ym: Optional[str] = None) -> List[Dict]:
        """일반현황 API 조회 (피봇된 데이터 반환, 18.12월 이후)"""
        params = {'numOfRows': '5000'}  # 일반현황 데이터
        if bank_nm:
            params['fncoNm'] = bank_nm
        if bas_ym:
            params['basYm'] = bas_ym

        result = self._make_request(self.OPERATIONS['general'], params)
        items = self._extract_items(result)
        return self._pivot_general(items)

    def get_finance(self, bank_nm: Optional[str] = None, bas_ym: Optional[str] = None) -> List[Dict]:
        """재무현황 API 조회 (피봇된 데이터 반환)"""
        params = {'numOfRows': '10000'}  # 재무현황은 데이터가 많음
        if bank_nm:
            params['fncoNm'] = bank_nm
        if bas_ym:
            params['basYm'] = bas_ym

        result = self._make_request(self.OPERATIONS['finance'], params)
        items = self._extract_items(result)
        return self._pivot_finance(items)

    def get_metrics(self, bank_nm: Optional[str] = None, bas_ym: Optional[str] = None) -> List[Dict]:
        """경영지표 API 조회 (피봇된 데이터 반환)"""
        params = {'numOfRows': '1000'}  # 충분한 데이터 조회
        if bank_nm:
            params['fncoNm'] = bank_nm
        if bas_ym:
            params['basYm'] = bas_ym

        result = self._make_request(self.OPERATIONS['metrics'], params)
        items = self._extract_items(result)
        return self._pivot_metrics(items)

    def get_business(self, bank_nm: Optional[str] = None, bas_ym: Optional[str] = None) -> List[Dict]:
        """영업활동 API 조회 (피봇된 데이터 반환)"""
        params = {'numOfRows': '5000'}
        if bank_nm:
            params['fncoNm'] = bank_nm
        if bas_ym:
            params['basYm'] = bas_ym

        result = self._make_request(self.OPERATIONS['business'], params)
        items = self._extract_items(result)
        return self._pivot_business(items)

    # ==================== 동기화 메서드 ====================

    def sync_data(self, data_type: str, bas_ym: str, bank_nm: Optional[str] = None) -> int:
        """데이터 동기화"""
        fetch_methods = {
            'general': (self.get_general, self.data_db.insert_general),
            'finance': (self.get_finance, self.data_db.insert_finance),
            'metrics': (self.get_metrics, self.data_db.insert_metrics),
            'business': (self.get_business, self.data_db.insert_business),
        }

        if data_type not in fetch_methods:
            raise ValueError(f'유효하지 않은 데이터 유형: {data_type}')

        fetch_func, insert_func = fetch_methods[data_type]
        type_name = self.meta_db.get_data_type(data_type)['name']

        print(f'동기화 시작: {type_name} - {bas_ym[:4]}년 {bas_ym[4:]}월')

        try:
            items = fetch_func(bank_nm=bank_nm, bas_ym=bas_ym)

            if not items:
                print('  조회된 데이터가 없습니다.')
                return 0

            inserted = insert_func(items)
            self.data_db.update_sync_status(data_type, bas_ym, len(items))
            self.meta_db.log_sync(data_type, bas_ym, inserted)

            print(f'  완료: {len(items)}건 조회, {inserted}건 저장')
            return inserted

        except Exception as e:
            print(f'  오류: {e}')
            return 0

    def sync_range(self, data_type: str, start_ym: str, end_ym: str, bank_nm: Optional[str] = None) -> int:
        """기간 범위 동기화"""
        total = 0
        for ym in self._generate_ym_range(start_ym, end_ym):
            total += self.sync_data(data_type, ym, bank_nm)
        return total

    def _generate_ym_range(self, start: str, end: str) -> List[str]:
        """YYYYMM 범위 생성"""
        result = []
        y, m = int(start[:4]), int(start[4:])
        end_y, end_m = int(end[:4]), int(end[4:])

        while (y < end_y) or (y == end_y and m <= end_m):
            result.append(f'{y}{m:02d}')
            m += 1
            if m > 12:
                m = 1
                y += 1

        return result

    def close(self):
        """리소스 정리"""
        self.meta_db.close()
        self.data_db.close()

    # ==================== DB-First 패턴 (v1.1) ====================

    def get_metrics_with_db_first(
        self,
        bas_ym: str,
        bank_nm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB-First 패턴으로 경영지표 조회

        1. DB에서 해당 기간 데이터 확인
        2. DB에 데이터가 있으면 반환
        3. 없으면 API 호출 → DB 저장 → 반환

        Args:
            bas_ym: 기준년월 (YYYYMM)
            bank_nm: 은행명 (선택)

        Returns:
            {
                'data': 데이터 리스트,
                'source': 'db' 또는 'api',
                'db_count': DB에서 조회한 건수,
                'api_count': API에서 조회한 건수,
                'saved': DB에 저장한 건수
            }
        """
        result = {
            'data': [],
            'source': None,
            'db_count': 0,
            'api_count': 0,
            'saved': 0
        }

        # 1. DB에서 기존 데이터 조회
        db_data = self.data_db.get_metrics(bank_nm=bank_nm, bas_ym=bas_ym)

        if db_data:
            result['data'] = db_data
            result['source'] = 'db'
            result['db_count'] = len(db_data)
            print(f"[DB-First] DB에서 조회: {len(db_data)}건 ({bas_ym})")
            return result

        # 2. DB에 데이터가 없으면 API 호출
        print(f"[DB-First] API 호출: metrics ({bas_ym})")
        api_data = self.get_metrics(bank_nm=bank_nm, bas_ym=bas_ym)
        result['api_count'] = len(api_data)

        # 3. API 데이터 DB에 저장
        if api_data:
            saved = self.data_db.insert_metrics(api_data)
            result['saved'] = saved
            self.data_db.update_sync_status('metrics', bas_ym, len(api_data))
            print(f"[DB-First] API에서 조회 → DB 저장: {saved}건")

        result['data'] = api_data
        result['source'] = 'api'
        return result

    def get_finance_with_db_first(
        self,
        bas_ym: str,
        bank_nm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB-First 패턴으로 재무현황 조회
        """
        result = {
            'data': [],
            'source': None,
            'db_count': 0,
            'api_count': 0,
            'saved': 0
        }

        # 1. DB에서 기존 데이터 조회
        db_data = self.data_db.get_finance(bank_nm=bank_nm, bas_ym=bas_ym)

        if db_data:
            result['data'] = db_data
            result['source'] = 'db'
            result['db_count'] = len(db_data)
            print(f"[DB-First] DB에서 조회: {len(db_data)}건 ({bas_ym})")
            return result

        # 2. DB에 데이터가 없으면 API 호출
        print(f"[DB-First] API 호출: finance ({bas_ym})")
        api_data = self.get_finance(bank_nm=bank_nm, bas_ym=bas_ym)
        result['api_count'] = len(api_data)

        # 3. API 데이터 DB에 저장
        if api_data:
            saved = self.data_db.insert_finance(api_data)
            result['saved'] = saved
            self.data_db.update_sync_status('finance', bas_ym, len(api_data))
            print(f"[DB-First] API에서 조회 → DB 저장: {saved}건")

        result['data'] = api_data
        result['source'] = 'api'
        return result

    def get_general_with_db_first(
        self,
        bas_ym: str,
        bank_nm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB-First 패턴으로 일반현황 조회
        """
        result = {
            'data': [],
            'source': None,
            'db_count': 0,
            'api_count': 0,
            'saved': 0
        }

        # 1. DB에서 기존 데이터 조회
        db_data = self.data_db.get_general(bank_nm=bank_nm, bas_ym=bas_ym)

        if db_data:
            result['data'] = db_data
            result['source'] = 'db'
            result['db_count'] = len(db_data)
            print(f"[DB-First] DB에서 조회: {len(db_data)}건 ({bas_ym})")
            return result

        # 2. DB에 데이터가 없으면 API 호출
        print(f"[DB-First] API 호출: general ({bas_ym})")
        api_data = self.get_general(bank_nm=bank_nm, bas_ym=bas_ym)
        result['api_count'] = len(api_data)

        # 3. API 데이터 DB에 저장
        if api_data:
            saved = self.data_db.insert_general(api_data)
            result['saved'] = saved
            self.data_db.update_sync_status('general', bas_ym, len(api_data))
            print(f"[DB-First] API에서 조회 → DB 저장: {saved}건")

        result['data'] = api_data
        result['source'] = 'api'
        return result

    def get_business_with_db_first(
        self,
        bas_ym: str,
        bank_nm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB-First 패턴으로 영업활동 조회
        """
        result = {
            'data': [],
            'source': None,
            'db_count': 0,
            'api_count': 0,
            'saved': 0
        }

        # 1. DB에서 기존 데이터 조회
        db_data = self.data_db.get_business(bank_nm=bank_nm, bas_ym=bas_ym)

        if db_data:
            result['data'] = db_data
            result['source'] = 'db'
            result['db_count'] = len(db_data)
            print(f"[DB-First] DB에서 조회: {len(db_data)}건 ({bas_ym})")
            return result

        # 2. DB에 데이터가 없으면 API 호출
        print(f"[DB-First] API 호출: business ({bas_ym})")
        api_data = self.get_business(bank_nm=bank_nm, bas_ym=bas_ym)
        result['api_count'] = len(api_data)

        # 3. API 데이터 DB에 저장
        if api_data:
            saved = self.data_db.insert_business(api_data)
            result['saved'] = saved
            self.data_db.update_sync_status('business', bas_ym, len(api_data))
            print(f"[DB-First] API에서 조회 → DB 저장: {saved}건")

        result['data'] = api_data
        result['source'] = 'api'
        return result


# ==================== 출력 유틸리티 ====================

def save_output(data: List[Dict], output_path: str):
    """결과를 파일로 저장"""
    path = Path(output_path)

    if path.suffix.lower() == '.json':
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif path.suffix.lower() == '.csv':
        if data:
            with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
    else:
        raise ValueError(f'지원하지 않는 형식: {path.suffix}')

    print(f'\n저장 완료: {path}')


def main():
    parser = argparse.ArgumentParser(description='금융위원회 국내은행정보 API 클라이언트')

    # 동기화 옵션
    parser.add_argument('--sync', action='store_true', help='데이터 동기화')
    parser.add_argument('--type', choices=['general', 'finance', 'metrics', 'business'],
                        help='데이터 유형')

    # 조회 옵션
    parser.add_argument('--general', action='store_true', help='일반현황 조회')
    parser.add_argument('--finance', action='store_true', help='재무현황 조회')
    parser.add_argument('--metrics', action='store_true', help='경영지표 조회')
    parser.add_argument('--business', action='store_true', help='영업활동 조회')

    # 필터 옵션
    parser.add_argument('--bank', '-b', help='은행명')
    parser.add_argument('--ym', help='기준년월 (YYYYMM 또는 YYYYMM-YYYYMM)')

    # 비교/분석 옵션
    parser.add_argument('--compare', action='store_true', help='은행간 비교')
    parser.add_argument('--metric', choices=['ROA', 'ROE', 'NIM', 'BIS', 'NPL', 'LDR', 'CIR'],
                        help='비교 지표')

    # DB 옵션
    parser.add_argument('--banks', action='store_true', help='은행 목록 (메타DB)')
    parser.add_argument('--search', '-s', help='은행 검색')
    parser.add_argument('--top', type=int, help='상위 N개')
    parser.add_argument('--by', choices=['assets', 'equity', 'loans', 'deposits'],
                        default='assets', help='정렬 기준')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--force-api', action='store_true',
                        help='DB 무시하고 API 직접 호출')
    parser.add_argument('--db-only', action='store_true',
                        help='DB에서만 조회 (API 호출 안함, 기존 --sync 없이 조회)')
    parser.add_argument('--db-first', action='store_true',
                        help='DB-First 패턴으로 조회 (기본값, DB→API 순서)')

    # 출력 옵션
    parser.add_argument('--output', '-o', help='결과 저장 (json/csv)')

    args = parser.parse_args()

    api = FscAPI()

    try:
        # 은행 목록 (메타DB)
        if args.banks:
            banks = api.meta_db.get_all_banks()
            print(f'\n=== 등록 은행 목록 ({len(banks)}개) ===')
            print(f'{"코드":<8} {"은행명":<20} {"유형":<12} {"금융지주":<15}')
            print('-' * 60)
            for b in banks:
                print(f'{b["bank_cd"]:<8} {b["bank_nm"]:<20} {b["bank_type"]:<12} {b["group_nm"] or "-":<15}')
            return

        # 은행 검색
        if args.search:
            results = api.meta_db.search_banks(args.search)
            print(f'\n=== "{args.search}" 검색 결과 ({len(results)}건) ===')
            for b in results:
                print(f'  {b["bank_nm"]} ({b["bank_type"]})')
            return

        # DB 통계
        if args.stats:
            stats = api.data_db.get_stats()
            print('\n=== FSC 데이터DB 통계 ===')
            print(f'일반현황: {stats["bank_general"]:,}건')
            print(f'재무현황: {stats["bank_finance"]:,}건')
            print(f'경영지표: {stats["bank_metrics"]:,}건')
            print(f'영업활동: {stats["bank_business"]:,}건')
            print(f'\n등록 은행: {stats["bank_count"]}개')
            if stats['date_range'][0]:
                print(f'데이터 기간: {stats["date_range"][0]} ~ {stats["date_range"][1]}')

            if stats['recent_syncs']:
                print('\n최근 동기화:')
                for s in stats['recent_syncs']:
                    print(f'  {s["data_type"]} {s["bas_ym"]}: {s["total_count"]}건 ({s["synced_at"][:16]})')
            return

        # 데이터 동기화
        if args.sync:
            if not args.type or not args.ym:
                print('오류: --sync에는 --type과 --ym이 필요합니다.')
                print('예: python fsc_api.py --sync --type metrics --ym 202412')
                return

            if '-' in args.ym:
                start_ym, end_ym = args.ym.split('-')
                api.sync_range(args.type, start_ym, end_ym, args.bank)
            else:
                api.sync_data(args.type, args.ym, args.bank)

            print(f'\n저장 위치: {api.data_db.db_path}')
            return

        # 경영지표 조회
        if args.metrics:
            if args.db_only:
                # DB에서만 조회
                results = api.data_db.get_metrics(args.bank, args.ym)
                source_str = "DB"
            elif args.force_api:
                # API 직접 호출 후 저장
                results = api.sync_data('metrics', args.ym, args.bank)
                source_str = "API"
                results = api.data_db.get_metrics(args.bank, args.ym)
            else:
                # DB-First 패턴 (기본값)
                db_first_result = api.get_metrics_with_db_first(args.ym, args.bank)
                results = db_first_result['data']
                source_str = "DB" if db_first_result['source'] == 'db' else "API"

            if not results:
                print('조회된 데이터가 없습니다.')
                return

            print(f'\n=== 경영지표 ({len(results)}건, {source_str}) ===')
            print(f'{"은행명":<20} {"기준월":<8} {"ROA":<8} {"ROE":<8} {"NIM":<8} {"BIS":<8}')
            print('-' * 65)
            for r in results[:20]:
                roa = f'{r["roa"]:.2f}%' if r["roa"] else '-'
                roe = f'{r["roe"]:.2f}%' if r["roe"] else '-'
                nim = f'{r["nim"]:.2f}%' if r["nim"] else '-'
                bis = f'{r["bis_ratio"]:.2f}%' if r["bis_ratio"] else '-'
                print(f'{r["bank_nm"]:<20} {r["bas_ym"]:<8} {roa:<8} {roe:<8} {nim:<8} {bis:<8}')

            if args.output:
                save_output(results, args.output)
            return

        # 재무현황 조회
        if args.finance:
            if args.db_only:
                results = api.data_db.get_finance(args.bank, args.ym)
                source_str = "DB"
            elif args.force_api:
                api.sync_data('finance', args.ym, args.bank)
                results = api.data_db.get_finance(args.bank, args.ym)
                source_str = "API"
            else:
                db_first_result = api.get_finance_with_db_first(args.ym, args.bank)
                results = db_first_result['data']
                source_str = "DB" if db_first_result['source'] == 'db' else "API"

            if not results:
                print('조회된 데이터가 없습니다.')
                return

            print(f'\n=== 재무현황 ({len(results)}건, {source_str}) ===')
            print(f'{"은행명":<20} {"기준월":<8} {"총자산(억)":<15} {"총부채(억)":<15} {"자기자본(억)":<15}')
            print('-' * 80)
            for r in results[:20]:
                assets = f'{r["total_assets"]/100000000:,.0f}' if r["total_assets"] else '-'
                liab = f'{r["total_liab"]/100000000:,.0f}' if r["total_liab"] else '-'
                equity = f'{r["total_equity"]/100000000:,.0f}' if r["total_equity"] else '-'
                print(f'{r["bank_nm"]:<20} {r["bas_ym"]:<8} {assets:<15} {liab:<15} {equity:<15}')

            if args.output:
                save_output(results, args.output)
            return

        # 일반현황 조회
        if args.general:
            if args.db_only:
                results = api.data_db.get_general(args.bank, args.ym)
                source_str = "DB"
            elif args.force_api:
                api.sync_data('general', args.ym, args.bank)
                results = api.data_db.get_general(args.bank, args.ym)
                source_str = "API"
            else:
                db_first_result = api.get_general_with_db_first(args.ym, args.bank)
                results = db_first_result['data']
                source_str = "DB" if db_first_result['source'] == 'db' else "API"

            if not results:
                print('조회된 데이터가 없습니다.')
                return

            print(f'\n=== 일반현황 ({len(results)}건, {source_str}) ===')
            print(f'{"은행명":<20} {"기준월":<8} {"설립년도":<10} {"점포수":<10} {"임직원수":<10}')
            print('-' * 65)
            for r in results[:20]:
                print(f'{r["bank_nm"]:<20} {r["bas_ym"]:<8} {r["estb_year"] or "-":<10} '
                      f'{r["branch_cnt"] or "-":<10} {r["employee_cnt"] or "-":<10}')

            if args.output:
                save_output(results, args.output)
            return

        # 영업활동 조회
        if args.business:
            if args.db_only:
                results = api.data_db.get_business(args.bank, args.ym)
                source_str = "DB"
            elif args.force_api:
                api.sync_data('business', args.ym, args.bank)
                results = api.data_db.get_business(args.bank, args.ym)
                source_str = "API"
            else:
                db_first_result = api.get_business_with_db_first(args.ym, args.bank)
                results = db_first_result['data']
                source_str = "DB" if db_first_result['source'] == 'db' else "API"

            if not results:
                print('조회된 데이터가 없습니다.')
                return

            print(f'\n=== 영업활동 ({len(results)}건, {source_str}) ===')
            print(f'{"은행명":<20} {"기준월":<8} {"대출(억)":<15} {"예금(억)":<15}')
            print('-' * 65)
            for r in results[:20]:
                loan = f'{r["loan_amt"]/100000000:,.0f}' if r["loan_amt"] else '-'
                deposit = f'{r["deposit_amt"]/100000000:,.0f}' if r["deposit_amt"] else '-'
                print(f'{r["bank_nm"]:<20} {r["bas_ym"]:<8} {loan:<15} {deposit:<15}')

            if args.output:
                save_output(results, args.output)
            return

        # 은행간 비교
        if args.compare:
            if not args.metric or not args.ym:
                print('오류: --compare에는 --metric과 --ym이 필요합니다.')
                print('예: python fsc_api.py --compare --metric ROE --ym 202412')
                return

            results = api.data_db.compare_banks(args.metric, args.ym)
            if not results:
                print('조회된 데이터가 없습니다. --sync로 동기화하세요.')
                return

            metric_info = api.meta_db.get_metric(args.metric)
            metric_name = metric_info['name'] if metric_info else args.metric

            print(f'\n=== 은행별 {metric_name} 비교 ({args.ym[:4]}년 {args.ym[4:]}월) ===')
            print(f'{"순위":<6} {"은행명":<25} {args.metric:<10}')
            print('-' * 45)
            for i, r in enumerate(results, 1):
                val = f'{r["value"]:.2f}%' if r["value"] else '-'
                print(f'{i:<6} {r["bank_nm"]:<25} {val:<10}')

            if args.output:
                save_output(results, args.output)
            return

        # TOP N 조회
        if args.top:
            if not args.ym:
                print('오류: --top에는 --ym이 필요합니다.')
                return

            results = api.data_db.get_top_banks(args.top, args.by, args.ym)
            if not results:
                print('조회된 데이터가 없습니다. --sync로 동기화하세요.')
                return

            by_name = {'assets': '총자산', 'equity': '자기자본', 'loans': '대출', 'deposits': '예금'}.get(args.by, args.by)

            print(f'\n=== {by_name} 상위 {args.top}개 은행 ({args.ym[:4]}년 {args.ym[4:]}월) ===')
            print(f'{"순위":<6} {"은행명":<25} {by_name + "(억)":<15}')
            print('-' * 50)
            for i, r in enumerate(results, 1):
                val = f'{r["value"]/100000000:,.0f}' if r["value"] else '-'
                print(f'{i:<6} {r["bank_nm"]:<25} {val:<15}')

            if args.output:
                save_output(results, args.output)
            return

        # 도움말
        parser.print_help()

    finally:
        api.close()


if __name__ == '__main__':
    main()
