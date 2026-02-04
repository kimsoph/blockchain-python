# -*- coding: utf-8 -*-
"""
FRED OpenAPI Client
미국 연방준비제도 FRED OpenAPI 클라이언트

Author: Claude Code
Version: 1.0.0

Features:
- 시리즈 검색
- 시리즈 정보 조회
- 시계열 데이터 조회
- 메타데이터 SQLite DB 관리
- SQLite DB 저장 (fred.db)
- CSV/JSON 내보내기
"""

import os
import sys
import json
import csv
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
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
    from fred_meta_db import FredMetaDB
    HAS_META_DB = True
except ImportError:
    HAS_META_DB = False


class FredAPI:
    """FRED OpenAPI 클라이언트 클래스"""

    # API Base URL
    BASE_URL = "https://api.stlouisfed.org/fred"

    # 데이터 DB 경로 (R-DB/fred.db)
    DATA_DB_PATH = Path(__file__).parents[4] / '3_Resources' / 'R-DB' / 'fred.db'

    # DB 스키마
    DB_SCHEMA = """
    -- 메인 데이터 테이블
    CREATE TABLE IF NOT EXISTS fred_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id TEXT NOT NULL,
        title TEXT,
        date TEXT NOT NULL,
        value TEXT,
        frequency TEXT,
        units TEXT,
        raw_data TEXT,
        collected_at TEXT,
        UNIQUE(series_id, date)
    );

    -- 수집 로그 테이블
    CREATE TABLE IF NOT EXISTS collection_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id TEXT,
        observation_start TEXT,
        observation_end TEXT,
        status TEXT,
        record_count INTEGER,
        error_message TEXT,
        collected_at TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_fred_series ON fred_data(series_id);
    CREATE INDEX IF NOT EXISTS idx_fred_date ON fred_data(date);
    CREATE INDEX IF NOT EXISTS idx_log_series ON collection_log(series_id);
    """

    # 빈도 코드
    FREQUENCIES = {
        'd': 'Daily',
        'w': 'Weekly',
        'bw': 'Biweekly',
        'm': 'Monthly',
        'q': 'Quarterly',
        'sa': 'Semiannual',
        'a': 'Annual',
    }

    # 인기 시리즈 (하드코딩)
    POPULAR_SERIES = {
        'DGS1': '1년 국채 금리',
        'DGS2': '2년 국채 금리',
        'DGS3': '3년 국채 금리',
        'DGS5': '5년 국채 금리',
        'DGS7': '7년 국채 금리',
        'DGS10': '10년 국채 금리',
        'DGS20': '20년 국채 금리',
        'DGS30': '30년 국채 금리',
        'FEDFUNDS': '연방기금금리',
        'DFEDTARU': '연방기금 목표금리 상한',
        'DFEDTARL': '연방기금 목표금리 하한',
        'T10Y2Y': '10년-2년 금리 스프레드',
        'T10Y3M': '10년-3개월 금리 스프레드',
        'UNRATE': '실업률',
        'PAYEMS': '비농업 고용자 수',
        'ICSA': '실업수당 청구건수',
        'CPIAUCSL': '소비자물가지수(CPI)',
        'CPILFESL': '근원 CPI',
        'PCEPI': 'PCE 물가지수',
        'PCEPILFE': '근원 PCE',
        'GDP': '명목 GDP',
        'GDPC1': '실질 GDP',
        'A191RL1Q225SBEA': '실질 GDP 성장률(분기)',
        'DEXKOUS': '원/달러 환율',
        'DEXJPUS': '엔/달러 환율',
        'DEXUSEU': '유로/달러 환율',
        'DEXCHUS': '위안/달러 환율',
        'SP500': 'S&P 500 지수',
        'NASDAQCOM': '나스닥 종합지수',
        'VIXCLS': 'VIX 변동성 지수',
        'M2SL': 'M2 통화량',
        'WALCL': '연준 총자산',
        'HOUST': '주택착공건수',
        'HSN1F': '신규주택판매',
        'RSAFS': '소매판매',
        'UMCSENT': '미시간대 소비자심리지수',
    }

    def __init__(self, api_key: Optional[str] = None, use_meta_db: bool = True):
        """
        FredAPI 초기화

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

        # 데이터 디렉토리
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.data_dir.mkdir(exist_ok=True)

        # 메타데이터 DB 초기화
        self.meta_db = None
        if use_meta_db and HAS_META_DB:
            try:
                self.meta_db = FredMetaDB()
                self.meta_db.connect()
            except Exception:
                self.meta_db = None

    def _load_api_key(self) -> str:
        """환경변수에서 API 키 로드"""
        env_paths = [
            Path('.claude/.env'),
            Path('.env'),
            Path.home() / '.fred_api_key',
        ]

        if load_dotenv:
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path)
                    break

        api_key = os.getenv('FRED_API_KEY')
        if not api_key:
            print("경고: FRED_API_KEY가 설정되지 않았습니다.")
            print("  .claude/.env 파일에 FRED_API_KEY=your_key 형식으로 설정하세요.")
        return api_key or ''

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        API 요청 실행

        Args:
            endpoint: API 엔드포인트
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
            response = self.session.get(url, params=request_params, timeout=30)
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
            return {'error': 'REQUEST_ERROR', 'message': f'요청 실패: {str(e)}'}
        except json.JSONDecodeError as e:
            return {'error': 'PARSE_ERROR', 'message': f'JSON 파싱 실패: {str(e)}'}

    def _check_response(self, result: Dict, key: str = None) -> bool:
        """응답 상태 확인"""
        if 'error' in result:
            print(f"오류: {result.get('error')} - {result.get('message', '')}")
            return False
        if key and key not in result:
            print(f"응답에 '{key}'가 없습니다.")
            return False
        return True

    # ==================== 메타데이터 관리 ====================

    def sync_metadata(self, force: bool = False) -> bool:
        """
        메타데이터 동기화

        Args:
            force: 강제 동기화 여부

        Returns:
            성공 여부
        """
        if self.meta_db:
            results = self.meta_db.sync_all(force=force)
            return sum(results.values()) > 0
        else:
            print("메타데이터 DB를 사용할 수 없습니다.")
            return False

    def get_db_stats(self) -> Optional[Dict]:
        """메타DB 통계 조회"""
        if self.meta_db:
            return self.meta_db.get_stats()
        return None

    def search_local(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        메타DB에서 시리즈 검색

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        if self.meta_db:
            return self.meta_db.search_series(keyword, limit=limit)
        return []

    # ==================== 시리즈 API ====================

    def search_series(
        self,
        search_text: str,
        limit: int = 100,
        order_by: str = 'popularity',
        sort_order: str = 'desc'
    ) -> Dict[str, Any]:
        """
        시리즈 검색 (API)

        Args:
            search_text: 검색어
            limit: 최대 결과 수
            order_by: 정렬 기준 (search_rank, series_id, title, popularity 등)
            sort_order: 정렬 순서 (asc, desc)

        Returns:
            검색 결과
        """
        result = self._make_request('series/search', {
            'search_text': search_text,
            'limit': limit,
            'order_by': order_by,
            'sort_order': sort_order
        })
        return result

    def get_series(self, series_id: str) -> Dict[str, Any]:
        """
        시리즈 정보 조회

        Args:
            series_id: 시리즈 ID (예: DGS10)

        Returns:
            시리즈 정보
        """
        result = self._make_request('series', {'series_id': series_id})
        return result

    def get_observations(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        frequency: Optional[str] = None,
        units: str = 'lin',
        limit: int = 100000
    ) -> Dict[str, Any]:
        """
        시계열 데이터 조회

        Args:
            series_id: 시리즈 ID
            observation_start: 시작일 (YYYY-MM-DD)
            observation_end: 종료일 (YYYY-MM-DD)
            frequency: 빈도 변환 (d, w, bw, m, q, sa, a)
            units: 단위 (lin, chg, ch1, pch, pc1, pca, cch, cca, log)
            limit: 최대 결과 수

        Returns:
            시계열 데이터
        """
        params = {
            'series_id': series_id,
            'units': units,
            'limit': limit
        }

        if observation_start:
            params['observation_start'] = observation_start
        if observation_end:
            params['observation_end'] = observation_end
        if frequency:
            params['frequency'] = frequency

        result = self._make_request('series/observations', params)
        return result

    # ==================== 유틸리티 ====================

    def export_to_csv(
        self,
        data: Union[List, Dict],
        output_path: str,
        encoding: str = 'utf-8-sig'
    ) -> bool:
        """
        데이터를 CSV로 내보내기

        Args:
            data: 내보낼 데이터
            output_path: 출력 파일 경로
            encoding: 파일 인코딩

        Returns:
            성공 여부
        """
        try:
            # 데이터 추출
            if isinstance(data, dict):
                # API 응답에서 observations 또는 seriess 추출
                rows = data.get('observations', data.get('seriess', []))
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
        """
        데이터를 JSON으로 내보내기

        Args:
            data: 내보낼 데이터
            output_path: 출력 파일 경로

        Returns:
            성공 여부
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"JSON 저장 완료: {output_path}")
            return True

        except Exception as e:
            print(f"JSON 저장 실패: {e}")
            return False

    # ==================== DB 저장 기능 ====================

    def _get_data_db_connection(self) -> sqlite3.Connection:
        """데이터 DB 연결 (없으면 생성)"""
        self.DATA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.DATA_DB_PATH))
        conn.executescript(self.DB_SCHEMA)
        conn.commit()
        return conn

    def save_to_db(
        self,
        data: Dict[str, Any],
        series_id: str
    ) -> int:
        """
        API 응답 데이터를 fred.db에 저장

        Args:
            data: API 응답 데이터 (observations)
            series_id: 시리즈 ID

        Returns:
            저장된 레코드 수
        """
        observations = data.get('observations', [])
        if not observations:
            self._log_collection(series_id, None, None, 'error', 0, 'No observations')
            return 0

        # 시리즈 정보 조회
        series_info = self.get_series(series_id)
        title = ''
        frequency = ''
        units = ''
        if 'seriess' in series_info and series_info['seriess']:
            info = series_info['seriess'][0]
            title = info.get('title', '')
            frequency = info.get('frequency', '')
            units = info.get('units', '')

        conn = self._get_data_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        saved_count = 0

        start_date = None
        end_date = None

        try:
            for obs in observations:
                date = obs.get('date', '')
                value = obs.get('value', '')

                if not start_date or date < start_date:
                    start_date = date
                if not end_date or date > end_date:
                    end_date = date

                cursor.execute('''
                    INSERT OR REPLACE INTO fred_data
                    (series_id, title, date, value, frequency, units, raw_data, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    series_id,
                    title,
                    date,
                    value,
                    frequency,
                    units,
                    json.dumps(obs, ensure_ascii=False),
                    now
                ))
                saved_count += 1

            conn.commit()
            self._log_collection(series_id, start_date, end_date, 'success', saved_count, None)
            print(f"DB 저장 완료: {saved_count}건 → {self.DATA_DB_PATH.name}")

        except Exception as e:
            conn.rollback()
            self._log_collection(series_id, start_date, end_date, 'error', 0, str(e))
            print(f"DB 저장 실패: {e}")

        finally:
            conn.close()

        return saved_count

    def _log_collection(
        self,
        series_id: str,
        start: Optional[str],
        end: Optional[str],
        status: str,
        record_count: int,
        error_message: Optional[str]
    ):
        """수집 로그 기록"""
        try:
            conn = self._get_data_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO collection_log
                (series_id, observation_start, observation_end, status,
                 record_count, error_message, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                series_id, start, end, status,
                record_count, error_message, datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_data_db_stats(self) -> Dict[str, Any]:
        """데이터 DB 통계 조회"""
        if not self.DATA_DB_PATH.exists():
            return {}

        conn = self._get_data_db_connection()
        cursor = conn.cursor()

        stats = {}

        # 총 레코드 수
        cursor.execute('SELECT COUNT(*) FROM fred_data')
        stats['total_records'] = cursor.fetchone()[0]

        # 시리즈별 레코드 수
        cursor.execute('''
            SELECT series_id, title, COUNT(*) as cnt,
                   MIN(date) as min_date, MAX(date) as max_date
            FROM fred_data
            GROUP BY series_id
            ORDER BY cnt DESC
        ''')
        stats['by_series'] = [
            {'series_id': r[0], 'title': r[1], 'count': r[2],
             'min_date': r[3], 'max_date': r[4]}
            for r in cursor.fetchall()
        ]

        # 최근 수집 로그
        cursor.execute('''
            SELECT series_id, status, record_count, collected_at
            FROM collection_log
            ORDER BY collected_at DESC
            LIMIT 10
        ''')
        stats['recent_logs'] = [
            {'series_id': r[0], 'status': r[1], 'count': r[2], 'collected_at': r[3]}
            for r in cursor.fetchall()
        ]

        conn.close()
        return stats

    def query_db(
        self,
        series_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        데이터 DB 조회

        Args:
            series_id: 시리즈 ID
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            limit: 조회 건수

        Returns:
            조회 결과 리스트
        """
        if not self.DATA_DB_PATH.exists():
            return []

        conn = self._get_data_db_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM fred_data WHERE 1=1'
        params = []

        if series_id:
            query += ' AND series_id = ?'
            params.append(series_id)
        if start_date:
            query += ' AND date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND date <= ?'
            params.append(end_date)

        query += f' ORDER BY date DESC LIMIT {limit}'

        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return results

    # ==================== DB-First 패턴 (v1.1) ====================

    def _normalize_date(self, date_str: str) -> str:
        """
        입력 날짜를 DB 형식(YYYY-MM-DD)으로 변환

        Args:
            date_str: 입력 날짜 (YYYYMM, YYYY-MM, YYYY-MM-DD 등)

        Returns:
            YYYY-MM-DD 형식의 날짜
        """
        # 숫자만 추출
        digits = ''.join(c for c in date_str if c.isdigit())

        if len(digits) == 6:  # YYYYMM
            return f"{digits[:4]}-{digits[4:6]}-01"
        elif len(digits) == 8:  # YYYYMMDD
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        elif '-' in date_str and len(date_str) == 10:  # YYYY-MM-DD
            return date_str
        elif '-' in date_str and len(date_str) == 7:  # YYYY-MM
            return f"{date_str}-01"
        else:
            return date_str

    def get_observations_with_db_first(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        frequency: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB-First 패턴으로 시계열 데이터 조회

        1. DB에서 해당 기간 데이터 확인
        2. DB에 데이터가 있고 기간이 충족되면 반환
        3. 없거나 기간이 부족하면 API 호출 → DB 저장 → 반환

        Args:
            series_id: 시리즈 ID (예: DGS10)
            observation_start: 시작일
            observation_end: 종료일
            frequency: 빈도 변환 (d, w, bw, m, q, sa, a)

        Returns:
            {
                'data': 데이터 리스트,
                'source': 'db' 또는 'api',
                'db_count': DB에서 조회한 건수,
                'api_count': API에서 조회한 건수,
                'saved': DB에 저장한 건수
            }
        """
        # 날짜 정규화
        start_date = self._normalize_date(observation_start) if observation_start else None
        end_date = self._normalize_date(observation_end) if observation_end else None

        result = {
            'data': [],
            'source': None,
            'db_count': 0,
            'api_count': 0,
            'saved': 0,
            'series_id': series_id
        }

        # 1. DB에서 기존 데이터 조회
        db_data = self.query_db(
            series_id=series_id,
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )

        if db_data and start_date and end_date:
            # DB 데이터 기간 확인
            db_dates = [d['date'] for d in db_data]
            db_start = min(db_dates)
            db_end = max(db_dates)

            # 요청 기간이 DB 데이터로 충족되면 반환
            if db_start <= start_date and db_end >= end_date:
                # 기간 내 데이터만 필터링
                filtered = [
                    d for d in db_data
                    if start_date <= d['date'] <= end_date
                ]
                result['data'] = sorted(filtered, key=lambda x: x['date'])
                result['source'] = 'db'
                result['db_count'] = len(filtered)
                print(f"[DB-First] DB에서 조회: {len(filtered)}건 ({start_date}~{end_date})")
                return result

        # 2. DB에 데이터가 없거나 기간이 부족하면 API 호출
        print(f"[DB-First] API 호출: {series_id} ({start_date}~{end_date})")
        api_result = self.get_observations(
            series_id=series_id,
            observation_start=start_date,
            observation_end=end_date,
            frequency=frequency
        )

        if 'observations' not in api_result:
            result['source'] = 'api'
            result['api_count'] = 0
            return result

        api_rows = api_result.get('observations', [])
        result['api_count'] = len(api_rows)

        # 3. API 데이터 DB에 저장
        if api_rows:
            saved = self.save_to_db(api_result, series_id)
            result['saved'] = saved
            print(f"[DB-First] API에서 조회 → DB 저장: {saved}건")

        # 4. 결과 반환 (API 원본 형식 그대로)
        result['data'] = api_rows
        result['source'] = 'api'
        return result

    def get_data_db_only(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB에서만 데이터 조회 (API 호출 안함)

        Args:
            series_id: 시리즈 ID
            start_date: 시작일
            end_date: 종료일

        Returns:
            DB 조회 결과
        """
        start = self._normalize_date(start_date) if start_date else None
        end = self._normalize_date(end_date) if end_date else None

        db_data = self.query_db(
            series_id=series_id,
            start_date=start,
            end_date=end,
            limit=100000
        )

        return {
            'data': sorted(db_data, key=lambda x: x['date']),
            'source': 'db',
            'db_count': len(db_data),
            'api_count': 0,
            'saved': 0,
            'series_id': series_id
        }


# ==================== CLI 함수 ====================

def print_search_result(api: FredAPI, args):
    """검색 결과 출력"""
    result = api.search_series(args.search, limit=args.limit)

    if not api._check_response(result, 'seriess'):
        return result

    items = result.get('seriess', [])
    print(f"\n=== '{args.search}' 검색 결과 ({len(items)}건) ===")
    print(f"{'시리즈ID':<15} {'제목':<50} {'빈도':<8} {'인기도':<6}")
    print("-" * 85)

    for item in items:
        sid = (item.get('id') or '')[:13]
        title = (item.get('title') or '')[:48]
        freq = item.get('frequency_short') or '-'
        pop = item.get('popularity') or 0
        print(f"{sid:<15} {title:<50} {freq:<8} {pop:<6}")

    return result


def print_series_info(api: FredAPI, args):
    """시리즈 정보 출력"""
    result = api.get_series(args.info)

    if not api._check_response(result, 'seriess'):
        return result

    seriess = result.get('seriess', [])
    if not seriess:
        print(f"시리즈 '{args.info}'를 찾을 수 없습니다.")
        return result

    info = seriess[0]
    print(f"\n=== 시리즈 정보: {args.info} ===")
    print(f"시리즈 ID: {info.get('id', '')}")
    print(f"제목: {info.get('title', '')}")
    print(f"빈도: {info.get('frequency', '')} ({info.get('frequency_short', '')})")
    print(f"단위: {info.get('units', '')}")
    print(f"계절조정: {info.get('seasonal_adjustment', '')}")
    print(f"기간: {info.get('observation_start', '')} ~ {info.get('observation_end', '')}")
    print(f"인기도: {info.get('popularity', 0)}")
    print(f"마지막 업데이트: {info.get('last_updated', '')}")

    if info.get('notes'):
        notes = info['notes'][:300] + '...' if len(info['notes']) > 300 else info['notes']
        print(f"설명: {notes}")

    # 한글 설명 추가
    if args.info in api.POPULAR_SERIES:
        print(f"한글명: {api.POPULAR_SERIES[args.info]}")

    return result


def print_observations(api: FredAPI, args):
    """시계열 데이터 출력"""
    # 최근 N일 옵션 처리
    start_date = args.start
    end_date = args.end

    if args.recent:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.recent)).strftime('%Y-%m-%d')

    result = api.get_observations(
        series_id=args.data,
        observation_start=start_date,
        observation_end=end_date,
        frequency=args.frequency
    )

    if not api._check_response(result, 'observations'):
        return result

    observations = result.get('observations', [])

    # 시리즈 정보
    series_info = api.get_series(args.data)
    title = args.data
    units = ''
    if 'seriess' in series_info and series_info['seriess']:
        info = series_info['seriess'][0]
        title = info.get('title', args.data)
        units = info.get('units', '')

    print(f"\n=== [{args.data}] {title} ({len(observations)}건) ===")
    if start_date or end_date:
        print(f"기간: {start_date or '처음'} ~ {end_date or '현재'}")
    print(f"{'날짜':<12} {'값':<20} {'단위':<15}")
    print("-" * 50)

    # 최근 데이터부터 출력
    for obs in observations[-args.limit:][::-1]:
        date = obs.get('date', '')
        value = obs.get('value', '.')
        if value == '.':
            value = '(결측)'
        print(f"{date:<12} {value:<20} {units:<15}")

    return result


def print_popular_series(api: FredAPI):
    """인기 시리즈 출력"""
    print(f"\n=== FRED 인기 시리즈 ({len(api.POPULAR_SERIES)}개) ===")
    print(f"{'시리즈ID':<20} {'한글명':<30}")
    print("-" * 55)

    for series_id, desc_kr in api.POPULAR_SERIES.items():
        print(f"{series_id:<20} {desc_kr:<30}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='FRED 미국 연방준비제도 OpenAPI 클라이언트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 메타데이터 동기화
  python fred_api.py --sync

  # 메타DB 통계
  python fred_api.py --stats

  # 시리즈 검색 (API)
  python fred_api.py --search "treasury"

  # 로컬 검색 (메타DB)
  python fred_api.py --search-local "interest"

  # 인기 시리즈 목록
  python fred_api.py --popular

  # 시리즈 정보
  python fred_api.py --info DGS10

  # 데이터 조회
  python fred_api.py --data DGS10
  python fred_api.py --data DGS10 --start 2024-01-01 --end 2024-12-31
  python fred_api.py --data DGS10 --recent 365

  # 결과 저장
  python fred_api.py --data DGS10 --recent 365 --output result.csv
  python fred_api.py --data DGS10 --save-db

  # 데이터 DB 조회
  python fred_api.py --db-stats
  python fred_api.py --query-db --series DGS10
        """
    )

    # 메타데이터 관리
    parser.add_argument('--sync', action='store_true',
                        help='메타데이터 DB 동기화')
    parser.add_argument('--force', action='store_true',
                        help='강제 동기화')
    parser.add_argument('--stats', action='store_true',
                        help='메타DB 통계 출력')

    # 검색
    parser.add_argument('--search', type=str, metavar='TEXT',
                        help='시리즈 검색 (API)')
    parser.add_argument('--search-local', type=str, metavar='KEYWORD',
                        help='메타DB에서 시리즈 검색')
    parser.add_argument('--popular', action='store_true',
                        help='인기 시리즈 목록')

    # 시리즈 정보
    parser.add_argument('--info', type=str, metavar='SERIES_ID',
                        help='시리즈 정보 조회')

    # 데이터 조회
    parser.add_argument('--data', type=str, metavar='SERIES_ID',
                        help='시계열 데이터 조회')
    parser.add_argument('--start', type=str, metavar='YYYY-MM-DD',
                        help='시작일')
    parser.add_argument('--end', type=str, metavar='YYYY-MM-DD',
                        help='종료일')
    parser.add_argument('--recent', type=int, metavar='DAYS',
                        help='최근 N일 데이터')
    parser.add_argument('--frequency', '-f', type=str,
                        choices=['d', 'w', 'bw', 'm', 'q', 'sa', 'a'],
                        help='빈도 변환 (d=일, w=주, m=월, q=분기, a=연)')

    # 출력 옵션
    parser.add_argument('--limit', type=int, default=50,
                        help='조회/출력 건수 (기본: 50)')
    parser.add_argument('--output', '-o', type=str,
                        help='결과 저장 파일 (json/csv)')
    parser.add_argument('--save-db', action='store_true',
                        help='결과를 fred.db에 저장')

    # 데이터 DB
    parser.add_argument('--db-stats', action='store_true',
                        help='데이터 DB 통계 출력')
    parser.add_argument('--query-db', action='store_true',
                        help='데이터 DB 조회 (--series, --start, --end 사용)')
    parser.add_argument('--series', type=str, metavar='SERIES_ID',
                        help='DB 조회 시 시리즈 ID')
    parser.add_argument('--force-api', action='store_true',
                        help='DB 무시하고 API 직접 호출')
    parser.add_argument('--db-only', action='store_true',
                        help='DB에서만 조회 (API 호출 안함)')
    parser.add_argument('--db-first', action='store_true',
                        help='DB-First 패턴으로 조회 (기본값, DB→API 순서)')

    parser.add_argument('--api-key', type=str,
                        help='API 인증키')

    args = parser.parse_args()

    # API 클라이언트 초기화
    api = FredAPI(api_key=args.api_key)

    result = None

    if args.sync:
        api.sync_metadata(force=args.force)

    elif args.stats:
        stats = api.get_db_stats()
        if stats:
            print("\n=== FRED 메타DB 통계 ===")
            print(f"시리즈: {stats['series']:,}개")
            print(f"인기 시리즈: {stats['popular_series']:,}개")

            if stats.get('by_frequency'):
                print("\n빈도별 시리즈:")
                for code, cnt in list(stats['by_frequency'].items())[:10]:
                    name = api.FREQUENCIES.get(code.lower(), code)
                    print(f"  - {name}({code}): {cnt:,}개")

            if stats.get('series_updated'):
                print(f"\n마지막 업데이트: {stats['series_updated'][:19]}")
        else:
            print("메타DB가 초기화되지 않았습니다. --sync를 먼저 실행하세요.")

    elif args.db_stats:
        stats = api.get_data_db_stats()
        if stats:
            print(f"\n=== FRED 데이터 DB 통계 ({api.DATA_DB_PATH.name}) ===")
            print(f"총 레코드: {stats['total_records']:,}건")

            if stats.get('by_series'):
                print("\n시리즈별 데이터:")
                print(f"{'시리즈ID':<15} {'제목':<35} {'건수':<10} {'기간':<25}")
                print("-" * 90)
                for s in stats['by_series'][:20]:
                    title = (s['title'] or '')[:33]
                    period = f"{s['min_date']}~{s['max_date']}"
                    print(f"{s['series_id']:<15} {title:<35} {s['count']:<10,} {period:<25}")

            if stats.get('recent_logs'):
                print("\n최근 수집 로그:")
                for log in stats['recent_logs'][:5]:
                    print(f"  - [{log['status']}] {log['series_id']}: {log['count']}건 ({log['collected_at'][:16]})")
        else:
            print("데이터 DB가 없습니다. --save-db 옵션으로 데이터를 저장하세요.")

    elif args.query_db:
        results = api.query_db(
            series_id=args.series,
            start_date=args.start,
            end_date=args.end,
            limit=args.limit
        )
        if results:
            print(f"\n=== DB 조회 결과 ({len(results)}건) ===")
            print(f"{'날짜':<12} {'시리즈ID':<15} {'제목':<30} {'값':<15}")
            print("-" * 75)
            for r in results:
                date = r.get('date') or ''
                sid = (r.get('series_id') or '')[:13]
                title = (r.get('title') or '')[:28]
                val = (r.get('value') or '')[:13]
                print(f"{date:<12} {sid:<15} {title:<30} {val:<15}")
        else:
            print("조회 결과가 없습니다.")

    elif args.search:
        result = print_search_result(api, args)

    elif args.search_local:
        results = api.search_local(args.search_local, limit=args.limit)
        print(f"\n=== '{args.search_local}' 로컬 검색 결과 ({len(results)}건) ===")
        print(f"{'시리즈ID':<15} {'제목':<50} {'빈도':<8} {'인기도':<6}")
        print("-" * 85)
        for s in results:
            sid = (s.get('series_id') or '')[:13]
            title = (s.get('title') or '')[:48]
            freq = s.get('frequency_short') or '-'
            pop = s.get('popularity') or 0
            print(f"{sid:<15} {title:<50} {freq:<8} {pop:<6}")

    elif args.popular:
        print_popular_series(api)

    elif args.info:
        result = print_series_info(api, args)

    elif args.data:
        # DB-First 패턴 처리
        if args.db_only:
            # DB에서만 조회
            db_result = api.get_data_db_only(
                series_id=args.data,
                start_date=args.start,
                end_date=args.end
            )
            # 시리즈 정보
            title = args.data
            if args.data in api.POPULAR_SERIES:
                title = f"{args.data} ({api.POPULAR_SERIES[args.data]})"

            print(f"\n=== [{title}] DB 조회 결과 ({db_result['db_count']}건) ===")
            if args.start or args.end:
                print(f"기간: {args.start or '처음'} ~ {args.end or '현재'}")
            print(f"{'날짜':<12} {'값':<20} {'단위':<15}")
            print("-" * 50)

            for item in db_result['data'][-args.limit:][::-1]:
                date = item.get('date') or ''
                value = item.get('value') or '.'
                if value == '.':
                    value = '(결측)'
                units = (item.get('units') or '')[:13]
                print(f"{date:<12} {value:<20} {units:<15}")
            result = db_result
        elif args.force_api:
            # API 직접 호출 (기존 방식)
            result = print_observations(api, args)
        else:
            # DB-First 패턴 (기본값)
            # 최근 N일 옵션 처리
            start_date = args.start
            end_date = args.end
            if args.recent:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=args.recent)).strftime('%Y-%m-%d')

            db_first_result = api.get_observations_with_db_first(
                series_id=args.data,
                observation_start=start_date,
                observation_end=end_date,
                frequency=args.frequency
            )

            source_str = "DB" if db_first_result['source'] == 'db' else "API"
            total_count = db_first_result['db_count'] or db_first_result['api_count']

            # 시리즈 정보
            title = args.data
            units = ''
            if args.data in api.POPULAR_SERIES:
                title = f"{args.data} ({api.POPULAR_SERIES[args.data]})"
            if db_first_result['data']:
                first_item = db_first_result['data'][0]
                if isinstance(first_item, dict):
                    units = first_item.get('units', '') or ''

            print(f"\n=== [{title}] ({total_count}건, {source_str}) ===")
            if start_date or end_date:
                print(f"기간: {start_date or '처음'} ~ {end_date or '현재'}")
            print(f"{'날짜':<12} {'값':<20} {'단위':<15}")
            print("-" * 50)

            # 최근 데이터부터 출력
            data_list = db_first_result['data']
            if db_first_result['source'] == 'db':
                for item in data_list[-args.limit:][::-1]:
                    date = item.get('date', '')
                    value = item.get('value', '.')
                    if value == '.':
                        value = '(결측)'
                    print(f"{date:<12} {value:<20} {units:<15}")
            else:
                for item in data_list[-args.limit:][::-1]:
                    date = item.get('date', '')
                    value = item.get('value', '.')
                    if value == '.':
                        value = '(결측)'
                    print(f"{date:<12} {value:<20} {units:<15}")

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

    # DB 저장
    if args.save_db and result and args.data:
        api.save_to_db(result, args.data)


if __name__ == '__main__':
    main()
