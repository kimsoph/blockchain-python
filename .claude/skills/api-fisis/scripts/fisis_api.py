# -*- coding: utf-8 -*-
"""
FISIS OpenAPI Client
금융감독원 금융통계정보시스템 API 클라이언트

Author: Claude Code
Version: 2.0.0

Changes in 2.0.0:
- term 파라미터 규격 수정 (term=Q|Y, startBaseMm/endBaseMm 사용)
- 기간 변환 헬퍼 함수 추가 (분기→YYYYMM, 연도→YYYYMM)
- CLI 인터페이스 개선
- 에러 핸들링 강화

API 파라미터 규격:
- term: 기간 유형 (Q=분기, Y=연간)
- startBaseMm: 시작 기준월 (YYYYMM)
- endBaseMm: 종료 기준월 (YYYYMM)
"""

import os
import sys
import json
import csv
import sqlite3
import argparse
from datetime import datetime
from typing import Optional, Dict, List, Any, Union, Tuple
from pathlib import Path

# 한글 출력을 위한 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    print("requests 패키지가 필요합니다: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# 메타데이터 DB 임포트
try:
    from fisis_meta_db import FisisMetaDB
    HAS_META_DB = True
except ImportError:
    HAS_META_DB = False


class FisisDataDB:
    """FISIS 데이터 DB 관리 클래스"""

    SCHEMA = """
    -- 통계 데이터 테이블
    CREATE TABLE IF NOT EXISTS fisis_data (
        id INTEGER PRIMARY KEY,
        stat_code TEXT NOT NULL,
        company_code TEXT,
        company_name TEXT,
        base_period TEXT NOT NULL,
        term_type TEXT,
        item_code TEXT,
        item_name TEXT,
        data_value REAL,
        unit_name TEXT,
        created_at TEXT,
        UNIQUE(stat_code, company_code, base_period, item_code)
    );

    -- 동기화 상태
    CREATE TABLE IF NOT EXISTS data_sync_status (
        id INTEGER PRIMARY KEY,
        stat_code TEXT NOT NULL,
        base_period TEXT NOT NULL,
        total_count INTEGER,
        synced_at TEXT,
        UNIQUE(stat_code, base_period)
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_data_stat ON fisis_data(stat_code);
    CREATE INDEX IF NOT EXISTS idx_data_period ON fisis_data(base_period);
    CREATE INDEX IF NOT EXISTS idx_data_company ON fisis_data(company_code);
    CREATE INDEX IF NOT EXISTS idx_data_stat_period ON fisis_data(stat_code, base_period);
    """

    def __init__(self, db_path: Optional[Path] = None):
        # 프로젝트 루트 경로 설정
        skill_root = Path(__file__).parent.parent
        project_root = skill_root.parent.parent.parent
        self.db_path = db_path or project_root / '3_Resources' / 'R-DB' / 'fisis.db'
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

    def save_data(self, items: List[Dict], stat_code: str) -> int:
        """통계 데이터 저장"""
        conn = self.connect()
        now = datetime.now().isoformat()
        inserted = 0

        for item in items:
            try:
                # FISIS API 응답 필드 매핑
                company_code = item.get('finance_cd', '')
                company_name = item.get('finance_nm', '')
                base_period = item.get('base_mm', '') or item.get('base_yy', '')
                item_code = item.get('account_cd', '') or item.get('itm_cd', '')
                item_name = item.get('account_nm', '') or item.get('itm_nm', '')

                # 데이터 값 파싱
                data_val = item.get('a', item.get('data_val', ''))
                try:
                    data_value = float(str(data_val).replace(',', '')) if data_val else None
                except (ValueError, TypeError):
                    data_value = None

                unit_name = item.get('unit_nm', '')

                conn.execute("""
                    INSERT OR REPLACE INTO fisis_data (
                        stat_code, company_code, company_name, base_period,
                        term_type, item_code, item_name, data_value, unit_name, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stat_code,
                    company_code,
                    company_name,
                    base_period,
                    item.get('term', ''),
                    item_code,
                    item_name,
                    data_value,
                    unit_name,
                    now
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def query_data(
        self,
        stat_code: Optional[str] = None,
        company_code: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """데이터 조회"""
        conn = self.connect()
        cursor = conn.cursor()

        query = 'SELECT * FROM fisis_data WHERE 1=1'
        params = []

        if stat_code:
            query += ' AND stat_code = ?'
            params.append(stat_code)
        if company_code:
            query += ' AND company_code = ?'
            params.append(company_code)
        if start_period:
            query += ' AND base_period >= ?'
            params.append(start_period)
        if end_period:
            query += ' AND base_period <= ?'
            params.append(end_period)

        query += f' ORDER BY base_period DESC, company_name LIMIT {limit}'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_sync_status(self, stat_code: str, base_period: str, total_count: int):
        """동기화 상태 업데이트"""
        conn = self.connect()
        conn.execute("""
            INSERT OR REPLACE INTO data_sync_status (stat_code, base_period, total_count, synced_at)
            VALUES (?, ?, ?, ?)
        """, (stat_code, base_period, total_count, datetime.now().isoformat()))
        conn.commit()

    def get_stats(self) -> Dict:
        """DB 통계"""
        conn = self.connect()
        stats = {}

        # 총 레코드 수
        cursor = conn.execute("SELECT COUNT(*) FROM fisis_data")
        stats['total_records'] = cursor.fetchone()[0]

        # 통계표 수
        cursor = conn.execute("SELECT COUNT(DISTINCT stat_code) FROM fisis_data")
        stats['stat_count'] = cursor.fetchone()[0]

        # 금융회사 수
        cursor = conn.execute("SELECT COUNT(DISTINCT company_code) FROM fisis_data WHERE company_code != ''")
        stats['company_count'] = cursor.fetchone()[0]

        # 기간 범위
        cursor = conn.execute("SELECT MIN(base_period), MAX(base_period) FROM fisis_data")
        row = cursor.fetchone()
        stats['date_range'] = (row[0], row[1]) if row and row[0] else (None, None)

        # 통계표별 레코드 수
        cursor = conn.execute("""
            SELECT stat_code, COUNT(*) as cnt
            FROM fisis_data
            GROUP BY stat_code
            ORDER BY cnt DESC
            LIMIT 10
        """)
        stats['stats_by_code'] = [dict(row) for row in cursor.fetchall()]

        # 최근 동기화
        cursor = conn.execute("""
            SELECT stat_code, base_period, total_count, synced_at
            FROM data_sync_status
            ORDER BY synced_at DESC
            LIMIT 5
        """)
        stats['recent_syncs'] = [dict(row) for row in cursor.fetchall()]

        return stats


class FisisAPI:
    """FISIS OpenAPI 클라이언트 클래스"""

    # API Base URL
    BASE_URL = "http://fisis.fss.or.kr/openapi"

    # 금융권역 코드 (partDiv 파라미터)
    SECTORS = {
        'bank': {'code': 'A', 'name': '국내은행', 'desc': '시중은행, 지방은행, 특수은행'},
        'bank_foreign': {'code': 'J', 'name': '외은지점', 'desc': '외국은행 국내지점'},
        'insurance_life': {'code': 'H', 'name': '생명보험', 'desc': '생명보험사'},
        'insurance_nonlife': {'code': 'I', 'name': '손해보험', 'desc': '손해보험사'},
        'securities': {'code': 'F', 'name': '증권사', 'desc': '증권회사'},
        'asset_mgmt': {'code': 'G', 'name': '자산운용', 'desc': '자산운용사'},
        'savings': {'code': 'E', 'name': '저축은행', 'desc': '저축은행'},
        'card': {'code': 'C', 'name': '신용카드', 'desc': '신용카드사'},
        'lease': {'code': 'K', 'name': '리스', 'desc': '리스사'},
        'installment': {'code': 'T', 'name': '할부금융', 'desc': '할부금융사'},
        'holding': {'code': 'L', 'name': '금융지주', 'desc': '금융지주회사'},
        'credit_union': {'code': 'O', 'name': '신협', 'desc': '신용협동조합'},
        'nacf': {'code': 'Q', 'name': '농협', 'desc': '농업협동조합'},
        'nffc': {'code': 'P', 'name': '수협', 'desc': '수협단위조합'},
        'futures': {'code': 'W', 'name': '선물사', 'desc': '선물회사'},
        'advisory': {'code': 'X', 'name': '투자자문', 'desc': '투자자문사'},
    }

    # 기간 유형
    TERM_TYPES = {
        'Q': '분기 (Quarterly)',
        'Y': '연간 (Yearly)',
    }

    # 주요 통계표 코드 (은행)
    STAT_CODES_BANK = {
        'SA003': '요약재무상태표(자산)',
        'SA004': '요약재무상태표(부채/자본)',
        'SA017': '수익성지표',
        'SA021': '주요계정 및 지표',
        'SA101': '임직원현황',
        'SA002': '영업점포현황',
    }

    def __init__(self, api_key: Optional[str] = None, use_meta_db: bool = True):
        """
        FisisAPI 초기화

        Args:
            api_key: API 인증키 (없으면 환경변수에서 로드)
            use_meta_db: 메타데이터 DB 사용 여부
        """
        self.api_key = api_key or self._load_api_key()
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Accept-Charset': 'utf-8',
        })

        # 메타데이터 DB 초기화
        self.meta_db = None
        if use_meta_db and HAS_META_DB:
            try:
                self.meta_db = FisisMetaDB()
                self.meta_db.connect()
            except Exception:
                self.meta_db = None

        # 데이터 DB 초기화
        self.data_db = FisisDataDB()

    def _load_api_key(self) -> str:
        """환경변수에서 API 키 로드"""
        env_paths = [
            Path('.claude/.env'),
            Path('.env'),
            Path.home() / '.fisis_api_key',
        ]

        if load_dotenv:
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path)
                    break

        api_key = os.getenv('FISIS_API_KEY')
        if not api_key:
            print("경고: FISIS_API_KEY가 설정되지 않았습니다.")
            print("  .claude/.env 파일에 FISIS_API_KEY=your_key 형식으로 설정하세요.")
        return api_key or ''

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        format_type: str = 'json'
    ) -> Dict[str, Any]:
        """
        API 요청 실행

        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터
            format_type: 응답 형식 (json/xml)

        Returns:
            API 응답 데이터
        """
        if not self.api_key:
            return {'error': 'API 키가 설정되지 않았습니다.'}

        url = f"{self.BASE_URL}/{endpoint}.{format_type}"

        # 기본 파라미터
        request_params = {
            'auth': self.api_key,
            'lang': 'kr',
        }

        if params:
            request_params.update(params)

        try:
            response = self.session.get(url, params=request_params, timeout=30)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                if format_type == 'json':
                    return response.json()
                else:
                    return {'xml': response.text}
            else:
                return {
                    'error': f'HTTP {response.status_code}',
                    'message': response.text
                }

        except requests.exceptions.Timeout:
            return {'error': '요청 시간 초과'}
        except requests.exceptions.RequestException as e:
            return {'error': f'요청 실패: {str(e)}'}
        except json.JSONDecodeError as e:
            return {'error': f'JSON 파싱 실패: {str(e)}'}

    # ==================== 기간 변환 헬퍼 ====================

    @staticmethod
    def quarter_to_dates(year: int, quarter: int) -> Tuple[str, str]:
        """
        연도와 분기를 startBaseMm/endBaseMm 형식으로 변환

        Args:
            year: 연도 (예: 2024)
            quarter: 분기 (1-4)

        Returns:
            (startBaseMm, endBaseMm) 튜플

        Example:
            quarter_to_dates(2024, 1) -> ('202401', '202403')
            quarter_to_dates(2024, 4) -> ('202410', '202412')
        """
        quarter_months = {
            1: ('01', '03'),
            2: ('04', '06'),
            3: ('07', '09'),
            4: ('10', '12'),
        }
        if quarter not in quarter_months:
            raise ValueError(f"분기는 1-4 사이여야 합니다: {quarter}")

        start_month, end_month = quarter_months[quarter]
        return f"{year}{start_month}", f"{year}{end_month}"

    @staticmethod
    def year_to_dates(year: int) -> Tuple[str, str]:
        """
        연도를 startBaseMm/endBaseMm 형식으로 변환

        Args:
            year: 연도 (예: 2024)

        Returns:
            (startBaseMm, endBaseMm) 튜플

        Example:
            year_to_dates(2024) -> ('202401', '202412')
        """
        return f"{year}01", f"{year}12"

    @staticmethod
    def month_to_dates(year: int, month: int) -> Tuple[str, str]:
        """
        연도와 월을 startBaseMm/endBaseMm 형식으로 변환

        Args:
            year: 연도
            month: 월 (1-12)

        Returns:
            (startBaseMm, endBaseMm) 튜플
        """
        date_str = f"{year}{month:02d}"
        return date_str, date_str

    # ==================== API 메서드 ====================

    def get_sectors(self) -> List[Dict[str, str]]:
        """금융권역 목록 반환"""
        return [
            {'code': k, **v} for k, v in self.SECTORS.items()
        ]

    def check_api_status(self) -> Dict[str, Any]:
        """
        FISIS API 엔드포인트 상태 확인

        Returns:
            각 API 엔드포인트의 상태 정보
        """
        status = {
            'timestamp': datetime.now().isoformat(),
            'endpoints': {}
        }

        # 1. 금융회사 목록 API
        try:
            result = self.get_companies('bank')
            if 'error' not in result:
                count = result.get('total_count', 0)
                status['endpoints']['companySearch'] = {'status': 'OK', 'count': count}
            else:
                status['endpoints']['companySearch'] = {'status': 'ERROR', 'message': result['error']}
        except Exception as e:
            status['endpoints']['companySearch'] = {'status': 'ERROR', 'message': str(e)}

        # 2. 통계표 목록 API
        try:
            result = self.get_statistics_list('bank')
            if 'result' in result and result['result'].get('err_cd') == '000':
                count = result['result'].get('total_count', 0)
                status['endpoints']['statisticsListSearch'] = {'status': 'OK', 'count': count}
            else:
                err_msg = result.get('result', {}).get('err_msg', 'Unknown')
                status['endpoints']['statisticsListSearch'] = {'status': 'ERROR', 'message': err_msg}
        except Exception as e:
            status['endpoints']['statisticsListSearch'] = {'status': 'ERROR', 'message': str(e)}

        # 3. 통계 데이터 API (올바른 파라미터로 테스트)
        try:
            result = self.get_statistics_data(
                stat_code='SA003',
                year=2024,
                quarter=1
            )
            if 'result' in result:
                err_cd = result['result'].get('err_cd', '')
                if err_cd == '000':
                    count = result['result'].get('total_count', 0)
                    status['endpoints']['statisticsInfoSearch'] = {'status': 'OK', 'count': count}
                else:
                    status['endpoints']['statisticsInfoSearch'] = {
                        'status': 'ERROR',
                        'message': result['result'].get('err_msg', '')
                    }
        except Exception as e:
            status['endpoints']['statisticsInfoSearch'] = {'status': 'ERROR', 'message': str(e)}

        return status

    def lookup_company_code(self, name: str) -> Optional[str]:
        """
        회사명으로 금융회사 코드 조회 (메타DB 우선 사용)

        Args:
            name: 금융회사명 (예: "신한은행", "IBK기업은행")

        Returns:
            금융회사 코드 또는 None
        """
        # 1. 메타데이터 DB에서 먼저 조회
        if self.meta_db:
            code = self.meta_db.get_company_code(name)
            if code:
                return code

        # 2. DB에 없으면 API로 조회
        for sector_code in ['bank', 'holding', 'securities', 'insurance_life']:
            companies = self.get_companies(sector_code)
            if 'companies' in companies:
                for co in companies['companies']:
                    if name in co['name']:
                        return co['code']

        return None

    def lookup_stat_table(self, keyword: str) -> Optional[Dict]:
        """
        키워드로 통계표 정보 조회 (메타DB 사용)

        Args:
            keyword: 통계표명 또는 코드 (예: "손익계산서", "SA021")

        Returns:
            통계표 정보 딕셔너리 또는 None
        """
        if self.meta_db:
            return self.meta_db.get_stat_table(keyword)
        return None

    def get_companies(
        self,
        sector: str = 'bank',
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        금융회사 목록 조회

        Args:
            sector: 금융권역 코드
            year: 조회 연도

        Returns:
            금융회사 목록
        """
        if sector not in self.SECTORS:
            return {'error': f'유효하지 않은 권역 코드: {sector}'}

        sector_info = self.SECTORS[sector]
        params = {
            'partDiv': sector_info['code'],
        }

        if year:
            params['searchYear'] = str(year)

        result = self._make_request('companySearch', params)

        # 회사 목록 정리
        if 'result' in result and 'list' in result['result']:
            companies = []
            for item in result['result']['list']:
                companies.append({
                    'code': item.get('finance_cd', ''),
                    'name': item.get('finance_nm', ''),
                    'path': item.get('finance_path', ''),
                    'sector': sector_info['name'],
                })
            result['companies'] = companies
            result['total_count'] = result['result'].get('total_count', len(companies))

        return result

    def get_company_info(self, company_code: str) -> Dict[str, Any]:
        """
        금융회사 상세 정보 조회

        Args:
            company_code: 금융회사 코드

        Returns:
            회사 상세 정보
        """
        params = {
            'fncoNo': company_code,
        }
        return self._make_request('companyInfoSearch', params)

    def get_statistics_list(
        self,
        sector: str = 'bank'
    ) -> Dict[str, Any]:
        """
        통계표 목록 조회

        Args:
            sector: 금융권역 코드

        Returns:
            통계표 목록
        """
        if sector not in self.SECTORS:
            return {'error': f'유효하지 않은 권역 코드: {sector}'}

        sector_info = self.SECTORS[sector]
        params = {
            'lrgDiv': sector_info['code'],
        }
        return self._make_request('statisticsListSearch', params)

    def get_statistics_data(
        self,
        stat_code: str,
        year: int,
        quarter: Optional[int] = None,
        company_code: Optional[str] = None,
        term_type: str = 'Q'
    ) -> Dict[str, Any]:
        """
        통계 데이터 조회

        Args:
            stat_code: 통계표 코드 (예: 'SA003', 'SA017')
            year: 조회 연도
            quarter: 분기 (1-4), None이면 연간
            company_code: 금융회사 코드 (선택)
            term_type: 기간 유형 ('Q'=분기, 'Y'=연간)

        Returns:
            통계 데이터

        Example:
            # 2024년 1분기 데이터
            api.get_statistics_data('SA003', 2024, quarter=1)

            # 2023년 연간 데이터
            api.get_statistics_data('SA003', 2023, term_type='Y')
        """
        # 기간 변환
        if quarter:
            start_date, end_date = self.quarter_to_dates(year, quarter)
            term_type = 'Q'
        else:
            start_date, end_date = self.year_to_dates(year)
            term_type = 'Y'

        params = {
            'listNo': stat_code,
            'term': term_type,
            'startBaseMm': start_date,
            'endBaseMm': end_date,
        }

        if company_code:
            params['financeCd'] = company_code

        result = self._make_request('statisticsInfoSearch', params)

        # 데이터 정리
        if 'result' in result and result['result'].get('err_cd') == '000':
            items = result['result'].get('list', [])
            result['data'] = items
            result['total_count'] = result['result'].get('total_count', len(items))

        return result

    def get_statistics_data_range(
        self,
        stat_code: str,
        start_date: str,
        end_date: str,
        company_code: Optional[str] = None,
        term_type: str = 'Q'
    ) -> Dict[str, Any]:
        """
        기간 범위로 통계 데이터 조회 (고급)

        Args:
            stat_code: 통계표 코드
            start_date: 시작 기준월 (YYYYMM)
            end_date: 종료 기준월 (YYYYMM)
            company_code: 금융회사 코드 (선택)
            term_type: 기간 유형 ('Q' 또는 'Y')

        Returns:
            통계 데이터
        """
        params = {
            'listNo': stat_code,
            'term': term_type,
            'startBaseMm': start_date,
            'endBaseMm': end_date,
        }

        if company_code:
            params['financeCd'] = company_code

        return self._make_request('statisticsInfoSearch', params)

    def get_metrics(
        self,
        company_name: str,
        year: int,
        quarter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        회사 경영지표 조회

        Args:
            company_name: 금융회사명
            year: 조회 연도
            quarter: 분기 (선택)

        Returns:
            경영지표 데이터
        """
        # 회사 코드 조회
        company_code = self.lookup_company_code(company_name)
        if not company_code:
            return {'error': f'회사를 찾을 수 없음: {company_name}'}

        # 경영지표 통계표 조회 (SA017 = 수익성지표)
        return self.get_statistics_data('SA017', year, quarter, company_code)

    def get_financial_summary(
        self,
        company_name: str,
        year: int,
        quarter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        회사 재무요약 조회

        Args:
            company_name: 금융회사명
            year: 조회 연도
            quarter: 분기 (선택)

        Returns:
            재무요약 데이터
        """
        company_code = self.lookup_company_code(company_name)
        if not company_code:
            return {'error': f'회사를 찾을 수 없음: {company_name}'}

        # 요약재무상태표 조회 (SA003)
        return self.get_statistics_data('SA003', year, quarter, company_code)

    def search_by_keyword(
        self,
        keyword: str,
        sector: str = 'bank'
    ) -> List[Dict[str, Any]]:
        """
        키워드로 금융회사 검색

        Args:
            keyword: 검색 키워드
            sector: 금융권역

        Returns:
            매칭된 회사 목록
        """
        companies = self.get_companies(sector)

        results = []
        if 'companies' in companies:
            for co in companies['companies']:
                if keyword.lower() in co['name'].lower():
                    results.append(co)

        return results

    # ==================== 내보내기 ====================

    def export_to_csv(
        self,
        data: Union[List, Dict],
        output_path: str,
        encoding: str = 'utf-8-sig'
    ) -> bool:
        """데이터를 CSV로 내보내기"""
        try:
            if isinstance(data, dict):
                if 'data' in data:
                    rows = data['data']
                elif 'list' in data:
                    rows = data['list']
                elif 'companies' in data:
                    rows = data['companies']
                else:
                    rows = [data]
            else:
                rows = data

            if not rows:
                print("내보낼 데이터가 없습니다.")
                return False

            with open(output_path, 'w', encoding=encoding, newline='') as f:
                if isinstance(rows[0], dict):
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                else:
                    writer = csv.writer(f)
                    writer.writerows(rows)

            print(f"CSV 저장 완료: {output_path}")
            return True

        except Exception as e:
            print(f"CSV 저장 실패: {e}")
            return False

    def export_to_json(
        self,
        data: Union[List, Dict],
        output_path: str
    ) -> bool:
        """데이터를 JSON으로 내보내기"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"JSON 저장 완료: {output_path}")
            return True

        except Exception as e:
            print(f"JSON 저장 실패: {e}")
            return False

    # ==================== DB-First 패턴 (v2.1) ====================

    def _normalize_date(self, date_str: str) -> str:
        """
        입력 날짜를 DB 형식(YYYYMM)으로 변환

        Args:
            date_str: 입력 날짜 (YYYY-MM, YYYYMM, YYYY 등)

        Returns:
            YYYYMM 형식의 날짜
        """
        # 하이픈 제거 후 숫자만 추출
        digits = ''.join(c for c in date_str if c.isdigit())
        return digits[:6] if len(digits) >= 6 else digits

    def save_to_db(
        self,
        result: Dict,
        stat_code: str
    ) -> int:
        """
        API 응답을 데이터DB에 저장

        Args:
            result: API 응답 데이터
            stat_code: 통계표 코드

        Returns:
            저장된 레코드 수
        """
        items = result.get('data', [])
        if not items:
            return 0

        saved = self.data_db.save_data(items, stat_code)

        # 동기화 상태 업데이트
        if items:
            first_item = items[0]
            base_period = first_item.get('base_mm', '') or first_item.get('base_yy', '')
            self.data_db.update_sync_status(stat_code, base_period, saved)

        return saved

    def query_db(
        self,
        stat_code: Optional[str] = None,
        company_code: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        데이터 DB 조회

        Args:
            stat_code: 통계표 코드
            company_code: 금융회사 코드
            start_period: 시작 기간 (YYYYMM)
            end_period: 종료 기간 (YYYYMM)
            limit: 조회 건수

        Returns:
            조회 결과 리스트
        """
        return self.data_db.query_data(
            stat_code=stat_code,
            company_code=company_code,
            start_period=start_period,
            end_period=end_period,
            limit=limit
        )

    def get_data_with_db_first(
        self,
        stat_code: str,
        year: int,
        quarter: Optional[int] = None,
        company_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB-First 패턴으로 통계 데이터 조회

        1. DB에서 해당 기간 데이터 확인
        2. DB에 데이터가 있으면 반환
        3. 없으면 API 호출 → DB 저장 → 반환

        Args:
            stat_code: 통계표 코드 (예: SA003)
            year: 조회 연도
            quarter: 분기 (1-4), None이면 연간
            company_code: 금융회사 코드 (선택)

        Returns:
            {
                'data': 데이터 리스트,
                'source': 'db' 또는 'api',
                'db_count': DB에서 조회한 건수,
                'api_count': API에서 조회한 건수,
                'saved': DB에 저장한 건수
            }
        """
        # 기간 계산
        if quarter:
            start_date, end_date = self.quarter_to_dates(year, quarter)
        else:
            start_date, end_date = self.year_to_dates(year)

        result = {
            'data': [],
            'source': None,
            'db_count': 0,
            'api_count': 0,
            'saved': 0,
            'stat_code': stat_code
        }

        # 1. DB에서 기존 데이터 조회
        db_data = self.query_db(
            stat_code=stat_code,
            company_code=company_code,
            start_period=start_date,
            end_period=end_date,
            limit=100000
        )

        if db_data:
            result['data'] = db_data
            result['source'] = 'db'
            result['db_count'] = len(db_data)
            period_str = f"{year}년 {quarter}분기" if quarter else f"{year}년"
            print(f"[DB-First] DB에서 조회: {len(db_data)}건 ({period_str})")
            return result

        # 2. DB에 데이터가 없으면 API 호출
        period_str = f"{year}년 {quarter}분기" if quarter else f"{year}년"
        print(f"[DB-First] API 호출: {stat_code} ({period_str})")

        api_result = self.get_statistics_data(
            stat_code=stat_code,
            year=year,
            quarter=quarter,
            company_code=company_code
        )

        api_data = api_result.get('data', [])
        result['api_count'] = len(api_data)

        # 3. API 데이터 DB에 저장
        if api_data:
            saved = self.save_to_db(api_result, stat_code)
            result['saved'] = saved
            print(f"[DB-First] API에서 조회 → DB 저장: {saved}건")

        result['data'] = api_data
        result['source'] = 'api'
        return result

    def get_data_db_only(
        self,
        stat_code: str,
        start_period: str,
        end_period: str,
        company_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB에서만 데이터 조회 (API 호출 안함)

        Args:
            stat_code: 통계표 코드
            start_period: 시작 기간
            end_period: 종료 기간
            company_code: 금융회사 코드 (선택)

        Returns:
            DB 조회 결과
        """
        start = self._normalize_date(start_period)
        end = self._normalize_date(end_period)

        db_data = self.query_db(
            stat_code=stat_code,
            company_code=company_code,
            start_period=start,
            end_period=end,
            limit=100000
        )

        return {
            'data': db_data,
            'source': 'db',
            'db_count': len(db_data),
            'api_count': 0,
            'saved': 0,
            'stat_code': stat_code
        }


# ==================== CLI 함수 ====================

def print_sectors(api: FisisAPI):
    """금융권역 목록 출력"""
    print("\n=== 금융권역 목록 ===")
    print(f"{'코드':<15} {'권역명':<10} {'설명':<20}")
    print("-" * 50)
    for sector in api.get_sectors():
        print(f"{sector['code']:<15} {sector['name']:<10} {sector['desc']:<20}")


def print_companies(api: FisisAPI, sector: str, year: Optional[int] = None):
    """금융회사 목록 출력"""
    result = api.get_companies(sector, year)

    if 'error' in result:
        print(f"오류: {result['error']}")
        return

    sector_name = api.SECTORS.get(sector, {}).get('name', sector)
    print(f"\n=== {sector_name} 금융회사 목록 ===")

    if 'companies' in result:
        for i, co in enumerate(result['companies'], 1):
            print(f"{i:3}. {co['name']} ({co['code']})")
    else:
        print("데이터가 없습니다.")


def print_stat_codes(api: FisisAPI, sector: str = 'bank'):
    """통계표 코드 목록 출력"""
    result = api.get_statistics_list(sector)

    if 'result' not in result or 'list' not in result['result']:
        print("통계표 목록을 가져올 수 없습니다.")
        return

    tables = result['result']['list']
    sector_name = api.SECTORS.get(sector, {}).get('name', sector)

    print(f"\n=== {sector_name} 통계표 목록 ({len(tables)}개) ===")
    print(f"{'코드':<10} {'통계표명':<40}")
    print("-" * 55)

    for t in tables[:30]:  # 상위 30개
        code = t.get('list_no', '')
        name = t.get('list_nm', '')
        print(f"{code:<10} {name:<40}")


def print_statistics(api: FisisAPI, stat_code: str, year: int, quarter: Optional[int], company: Optional[str]):
    """통계 데이터 출력"""
    company_code = None
    if company:
        company_code = api.lookup_company_code(company)
        if not company_code:
            print(f"회사를 찾을 수 없음: {company}")
            return None

    result = api.get_statistics_data(stat_code, year, quarter, company_code)

    if 'error' in result:
        print(f"오류: {result['error']}")
        return result

    err_cd = result.get('result', {}).get('err_cd', '')
    if err_cd != '000':
        err_msg = result.get('result', {}).get('err_msg', 'Unknown error')
        print(f"API 오류 [{err_cd}]: {err_msg}")
        return result

    items = result.get('data', [])
    period = f"{year}년 {quarter}분기" if quarter else f"{year}년"
    company_str = f" - {company}" if company else ""

    print(f"\n=== 통계 데이터: {stat_code} ({period}){company_str} ===")
    print(f"총 {len(items)}건")
    print()

    # 상위 20개 출력 (필드명: account_nm, a=금액, b=비율)
    print(f"{'계정명':<35} {'금액':>18} {'비율':>8}")
    print("-" * 65)
    for item in items[:20]:
        name = (item.get('account_nm') or item.get('itm_nm') or 'N/A')[:33]
        amount = item.get('a') or item.get('data_val') or '-'
        ratio = item.get('b') or ''

        # 금액 포맷팅 (천원 단위)
        try:
            if amount and amount != '-':
                amount_int = int(amount)
                if amount_int >= 100000000:
                    amount = f"{amount_int/100000000:,.0f}억"
                elif amount_int >= 10000:
                    amount = f"{amount_int/10000:,.0f}만"
                else:
                    amount = f"{amount_int:,}"
        except:
            pass

        ratio_str = f"{ratio}%" if ratio else ""
        print(f"{name:<35} {amount:>18} {ratio_str:>8}")

    return result


def print_metrics(api: FisisAPI, company: str, year: int, quarter: Optional[int] = None):
    """경영지표 출력"""
    result = api.get_metrics(company, year, quarter)

    if 'error' in result:
        print(f"오류: {result['error']}")
        return result

    err_cd = result.get('result', {}).get('err_cd', '')
    if err_cd != '000':
        err_msg = result.get('result', {}).get('err_msg', 'Unknown error')
        print(f"API 오류 [{err_cd}]: {err_msg}")
        return result

    items = result.get('data', [])
    period = f"{year}년 {quarter}분기" if quarter else f"{year}년"

    print(f"\n=== {company} 경영지표 ({period}) ===")
    print(f"{'지표명':<40} {'값':>15}")
    print("-" * 58)

    for item in items:
        name = (item.get('account_nm') or item.get('itm_nm') or '')[:38]
        value = item.get('a') or item.get('data_val') or '-'

        # 값 포맷팅
        try:
            if value and value != '-':
                val_float = float(value)
                if val_float >= 1000000000000:  # 1조 이상
                    value = f"{val_float/1000000000000:,.1f}조"
                elif val_float >= 100000000:  # 1억 이상
                    value = f"{val_float/100000000:,.0f}억"
                elif val_float < 100:  # 비율
                    value = f"{val_float:.2f}%"
        except:
            pass

        print(f"{name:<40} {value:>15}")

    return result


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='FISIS 금융통계정보시스템 OpenAPI 클라이언트 v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 금융권역 목록
  python fisis_api.py --sectors

  # 은행 목록 조회
  python fisis_api.py --list-companies --sector bank

  # 통계표 목록 조회
  python fisis_api.py --list-stats --sector bank

  # 2024년 1분기 통계 데이터 조회
  python fisis_api.py --stat-code SA003 --year 2024 --quarter 1

  # 특정 회사 경영지표 조회
  python fisis_api.py --company "신한은행" --metrics --year 2024 --quarter 1

  # API 상태 확인
  python fisis_api.py --status
        """
    )

    # 조회 유형
    parser.add_argument('--sectors', action='store_true',
                        help='금융권역 목록 출력')
    parser.add_argument('--list-companies', action='store_true',
                        help='금융회사 목록 조회')
    parser.add_argument('--list-stats', action='store_true',
                        help='통계표 목록 조회')
    parser.add_argument('--status', action='store_true',
                        help='API 엔드포인트 상태 확인')

    # 필터 옵션
    parser.add_argument('--sector', type=str, default='bank',
                        help='금융권역 코드 (기본: bank)')
    parser.add_argument('--company', '-c', type=str,
                        help='금융회사명')
    parser.add_argument('--stat-code', type=str,
                        help='통계표 코드 (예: SA003, SA017)')

    # 상세 옵션
    parser.add_argument('--info', action='store_true',
                        help='회사 기본정보 조회')
    parser.add_argument('--metrics', action='store_true',
                        help='경영지표 조회')
    parser.add_argument('--financials', action='store_true',
                        help='재무요약 조회')

    # 기간 옵션
    parser.add_argument('--year', type=int, default=datetime.now().year,
                        help='조회 연도 (기본: 현재연도)')
    parser.add_argument('--quarter', '-q', type=int, choices=[1, 2, 3, 4],
                        help='분기 (1-4)')

    # 출력 옵션
    parser.add_argument('--output', '-o', type=str,
                        help='결과 저장 파일 (json/csv)')
    parser.add_argument('--api-key', type=str,
                        help='API 인증키 (환경변수 대신 직접 지정)')

    # DB 옵션
    parser.add_argument('--db-stats', action='store_true',
                        help='데이터 DB 통계 출력')
    parser.add_argument('--query-db', action='store_true',
                        help='DB에서 데이터 조회 (--stat-code 사용)')
    parser.add_argument('--save-db', action='store_true',
                        help='API 결과를 DB에 저장')
    parser.add_argument('--force-api', action='store_true',
                        help='DB 무시하고 API 직접 호출')
    parser.add_argument('--db-only', action='store_true',
                        help='DB에서만 조회 (API 호출 안함)')
    parser.add_argument('--db-first', action='store_true',
                        help='DB-First 패턴으로 조회 (기본값, DB→API 순서)')

    args = parser.parse_args()

    # API 클라이언트 초기화
    api = FisisAPI(api_key=args.api_key)

    # 명령 실행
    result = None

    if args.status:
        print("\n=== FISIS API 상태 확인 ===")
        status = api.check_api_status()
        print(f"확인 시각: {status['timestamp']}")
        print()
        for name, info in status['endpoints'].items():
            if info['status'] == 'OK':
                count_str = f" ({info.get('count', '')}건)" if 'count' in info else ""
                print(f"  [OK] {name}: 정상{count_str}")
            else:
                print(f"  [ERROR] {name}: {info.get('message', '')}")

    elif args.sectors:
        print_sectors(api)

    elif args.list_companies:
        if args.output:
            result = api.get_companies(args.sector, args.year)
        else:
            print_companies(api, args.sector, args.year)

    elif args.list_stats:
        print_stat_codes(api, args.sector)

    elif args.company and args.metrics:
        result = print_metrics(api, args.company, args.year, args.quarter)

    elif args.company and args.financials:
        result = api.get_financial_summary(args.company, args.year, args.quarter)
        if 'data' in result:
            print(f"\n=== {args.company} 재무요약 ===")
            for item in result['data'][:15]:
                name = item.get('itm_nm', '')
                value = item.get('data_val', '')
                print(f"  {name}: {value}")

    elif args.company and args.info:
        matches = api.search_by_keyword(args.company, args.sector)
        if matches:
            result = api.get_company_info(matches[0]['code'])
            if not args.output:
                print(f"\n=== {args.company} 기본정보 ===")
                print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"회사를 찾을 수 없음: {args.company}")

    elif args.db_stats:
        # 데이터 DB 통계
        stats = api.data_db.get_stats()
        print('\n=== FISIS 데이터DB 통계 ===')
        print(f'총 레코드: {stats["total_records"]:,}건')
        print(f'통계표 수: {stats["stat_count"]}개')
        print(f'금융회사 수: {stats["company_count"]}개')
        if stats['date_range'][0]:
            print(f'데이터 기간: {stats["date_range"][0]} ~ {stats["date_range"][1]}')

        if stats['stats_by_code']:
            print('\n통계표별 레코드 수:')
            for s in stats['stats_by_code']:
                print(f'  {s["stat_code"]}: {s["cnt"]:,}건')

        if stats['recent_syncs']:
            print('\n최근 동기화:')
            for s in stats['recent_syncs']:
                print(f'  {s["stat_code"]} {s["base_period"]}: {s["total_count"]}건 ({s["synced_at"][:16]})')

        print(f'\nDB 위치: {api.data_db.db_path}')

    elif args.stat_code:
        # DB-First 패턴 처리
        if args.db_only:
            # DB에서만 조회
            if args.quarter:
                start_date, end_date = api.quarter_to_dates(args.year, args.quarter)
            else:
                start_date, end_date = api.year_to_dates(args.year)

            # 회사 코드 조회
            company_code = None
            if args.company:
                company_code = api.lookup_company_code(args.company)

            db_result = api.get_data_db_only(
                stat_code=args.stat_code,
                start_period=start_date,
                end_period=end_date,
                company_code=company_code
            )
            period = f"{args.year}년 {args.quarter}분기" if args.quarter else f"{args.year}년"
            print(f"\n=== 통계 데이터: {args.stat_code} ({period}) - DB 조회 ===")
            print(f"총 {db_result['db_count']}건")
            print()
            print(f"{'회사명':<20} {'계정명':<35} {'값':>18}")
            print("-" * 75)
            for item in db_result['data'][:20]:
                name = (item.get('company_name') or '')[:18]
                acct = (item.get('item_name') or '')[:33]
                value = item.get('data_value')
                if value:
                    try:
                        if abs(value) >= 100000000:
                            val_str = f"{value/100000000:,.0f}억"
                        elif abs(value) >= 10000:
                            val_str = f"{value/10000:,.0f}만"
                        else:
                            val_str = f"{value:,.2f}"
                    except:
                        val_str = str(value)
                else:
                    val_str = '-'
                print(f"{name:<20} {acct:<35} {val_str:>18}")
            result = db_result
        elif args.force_api:
            # API 직접 호출 (기존 방식)
            result = print_statistics(api, args.stat_code, args.year, args.quarter, args.company)
            # DB 저장 옵션
            if args.save_db and result:
                saved = api.save_to_db(result, args.stat_code)
                print(f"\nDB 저장: {saved}건")
        else:
            # DB-First 패턴 (기본값)
            company_code = None
            if args.company:
                company_code = api.lookup_company_code(args.company)

            db_first_result = api.get_data_with_db_first(
                stat_code=args.stat_code,
                year=args.year,
                quarter=args.quarter,
                company_code=company_code
            )

            source_str = "DB" if db_first_result['source'] == 'db' else "API"
            total_count = db_first_result['db_count'] or db_first_result['api_count']
            period = f"{args.year}년 {args.quarter}분기" if args.quarter else f"{args.year}년"
            company_str = f" - {args.company}" if args.company else ""

            print(f"\n=== 통계 데이터: {args.stat_code} ({period}){company_str} ({total_count}건, {source_str}) ===")
            print()
            print(f"{'회사명':<20} {'계정명':<35} {'값':>18}")
            print("-" * 75)

            for item in db_first_result['data'][:20]:
                if db_first_result['source'] == 'db':
                    name = (item.get('company_name') or '')[:18]
                    acct = (item.get('item_name') or '')[:33]
                    value = item.get('data_value')
                else:
                    name = (item.get('finance_nm') or '')[:18]
                    acct = (item.get('account_nm', item.get('itm_nm', '')) or '')[:33]
                    amount = item.get('a', item.get('data_val', '-'))
                    try:
                        value = float(str(amount).replace(',', '')) if amount and amount != '-' else None
                    except:
                        value = None

                if value:
                    try:
                        if abs(value) >= 100000000:
                            val_str = f"{value/100000000:,.0f}억"
                        elif abs(value) >= 10000:
                            val_str = f"{value/10000:,.0f}만"
                        elif abs(value) < 100:
                            val_str = f"{value:.2f}%"
                        else:
                            val_str = f"{value:,.0f}"
                    except:
                        val_str = str(value)
                else:
                    val_str = '-'
                print(f"{name:<20} {acct:<35} {val_str:>18}")

            result = db_first_result

    else:
        parser.print_help()
        return

    # 결과 저장
    if args.output and result:
        if args.output.endswith('.csv'):
            api.export_to_csv(result, args.output)
        else:
            api.export_to_json(result, args.output)


if __name__ == '__main__':
    main()
