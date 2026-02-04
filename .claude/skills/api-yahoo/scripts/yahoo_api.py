# -*- coding: utf-8 -*-
"""
Yahoo Finance API Client
yfinance 라이브러리를 통한 주식 데이터 조회

Author: Claude Code
Version: 2.0.0

Features:
- 주가 데이터 조회 (OHLCV)
- 재무제표 조회 (손익계산서, 대차대조표, 현금흐름표)
- 배당 이력 조회
- 기업 정보 조회
- SQLite DB 저장 (yahoo.db) - NEW in v2.0
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

# 한글 출력 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import pandas as pd
except ImportError:
    print("pandas 패키지가 필요합니다: pip install pandas")
    sys.exit(1)

try:
    import yfinance as yf
except ImportError:
    print("yfinance 패키지가 필요합니다: pip install yfinance")
    sys.exit(1)

# 메타DB 임포트
try:
    from yahoo_meta_db import YahooMetaDB
    HAS_META_DB = True
except ImportError:
    HAS_META_DB = False

# 데이터 DB 경로 (R-DB/yahoo.db)
DATA_DB_PATH = Path(__file__).parents[4] / '3_Resources' / 'R-DB' / 'yahoo.db'

# DB 스키마
DB_SCHEMA = """
-- 주가 데이터 테이블
CREATE TABLE IF NOT EXISTS price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adj_close REAL,
    volume INTEGER,
    dividends REAL,
    stock_splits REAL,
    collected_at TEXT,
    UNIQUE(ticker, date)
);

-- 재무제표 데이터 테이블
CREATE TABLE IF NOT EXISTS financial_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    report_type TEXT NOT NULL,
    fiscal_date TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    currency TEXT,
    period_type TEXT,
    collected_at TEXT,
    UNIQUE(ticker, report_type, fiscal_date, metric_name)
);

-- 배당 데이터 테이블
CREATE TABLE IF NOT EXISTS dividend_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    dividend REAL,
    collected_at TEXT,
    UNIQUE(ticker, date)
);

