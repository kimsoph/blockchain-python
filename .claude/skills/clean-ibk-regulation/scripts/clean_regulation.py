# -*- coding: utf-8 -*-
"""
IBK 내규 문서 클리닝 스크립트
.claude/skills/clean-ibk-regulation/

Features:
- 제/개정 이력 테이블 → 최종 개정일만 표기
- 잘못된 헤더 제거 (페이지 넘김 아티팩트)
- 조문 구조 인식 (제X조, ①②③, 1. 2. 3.)
- 불완전 문장 연결 (빈 줄 넘어서도)
"""
import re
import json
import argparse
import logging
from pathlib import Path
from typing import Optional

__version__ = "1.3.0"

# 스킬 디렉토리 기준 경로
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
MANUAL_REVISIONS_FILE = DATA_DIR / "manual_revisions.json"

# 로깅 설정
logger = logging.getLogger(__name__)


def load_manual_revisions() -> dict:
    """수동 개정일 파일 로드"""
    if MANUAL_REVISIONS_FILE.exists():
        try:
            with open(MANUAL_REVISIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # _comment 키 제거
                return {k: v for k, v in data.items() if not k.startswith('_')}
        except Exception as e:
            logger.warning(f"수동 개정일 파일 로드 실패: {e}")
    return {}


def extract_revision_info(lines: list) -> tuple:
    """
    제/개정 이력 테이블에서 최종 개정일 추출 (불규칙 형식 대응)
    Returns: (last_date, last_revision, table_end_index)
    """
    table_start = -1
    table_end = -1
    all_revisions = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 테이블 행 감지 (| 포함)
        if '|' in stripped:
            if table_start == -1:
                table_start = i
            table_end = i

            # 날짜와 개정 정보 추출 (정규식으로)
            # 날짜 패턴: YYYY. M.DD. 또는 YYYY.MM.DD
            dates = re.findall(r'(\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?)', stripped)
            # 개정 패턴: 제XX차 개정 또는 제정
            revisions = re.findall(r'(제\d+차\s*개정|제정)', stripped)

            for date in dates:
                # 날짜 정규화
                norm_date = re.sub(r'\s+', '', date).rstrip('.')
                if revisions:
                    all_revisions.append((norm_date, revisions[-1]))
                else:
                    all_revisions.append((norm_date, None))

        else:
            # 테이블이 끝남
            if table_start != -1 and table_end != -1:
                # 다음 줄이 빈 줄이거나 본문이면 테이블 종료
                if not stripped or stripped.startswith('제') or stripped.startswith('##'):
                    break

    # 마지막 유효한 개정 정보 찾기
    last_date = None
    last_revision = None
    for date, rev in reversed(all_revisions):
        if rev:
            last_date = date
            last_revision = rev
            break
        elif date and not last_date:
            last_date = date

    # 개정 정보 없이 날짜만 있는 경우
    if last_date and not last_revision:
        # all_revisions에서 가장 마지막 개정 정보 찾기
        for _, rev in reversed(all_revisions):
            if rev:
                last_revision = rev
                break

    return last_date, last_revision, table_end


def is_valid_header(line: str) -> bool:
    """유효한 헤더인지 확인 (제X장, 제X절, 부칙, 별표)"""
    valid_patterns = [
        r'^#\s*제\d+장',
        r'^#\s*제\d+절',
        r'^#\s*부\s*칙',
        r'^#\s*\[별표',
        r'^#\s*별표',
    ]
    stripped = line.strip()
    for pattern in valid_patterns:
        if re.match(pattern, stripped):
            return True
    return False


def is_article_start(text: str) -> bool:
    """조문 시작인지 확인 (제X조)"""
    return bool(re.match(r'^제\d+조의?\d*\s*[\(（]', text.strip()))


def is_paragraph_start(text: str) -> bool:
    """항번호 시작인지 확인 (①~⑳)"""
    return bool(re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]', text.strip()))


def is_number_item(text: str) -> bool:
    """호번호 시작인지 확인 (1. 2. 3.)"""
    return bool(re.match(r'^\d+\.', text.strip()))


def is_subparagraph_marker(text: str) -> bool:
    """소제목 마커인지 확인 (예: (가) (나))"""
    return bool(re.match(r'^[\(（][^)）]+[\)）]$', text.strip()))


def is_structure_start(text: str) -> bool:
    """조문 구조 시작 여부 확인"""
    stripped = text.strip()
    if is_article_start(stripped): return True
    if is_paragraph_start(stripped): return True
    if is_number_item(stripped): return True
    if is_subparagraph_marker(stripped): return True
    if stripped.startswith('## '): return True
    if stripped.startswith('[본조'): return True
    return False


def is_incomplete_ending(text: str) -> bool:
    """불완전한 문장 끝인지 확인"""
    stripped = text.strip()
    if not stripped:
        return False
    incomplete_patterns = [
        r'이전$', r'의$', r'에$', r'를$', r'을$', r'는$', r'로$',
        r'와$', r'과$', r'및$', r'또는$', r'중$', r'시$', r'후$',
        r'한$', r'할$', r'할\s수$', r'아니한$', r'표시$', r'정하$',
        r'없$', r'위촉$', r'결정$', r'재직$', r'사항$', r'절차$',
        r'거$', r'없는$', r'위원장이$', r'어느$', r'구성$',
        r'포함$', r'심의$', r'담당$', r'자격$',
        # v1.1 추가 패턴
        r'우대사$', r'채용사$', r'변경사$', r'관한$', r'따른$',
        r'위한$', r'대한$', r'정한$', r'각$', r'해당$',
        r'규정에$', r'경우에$', r'때에$', r'자에$', r'자가$',
    ]
    for pattern in incomplete_patterns:
        if re.search(pattern, stripped):
            return True
    return False


def is_continuation_fragment(text: str) -> bool:
    """연결 조각인지 확인"""
    stripped = text.strip()
    if not stripped:
        return False
    continuation_patterns = [
        r'^으로\b', r'^는\b', r'^을\b', r'^를\b', r'^에\b', r'^의\b',
        r'^와\b', r'^과\b', r'^로\b', r'^만,', r'^며\b', r'^고\b',
        r'^한다', r'^수\s있', r'^에도\b', r'^때에는', r'^\d+월',
        r'^인\s자', r'^하여\b', r'^쳐\b', r'^단위로', r'^내용$',
        r'^찬성', r'^다\.$', r'^다\.<', r'^지원부장', r'^소의',
        # v1.1 추가 패턴
        r'^항\s', r'^등에\s', r'^호의\s', r'^바에\s', r'^유를\s',
        r'^원을\s', r'^용의\s', r'^용에\s', r'^항을\s', r'^항에\s',
    ]
    for pattern in continuation_patterns:
        if re.match(pattern, stripped):
            return True
    return False


def fix_word_spacing(text: str) -> str:
    """잘못된 단어 공백 수정"""
    patterns = [
        # 호번호 마침표 누락: "9 타부서" → "9. 타부서" (줄 시작)
        (r'^(\d+) ([가-힣])', r'\1. \2'),
        # 숫자 사이 공백: "1 1 정부" → "11. 정부" (줄 시작)
        (r'^(\d) (\d+) ', r'\1\2. '),
        # 조문 번호 공백 제거 (일반화)
        (r'제\s*(\d+)\s*조', r'제\1조'),
        (r'제\s*(\d+)\s*항', r'제\1항'),
        (r'제\s*(\d+)\s*호', r'제\1호'),
        (r'제\s*(\d+)\s*장', r'제\1장'),
        (r'제\s*(\d+)\s*절', r'제\1절'),
        # 특수 패턴
        (r'적재적\s+소의', '적재적소의'),
        (r'재직\s+중\s+인\s+자', '재직 중인 자'),
        (r'같을\s+때에\s+는', '같을 때에는'),
        (r'경우에\s+는', '경우에는'),
        (r'목적\s+으로\s+한다', '목적으로 한다'),
        (r'원칙으로\s+한다', '원칙으로 한다'),
        # 문장 끝 공백 수정
        (r'한\s+다\.\s*<', '한다.<'),
        (r'있\s+다\.\s*<', '있다.<'),
        (r'없\s+다\.', '없다.'),
        (r'한\s+다\.', '한다.'),
        (r'있\s+다\.', '있다.'),
        (r'된\s+다\.', '된다.'),
        (r'할\s*수\s*있다', '할 수 있다'),
        (r'수\s*없다', '수 없다'),
        (r'([가-힣])으로\s+한다', r'\1으로 한다'),
        (r'([가-힣])\s+하며', r'\1하며'),
        (r'([가-힣])\s+되며', r'\1되며'),
        (r'^\s+', ''),
    ]
    for old, new in patterns:
        text = re.sub(old, new, text)
    text = re.sub(r'  +', ' ', text)
    return text


def remove_blank_between_items(text: str) -> str:
    """호번호 항목 사이 불필요한 빈 줄 제거"""
    # 패턴: 번호. 내용\n\n번호. 내용 → 번호. 내용\n번호. 내용
    pattern = r'(\d+\. .+)\n\n(\d+\. )'
    prev = ''
    while prev != text:
        prev = text
        text = re.sub(pattern, r'\1\n\2', text)
    return text


def clean_regulations(content: str, manual_revision: Optional[str] = None) -> str:
    """
    내규 문서 클리닝 메인 함수

    Args:
        content: 원본 마크다운 내용
        manual_revision: 수동 지정 개정일 (예: "2025.7.15(제83차 개정)")
    """
    lines = content.split('\n')

    # 0단계: 제목 추출
    title = None
    title_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('#'):
            title = re.sub(r'^#+\s*', '', line.strip())
            title_idx = i
            break

    # 1단계: 제/개정 이력 추출 및 테이블 제거
    last_date, last_revision, table_end = extract_revision_info(lines)

    # 수동 개정일이 지정된 경우 사용
    if manual_revision:
        revision_info = manual_revision
        last_date = True  # 플래그용
    elif last_date:
        if last_revision:
            revision_info = f'{last_date}({last_revision})'
        else:
            revision_info = last_date
    else:
        revision_info = None

    if table_end > 0:
        # 제목 + 최종 개정일 + 본문
        if revision_info:
            new_header = [f'# {title}', revision_info, '']
        else:
            new_header = [f'# {title}', '']

        # 테이블 이후 본문
        post_table = lines[table_end+1:]

        # 빈 줄 제거
        while post_table and not post_table[0].strip():
            post_table.pop(0)

        lines = new_header + post_table
    elif manual_revision and title:
        # 테이블은 없지만 수동 개정일 지정된 경우
        # 제목 바로 다음에 개정일 추가
        new_lines = []
        title_found = False
        for line in lines:
            new_lines.append(line)
            if not title_found and line.strip().startswith('#'):
                new_lines.append(manual_revision)
                title_found = True
        lines = new_lines

    # 2단계: 기본 정리
    processed = []
    skip_title = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            processed.append('')
            continue

        if skip_title and stripped.startswith('# '):
            processed.append(stripped)
            skip_title = False
            continue

        if re.match(r'^\d{4}\.\d{1,2}\.\d{1,2}\(', stripped):
            processed.append(stripped)
            continue

        # 테이블 행 스킵 (이미 처리됨)
        if '|' in stripped and ('---' in stripped or re.search(r'\d{4}\.', stripped)):
            continue

        if stripped.startswith('#'):
            if is_valid_header(stripped):
                header_text = re.sub(r'^#+\s*', '', stripped)
                processed.append(f'## {header_text}')
            else:
                clean_text = re.sub(r'^#+\s*', '', stripped)
                processed.append(clean_text)
            continue

        if stripped.startswith('-'):
            inner = stripped[1:].strip()
            if is_article_start(inner):
                processed.append(inner)
            elif is_subparagraph_marker(inner):
                processed.append(inner)
            elif is_paragraph_start(inner):
                processed.append(inner)
            elif is_number_item(inner):
                processed.append(inner)  # 호번호: 리스트 마커 없이 출력
            else:
                processed.append(inner)
            continue

        processed.append(stripped)

    # 3단계: 문장 연결
    result = []
    i = 0
    while i < len(processed):
        line = processed[i]

        if not line:
            if result and is_incomplete_ending(result[-1]):
                j = i + 1
                while j < len(processed) and not processed[j]:
                    j += 1
                if j < len(processed) and is_continuation_fragment(processed[j]):
                    i = j
                    continue
            result.append('')
            i += 1
            continue

        if is_structure_start(line):
            result.append(line)
            i += 1
            continue

        if result and result[-1] and not is_structure_start(line):
            prev = result[-1]
            if is_incomplete_ending(prev) or is_continuation_fragment(line):
                while result and not result[-1]:
                    result.pop()
                if result:
                    result[-1] = result[-1].rstrip() + ' ' + line.lstrip()
                    i += 1
                    continue

        result.append(line)
        i += 1

    # 4단계: 연속 빈 줄 정리
    cleaned = []
    prev_empty = False
    for line in result:
        if not line.strip():
            if not prev_empty:
                cleaned.append('')
                prev_empty = True
        else:
            cleaned.append(line)
            prev_empty = False

    # 5단계: 단어 공백 수정
    cleaned = [fix_word_spacing(line) for line in cleaned]

    # 6단계: 호번호 사이 빈 줄 제거
    result_text = '\n'.join(cleaned)
    result_text = remove_blank_between_items(result_text)

    return result_text


def process_file(input_path: Path, output_path: Path, manual_revision: Optional[str] = None, dry_run: bool = False) -> tuple:
    """
    단일 파일 처리

    Returns: (original_size, cleaned_size, success)
    """
    content = None
    encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']

    for encoding in encodings:
        try:
            with open(input_path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise ValueError(f"지원하지 않는 인코딩: {input_path}")

    original_size = len(content.encode('utf-8'))
    cleaned = clean_regulations(content, manual_revision)
    cleaned_size = len(cleaned.encode('utf-8'))

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)

    return original_size, cleaned_size, True


def get_output_path(input_path: Path, output_dir: Optional[Path] = None) -> Path:
    """출력 파일 경로 결정"""
    stem = input_path.stem
    if stem.endswith('_clean'):
        new_stem = stem  # 이미 _clean 접미사가 있음
    else:
        new_stem = f"{stem}_clean"

    if output_dir:
        return output_dir / f"{new_stem}.md"
    else:
        return input_path.parent / f"{new_stem}.md"


def main():
    parser = argparse.ArgumentParser(
        description='IBK 내규 문서 클리닝 스킬',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 단일 파일 처리
  python clean_regulation.py "인사규정.md"

  # 배치 처리 (디렉토리 내 모든 .md)
  python clean_regulation.py --batch "sources/internal_regulations/"

  # 출력 폴더 지정
  python clean_regulation.py --batch "sources/" --output "notes/"

  # 수동 개정일 지정
  python clean_regulation.py "업무분장규정.md" --revision "2025.7.15(제83차 개정)"

  # 미리보기 (파일 생성 안 함)
  python clean_regulation.py --batch "sources/" --dry-run
"""
    )

    parser.add_argument('input', nargs='?', help='입력 파일 경로')
    parser.add_argument('--batch', '-b', metavar='DIR', help='배치 처리할 디렉토리')
    parser.add_argument('--output', '-o', metavar='DIR', help='출력 디렉토리 (기본: 입력과 동일)')
    parser.add_argument('--revision', '-r', metavar='STR', help='수동 개정일 지정 (예: "2025.7.15(제83차 개정)")')
    parser.add_argument('--dry-run', '-n', action='store_true', help='미리보기 (파일 생성 안 함)')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 로그 출력')
    parser.add_argument('--version', '-V', action='version', version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    # 로깅 설정
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    # 입력 검증
    if not args.input and not args.batch:
        parser.error('입력 파일 또는 --batch 옵션이 필요합니다')

    # 수동 개정일 파일 로드
    manual_revisions = load_manual_revisions()

    # 출력 디렉토리
    output_dir = Path(args.output) if args.output else None

    files_to_process = []

    if args.batch:
        batch_dir = Path(args.batch)
        if not batch_dir.is_dir():
            logger.error(f"디렉토리가 존재하지 않습니다: {batch_dir}")
            return 1

        for md_file in batch_dir.glob("*.md"):
            if md_file.name.endswith('_clean.md'):
                continue
            files_to_process.append(md_file)
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"파일이 존재하지 않습니다: {input_path}")
            return 1
        files_to_process.append(input_path)

    if not files_to_process:
        logger.warning("처리할 파일이 없습니다")
        return 0

    # 처리
    print("=" * 60)
    print("IBK 내규 문서 클리닝")
    if args.dry_run:
        print("[DRY-RUN 모드]")
    print("=" * 60)

    total_original = 0
    total_cleaned = 0
    success_count = 0
    fail_count = 0

    for input_file in sorted(files_to_process):
        output_file = get_output_path(input_file, output_dir)

        # 수동 개정일 확인 (파일명 기준)
        file_key = input_file.stem
        manual_rev = args.revision or manual_revisions.get(file_key)

        try:
            orig_size, clean_size, success = process_file(
                input_file, output_file, manual_rev, args.dry_run
            )

            diff = orig_size - clean_size
            pct = (diff / orig_size * 100) if orig_size > 0 else 0

            status = "[DRY]" if args.dry_run else "[OK]"
            print(f"{status} {input_file.name}")
            print(f"     {orig_size:,} → {clean_size:,} bytes ({diff:+,}, {pct:.1f}%)")
            if manual_rev:
                print(f"     개정일: {manual_rev}")
            if args.verbose:
                print(f"     출력: {output_file}")

            total_original += orig_size
            total_cleaned += clean_size
            success_count += 1

        except Exception as e:
            print(f"[ERROR] {input_file.name}: {e}")
            logger.debug(f"상세 오류:", exc_info=True)
            fail_count += 1

    # 요약
    print("=" * 60)
    if total_original > 0:
        total_diff = total_original - total_cleaned
        total_pct = (total_diff / total_original * 100)
        print(f"총 원본: {total_original:,} bytes")
        print(f"총 정리: {total_cleaned:,} bytes")
        print(f"총 감소: {total_diff:,} bytes ({total_pct:.1f}%)")
    print(f"성공: {success_count}개, 실패: {fail_count}개")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    exit(main())
