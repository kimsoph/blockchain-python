#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZK-PARA Vault 메타데이터 DB 관리 스크립트
YAML frontmatter를 파싱하여 SQLite DB로 저장

사용법:
    python meta_db.py --init          # DB 초기화
    python meta_db.py --sync          # 전체 동기화
    python meta_db.py --search "검색어"  # 검색
    python meta_db.py --info          # DB 통계

한글 인코딩 처리:
    - 모든 파일 경로는 NFC 정규화 적용
    - SQLite는 UTF-8 인코딩 강제
    - Windows 콘솔 UTF-8 출력 설정
"""

import argparse
import io
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================
# 한글 인코딩 설정 (최우선 실행)
# ============================================================

# 환경 변수 강제 설정 (Python UTF-8 모드)
os.environ['PYTHONUTF8'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == 'win32':
    # 콘솔 코드 페이지를 UTF-8로 변경 시도
    try:
        import subprocess
        subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
    except Exception:
        pass

    # stdout/stderr UTF-8 래퍼
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================
# 설정
# ============================================================

VAULT_ROOT = Path(__file__).resolve().parents[4]  # ZK-PARA 폴더
DB_PATH = VAULT_ROOT / ".claude" / "ZK-PARA.db"

# 제외할 폴더
EXCLUDE_DIRS = {
    '.claude',
    '.git',
    '.obsidian',
    'node_modules',
    '__pycache__',
    '.venv',
    'venv',
}

# 폴더 카테고리 매핑
FOLDER_CATEGORY_MAP = {
    '0_Inbox': 'Inbox',
    '1_Projects': 'Projects',
    '2_Areas': 'Areas',
    '3_Resources': 'Resources',
    '4_Archive': 'Archive',
    '5_Zettelkasten': 'Zettelkasten',
    '9_Attachments': 'Attachments',
    '9_Imports': 'Imports',
    '9_Templates': 'Templates',
    '_Docs': 'Docs',
}

# ============================================================
# 한글 인코딩 유틸리티
# ============================================================

def normalize_path(path_str: str) -> str:
    """
    파일 경로를 NFC 정규화.
    Windows에서 한글 파일명의 조합형(NFD)/완성형(NFC) 불일치 문제 해결.
    macOS는 NFD를 사용하고, Windows/Linux는 NFC를 사용함.
    """
    return unicodedata.normalize('NFC', path_str)


def normalize_text(text) -> str:
    """텍스트를 NFC 정규화. 리스트인 경우 ', '로 조인"""
    if text is None:
        return None
    if isinstance(text, list):
        # 리스트 요소를 문자열로 변환 후 조인
        text = ', '.join(str(item) for item in text)
    if not isinstance(text, str):
        text = str(text)
    return unicodedata.normalize('NFC', text)


def safe_path_str(path: Path, base: Path) -> str:
    """
    Path 객체를 안전한 문자열로 변환.
    - NFC 정규화
    - 백슬래시를 슬래시로 변환
    - 상대 경로로 변환
    """
    rel_path = path.relative_to(base)
    path_str = str(rel_path).replace('\\', '/')
    return normalize_path(path_str)


def read_file_with_fallback(file_path: Path) -> tuple[str, str]:
    """
    다양한 인코딩으로 파일 읽기 시도.
    순서: utf-8 → utf-8-sig → cp949 → euc-kr → utf-8(errors='replace')

    Returns:
        (content, encoding_used) 튜플
    """
    encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            return content, enc
        except (UnicodeDecodeError, UnicodeError):
            continue

    # 최후의 수단: UTF-8 + 대체 문자
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read(), 'utf-8-fallback'


def convert_to_utf8(file_path: Path, content: str) -> bool:
    """
    파일을 UTF-8로 변환하여 저장.

    Args:
        file_path: 변환할 파일 경로
        content: 이미 읽은 파일 내용

    Returns:
        성공 여부
    """
    try:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        return True
    except Exception:
        return False


def get_sqlite_connection(db_path: Path) -> sqlite3.Connection:
    """
    UTF-8 인코딩이 보장된 SQLite 연결 생성.
    """
    conn = sqlite3.connect(db_path)
    # UTF-8 인코딩 확인 (SQLite 기본값이지만 명시적 확인)
    cursor = conn.cursor()
    cursor.execute("PRAGMA encoding")
    encoding = cursor.fetchone()[0]
    if encoding != 'UTF-8':
        print(f"⚠ DB 인코딩이 UTF-8이 아님: {encoding}")

    # 외래 키 제약 활성화
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ============================================================
# 유틸리티 함수
# ============================================================

def parse_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """YAML frontmatter 파싱. (frontmatter_dict, body) 반환"""
    if not content.startswith('---'):
        return {}, content

    # YAML 블록 끝 찾기
    end_match = re.search(r'\n---\s*\n', content[3:])
    if not end_match:
        return {}, content

    yaml_str = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:]

    # 간단한 YAML 파싱 (PyYAML 없이)
    frontmatter = {}
    current_key = None
    list_values = []

    for line in yaml_str.split('\n'):
        line = line.rstrip()
        if not line or line.startswith('#'):
            continue

        # 리스트 아이템
        if line.startswith('  - ') or line.startswith('- '):
            if current_key:
                value = line.lstrip(' -').strip()
                list_values.append(value)
            continue

        # 이전 리스트 저장
        if current_key and list_values:
            frontmatter[current_key] = list_values
            list_values = []

        # key: value 파싱
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()

            # 값 정리
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            elif value.startswith('[') and value.endswith(']'):
                # 인라인 배열
                items = value[1:-1].split(',')
                value = [item.strip().strip('"\'') for item in items if item.strip()]

            if value == '' or value == '[]':
                current_key = key
                list_values = []
            else:
                frontmatter[key] = value
                current_key = None

    # 마지막 리스트 저장
    if current_key and list_values:
        frontmatter[current_key] = list_values

    return frontmatter, body


def extract_title_from_body(body: str) -> Optional[str]:
    """본문에서 첫 번째 헤딩 추출"""
    for line in body.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return None


def extract_wikilinks(content: str) -> list[dict]:
    """위키링크 추출. [[target|display]] 또는 ![[embed]] 형식"""
    links = []

    # 일반 위키링크: [[target]] 또는 [[target|display]]
    for match in re.finditer(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', content):
        target = match.group(1).strip()
        display = match.group(2).strip() if match.group(2) else None
        links.append({
            'target': target,
            'display': display,
            'type': 'wikilink'
        })

    # 임베드: ![[embed]]
    for match in re.finditer(r'!\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content):
        target = match.group(1).strip()
        links.append({
            'target': target,
            'display': None,
            'type': 'embed'
        })

    return links


def get_folder_category(file_path: Path) -> str:
    """파일 경로에서 폴더 카테고리 추출"""
    rel_path = file_path.relative_to(VAULT_ROOT)
    parts = rel_path.parts

    if parts:
        top_folder = parts[0]
        return FOLDER_CATEGORY_MAP.get(top_folder, 'Other')
    return 'Other'


def get_folder_path(file_path: Path) -> str:
    """상위 폴더 경로 (상대 경로)"""
    rel_path = file_path.relative_to(VAULT_ROOT)
    return str(rel_path.parent).replace('\\', '/')


def count_words(text: str) -> int:
    """단어 수 계산 (한글 + 영어)"""
    # 한글은 글자 수, 영어는 단어 수
    korean = len(re.findall(r'[\uac00-\ud7af]', text))
    english = len(re.findall(r'[a-zA-Z]+', text))
    return korean + english


def get_summary(body: str, max_length: int = 200) -> str:
    """본문 요약 (첫 N자)"""
    # 헤딩과 빈 줄 제거
    lines = []
    for line in body.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            lines.append(line)
        if len(' '.join(lines)) > max_length:
            break

    summary = ' '.join(lines)[:max_length]
    if len(summary) == max_length:
        summary = summary.rsplit(' ', 1)[0] + '...'
    return summary


# ============================================================
# DB 스키마
# ============================================================

SCHEMA_SQL = """
-- 노트 메타데이터
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    title TEXT,
    author TEXT,
    note_type TEXT,
    source TEXT,
    status TEXT,
    created TEXT,
    updated TEXT,
    date_consumed TEXT,
    folder_category TEXT,
    folder_path TEXT,
    summary TEXT,
    word_count INTEGER,
    has_frontmatter INTEGER DEFAULT 0,
    frontmatter_raw TEXT,
    indexed_at TEXT
);

