# -*- coding: utf-8 -*-
"""
DART 메타데이터 DB 관리
고유번호, 기업정보를 SQLite로 관리

Author: Claude Code
Version: 1.0.0
"""

import os
import sys
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from io import BytesIO

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


class DartMetaDB:
    """DART 메타데이터 DB 관리 클래스"""

    API_URL = "https://opendart.fss.or.kr/api/corpCode.xml"

    SCHEMA = """
    -- 기업 고유번호
    CREATE TABLE IF NOT EXISTS corporations (
        id INTEGER PRIMARY KEY,
        corp_code TEXT UNIQUE NOT NULL,   -- 고유번호 (8자리)
        corp_name TEXT NOT NULL,          -- 정식회사명
        corp_name_eng TEXT,               -- 영문명
        stock_code TEXT,                  -- 종목코드 (6자리, 상장사만)
        modify_date TEXT,                 -- 최종변경일 (YYYYMMDD)
        is_listed INTEGER DEFAULT 0,      -- 상장 여부
        corp_cls TEXT,                    -- 법인구분 (Y/K/N/E)
        updated_at TEXT
    );

    -- 법인구분 코드
    CREATE TABLE IF NOT EXISTS corp_classes (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_corp_name ON corporations(corp_name);
    CREATE INDEX IF NOT EXISTS idx_stock_code ON corporations(stock_code);
    CREATE INDEX IF NOT EXISTS idx_is_listed ON corporations(is_listed);

    -- FTS5 전문 검색 (선택적)
    CREATE VIRTUAL TABLE IF NOT EXISTS corp_fts USING fts5(
        corp_name,
        corp_name_eng,
        content='corporations',
        content_rowid='id'
    );

    -- FTS 트리거
    CREATE TRIGGER IF NOT EXISTS corp_ai AFTER INSERT ON corporations BEGIN
        INSERT INTO corp_fts(rowid, corp_name, corp_name_eng)
        VALUES (new.id, new.corp_name, new.corp_name_eng);
    END;

    CREATE TRIGGER IF NOT EXISTS corp_ad AFTER DELETE ON corporations BEGIN
        INSERT INTO corp_fts(corp_fts, rowid, corp_name, corp_name_eng)
        VALUES ('delete', old.id, old.corp_name, old.corp_name_eng);
    END;

    CREATE TRIGGER IF NOT EXISTS corp_au AFTER UPDATE ON corporations BEGIN
        INSERT INTO corp_fts(corp_fts, rowid, corp_name, corp_name_eng)
        VALUES ('delete', old.id, old.corp_name, old.corp_name_eng);
        INSERT INTO corp_fts(rowid, corp_name, corp_name_eng)
        VALUES (new.id, new.corp_name, new.corp_name_eng);
    END;
    """

    # 법인구분 코드
    CORP_CLASSES = [
        ('Y', '유가증권시장', 'KOSPI 상장'),
        ('K', '코스닥', 'KOSDAQ 상장'),
        ('N', '코넥스', 'KONEX 상장'),
        ('E', '기타', '비상장'),
    ]

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent / 'data'
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / 'dart_meta.db')

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
        return os.getenv('DART_API_KEY', '')

    def connect(self) -> sqlite3.Connection:
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

        # 법인구분 코드 삽입
        conn.executemany("""
            INSERT OR IGNORE INTO corp_classes (code, name, description)
            VALUES (?, ?, ?)
        """, self.CORP_CLASSES)

        conn.commit()
        print(f"DB 초기화 완료: {self.db_path}")
        return True

    def download_and_import(self, force: bool = False) -> int:
        """
        고유번호 파일 다운로드 및 DB 저장

        Args:
            force: 강제 다운로드 여부

        Returns:
            저장된 기업 수
        """
        if not self.api_key:
            print("DART_API_KEY가 설정되지 않았습니다.")
            return 0

        # DB 초기화 (테이블 없으면 생성)
        self.init_db()
        conn = self.connect()

        # 마지막 업데이트 확인
        if not force:
            try:
                cursor = conn.execute(
                    "SELECT MAX(updated_at) FROM corporations"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    last_update = datetime.fromisoformat(row[0])
                    if datetime.now() - last_update < timedelta(days=1):
                        print("DB가 최신 상태입니다 (1일 이내 업데이트)")
                        cursor = conn.execute("SELECT COUNT(*) FROM corporations")
                        return cursor.fetchone()[0]
            except Exception:
                pass  # 테이블이 없거나 비어있는 경우

        print("DART 고유번호 파일 다운로드 중...")

        try:
            response = requests.get(
                self.API_URL,
                params={'crtfc_key': self.api_key},
                timeout=60
            )

            if response.status_code != 200:
                print(f"다운로드 실패: HTTP {response.status_code}")
                return 0

            # ZIP 파일 압축 해제
            print("XML 파싱 중...")
            with zipfile.ZipFile(BytesIO(response.content)) as zf:
                xml_name = zf.namelist()[0]
                with zf.open(xml_name) as f:
                    xml_content = f.read()

            # XML 파싱
            root = ET.fromstring(xml_content)
            now = datetime.now().isoformat()
            count = 0

            # 기존 데이터 삭제 (전체 갱신)
            conn.execute("DELETE FROM corporations")

            # 배치 처리
            batch = []
            batch_size = 1000

            for item in root.findall('.//list'):
                corp_code = item.findtext('corp_code', '').strip()
                corp_name = item.findtext('corp_name', '').strip()
                corp_name_eng = item.findtext('corp_eng_name', '').strip()
                stock_code = item.findtext('stock_code', '').strip()
                modify_date = item.findtext('modify_date', '').strip()

                if not corp_code or not corp_name:
                    continue

                is_listed = 1 if stock_code else 0

                batch.append((
                    corp_code,
                    corp_name,
                    corp_name_eng or None,
                    stock_code or None,
                    modify_date or None,
                    is_listed,
                    now
                ))

                if len(batch) >= batch_size:
                    conn.executemany("""
                        INSERT INTO corporations
                        (corp_code, corp_name, corp_name_eng, stock_code, modify_date, is_listed, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    count += len(batch)
                    batch = []
                    print(f"  {count}개 저장...", end='\r')

            # 남은 배치 처리
            if batch:
                conn.executemany("""
                    INSERT INTO corporations
                    (corp_code, corp_name, corp_name_eng, stock_code, modify_date, is_listed, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, batch)
                count += len(batch)

            conn.commit()
            print(f"\n총 {count}개 기업 저장 완료")
            return count

        except Exception as e:
            print(f"오류 발생: {e}")
            return 0

    def get_corp_code(self, name: str) -> Optional[str]:
        """
        회사명으로 고유번호 조회

        Args:
            name: 회사명 (정확한 명칭 또는 부분 일치)

        Returns:
            고유번호 또는 None
        """
        conn = self.connect()

        # 1. 정확한 매칭
        cursor = conn.execute(
            "SELECT corp_code FROM corporations WHERE corp_name = ?",
            (name,)
        )
        row = cursor.fetchone()
        if row:
            return row['corp_code']

        # 2. 부분 매칭 (상장사 우선)
        cursor = conn.execute("""
            SELECT corp_code, corp_name, is_listed
            FROM corporations
            WHERE corp_name LIKE ?
            ORDER BY is_listed DESC, LENGTH(corp_name)
            LIMIT 1
        """, (f'%{name}%',))

        row = cursor.fetchone()
        if row:
            return row['corp_code']

        return None

    def search_corp(
        self,
        keyword: str,
        listed_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """
        키워드로 기업 검색

        Args:
            keyword: 검색 키워드
            listed_only: 상장사만 검색
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        if listed_only:
            cursor = conn.execute("""
                SELECT corp_code, corp_name, stock_code, is_listed
                FROM corporations
                WHERE (corp_name LIKE ? OR corp_name_eng LIKE ?)
                  AND is_listed = 1
                ORDER BY LENGTH(corp_name)
                LIMIT ?
            """, (f'%{keyword}%', f'%{keyword}%', limit))
        else:
            cursor = conn.execute("""
                SELECT corp_code, corp_name, stock_code, is_listed
                FROM corporations
                WHERE corp_name LIKE ? OR corp_name_eng LIKE ?
                ORDER BY is_listed DESC, LENGTH(corp_name)
                LIMIT ?
            """, (f'%{keyword}%', f'%{keyword}%', limit))

        return [dict(row) for row in cursor.fetchall()]

    def search_fts(self, query: str, limit: int = 50) -> List[Dict]:
        """
        FTS5 전문 검색

        Args:
            query: 검색 쿼리 (FTS5 문법 지원)
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        try:
            cursor = conn.execute("""
                SELECT c.corp_code, c.corp_name, c.stock_code, c.is_listed
                FROM corp_fts f
                JOIN corporations c ON f.rowid = c.id
                WHERE corp_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # FTS가 비어있는 경우 일반 검색으로 폴백
            return self.search_corp(query, limit=limit)

    def get_corp_info(self, corp_code: str) -> Optional[Dict]:
        """
        고유번호로 기업 정보 조회

        Args:
            corp_code: 고유번호

        Returns:
            기업 정보 딕셔너리
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT * FROM corporations WHERE corp_code = ?
        """, (corp_code,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_listed_corps(self, market: Optional[str] = None) -> List[Dict]:
        """
        상장사 목록 조회

        Args:
            market: 시장 구분 (Y=KOSPI, K=KOSDAQ, N=KONEX, None=전체)

        Returns:
            상장사 목록
        """
        conn = self.connect()

        if market:
            cursor = conn.execute("""
                SELECT corp_code, corp_name, stock_code
                FROM corporations
                WHERE is_listed = 1 AND corp_cls = ?
                ORDER BY corp_name
            """, (market,))
        else:
            cursor = conn.execute("""
                SELECT corp_code, corp_name, stock_code
                FROM corporations
                WHERE is_listed = 1
                ORDER BY corp_name
            """)

        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """DB 통계 조회"""
        conn = self.connect()

        stats = {}

        cursor = conn.execute("SELECT COUNT(*) FROM corporations")
        stats['total'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM corporations WHERE is_listed = 1")
        stats['listed'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM corporations WHERE is_listed = 0")
        stats['unlisted'] = cursor.fetchone()[0]

        # 법인구분별 통계
        cursor = conn.execute("""
            SELECT corp_cls, COUNT(*) as cnt FROM corporations
            WHERE corp_cls IS NOT NULL
            GROUP BY corp_cls
        """)
        stats['by_corp_cls'] = {row[0]: row[1] for row in cursor.fetchall()}

        cursor = conn.execute("SELECT MAX(updated_at) FROM corporations")
        row = cursor.fetchone()
        stats['last_update'] = row[0] if row else None

        return stats

    def update_corp_cls(self, batch_size: int = 100, delay: float = 0.5) -> int:
        """
        상장사의 법인구분(corp_cls) 업데이트
        기업개황 API를 호출해서 corp_cls 정보를 채움

        Args:
            batch_size: 배치 크기
            delay: API 호출 간 딜레이 (초)

        Returns:
            업데이트된 기업 수
        """
        import time

        if not self.api_key:
            print("DART_API_KEY가 설정되지 않았습니다.")
            return 0

        conn = self.connect()

        # corp_cls가 NULL인 상장사 조회
        cursor = conn.execute("""
            SELECT corp_code, corp_name FROM corporations
            WHERE is_listed = 1 AND corp_cls IS NULL
        """)
        corps = cursor.fetchall()

        if not corps:
            print("업데이트할 상장사가 없습니다.")
            return 0

        print(f"총 {len(corps)}개 상장사의 법인구분 업데이트 시작...")

        updated = 0
        errors = 0

        for i, corp in enumerate(corps):
            corp_code = corp['corp_code']
            corp_name = corp['corp_name']

            try:
                # 기업개황 API 호출
                url = "https://opendart.fss.or.kr/api/company.json"
                params = {
                    'crtfc_key': self.api_key,
                    'corp_code': corp_code
                }

                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data.get('status') == '000':
                    corp_cls = data.get('corp_cls')
                    if corp_cls:
                        conn.execute("""
                            UPDATE corporations SET corp_cls = ?
                            WHERE corp_code = ?
                        """, (corp_cls, corp_code))
                        updated += 1
                else:
                    errors += 1

            except Exception as e:
                errors += 1

            # 진행 상황 출력
            if (i + 1) % 100 == 0:
                conn.commit()
                print(f"  {i + 1}/{len(corps)} 처리 완료 (업데이트: {updated}, 오류: {errors})")

            # API 호출 제한 방지
            time.sleep(delay)

        conn.commit()
        print(f"\n총 {updated}개 기업 법인구분 업데이트 완료 (오류: {errors}개)")
        return updated


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='DART 메타데이터 DB 관리')
    parser.add_argument('--init', action='store_true', help='DB 초기화')
    parser.add_argument('--sync', action='store_true',
                        help='고유번호 파일 다운로드 및 DB 동기화')
    parser.add_argument('--force', action='store_true',
                        help='강제 다운로드 (--sync와 함께 사용)')
    parser.add_argument('--update-corp-cls', action='store_true',
                        help='상장사 법인구분(Y/K/N/E) 업데이트 (API 호출 필요)')
    parser.add_argument('--delay', type=float, default=0.3,
                        help='API 호출 간 딜레이 초 (기본: 0.3)')
    parser.add_argument('--search', type=str, metavar='KEYWORD',
                        help='기업 검색')
    parser.add_argument('--listed-only', action='store_true',
                        help='상장사만 검색')
    parser.add_argument('--get-code', type=str, metavar='NAME',
                        help='회사명으로 고유번호 조회')
    parser.add_argument('--info', type=str, metavar='CORP_CODE',
                        help='고유번호로 기업 정보 조회')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    db = DartMetaDB(args.db)

    try:
        if args.init:
            db.init_db()

        elif args.sync:
            db.init_db()
            db.download_and_import(force=args.force)

        elif args.update_corp_cls:
            db.update_corp_cls(delay=args.delay)

        elif args.search:
            results = db.search_corp(args.search, listed_only=args.listed_only)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            print(f"{'회사명':<30} {'종목코드':<10} {'고유번호':<12}")
            print("-" * 55)
            for co in results[:30]:
                name = co['corp_name'][:28]
                stock = co['stock_code'] or '-'
                code = co['corp_code']
                listed = '*' if co['is_listed'] else ''
                print(f"{name:<30} {stock:<10} {code:<12} {listed}")

        elif args.get_code:
            code = db.get_corp_code(args.get_code)
            if code:
                print(f"{args.get_code} → {code}")
            else:
                print(f"'{args.get_code}'를 찾을 수 없습니다.")

        elif args.info:
            info = db.get_corp_info(args.info)
            if info:
                print(f"\n=== 기업 정보 ===")
                print(f"고유번호: {info['corp_code']}")
                print(f"회사명: {info['corp_name']}")
                if info['corp_name_eng']:
                    print(f"영문명: {info['corp_name_eng']}")
                if info['stock_code']:
                    print(f"종목코드: {info['stock_code']}")
                print(f"상장여부: {'상장' if info['is_listed'] else '비상장'}")
                print(f"최종변경일: {info['modify_date']}")
            else:
                print(f"고유번호 '{args.info}'를 찾을 수 없습니다.")

        elif args.stats:
            stats = db.get_stats()
            print("\n=== DART 메타DB 통계 ===")
            print(f"전체 기업: {stats['total']:,}개")
            print(f"  - 상장사: {stats['listed']:,}개")
            print(f"  - 비상장: {stats['unlisted']:,}개")
            if stats.get('by_corp_cls'):
                print("\n법인구분별:")
                corp_cls_names = {'Y': '유가증권(KOSPI)', 'K': '코스닥(KOSDAQ)', 'N': '코넥스(KONEX)', 'E': '기타'}
                for code, cnt in stats['by_corp_cls'].items():
                    name = corp_cls_names.get(code, code)
                    print(f"  - {name}: {cnt:,}개")
            else:
                print("\n법인구분: 미설정 (--update-corp-cls 실행 필요)")
            if stats['last_update']:
                print(f"\n마지막 업데이트: {stats['last_update'][:19]}")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
