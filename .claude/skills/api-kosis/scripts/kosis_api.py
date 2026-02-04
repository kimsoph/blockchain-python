# -*- coding: utf-8 -*-
"""
KOSIS OpenAPI Client
국가통계포털 KOSIS OpenAPI 클라이언트

Author: Claude Code
Version: 2.1.0

Features:
- 통합검색: 통계표 검색
- 통계목록: 계층구조 조회
- 통계자료: 실제 데이터 조회
- 통계설명: 메타정보 조회
- 주요지표: 주요 통계지표 조회
- 메타데이터 SQLite DB 관리
- SQLite DB 저장 (kosis.db) - NEW in v2.0
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
    from kosis_meta_db import KosisMetaDB
    HAS_META_DB = True
except ImportError:
    HAS_META_DB = False


class KosisAPI:
    """KOSIS OpenAPI 클라이언트 클래스"""

    # API Base URL
    BASE_URL = "https://kosis.kr/openapi"

    # 데이터 DB 경로 (R-DB/kosis.db)
    DATA_DB_PATH = Path(__file__).parents[4] / '3_Resources' / 'R-DB' / 'kosis.db'

    # DB 스키마
    DB_SCHEMA = """
    -- 메인 데이터 테이블
    CREATE TABLE IF NOT EXISTS kosis_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id TEXT,
        tbl_id TEXT NOT NULL,
        tbl_name TEXT,
        itm_id TEXT,
        itm_name TEXT,
        cls_id TEXT,
        cls_name TEXT,
        time_period TEXT NOT NULL,
        prd_se TEXT,
        data_value TEXT,
        unit_name TEXT,
        raw_data TEXT,
        collected_at TEXT,
        UNIQUE(tbl_id, itm_id, cls_id, time_period)
    );

    -- 수집 로그 테이블
    CREATE TABLE IF NOT EXISTS collection_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id TEXT,
        tbl_id TEXT,
        start_period TEXT,
        end_period TEXT,
        prd_se TEXT,
        status TEXT,
        record_count INTEGER,
        error_message TEXT,
        collected_at TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_kosis_tbl ON kosis_data(tbl_id);
    CREATE INDEX IF NOT EXISTS idx_kosis_time ON kosis_data(time_period);
    CREATE INDEX IF NOT EXISTS idx_kosis_org ON kosis_data(org_id);
    CREATE INDEX IF NOT EXISTS idx_log_tbl ON collection_log(tbl_id);
    """

    # 수록주기 코드
    PERIOD_CODES = {
        'Y': '년',
        'H': '반년',
        'Q': '분기',
        'M': '월',
        'S': '반월',
        'D': '일',
    }

    # 서비스뷰 코드
    VIEW_CODES = {
        'MT_ZTITLE': '국내통계 주제별',
        'MT_OTITLE': '국내통계 기관별',
        'MT_GTITLE01': 'e-지방지표 시도별',
        'MT_GTITLE02': 'e-지방지표 시군구별',
        'MT_ATITLE01': '북한통계 주제별',
        'MT_BTITLE': '국제통계',
    }

    def __init__(self, api_key: Optional[str] = None, use_meta_db: bool = True):
        """
        KosisAPI 초기화

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
                self.meta_db = KosisMetaDB()
                self.meta_db.connect()
            except Exception:
                self.meta_db = None

    def _load_api_key(self) -> str:
        """환경변수에서 API 키 로드"""
        env_paths = [
            Path('.claude/.env'),
            Path('.env'),
            Path.home() / '.kosis_api_key',
        ]

        if load_dotenv:
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path)
                    break

        api_key = os.getenv('KOSIS_API_KEY')
        if not api_key:
            print("경고: KOSIS_API_KEY가 설정되지 않았습니다.")
            print("  .claude/.env 파일에 KOSIS_API_KEY=your_key 형식으로 설정하세요.")
        return api_key or ''

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        method: str = 'GET'
    ) -> Dict[str, Any]:
        """
        API 요청 실행

        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터
            method: HTTP 메서드

        Returns:
            API 응답 데이터
        """
        if not self.api_key:
            return {'err': 'API 키가 설정되지 않았습니다.'}

        if params is None:
            params = {}

        # 기본 파라미터 추가
        params['apiKey'] = self.api_key
        params['format'] = 'json'
        params['jsonVD'] = 'Y'

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            else:
                response = self.session.post(url, data=params, timeout=30)

            response.encoding = 'utf-8'

            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {'raw': response.text}
            else:
                return {
                    'err': f'HTTP {response.status_code}',
                    'message': response.text[:200]
                }

        except requests.exceptions.Timeout:
            return {'err': 'TIMEOUT', 'message': '요청 시간 초과'}
        except requests.exceptions.RequestException as e:
            return {'err': 'REQUEST_ERROR', 'message': str(e)}
        except Exception as e:
            return {'err': 'ERROR', 'message': str(e)}

    # API 오류 코드
    ERROR_CODES = {
        '00': '정상',
        '01': '잘못된 인증키',
        '02': '인증키 사용 신청 미완료',
        '10': '잘못된 요청 파라미터',
        '11': '조회 결과 없음',
        '12': '인증키 기간 만료',
        '20': '서비스 이용 횟수 초과',
        '21': '잘못된 요청 파라미터 호출',
        '30': '데이터 미존재',
        '31': '필수 파라미터 누락',
        '99': '서버 오류',
    }

    def _check_response(self, result, key: str = None) -> bool:
        """응답 상태 확인"""
        # 리스트 응답은 성공
        if isinstance(result, list):
            return True
        # 딕셔너리 응답에서 오류 확인
        if isinstance(result, dict) and 'err' in result:
            err_code = result.get('err', '')
            err_msg = self.ERROR_CODES.get(err_code, result.get('errMsg', '알 수 없는 오류'))
            print(f"오류 [{err_code}]: {err_msg}")
            return False
        if key and key not in result:
            return False
        return True

    # ==================== 통합검색 API ====================

    def search(
        self,
        keyword: str,
        sort: str = 'RANK',
        start_count: int = 1,
        result_count: int = 100
    ) -> Dict[str, Any]:
        """
        KOSIS 통합검색

        Args:
            keyword: 검색어
            sort: 정렬 방식 (RANK: 정확도, DATE: 최신순)
            start_count: 시작 페이지
            result_count: 결과 개수

        Returns:
            검색 결과
        """
        params = {
            'searchNm': keyword,
            'sort': sort,
            'startCount': str(start_count),
            'resultCount': str(result_count),
        }

        result = self._make_request('statisticsSearch.do', params)
        return result

    # ==================== 통계목록 API ====================

    def get_stat_list(
        self,
        vw_cd: str = 'MT_ZTITLE',
        parent_id: str = 'A'
    ) -> Dict[str, Any]:
        """
        통계목록 조회

        Args:
            vw_cd: 서비스뷰 코드
            parent_id: 상위 목록 ID

        Returns:
            통계목록
        """
        params = {
            'vwCd': vw_cd,
            'parentListId': parent_id,
        }

        result = self._make_request('statisticsList.do', params)
        return result

    # ==================== 통계자료 API ====================

    def get_stat_data(
        self,
        org_id: str,
        tbl_id: str,
        prd_se: str = 'Y',
        start_prd_de: Optional[str] = None,
        end_prd_de: Optional[str] = None,
        new_est_prd_cnt: Optional[int] = None,
        itm_id: str = 'ALL',
        obj_l1: str = 'ALL',
        obj_l2: str = '',
        obj_l3: str = '',
        obj_l4: str = '',
        obj_l5: str = '',
        obj_l6: str = '',
        obj_l7: str = '',
        obj_l8: str = ''
    ) -> Dict[str, Any]:
        """
        통계자료 조회

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            prd_se: 수록주기 (Y/H/Q/M/S/D)
            start_prd_de: 시작 시점 (예: 2023, 202301)
            end_prd_de: 종료 시점
            new_est_prd_cnt: 최근 N개 시점
            itm_id: 항목 ID (ALL 가능)
            obj_l1~l8: 분류1~8 (ALL 가능)

        Returns:
            통계자료
        """
        params = {
            'method': 'getList',
            'orgId': org_id,
            'tblId': tbl_id,
            'prdSe': prd_se,
            'itmId': itm_id,
            'objL1': obj_l1,
        }

        # 분류 파라미터 추가 (빈 문자열도 유효한 값으로 전달)
        if obj_l2 is not None:
            params['objL2'] = obj_l2
        if obj_l3 is not None:
            params['objL3'] = obj_l3
        if obj_l4 is not None:
            params['objL4'] = obj_l4
        if obj_l5 is not None:
            params['objL5'] = obj_l5
        if obj_l6 is not None:
            params['objL6'] = obj_l6
        if obj_l7 is not None:
            params['objL7'] = obj_l7
        if obj_l8 is not None:
            params['objL8'] = obj_l8

        # 기간 설정
        if new_est_prd_cnt:
            params['newEstPrdCnt'] = str(new_est_prd_cnt)
        else:
            if start_prd_de:
                params['startPrdDe'] = start_prd_de
            if end_prd_de:
                params['endPrdDe'] = end_prd_de

        result = self._make_request('Param/statisticsParameterData.do', params)
        return result

    # ==================== 통계설명 API ====================

    def get_stat_meta(
        self,
        org_id: str,
        tbl_id: str,
        meta_itm: str = 'ALL'
    ) -> Dict[str, Any]:
        """
        통계설명 조회

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            meta_itm: 메타항목 (ALL 또는 특정 항목)

        Returns:
            통계설명
        """
        params = {
            'method': 'getMeta',
            'orgId': org_id,
            'tblId': tbl_id,
            'metaItm': meta_itm,
        }

        result = self._make_request('statisticsData.do', params)
        return result

    # ==================== 분류/항목 조회 API ====================

    def get_stat_item_list(self, org_id: str, tbl_id: str, prd_se: str = 'Y') -> Dict[str, Any]:
        """
        통계표의 분류/항목 목록 조회
        실제 데이터를 샘플 조회하여 분류 구조 파악

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            prd_se: 수록주기 (기본: Y)

        Returns:
            분류/항목 목록 응답 (리스트 형태)
        """
        # 최근 1개 시점 데이터를 조회하여 분류 구조 파악
        # ALL을 사용하면 너무 많을 수 있으므로 제한적으로 조회
        result = self.get_stat_data(
            org_id=org_id,
            tbl_id=tbl_id,
            prd_se=prd_se,
            new_est_prd_cnt=1,
            itm_id='ALL',
            obj_l1='ALL'
        )

        # 40,000셀 초과 오류 시 objL1을 제한해서 재시도
        if isinstance(result, dict) and result.get('err') == '31':
            result = self.get_stat_data(
                org_id=org_id,
                tbl_id=tbl_id,
                prd_se=prd_se,
                new_est_prd_cnt=1,
                itm_id='ALL',
                obj_l1='00'  # 전국만 조회
            )

        return result

    def parse_classifications(self, item_list_result: Any) -> Dict[str, Any]:
        """
        API 응답에서 분류 구조 파싱

        Args:
            item_list_result: get_stat_item_list() 응답 (실제 데이터 리스트)

        Returns:
            {
                'obj_count': 분류 단계 수,
                'itm_count': 항목 수,
                'classifications': [
                    {'level': 1, 'id': 'OBJ_L1', 'name': '지역',
                     'values': [{'code': '00', 'name': '전국'}, ...]},
                    ...
                ],
                'items': [
                    {'id': 'T1', 'name': '총인구', 'unit': '명'},
                    ...
                ]
            }
        """
        result = {
            'obj_count': 0,
            'itm_count': 0,
            'classifications': [],
            'items': [],
            'raw_values': []
        }

        # 응답이 리스트가 아니면 오류
        if not isinstance(item_list_result, list):
            return result

        items = item_list_result

        # 분류 단계별로 그룹화
        obj_levels = {}  # level -> {'id', 'name', 'values': []}
        item_dict = {}   # itm_id -> item info (중복 제거용)

        for item in items:
            # 항목 정보 수집 (ITM_ID, ITM_NM, UNIT_NM)
            itm_id = item.get('ITM_ID', '')
            if itm_id and itm_id not in item_dict:
                item_dict[itm_id] = {
                    'id': itm_id,
                    'name': item.get('ITM_NM', ''),
                    'unit': item.get('UNIT_NM', ''),
                    'parent_id': ''
                }

            # 분류 정보 수집 (C1, C2, ... 또는 C1_OBJ_NM 등)
            for i in range(1, 9):  # C1 ~ C8
                c_key = f'C{i}'
                c_nm_key = f'C{i}_NM'
                c_obj_nm_key = f'C{i}_OBJ_NM'

                c_val = item.get(c_key, '')
                c_nm = item.get(c_nm_key, '')
                c_obj_nm = item.get(c_obj_nm_key, '')

                if c_val and c_val not in ['', 'ALL']:
                    if i not in obj_levels:
                        obj_levels[i] = {
                            'level': i,
                            'id': f'OBJ_L{i}',
                            'name': c_obj_nm or f'분류{i}',
                            'values': []
                        }
                    elif c_obj_nm and obj_levels[i]['name'] == f'분류{i}':
                        obj_levels[i]['name'] = c_obj_nm

                    # 중복 체크 후 추가
                    existing_codes = [v['code'] for v in obj_levels[i]['values']]
                    if c_val not in existing_codes:
                        obj_levels[i]['values'].append({
                            'code': c_val,
                            'name': c_nm
                        })

        # raw_values 구성 (DB 저장용)
        for level, cls_info in obj_levels.items():
            for val in cls_info['values']:
                result['raw_values'].append({
                    'cls_level': level,
                    'cls_id': cls_info['id'],
                    'cls_nm': cls_info['name'],
                    'value_code': val['code'],
                    'value_name': val['name'],
                    'parent_code': '',
                    'unit_nm': ''
                })

        # 항목도 raw_values에 추가 (level=0)
        for itm_id, itm_info in item_dict.items():
            result['raw_values'].append({
                'cls_level': 0,
                'cls_id': 'ITM',
                'cls_nm': '항목',
                'value_code': itm_info['id'],
                'value_name': itm_info['name'],
                'parent_code': '',
                'unit_nm': itm_info.get('unit', '')
            })

        # 결과 구성
        result['obj_count'] = len(obj_levels)
        result['itm_count'] = len(item_dict)
        result['classifications'] = sorted(obj_levels.values(), key=lambda x: x['level'])
        result['items'] = list(item_dict.values())

        return result

    def sync_classifications(
        self,
        org_id: str,
        tbl_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        통계표의 분류/항목 정보 동기화 (API 호출 → DB 저장)

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            force: 강제 동기화 여부

        Returns:
            동기화 결과 정보
        """
        result = {
            'success': False,
            'org_id': org_id,
            'tbl_id': tbl_id,
            'obj_count': 0,
            'itm_count': 0,
            'saved': 0,
            'message': ''
        }

        # DB에서 기존 정보 확인
        if not force and self.meta_db:
            existing = self.meta_db.get_classification_values(org_id, tbl_id)
            if existing:
                result['success'] = True
                result['obj_count'] = existing.get('obj_count', 0)
                result['itm_count'] = existing.get('itm_count', 0)
                result['message'] = 'DB에서 기존 정보 사용 (force=True로 갱신)'
                return result

        # API 호출
        api_result = self.get_stat_item_list(org_id, tbl_id)

        if not isinstance(api_result, list):
            err_msg = ''
            if isinstance(api_result, dict):
                err_msg = api_result.get('err', api_result.get('errMsg', '알 수 없는 오류'))
            result['message'] = f'API 오류: {err_msg}'
            return result

        # 분류 구조 파싱
        parsed = self.parse_classifications(api_result)

        result['obj_count'] = parsed['obj_count']
        result['itm_count'] = parsed['itm_count']

        # DB에 저장
        if self.meta_db and parsed['raw_values']:
            saved = self.meta_db.save_classification_values(
                org_id, tbl_id, parsed, parsed['raw_values']
            )
            result['saved'] = saved
            result['success'] = True
            result['message'] = f'{saved}건 저장 완료'
        else:
            result['success'] = True
            result['message'] = '파싱 완료 (DB 저장 안함)'

        # 상세 정보 포함
        result['classifications'] = parsed['classifications']
        result['items'] = parsed['items']

        return result

    # ==================== 스마트 조회 기능 ====================

    def get_table_classification_info(
        self,
        org_id: str,
        tbl_id: str,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        통계표의 분류 구조 정보 조회 (DB 우선, 없으면 API 호출 후 저장)

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            force: 강제 API 호출 여부

        Returns:
            {
                'obj_count': 분류 단계 수,
                'itm_count': 항목 수,
                'classifications': [...],
                'items': [...],
                'suggested_params': {'objL1': '00', 'objL2': 'ALL', 'itmId': 'ALL'}
            }
        """
        # DB에서 먼저 조회
        if not force and self.meta_db:
            existing = self.meta_db.get_classification_values(org_id, tbl_id)
            if existing:
                # suggested_params 생성
                existing['suggested_params'] = self._build_suggested_params(existing)
                return existing

        # API 호출 및 동기화
        sync_result = self.sync_classifications(org_id, tbl_id, force=True)

        if sync_result['success']:
            result = {
                'obj_count': sync_result.get('obj_count', 0),
                'itm_count': sync_result.get('itm_count', 0),
                'classifications': sync_result.get('classifications', []),
                'items': sync_result.get('items', [])
            }
            result['suggested_params'] = self._build_suggested_params(result)
            return result

        return None

    def _build_suggested_params(self, classification_info: Dict) -> Dict[str, str]:
        """
        분류 정보를 바탕으로 추천 파라미터 생성

        Args:
            classification_info: 분류 구조 정보

        Returns:
            추천 파라미터 딕셔너리
        """
        params = {'itmId': 'ALL'}

        classifications = classification_info.get('classifications', [])

        for cls in classifications:
            level = cls.get('level', 1)
            values = cls.get('values', [])

            if values:
                # 첫 번째 값을 기본값으로 (보통 '전체' 또는 '전국')
                first_value = values[0].get('code', 'ALL')
                params[f'objL{level}'] = first_value
            else:
                # 분류 정보가 있지만 값이 없으면 첫 번째 분류는 기본값 사용
                params[f'objL{level}'] = '00' if level == 1 else ''

        # 분류 정보가 전혀 없으면 objL1에 기본값 설정
        if not classifications:
            params['objL1'] = 'ALL'

        return params

    def _estimate_cell_count(
        self,
        classification_info: Dict,
        params: Dict
    ) -> int:
        """
        조회 결과 예상 셀 수 계산

        Args:
            classification_info: 분류 구조 정보
            params: 조회 파라미터

        Returns:
            예상 셀 수
        """
        count = 1

        classifications = classification_info.get('classifications', [])

        for cls in classifications:
            level = cls.get('level', 1)
            param_key = f'objL{level}'
            param_value = params.get(param_key, 'ALL')

            if param_value == 'ALL':
                # 모든 값 조회 시 해당 분류의 값 개수 곱함
                values = cls.get('values', [])
                if values:
                    count *= len(values)
                else:
                    count *= 10  # 기본 추정치
            # 특정 값 지정 시 1개

        # 항목 수
        itm_count = classification_info.get('itm_count', 1)
        if params.get('itmId', 'ALL') == 'ALL':
            count *= max(itm_count, 1)

        return count

    def get_stat_data_smart(
        self,
        org_id: str,
        tbl_id: str,
        prd_se: str,
        start_prd_de: str,
        end_prd_de: str,
        **classification_params
    ) -> Dict[str, Any]:
        """
        분류 구조를 자동 확인하여 데이터 조회 (스마트 모드)

        1. 분류 구조 확인 (DB/API)
        2. 누락된 분류 파라미터에 기본값 설정
        3. 대용량 예상 시 경고 또는 분할
        4. 조회 실행

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            prd_se: 수록주기 (Y/H/Q/M/S/D)
            start_prd_de: 시작 시점
            end_prd_de: 종료 시점
            **classification_params: 분류 파라미터 (itm_id, obj_l1~l8)

        Returns:
            {
                'data': 조회 데이터,
                'classification_info': 분류 구조 정보,
                'used_params': 실제 사용된 파라미터,
                'estimated_cells': 예상 셀 수,
                'warnings': 경고 메시지 리스트
            }
        """
        result = {
            'data': [],
            'classification_info': None,
            'used_params': {},
            'estimated_cells': 0,
            'warnings': [],
            'success': False
        }

        # 1. 분류 구조 확인
        print(f"[스마트 모드] 분류 구조 확인 중: {tbl_id}")
        cls_info = self.get_table_classification_info(org_id, tbl_id)

        if not cls_info:
            result['warnings'].append("분류 구조를 확인할 수 없습니다. 기본 파라미터로 조회합니다.")
            cls_info = {'obj_count': 1, 'classifications': [], 'items': []}

        result['classification_info'] = cls_info

        # 2. 파라미터 구성 (스마트 모드에서는 ALL도 빈값으로 취급)
        def get_param(key, default=''):
            val = classification_params.get(key, default)
            # 스마트 모드에서 'ALL'은 자동 결정 대상
            return '' if val == 'ALL' else val

        params = {
            'itm_id': classification_params.get('itm_id', 'ALL'),  # 항목은 ALL 유지
            'obj_l1': get_param('obj_l1'),
            'obj_l2': get_param('obj_l2'),
            'obj_l3': get_param('obj_l3'),
            'obj_l4': get_param('obj_l4'),
            'obj_l5': get_param('obj_l5'),
            'obj_l6': get_param('obj_l6'),
            'obj_l7': get_param('obj_l7'),
            'obj_l8': get_param('obj_l8'),
        }

        # 누락된 파라미터에 추천값 설정
        suggested = cls_info.get('suggested_params', {})

        for key, suggested_val in suggested.items():
            param_key = key.lower().replace('objl', 'obj_l').replace('itmid', 'itm_id')
            # 사용자가 명시적으로 지정하지 않은 경우에만 추천값 사용
            # (빈 문자열도 유효한 지정값으로 인정)
            current_val = params.get(param_key)
            user_specified = param_key in classification_params and classification_params.get(param_key) != 'ALL'
            if current_val == '' and not user_specified:
                params[param_key] = suggested_val

        # objL1이 여전히 비어있으면 첫 번째 분류값 또는 'ALL'
        if params.get('obj_l1') == '':
            classifications = cls_info.get('classifications', [])
            if classifications and classifications[0].get('values'):
                params['obj_l1'] = classifications[0]['values'][0].get('code', 'ALL')
            else:
                params['obj_l1'] = 'ALL'

        result['used_params'] = params

        # 3. 예상 셀 수 계산
        estimated_cells = self._estimate_cell_count(cls_info, {
            'objL1': params['obj_l1'],
            'objL2': params['obj_l2'],
            'objL3': params['obj_l3'],
            'objL4': params['obj_l4'],
            'objL5': params['obj_l5'],
            'objL6': params['obj_l6'],
            'objL7': params['obj_l7'],
            'objL8': params['obj_l8'],
            'itmId': params['itm_id']
        })

        # 기간 수 곱하기
        try:
            if prd_se == 'Y':
                period_count = int(end_prd_de) - int(start_prd_de) + 1
            elif prd_se == 'M':
                start_y, start_m = int(start_prd_de[:4]), int(start_prd_de[4:6])
                end_y, end_m = int(end_prd_de[:4]), int(end_prd_de[4:6])
                period_count = (end_y - start_y) * 12 + (end_m - start_m) + 1
            elif prd_se == 'Q':
                period_count = 4 * (int(end_prd_de[:4]) - int(start_prd_de[:4])) + 4
            else:
                period_count = 12  # 기본 추정
        except (ValueError, IndexError):
            period_count = 12

        estimated_cells *= period_count
        result['estimated_cells'] = estimated_cells

        # 대용량 경고
        if estimated_cells > 40000:
            result['warnings'].append(
                f"⚠️ 예상 셀 수({estimated_cells:,})가 40,000을 초과합니다. "
                "분류나 기간을 좁혀서 조회하세요."
            )
            print(f"[스마트 모드] 경고: 예상 셀 수 {estimated_cells:,}개 (40,000 초과)")

        # 4. 데이터 조회
        print(f"[스마트 모드] 데이터 조회: {org_id}/{tbl_id}")
        print(f"  파라미터: objL1={params['obj_l1']}, objL2={params['obj_l2']}, itmId={params['itm_id']}")

        api_result = self.get_stat_data(
            org_id=org_id,
            tbl_id=tbl_id,
            prd_se=prd_se,
            start_prd_de=start_prd_de,
            end_prd_de=end_prd_de,
            itm_id=params['itm_id'],
            obj_l1=params['obj_l1'],
            obj_l2=params['obj_l2'],
            obj_l3=params['obj_l3'],
            obj_l4=params['obj_l4'],
            obj_l5=params['obj_l5'],
            obj_l6=params['obj_l6'],
            obj_l7=params['obj_l7'],
            obj_l8=params['obj_l8']
        )

        # 결과 처리
        if isinstance(api_result, list):
            result['data'] = api_result
            result['success'] = True
            print(f"[스마트 모드] 조회 완료: {len(api_result)}건")
        elif isinstance(api_result, dict) and 'err' in api_result:
            err_code = api_result.get('err', '')
            err_msg = self.ERROR_CODES.get(err_code, api_result.get('errMsg', '알 수 없는 오류'))
            result['warnings'].append(f"API 오류 [{err_code}]: {err_msg}")

            # 오류 31 (필수 파라미터 누락) 시 친절한 안내
            if err_code == '31':
                hint = self._build_error_hint(org_id, tbl_id, cls_info)
                result['warnings'].append(hint)
        else:
            result['data'] = api_result if api_result else []
            result['success'] = True

        return result

    def _build_error_hint(
        self,
        org_id: str,
        tbl_id: str,
        cls_info: Optional[Dict]
    ) -> str:
        """
        오류 발생 시 친절한 힌트 메시지 생성

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            cls_info: 분류 구조 정보

        Returns:
            힌트 메시지
        """
        lines = [
            f"\n이 통계표({tbl_id})의 분류 구조:",
        ]

        if cls_info and cls_info.get('classifications'):
            for cls in cls_info['classifications']:
                level = cls.get('level', 1)
                name = cls.get('name', f'분류{level}')
                values = cls.get('values', [])

                values_str = ', '.join([
                    f"{v['code']}({v['name']})"
                    for v in values[:5]
                ])
                if len(values) > 5:
                    values_str += f' ... 외 {len(values)-5}개'

                lines.append(f"  - objL{level}: {name} - 값: {values_str}")

            # 권장 명령어
            suggested = cls_info.get('suggested_params', {})
            cmd_parts = [f"--obj-l{k.replace('objL', '')} {v}" for k, v in suggested.items() if k.startswith('objL')]
            cmd = f"python kosis_api.py --data {org_id} {tbl_id} " + ' '.join(cmd_parts)

            lines.append(f"\n권장 조회 방법:")
            lines.append(f"  {cmd}")
            lines.append(f"\n또는 --smart 옵션 사용:")
            lines.append(f"  python kosis_api.py --data {org_id} {tbl_id} --smart")
        else:
            lines.append("  분류 구조를 확인할 수 없습니다.")
            lines.append("  --cls-info 명령으로 먼저 분류 정보를 확인하세요.")

        return '\n'.join(lines)

    # ==================== 통계표설명 API ====================

    def get_stat_desc(
        self,
        org_id: str,
        tbl_id: str,
        desc_type: str = 'TBL_NM'
    ) -> Dict[str, Any]:
        """
        통계표설명 조회

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            desc_type: 설명유형 (TBL_NM, ORG_NM, PRD_INFO, OBJ_VAR 등)

        Returns:
            통계표설명
        """
        params = {
            'method': 'getList',
            'orgId': org_id,
            'tblId': tbl_id,
            'type': desc_type,
        }

        result = self._make_request('statisticsTableData.do', params)
        return result

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
            default_keywords = ['인구', '경제', '물가', '고용', '주택', '환경']
            tables = self.meta_db.sync_from_search(default_keywords, force=force)
            return tables > 0
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
        통계표 검색 (메타DB 활용)

        Args:
            keyword: 검색 키워드

        Returns:
            검색 결과 리스트
        """
        if self.meta_db:
            return self.meta_db.search_tables(keyword)
        return []

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
                rows = data if isinstance(data, list) else []
                if not rows:
                    for key in data:
                        if isinstance(data[key], list):
                            rows = data[key]
                            break
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
        data: Union[List, Dict],
        org_id: str,
        tbl_id: str,
        prd_se: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None
    ) -> int:
        """
        API 응답 데이터를 kosis.db에 저장

        Args:
            data: API 응답 데이터
            org_id: 기관 ID
            tbl_id: 통계표 ID
            prd_se: 수록주기
            start_period: 시작 기간
            end_period: 종료 기간

        Returns:
            저장된 레코드 수
        """
        # 데이터 추출 (KOSIS는 리스트로 반환)
        rows = data if isinstance(data, list) else []
        if not rows:
            self._log_collection(org_id, tbl_id, start_period, end_period, prd_se,
                               'success', 0, 'No data')
            return 0

        conn = self._get_data_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        saved_count = 0

        try:
            for item in rows:
                cursor.execute('''
                    INSERT OR REPLACE INTO kosis_data
                    (org_id, tbl_id, tbl_name, itm_id, itm_name, cls_id, cls_name,
                     time_period, prd_se, data_value, unit_name, raw_data, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item.get('ORG_ID', org_id),
                    item.get('TBL_ID', tbl_id),
                    item.get('TBL_NM', ''),
                    item.get('ITM_ID', ''),
                    item.get('ITM_NM', ''),
                    item.get('C1', ''),
                    item.get('C1_NM', ''),
                    item.get('PRD_DE', ''),
                    prd_se,
                    item.get('DT', ''),
                    item.get('UNIT_NM', ''),
                    json.dumps(item, ensure_ascii=False),
                    now
                ))
                saved_count += 1

            conn.commit()
            self._log_collection(org_id, tbl_id, start_period, end_period, prd_se,
                               'success', saved_count, None)
            print(f"DB 저장 완료: {saved_count}건 → {self.DATA_DB_PATH.name}")

        except Exception as e:
            conn.rollback()
            self._log_collection(org_id, tbl_id, start_period, end_period, prd_se,
                               'error', 0, str(e))
            print(f"DB 저장 실패: {e}")

        finally:
            conn.close()

        return saved_count

    def _log_collection(
        self,
        org_id: str,
        tbl_id: str,
        start_period: Optional[str],
        end_period: Optional[str],
        prd_se: str,
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
                (org_id, tbl_id, start_period, end_period, prd_se, status,
                 record_count, error_message, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                org_id, tbl_id, start_period, end_period, prd_se, status,
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

        cursor.execute('SELECT COUNT(*) FROM kosis_data')
        stats['total_records'] = cursor.fetchone()[0]

        cursor.execute('''
            SELECT tbl_id, tbl_name, COUNT(*) as cnt,
                   MIN(time_period) as min_time, MAX(time_period) as max_time
            FROM kosis_data
            GROUP BY tbl_id
            ORDER BY cnt DESC
        ''')
        stats['by_table'] = [
            {'tbl_id': r[0], 'tbl_name': r[1], 'count': r[2],
             'min_time': r[3], 'max_time': r[4]}
            for r in cursor.fetchall()
        ]

        cursor.execute('''
            SELECT tbl_id, status, record_count, collected_at
            FROM collection_log
            ORDER BY collected_at DESC
            LIMIT 10
        ''')
        stats['recent_logs'] = [
            {'tbl_id': r[0], 'status': r[1], 'count': r[2], 'collected_at': r[3]}
            for r in cursor.fetchall()
        ]

        conn.close()
        return stats

    def query_db(
        self,
        tbl_id: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        itm_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """데이터 DB 조회"""
        if not self.DATA_DB_PATH.exists():
            return []

        conn = self._get_data_db_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM kosis_data WHERE 1=1'
        params = []

        if tbl_id:
            query += ' AND tbl_id = ?'
            params.append(tbl_id)
        if start_period:
            query += ' AND time_period >= ?'
            params.append(start_period)
        if end_period:
            query += ' AND time_period <= ?'
            params.append(end_period)
        if itm_id:
            query += ' AND itm_id = ?'
            params.append(itm_id)

        query += f' ORDER BY time_period DESC LIMIT {limit}'

        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return results

    # ==================== DB-First 패턴 (v2.1) ====================

    def _normalize_date(self, date_str: str) -> str:
        """
        입력 날짜를 DB 형식(YYYYMM 또는 YYYY)으로 변환

        Args:
            date_str: 입력 날짜 (YYYY-MM, YYYYMM, YYYY 등)

        Returns:
            YYYYMM 또는 YYYY 형식의 날짜
        """
        # 하이픈 제거 후 숫자만 추출
        digits = ''.join(c for c in date_str if c.isdigit())
        return digits  # 그대로 반환 (YYYY, YYYYMM, YYYYMMDD 등)

    def get_data_with_db_first(
        self,
        org_id: str,
        tbl_id: str,
        prd_se: str,
        start_date: str,
        end_date: str,
        itm_id: str = 'ALL',
        obj_l1: str = 'ALL'
    ) -> Dict[str, Any]:
        """
        DB-First 패턴으로 데이터 조회

        1. DB에서 해당 기간 데이터 확인
        2. DB에 데이터가 있고 기간이 충족되면 반환
        3. 없거나 기간이 부족하면 API 호출 → DB 저장 → 반환

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            prd_se: 수록주기 (Y/H/Q/M/S/D)
            start_date: 시작 시점
            end_date: 종료 시점
            itm_id: 항목 ID
            obj_l1: 분류1

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
            'saved': 0,
            'tbl_id': tbl_id
        }

        # 1. DB에서 기존 데이터 조회
        db_data = self.query_db(
            tbl_id=tbl_id,
            start_period=start_period,
            end_period=end_period,
            itm_id=itm_id if itm_id != 'ALL' else None,
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
        print(f"[DB-First] API 호출: {tbl_id} ({start_period}~{end_period})")
        api_result = self.get_stat_data(
            org_id=org_id,
            tbl_id=tbl_id,
            prd_se=prd_se,
            start_prd_de=start_period,
            end_prd_de=end_period,
            itm_id=itm_id,
            obj_l1=obj_l1
        )

        # KOSIS API는 리스트로 반환
        api_rows = api_result if isinstance(api_result, list) else []
        result['api_count'] = len(api_rows)

        # 3. API 데이터 DB에 저장
        if api_rows:
            saved = self.save_to_db(api_result, org_id, tbl_id, prd_se, start_period, end_period)
            result['saved'] = saved
            print(f"[DB-First] API에서 조회 → DB 저장: {saved}건")

        # 4. 결과 반환 (API 원본 형식 그대로)
        result['data'] = api_rows
        result['source'] = 'api'
        return result

    def get_data_db_only(
        self,
        tbl_id: str,
        start_date: str,
        end_date: str,
        itm_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DB에서만 데이터 조회 (API 호출 안함)

        Args:
            tbl_id: 통계표 ID
            start_date: 시작 시점
            end_date: 종료 시점
            itm_id: 항목 ID (선택)

        Returns:
            DB 조회 결과
        """
        start_period = self._normalize_date(start_date)
        end_period = self._normalize_date(end_date)

        db_data = self.query_db(
            tbl_id=tbl_id,
            start_period=start_period,
            end_period=end_period,
            itm_id=itm_id,
            limit=100000
        )

        return {
            'data': sorted(db_data, key=lambda x: x['time_period']),
            'source': 'db',
            'db_count': len(db_data),
            'api_count': 0,
            'saved': 0,
            'tbl_id': tbl_id
        }


# ==================== CLI 함수 ====================

def print_search_result(api: KosisAPI, args):
    """검색 결과 출력"""
    result = api.search(args.search, result_count=args.limit if hasattr(args, 'limit') else 100)

    if not api._check_response(result):
        return result

    items = result if isinstance(result, list) else []

    print(f"\n=== '{args.search}' 검색 결과 ({len(items)}건) ===")
    print(f"{'통계표ID':<20} {'통계표명':<40} {'기관명':<15}")
    print("-" * 80)

    for item in items[:args.limit]:
        tbl_id = (item.get('TBL_ID') or '')[:18]
        tbl_nm = (item.get('TBL_NM') or '')[:38]
        org_nm = (item.get('ORG_NM') or '')[:13]
        print(f"{tbl_id:<20} {tbl_nm:<40} {org_nm:<15}")

    return result


def print_stat_list(api: KosisAPI, args):
    """통계목록 출력"""
    vw_cd = args.list[0] if args.list else 'MT_ZTITLE'
    parent_id = args.list[1] if len(args.list) > 1 else 'A'

    result = api.get_stat_list(vw_cd, parent_id)

    if not api._check_response(result):
        return result

    items = result if isinstance(result, list) else []

    print(f"\n=== 통계목록: {vw_cd} > {parent_id} ({len(items)}건) ===")
    print(f"{'목록ID':<15} {'목록명':<40} {'유형':<5} {'통계표ID':<20}")
    print("-" * 85)

    for item in items[:args.limit]:
        list_id = (item.get('LIST_ID') or '')[:13]
        list_nm = (item.get('LIST_NM') or '')[:38]
        rec_type = item.get('REC_TBL_SE') or '-'
        tbl_id = (item.get('TBL_ID') or '-')[:18]
        print(f"{list_id:<15} {list_nm:<40} {rec_type:<5} {tbl_id:<20}")

    return result


def print_stat_data(api: KosisAPI, args):
    """통계자료 출력"""
    result = api.get_stat_data(
        org_id=args.org_id,
        tbl_id=args.tbl_id,
        prd_se=args.prd_se,
        start_prd_de=args.start,
        end_prd_de=args.end,
        new_est_prd_cnt=args.recent if hasattr(args, 'recent') else None,
        itm_id=getattr(args, 'itm_id', 'ALL'),
        obj_l1=getattr(args, 'obj_l1', 'ALL'),
        obj_l2=getattr(args, 'obj_l2', ''),
        obj_l3=getattr(args, 'obj_l3', ''),
        obj_l4=getattr(args, 'obj_l4', ''),
        obj_l5=getattr(args, 'obj_l5', ''),
        obj_l6=getattr(args, 'obj_l6', ''),
        obj_l7=getattr(args, 'obj_l7', ''),
        obj_l8=getattr(args, 'obj_l8', ''),
    )

    if not api._check_response(result):
        return result

    items = result if isinstance(result, list) else []

    # 통계표명 가져오기
    tbl_nm = items[0].get('TBL_NM', args.tbl_id) if items else args.tbl_id

    print(f"\n=== [{args.tbl_id}] {tbl_nm} ({len(items)}건) ===")
    if args.start and args.end:
        print(f"기간: {args.start} ~ {args.end} (주기: {api.PERIOD_CODES.get(args.prd_se, args.prd_se)})")
    print(f"{'시점':<12} {'분류':<25} {'항목':<25} {'값':<15} {'단위':<10}")
    print("-" * 95)

    for item in items[:args.limit]:
        prd = item.get('PRD_DE', '')
        c1 = (item.get('C1_NM') or '')[:23]
        itm = (item.get('ITM_NM') or '')[:23]
        dt = item.get('DT', '-')
        unit = (item.get('UNIT_NM') or '-')[:8]
        print(f"{prd:<12} {c1:<25} {itm:<25} {dt:<15} {unit:<10}")

    return result


def print_db_search(api: KosisAPI, args):
    """DB 검색 결과 출력"""
    if api.meta_db:
        results = api.meta_db.search_tables(args.db_search)
        print(f"\n=== DB 검색: '{args.db_search}' ({len(results)}건) ===")
        print(f"{'통계표ID':<20} {'통계표명':<40} {'기관명':<15}")
        print("-" * 80)
        for t in results[:args.limit]:
            tbl_id = (t.get('tbl_id') or '')[:18]
            tbl_nm = (t.get('tbl_nm') or '')[:38]
            org_nm = (t.get('org_nm') or '-')[:13]
            print(f"{tbl_id:<20} {tbl_nm:<40} {org_nm:<15}")
    else:
        print("메타DB가 초기화되지 않았습니다. --sync를 먼저 실행하세요.")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='KOSIS 국가통계포털 OpenAPI 클라이언트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 메타데이터 동기화
  python kosis_api.py --sync

  # DB 통계
  python kosis_api.py --stats

  # 통합검색
  python kosis_api.py --search "실업률"

  # 통계목록 조회
  python kosis_api.py --list MT_ZTITLE A

  # 통계자료 조회
  python kosis_api.py --data 101 DT_1IN1502 --prd-se M --start 202301 --end 202312

  # 최근 N개 시점 조회
  python kosis_api.py --data 101 DT_1IN1502 --prd-se M --recent 12

  # 결과 저장
  python kosis_api.py --data 101 DT_1IN1502 --prd-se M --recent 12 --output result.csv
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
                        help='KOSIS 통합검색')
    parser.add_argument('--db-search', type=str, metavar='KEYWORD',
                        help='메타DB 검색')
    parser.add_argument('--list', nargs='*', metavar=('VW_CD', 'PARENT_ID'),
                        help='통계목록 조회')
    parser.add_argument('--info', type=str, metavar='TBL_ID',
                        help='통계표 정보 조회')

    # 데이터 조회
    parser.add_argument('--data', nargs=2, metavar=('ORG_ID', 'TBL_ID'),
                        help='통계자료 조회 (기관ID, 통계표ID)')
    parser.add_argument('--prd-se', type=str, default='Y',
                        choices=['Y', 'H', 'Q', 'M', 'S', 'D'],
                        help='수록주기 (Y=년, H=반년, Q=분기, M=월, S=반월, D=일)')
    parser.add_argument('--start', type=str,
                        help='시작 시점 (예: 2023, 202301)')
    parser.add_argument('--end', type=str,
                        help='종료 시점')
    parser.add_argument('--recent', type=int,
                        help='최근 N개 시점')
    parser.add_argument('--itm-id', type=str, default='ALL',
                        help='항목 ID')
    parser.add_argument('--obj-l1', type=str, default='ALL',
                        help='분류1')
    parser.add_argument('--obj-l2', type=str, default='',
                        help='분류2')
    parser.add_argument('--obj-l3', type=str, default='',
                        help='분류3')
    parser.add_argument('--obj-l4', type=str, default='',
                        help='분류4')
    parser.add_argument('--obj-l5', type=str, default='',
                        help='분류5')
    parser.add_argument('--obj-l6', type=str, default='',
                        help='분류6')
    parser.add_argument('--obj-l7', type=str, default='',
                        help='분류7')
    parser.add_argument('--obj-l8', type=str, default='',
                        help='분류8')

    # 분류정보 조회
    parser.add_argument('--cls-info', nargs=2, metavar=('ORG_ID', 'TBL_ID'),
                        help='통계표 분류/항목 정보 조회')

    # 스마트 조회 모드
    parser.add_argument('--smart', action='store_true',
                        help='스마트 모드 (분류 자동 처리)')

    # 출력 옵션
    parser.add_argument('--limit', type=int, default=100,
                        help='조회 건수 (기본: 100)')
    parser.add_argument('--output', '-o', type=str,
                        help='결과 저장 파일 (json/csv)')
    parser.add_argument('--save-db', action='store_true',
                        help='결과를 DB에 저장 (R-DB/outputs/kosis.db)')
    parser.add_argument('--data-db-stats', action='store_true',
                        help='데이터 DB 통계 출력')
    parser.add_argument('--query-db', action='store_true',
                        help='DB에서 데이터 조회 (--data TBL_ID, --start, --end 사용)')
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
    api = KosisAPI(api_key=args.api_key)

    result = None

    if args.sync:
        api.sync_metadata(force=args.force)

    elif args.stats:
        stats = api.get_db_stats()
        if stats:
            print("\n=== KOSIS 메타DB 통계 ===")
            print(f"통계표: {stats['tables']:,}개")
            print(f"계층항목: {stats['hierarchy']:,}개")
            print(f"주요지표: {stats['key_indicators']:,}개")

            if stats.get('by_org'):
                print("\n기관별 통계표 (Top 10):")
                for org, cnt in list(stats['by_org'].items())[:10]:
                    print(f"  - {org}: {cnt:,}개")

            if stats.get('tables_updated'):
                print(f"\n마지막 업데이트: {stats['tables_updated'][:19]}")
        else:
            print("DB가 초기화되지 않았습니다. --sync를 먼저 실행하세요.")

    elif args.data_db_stats:
        stats = api.get_data_db_stats()
        if stats:
            print(f"\n=== KOSIS 데이터 DB 통계 ({api.DATA_DB_PATH.name}) ===")
            print(f"총 레코드: {stats['total_records']:,}건")

            if stats.get('by_table'):
                print("\n통계표별 데이터:")
                print(f"{'통계표ID':<20} {'통계표명':<30} {'건수':<10} {'기간':<20}")
                print("-" * 85)
                for t in stats['by_table'][:20]:
                    name = (t['tbl_name'] or '')[:28]
                    period = f"{t['min_time']}~{t['max_time']}"
                    print(f"{t['tbl_id']:<20} {name:<30} {t['count']:<10,} {period:<20}")

            if stats.get('recent_logs'):
                print("\n최근 수집 로그:")
                for log in stats['recent_logs'][:5]:
                    print(f"  - [{log['status']}] {log['tbl_id']}: {log['count']}건 ({log['collected_at'][:16]})")
        else:
            print("데이터 DB가 없습니다. --save-db 옵션으로 데이터를 저장하세요.")

    elif args.query_db:
        tbl_id = args.data[1] if args.data else None
        results = api.query_db(
            tbl_id=tbl_id,
            start_period=args.start,
            end_period=args.end,
            limit=args.limit
        )
        if results:
            print(f"\n=== DB 조회 결과 ({len(results)}건) ===")
            print(f"{'시점':<12} {'통계표ID':<20} {'항목명':<25} {'값':<15} {'단위':<10}")
            print("-" * 90)
            for r in results:
                time = r.get('time_period', '')
                tbl = (r.get('tbl_id', '') or '')[:18]
                name = (r.get('itm_name', '') or '')[:23]
                val = (r.get('data_value', '') or '')[:13]
                unit = (r.get('unit_name', '') or '')[:8]
                print(f"{time:<12} {tbl:<20} {name:<25} {val:<15} {unit:<10}")
        else:
            print("조회 결과가 없습니다.")

    elif args.search:
        result = print_search_result(api, args)

    elif args.db_search:
        print_db_search(api, args)

    elif args.list is not None:
        result = print_stat_list(api, args)

    elif args.info:
        if api.meta_db:
            info = api.meta_db.get_table_info(args.info)
            if info:
                print(f"\n=== 통계표 정보 ===")
                print(f"통계표ID: {info.get('tbl_id', '-')}")
                print(f"통계표명: {info.get('tbl_nm', '-')}")
                print(f"기관ID: {info.get('org_id', '-')}")
                print(f"기관명: {info.get('org_nm', '-')}")
                print(f"통계명: {info.get('stat_nm', '-')}")
                print(f"수록주기: {info.get('prd_se', '-')}")
                print(f"수록시점: {info.get('prd_de', '-')}")
            else:
                print(f"통계표 '{args.info}'를 찾을 수 없습니다.")
        else:
            print("메타DB가 초기화되지 않았습니다.")

    elif args.cls_info:
        # 분류/항목 정보 조회
        org_id, tbl_id = args.cls_info
        print(f"\n분류/항목 정보 조회 중: {org_id}/{tbl_id}...")

        cls_result = api.sync_classifications(org_id, tbl_id, force=args.force)

        if cls_result['success']:
            print(f"\n=== [{tbl_id}] 분류/항목 정보 ===")
            print(f"분류 단계 수: {cls_result['obj_count']}")
            print(f"항목 수: {cls_result['itm_count']}")
            print(f"DB 저장: {cls_result['saved']}건")

            # 분류 구조 출력
            classifications = cls_result.get('classifications', [])
            if classifications:
                print("\n분류 구조:")
                for cls in classifications:
                    level = cls.get('level', 1)
                    name = cls.get('name', f'분류{level}')
                    values = cls.get('values', [])

                    print(f"  objL{level}: {name}")
                    if values:
                        print(f"    값({len(values)}개):", end=' ')
                        for v in values[:8]:
                            print(f"{v['code']}({v['name']})", end=' ')
                        if len(values) > 8:
                            print(f"... 외 {len(values)-8}개")
                        else:
                            print()

            # 항목 목록 출력
            items = cls_result.get('items', [])
            if items:
                print(f"\n항목 목록({len(items)}개):")
                for itm in items[:15]:
                    unit = itm.get('unit', '')
                    unit_str = f" ({unit})" if unit else ""
                    print(f"  - {itm['id']}: {itm['name']}{unit_str}")
                if len(items) > 15:
                    print(f"  ... 외 {len(items)-15}개")

            # 추천 파라미터
            suggested = api._build_suggested_params({
                'classifications': classifications,
                'itm_count': cls_result['itm_count']
            })
            print("\n추천 파라미터:")
            for k, v in suggested.items():
                print(f"  --{k.lower().replace('objl', 'obj-l').replace('itmid', 'itm-id')} {v}")
        else:
            print(f"오류: {cls_result.get('message', '알 수 없는 오류')}")

    elif args.data:
        args.org_id = args.data[0]
        args.tbl_id = args.data[1]

        # 스마트 모드 처리
        if args.smart and args.start and args.end:
            smart_result = api.get_stat_data_smart(
                org_id=args.org_id,
                tbl_id=args.tbl_id,
                prd_se=args.prd_se,
                start_prd_de=args.start,
                end_prd_de=args.end,
                itm_id=args.itm_id,
                obj_l1=args.obj_l1,
                obj_l2=args.obj_l2,
                obj_l3=args.obj_l3,
                obj_l4=args.obj_l4,
                obj_l5=args.obj_l5,
                obj_l6=args.obj_l6,
                obj_l7=args.obj_l7,
                obj_l8=args.obj_l8,
            )

            # 경고 메시지 출력
            for warning in smart_result.get('warnings', []):
                print(warning)

            # 결과 출력
            data = smart_result.get('data', [])
            if data:
                tbl_nm = data[0].get('TBL_NM', args.tbl_id) if data else args.tbl_id
                print(f"\n=== [{args.tbl_id}] {tbl_nm} ({len(data)}건, 스마트 모드) ===")
                print(f"기간: {args.start} ~ {args.end} (주기: {api.PERIOD_CODES.get(args.prd_se, args.prd_se)})")
                print(f"사용 파라미터: {smart_result.get('used_params', {})}")
                print(f"{'시점':<12} {'분류':<25} {'항목':<25} {'값':<15} {'단위':<10}")
                print("-" * 95)

                for item in data[:args.limit]:
                    prd = item.get('PRD_DE', '')
                    c1 = (item.get('C1_NM') or '')[:23]
                    itm = (item.get('ITM_NM') or '')[:23]
                    dt = item.get('DT', '-')
                    unit = (item.get('UNIT_NM') or '-')[:8]
                    print(f"{prd:<12} {c1:<25} {itm:<25} {dt:<15} {unit:<10}")

            result = smart_result.get('data', [])

        # DB-First 패턴 처리
        elif args.db_only and args.start and args.end:
            # DB에서만 조회
            db_result = api.get_data_db_only(
                tbl_id=args.tbl_id,
                start_date=args.start,
                end_date=args.end,
                itm_id=args.itm_id if args.itm_id != 'ALL' else None
            )
            print(f"\n=== [{args.tbl_id}] DB 조회 결과 ({db_result['db_count']}건) ===")
            print(f"기간: {args.start} ~ {args.end}")
            print(f"{'시점':<12} {'분류':<25} {'항목':<25} {'값':<15} {'단위':<10}")
            print("-" * 95)
            for item in db_result['data'][:args.limit]:
                prd = item.get('time_period', '')
                c1 = (item.get('cls_name', '') or '')[:23]
                itm = (item.get('itm_name', '') or '')[:23]
                dt = item.get('data_value', '-')
                unit = (item.get('unit_name', '') or '-')[:8]
                print(f"{prd:<12} {c1:<25} {itm:<25} {dt:<15} {unit:<10}")
            result = db_result
        elif args.force_api or not (args.start and args.end):
            # API 직접 호출 (기존 방식)
            result = print_stat_data(api, args)
        else:
            # DB-First 패턴 (기본값)
            db_first_result = api.get_data_with_db_first(
                org_id=args.org_id,
                tbl_id=args.tbl_id,
                prd_se=args.prd_se,
                start_date=args.start,
                end_date=args.end,
                itm_id=args.itm_id,
                obj_l1=args.obj_l1
            )

            source_str = "DB" if db_first_result['source'] == 'db' else "API"
            total_count = db_first_result['db_count'] or db_first_result['api_count']

            # 통계표명 가져오기
            tbl_nm = args.tbl_id
            if db_first_result['data']:
                first_item = db_first_result['data'][0]
                if isinstance(first_item, dict):
                    tbl_nm = first_item.get('TBL_NM') or first_item.get('tbl_name') or args.tbl_id

            print(f"\n=== [{args.tbl_id}] {tbl_nm} ({total_count}건, {source_str}) ===")
            print(f"기간: {args.start} ~ {args.end} (주기: {api.PERIOD_CODES.get(args.prd_se, args.prd_se)})")
            print(f"{'시점':<12} {'분류':<25} {'항목':<25} {'값':<15} {'단위':<10}")
            print("-" * 95)

            for item in db_first_result['data'][:args.limit]:
                if db_first_result['source'] == 'db':
                    prd = item.get('time_period', '')
                    c1 = (item.get('cls_name', '') or '')[:23]
                    itm = (item.get('itm_name', '') or '')[:23]
                    dt = item.get('data_value', '-')
                    unit = (item.get('unit_name', '') or '-')[:8]
                else:
                    prd = item.get('PRD_DE', '')
                    c1 = (item.get('C1_NM') or '')[:23]
                    itm = (item.get('ITM_NM') or '')[:23]
                    dt = item.get('DT', '-')
                    unit = (item.get('UNIT_NM') or '-')[:8]
                print(f"{prd:<12} {c1:<25} {itm:<25} {dt:<15} {unit:<10}")

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

    # DB 저장 (--save-db 옵션)
    if args.save_db and result and args.data:
        api.save_to_db(result, args.data[0], args.data[1], args.prd_se, args.start, args.end)


if __name__ == '__main__':
    main()
