#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown to SQLite DB Converter v2.0.0

마크다운 파일을 SQLite DB로 변환하여 저장합니다.
헤더 기반 섹션 계층 구조와 블록 단위 콘텐츠를 분리 저장합니다.

v2.0.0 신규 기능:
- YAML 파싱 고도화 (PyYAML 기반)
- 파일 중복/변경 감지 (SHA256 해시)
- ChromaDB 통합 (--to-chroma)
- 스키마 마이그레이션

Usage:
    # 변환
    python md2db.py input.md output.db
    python md2db.py input.md existing.db --append

    # 조회
    python md2db.py output.db --info
    python md2db.py output.db --sections
    python md2db.py output.db --search "키워드"

    # 내보내기
    python md2db.py output.db --export result.md

    # ChromaDB 변환
    python md2db.py output.db --to-chroma chroma_dir/

    # 마이그레이션
    python md2db.py old.db --migrate
"""

import sys
import argparse
from pathlib import Path

# Windows 환경에서 UTF-8 출력 보장
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 모듈 임포트
from core.parser import MarkdownParser
from core.models import Document
from db.sqlite_writer import DatabaseWriter
from db.sqlite_reader import DatabaseReader
from db.migrator import Migrator
from export.markdown import MarkdownExporter


def print_info(reader: DatabaseReader) -> None:
    """DB 정보 출력"""
    info = reader.get_info()

    print(f"\n=== DB 정보 (v{info['schema_version']}) ===")
    print(f"총 문서 수: {info['total_documents']}")
    print(f"총 섹션 수: {info['total_sections']}")
    print(f"총 블록 수: {info['total_blocks']}")

    print(f"\n--- 문서 목록 ---")
    for doc in info['documents']:
        print(f"[{doc['id']}] {doc['filename']}")
        print(f"    제목: {doc['title']}")
        print(f"    크기: {doc['file_size']:,} bytes")
        print(f"    섹션: {doc['total_sections']}, 블록: {doc['total_blocks']}")

    # v2: source_files 정보
    if info.get('source_files'):
        print(f"\n--- 원본 파일 ({len(info['source_files'])}개) ---")
        for sf in info['source_files'][:5]:  # 최대 5개
            print(f"  {sf['file_path']}")
            print(f"    해시: {sf['file_hash'][:16]}...")
            print(f"    상태: {sf['status']}")


def print_sections(reader: DatabaseReader, document_id: int = None) -> None:
    """섹션 목록 출력"""
    sections = reader.get_sections(document_id)

    print(f"\n=== 섹션 목록 ({len(sections)}개) ===\n")

    for section in sections:
        if section['level'] == 0:
            continue  # 루트 섹션 제외

        indent = "  " * (section['level'] - 1)
        print(f"{indent}{section['path']}. {section['title']}")
        print(f"{indent}   (라인 {section['start_line']}-{section['end_line']})")


def print_search_results(reader: DatabaseReader, query: str) -> None:
    """검색 결과 출력"""
    results = reader.search(query)

    print(f"\n=== '{query}' 검색 결과 ({len(results)}개) ===\n")

    for result in results[:20]:  # 최대 20개
        print(f"[Section {result['section_path']}] {result['section_title']}")
        print(f"  Type: {result['type']}")
        content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
        print(f"  Content: {content_preview}")
        print()


def run_migration(db_path: str) -> None:
    """마이그레이션 실행"""
    migrator = Migrator(db_path)

    current = migrator.get_current_version()
    print(f"[INFO] 현재 스키마 버전: v{current}")

    if not migrator.needs_migration():
        print("[INFO] 마이그레이션이 필요하지 않습니다.")
        return

    print("[INFO] 마이그레이션 시작...")
    result = migrator.migrate(create_backup=True)

    if result['status'] == 'success':
        print(f"[OK] {result['message']}")
        if result.get('backup_path'):
            print(f"[INFO] 백업 파일: {result['backup_path']}")
    else:
        print(f"[ERROR] {result['message']}")


def run_chroma_export(db_path: str, chroma_dir: str, chunk_size: int = 1000,
                      collection_name: str = None, embedding_model: str = None) -> None:
    """ChromaDB로 변환"""
    try:
        from db.chroma_writer import ChromaDBWriter
    except ImportError:
        print("[ERROR] ChromaDB 기능을 사용하려면 chromadb, sentence-transformers 패키지가 필요합니다.")
        print("        pip install chromadb sentence-transformers")
        return

    print(f"[INFO] ChromaDB 변환 시작...")
    print(f"       소스: {db_path}")
    print(f"       대상: {chroma_dir}")

    writer = ChromaDBWriter(
        chroma_path=chroma_dir,
        model_name=embedding_model,
        collection_name=collection_name
    )
    writer.connect()

    chunk_count = writer.from_sqlite(db_path, chunk_size=chunk_size)

    print(f"[OK] ChromaDB 변환 완료")
    print(f"     청크 수: {chunk_count}")
    print(f"     컬렉션: {writer.collection_name}")


def main():
    parser = argparse.ArgumentParser(
        description='Markdown to SQLite DB Converter v2.0.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python md2db.py input.md output.db              # 마크다운 → DB 변환
  python md2db.py input.md existing.db --append   # 기존 DB에 추가
  python md2db.py output.db --info                # DB 정보 조회
  python md2db.py output.db --sections            # 섹션 목록
  python md2db.py output.db --search "키워드"     # 전문 검색
  python md2db.py output.db --export result.md    # DB → 마크다운 복원
  python md2db.py output.db --to-chroma dir/      # ChromaDB 변환
  python md2db.py old.db --migrate                # v1 → v2 마이그레이션
        """
    )

    parser.add_argument('input', help='입력 마크다운 파일 또는 DB 파일')
    parser.add_argument('output', nargs='?', help='출력 DB 파일 (변환 모드)')

    # 변환 옵션
    parser.add_argument('--append', '-a', action='store_true',
                        help='기존 DB에 문서 추가')
    parser.add_argument('--section-level', type=int, default=1,
                        help='섹션 분리 기준 헤더 레벨 (기본: 1)')
    parser.add_argument('--skip-duplicates', action='store_true', default=True,
                        help='동일 해시 파일 스킵 (기본값)')
    parser.add_argument('--force-update', action='store_true',
                        help='동일 해시 파일도 강제 업데이트')

    # 조회 옵션
    parser.add_argument('--info', '-i', action='store_true',
                        help='DB 정보 출력')
    parser.add_argument('--sections', '-s', action='store_true',
                        help='섹션 목록 출력')
    parser.add_argument('--search', '-q', type=str,
                        help='전문 검색')

    # 내보내기 옵션
    parser.add_argument('--export', '-e', type=str,
                        help='마크다운으로 내보내기')
    parser.add_argument('--section', type=str,
                        help='특정 섹션 경로 (예: "1.2")')
    parser.add_argument('--max-level', type=int,
                        help='내보내기 시 최대 헤더 레벨')

    # ChromaDB 옵션
    parser.add_argument('--to-chroma', type=str, metavar='DIR',
                        help='ChromaDB로 변환 (디렉토리 경로)')
    parser.add_argument('--chunk-size', type=int, default=1000,
                        help='ChromaDB 청크 크기 (기본: 1000)')
    parser.add_argument('--collection', type=str,
                        help='ChromaDB 컬렉션 이름')
    parser.add_argument('--embed-model', type=str,
                        help='임베딩 모델 (기본: ko-sroberta)')

    # 마이그레이션 옵션
    parser.add_argument('--migrate', action='store_true',
                        help='v1 → v2 스키마 마이그레이션')

    # 기타
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='상세 로그 출력')
    parser.add_argument('--version', '-V', action='version', version='v2.0.0')

    args = parser.parse_args()

    input_path = Path(args.input)

    # 마이그레이션 모드
    if args.migrate:
        if input_path.suffix.lower() != '.db':
            print("[ERROR] 마이그레이션은 DB 파일에서만 실행할 수 있습니다.")
            return
        run_migration(str(input_path))
        return

    # ChromaDB 변환 모드
    if args.to_chroma:
        if input_path.suffix.lower() != '.db':
            print("[ERROR] ChromaDB 변환은 기존 DB 파일이 필요합니다.")
            return
        run_chroma_export(
            str(input_path),
            args.to_chroma,
            chunk_size=args.chunk_size,
            collection_name=args.collection,
            embedding_model=args.embed_model
        )
        return

    # 모드 판별
    if input_path.suffix.lower() == '.db':
        # DB 조회/내보내기 모드
        with DatabaseReader(str(input_path)) as reader:
            if args.info:
                print_info(reader)
            elif args.sections:
                print_sections(reader)
            elif args.search:
                print_search_results(reader, args.search)
            elif args.export:
                exporter = MarkdownExporter(reader)
                exporter.export(
                    args.export,
                    section_path=args.section,
                    max_level=args.max_level
                )
                print(f"[OK] 내보내기 완료: {args.export}")
            else:
                print_info(reader)
    else:
        # 변환 모드
        import glob as glob_module

        # glob 패턴 지원: 와일드카드(*,?)가 포함되면 확장
        input_str = args.input
        if '*' in input_str or '?' in input_str:
            file_list = sorted(glob_module.glob(input_str))
            if not file_list:
                print(f"[ERROR] 패턴에 일치하는 파일이 없습니다: {input_str}")
                return
            print(f"[INFO] {len(file_list)}개 파일 발견")
        else:
            file_list = [input_str]

        if not args.output:
            # 기본 출력 파일명 (첫 번째 파일 기준)
            args.output = str(Path(file_list[0]).with_suffix('.db'))

        # 중복 감지 옵션
        skip_if_exists = args.skip_duplicates and not args.force_update

        total_docs = 0
        for idx, filepath in enumerate(file_list):
            fp = Path(filepath)
            print(f"[INFO] 파싱 중: {fp} ({idx+1}/{len(file_list)})")

            parser_obj = MarkdownParser()
            doc = parser_obj.parse_file(str(fp))

            print(f"[INFO] 문서: {doc.title}")
            print(f"[INFO] 섹션: {len(doc.sections)}개")
            print(f"[INFO] 블록: {sum(len(s.blocks) for s in doc.sections)}개")
            print(f"[INFO] 단어: {doc.total_words:,}개")

            # 첫 번째 파일 이후는 append 모드
            append_mode = args.append or (idx > 0)

            with DatabaseWriter(args.output, append=append_mode) as writer:
                doc_id, status = writer.save_document(
                    doc,
                    filepath=str(fp),
                    skip_if_exists=skip_if_exists,
                    update_if_changed=args.force_update
                )

            if status == 'skipped':
                print(f"[INFO] 동일 파일 이미 존재 (스킵됨)")
            elif status == 'updated':
                print(f"[OK] 업데이트 완료 (문서 ID: {doc_id})")
                total_docs += 1
            else:
                print(f"[OK] 저장 완료 (문서 ID: {doc_id})")
                total_docs += 1

        print(f"\n[DONE] 총 {total_docs}개 문서 → {args.output}")


if __name__ == '__main__':
    main()
