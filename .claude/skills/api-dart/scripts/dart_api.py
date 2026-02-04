# -*- coding: utf-8 -*-
"""
DART OpenAPI Client
금융감독원 전자공시시스템 DART OpenAPI 클라이언트

Author: Claude Code
Version: 1.1.0

Changes in 1.1.0:
- SQLite 메타데이터 DB 지원 (dart_meta_db.py)
- XML 파싱 대신 DB 조회로 성능 향상
- FTS5 전문 검색 지원

Features:
- 공시검색: 기업별/기간별 공시보고서 검색
- 기업개황: 기업 기본정보 조회
- 재무정보: 재무제표, 주요계정 조회
- 고유번호: 기업 고유번호 DB 관리
"""

import os
import sys
import json
import csv
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
    from dart_meta_db import DartMetaDB
    HAS_META_DB = True
except ImportError:
    HAS_META_DB = False


class DartAPI:
    """DART OpenAPI 클라이언트 클래스"""

    # API Base URL
    BASE_URL = "https://opendart.fss.or.kr/api"

    # 보고서 코드
    REPORT_CODES = {
        '1Q': '11013',      # 1분기보고서
        '2Q': '11012',      # 반기보고서
        '3Q': '11014',      # 3분기보고서
        'annual': '11011',  # 사업보고서
    }

    # 공시유형 코드
    DISCLOSURE_TYPES = {
        'A': '정기공시',
        'B': '주요사항보고',
        'C': '발행공시',
        'D': '지분공시',
        'E': '기타공시',
        'F': '외부감사관련',
        'G': '펀드공시',
        'H': '자산유동화',
        'I': '거래소공시',
        'J': '공정위공시',
    }

    # 법인구분 코드
    CORP_CLASS = {
        'Y': '유가증권시장',
        'K': '코스닥',
        'N': '코넥스',
        'E': '기타',
    }

    # 재무제표 구분
    FS_DIV = {
        'OFS': '재무제표',
        'CFS': '연결재무제표',
    }

    # 재무제표 종류
    SJ_DIV = {
        'BS': '재무상태표',
        'IS': '손익계산서',
        'CIS': '포괄손익계산서',
        'CF': '현금흐름표',
        'SCE': '자본변동표',
    }

    def __init__(self, api_key: Optional[str] = None, use_meta_db: bool = True):
        """
        DartAPI 초기화

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
                self.meta_db = DartMetaDB()
                self.meta_db.connect()
            except Exception:
                self.meta_db = None

    def _load_api_key(self) -> str:
        """환경변수에서 API 키 로드"""
        env_paths = [
            Path('.claude/.env'),
            Path('.env'),
            Path.home() / '.dart_api_key',
        ]

        if load_dotenv:
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path)
                    break

        api_key = os.getenv('DART_API_KEY')
        if not api_key:
            print("경고: DART_API_KEY가 설정되지 않았습니다.")
            print("  .claude/.env 파일에 DART_API_KEY=your_key 형식으로 설정하세요.")
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
            return {'status': '999', 'message': 'API 키가 설정되지 않았습니다.'}

        url = f"{self.BASE_URL}/{endpoint}.{format_type}"

        # 기본 파라미터
        request_params = {
            'crtfc_key': self.api_key,
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
                    'status': str(response.status_code),
                    'message': f'HTTP {response.status_code}'
                }

        except requests.exceptions.Timeout:
            return {'status': '998', 'message': '요청 시간 초과'}
        except requests.exceptions.RequestException as e:
            return {'status': '997', 'message': f'요청 실패: {str(e)}'}
        except json.JSONDecodeError as e:
            return {'status': '996', 'message': f'JSON 파싱 실패: {str(e)}'}

    def _check_response(self, result: Dict) -> bool:
        """응답 상태 확인"""
        status = result.get('status', '999')
        if status == '000':
            return True
        elif status == '013':
            print("조회된 데이터가 없습니다.")
        else:
            msg = result.get('message', '알 수 없는 오류')
            print(f"오류 [{status}]: {msg}")
        return False

    # ==================== 고유번호 관리 ====================

    def sync_corp_codes(self, force: bool = False) -> int:
        """
        고유번호 다운로드 및 DB 동기화

        Args:
            force: 강제 동기화 여부

        Returns:
            저장된 기업 수
        """
        if self.meta_db:
            return self.meta_db.download_and_import(force=force)
        else:
            print("메타데이터 DB를 사용할 수 없습니다.")
            print("dart_meta_db.py가 필요합니다.")
            return 0

    def get_corp_code(self, corp_name: str) -> Optional[str]:
        """
        회사명으로 고유번호 조회

        Args:
            corp_name: 회사명 (정확한 명칭 또는 부분 일치)

        Returns:
            고유번호 (8자리) 또는 None
        """
        # 메타DB 우선 사용
        if self.meta_db:
            code = self.meta_db.get_corp_code(corp_name)
            if code:
                return code

            # 부분 매칭 결과가 여러 개인 경우 안내
            results = self.meta_db.search_corp(corp_name, limit=10)
            if len(results) > 1:
                print(f"'{corp_name}'에 대해 {len(results)}개 기업이 검색되었습니다:")
                for r in results[:10]:
                    stock = f" ({r['stock_code']})" if r.get('stock_code') else ""
                    print(f"  - {r['corp_name']}{stock}: {r['corp_code']}")

        return None

    def search_corp(self, keyword: str, listed_only: bool = False) -> List[Dict]:
        """
        키워드로 기업 검색

        Args:
            keyword: 검색 키워드
            listed_only: 상장사만 검색

        Returns:
            검색 결과 리스트
        """
        if self.meta_db:
            return self.meta_db.search_corp(keyword, listed_only=listed_only)

        return []

    def get_db_stats(self) -> Optional[Dict]:
        """DB 통계 조회"""
        if self.meta_db:
            return self.meta_db.get_stats()
        return None

    # ==================== 공시정보 API ====================

    def search_disclosure(
        self,
        corp_code: Optional[str] = None,
        corp_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        pblntf_ty: Optional[str] = None,
        corp_cls: Optional[str] = None,
        last_reprt_at: str = 'N',
        page_no: int = 1,
        page_count: int = 100
    ) -> Dict[str, Any]:
        """
        공시검색

        Args:
            corp_code: 고유번호 (8자리)
            corp_name: 회사명 (corp_code 대신 사용 가능)
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            pblntf_ty: 공시유형 (A~J)
            corp_cls: 법인구분 (Y/K/N/E)
            last_reprt_at: 최종보고서만 검색 (Y/N)
            page_no: 페이지 번호
            page_count: 페이지당 건수 (1-100)

        Returns:
            공시 목록
        """
        # 회사명으로 고유번호 조회
        if corp_name and not corp_code:
            corp_code = self.get_corp_code(corp_name)
            if not corp_code:
                return {'status': '013', 'message': f'회사를 찾을 수 없음: {corp_name}'}

        params = {
            'page_no': str(page_no),
            'page_count': str(page_count),
            'last_reprt_at': last_reprt_at,
        }

        if corp_code:
            params['corp_code'] = corp_code
        if start_date:
            params['bgn_de'] = start_date
        if end_date:
            params['end_de'] = end_date
        if pblntf_ty:
            params['pblntf_ty'] = pblntf_ty
        if corp_cls:
            params['corp_cls'] = corp_cls

        result = self._make_request('list', params)
        return result

    def get_company_info(
        self,
        corp_code: Optional[str] = None,
        corp_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        기업개황 조회

        Args:
            corp_code: 고유번호
            corp_name: 회사명

        Returns:
            기업 기본정보
        """
        if corp_name and not corp_code:
            corp_code = self.get_corp_code(corp_name)
            if not corp_code:
                return {'status': '013', 'message': f'회사를 찾을 수 없음: {corp_name}'}

        params = {'corp_code': corp_code}
        result = self._make_request('company', params)
        return result

    # ==================== 재무정보 API ====================

    def get_financial_statements(
        self,
        corp_code: Optional[str] = None,
        corp_name: Optional[str] = None,
        bsns_year: int = None,
        reprt_code: str = '11011',
        fs_div: str = 'CFS'
    ) -> Dict[str, Any]:
        """
        단일회사 전체 재무제표 조회

        Args:
            corp_code: 고유번호
            corp_name: 회사명
            bsns_year: 사업연도 (기본: 전년도)
            reprt_code: 보고서 코드 (11011=사업보고서, 11012=반기, 11013=1분기, 11014=3분기)
            fs_div: 재무제표 구분 (OFS=재무제표, CFS=연결재무제표)

        Returns:
            재무제표 데이터
        """
        if corp_name and not corp_code:
            corp_code = self.get_corp_code(corp_name)
            if not corp_code:
                return {'status': '013', 'message': f'회사를 찾을 수 없음: {corp_name}'}

        if bsns_year is None:
            bsns_year = datetime.now().year - 1

        params = {
            'corp_code': corp_code,
            'bsns_year': str(bsns_year),
            'reprt_code': reprt_code,
            'fs_div': fs_div,
        }

        result = self._make_request('fnlttSinglAcntAll', params)
        return result

    def get_financial_summary(
        self,
        corp_code: Optional[str] = None,
        corp_name: Optional[str] = None,
        bsns_year: int = None,
        reprt_code: str = '11011'
    ) -> Dict[str, Any]:
        """
        단일회사 주요계정 조회

        Args:
            corp_code: 고유번호
            corp_name: 회사명
            bsns_year: 사업연도
            reprt_code: 보고서 코드

        Returns:
            주요 재무계정
        """
        if corp_name and not corp_code:
            corp_code = self.get_corp_code(corp_name)
            if not corp_code:
                return {'status': '013', 'message': f'회사를 찾을 수 없음: {corp_name}'}

        if bsns_year is None:
            bsns_year = datetime.now().year - 1

        params = {
            'corp_code': corp_code,
            'bsns_year': str(bsns_year),
            'reprt_code': reprt_code,
        }

        result = self._make_request('fnlttSinglAcnt', params)
        return result

    def get_multi_company_financials(
        self,
        corp_codes: List[str],
        bsns_year: int = None,
        reprt_code: str = '11011'
    ) -> Dict[str, Any]:
        """
        다중회사 주요계정 조회

        Args:
            corp_codes: 고유번호 리스트 (최대 100개)
            bsns_year: 사업연도
            reprt_code: 보고서 코드

        Returns:
            다중회사 재무정보
        """
        if bsns_year is None:
            bsns_year = datetime.now().year - 1

        params = {
            'corp_code': ','.join(corp_codes[:100]),
            'bsns_year': str(bsns_year),
            'reprt_code': reprt_code,
        }

        result = self._make_request('fnlttMultiAcnt', params)
        return result

    # 별칭 메서드 (하위 호환성)
    def get_financial_all(
        self,
        corp_code: Optional[str] = None,
        corp_name: Optional[str] = None,
        bsns_year: int = None,
        reprt_code: str = '11011',
        fs_div: str = 'CFS'
    ) -> Dict[str, Any]:
        """
        get_financial_statements의 별칭 (하위 호환성)
        """
        return self.get_financial_statements(
            corp_code=corp_code,
            corp_name=corp_name,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div
        )

    def get_dividend_history(
        self,
        corp_name: str,
        start_year: int = None,
        end_year: int = None,
        fs_div: str = 'OFS'
    ) -> Dict[str, int]:
        """
        기업의 연도별 배당금 지급 내역 조회

        Args:
            corp_name: 회사명
            start_year: 시작 연도 (기본: 5년 전)
            end_year: 종료 연도 (기본: 현재 연도)
            fs_div: 재무제표 구분 (OFS=개별, CFS=연결)

        Returns:
            연도별 배당금액 딕셔너리 {연도: 금액(원)}
        """
        if end_year is None:
            end_year = datetime.now().year
        if start_year is None:
            start_year = end_year - 5

        dividend_data = {}
        years_to_query = list(range(end_year, start_year - 1, -1))

        for year in years_to_query:
            try:
                result = self.get_financial_statements(
                    corp_name=corp_name,
                    bsns_year=year,
                    fs_div=fs_div
                )
                if result and 'list' in result:
                    for item in result['list']:
                        acct = item.get('account_nm', '')
                        if '배당금' in acct and '지급' in acct:
                            # 당기 금액
                            thstrm = item.get('thstrm_amount', '').replace(',', '')
                            if thstrm and thstrm not in ['-', '']:
                                try:
                                    dividend_data[year] = int(thstrm)
                                except ValueError:
                                    pass
                            # 전기 금액
                            frmtrm = item.get('frmtrm_amount', '').replace(',', '')
                            if frmtrm and frmtrm not in ['-', '']:
                                try:
                                    dividend_data[year - 1] = int(frmtrm)
                                except ValueError:
                                    pass
                            # 전전기 금액
                            bfefrmtrm = item.get('bfefrmtrm_amount', '').replace(',', '') if item.get('bfefrmtrm_amount') else ''
                            if bfefrmtrm and bfefrmtrm not in ['-', '']:
                                try:
                                    dividend_data[year - 2] = int(bfefrmtrm)
                                except ValueError:
                                    pass
                            break
            except Exception:
                continue

        return dividend_data

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
            if isinstance(data, dict):
                if 'list' in data:
                    rows = data['list']
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


