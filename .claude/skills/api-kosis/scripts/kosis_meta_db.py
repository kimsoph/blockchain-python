# -*- coding: utf-8 -*-
"""
KOSIS 메타데이터 DB 관리
국가통계포털 통계표/항목 정보를 SQLite로 관리

Author: Claude Code
Version: 1.0.0
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode

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


class KosisMetaDB:
    """KOSIS 메타데이터 DB 관리 클래스"""

    BASE_URL = "https://kosis.kr/openapi"

    # 서비스뷰 코드
    VIEW_CODES = {
        'MT_ZTITLE': '국내통계 주제별',
        'MT_OTITLE': '국내통계 기관별',
        'MT_GTITLE01': 'e-지방지표 시도별',
        'MT_GTITLE02': 'e-지방지표 시군구별',
        'MT_ATITLE01': '북한통계 주제별',
        'MT_BTITLE': '국제통계',
        'MT_CHOSUN_TITLE': '광복이전통계',
        'MT_TM1_TITLE': '대상별통계',
        'MT_TM2_TITLE': 'A~Z통계',
    }

    # 수록주기 코드
    PERIOD_CODES = {
        'Y': '년',
        'H': '반년',
        'Q': '분기',
        'M': '월',
        'S': '반월',
        'D': '일',
    }

    # API 오류 코드
    ERROR_CODES = {
        '00': '정상',
        '01': '잘못된 인증키',
        '02': '인증키 사용 신청 미완료',
        '10': '잘못된 요청 파라미터',
        '11': '조회 결과 없음',
        '12': '인증키 기간 만료',
        '20': '서비스 이용 횟수 초과',
        '30': '서비스 접근 거부',
        '99': '서버 오류',
    }

    SCHEMA = """
    -- 통계표 목록 (통합검색 결과 기반)
    CREATE TABLE IF NOT EXISTS stat_tables (
        id INTEGER PRIMARY KEY,
        tbl_id TEXT UNIQUE,           -- 통계표 ID
        tbl_nm TEXT,                  -- 통계표명
        org_id TEXT,                  -- 기관 ID
        org_nm TEXT,                  -- 기관명
        stat_id TEXT,                 -- 통계 ID
        stat_nm TEXT,                 -- 통계명
        vw_cd TEXT,                   -- 서비스뷰 코드
        vw_nm TEXT,                   -- 서비스뷰명
        list_id TEXT,                 -- 목록 ID
        list_nm TEXT,                 -- 목록명
        prd_se TEXT,                  -- 수록주기
        prd_de TEXT,                  -- 수록시점
        updt_de TEXT,                 -- 갱신일자
        updated_at TEXT
    );

    -- 통계목록 계층구조
    CREATE TABLE IF NOT EXISTS stat_hierarchy (
        id INTEGER PRIMARY KEY,
        vw_cd TEXT,                   -- 서비스뷰 코드
        vw_nm TEXT,                   -- 서비스뷰명
        list_id TEXT,                 -- 목록 ID
        list_nm TEXT,                 -- 목록명
        parent_list_id TEXT,          -- 상위 목록 ID
        tbl_id TEXT,                  -- 통계표 ID (leaf인 경우)
        tbl_nm TEXT,                  -- 통계표명
        org_id TEXT,                  -- 기관 ID
        stat_id TEXT,                 -- 통계 ID
        rec_tbl_se TEXT,              -- 목록유형 (T:통계표, G:그룹)
        send_de TEXT,                 -- 게시일
        updated_at TEXT,
        UNIQUE(vw_cd, list_id)
    );

    -- 통계표 분류/항목
    CREATE TABLE IF NOT EXISTS stat_classifications (
        id INTEGER PRIMARY KEY,
        org_id TEXT,                  -- 기관 ID
        tbl_id TEXT,                  -- 통계표 ID
        obj_id TEXT,                  -- 분류 ID
        obj_nm TEXT,                  -- 분류명
        obj_nm_eng TEXT,              -- 분류명(영문)
        itm_id TEXT,                  -- 항목 ID
        itm_nm TEXT,                  -- 항목명
        itm_nm_eng TEXT,              -- 항목명(영문)
        unit_nm TEXT,                 -- 단위
        unit_nm_eng TEXT,             -- 단위(영문)
        updated_at TEXT,
        UNIQUE(org_id, tbl_id, obj_id, itm_id)
    );

    -- 수록주기 코드
    CREATE TABLE IF NOT EXISTS period_codes (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    );

    -- 서비스뷰 코드
    CREATE TABLE IF NOT EXISTS view_codes (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL
    );

    -- 분류값 테이블 (통계표별 분류/항목 정보)
    CREATE TABLE IF NOT EXISTS stat_classification_values (
        id INTEGER PRIMARY KEY,
        org_id TEXT NOT NULL,
        tbl_id TEXT NOT NULL,
        cls_level INTEGER NOT NULL,     -- 분류 단계 (1~8, 0=항목)
        cls_id TEXT,                    -- 분류/항목 ID
        cls_nm TEXT,                    -- 분류/항목 이름
        value_code TEXT NOT NULL,       -- 값 코드
        value_name TEXT,                -- 값 이름
        parent_code TEXT,               -- 상위 분류 코드
        unit_nm TEXT,                   -- 단위 (항목인 경우)
        sort_order INTEGER,
        updated_at TEXT,
        UNIQUE(org_id, tbl_id, cls_level, value_code)
    );

    -- 통계표 분류 구조 정보
    CREATE TABLE IF NOT EXISTS stat_table_structure (
        id INTEGER PRIMARY KEY,
        org_id TEXT NOT NULL,
        tbl_id TEXT NOT NULL,
        obj_count INTEGER,              -- 분류 단계 수 (1~8)
        itm_count INTEGER,              -- 항목 수
        structure_json TEXT,            -- 구조 정보 JSON
        updated_at TEXT,
        UNIQUE(org_id, tbl_id)
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_tbl_id ON stat_tables(tbl_id);
    CREATE INDEX IF NOT EXISTS idx_tbl_nm ON stat_tables(tbl_nm);
    CREATE INDEX IF NOT EXISTS idx_org_id ON stat_tables(org_id);
    CREATE INDEX IF NOT EXISTS idx_hierarchy_vw ON stat_hierarchy(vw_cd);
    CREATE INDEX IF NOT EXISTS idx_hierarchy_parent ON stat_hierarchy(parent_list_id);
    CREATE INDEX IF NOT EXISTS idx_class_tbl ON stat_classifications(tbl_id);
    CREATE INDEX IF NOT EXISTS idx_clsval_tbl ON stat_classification_values(tbl_id);
    CREATE INDEX IF NOT EXISTS idx_clsval_level ON stat_classification_values(cls_level);
    CREATE INDEX IF NOT EXISTS idx_tblstruct_tbl ON stat_table_structure(tbl_id);

    -- FTS5 전문 검색
    CREATE VIRTUAL TABLE IF NOT EXISTS stat_tables_fts USING fts5(
        tbl_nm, org_nm, stat_nm,
        content='stat_tables',
        content_rowid='id'
    );

    -- FTS 트리거 (stat_tables)
    CREATE TRIGGER IF NOT EXISTS stat_tables_ai AFTER INSERT ON stat_tables BEGIN
        INSERT INTO stat_tables_fts(rowid, tbl_nm, org_nm, stat_nm)
        VALUES (new.id, new.tbl_nm, new.org_nm, new.stat_nm);
    END;

    CREATE TRIGGER IF NOT EXISTS stat_tables_ad AFTER DELETE ON stat_tables BEGIN
        INSERT INTO stat_tables_fts(stat_tables_fts, rowid, tbl_nm, org_nm, stat_nm)
        VALUES ('delete', old.id, old.tbl_nm, old.org_nm, old.stat_nm);
    END;

    CREATE TRIGGER IF NOT EXISTS stat_tables_au AFTER UPDATE ON stat_tables BEGIN
        INSERT INTO stat_tables_fts(stat_tables_fts, rowid, tbl_nm, org_nm, stat_nm)
        VALUES ('delete', old.id, old.tbl_nm, old.org_nm, old.stat_nm);
        INSERT INTO stat_tables_fts(rowid, tbl_nm, org_nm, stat_nm)
        VALUES (new.id, new.tbl_nm, new.org_nm, new.stat_nm);
    END;
    """

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent / 'data'
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / 'kosis_meta.db')

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
        return os.getenv('KOSIS_API_KEY', '')

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

        # 수록주기 코드 삽입
        period_data = [(k, v, f'{v}간 데이터') for k, v in self.PERIOD_CODES.items()]
        conn.executemany("""
            INSERT OR IGNORE INTO period_codes (code, name, description)
            VALUES (?, ?, ?)
        """, period_data)

        # 서비스뷰 코드 삽입
        view_data = [(k, v) for k, v in self.VIEW_CODES.items()]
        conn.executemany("""
            INSERT OR IGNORE INTO view_codes (code, name)
            VALUES (?, ?)
        """, view_data)

        conn.commit()
        print(f"DB 초기화 완료: {self.db_path}")
        return True

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        method: str = 'GET'
    ) -> Dict:
        """
        KOSIS API 요청

        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터
            method: HTTP 메서드

        Returns:
            API 응답 데이터
        """
        if not self.api_key:
            return {'err': 'API 키가 설정되지 않았습니다.'}

        # 기본 파라미터 추가
        params['apiKey'] = self.api_key
        params['format'] = 'json'
        params['jsonVD'] = 'Y'

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=30)
            else:
                response = requests.post(url, data=params, timeout=30)

            response.encoding = 'utf-8'

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    # JSON 파싱 실패시 텍스트 반환
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

    def sync_from_search(
        self,
        keywords: List[str],
        force: bool = False,
        limit_per_keyword: int = 100
    ) -> int:
        """
        통합검색으로 통계표 동기화

        Args:
            keywords: 검색 키워드 리스트
            force: 강제 동기화 여부
            limit_per_keyword: 키워드당 최대 결과 수

        Returns:
            저장된 통계표 수
        """
        if not self.api_key:
            print("KOSIS_API_KEY가 설정되지 않았습니다.")
            return 0

        self.init_db()
        conn = self.connect()

        # 마지막 업데이트 확인
        if not force:
            try:
                cursor = conn.execute(
                    "SELECT MAX(updated_at) FROM stat_tables"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    last_update = datetime.fromisoformat(row[0])
                    if datetime.now() - last_update < timedelta(days=1):
                        print("통계표 목록이 최신 상태입니다 (1일 이내 업데이트)")
                        cursor = conn.execute("SELECT COUNT(*) FROM stat_tables")
                        return cursor.fetchone()[0]
            except Exception:
                pass

        print("KOSIS 통계표 동기화 중...")

        now = datetime.now().isoformat()
        total_count = 0

        for keyword in keywords:
            print(f"  검색 중: '{keyword}'...")

            params = {
                'searchNm': keyword,
                'sort': 'RANK',
                'startCount': '1',
                'resultCount': str(limit_per_keyword),
            }

            result = self._make_request('statisticsSearch.do', params)

            if 'err' in result:
                print(f"  오류: {result.get('message', result.get('err'))}")
                continue

            # 결과 파싱
            items = result if isinstance(result, list) else result.get('StatisticSearch', [])
            if not items:
                print(f"  '{keyword}' 검색 결과 없음")
                continue

            batch = []
            for item in items:
                if not item.get('TBL_ID'):
                    continue

                batch.append((
                    item.get('TBL_ID', ''),
                    item.get('TBL_NM', ''),
                    item.get('ORG_ID', ''),
                    item.get('ORG_NM', ''),
                    item.get('STAT_ID', ''),
                    item.get('STAT_NM', ''),
                    item.get('VW_CD', ''),
                    item.get('VW_NM', ''),
                    item.get('LIST_ID', ''),
                    item.get('LIST_NM', ''),
                    item.get('PRD_SE', ''),
                    item.get('PRD_DE', ''),
                    item.get('SEND_DE', ''),
                    now
                ))

            if batch:
                conn.executemany("""
                    INSERT OR REPLACE INTO stat_tables
                    (tbl_id, tbl_nm, org_id, org_nm, stat_id, stat_nm,
                     vw_cd, vw_nm, list_id, list_nm, prd_se, prd_de, updt_de, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                total_count += len(batch)
                print(f"  '{keyword}': {len(batch)}건 저장")

        print(f"총 {total_count}개 통계표 저장 완료")
        return total_count

    def sync_hierarchy(
        self,
        vw_cd: str = 'MT_ZTITLE',
        parent_id: str = '',
        force: bool = False,
        depth: int = 0,
        max_depth: int = 3,
        _conn: sqlite3.Connection = None
    ) -> int:
        """
        통계목록 계층구조 동기화

        Args:
            vw_cd: 서비스뷰 코드
            parent_id: 시작 목록 ID
            force: 강제 동기화 여부
            depth: 현재 깊이
            max_depth: 최대 탐색 깊이
            _conn: 내부용 DB 연결 (재귀 호출 시 사용)

        Returns:
            저장된 항목 수
        """
        if not self.api_key:
            print("KOSIS_API_KEY가 설정되지 않았습니다.")
            return 0

        if depth > max_depth:
            return 0

        # 최초 호출 시에만 DB 초기화 및 연결 생성
        if depth == 0:
            self.init_db()
            _conn = self.connect()
            print(f"계층구조 동기화: {vw_cd} > {parent_id or '(루트)'}")

        indent = "  " * depth

        params = {
            'vwCd': vw_cd,
            'parentListId': parent_id,
        }

        result = self._make_request('statisticsList.do', params)

        if 'err' in result:
            print(f"{indent}오류: {result.get('message', result.get('err'))}")
            return 0

        items = result if isinstance(result, list) else result.get('StatisticsList', [])
        if not items:
            return 0

        now = datetime.now().isoformat()
        count = 0

        for item in items:
            list_id = item.get('LIST_ID', '')
            if not list_id:
                continue

            # 현재 항목 저장
            _conn.execute("""
                INSERT OR REPLACE INTO stat_hierarchy
                (vw_cd, vw_nm, list_id, list_nm, parent_list_id, tbl_id, tbl_nm,
                 org_id, stat_id, rec_tbl_se, send_de, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vw_cd,
                item.get('VW_NM', ''),
                list_id,
                item.get('LIST_NM', ''),
                parent_id,
                item.get('TBL_ID', ''),
                item.get('TBL_NM', ''),
                item.get('ORG_ID', ''),
                item.get('STAT_ID', ''),
                item.get('REC_TBL_SE', ''),
                item.get('SEND_DE', ''),
                now
            ))
            count += 1

            # 그룹인 경우 하위 탐색 (동일 연결 전달)
            if item.get('REC_TBL_SE') != 'T':
                count += self.sync_hierarchy(vw_cd, list_id, force, depth + 1, max_depth, _conn)

        # 최상위 호출에서만 커밋
        if depth == 0:
            _conn.commit()
            print(f"총 {count}개 계층 항목 저장 완료")

        return count

    def search_tables(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        통계표 검색 (LIKE 검색)

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT tbl_id, tbl_nm, org_id, org_nm, stat_nm, prd_se, prd_de
            FROM stat_tables
            WHERE tbl_nm LIKE ? OR org_nm LIKE ? OR stat_nm LIKE ?
            ORDER BY tbl_nm
            LIMIT ?
        """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit))

        return [dict(row) for row in cursor.fetchall()]

    def search_tables_fts(self, query: str, limit: int = 50) -> List[Dict]:
        """
        FTS5 전문 검색으로 통계표 검색

        Args:
            query: 검색 쿼리
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        conn = self.connect()

        try:
            cursor = conn.execute("""
                SELECT t.tbl_id, t.tbl_nm, t.org_id, t.org_nm, t.stat_nm, t.prd_se, t.prd_de
                FROM stat_tables_fts f
                JOIN stat_tables t ON f.rowid = t.id
                WHERE stat_tables_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return self.search_tables(query, limit=limit)

    def get_table_info(self, tbl_id: str) -> Optional[Dict]:
        """
        통계표 정보 조회

        Args:
            tbl_id: 통계표 ID

        Returns:
            통계표 정보
        """
        conn = self.connect()

        cursor = conn.execute("""
            SELECT * FROM stat_tables WHERE tbl_id = ?
        """, (tbl_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_hierarchy(self, vw_cd: str = 'MT_ZTITLE', parent_id: str = None) -> List[Dict]:
        """
        계층구조 조회

        Args:
            vw_cd: 서비스뷰 코드
            parent_id: 상위 목록 ID

        Returns:
            하위 항목 리스트
        """
        conn = self.connect()

        if parent_id:
            cursor = conn.execute("""
                SELECT * FROM stat_hierarchy
                WHERE vw_cd = ? AND parent_list_id = ?
                ORDER BY list_id
            """, (vw_cd, parent_id))
        else:
            cursor = conn.execute("""
                SELECT DISTINCT parent_list_id FROM stat_hierarchy
                WHERE vw_cd = ?
                ORDER BY parent_list_id
            """, (vw_cd,))

        return [dict(row) for row in cursor.fetchall()]

    def get_classification_values(self, org_id: str, tbl_id: str) -> Optional[Dict]:
        """
        통계표의 분류/항목 정보 조회 (DB에서)

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID

        Returns:
            분류 구조 정보 또는 None
        """
        conn = self.connect()

        try:
            # 구조 정보 확인
            cursor = conn.execute("""
                SELECT structure_json, obj_count, itm_count, updated_at
                FROM stat_table_structure
                WHERE org_id = ? AND tbl_id = ?
            """, (org_id, tbl_id))

            row = cursor.fetchone()
            if not row or not row['structure_json']:
                return None

            import json
            try:
                structure = json.loads(row['structure_json'])
                structure['obj_count'] = row['obj_count']
                structure['itm_count'] = row['itm_count']
                structure['updated_at'] = row['updated_at']
                return structure
            except (json.JSONDecodeError, TypeError):
                return None
        except sqlite3.OperationalError:
            # 테이블이 없는 경우 None 반환 (이후 init_db로 생성됨)
            return None

    def save_classification_values(
        self,
        org_id: str,
        tbl_id: str,
        structure: Dict,
        values: List[Dict]
    ) -> int:
        """
        분류/항목 정보 저장

        Args:
            org_id: 기관 ID
            tbl_id: 통계표 ID
            structure: 구조 정보
            values: 분류값 리스트

        Returns:
            저장된 건수
        """
        import json

        # 테이블이 없을 수 있으므로 init_db 호출
        self.init_db()
        conn = self.connect()
        now = datetime.now().isoformat()

        # 구조 정보 저장
        conn.execute("""
            INSERT OR REPLACE INTO stat_table_structure
            (org_id, tbl_id, obj_count, itm_count, structure_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            org_id,
            tbl_id,
            structure.get('obj_count', 0),
            structure.get('itm_count', 0),
            json.dumps(structure, ensure_ascii=False),
            now
        ))

        # 기존 분류값 삭제 후 재삽입
        conn.execute("""
            DELETE FROM stat_classification_values
            WHERE org_id = ? AND tbl_id = ?
        """, (org_id, tbl_id))

        # 분류값 저장
        batch = []
        for i, val in enumerate(values):
            batch.append((
                org_id,
                tbl_id,
                val.get('cls_level', 0),
                val.get('cls_id', ''),
                val.get('cls_nm', ''),
                val.get('value_code', ''),
                val.get('value_name', ''),
                val.get('parent_code', ''),
                val.get('unit_nm', ''),
                i,
                now
            ))

        if batch:
            conn.executemany("""
                INSERT INTO stat_classification_values
                (org_id, tbl_id, cls_level, cls_id, cls_nm, value_code, value_name,
                 parent_code, unit_nm, sort_order, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)

        conn.commit()
        return len(batch)

    def get_stats(self) -> Dict:
        """DB 통계 조회"""
        conn = self.connect()

        stats = {}

        cursor = conn.execute("SELECT COUNT(*) FROM stat_tables")
        stats['tables'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM stat_hierarchy")
        stats['hierarchy'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM stat_classifications")
        stats['classifications'] = cursor.fetchone()[0]

        # 분류값 통계 추가
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM stat_classification_values")
            stats['classification_values'] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats['classification_values'] = 0

        try:
            cursor = conn.execute("SELECT COUNT(*) FROM stat_table_structure")
            stats['table_structures'] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats['table_structures'] = 0

        # 기관별 통계표 수
        cursor = conn.execute("""
            SELECT org_nm, COUNT(*) as cnt FROM stat_tables
            WHERE org_nm IS NOT NULL AND org_nm != ''
            GROUP BY org_nm
            ORDER BY cnt DESC
            LIMIT 10
        """)
        stats['by_org'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 수록주기별 통계표 수
        cursor = conn.execute("""
            SELECT prd_se, COUNT(*) as cnt FROM stat_tables
            WHERE prd_se IS NOT NULL AND prd_se != ''
            GROUP BY prd_se
        """)
        stats['by_period'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 마지막 업데이트
        cursor = conn.execute("SELECT MAX(updated_at) FROM stat_tables")
        row = cursor.fetchone()
        stats['tables_updated'] = row[0] if row else None

        return stats


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='KOSIS 메타데이터 DB 관리')
    parser.add_argument('--init', action='store_true', help='DB 초기화')
    parser.add_argument('--sync-search', type=str, metavar='KEYWORDS',
                        help='검색 기반 동기화 (쉼표로 구분)')
    parser.add_argument('--sync-hierarchy', nargs=2, metavar=('VW_CD', 'PARENT_ID'),
                        help='계층구조 동기화')
    parser.add_argument('--max-depth', type=int, default=3,
                        help='계층구조 최대 탐색 깊이 (기본값: 3)')
    parser.add_argument('--sync-all', action='store_true',
                        help='전체 동기화')
    parser.add_argument('--force', action='store_true',
                        help='강제 동기화')
    parser.add_argument('--search', type=str, metavar='KEYWORD',
                        help='통계표 검색')
    parser.add_argument('--info', type=str, metavar='TBL_ID',
                        help='통계표 정보 조회')
    parser.add_argument('--hierarchy', nargs='*', metavar='VW_CD',
                        help='계층구조 조회')
    parser.add_argument('--stats', action='store_true', help='DB 통계')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    db = KosisMetaDB(args.db)

    try:
        if args.init:
            db.init_db()

        elif args.sync_all:
            # 기본 키워드로 검색 동기화
            default_keywords = ['인구', '경제', '물가', '고용', '주택', '환경', '교육', '보건']
            db.sync_from_search(default_keywords, force=args.force)
            # 주제별 계층구조 동기화
            db.sync_hierarchy('MT_ZTITLE', '', force=args.force, max_depth=args.max_depth)

        elif args.sync_search:
            keywords = [k.strip() for k in args.sync_search.split(',')]
            db.sync_from_search(keywords, force=args.force)

        elif args.sync_hierarchy:
            vw_cd, parent_id = args.sync_hierarchy
            db.sync_hierarchy(vw_cd, parent_id, force=args.force, max_depth=args.max_depth)

        elif args.search:
            results = db.search_tables(args.search)
            print(f"\n=== '{args.search}' 검색 결과 ({len(results)}건) ===")
            print(f"{'통계표ID':<20} {'통계표명':<40} {'기관명':<15} {'주기':<4}")
            print("-" * 85)
            for t in results[:30]:
                tbl_id = t['tbl_id'][:18] if t.get('tbl_id') else ''
                tbl_nm = (t.get('tbl_nm') or '')[:38]
                org_nm = (t.get('org_nm') or '')[:13]
                prd_se = t.get('prd_se') or '-'
                print(f"{tbl_id:<20} {tbl_nm:<40} {org_nm:<15} {prd_se:<4}")

        elif args.info:
            info = db.get_table_info(args.info)
            if info:
                print(f"\n=== 통계표 정보 ===")
                print(f"통계표ID: {info.get('tbl_id', '-')}")
                print(f"통계표명: {info.get('tbl_nm', '-')}")
                print(f"기관ID: {info.get('org_id', '-')}")
                print(f"기관명: {info.get('org_nm', '-')}")
                print(f"통계ID: {info.get('stat_id', '-')}")
                print(f"통계명: {info.get('stat_nm', '-')}")
                print(f"수록주기: {info.get('prd_se', '-')}")
                print(f"수록시점: {info.get('prd_de', '-')}")
            else:
                print(f"통계표 '{args.info}'를 찾을 수 없습니다.")

        elif args.hierarchy is not None:
            if len(args.hierarchy) >= 1:
                vw_cd = args.hierarchy[0]
                parent_id = args.hierarchy[1] if len(args.hierarchy) > 1 else None
            else:
                vw_cd = 'MT_ZTITLE'
                parent_id = None

            items = db.get_hierarchy(vw_cd, parent_id)
            print(f"\n=== 계층구조: {vw_cd} > {parent_id or '(root)'} ({len(items)}건) ===")
            for item in items[:30]:
                if 'list_id' in item:
                    list_id = item.get('list_id') or ''
                    list_nm = (item.get('list_nm') or '')[:40]
                    rec_type = item.get('rec_tbl_se') or '-'
                    print(f"  [{rec_type}] {list_id}: {list_nm}")
                else:
                    print(f"  {item.get('parent_list_id', '')}")

        elif args.stats:
            stats = db.get_stats()
            print("\n=== KOSIS 메타DB 통계 ===")
            print(f"통계표: {stats['tables']:,}개")
            print(f"계층항목: {stats['hierarchy']:,}개")
            print(f"분류/항목: {stats['classifications']:,}개")

            if stats.get('by_org'):
                print("\n기관별 통계표 (Top 10):")
                for org, cnt in stats['by_org'].items():
                    print(f"  - {org}: {cnt:,}개")

            if stats.get('by_period'):
                print("\n수록주기별 통계표:")
                for code, cnt in sorted(stats['by_period'].items()):
                    name = db.PERIOD_CODES.get(code, code)
                    print(f"  - {name}({code}): {cnt:,}개")

            if stats.get('tables_updated'):
                print(f"\n통계표 업데이트: {stats['tables_updated'][:19]}")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
