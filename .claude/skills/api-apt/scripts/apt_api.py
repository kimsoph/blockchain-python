# -*- coding: utf-8 -*-
"""
국토교통부 아파트 매매/전월세 실거래가 API 클라이언트

Usage:
    # ==================== DB-First 조회 (권장) ====================
    # 매매 데이터 조회 (DB 우선, 없으면 API 호출)
    python apt_api.py --trades --region 11170 --ym 202501-202512
    python apt_api.py --trades --region 11170 --ym 202511 --apt-name "래미안"
    python apt_api.py --trades --region 11170 --ym 202501-202512 --min-area 84 --max-area 120

    # 전월세 데이터 조회 (DB 우선, 없으면 API 호출)
    python apt_api.py --rents --region 11170 --ym 202501-202512
    python apt_api.py --rents --region 11170 --ym 202511 --jeonse  # 전세만
    python apt_api.py --rents --region 11170 --ym 202511 --monthly  # 월세만

    # DB-First 옵션
    python apt_api.py --trades --region 11170 --ym 202511 --force-api  # DB 무시, API 강제 호출
    python apt_api.py --trades --region 11170 --ym 202511 --db-only    # DB만 조회 (API 호출 안 함)

    # ==================== 기존 방식 (하위호환) ====================
    # 매매 데이터 동기화
    python apt_api.py --sync --region 11170 --ym 202511
    python apt_api.py --sync --region 11170 --ym 202501-202512

    # 전월세 데이터 동기화
    python apt_api.py --rent --sync --region 11170 --ym 202511

    # 검색
    python apt_api.py --search "한남더힐"
    python apt_api.py --rent --search "한남더힐"

    # 고가 거래
    python apt_api.py --top 10
    python apt_api.py --rent --top 10 --jeonse  # 전세만
    python apt_api.py --rent --top 10 --monthly  # 월세만

    # DB 통계
    python apt_api.py --stats
    python apt_api.py --rent --stats

    # 지역코드 목록
    python apt_api.py --regions
"""

import os
import sys
import json
import csv
import requests
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Any

# 환경변수 로드
from dotenv import load_dotenv

# 경로 설정
SKILL_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = SKILL_ROOT.parent.parent.parent
ENV_PATH = PROJECT_ROOT / '.claude' / '.env'
load_dotenv(ENV_PATH)

# 스크립트 경로 추가
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
from apt_meta_db import AptMetaDB
from apt_data_db import AptDataDB

# API 설정
API_KEY = os.getenv('APT_API_KEY')
TRADE_BASE_URL = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade'
TRADE_DEV_URL = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev'
RENT_BASE_URL = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent'

# 기본 매매 URL (상세자료)
BASE_URL = TRADE_DEV_URL


