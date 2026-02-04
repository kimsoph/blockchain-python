# -*- coding: utf-8 -*-
"""
ECOS OpenAPI Client
한국은행 경제통계시스템 ECOS OpenAPI 클라이언트

Author: Claude Code
Version: 2.0.0

Features:
- 통계표 목록 조회
- 통계 항목 조회
- 통계 데이터 조회
- 100대 통계지표 조회
- 통계용어사전 검색
- 메타데이터 SQLite DB 관리
- SQLite DB 저장 (ecos.db) - NEW in v2.0
"""

import os
import sys
import json
import csv
import sqlite3
import argparse
from datetime import datetime
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
    from ecos_meta_db import EcosMetaDB
    HAS_META_DB = True
except ImportError:
    HAS_META_DB = False


class EcosAPI:
    """ECOS OpenAPI 클라이언트 클래스"""

    # API Base URL
    BASE_URL = "http://ecos.bok.or.kr/api"

    # 데이터 DB 경로 (R-DB/ecos.db)
    DATA_DB_PATH = Path(__file__).parents[4] / '3_Resources' / 'R-DB' / 'ecos.db'

    # DB 스키마
    DB_SCHEMA = """
    -- 메인 데이터 테이블
    CREATE TABLE IF NOT EXISTS ecos_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stat_code TEXT NOT NULL,
        stat_name TEXT,
        item_code TEXT,
        item_name TEXT,
        time_period TEXT NOT NULL,
        cycle TEXT,
        data_value TEXT,
        unit_name TEXT,
        raw_data TEXT,
        collected_at TEXT,
        UNIQUE(stat_code, item_code, time_period)
    );

    -- 수집 로그 테이블
    CREATE TABLE IF NOT EXISTS collection_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stat_code TEXT,
        start_period TEXT,
        end_period TEXT,
        cycle TEXT,
        status TEXT,
        record_count INTEGER,
        error_message TEXT,
        collected_at TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_ecos_stat ON ecos_data(stat_code);
    CREATE INDEX IF NOT EXISTS idx_ecos_time ON ecos_data(time_period);
    CREATE INDEX IF NOT EXISTS idx_ecos_item ON ecos_data(item_code);
    CREATE INDEX IF NOT EXISTS idx_log_stat ON collection_log(stat_code);
    """

    # 주기 코드
    CYCLES = {
        'A': '년',
        'S': '반년',
        'Q': '분기',
        'M': '월',
        'SM': '반월',
        'D': '일',
    }

    # 주요 통계표 코드
    STAT_CODES = {
        '722Y001': '한국은행 기준금리',
        '721Y001': '시장금리(일별)',
        '731Y003': '주요국 금리',
        '200Y001': '주요 경제지표',
        '601Y002': '국제수지',
        '901Y014': '주요국 환율',
        '064Y001': '소비자물가지수',
        '104Y016': '고용률',
        '111Y002': '생산지수',
        '501Y001': '수출입',
    }

    def __init__(self, api_key: Optional[str] = None, use_meta_db: bool = True):
        """
        EcosAPI 초기화

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
                self.meta_db = EcosMetaDB()
                self.meta_db.connect()
            except Exception:
                self.meta_db = None

    def _load_api_key(self) -> str:
        """환경변수에서 API 키 로드"""
        env_paths = [
            Path('.claude/.env'),
            Path('.env'),
            Path.home() / '.ecos_api_key',
        ]

        if load_dotenv:
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path)
                    break

        api_key = os.getenv('ECOS_API_KEY')
        if not api_key:
            print("경고: ECOS_API_KEY가 설정되지 않았습니다.")
            print("  .claude/.env 파일에 ECOS_API_KEY=your_key 형식으로 설정하세요.")
        return api_key or ''

    def _make_request(
        self,
        service: str,
        params: List[str] = None,
        start: int = 1,
        end: int = 1000
    ) -> Dict[str, Any]:
        """
        API 요청 실행

        Args:
            service: 서비스명
            params: 추가 파라미터 리스트
            start: 시작 건수
            end: 종료 건수

        Returns:
            API 응답 데이터
        """
        if not self.api_key:
            return {'RESULT': {'CODE': 'ERROR', 'MESSAGE': 'API 키가 설정되지 않았습니다.'}}

        # URL 구성
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
            response = self.session.get(url, timeout=30)
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
            return {'RESULT': {'CODE': 'ERROR', 'MESSAGE': f'요청 실패: {str(e)}'}}
        except json.JSONDecodeError as e:
            return {'RESULT': {'CODE': 'PARSE_ERROR', 'MESSAGE': f'JSON 파싱 실패: {str(e)}'}}

    def _check_response(self, result: Dict, service_name: str) -> bool:
        """응답 상태 확인"""
        if service_name in result:
            return True
        elif 'RESULT' in result:
            error = result['RESULT']
            code = error.get('CODE', 'UNKNOWN')
            msg = error.get('MESSAGE', '알 수 없는 오류')
            print(f"오류 [{code}]: {msg}")
            return False
        return False

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
            tables = self.meta_db.sync_stat_tables(force=force)
            key_stats = self.meta_db.sync_key_statistics(force=force)
            return tables > 0 or key_stats > 0
        else:
            print("메타데이터 DB를 사용할 수 없습니다.")
            return False

    def get_db_stats(self) -> Optional[Dict]:
        """DB 통계 조회"""
        if self.meta_db:
            return self.meta_db.get_stats()
        return None

    def search_tables(self, keyword: str) -> List[Dict]:
        """
        통계표 검색

        Args:
            keyword: 검색 키워드

        Returns:
            검색 결과 리스트
        """
        if self.meta_db:
            return self.meta_db.search_tables(keyword)
        return []

    # ==================== 통계표/항목 API ====================

    def get_stat_table_list(
        self,
        stat_code: Optional[str] = None,
        start: int = 1,
        end: int = 1000
    ) -> Dict[str, Any]:
        """
        통계표 목록 조회

        Args:
            stat_code: 통계표 코드 (선택)
            start: 시작 건수
            end: 종료 건수

        Returns:
            통계표 목록
        """
        params = [stat_code] if stat_code else []
        result = self._make_request('StatisticTableList', params, start, end)
        return result

    def get_stat_item_list(
        self,
        stat_code: str,
        start: int = 1,
        end: int = 10000
    ) -> Dict[str, Any]:
        """
        통계 항목 목록 조회

        Args:
            stat_code: 통계표 코드
            start: 시작 건수
            end: 종료 건수

        Returns:
            항목 목록
        """
        result = self._make_request('StatisticItemList', [stat_code], start, end)
        return result

    # ==================== 통계 데이터 API ====================

    def get_statistic_search(
        self,
        stat_code: str,
        cycle: str,
        start_date: str,
        end_date: str,
        item_code1: Optional[str] = None,
        item_code2: Optional[str] = None,
        item_code3: Optional[str] = None,
        item_code4: Optional[str] = None,
        start: int = 1,
        end: int = 100000
    ) -> Dict[str, Any]:
        """
        통계 데이터 조회

        Args:
            stat_code: 통계표 코드
            cycle: 주기 (A/S/Q/M/SM/D)
            start_date: 검색시작일자 (YYYYMMDD 또는 YYYY)
            end_date: 검색종료일자 (YYYYMMDD 또는 YYYY)
            item_code1~4: 항목코드 (선택)
            start: 시작 건수
            end: 종료 건수

        Returns:
            통계 데이터
        """
        params = [stat_code, cycle, start_date, end_date]

        # 항목코드 추가 (비어있으면 빈 문자열)
        for item_code in [item_code1, item_code2, item_code3, item_code4]:
            params.append(item_code if item_code else '')

        result = self._make_request('StatisticSearch', params, start, end)
        return result

    def get_data(
        self,
        stat_code: str,
        start_date: str,
        end_date: str,
        cycle: Optional[str] = None,
        item_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        통계 데이터 조회 (편의 메서드)

        Args:
            stat_code: 통계표 코드
            start_date: 시작일
            end_date: 종료일
            cycle: 주기 (자동 감지 가능)
            item_code: 항목코드

        Returns:
            통계 데이터
        """
        # 주기 자동 감지
        if not cycle:
            if self.meta_db:
                table_info = self.meta_db.get_table_info(stat_code)
                if table_info:
                    cycle = table_info.get('cycle', 'M')
                else:
                    cycle = 'M'
            else:
                cycle = 'M'

        return self.get_statistic_search(
            stat_code=stat_code,
            cycle=cycle,
            start_date=start_date,
            end_date=end_date,
            item_code1=item_code
        )

    # ==================== 100대 통계지표 ====================

    def get_key_statistic_list(
        self,
        start: int = 1,
        end: int = 500
    ) -> Dict[str, Any]:
        """
        100대 통계지표 조회

        Args:
            start: 시작 건수
            end: 종료 건수

        Returns:
            100대 통계지표
        """
        result = self._make_request('KeyStatisticList', [], start, end)
        return result

    # ==================== 통계용어사전 ====================

    def get_statistic_word(
        self,
        keyword: str,
        start: int = 1,
        end: int = 100
    ) -> Dict[str, Any]:
        """
        통계용어사전 검색

        Args:
            keyword: 검색 키워드
            start: 시작 건수
            end: 종료 건수

        Returns:
            통계용어 검색 결과
        """
        result = self._make_request('StatisticWord', [keyword], start, end)
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
                # API 응답에서 row 추출
                for key in data:
                    if isinstance(data[key], dict) and 'row' in data[key]:
                        rows = data[key]['row']
                        break
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

    # ==================== DB 저장 기능 (v2.0) ====================

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
        stat_code: str,
        cycle: str,
        start_period: str,
        end_period: str
    ) -> int:
        """
        API 응답 데이터를 ecos.db에 저장

        Args:
            data: API 응답 데이터
            stat_code: 통계표 코드
            cycle: 주기
            start_period: 시작 기간
            end_period: 종료 기간

        Returns:
            저장된 레코드 수
        """
        # 데이터 추출
        if 'StatisticSearch' not in data:
            self._log_collection(stat_code, start_period, end_period, cycle,
                               'error', 0, 'StatisticSearch not found in response')
            return 0

        rows = data['StatisticSearch'].get('row', [])
        if not rows:
            self._log_collection(stat_code, start_period, end_period, cycle,
                               'success', 0, 'No data')
            return 0

        conn = self._get_data_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        saved_count = 0

        try:
            for item in rows:
                cursor.execute('''
                    INSERT OR REPLACE INTO ecos_data
                    (stat_code, stat_name, item_code, item_name, time_period,
                     cycle, data_value, unit_name, raw_data, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item.get('STAT_CODE', stat_code),
                    item.get('STAT_NAME', ''),
                    item.get('ITEM_CODE1', ''),
                    item.get('ITEM_NAME1', ''),
                    item.get('TIME', ''),
                    cycle,
                    item.get('DATA_VALUE', ''),
                    item.get('UNIT_NAME', ''),
                    json.dumps(item, ensure_ascii=False),
                    now
                ))
                saved_count += 1

            conn.commit()
            self._log_collection(stat_code, start_period, end_period, cycle,
                               'success', saved_count, None)
            print(f"DB 저장 완료: {saved_count}건 → {self.DATA_DB_PATH.name}")

        except Exception as e:
            conn.rollback()
            self._log_collection(stat_code, start_period, end_period, cycle,
                               'error', 0, str(e))
            print(f"DB 저장 실패: {e}")

        finally:
            conn.close()

        return saved_count

    def _log_collection(
        self,
        stat_code: str,
        start_period: str,
        end_period: str,
        cycle: str,
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
                (stat_code, start_period, end_period, cycle, status,
                 record_count, error_message, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stat_code, start_period, end_period, cycle, status,
                record_count, error_message, datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass  # 로그 실패는 무시

    def get_data_db_stats(self) -> Dict[str, Any]:
        """데이터 DB 통계 조회"""
        if not self.DATA_DB_PATH.exists():
            return {}

        conn = self._get_data_db_connection()
        cursor = conn.cursor()

        stats = {}

        # 총 레코드 수
        cursor.execute('SELECT COUNT(*) FROM ecos_data')
        stats['total_records'] = cursor.fetchone()[0]

        # 통계표별 레코드 수
        cursor.execute('''
            SELECT stat_code, stat_name, COUNT(*) as cnt,
                   MIN(time_period) as min_time, MAX(time_period) as max_time
            FROM ecos_data
            GROUP BY stat_code
            ORDER BY cnt DESC
        ''')
        stats['by_stat'] = [
            {'stat_code': r[0], 'stat_name': r[1], 'count': r[2],
             'min_time': r[3], 'max_time': r[4]}
            for r in cursor.fetchall()
        ]

        # 최근 수집 로그
        cursor.execute('''
            SELECT stat_code, status, record_count, collected_at
            FROM collection_log
            ORDER BY collected_at DESC
            LIMIT 10
        ''')
        stats['recent_logs'] = [
            {'stat_code': r[0], 'status': r[1], 'count': r[2], 'collected_at': r[3]}
            for r in cursor.fetchall()
        ]

        conn.close()
        return stats

    def query_db(
        self,
        stat_code: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        item_code: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        데이터 DB 조회

        Args:
            stat_code: 통계표 코드
            start_period: 시작 기간
            end_period: 종료 기간
            item_code: 항목 코드
            limit: 조회 건수

        Returns:
            조회 결과 리스트
        """
        if not self.DATA_DB_PATH.exists():
            return []

        conn = self._get_data_db_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM ecos_data WHERE 1=1'
        params = []

        if stat_code:
            query += ' AND stat_code = ?'
            params.append(stat_code)
        if start_period:
            query += ' AND time_period >= ?'
            params.append(start_period)
        if end_period:
            query += ' AND time_period <= ?'
            params.append(end_period)
        if item_code:
            query += ' AND item_code = ?'
            params.append(item_code)

        query += f' ORDER BY time_period DESC LIMIT {limit}'

        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return results

    # ==================== DB-First 패턴 (v2.1) ====================

    def _normalize_date(self, date_str: str) -> str:
        """
        입력 날짜를 DB 형식(YYYYMM)으로 변환

        Args:
            date_str: 입력 날짜 (YYYY-MM, YYYYMM, YYYY-MM-DD 등)

        Returns:
            YYYYMM 형식의 날짜
        """
        # 하이픈 제거 후 숫자만 추출
        digits = ''.join(c for c in date_str if c.isdigit())
        return digits[:6]  # YYYYMM

    def get_data_with_db_first(
        self,
        stat_code: str,
        cycle: str,
        start_date: str,
        end_date: str,
        item_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB-First 패턴으로 데이터 조회

        1. DB에서 해당 기간 데이터 확인
        2. DB에 데이터가 있고 기간이 충족되면 반환
        3. 없거나 기간이 부족하면 API 호출 → DB 저장 → 반환

        Args:
            stat_code: 통계표 코드
            cycle: 주기 (A/S/Q/M/SM/D)
            start_date: 시작일 (YYYYMM 또는 YYYY-MM)
            end_date: 종료일 (YYYYMM 또는 YYYY-MM)
            item_code: 항목코드 (선택)

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
        start_period = self._normalize_date(start_date)
        end_period = self._normalize_date(end_date)

        result = {
            'data': [],
            'source': None,
            'db_count': 0,
            'api_count': 0,
            'saved': 0
        }

        # 1. DB에서 기존 데이터 조회
        db_data = self.query_db(
            stat_code=stat_code,
            start_period=start_period,
            end_period=end_period,
            item_code=item_code,
            limit=100000
        )

        if db_data:
            # DB 데이터 기간 확인
            db_periods = [d['time_period'] for d in db_data]
            db_start = min(db_periods)
            db_end = max(db_periods)

            # 요청 기간이 DB 데이터로 충족되면 반환
            if db_start <= start_period and db_end >= end_period:
                # 기간 내 데이터만 필터링
                filtered = [
                    d for d in db_data
                    if start_period <= d['time_period'] <= end_period
                ]
                result['data'] = sorted(filtered, key=lambda x: x['time_period'])
                result['source'] = 'db'
                result['db_count'] = len(filtered)
                print(f"[DB-First] DB에서 조회: {len(filtered)}건 ({start_period}~{end_period})")
                return result

        # 2. DB에 데이터가 없거나 기간이 부족하면 API 호출
        print(f"[DB-First] API 호출: {stat_code} ({start_period}~{end_period})")
        api_result = self.get_statistic_search(
            stat_code=stat_code,
            cycle=cycle,
            start_date=start_period,
            end_date=end_period,
            item_code1=item_code
        )

        if 'StatisticSearch' not in api_result:
            result['source'] = 'api'
            result['api_count'] = 0
            return result

        api_rows = api_result['StatisticSearch'].get('row', [])
        result['api_count'] = len(api_rows)

        # 3. API 데이터 DB에 저장
        if api_rows:
            saved = self.save_to_db(api_result, stat_code, cycle, start_period, end_period)
            result['saved'] = saved
            print(f"[DB-First] API에서 조회 → DB 저장: {saved}건")

        # 4. 결과 반환 (API 원본 형식 그대로)
        result['data'] = api_rows
        result['source'] = 'api'
        return result

    def get_data_db_only(
        self,
        stat_code: str,
        start_date: str,
        end_date: str,
        item_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB에서만 데이터 조회 (API 호출 안함)

        Args:
            stat_code: 통계표 코드
            start_date: 시작일
            end_date: 종료일
            item_code: 항목코드 (선택)

        Returns:
            DB 조회 결과
        """
        start_period = self._normalize_date(start_date)
        end_period = self._normalize_date(end_date)

        db_data = self.query_db(
            stat_code=stat_code,
            start_period=start_period,
            end_period=end_period,
            item_code=item_code,
            limit=100000
        )

        return {
            'data': sorted(db_data, key=lambda x: x['time_period']),
            'source': 'db',
            'db_count': len(db_data),
            'api_count': 0,
            'saved': 0
        }


# ==================== CLI 함수 ====================

def print_stat_tables(api: EcosAPI, args):
    """통계표 목록 출력"""
    result = api.get_stat_table_list(stat_code=args.stat_code)

    if not api._check_response(result, 'StatisticTableList'):
        return result

    items = result['StatisticTableList'].get('row', [])
    print(f"\n=== 통계표 목록 ({len(items)}건) ===")
    print(f"{'코드':<12} {'통계명':<40} {'주기':<4} {'출처':<20}")
    print("-" * 80)

    for item in items[:args.limit]:
        code = item.get('STAT_CODE') or ''
        name = (item.get('STAT_NAME') or '')[:38]
        cycle = item.get('CYCLE') or '-'
        org = (item.get('ORG_NAME') or '-')[:18]
        print(f"{code:<12} {name:<40} {cycle:<4} {org:<20}")

    return result


def print_stat_items(api: EcosAPI, args):
    """통계 항목 출력"""
    result = api.get_stat_item_list(args.items)

    if not api._check_response(result, 'StatisticItemList'):
        return result

    items = result['StatisticItemList'].get('row', [])
    print(f"\n=== [{args.items}] 항목 목록 ({len(items)}건) ===")
    print(f"{'항목코드':<15} {'항목명':<40} {'단위':<10} {'자료수':<8}")
    print("-" * 75)

    for item in items[:args.limit]:
        code = (item.get('ITEM_CODE') or '')[:13]
        name = (item.get('ITEM_NAME') or '')[:38]
        unit = (item.get('UNIT_NAME') or '-')[:8]
        cnt = item.get('DATA_CNT') or '-'
        print(f"{code:<15} {name:<40} {unit:<10} {cnt:<8}")

    return result


def print_statistic_data(api: EcosAPI, args):
    """통계 데이터 출력"""
    result = api.get_statistic_search(
        stat_code=args.stat_code,
        cycle=args.cycle,
        start_date=args.start,
        end_date=args.end,
        item_code1=args.item_code
    )

    if not api._check_response(result, 'StatisticSearch'):
        return result

    items = result['StatisticSearch'].get('row', [])

    # 통계표명 가져오기
    stat_name = items[0].get('STAT_NAME', args.stat_code) if items else args.stat_code

    print(f"\n=== [{args.stat_code}] {stat_name} ({len(items)}건) ===")
    print(f"기간: {args.start} ~ {args.end} (주기: {api.CYCLES.get(args.cycle, args.cycle)})")
    print(f"{'시점':<12} {'항목명':<35} {'값':<20} {'단위':<10}")
    print("-" * 80)

    for item in items[:args.limit]:
        time = item.get('TIME') or ''
        item_name = (item.get('ITEM_NAME1') or '')[:33]
        value = item.get('DATA_VALUE') or '-'
        unit = (item.get('UNIT_NAME') or '-')[:8]
        print(f"{time:<12} {item_name:<35} {value:<20} {unit:<10}")

    return result


def print_key_statistics(api: EcosAPI, args):
    """100대 통계지표 출력"""
    result = api.get_key_statistic_list()

    if not api._check_response(result, 'KeyStatisticList'):
        return result

    items = result['KeyStatisticList'].get('row', [])
    print(f"\n=== 100대 통계지표 ({len(items)}건) ===")
    print(f"{'분류':<15} {'지표명':<35} {'값':<15} {'단위':<10} {'시점':<10}")
    print("-" * 90)

    for item in items[:args.limit]:
        cls = (item.get('CLASS_NAME') or '')[:13]
        # KEYSTAT_NAME이 실제 지표명 (ITEM_NAME은 API에 없음)
        name = (item.get('KEYSTAT_NAME') or item.get('ITEM_NAME') or '')[:33]
        value = (item.get('DATA_VALUE') or '-')[:13]
        unit = (item.get('UNIT_NAME') or '-')[:8]
        # CYCLE이 실제 시점 (TIME은 API에 없음)
        time = item.get('CYCLE') or item.get('TIME') or '-'
        print(f"{cls:<15} {name:<35} {value:<15} {unit:<10} {time:<10}")

    return result


def print_search_result(api: EcosAPI, args):
    """검색 결과 출력"""
    if api.meta_db:
        results = api.search_tables(args.search)
        print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
        print(f"{'통계코드':<12} {'통계명':<40} {'주기':<4} {'출처':<20}")
        print("-" * 80)
        for t in results[:args.limit]:
            code = t['stat_code']
            name = t['stat_name'][:38]
            cycle = t['cycle'] or '-'
            org = (t['org_name'] or '-')[:18]
            print(f"{code:<12} {name:<40} {cycle:<4} {org:<20}")
    else:
        print("메타DB가 초기화되지 않았습니다. --sync를 먼저 실행하세요.")


def print_word_search(api: EcosAPI, args):
    """통계용어 검색 결과 출력"""
    result = api.get_statistic_word(args.word)

    if not api._check_response(result, 'StatisticWord'):
        return result

    items = result['StatisticWord'].get('row', [])
    print(f"\n=== '{args.word}' 용어 검색 결과 ({len(items)}건) ===")

    for item in items[:args.limit]:
        word = item.get('WORD', '')
        content = item.get('CONTENT', '')
        print(f"\n[{word}]")
        print(f"  {content[:200]}...")

    return result


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='ECOS 한국은행 경제통계시스템 OpenAPI 클라이언트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 메타데이터 동기화
  python ecos_api.py --sync

  # DB 통계
  python ecos_api.py --stats

  # 통계표 검색
  python ecos_api.py --search "금리"

  # 통계표 목록 조회
  python ecos_api.py --tables

  # 통계 항목 조회
  python ecos_api.py --items 722Y001

  # 통계 데이터 조회
  python ecos_api.py --stat-code 722Y001 --cycle M --start 202301 --end 202312

  # 100대 통계지표
  python ecos_api.py --key-stats

  # 통계용어 검색
  python ecos_api.py --word "기준금리"

  # 결과 저장
  python ecos_api.py --stat-code 722Y001 --cycle M --start 202301 --end 202312 --output result.csv
        """
    )

    # 메타데이터 관리
    parser.add_argument('--sync', action='store_true',
                        help='메타데이터 DB 동기화')
    parser.add_argument('--force', action='store_true',
                        help='강제 동기화')
    parser.add_argument('--stats', action='store_true',
                        help='DB 통계 출력')

    # 검색
    parser.add_argument('--search', type=str, metavar='KEYWORD',
                        help='통계표 검색')
    parser.add_argument('--tables', action='store_true',
                        help='통계표 목록 조회')
    parser.add_argument('--items', type=str, metavar='CODE',
                        help='통계 항목 목록 조회')

    # 데이터 조회
    parser.add_argument('--stat-code', type=str, metavar='CODE',
                        help='통계표 코드')
    parser.add_argument('--cycle', type=str, default='M',
                        choices=['A', 'S', 'Q', 'M', 'SM', 'D'],
                        help='주기 (A=년, S=반년, Q=분기, M=월, SM=반월, D=일)')
    parser.add_argument('--start', type=str,
                        help='검색시작일자 (YYYYMMDD 또는 YYYY)')
    parser.add_argument('--end', type=str,
                        help='검색종료일자 (YYYYMMDD 또는 YYYY)')
    parser.add_argument('--item-code', type=str,
                        help='항목코드')

    # 100대 통계지표
    parser.add_argument('--key-stats', action='store_true',
                        help='100대 통계지표 조회')

    # 통계용어
    parser.add_argument('--word', type=str, metavar='KEYWORD',
                        help='통계용어 검색')

    # 출력 옵션
    parser.add_argument('--limit', type=int, default=100,
                        help='조회 건수 (기본: 100)')
    parser.add_argument('--output', '-o', type=str,
                        help='결과 저장 파일 (json/csv)')
    parser.add_argument('--save-db', action='store_true',
                        help='결과를 DB에 저장 (R-DB/outputs/ecos.db)')
    parser.add_argument('--db-stats', action='store_true',
                        help='데이터 DB 통계 출력')
    parser.add_argument('--query-db', action='store_true',
                        help='DB에서 데이터 조회 (--stat-code, --start, --end 사용)')
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
    api = EcosAPI(api_key=args.api_key)

    result = None

    if args.sync:
        api.sync_metadata(force=args.force)

    elif args.stats:
        stats = api.get_db_stats()
        if stats:
            print("\n=== ECOS 메타DB 통계 ===")
            print(f"통계표: {stats['tables']:,}개")
            print(f"통계항목: {stats['items']:,}개")
            print(f"100대 지표: {stats['key_stats']:,}개")

            if stats.get('by_cycle'):
                print("\n주기별 통계표:")
                for code, cnt in sorted(stats['by_cycle'].items()):
                    name = api.CYCLES.get(code, code)
                    print(f"  - {name}({code}): {cnt:,}개")

            if stats.get('tables_updated'):
                print(f"\n마지막 업데이트: {stats['tables_updated'][:19]}")
        else:
            print("DB가 초기화되지 않았습니다. --sync를 먼저 실행하세요.")

    elif args.db_stats:
        stats = api.get_data_db_stats()
        if stats:
            print(f"\n=== ECOS 데이터 DB 통계 ({api.DATA_DB_PATH.name}) ===")
            print(f"총 레코드: {stats['total_records']:,}건")

            if stats.get('by_stat'):
                print("\n통계표별 데이터:")
                print(f"{'코드':<12} {'통계명':<30} {'건수':<10} {'기간':<20}")
                print("-" * 75)
                for s in stats['by_stat'][:20]:
                    name = (s['stat_name'] or '')[:28]
                    period = f"{s['min_time']}~{s['max_time']}"
                    print(f"{s['stat_code']:<12} {name:<30} {s['count']:<10,} {period:<20}")

            if stats.get('recent_logs'):
                print("\n최근 수집 로그:")
                for log in stats['recent_logs'][:5]:
                    print(f"  - [{log['status']}] {log['stat_code']}: {log['count']}건 ({log['collected_at'][:16]})")
        else:
            print("데이터 DB가 없습니다. --save-db 옵션으로 데이터를 저장하세요.")

    elif args.query_db:
        results = api.query_db(
            stat_code=args.stat_code,
            start_period=args.start,
            end_period=args.end,
            item_code=args.item_code,
            limit=args.limit
        )
        if results:
            print(f"\n=== DB 조회 결과 ({len(results)}건) ===")
            print(f"{'시점':<12} {'통계코드':<12} {'항목명':<30} {'값':<15} {'단위':<10}")
            print("-" * 85)
            for r in results:
                time = r.get('time_period', '')
                code = r.get('stat_code', '')
                name = (r.get('item_name', '') or '')[:28]
                val = (r.get('data_value', '') or '')[:13]
                unit = (r.get('unit_name', '') or '')[:8]
                print(f"{time:<12} {code:<12} {name:<30} {val:<15} {unit:<10}")
        else:
            print("조회 결과가 없습니다.")

    elif args.search:
        print_search_result(api, args)

    elif args.tables:
        result = print_stat_tables(api, args)

    elif args.items:
        result = print_stat_items(api, args)

    elif args.stat_code and args.start and args.end:
        # DB-First 패턴 처리
        if args.db_only:
            # DB에서만 조회
            db_result = api.get_data_db_only(
                stat_code=args.stat_code,
                start_date=args.start,
                end_date=args.end,
                item_code=args.item_code
            )
            print(f"\n=== [{args.stat_code}] DB 조회 결과 ({db_result['db_count']}건) ===")
            print(f"기간: {args.start} ~ {args.end}")
            print(f"{'시점':<12} {'항목명':<35} {'값':<20} {'단위':<10}")
            print("-" * 80)
            for item in db_result['data'][:args.limit]:
                time = item.get('time_period', '')
                item_name = (item.get('item_name', '') or '')[:33]
                value = item.get('data_value', '-')
                unit = (item.get('unit_name', '') or '-')[:8]
                print(f"{time:<12} {item_name:<35} {value:<20} {unit:<10}")
            result = db_result
        elif args.force_api:
            # API 직접 호출 (기존 방식)
            result = print_statistic_data(api, args)
        else:
            # DB-First 패턴 (기본값)
            db_first_result = api.get_data_with_db_first(
                stat_code=args.stat_code,
                cycle=args.cycle,
                start_date=args.start,
                end_date=args.end,
                item_code=args.item_code
            )

            source_str = "DB" if db_first_result['source'] == 'db' else "API"
            total_count = db_first_result['db_count'] or db_first_result['api_count']

            # 통계표명 가져오기
            stat_name = args.stat_code
            if db_first_result['data']:
                first_item = db_first_result['data'][0]
                if isinstance(first_item, dict):
                    stat_name = first_item.get('STAT_NAME') or first_item.get('stat_name') or args.stat_code

            print(f"\n=== [{args.stat_code}] {stat_name} ({total_count}건, {source_str}) ===")
            print(f"기간: {args.start} ~ {args.end} (주기: {api.CYCLES.get(args.cycle, args.cycle)})")
            print(f"{'시점':<12} {'항목명':<35} {'값':<20} {'단위':<10}")
            print("-" * 80)

            for item in db_first_result['data'][:args.limit]:
                if db_first_result['source'] == 'db':
                    time = item.get('time_period', '')
                    item_name = (item.get('item_name', '') or '')[:33]
                    value = item.get('data_value') or '-'
                    unit = (item.get('unit_name', '') or '-')[:8]
                else:
                    time = item.get('TIME', '')
                    item_name = (item.get('ITEM_NAME1', '') or '')[:33]
                    value = item.get('DATA_VALUE') or '-'
                    unit = (item.get('UNIT_NAME', '') or '-')[:8]
                print(f"{time:<12} {item_name:<35} {value:<20} {unit:<10}")

            result = db_first_result

    elif args.key_stats:
        result = print_key_statistics(api, args)

    elif args.word:
        result = print_word_search(api, args)

    else:
        parser.print_help()
        return

    # 결과 저장
    if args.output and result:
        if args.output.endswith('.csv'):
            api.export_to_csv(result, args.output)
        else:
            api.export_to_json(result, args.output)

    # DB 저장 (--save-db 옵션)
    if args.save_db and result and args.stat_code and args.start and args.end:
        api.save_to_db(result, args.stat_code, args.cycle, args.start, args.end)


if __name__ == '__main__':
    main()