# ==================== CLI 함수 ====================

def print_disclosure_list(api: DartAPI, args):
    """공시 목록 출력"""
    result = api.search_disclosure(
        corp_name=args.company,
        start_date=args.start_date,
        end_date=args.end_date,
        pblntf_ty=args.disclosure_type,
        corp_cls=args.corp_cls,
        page_count=args.limit
    )

    if not api._check_response(result):
        return result

    items = result.get('list', [])
    print(f"\n=== 공시 검색 결과 ({len(items)}건) ===")
    print(f"{'접수일':<12} {'회사명':<20} {'보고서명':<40}")
    print("-" * 75)

    for item in items:
        rcept_dt = item.get('rcept_dt') or ''
        corp_name = (item.get('corp_name') or '')[:18]
        report_nm = (item.get('report_nm') or '')[:38]
        print(f"{rcept_dt:<12} {corp_name:<20} {report_nm:<40}")

    return result


def print_company_info(api: DartAPI, args):
    """기업개황 출력"""
    result = api.get_company_info(corp_name=args.company)

    if not api._check_response(result):
        return result

    print(f"\n=== {result.get('corp_name', '')} 기업개황 ===")
    info_fields = [
        ('corp_name', '정식명칭'),
        ('corp_name_eng', '영문명칭'),
        ('ceo_nm', '대표자'),
        ('corp_cls', '법인구분'),
        ('jurir_no', '법인등록번호'),
        ('bizr_no', '사업자등록번호'),
        ('adres', '주소'),
        ('hm_url', '홈페이지'),
        ('ir_url', 'IR홈페이지'),
        ('phn_no', '전화번호'),
        ('induty_code', '업종코드'),
        ('est_dt', '설립일'),
        ('acc_mt', '결산월'),
    ]

    for key, label in info_fields:
        value = result.get(key, '')
        if value:
            # 법인구분 변환
            if key == 'corp_cls':
                value = api.CORP_CLASS.get(value, value)
            print(f"  {label}: {value}")

    return result