class AptTradeAPI:
    """국토교통부 아파트 매매 실거래가 API 클라이언트"""

    def __init__(self, api_key: str = API_KEY):
        self.api_key = api_key
        self.meta_db = AptMetaDB()
        self.data_db = AptDataDB()

    def fetch_trades(self, sgg_cd: str, deal_ym: str, page: int = 1, num_rows: int = 1000) -> Dict:
        """API 호출하여 거래 데이터 조회"""
        if not self.api_key:
            raise Exception('API 키가 설정되지 않았습니다. .env 파일의 APT_API_KEY를 확인하세요.')

        params = {
            'serviceKey': self.api_key,
            'LAWD_CD': sgg_cd,
            'DEAL_YMD': deal_ym,
            'pageNo': str(page),
            'numOfRows': str(num_rows)
        }

        response = requests.get(BASE_URL, params=params, timeout=30)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            raise Exception(f'API 오류: HTTP {response.status_code}')

        return self._parse_xml(response.text)

    def _parse_xml(self, xml_text: str) -> Dict:
        """XML 응답 파싱"""
        root = ET.fromstring(xml_text)

        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text not in ('00', '000'):
            result_msg = root.find('.//resultMsg')
            raise Exception(f'API 오류: {result_code.text} - {result_msg.text if result_msg is not None else ""}')

        total_count_elem = root.find('.//totalCount')
        total_count = int(total_count_elem.text) if total_count_elem is not None else 0

        items = []
        for item in root.findall('.//item'):
            tx = {
                'sgg_cd': self._get_text(item, 'sggCd'),
                'umd_cd': self._get_text(item, 'umdCd'),
                'umd_nm': self._get_text(item, 'umdNm'),
                'jibun': self._get_text(item, 'jibun'),
                'apt_seq': self._get_text(item, 'aptSeq'),
                'apt_nm': self._get_text(item, 'aptNm'),
                'apt_dong': self._get_text(item, 'aptDong'),
                'build_year': self._get_int(item, 'buildYear'),
                'deal_year': self._get_int(item, 'dealYear'),
                'deal_month': self._get_int(item, 'dealMonth'),
                'deal_day': self._get_int(item, 'dealDay'),
                'deal_amount': self._get_text(item, 'dealAmount'),
                'exclu_use_ar': self._get_float(item, 'excluUseAr'),
                'floor': self._get_int(item, 'floor'),
                'dealing_gbn': self._get_text(item, 'dealingGbn'),
                'buyer_gbn': self._get_text(item, 'buyerGbn'),
                'sler_gbn': self._get_text(item, 'slerGbn'),
                'road_nm': self._get_text(item, 'roadNm'),
                'road_nm_bonbun': self._get_text(item, 'roadNmBonbun'),
                'road_nm_bubun': self._get_text(item, 'roadNmBubun'),
                'cdeal_day': self._get_text(item, 'cdealDay'),
                'cdeal_type': self._get_text(item, 'cdealType'),
                'land_leasehold_gbn': self._get_text(item, 'landLeaseholdGbn'),
                'rgst_date': self._get_text(item, 'rgstDate'),
                'estate_agent_sgg_nm': self._get_text(item, 'estateAgentSggNm'),
            }
            items.append(tx)

        return {
            'total_count': total_count,
            'items': items
        }

    def _get_text(self, item, tag: str) -> Optional[str]:
        elem = item.find(tag)
        return elem.text.strip() if elem is not None and elem.text else None

    def _get_int(self, item, tag: str) -> Optional[int]:
        text = self._get_text(item, tag)
        try:
            return int(text) if text else None
        except ValueError:
            return None

    def _get_float(self, item, tag: str) -> Optional[float]:
        text = self._get_text(item, tag)
        try:
            return float(text) if text else None
        except ValueError:
            return None

    def sync_region_month(self, sgg_cd: str, deal_ym: str) -> int:
        """특정 지역/년월 데이터 동기화"""
        region_name = self.meta_db.get_region_name(sgg_cd)
        print(f'동기화 시작: {region_name} ({sgg_cd}) - {deal_ym[:4]}년 {deal_ym[4:]}월')

        page = 1
        total_synced = 0
        total_count = 0

        while True:
            try:
                result = self.fetch_trades(sgg_cd, deal_ym, page=page)
                total_count = result['total_count']
                items = result['items']

                if not items:
                    break

                inserted = self.data_db.insert_trades(items)
                total_synced += inserted

                print(f'  페이지 {page}: {len(items)}건 조회, {inserted}건 신규 저장')

                if len(items) < 1000:
                    break

                page += 1

            except Exception as e:
                print(f'  오류: {e}')
                break

        self.data_db.update_sync_status(sgg_cd, deal_ym, total_count, total_synced)
        print(f'  완료: 총 {total_count}건 중 {total_synced}건 신규 저장')

        return total_synced

    def sync_region_range(self, sgg_cd: str, start_ym: str, end_ym: str) -> int:
        """특정 지역의 기간 범위 동기화"""
        start_year, start_month = int(start_ym[:4]), int(start_ym[4:])
        end_year, end_month = int(end_ym[:4]), int(end_ym[4:])

        total_synced = 0

        year, month = start_year, start_month
        while (year < end_year) or (year == end_year and month <= end_month):
            deal_ym = f'{year}{month:02d}'
            total_synced += self.sync_region_month(sgg_cd, deal_ym)

            month += 1
            if month > 12:
                month = 1
                year += 1

        return total_synced

    # ==================== DB-First 메서드 ====================

    def _normalize_date(self, date_str: str) -> str:
        """입력 날짜를 YYYYMM 형식으로 정규화"""
        digits = ''.join(c for c in date_str if c.isdigit())
        return digits[:6]

    def _generate_months(self, start_ym: str, end_ym: str) -> List[str]:
        """시작~종료 월 목록 생성"""
        start_year, start_month = int(start_ym[:4]), int(start_ym[4:6])
        end_year, end_month = int(end_ym[:4]), int(end_ym[4:6])

        months = []
        year, month = start_year, start_month
        while (year < end_year) or (year == end_year and month <= end_month):
            months.append(f'{year}{month:02d}')
            month += 1
            if month > 12:
                month = 1
                year += 1
        return months

    def get_trades_with_db_first(
        self,
        sgg_cd: str,
        start_ym: str,
        end_ym: str,
        apt_name: Optional[str] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        min_amount: Optional[int] = None,
        limit: int = 1000,
        force_api: bool = False
    ) -> Dict[str, Any]:
        """DB-First 패턴으로 매매 데이터 조회

        1. sync_status 확인 → 미동기화 월 식별
        2. 미동기화 월만 API 호출 & 저장
        3. DB에서 전체 결과 조회 (필터 적용)
        """
        start_ym = self._normalize_date(start_ym)
        end_ym = self._normalize_date(end_ym)
        months = self._generate_months(start_ym, end_ym)

        # 1. 동기화 상태 확인
        if force_api:
            unsynced = months
        else:
            unsynced = [m for m in months if not self.data_db.is_synced(sgg_cd, m)]

        # 2. 미동기화 월 API 호출 & 저장
        api_synced = 0
        if unsynced:
            region_name = self.meta_db.get_region_name(sgg_cd)
            print(f'[DB-First] {region_name} ({sgg_cd}): {len(unsynced)}개월 미동기화')
            for deal_ym in unsynced:
                api_synced += self.sync_region_month(sgg_cd, deal_ym)

        # 3. DB에서 결과 조회
        results = self.data_db.query_trades(
            sgg_cd=sgg_cd,
            start_ym=start_ym,
            end_ym=end_ym,
            apt_name=apt_name,
            min_area=min_area,
            max_area=max_area,
            min_amount=min_amount,
            limit=limit
        )

        source = 'api+db' if unsynced else 'db'
        if unsynced:
            print(f'[DB-First] API 동기화 완료: {api_synced}건 신규 저장')
        else:
            print(f'[DB-First] DB에서 조회: {len(results)}건')

        return {
            'data': results,
            'source': source,
            'total_count': len(results),
            'api_synced': api_synced,
            'months_synced': len(unsynced)
        }

    def get_trades_db_only(
        self,
        sgg_cd: str,
        start_ym: str,
        end_ym: str,
        apt_name: Optional[str] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        min_amount: Optional[int] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """DB에서만 매매 데이터 조회 (API 호출 없음)"""
        start_ym = self._normalize_date(start_ym)
        end_ym = self._normalize_date(end_ym)

        results = self.data_db.query_trades(
            sgg_cd=sgg_cd,
            start_ym=start_ym,
            end_ym=end_ym,
            apt_name=apt_name,
            min_area=min_area,
            max_area=max_area,
            min_amount=min_amount,
            limit=limit
        )

        print(f'[DB-Only] DB에서 조회: {len(results)}건')

        return {
            'data': results,
            'source': 'db',
            'total_count': len(results)
        }


class AptRentAPI:
    """국토교통부 아파트 전월세 실거래가 API 클라이언트"""

    def __init__(self, api_key: str = API_KEY):
        self.api_key = api_key
        self.meta_db = AptMetaDB()
        self.data_db = AptDataDB()

    def fetch_rents(self, sgg_cd: str, deal_ym: str, page: int = 1, num_rows: int = 1000) -> Dict:
        """API 호출하여 전월세 데이터 조회"""
        if not self.api_key:
            raise Exception('API 키가 설정되지 않았습니다. .env 파일의 APT_API_KEY를 확인하세요.')

        params = {
            'serviceKey': self.api_key,
            'LAWD_CD': sgg_cd,
            'DEAL_YMD': deal_ym,
            'pageNo': str(page),
            'numOfRows': str(num_rows)
        }

        response = requests.get(RENT_BASE_URL, params=params, timeout=30)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            raise Exception(f'API 오류: HTTP {response.status_code}')

        return self._parse_xml(response.text, sgg_cd)

    def _parse_xml(self, xml_text: str, sgg_cd: str) -> Dict:
        """XML 응답 파싱"""
        root = ET.fromstring(xml_text)

        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text not in ('00', '000'):
            result_msg = root.find('.//resultMsg')
            raise Exception(f'API 오류: {result_code.text} - {result_msg.text if result_msg is not None else ""}')

        total_count_elem = root.find('.//totalCount')
        total_count = int(total_count_elem.text) if total_count_elem is not None else 0

        items = []
        for item in root.findall('.//item'):
            tx = {
                'sgg_cd': sgg_cd,
                'umd_nm': self._get_text(item, 'umdNm'),
                'jibun': self._get_text(item, 'jibun'),
                'apt_nm': self._get_text(item, 'aptNm'),
                'build_year': self._get_int(item, 'buildYear'),
                'deal_year': self._get_int(item, 'dealYear'),
                'deal_month': self._get_int(item, 'dealMonth'),
                'deal_day': self._get_int(item, 'dealDay'),
                'deposit': self._get_int(item, 'deposit'),
                'monthly_rent': self._get_int(item, 'monthlyRent'),
                'exclu_use_ar': self._get_float(item, 'excluUseAr'),
                'floor': self._get_int(item, 'floor'),
                'contract_term': self._get_text(item, 'contractTerm'),
                'contract_type': self._get_text(item, 'contractType'),
                'use_rr_right': self._get_text(item, 'useRRRight'),
                'pre_deposit': self._get_int(item, 'preDeposit'),
                'pre_monthly_rent': self._get_int(item, 'preMonthlyRent'),
            }
            items.append(tx)

        return {
            'total_count': total_count,
            'items': items
        }

    def _get_text(self, item, tag: str) -> Optional[str]:
        elem = item.find(tag)
        return elem.text.strip() if elem is not None and elem.text else None

    def _get_int(self, item, tag: str) -> Optional[int]:
        text = self._get_text(item, tag)
        try:
            if text:
                return int(text.replace(',', '').strip())
            return None
        except ValueError:
            return None

    def _get_float(self, item, tag: str) -> Optional[float]:
        text = self._get_text(item, tag)
        try:
            return float(text) if text else None
        except ValueError:
            return None

    def sync_region_month(self, sgg_cd: str, deal_ym: str) -> int:
        """특정 지역/년월 전월세 데이터 동기화"""
        region_name = self.meta_db.get_region_name(sgg_cd)
        print(f'전월세 동기화 시작: {region_name} ({sgg_cd}) - {deal_ym[:4]}년 {deal_ym[4:]}월')

        page = 1
        total_synced = 0
        total_count = 0

        while True:
            try:
                result = self.fetch_rents(sgg_cd, deal_ym, page=page)
                total_count = result['total_count']
                items = result['items']

                if not items:
                    break

                inserted = self.data_db.insert_rents(items)
                total_synced += inserted

                print(f'  페이지 {page}: {len(items)}건 조회, {inserted}건 신규 저장')

                if len(items) < 1000:
                    break

                page += 1

            except Exception as e:
                print(f'  오류: {e}')
                break

        self.data_db.update_rent_sync_status(sgg_cd, deal_ym, total_count, total_synced)
        print(f'  완료: 총 {total_count}건 중 {total_synced}건 신규 저장')

        return total_synced

    def sync_region_range(self, sgg_cd: str, start_ym: str, end_ym: str) -> int:
        """특정 지역의 기간 범위 전월세 동기화"""
        start_year, start_month = int(start_ym[:4]), int(start_ym[4:])
        end_year, end_month = int(end_ym[:4]), int(end_ym[4:])

        total_synced = 0

        year, month = start_year, start_month
        while (year < end_year) or (year == end_year and month <= end_month):
            deal_ym = f'{year}{month:02d}'
            total_synced += self.sync_region_month(sgg_cd, deal_ym)

            month += 1
            if month > 12:
                month = 1
                year += 1

        return total_synced

    # ==================== DB-First 메서드 ====================

    def _normalize_date(self, date_str: str) -> str:
        """입력 날짜를 YYYYMM 형식으로 정규화"""
        digits = ''.join(c for c in date_str if c.isdigit())
        return digits[:6]

    def _generate_months(self, start_ym: str, end_ym: str) -> List[str]:
        """시작~종료 월 목록 생성"""
        start_year, start_month = int(start_ym[:4]), int(start_ym[4:6])
        end_year, end_month = int(end_ym[:4]), int(end_ym[4:6])

        months = []
        year, month = start_year, start_month
        while (year < end_year) or (year == end_year and month <= end_month):
            months.append(f'{year}{month:02d}')
            month += 1
            if month > 12:
                month = 1
                year += 1
        return months

    def get_rents_with_db_first(
        self,
        sgg_cd: str,
        start_ym: str,
        end_ym: str,
        apt_name: Optional[str] = None,
        rent_type: Optional[str] = None,
        min_deposit: Optional[int] = None,
        limit: int = 1000,
        force_api: bool = False
    ) -> Dict[str, Any]:
        """DB-First 패턴으로 전월세 데이터 조회

        1. rent_sync_status 확인 → 미동기화 월 식별
        2. 미동기화 월만 API 호출 & 저장
        3. DB에서 전체 결과 조회 (필터 적용)

        Args:
            rent_type: 'jeonse' (전세), 'monthly' (월세), None (전체)
        """
        start_ym = self._normalize_date(start_ym)
        end_ym = self._normalize_date(end_ym)
        months = self._generate_months(start_ym, end_ym)

        # 1. 동기화 상태 확인
        if force_api:
            unsynced = months
        else:
            unsynced = [m for m in months if not self.data_db.is_rent_synced(sgg_cd, m)]

        # 2. 미동기화 월 API 호출 & 저장
        api_synced = 0
        if unsynced:
            region_name = self.meta_db.get_region_name(sgg_cd)
            print(f'[DB-First] {region_name} ({sgg_cd}): {len(unsynced)}개월 미동기화')
            for deal_ym in unsynced:
                api_synced += self.sync_region_month(sgg_cd, deal_ym)

        # 3. DB에서 결과 조회
        results = self.data_db.query_rents(
            sgg_cd=sgg_cd,
            start_ym=start_ym,
            end_ym=end_ym,
            apt_name=apt_name,
            rent_type=rent_type,
            min_deposit=min_deposit,
            limit=limit
        )

        source = 'api+db' if unsynced else 'db'
        if unsynced:
            print(f'[DB-First] API 동기화 완료: {api_synced}건 신규 저장')
        else:
            print(f'[DB-First] DB에서 조회: {len(results)}건')

        return {
            'data': results,
            'source': source,
            'total_count': len(results),
            'api_synced': api_synced,
            'months_synced': len(unsynced)
        }

    def get_rents_db_only(
        self,
        sgg_cd: str,
        start_ym: str,
        end_ym: str,
        apt_name: Optional[str] = None,
        rent_type: Optional[str] = None,
        min_deposit: Optional[int] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """DB에서만 전월세 데이터 조회 (API 호출 없음)

        Args:
            rent_type: 'jeonse' (전세), 'monthly' (월세), None (전체)
        """
        start_ym = self._normalize_date(start_ym)
        end_ym = self._normalize_date(end_ym)

        results = self.data_db.query_rents(
            sgg_cd=sgg_cd,
            start_ym=start_ym,
            end_ym=end_ym,
            apt_name=apt_name,
            rent_type=rent_type,
            min_deposit=min_deposit,
            limit=limit
        )

        print(f'[DB-Only] DB에서 조회: {len(results)}건')

        return {
            'data': results,
            'source': 'db',
            'total_count': len(results)
        }


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
    parser = argparse.ArgumentParser(description='아파트 매매/전월세 실거래가 API 클라이언트')
    parser.add_argument('--rent', action='store_true', help='전월세 모드 (기본: 매매)')
    parser.add_argument('--sync', action='store_true', help='데이터 동기화 (기존 방식)')
    parser.add_argument('--region', '-r', help='지역코드 (예: 11170)')
    parser.add_argument('--ym', help='년월 (예: 202511 또는 202501-202512)')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--search', '-s', help='아파트명/법정동 검색')
    parser.add_argument('--top', type=int, help='고가 거래 TOP N')
    parser.add_argument('--jeonse', action='store_true', help='전세만 (--rent와 함께 사용)')
    parser.add_argument('--monthly', action='store_true', help='월세만 (--rent와 함께 사용)')
    parser.add_argument('--limit', type=int, default=100, help='조회 건수 제한')
    parser.add_argument('--regions', action='store_true', help='지역코드 목록')
    parser.add_argument('--sido', type=str, help='시도 필터 (--regions와 함께 사용)')
    parser.add_argument('--output', '-o', help='결과 저장 (json/csv)')

    # DB-First 옵션
    parser.add_argument('--trades', action='store_true', help='[DB-First] 매매 데이터 조회')
    parser.add_argument('--rents', action='store_true', help='[DB-First] 전월세 데이터 조회')
    parser.add_argument('--force-api', action='store_true', help='DB 무시하고 API 호출')
    parser.add_argument('--db-only', action='store_true', help='DB에서만 조회 (API 호출 안 함)')

    # DB-First 필터 옵션
    parser.add_argument('--apt-name', type=str, help='아파트명 필터')
    parser.add_argument('--min-area', type=float, help='최소 전용면적 (㎡)')
    parser.add_argument('--max-area', type=float, help='최대 전용면적 (㎡)')
    parser.add_argument('--min-amount', type=int, help='최소 거래금액 (만원)')
    parser.add_argument('--min-deposit', type=int, help='최소 보증금 (만원)')

    args = parser.parse_args()

    # 전월세 모드 여부
    is_rent_mode = args.rent

    meta_db = AptMetaDB()
    data_db = AptDataDB()

    # 지역코드 자동 로드
    stats = meta_db.get_stats()
    if stats['regions'] == 0:
        print("지역코드 로드 중...")
        count = meta_db.load_regions_from_csv()
        print(f"지역코드 {count}개 로드 완료\n")

    # 지역코드 목록
    if args.regions:
        regions = meta_db.get_all_regions(sido=args.sido)
        title = "지역코드 목록"
        if args.sido:
            title += f" ({args.sido})"
        print(f'\n=== {title} ({len(regions)}개) ===\n')
        print(f'{"코드":<8} {"지역명":<15} {"시도":<8} {"유형":<8}')
        print('-' * 45)
        for r in regions:
            print(f'{r["region_cd"]:<8} {r["region_nm"]:<15} {r["sido_nm"]:<8} {r["region_type"]:<8}')
        return

    # DB 통계
    if args.stats:
        if is_rent_mode:
            stats = data_db.get_rent_stats()
            print(f'\n=== 전월세 DB 통계 ===')
            print(f'총 거래 건수: {stats["total_count"]:,}건')
            print(f'  - 전세: {stats["jeonse_count"]:,}건')
            print(f'  - 월세: {stats["monthly_count"]:,}건\n')

            if stats['by_region']:
                print('지역별 건수 (TOP 10):')
                for sgg_cd, cnt in stats['by_region']:
                    region_name = meta_db.get_region_name(sgg_cd)
                    print(f'  {region_name}: {cnt:,}건')

            if stats['by_month']:
                print('\n년월별 건수 (최근 12개월):')
                for year, month, cnt in stats['by_month']:
                    print(f'  {year}년 {month:02d}월: {cnt:,}건')
        else:
            stats = data_db.get_stats()
            meta_stats = meta_db.get_stats()
            print(f'\n=== 매매 DB 통계 ===')
            print(f'총 거래 건수: {stats["total_count"]:,}건')
            print(f'등록 지역코드: {meta_stats["regions"]}개\n')

            if stats['by_region']:
                print('지역별 건수 (TOP 10):')
                for sgg_cd, cnt in stats['by_region']:
                    region_name = meta_db.get_region_name(sgg_cd)
                    print(f'  {region_name}: {cnt:,}건')

            if stats['by_month']:
                print('\n년월별 건수 (최근 12개월):')
                for year, month, cnt in stats['by_month']:
                    print(f'  {year}년 {month:02d}월: {cnt:,}건')

            if stats['sync_status']:
                print('\n최근 동기화:')
                for row in stats['sync_status']:
                    sgg_cd, deal_ym, total, synced, synced_at = row
                    region_name = meta_db.get_region_name(sgg_cd)
                    print(f'  {region_name} {deal_ym}: {total}건 (신규 {synced}건) - {synced_at}')
        return

    # ==================== DB-First 조회 ====================

    # 매매 데이터 (DB-First)
    if args.trades:
        if not args.region or not args.ym:
            print('오류: --trades에는 --region과 --ym이 필요합니다.')
            print('예: python apt_api.py --trades --region 11170 --ym 202501-202512')
            return

        # 기간 파싱
        if '-' in args.ym:
            start_ym, end_ym = args.ym.split('-')
        else:
            start_ym = end_ym = args.ym

        api = AptTradeAPI()

        if args.db_only:
            result = api.get_trades_db_only(
                sgg_cd=args.region,
                start_ym=start_ym,
                end_ym=end_ym,
                apt_name=args.apt_name,
                min_area=args.min_area,
                max_area=args.max_area,
                min_amount=args.min_amount,
                limit=args.limit
            )
        else:
            result = api.get_trades_with_db_first(
                sgg_cd=args.region,
                start_ym=start_ym,
                end_ym=end_ym,
                apt_name=args.apt_name,
                min_area=args.min_area,
                max_area=args.max_area,
                min_amount=args.min_amount,
                limit=args.limit,
                force_api=args.force_api
            )

        # 결과 출력
        results = result['data']
        region_name = meta_db.get_region_name(args.region)
        print(f'\n=== {region_name} 매매 조회 결과 ({len(results)}건, source: {result["source"]}) ===\n')
        print(f'{"아파트명":<20} {"동":<10} {"면적":<8} {"층":<4} {"거래금액":<12} {"거래일":<12}')
        print('-' * 70)
        for tx in results[:50]:  # 최대 50건 출력
            deal_date = f'{tx["deal_year"]}-{tx["deal_month"]:02d}-{tx["deal_day"] or 0:02d}'
            print(f'{tx["apt_nm"]:<20} {tx["umd_nm"] or "":<10} {tx["exclu_use_ar"] or 0:<8.2f} '
                  f'{tx["floor"] or 0:<4} {tx["deal_amount"] or "":<12} {deal_date:<12}')

        if len(results) > 50:
            print(f'\n... 외 {len(results) - 50}건 (--output으로 전체 저장 가능)')

        if args.output and results:
            save_output(results, args.output)

        print(f'\n저장 위치: {data_db.db_path}')
        return

    # 전월세 데이터 (DB-First)
    if args.rents:
        if not args.region or not args.ym:
            print('오류: --rents에는 --region과 --ym이 필요합니다.')
            print('예: python apt_api.py --rents --region 11170 --ym 202501-202512')
            return

        # 기간 파싱
        if '-' in args.ym:
            start_ym, end_ym = args.ym.split('-')
        else:
            start_ym = end_ym = args.ym

        # 전세/월세 필터
        rent_type = None
        if args.jeonse:
            rent_type = 'jeonse'
        elif args.monthly:
            rent_type = 'monthly'

        api = AptRentAPI()

        if args.db_only:
            result = api.get_rents_db_only(
                sgg_cd=args.region,
                start_ym=start_ym,
                end_ym=end_ym,
                apt_name=args.apt_name,
                rent_type=rent_type,
                min_deposit=args.min_deposit,
                limit=args.limit
            )
        else:
            result = api.get_rents_with_db_first(
                sgg_cd=args.region,
                start_ym=start_ym,
                end_ym=end_ym,
                apt_name=args.apt_name,
                rent_type=rent_type,
                min_deposit=args.min_deposit,
                limit=args.limit,
                force_api=args.force_api
            )

        # 결과 출력
        results = result['data']
        region_name = meta_db.get_region_name(args.region)
        title = '전월세'
        if rent_type == 'jeonse':
            title = '전세'
        elif rent_type == 'monthly':
            title = '월세'

        print(f'\n=== {region_name} {title} 조회 결과 ({len(results)}건, source: {result["source"]}) ===\n')
        print(f'{"아파트명":<20} {"동":<10} {"면적":<8} {"층":<4} {"보증금":<12} {"월세":<8} {"거래일":<12} {"유형":<6}')
        print('-' * 90)
        for tx in results[:50]:  # 최대 50건 출력
            deal_date = f'{tx["deal_year"]}-{tx["deal_month"]:02d}-{tx["deal_day"] or 0:02d}'
            deposit = tx["deposit"] or 0
            monthly = tx["monthly_rent"] or 0
            r_type = '전세' if monthly == 0 else '월세'
            print(f'{tx["apt_nm"]:<20} {tx["umd_nm"] or "":<10} {tx["exclu_use_ar"] or 0:<8.2f} '
                  f'{tx["floor"] or 0:<4} {deposit:>10,}  {monthly:>6,}  {deal_date:<12} {r_type:<6}')

        if len(results) > 50:
            print(f'\n... 외 {len(results) - 50}건 (--output으로 전체 저장 가능)')

        if args.output and results:
            save_output(results, args.output)

        print(f'\n저장 위치: {data_db.db_path}')
        return

    # 검색
    if args.search:
        if is_rent_mode:
            results = data_db.search_rents(args.search, sgg_cd=args.region, limit=args.limit)
            print(f'\n=== "{args.search}" 전월세 검색 결과 ({len(results)}건) ===\n')
            print(f'{"아파트명":<20} {"동":<10} {"면적":<8} {"층":<4} {"보증금":<12} {"월세":<8} {"거래일":<12} {"유형":<6}')
            print('-' * 90)
            for tx in results:
                deal_date = f'{tx["deal_year"]}-{tx["deal_month"]:02d}-{tx["deal_day"] or 0:02d}'
                deposit = tx["deposit"] or 0
                monthly = tx["monthly_rent"] or 0
                rent_type = '전세' if monthly == 0 else '월세'
                print(f'{tx["apt_nm"]:<20} {tx["umd_nm"] or "":<10} {tx["exclu_use_ar"] or 0:<8.2f} '
                      f'{tx["floor"] or 0:<4} {deposit:>10,}  {monthly:>6,}  {deal_date:<12} {rent_type:<6}')
        else:
            results = data_db.search(args.search, sgg_cd=args.region, limit=args.limit)
            print(f'\n=== "{args.search}" 매매 검색 결과 ({len(results)}건) ===\n')
            print(f'{"아파트명":<20} {"동":<10} {"면적":<8} {"층":<4} {"거래금액":<12} {"거래일":<12}')
            print('-' * 70)
            for tx in results:
                deal_date = f'{tx["deal_year"]}-{tx["deal_month"]:02d}-{tx["deal_day"] or 0:02d}'
                print(f'{tx["apt_nm"]:<20} {tx["umd_nm"] or "":<10} {tx["exclu_use_ar"] or 0:<8.2f} '
                      f'{tx["floor"] or 0:<4} {tx["deal_amount"] or "":<12} {deal_date:<12}')

        if args.output and results:
            save_output(results, args.output)
        return

    # 고가 거래 TOP
    if args.top:
        if is_rent_mode:
            # 전세/월세 필터
            rent_type = None
            if args.jeonse:
                rent_type = 'jeonse'
            elif args.monthly:
                rent_type = 'monthly'

            results = data_db.get_top_rents(args.top, sgg_cd=args.region, deal_ym=args.ym, rent_type=rent_type)
            title = '고가 전월세 TOP'
            if rent_type == 'jeonse':
                title = '고가 전세 TOP'
            elif rent_type == 'monthly':
                title = '고가 월세 TOP'

            if args.region:
                title += f' ({meta_db.get_region_name(args.region)})'
            if args.ym:
                title += f' {args.ym[:4]}년 {args.ym[4:]}월'

            print(f'\n=== {title} ({len(results)}건) ===\n')
            print(f'{"순위":<4} {"아파트명":<20} {"동":<10} {"면적":<8} {"층":<4} {"보증금":<12} {"월세":<8} {"거래일":<12} {"유형":<6}')
            print('-' * 95)
            for i, tx in enumerate(results, 1):
                deal_date = f'{tx["deal_year"]}-{tx["deal_month"]:02d}-{tx["deal_day"] or 0:02d}'
                deposit = tx["deposit"] or 0
                monthly = tx["monthly_rent"] or 0
                r_type = '전세' if monthly == 0 else '월세'
                print(f'{i:<4} {tx["apt_nm"]:<20} {tx["umd_nm"] or "":<10} {tx["exclu_use_ar"] or 0:<8.2f} '
                      f'{tx["floor"] or 0:<4} {deposit:>10,}  {monthly:>6,}  {deal_date:<12} {r_type:<6}')
        else:
            results = data_db.get_top_trades(args.top, sgg_cd=args.region, deal_ym=args.ym)
            title = '고가 매매 TOP'
            if args.region:
                title += f' ({meta_db.get_region_name(args.region)})'
            if args.ym:
                title += f' {args.ym[:4]}년 {args.ym[4:]}월'

            print(f'\n=== {title} ({len(results)}건) ===\n')
            print(f'{"순위":<4} {"아파트명":<20} {"동":<10} {"면적":<8} {"층":<4} {"거래금액":<12} {"거래일":<12}')
            print('-' * 75)
            for i, tx in enumerate(results, 1):
                deal_date = f'{tx["deal_year"]}-{tx["deal_month"]:02d}-{tx["deal_day"] or 0:02d}'
                print(f'{i:<4} {tx["apt_nm"]:<20} {tx["umd_nm"] or "":<10} {tx["exclu_use_ar"] or 0:<8.2f} '
                      f'{tx["floor"] or 0:<4} {tx["deal_amount"] or "":<12} {deal_date:<12}')

        if args.output and results:
            save_output(results, args.output)
        return

    # 데이터 동기화
    if args.sync:
        if not args.region or not args.ym:
            print('오류: --sync에는 --region과 --ym이 필요합니다.')
            if is_rent_mode:
                print('예: python apt_api.py --rent --sync --region 11170 --ym 202511')
            else:
                print('예: python apt_api.py --sync --region 11170 --ym 202511')
            return

        if is_rent_mode:
            api = AptRentAPI()
            if '-' in args.ym:
                start_ym, end_ym = args.ym.split('-')
                api.sync_region_range(args.region, start_ym, end_ym)
            else:
                api.sync_region_month(args.region, args.ym)
        else:
            api = AptTradeAPI()
            if '-' in args.ym:
                start_ym, end_ym = args.ym.split('-')
                api.sync_region_range(args.region, start_ym, end_ym)
            else:
                api.sync_region_month(args.region, args.ym)

        print(f'\n저장 위치: {data_db.db_path}')
        return

    # 도움말
    parser.print_help()


if __name__ == '__main__':
    main()