-- 태그
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT UNIQUE NOT NULL
);

-- 노트-태그 관계
CREATE TABLE IF NOT EXISTS note_tags (
    note_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 노트 간 링크
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    target_note TEXT NOT NULL,
    link_type TEXT DEFAULT 'wikilink',
    display_text TEXT,
    FOREIGN KEY (source_path) REFERENCES notes(file_path) ON DELETE CASCADE
);

-- 메타 정보
CREATE TABLE IF NOT EXISTS meta_info (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_notes_folder_category ON notes(folder_category);
CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author);
CREATE INDEX IF NOT EXISTS idx_notes_note_type ON notes(note_type);
CREATE INDEX IF NOT EXISTS idx_notes_status ON notes(status);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_path);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_note);
"""


# ============================================================
# DB 작업
# ============================================================

def init_db():
    """DB 초기화 (스키마 생성)"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_sqlite_connection(DB_PATH)
    conn.executescript(SCHEMA_SQL)

    # 메타 정보 초기화
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO meta_info (key, value, updated_at) VALUES (?, ?, ?)",
        ('schema_version', '1.0', now)
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta_info (key, value, updated_at) VALUES (?, ?, ?)",
        ('vault_root', str(VAULT_ROOT), now)
    )

    conn.commit()
    conn.close()
    print(f"✓ DB 초기화 완료: {DB_PATH}")


