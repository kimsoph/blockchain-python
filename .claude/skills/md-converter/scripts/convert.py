#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
md-converter: 문서 포맷 → 마크다운 변환 CLI

사용법:
    # 단일 파일 변환
    python convert.py input.hwpx
    python convert.py input.hwpx -o output.md

    # 배치 변환
    python convert.py --batch ./folder/
    python convert.py --batch -r ./folder/  # 재귀

    # 옵션
    python convert.py --doc-type law input.hwpx   # 법률 문서 구조
    python convert.py --doc-type general input.hwpx  # 일반 문서
    python convert.py --dry-run input.hwpx  # 미리보기
    python convert.py --verbose input.hwpx  # 상세 로그
"""

import argparse
import io
import sys
from pathlib import Path
from typing import List

# Windows UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 스크립트 디렉토리를 Python 경로에 추가
SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from converters import ConversionResult
from converters.hwpx import HWPXConverter, get_converter


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='다양한 문서 포맷(HWPX, PDF, DOCX)을 마크다운으로 변환',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  %(prog)s input.hwpx                     # 단일 파일 변환
  %(prog)s input.hwpx -o output.md        # 출력 경로 지정
  %(prog)s --batch ./docs/                # 폴더 내 모든 파일 변환
  %(prog)s --batch -r ./docs/             # 재귀적으로 변환
  %(prog)s --doc-type law input.hwpx      # 법률 문서 구조로 변환
  %(prog)s --dry-run input.hwpx           # 미리보기 (파일 생성 안 함)
"""
    )

    # 위치 인자
    parser.add_argument(
        'input',
        nargs='?',
        help='변환할 파일 경로'
    )

    # 출력 옵션
    parser.add_argument(
        '-o', '--output',
        help='출력 파일 경로 (기본: 입력 파일과 같은 디렉토리에 자동 생성)'
    )

    # 배치 모드
    parser.add_argument(
        '--batch',
        action='store_true',
        help='배치 모드: 폴더 내 모든 지원 파일 변환'
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='재귀적으로 하위 폴더까지 검색 (--batch와 함께 사용)'
    )

    # 포맷/유형 옵션
    parser.add_argument(
        '--format',
        choices=['hwpx', 'pdf', 'docx', 'auto'],
        default='auto',
        help='입력 파일 포맷 (기본: auto - 확장자로 자동 감지)'
    )
    parser.add_argument(
        '--doc-type',
        choices=['auto', 'law', 'general'],
        default='auto',
        help='문서 유형 (기본: auto - 내용으로 자동 감지)'
    )

    # 동작 옵션
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='미리보기 모드: 변환 결과를 stdout에 출력 (파일 생성 안 함)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='기존 출력 파일 덮어쓰기'
    )

    # 출력 옵션
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='상세 로그 출력'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='에러만 출력'
    )

    return parser.parse_args()


def find_files(path: Path, recursive: bool = False) -> List[Path]:
    """
    변환 가능한 파일 찾기

    Args:
        path: 검색 경로 (파일 또는 디렉토리)
        recursive: 재귀 검색 여부

    Returns:
        List[Path]: 파일 경로 리스트
    """
    supported_extensions = {'.hwpx'}  # 향후 .pdf, .docx 추가

    if path.is_file():
        if path.suffix.lower() in supported_extensions:
            return [path]
        return []

    if path.is_dir():
        pattern = '**/*' if recursive else '*'
        files = []
        for ext in supported_extensions:
            files.extend(path.glob(f'{pattern}{ext}'))
        return sorted(files)

    return []


def convert_file(
    input_path: Path,
    output_path: Path = None,
    doc_type: str = 'auto',
    dry_run: bool = False,
    verbose: bool = False,
    overwrite: bool = False
) -> ConversionResult:
    """
    단일 파일 변환

    Args:
        input_path: 입력 파일 경로
        output_path: 출력 파일 경로
        doc_type: 문서 유형
        dry_run: 미리보기 모드
        verbose: 상세 로그
        overwrite: 덮어쓰기

    Returns:
        ConversionResult: 변환 결과
    """
    try:
        converter = get_converter(input_path)
    except ValueError as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            error=str(e)
        )

    # doc_type 설정
    if hasattr(converter, 'doc_type'):
        converter.doc_type = doc_type

    # 출력 경로 확인
    if output_path and output_path.exists() and not overwrite:
        return ConversionResult(
            success=False,
            input_path=input_path,
            error=f"출력 파일이 이미 존재합니다: {output_path} (--overwrite 옵션 사용)"
        )

    if dry_run:
        # 미리보기 모드: 변환은 하되 파일 저장 안 함
        # 임시 경로로 변환 후 내용 출력
        result = converter.convert(input_path, output_path)
        if result.success and result.output_path:
            content = result.output_path.read_text(encoding='utf-8')
            print(f"\n{'='*60}")
            print(f"[미리보기] {input_path.name}")
            print('='*60)
            print(content[:2000])  # 앞부분만 출력
            if len(content) > 2000:
                print(f"\n... (총 {len(content)} 문자, 이하 생략)")
            print('='*60)
            # 미리보기 후 파일 삭제
            result.output_path.unlink()
            result.output_path = None
        return result
    else:
        return converter.convert(input_path, output_path)


def main():
    """메인 함수"""
    args = parse_args()

    # 입력 검증
    if not args.input:
        print("오류: 입력 파일 또는 폴더를 지정해주세요.", file=sys.stderr)
        print("사용법: python convert.py <input_file> 또는 python convert.py --batch <folder>")
        sys.exit(1)

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"오류: 경로를 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 파일 목록 수집
    if args.batch or input_path.is_dir():
        files = find_files(input_path, args.recursive)
        if not files:
            print(f"변환 가능한 파일을 찾을 수 없습니다: {input_path}")
            sys.exit(0)
    else:
        files = [input_path]

    # 변환 실행
    results = []
    success_count = 0
    fail_count = 0

    for file_path in files:
        if not args.quiet:
            print(f"변환 중: {file_path.name}...", end=' ')

        # 출력 경로 결정
        output_path = Path(args.output) if args.output and len(files) == 1 else None

        result = convert_file(
            input_path=file_path,
            output_path=output_path,
            doc_type=args.doc_type,
            dry_run=args.dry_run,
            verbose=args.verbose,
            overwrite=args.overwrite
        )

        results.append(result)

        if result.success:
            success_count += 1
            if not args.quiet:
                print(f"✓ → {result.output_path.name if result.output_path else '(미리보기)'}")
            if args.verbose and result.output_path:
                print(f"  제목: {result.title}")
                print(f"  유형: {result.doc_type}")
                print(f"  출력: {result.output_path}")
        else:
            fail_count += 1
            if not args.quiet:
                print(f"✗ {result.error}")

    # 요약
    if len(files) > 1 and not args.quiet:
        print(f"\n{'='*40}")
        print(f"총 {len(files)}개 파일 중 {success_count}개 성공, {fail_count}개 실패")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == '__main__':
    main()