-- 수집 로그 테이블
CREATE TABLE IF NOT EXISTS collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,
    ticker TEXT,
    period TEXT,
    status TEXT NOT NULL,
    record_count INTEGER,
    error_message TEXT,
    collected_at TEXT NOT NULL
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_price_ticker ON price_data(ticker);
CREATE INDEX IF NOT EXISTS idx_price_date ON price_data(date);
CREATE INDEX IF NOT EXISTS idx_financial_ticker ON financial_data(ticker);
CREATE INDEX IF NOT EXISTS idx_financial_type ON financial_data(report_type);
CREATE INDEX IF NOT EXISTS idx_dividend_ticker ON dividend_data(ticker);
"""


class YahooAPI:
    """Yahoo Finance API 클라이언트 클래스"""

    # 한국 시장 접미사
    MARKET_SUFFIX = {
        'kospi': '.KS',
        'kosdaq': '.KQ',
        'nasdaq': '',
        'nyse': '',
        'us': '',
    }

    # 기간 옵션 (yfinance 지원)
    VALID_PERIODS = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '3y', '5y', '10y', 'ytd', 'max']

    # 간격 옵션
    VALID_INTERVALS = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']

    def __init__(self, use_meta_db: bool = True):
        """
        YahooAPI 초기화

        Args:
            use_meta_db: 메타데이터 DB 사용 여부
        """
        # 데이터 디렉토리 (스킬 내부)
        self.skill_data_dir = Path(__file__).parent.parent / 'data'
        self.skill_data_dir.mkdir(exist_ok=True)

        # 출력 디렉토리 (볼트 내 Attachments)
        self.output_dir = self._get_output_dir()

        # 메타DB 초기화
        self.meta_db = None
        if use_meta_db and HAS_META_DB:
            try:
                self.meta_db = YahooMetaDB()
                self.meta_db.connect()
            except Exception:
                self.meta_db = None

    def _get_output_dir(self) -> Path:
        """출력 디렉토리 경로 반환 (9_Attachments/Data/yahoo/)"""
        # 볼트 루트 찾기
        current = Path(__file__).resolve()
        for _ in range(10):
            if current.parent == current:
                break
            current = current.parent

            # 볼트 식별자 확인
            if (current / 'CLAUDE.md').exists() or (current / '.obsidian').exists():
                output_dir = current / '9_Attachments' / 'Data' / 'yahoo'
                output_dir.mkdir(parents=True, exist_ok=True)
                return output_dir

        # 찾지 못하면 스킬 내부에 저장
        fallback = Path(__file__).parent.parent / 'data' / 'output'
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    # ==================== 티커 처리 ====================

    def normalize_ticker(self, ticker: str, market: Optional[str] = None) -> str:
        """
        티커 정규화 (한국 종목 자동 감지)

        Args:
            ticker: 종목 코드 또는 심볼
            market: 시장 지정 (kospi/kosdaq/us, 미지정시 자동 감지)

        Returns:
            정규화된 티커 (예: 005930.KS)
        """
        ticker = ticker.strip().upper()

        # 이미 접미사가 있으면 그대로 반환
        if ticker.endswith('.KS') or ticker.endswith('.KQ'):
            return ticker

        # 숫자 6자리면 한국 종목으로 간주
        if ticker.isdigit() and len(ticker) == 6:
            if market:
                suffix = self.MARKET_SUFFIX.get(market.lower(), '.KS')
            else:
                # 메타DB에서 시장 조회
                if self.meta_db:
                    market_type = self.meta_db.get_market_type(ticker)
                    suffix = self.MARKET_SUFFIX.get(market_type, '.KS')
                else:
                    suffix = '.KS'  # 기본값 코스피
            return f"{ticker}{suffix}"

        return ticker

    def resolve_ticker(self, name_or_code: str) -> Optional[str]:
        """
        종목명 또는 코드로 티커 조회

        Args:
            name_or_code: 종목명 (삼성전자) 또는 코드 (005930)

        Returns:
            정규화된 티커 또는 None
        """
        # 이미 티커 형식이면 정규화만
        if name_or_code.endswith('.KS') or name_or_code.endswith('.KQ'):
            return name_or_code

        # 숫자 6자리면 한국 종목 코드
        if name_or_code.isdigit() and len(name_or_code) == 6:
            return self.normalize_ticker(name_or_code)

        # 영문이면 미국 종목으로 간주
        if name_or_code.isascii() and name_or_code.isalpha():
            return name_or_code.upper()

        # 한글이면 메타DB에서 검색
        if self.meta_db:
            results = self.meta_db.search_stock(name_or_code, limit=1)
            if results:
                return results[0]['yahoo_ticker']

        return None

    # ==================== 주가 데이터 ====================

    def get_price_history(
        self,
        ticker: str,
        period: str = '1y',
        interval: str = '1d',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        save_to_db: bool = True
    ) -> pd.DataFrame:
        """
        주가 이력 조회 (OHLCV)

        Args:
            ticker: 티커 심볼
            period: 조회 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 데이터 간격 (1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo)
            start_date: 시작일 (YYYY-MM-DD) - period 대신 사용
            end_date: 종료일 (YYYY-MM-DD)
            save_to_db: DB 자동 저장 여부 (기본: True)

        Returns:
            OHLCV DataFrame (date, open, high, low, close, volume, dividends, stock_splits)
        """
        ticker = self.normalize_ticker(ticker)
        stock = yf.Ticker(ticker)

        try:
            if start_date:
                df = stock.history(start=start_date, end=end_date, interval=interval)
            else:
                df = stock.history(period=period, interval=interval)

            if df.empty:
                print(f"주가 데이터 없음: {ticker}")
                return pd.DataFrame()

            # 인덱스를 열로 변환
            df.reset_index(inplace=True)

            # 열 이름 정규화 (소문자, 공백 → 언더스코어)
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]

            # DB 자동 저장 (기본값)
            if save_to_db:
                self.save_price_to_db(ticker, df)

            return df

        except Exception as e:
            print(f"주가 조회 실패 [{ticker}]: {e}")
            return pd.DataFrame()

    # ==================== 재무제표 ====================

    def get_income_statement(
        self,
        ticker: str,
        quarterly: bool = False
    ) -> pd.DataFrame:
        """
        손익계산서 조회

        Args:
            ticker: 티커 심볼
            quarterly: 분기별 (True) 또는 연간 (False)

        Returns:
            손익계산서 DataFrame
        """
        ticker = self.normalize_ticker(ticker)
        stock = yf.Ticker(ticker)

        try:
            if quarterly:
                df = stock.quarterly_income_stmt
            else:
                df = stock.income_stmt

            if df is None or df.empty:
                print(f"손익계산서 데이터 없음: {ticker}")
                return pd.DataFrame()

            # 전치하여 날짜를 행으로
            df = df.T
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'date'}, inplace=True)

            return df

        except Exception as e:
            print(f"손익계산서 조회 실패 [{ticker}]: {e}")
            return pd.DataFrame()

    def get_balance_sheet(
        self,
        ticker: str,
        quarterly: bool = False
    ) -> pd.DataFrame:
        """
        대차대조표 조회

        Args:
            ticker: 티커 심볼
            quarterly: 분기별 (True) 또는 연간 (False)

        Returns:
            대차대조표 DataFrame
        """
        ticker = self.normalize_ticker(ticker)
        stock = yf.Ticker(ticker)

        try:
            if quarterly:
                df = stock.quarterly_balance_sheet
            else:
                df = stock.balance_sheet

            if df is None or df.empty:
                print(f"대차대조표 데이터 없음: {ticker}")
                return pd.DataFrame()

            df = df.T
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'date'}, inplace=True)

            return df

        except Exception as e:
            print(f"대차대조표 조회 실패 [{ticker}]: {e}")
            return pd.DataFrame()

    def get_cash_flow(
        self,
        ticker: str,
        quarterly: bool = False
    ) -> pd.DataFrame:
        """
        현금흐름표 조회

        Args:
            ticker: 티커 심볼
            quarterly: 분기별 (True) 또는 연간 (False)

        Returns:
            현금흐름표 DataFrame
        """
        ticker = self.normalize_ticker(ticker)
        stock = yf.Ticker(ticker)

        try:
            if quarterly:
                df = stock.quarterly_cashflow
            else:
                df = stock.cashflow

            if df is None or df.empty:
                print(f"현금흐름표 데이터 없음: {ticker}")
                return pd.DataFrame()

            df = df.T
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'date'}, inplace=True)

            return df

        except Exception as e:
            print(f"현금흐름표 조회 실패 [{ticker}]: {e}")
            return pd.DataFrame()

    def get_all_financials(
        self,
        ticker: str,
        quarterly: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        전체 재무제표 조회

        Args:
            ticker: 티커 심볼
            quarterly: 분기별 (True) 또는 연간 (False)

        Returns:
            {'income': DataFrame, 'balance': DataFrame, 'cashflow': DataFrame}
        """
        return {
            'income': self.get_income_statement(ticker, quarterly),
            'balance': self.get_balance_sheet(ticker, quarterly),
            'cashflow': self.get_cash_flow(ticker, quarterly),
        }

    # ==================== 배당 ====================

    def get_dividends(self, ticker: str) -> pd.DataFrame:
        """
        배당 이력 조회

        Args:
            ticker: 티커 심볼

        Returns:
            배당 DataFrame (date, dividend)
        """
        ticker = self.normalize_ticker(ticker)
        stock = yf.Ticker(ticker)

        try:
            dividends = stock.dividends

            if dividends is None or dividends.empty:
                print(f"배당 데이터 없음: {ticker}")
                return pd.DataFrame()

            df = dividends.reset_index()
            df.columns = ['date', 'dividend']

            return df

        except Exception as e:
            print(f"배당 조회 실패 [{ticker}]: {e}")
            return pd.DataFrame()

    # ==================== 기업 정보 ====================

    def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """
        기업 기본 정보 조회

        Args:
            ticker: 티커 심볼

        Returns:
            기업 정보 딕셔너리
        """
        ticker = self.normalize_ticker(ticker)
        stock = yf.Ticker(ticker)

        try:
            info = stock.info

            if not info:
                print(f"기업 정보 없음: {ticker}")
                return {}

            # 주요 필드 추출
            key_fields = [
                'shortName', 'longName', 'symbol', 'exchange',
                'sector', 'industry', 'country',
                'marketCap', 'enterpriseValue',
                'trailingPE', 'forwardPE', 'priceToBook',
                'dividendYield', 'payoutRatio',
                'fiftyTwoWeekHigh', 'fiftyTwoWeekLow',
                'regularMarketPrice', 'regularMarketVolume',
                'currency', 'website'
            ]

            return {k: info.get(k) for k in key_fields if info.get(k) is not None}

        except Exception as e:
            print(f"기업 정보 조회 실패 [{ticker}]: {e}")
            return {}

    # ==================== 내보내기 ====================

    def export_to_csv(
        self,
        data: Union[pd.DataFrame, Dict, List],
        output_path: str,
        encoding: str = 'utf-8-sig'
    ) -> bool:
        """
        CSV 내보내기

        Args:
            data: 저장할 데이터
            output_path: 저장 경로
            encoding: 인코딩 (기본 utf-8-sig, Excel 호환)

        Returns:
            성공 여부
        """
        try:
            if isinstance(data, pd.DataFrame):
                data.to_csv(output_path, index=False, encoding=encoding)
            elif isinstance(data, dict):
                pd.DataFrame([data]).to_csv(output_path, index=False, encoding=encoding)
            else:
                pd.DataFrame(data).to_csv(output_path, index=False, encoding=encoding)

            print(f"CSV 저장 완료: {output_path}")
            return True
        except Exception as e:
            print(f"CSV 저장 실패: {e}")
            return False

    def export_to_json(
        self,
        data: Union[pd.DataFrame, Dict, List],
        output_path: str
    ) -> bool:
        """
        JSON 내보내기

        Args:
            data: 저장할 데이터
            output_path: 저장 경로

        Returns:
            성공 여부
        """
        try:
            if isinstance(data, pd.DataFrame):
                data.to_json(
                    output_path,
                    orient='records',
                    date_format='iso',
                    force_ascii=False,
                    indent=2
                )
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            print(f"JSON 저장 완료: {output_path}")
            return True
        except Exception as e:
            print(f"JSON 저장 실패: {e}")
            return False

    def auto_save(
        self,
        data: pd.DataFrame,
        ticker: str,
        data_type: str,
        format: str = 'csv'
    ) -> Optional[str]:
        """
        자동 저장 (9_Attachments/Data/yahoo/)

        Args:
            data: 저장할 데이터
            ticker: 티커
            data_type: 데이터 유형 (price/income/balance/cashflow/dividends)
            format: 파일 형식 (csv/json)

        Returns:
            저장된 파일 경로
        """
        if data.empty:
            print(f"저장할 데이터가 없습니다: {ticker} ({data_type})")
            return None

        # 서브 폴더 매핑
        subfolder_map = {
            'price': 'prices',
            'income': 'financials',
            'balance': 'financials',
            'cashflow': 'financials',
            'dividends': 'dividends',
        }

        subfolder = subfolder_map.get(data_type, 'misc')
        save_dir = self.output_dir / subfolder
        save_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성 (티커의 . → _)
        ticker_clean = ticker.replace('.', '_')
        filename = f"{ticker_clean}_{data_type}.{format}"
        filepath = save_dir / filename

        if format == 'csv':
            self.export_to_csv(data, str(filepath))
        else:
            self.export_to_json(data, str(filepath))

        return str(filepath)

    # ==================== 유틸리티 ====================

    def print_dataframe(self, df: pd.DataFrame, title: str = "", max_rows: int = 20):
        """DataFrame 출력 헬퍼"""
        if df.empty:
            print(f"{title}: 데이터 없음")
            return

        if title:
            print(f"\n=== {title} ===")

        # pandas 출력 옵션 설정
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 30)

        print(df.head(max_rows).to_string(index=False))

        if len(df) > max_rows:
            print(f"... ({len(df)}행 중 {max_rows}행 표시)")

    # ==================== 데이터 DB 저장 ====================

    def _get_data_db_connection(self) -> sqlite3.Connection:
        """데이터 DB 연결 (없으면 생성)"""
        DATA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DATA_DB_PATH))

        # 스키마 초기화
        conn.executescript(DB_SCHEMA)
        conn.commit()

        return conn

    def _log_collection(
        self,
        conn: sqlite3.Connection,
        data_type: str,
        ticker: str,
        period: str,
        status: str,
        record_count: int = 0,
        error_message: str = None
    ):
        """수집 로그 기록"""
        conn.execute('''
            INSERT INTO collection_log
            (data_type, ticker, period, status, record_count, error_message, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data_type, ticker, period, status, record_count, error_message,
              datetime.now().isoformat()))
        conn.commit()

    def save_price_to_db(self, ticker: str, df: pd.DataFrame) -> int:
        """
        주가 데이터 DB 저장

        Args:
            ticker: 티커 심볼
            df: 주가 DataFrame (date, open, high, low, close, volume 등)

        Returns:
            저장된 레코드 수
        """
        if df.empty:
            return 0

        conn = self._get_data_db_connection()
        collected_at = datetime.now().isoformat()
        saved_count = 0

        try:
            cursor = conn.cursor()

            for _, row in df.iterrows():
                # 날짜 처리 (datetime → string)
                date_val = row.get('date', row.get('Date'))
                if hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)[:10]

                cursor.execute('''
                    INSERT OR REPLACE INTO price_data
                    (ticker, date, open, high, low, close, adj_close, volume,
                     dividends, stock_splits, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ticker,
                    date_str,
                    row.get('open'),
                    row.get('high'),
                    row.get('low'),
                    row.get('close'),
                    row.get('adj_close', row.get('close')),
                    row.get('volume'),
                    row.get('dividends', 0),
                    row.get('stock_splits', 0),
                    collected_at
                ))
                saved_count += 1

            conn.commit()

            # 로그 기록
            self._log_collection(
                conn, 'price', ticker, f"{len(df)} days",
                'success', saved_count
            )

            print(f"DB 저장 완료: {ticker} 주가 {saved_count}건 → yahoo.db")
            return saved_count

        except Exception as e:
            self._log_collection(
                conn, 'price', ticker, '',
                'error', 0, str(e)
            )
            print(f"DB 저장 실패 [{ticker}]: {e}")
            return 0
        finally:
            conn.close()

    def save_financial_to_db(
        self,
        ticker: str,
        report_type: str,
        df: pd.DataFrame,
        period_type: str = 'annual'
    ) -> int:
        """
        재무제표 데이터 DB 저장

        Args:
            ticker: 티커 심볼
            report_type: 보고서 유형 (income/balance/cashflow)
            df: 재무제표 DataFrame
            period_type: 기간 유형 (annual/quarterly)

        Returns:
            저장된 레코드 수
        """
        if df.empty:
            return 0

        conn = self._get_data_db_connection()
        collected_at = datetime.now().isoformat()
        saved_count = 0

        try:
            cursor = conn.cursor()

            for _, row in df.iterrows():
                # 날짜 처리
                date_val = row.get('date', row.get('Date'))
                if hasattr(date_val, 'strftime'):
                    fiscal_date = date_val.strftime('%Y-%m-%d')
                else:
                    fiscal_date = str(date_val)[:10]

                # 각 컬럼을 metric으로 저장
                for col in df.columns:
                    if col.lower() == 'date':
                        continue

                    metric_value = row[col]
                    if pd.isna(metric_value):
                        continue

                    cursor.execute('''
                        INSERT OR REPLACE INTO financial_data
                        (ticker, report_type, fiscal_date, metric_name,
                         metric_value, currency, period_type, collected_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ticker,
                        report_type,
                        fiscal_date,
                        col,
                        float(metric_value) if metric_value else None,
                        'KRW' if ticker.endswith(('.KS', '.KQ')) else 'USD',
                        period_type,
                        collected_at
                    ))
                    saved_count += 1

            conn.commit()

            # 로그 기록
            self._log_collection(
                conn, f'financial_{report_type}', ticker, period_type,
                'success', saved_count
            )

            print(f"DB 저장 완료: {ticker} {report_type} {saved_count}건 → yahoo.db")
            return saved_count

        except Exception as e:
            self._log_collection(
                conn, f'financial_{report_type}', ticker, period_type,
                'error', 0, str(e)
            )
            print(f"DB 저장 실패 [{ticker} {report_type}]: {e}")
            return 0
        finally:
            conn.close()

    def save_dividend_to_db(self, ticker: str, df: pd.DataFrame) -> int:
        """
        배당 데이터 DB 저장

        Args:
            ticker: 티커 심볼
            df: 배당 DataFrame (date, dividend)

        Returns:
            저장된 레코드 수
        """
        if df.empty:
            return 0

        conn = self._get_data_db_connection()
        collected_at = datetime.now().isoformat()
        saved_count = 0

        try:
            cursor = conn.cursor()

            for _, row in df.iterrows():
                # 날짜 처리
                date_val = row.get('date', row.get('Date'))
                if hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)[:10]

                cursor.execute('''
                    INSERT OR REPLACE INTO dividend_data
                    (ticker, date, dividend, collected_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    ticker,
                    date_str,
                    row.get('dividend'),
                    collected_at
                ))
                saved_count += 1

            conn.commit()

            # 로그 기록
            self._log_collection(
                conn, 'dividend', ticker, f"{len(df)} records",
                'success', saved_count
            )

            print(f"DB 저장 완료: {ticker} 배당 {saved_count}건 → yahoo.db")
            return saved_count

        except Exception as e:
            self._log_collection(
                conn, 'dividend', ticker, '',
                'error', 0, str(e)
            )
            print(f"DB 저장 실패 [{ticker}]: {e}")
            return 0
        finally:
            conn.close()

    def get_data_db_stats(self) -> Dict[str, Any]:
        """데이터 DB 통계 조회"""
        if not DATA_DB_PATH.exists():
            return {'error': 'DB 파일이 없습니다.'}

        conn = self._get_data_db_connection()

        try:
            cursor = conn.cursor()
            stats = {}

            # 주가 데이터 통계
            cursor.execute('SELECT COUNT(*) FROM price_data')
            stats['price_records'] = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(DISTINCT ticker) FROM price_data')
            stats['price_tickers'] = cursor.fetchone()[0]

            # 재무제표 통계
            cursor.execute('SELECT COUNT(*) FROM financial_data')
            stats['financial_records'] = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(DISTINCT ticker) FROM financial_data')
            stats['financial_tickers'] = cursor.fetchone()[0]

            # 배당 통계
            cursor.execute('SELECT COUNT(*) FROM dividend_data')
            stats['dividend_records'] = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(DISTINCT ticker) FROM dividend_data')
            stats['dividend_tickers'] = cursor.fetchone()[0]

            # 수집 로그 통계
            cursor.execute('''
                SELECT data_type, COUNT(*), MAX(collected_at)
                FROM collection_log
                WHERE status = 'success'
                GROUP BY data_type
            ''')
            stats['collection_by_type'] = {
                row[0]: {'count': row[1], 'last_collected': row[2]}
                for row in cursor.fetchall()
            }

            # DB 파일 크기
            stats['db_size_mb'] = round(DATA_DB_PATH.stat().st_size / (1024 * 1024), 2)

            return stats

        except Exception as e:
            return {'error': str(e)}
        finally:
            conn.close()

    def query_db(
        self,
        data_type: str,
        ticker: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        데이터 DB 조회

        Args:
            data_type: 데이터 유형 (price/financial/dividend)
            ticker: 티커 필터 (선택)
            start_date: 시작일 필터 (선택)
            end_date: 종료일 필터 (선택)
            limit: 최대 결과 수

        Returns:
            조회 결과 DataFrame
        """
        if not DATA_DB_PATH.exists():
            print("DB 파일이 없습니다.")
            return pd.DataFrame()

        conn = self._get_data_db_connection()

        try:
            table_map = {
                'price': 'price_data',
                'financial': 'financial_data',
                'dividend': 'dividend_data'
            }

            table = table_map.get(data_type)
            if not table:
                print(f"지원하지 않는 데이터 유형: {data_type}")
                return pd.DataFrame()

            date_col = 'fiscal_date' if data_type == 'financial' else 'date'

            query = f"SELECT * FROM {table} WHERE 1=1"
            params = []

            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)

            if start_date:
                query += f" AND {date_col} >= ?"
                params.append(start_date)

            if end_date:
                query += f" AND {date_col} <= ?"
                params.append(end_date)

            query += f" ORDER BY {date_col} DESC LIMIT ?"
            params.append(limit)

            df = pd.read_sql_query(query, conn, params=params)
            return df

        except Exception as e:
            print(f"DB 조회 실패: {e}")
            return pd.DataFrame()
        finally:
            conn.close()


def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description='Yahoo Finance 주식 데이터 클라이언트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 한국 종목 DB 동기화
  python yahoo_api.py --sync-kr

  # 종목 검색
  python yahoo_api.py --search "삼성"

  # 주가 조회 (1년)
  python yahoo_api.py --ticker AAPL --price --period 1y

  # 한국 종목 주가
  python yahoo_api.py --ticker 005930 --price --period 6mo

  # 특정 기간 주가
  python yahoo_api.py --ticker AAPL --price --start-date 2024-01-01 --end-date 2024-12-31

  # 재무제표 (연간)
  python yahoo_api.py --ticker AAPL --financials

  # 재무제표 (분기)
  python yahoo_api.py --ticker AAPL --financials --quarterly

  # 배당 이력
  python yahoo_api.py --ticker AAPL --dividends

  # 기업 정보
  python yahoo_api.py --ticker AAPL --info

  # 자동 저장 (9_Attachments/Data/yahoo/)
  python yahoo_api.py --ticker AAPL --price --period 1y --save

  # 특정 파일로 저장
  python yahoo_api.py --ticker AAPL --price --output result.csv

  # === DB 저장 (yahoo.db) ===
  # 주가 데이터 DB 저장
  python yahoo_api.py --ticker 005930 --price --period 1y --save-db

  # 재무제표 DB 저장
  python yahoo_api.py --ticker AAPL --financials --save-db

  # DB 통계 확인
  python yahoo_api.py --data-db-stats

  # DB 조회 (저장된 주가 데이터)
  python yahoo_api.py --query-db price --ticker 005930.KS --limit 30
        """
    )

    # 동기화 옵션
    parser.add_argument('--sync-kr', action='store_true',
                        help='한국 종목 DB 동기화 (DART 연동)')
    parser.add_argument('--force', action='store_true',
                        help='강제 동기화')
    parser.add_argument('--stats', action='store_true',
                        help='DB 통계 출력')

    # 검색 옵션
    parser.add_argument('--search', type=str, metavar='KEYWORD',
                        help='종목 검색 (종목명 또는 코드)')
    parser.add_argument('--market', type=str,
                        choices=['kospi', 'kosdaq', 'nasdaq', 'nyse'],
                        help='시장 필터')

    # 조회 옵션
    parser.add_argument('--ticker', '-t', type=str,
                        help='티커 심볼 (AAPL, 005930, 삼성전자)')
    parser.add_argument('--price', action='store_true',
                        help='주가 조회 (OHLCV)')
    parser.add_argument('--financials', action='store_true',
                        help='재무제표 조회')
    parser.add_argument('--dividends', action='store_true',
                        help='배당 이력 조회')
    parser.add_argument('--info', action='store_true',
                        help='기업 정보 조회')

    # 주가 옵션
    parser.add_argument('--period', type=str, default='1y',
                        choices=['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '3y', '5y', '10y', 'ytd', 'max'],
                        help='조회 기간 (기본: 1y)')
    parser.add_argument('--interval', type=str, default='1d',
                        choices=['1m', '5m', '15m', '30m', '60m', '1h', '1d', '1wk', '1mo'],
                        help='데이터 간격 (기본: 1d)')
    parser.add_argument('--start-date', type=str,
                        help='시작일 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                        help='종료일 (YYYY-MM-DD)')

    # 재무제표 옵션
    parser.add_argument('--quarterly', '-q', action='store_true',
                        help='분기별 재무제표')

    # 출력 옵션
    parser.add_argument('--output', '-o', type=str,
                        help='결과 저장 파일 (csv/json)')
    parser.add_argument('--save', action='store_true',
                        help='자동 저장 (9_Attachments/Data/yahoo/)')
    parser.add_argument('--json', action='store_true',
                        help='JSON 형식으로 저장')
    parser.add_argument('--limit', type=int, default=50,
                        help='검색 결과/출력 행 수 (기본: 50)')

    # DB 저장 옵션 (yahoo.db) - 기본값 True
    parser.add_argument('--no-save-db', action='store_true',
                        help='DB 저장 안 함 (기본: DB에 자동 저장)')
    parser.add_argument('--data-db-stats', action='store_true',
                        help='데이터 DB(yahoo.db) 통계 출력')
    parser.add_argument('--query-db', type=str, metavar='TYPE',
                        choices=['price', 'financial', 'dividend'],
                        help='DB에서 데이터 조회 (price/financial/dividend)')

    args = parser.parse_args()

    api = YahooAPI()

    # 동기화
    if args.sync_kr:
        if api.meta_db:
            api.meta_db.sync_korean_stocks(force=args.force)
        else:
            print("메타DB를 사용할 수 없습니다.")
        return

    # 통계
    if args.stats:
        if api.meta_db:
            stats = api.meta_db.get_stats()
            print("\n=== Yahoo 메타DB 통계 ===")
            print(f"전체 종목: {stats.get('total', 0):,}개")
            if stats.get('by_market'):
                print("\n시장별:")
                for market, cnt in stats['by_market'].items():
                    print(f"  - {market}: {cnt:,}개")
        else:
            print("메타DB를 사용할 수 없습니다.")
        return

    # 검색
    if args.search:
        if api.meta_db:
            results = api.meta_db.search_stock(
                args.search,
                market=args.market,
                limit=args.limit
            )
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            print(f"{'종목명':<20} {'코드':<10} {'티커':<12} {'시장':<8}")
            print("-" * 55)
            for s in results:
                name = s['stock_name'][:18]
                code = s['stock_code']
                ticker = s['yahoo_ticker']
                market = s['market']
                print(f"{name:<20} {code:<10} {ticker:<12} {market:<8}")
        else:
            print("메타DB를 사용할 수 없습니다.")
        return

    # 데이터 DB 통계
    if args.data_db_stats:
        stats = api.get_data_db_stats()
        if 'error' in stats:
            print(f"오류: {stats['error']}")
        else:
            print("\n=== Yahoo 데이터 DB (yahoo.db) 통계 ===")
            print(f"DB 크기: {stats.get('db_size_mb', 0)} MB")
            print(f"\n[주가 데이터]")
            print(f"  - 레코드 수: {stats.get('price_records', 0):,}건")
            print(f"  - 종목 수: {stats.get('price_tickers', 0)}개")
            print(f"\n[재무제표 데이터]")
            print(f"  - 레코드 수: {stats.get('financial_records', 0):,}건")
            print(f"  - 종목 수: {stats.get('financial_tickers', 0)}개")
            print(f"\n[배당 데이터]")
            print(f"  - 레코드 수: {stats.get('dividend_records', 0):,}건")
            print(f"  - 종목 수: {stats.get('dividend_tickers', 0)}개")
            if stats.get('collection_by_type'):
                print(f"\n[수집 현황]")
                for dtype, info in stats['collection_by_type'].items():
                    print(f"  - {dtype}: {info['count']}회 (최종: {info['last_collected'][:10]})")
        return

    # DB 조회
    if args.query_db:
        df = api.query_db(
            args.query_db,
            ticker=args.ticker,
            start_date=args.start_date,
            end_date=args.end_date,
            limit=args.limit
        )
        if not df.empty:
            api.print_dataframe(df, f"DB 조회: {args.query_db}", args.limit)
        else:
            print("조회 결과가 없습니다.")
        return

    # 티커 필수 체크
    if not args.ticker:
        if not (args.sync_kr or args.stats or args.search):
            parser.print_help()
        return

    # 티커 해석
    resolved_ticker = api.resolve_ticker(args.ticker)
    if not resolved_ticker:
        resolved_ticker = api.normalize_ticker(args.ticker)

    print(f"티커: {resolved_ticker}")

    # 기업 정보
    if args.info:
        info = api.get_stock_info(resolved_ticker)
        if info:
            print(f"\n=== 기업 정보: {resolved_ticker} ===")
            for key, value in info.items():
                print(f"  {key}: {value}")

            if args.output:
                ext = Path(args.output).suffix.lower()
                if ext == '.json' or args.json:
                    api.export_to_json(info, args.output)
                else:
                    api.export_to_csv(info, args.output)
        return

    # 주가 조회
    if args.price:
        df = api.get_price_history(
            resolved_ticker,
            period=args.period,
            interval=args.interval,
            start_date=args.start_date,
            end_date=args.end_date,
            save_to_db=not args.no_save_db  # DB 저장 여부 전달
        )

        if not df.empty:
            api.print_dataframe(df, f"주가 데이터: {resolved_ticker}", args.limit)

            if args.save:
                fmt = 'json' if args.json else 'csv'
                api.auto_save(df, resolved_ticker, 'price', fmt)
            elif args.output:
                ext = Path(args.output).suffix.lower()
                if ext == '.json' or args.json:
                    api.export_to_json(df, args.output)
                else:
                    api.export_to_csv(df, args.output)

    # 재무제표 조회
    if args.financials:
        financials = api.get_all_financials(resolved_ticker, quarterly=args.quarterly)
        period_type = 'quarterly' if args.quarterly else 'annual'

        for name, df in financials.items():
            if not df.empty:
                period_label = "분기" if args.quarterly else "연간"
                api.print_dataframe(df, f"{name} ({period_label}): {resolved_ticker}", 10)

                # DB 저장 (기본값: 저장함)
                if not args.no_save_db:
                    api.save_financial_to_db(resolved_ticker, name, df, period_type)

                if args.save:
                    fmt = 'json' if args.json else 'csv'
                    api.auto_save(df, resolved_ticker, name, fmt)

        if args.output and not args.save:
            # 전체 재무제표를 하나의 파일로 저장
            combined = {}
            for name, df in financials.items():
                if not df.empty:
                    combined[name] = df.to_dict(orient='records')

            if combined:
                ext = Path(args.output).suffix.lower()
                if ext == '.json' or args.json:
                    api.export_to_json(combined, args.output)
                else:
                    # CSV는 첫 번째 재무제표만 저장
                    first_df = list(financials.values())[0]
                    if not first_df.empty:
                        api.export_to_csv(first_df, args.output)

    # 배당 조회
    if args.dividends:
        df = api.get_dividends(resolved_ticker)

        if not df.empty:
            api.print_dataframe(df, f"배당 이력: {resolved_ticker}", args.limit)

            # DB 저장 (기본값: 저장함)
            if not args.no_save_db:
                api.save_dividend_to_db(resolved_ticker, df)

            if args.save:
                fmt = 'json' if args.json else 'csv'
                api.auto_save(df, resolved_ticker, 'dividends', fmt)
            elif args.output:
                ext = Path(args.output).suffix.lower()
                if ext == '.json' or args.json:
                    api.export_to_json(df, args.output)
                else:
                    api.export_to_csv(df, args.output)


if __name__ == '__main__':
    main()