def print_financials(api: DartAPI, args):
    """재무제표 출력"""
    if args.summary:
        result = api.get_financial_summary(
            corp_name=args.company,
            bsns_year=args.year,
            reprt_code=api.REPORT_CODES.get(args.report, '11011')
        )
    else:
        result = api.get_financial_statements(
            corp_name=args.company,
            bsns_year=args.year,
            reprt_code=api.REPORT_CODES.get(args.report, '11011'),
            fs_div=args.fs_div
        )

    if not api._check_response(result):
        return result

    items = result.get('list', [])
    report_type = '주요계정' if args.summary else '전체 재무제표'
    fs_name = api.FS_DIV.get(args.fs_div, args.fs_div)

    print(f"\n=== {args.company} {args.year}년 {report_type} ({fs_name}) ===")

    # 재무제표 종류별 그룹화
    by_sj_div = {}
    for item in items:
        sj_div = item.get('sj_div', 'etc')
        if sj_div not in by_sj_div:
            by_sj_div[sj_div] = []
        by_sj_div[sj_div].append(item)

    for sj_div, sj_items in by_sj_div.items():
        sj_name = api.SJ_DIV.get(sj_div, sj_div)
        print(f"\n[{sj_name}]")
        print(f"{'계정명':<30} {'당기금액':>20} {'전기금액':>20}")
        print("-" * 72)

        for item in sj_items[:20]:  # 상위 20개만 출력
            account = (item.get('account_nm') or '')[:28]
            thstrm = item.get('thstrm_amount') or '-'
            frmtrm = item.get('frmtrm_amount') or '-'

            # 금액 포맷팅
            try:
                thstrm = f"{int(thstrm):,}" if thstrm and thstrm != '-' else '-'
            except:
                pass
            try:
                frmtrm = f"{int(frmtrm):,}" if frmtrm and frmtrm != '-' else '-'
            except:
                pass

            print(f"{account:<30} {thstrm:>20} {frmtrm:>20}")

    return result