def sync_all(verbose: bool = False):
    """
    전체 동기화 (YAML → DB)

    Args:
        verbose: True면 각 파일 처리 상황 출력
    """
    if not DB_PATH.exists():
        print("DB가 없습니다. --init으로 먼저 초기화하세요.")
        return

    conn = get_sqlite_connection(DB_PATH)
    cursor = conn.cursor()

    # 기존 데이터 삭제
    cursor.execute("DELETE FROM note_tags")
    cursor.execute("DELETE FROM links")
    cursor.execute("DELETE FROM notes")
    # tags는 유지 (재사용)

    now = datetime.now().isoformat()
    note_count = 0
    link_count = 0
    error_count = 0
    tag_cache = {}  # tag_name -> tag_id

    # 인코딩 관련 추적 변수
    error_details: list[tuple[str, str, str]] = []  # (file_path, error_type, message)
    encoding_conversions: list[tuple[str, str]] = []  # (file_path, original_encoding)
    conversion_failures: list[tuple[str, str]] = []  # (file_path, error_message)

    # 기존 태그 로드
    for row in cursor.execute("SELECT id, tag_name FROM tags"):
        tag_cache[normalize_text(row[1])] = row[0]

    # 마크다운 파일 순회
    md_files = list(VAULT_ROOT.rglob('*.md'))
    total_files = len(md_files)
    print(f"📂 발견된 마크다운 파일: {total_files}개")

    for idx, md_file in enumerate(md_files, 1):
        # 제외 폴더 체크
        rel_path = md_file.relative_to(VAULT_ROOT)
        if any(part in EXCLUDE_DIRS for part in rel_path.parts):
            continue

        try:
            # 파일 읽기 (다중 인코딩 fallback)
            content, encoding_used = read_file_with_fallback(md_file)

            # BOM 제거 (혹시 남아있을 경우)
            if content.startswith('\ufeff'):
                content = content[1:]

            # 내용 NFC 정규화
            content = normalize_text(content)

            # UTF-8 외 인코딩 파일은 자동 변환
            if encoding_used not in ('utf-8', 'utf-8-sig'):
                if convert_to_utf8(md_file, content):
                    encoding_conversions.append((str(rel_path), encoding_used))
                else:
                    conversion_failures.append((str(rel_path), f"변환 실패 (원본: {encoding_used})"))
        except Exception as e:
            error_details.append((str(rel_path), 'file_access', str(e)))
            error_count += 1
            if verbose:
                print(f"  ⚠ 읽기 실패 [{idx}/{total_files}]: {rel_path} - {e}")
            continue

        # YAML 파싱
        frontmatter, body = parse_yaml_frontmatter(content)
        has_frontmatter = 1 if frontmatter else 0

        # 제목 추출 (NFC 정규화)
        title = frontmatter.get('title')
        if not title:
            title = extract_title_from_body(body)
        if not title:
            title = md_file.stem
        title = normalize_text(str(title))

        # 노트 데이터 준비 (경로는 safe_path_str로 정규화)
        file_path_str = safe_path_str(md_file, VAULT_ROOT)
        file_name = normalize_path(md_file.name)

        note_data = {
            'file_path': file_path_str,
            'file_name': file_name,
            'title': title,
            'author': normalize_text(frontmatter.get('author')),
            'note_type': normalize_text(frontmatter.get('type')),
            'source': normalize_text(frontmatter.get('source')),
            'status': normalize_text(frontmatter.get('status')),
            'created': str(frontmatter.get('created', '')),
            'updated': str(frontmatter.get('updated', '')),
            'date_consumed': str(frontmatter.get('date_consumed', '')),
            'folder_category': get_folder_category(md_file),
            'folder_path': get_folder_path(md_file),
            'summary': get_summary(body),
            'word_count': count_words(content),
            'has_frontmatter': has_frontmatter,
            'frontmatter_raw': json.dumps(frontmatter, ensure_ascii=False) if frontmatter else None,
            'indexed_at': now,
        }

        # 노트 삽입
        cursor.execute("""
            INSERT INTO notes (
                file_path, file_name, title, author, note_type, source, status,
                created, updated, date_consumed, folder_category, folder_path,
                summary, word_count, has_frontmatter, frontmatter_raw, indexed_at
            ) VALUES (
                :file_path, :file_name, :title, :author, :note_type, :source, :status,
                :created, :updated, :date_consumed, :folder_category, :folder_path,
                :summary, :word_count, :has_frontmatter, :frontmatter_raw, :indexed_at
            )
        """, note_data)

        note_id = cursor.lastrowid
        note_count += 1

        # 태그 처리 (NFC 정규화 적용)
        tags = frontmatter.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]

        for tag_name in tags:
            tag_name = normalize_text(str(tag_name).strip())
            if not tag_name:
                continue

            # 태그 ID 가져오기 (없으면 생성)
            if tag_name not in tag_cache:
                cursor.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?)", (tag_name,))
                cursor.execute("SELECT id FROM tags WHERE tag_name = ?", (tag_name,))
                tag_cache[tag_name] = cursor.fetchone()[0]

            tag_id = tag_cache[tag_name]
            cursor.execute(
                "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                (note_id, tag_id)
            )

        # 링크 추출 (타겟 경로도 NFC 정규화)
        links = extract_wikilinks(content)
        for link in links:
            target = normalize_text(link['target'])
            display = normalize_text(link['display']) if link['display'] else None
            cursor.execute("""
                INSERT INTO links (source_path, target_note, link_type, display_text)
                VALUES (?, ?, ?, ?)
            """, (file_path_str, target, link['type'], display))
            link_count += 1

        # 진행 상황 출력 (verbose 모드 또는 100개마다)
        if verbose or (idx % 100 == 0):
            print(f"  처리 중: {idx}/{total_files} - {file_name}")

    # 메타 정보 업데이트
    cursor.execute(
        "INSERT OR REPLACE INTO meta_info (key, value, updated_at) VALUES (?, ?, ?)",
        ('last_sync', now, now)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO meta_info (key, value, updated_at) VALUES (?, ?, ?)",
        ('note_count', str(note_count), now)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO meta_info (key, value, updated_at) VALUES (?, ?, ?)",
        ('link_count', str(link_count), now)
    )

    conn.commit()
    conn.close()

    print(f"\n✓ 동기화 완료")
    print(f"  - 노트: {note_count}개")
    print(f"  - 링크: {link_count}개")
    print(f"  - 태그: {len(tag_cache)}개")

    # UTF-8 자동 변환 결과 출력
    if encoding_conversions:
        print(f"\n✓ UTF-8 자동 변환 ({len(encoding_conversions)}개):")
        for file_path, enc in encoding_conversions[:10]:
            print(f"    - {file_path} ({enc} → UTF-8)")
        if len(encoding_conversions) > 10:
            print(f"    ... 외 {len(encoding_conversions) - 10}개")

    # 변환 실패 출력
    if conversion_failures:
        print(f"\n⚠ UTF-8 변환 실패 ({len(conversion_failures)}개):")
        for file_path, msg in conversion_failures[:10]:
            print(f"    - {file_path}: {msg}")
        if len(conversion_failures) > 10:
            print(f"    ... 외 {len(conversion_failures) - 10}개")

    # 오류 상세 출력
    if error_details:
        print(f"\n⚠ 처리 실패 파일 ({len(error_details)}개):")
        for file_path, error_type, msg in error_details[:10]:
            print(f"    - [{error_type}] {file_path}: {msg}")
        if len(error_details) > 10:
            print(f"    ... 외 {len(error_details) - 10}개")