def print_corp_search(api: DartAPI, args):
    """기업 검색 결과 출력"""
    results = api.search_corp(args.search, listed_only=args.listed_only)

    print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
    print(f"{'회사명':<30} {'종목코드':<10} {'고유번호':<12}")
    print("-" * 55)

    for item in results[:50]:  # 상위 50개
        name = item['corp_name'][:28]
        stock = item['stock_code'] or '-'
        code = item['corp_code']
        print(f"{name:<30} {stock:<10} {code:<12}")

    return results


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='DART 전자공시시스템 OpenAPI 클라이언트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 고유번호 DB 동기화
  python dart_api.py --sync

  # 기업 검색
  python dart_api.py --search "삼성전자"

  # 기업개황 조회
  python dart_api.py --company "삼성전자" --info

  # 공시 검색
  python dart_api.py --company "삼성전자" --disclosure --start-date 20240101

  # 재무제표 조회
  python dart_api.py --company "삼성전자" --financials --year 2023

  # 주요계정 조회
  python dart_api.py --company "삼성전자" --financials --summary --year 2023

  # DB 통계
  python dart_api.py --stats
        """
    )

    # 조회 유형
    parser.add_argument('--sync', action='store_true',
                        help='고유번호 다운로드 및 DB 동기화')
    parser.add_argument('--force', action='store_true',
                        help='강제 동기화 (--sync와 함께 사용)')
    parser.add_argument('--stats', action='store_true',
                        help='DB 통계 출력')
    parser.add_argument('--search', type=str,
                        help='기업명 검색')
    parser.add_argument('--listed-only', action='store_true',
                        help='상장사만 검색')
    parser.add_argument('--disclosure', action='store_true',
                        help='공시 검색')
    parser.add_argument('--info', action='store_true',
                        help='기업개황 조회')
    parser.add_argument('--financials', action='store_true',
                        help='재무제표 조회')
    parser.add_argument('--summary', action='store_true',
                        help='주요계정만 조회')

    # 필터 옵션
    parser.add_argument('--company', '-c', type=str,
                        help='회사명')
    parser.add_argument('--corp-code', type=str,
                        help='고유번호 (8자리)')
    parser.add_argument('--start-date', type=str,
                        help='시작일 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str,
                        help='종료일 (YYYYMMDD)')
    parser.add_argument('--disclosure-type', type=str, choices=list('ABCDEFGHIJ'),
                        help='공시유형 (A~J)')
    parser.add_argument('--corp-cls', type=str, choices=['Y', 'K', 'N', 'E'],
                        help='법인구분 (Y=유가증권, K=코스닥, N=코넥스, E=기타)')

    # 재무제표 옵션
    parser.add_argument('--year', type=int, default=datetime.now().year - 1,
                        help='사업연도 (기본: 전년도)')
    parser.add_argument('--report', type=str, default='annual',
                        choices=['1Q', '2Q', '3Q', 'annual'],
                        help='보고서 유형 (기본: annual)')
    parser.add_argument('--fs-div', type=str, default='CFS',
                        choices=['OFS', 'CFS'],
                        help='재무제표 구분 (OFS=개별, CFS=연결)')

    # 출력 옵션
    parser.add_argument('--limit', type=int, default=100,
                        help='조회 건수 (기본: 100)')
    parser.add_argument('--output', '-o', type=str,
                        help='결과 저장 파일 (json/csv)')
    parser.add_argument('--api-key', type=str,
                        help='API 인증키')

    args = parser.parse_args()

    # API 클라이언트 초기화
    api = DartAPI(api_key=args.api_key)

    result = None

    if args.sync:
        api.sync_corp_codes(force=args.force)

    elif args.stats:
        stats = api.get_db_stats()
        if stats:
            print("\n=== DART 메타DB 통계 ===")
            print(f"전체 기업: {stats['total']:,}개")
            print(f"  - 상장사: {stats['listed']:,}개")
            print(f"  - 비상장: {stats['unlisted']:,}개")
            if stats.get('last_update'):
                print(f"마지막 업데이트: {stats['last_update'][:19]}")
        else:
            print("DB가 초기화되지 않았습니다. --sync를 먼저 실행하세요.")

    elif args.search:
        result = print_corp_search(api, args)

    elif args.info and args.company:
        result = print_company_info(api, args)

    elif args.disclosure:
        result = print_disclosure_list(api, args)

    elif args.financials and args.company:
        result = print_financials(api, args)

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