def search(keyword: str):
    """키워드 검색"""
    if not DB_PATH.exists():
        print("DB가 없습니다. --init으로 먼저 초기화하세요.")
        return

    # 검색어 NFC 정규화
    keyword = normalize_text(keyword)

    conn = get_sqlite_connection(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT file_path, title, author, folder_category, note_type
        FROM notes
        WHERE title LIKE ? OR author LIKE ? OR summary LIKE ?
        ORDER BY folder_category, title
    """
    pattern = f'%{keyword}%'
    cursor.execute(query, (pattern, pattern, pattern))

    results = cursor.fetchall()
    conn.close()

    if not results:
        print(f"'{keyword}' 검색 결과 없음")
        return

    print(f"'{keyword}' 검색 결과: {len(results)}건\n")
    for row in results:
        file_path, title, author, category, note_type = row
        author_str = f" - {author}" if author else ""
        type_str = f" [{note_type}]" if note_type else ""
        print(f"  [{category}] {title}{author_str}{type_str}")
        print(f"    → {file_path}")


def search_by_tag(tag_name: str):
    """태그로 검색"""
    if not DB_PATH.exists():
        print("DB가 없습니다.")
        return

    # 태그명 NFC 정규화
    tag_name = normalize_text(tag_name)

    conn = get_sqlite_connection(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT n.file_path, n.title, n.author, n.folder_category
        FROM notes n
        JOIN note_tags nt ON n.id = nt.note_id
        JOIN tags t ON nt.tag_id = t.id
        WHERE t.tag_name = ?
        ORDER BY n.folder_category, n.title
    """
    cursor.execute(query, (tag_name,))

    results = cursor.fetchall()
    conn.close()

    if not results:
        print(f"태그 '{tag_name}' 검색 결과 없음")
        return

    print(f"태그 '{tag_name}' 검색 결과: {len(results)}건\n")
    for row in results:
        file_path, title, author, category = row
        author_str = f" - {author}" if author else ""
        print(f"  [{category}] {title}{author_str}")
        print(f"    → {file_path}")


def search_by_category(category: str):
    """폴더 카테고리로 검색"""
    if not DB_PATH.exists():
        print("DB가 없습니다.")
        return

    # 카테고리 NFC 정규화
    category = normalize_text(category)

    conn = get_sqlite_connection(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT file_path, title, author, note_type
        FROM notes
        WHERE folder_category = ?
        ORDER BY title
    """
    cursor.execute(query, (category,))

    results = cursor.fetchall()
    conn.close()

    if not results:
        print(f"카테고리 '{category}' 검색 결과 없음")
        return

    print(f"카테고리 '{category}' 검색 결과: {len(results)}건\n")
    for row in results:
        file_path, title, author, note_type = row
        author_str = f" - {author}" if author else ""
        type_str = f" [{note_type}]" if note_type else ""
        print(f"  {title}{author_str}{type_str}")
        print(f"    → {file_path}")


def execute_query(query: str):
    """직접 쿼리 실행"""
    if not DB_PATH.exists():
        print("DB가 없습니다.")
        return

    conn = get_sqlite_connection(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(query)
        results = cursor.fetchall()

        if cursor.description:
            headers = [desc[0] for desc in cursor.description]
            print(" | ".join(headers))
            print("-" * (len(" | ".join(headers))))

            for row in results:
                print(" | ".join(str(v) if v else "" for v in row))

        print(f"\n총 {len(results)}건")
    except Exception as e:
        print(f"쿼리 오류: {e}")
    finally:
        conn.close()


def show_info():
    """DB 통계 정보"""
    if not DB_PATH.exists():
        print("DB가 없습니다. --init으로 먼저 초기화하세요.")
        return

    conn = get_sqlite_connection(DB_PATH)
    cursor = conn.cursor()

    print("=" * 50)
    print("ZK-PARA 메타DB 통계")
    print("=" * 50)

    # 기본 정보
    print(f"\nDB 위치: {DB_PATH}")
    print(f"DB 크기: {DB_PATH.stat().st_size / 1024:.1f} KB")

    # 메타 정보
    cursor.execute("SELECT key, value, updated_at FROM meta_info")
    print("\n[메타 정보]")
    for key, value, updated_at in cursor.fetchall():
        print(f"  {key}: {value} ({updated_at[:10]})")

    # 전체 노트 수
    cursor.execute("SELECT COUNT(*) FROM notes")
    total_notes = cursor.fetchone()[0]
    print(f"\n[전체 노트: {total_notes}개]")

    # 폴더 카테고리별
    cursor.execute("""
        SELECT folder_category, COUNT(*) as cnt
        FROM notes
        GROUP BY folder_category
        ORDER BY cnt DESC
    """)
    print("\n[카테고리별]")
    for category, cnt in cursor.fetchall():
        print(f"  {category}: {cnt}개")

    # 노트 유형별
    cursor.execute("""
        SELECT note_type, COUNT(*) as cnt
        FROM notes
        WHERE note_type IS NOT NULL
        GROUP BY note_type
        ORDER BY cnt DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
    if results:
        print("\n[유형별 TOP 10]")
        for note_type, cnt in results:
            print(f"  {note_type}: {cnt}개")

    # 상위 태그
    cursor.execute("""
        SELECT t.tag_name, COUNT(*) as cnt
        FROM tags t
        JOIN note_tags nt ON t.id = nt.tag_id
        GROUP BY t.tag_name
        ORDER BY cnt DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
    if results:
        print("\n[태그 TOP 10]")
        for tag_name, cnt in results:
            print(f"  {tag_name}: {cnt}개")

    # 저자별
    cursor.execute("""
        SELECT author, COUNT(*) as cnt
        FROM notes
        WHERE author IS NOT NULL
        GROUP BY author
        ORDER BY cnt DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
    if results:
        print("\n[저자 TOP 10]")
        for author, cnt in results:
            print(f"  {author}: {cnt}개")

    # 링크 통계
    cursor.execute("SELECT COUNT(*) FROM links")
    total_links = cursor.fetchone()[0]
    print(f"\n[링크: {total_links}개]")

    # 가장 많이 참조되는 노트
    cursor.execute("""
        SELECT target_note, COUNT(*) as cnt
        FROM links
        GROUP BY target_note
        ORDER BY cnt DESC
        LIMIT 5
    """)
    results = cursor.fetchall()
    if results:
        print("\n[가장 많이 참조되는 노트 TOP 5]")
        for target, cnt in results:
            print(f"  {target}: {cnt}회")

    conn.close()
    print("\n" + "=" * 50)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='ZK-PARA Vault 메타DB 관리 (한글 인코딩 완전 지원)')
    parser.add_argument('--init', action='store_true', help='DB 초기화')
    parser.add_argument('--sync', action='store_true', help='전체 동기화')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 출력 모드')
    parser.add_argument('--search', type=str, help='키워드 검색')
    parser.add_argument('--tag', type=str, help='태그로 검색')
    parser.add_argument('--category', type=str, help='카테고리로 검색')
    parser.add_argument('--query', type=str, help='직접 SQL 쿼리')
    parser.add_argument('--info', action='store_true', help='DB 통계')

    args = parser.parse_args()

    if args.init:
        init_db()
    elif args.sync:
        sync_all(verbose=args.verbose)
    elif args.search:
        search(args.search)
    elif args.tag:
        search_by_tag(args.tag)
    elif args.category:
        search_by_category(args.category)
    elif args.query:
        execute_query(args.query)
    elif args.info:
        show_info()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
