#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLAUDE.md 파일 점검 스크립트
ZK-PARA Vault 내 모든 CLAUDE.md 파일의 품질을 점검하고 리포트 생성
"""

import os
import re
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import unicodedata

# UTF-8 환경 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Vault 루트 경로
VAULT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# 리포트 출력 경로
REPORT_PATH = VAULT_ROOT / "_Docs" / "claude-files-report.md"

# 필수 섹션 패턴
REQUIRED_PATTERNS = {
    "날짜 메타": r'\*최종 업데이트:',
    "목적 섹션": r'## (목적과 역할|개요|주제 설명|저장소 개요|프로젝트 개요|영역 정의)',
    "공통 지침": r'공통 지침'
}

# 날짜 경고 임계값 (일)
DATE_WARNING_THRESHOLD = 7


def normalize_path(path: str) -> str:
    """경로 NFC 정규화 (한글 호환)"""
    return unicodedata.normalize('NFC', str(path))


def find_claude_files(root: Path) -> List[Path]:
    """Vault 내 모든 CLAUDE.md 파일 찾기"""
    claude_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # 제외 폴더
        dirnames[:] = [d for d in dirnames if d not in ['.git', '.obsidian', 'node_modules', '.claude']]

        for filename in filenames:
            if filename == 'CLAUDE.md':
                full_path = Path(dirpath) / filename
                claude_files.append(full_path)

    # Root CLAUDE.md 추가 (별도 처리)
    root_claude = root / 'CLAUDE.md'
    if root_claude.exists() and root_claude not in claude_files:
        claude_files.insert(0, root_claude)

    return claude_files


def read_file_safe(filepath: Path) -> Optional[str]:
    """여러 인코딩으로 파일 읽기 시도"""
    encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']

    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
                # BOM 제거
                if content.startswith('\ufeff'):
                    content = content[1:]
                return content
        except (UnicodeDecodeError, UnicodeError):
            continue

    return None


def extract_links(content: str) -> List[Tuple[str, str]]:
    """내부 링크 추출: (경로, 표시텍스트)
    코드 블록(```) 내의 링크는 제외
    """
    # 코드 블록 제거 (```...``` 사이의 내용)
    content_no_code = re.sub(r'```[\s\S]*?```', '', content)

    # 인라인 코드 제거 (`...` 사이의 내용)
    content_no_code = re.sub(r'`[^`]+`', '', content_no_code)

    # [[path|text]] 또는 [[path]] 형식
    pattern = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
    matches = re.findall(pattern, content_no_code)
    return [(m[0], m[1] if m[1] else m[0]) for m in matches]


def check_link_validity(link_path: str, base_dir: Path) -> Tuple[bool, str]:
    """링크 유효성 검사"""
    # 경로 정규화
    link_path = normalize_path(link_path)

    # 앵커(#) 제거
    if '#' in link_path:
        link_path = link_path.split('#')[0]

    if not link_path:
        return True, "앵커 전용 링크"

    # 절대 경로로 변환
    if link_path.startswith('/'):
        target = VAULT_ROOT / link_path[1:]
    else:
        target = VAULT_ROOT / link_path

    # .md 확장자 처리
    if target.exists():
        return True, ""

    target_md = Path(str(target) + '.md')
    if target_md.exists():
        return True, ""

    # 폴더로 존재하는지 확인
    if target.is_dir():
        return True, ""

    return False, f"파일 없음: {link_path}"


def extract_date(content: str) -> Optional[datetime]:
    """최종 업데이트 날짜 추출"""
    pattern = r'\*최종 업데이트:\s*(\d{4}-\d{2}-\d{2})\*'
    match = re.search(pattern, content)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y-%m-%d')
        except ValueError:
            pass
    return None


def extract_stats_from_root(content: str) -> Dict[str, int]:
    """Root CLAUDE.md에서 통계 정보 추출"""
    stats = {}

    # 스킬 개수
    skill_match = re.search(r'커스텀 스킬\s*\|\s*(\d+)개', content)
    if skill_match:
        stats['skills'] = int(skill_match.group(1))

    # 에이전트 개수
    agent_match = re.search(r'커스텀 에이전트\s*\|\s*(\d+)개', content)
    if agent_match:
        stats['agents'] = int(agent_match.group(1))

    # 프로젝트 개수
    proj_match = re.search(r'활성 프로젝트\s*\|\s*(\d+)개', content)
    if proj_match:
        stats['projects'] = int(proj_match.group(1))

    # 영역 개수
    area_match = re.search(r'활성 영역\s*\|\s*(\d+)개', content)
    if area_match:
        stats['areas'] = int(area_match.group(1))

    # 리소스 개수
    res_match = re.search(r'리소스\s*\|\s*(\d+)개', content)
    if res_match:
        stats['resources'] = int(res_match.group(1))

    return stats


def extract_category_skill_counts(content: str) -> List[Dict]:
    """분류별 스킬 개수 검증: 헤더 기재 vs 실제 테이블 행 수 비교"""
    results = []

    # ## 커스텀 스킬 섹션만 추출 (에이전트 섹션 제외)
    skill_section_match = re.search(
        r'## 커스텀 스킬.*?\n(.*?)(?=\n## |$)',
        content,
        re.DOTALL
    )

    if not skill_section_match:
        return results

    skill_section = skill_section_match.group(1)

    # 문서를 분류 섹션별로 분리 (### 또는 ## 헤더 기준)
    sections = re.split(r'(###\s+[^\n]+\n)', skill_section)

    current_category = None
    documented_count = None

    for i, section in enumerate(sections):
        # 분류 헤더 발견
        header_match = re.match(r'###\s+([^\n(]+)\s*\((\d+)개\)', section.strip())
        if header_match:
            current_category = header_match.group(1).strip()
            documented_count = int(header_match.group(2))
            continue

        # 현재 분류 섹션의 테이블 행 수 계산
        if current_category and documented_count is not None:
            # 마크다운 테이블에서 데이터 행 수 계산 (헤더, 구분선 제외)
            # | 스킬 | 용도 | 형식의 테이블에서 실제 데이터 행만 카운트
            table_rows = re.findall(r'^\|\s*`[^`]+`\s*\|', section, re.MULTILINE)
            actual_count = len(table_rows)

            if actual_count > 0:  # 테이블이 있는 경우만
                results.append({
                    'category': current_category,
                    'documented': documented_count,
                    'actual': actual_count,
                    'match': documented_count == actual_count
                })

            current_category = None
            documented_count = None

    return results


def count_actual_items(vault_root: Path) -> Dict[str, int]:
    """실제 폴더/파일 수 계산"""
    counts = {}

    # 스킬 수
    skills_dir = vault_root / '.claude' / 'skills'
    if skills_dir.exists():
        counts['skills'] = len([d for d in skills_dir.iterdir() if d.is_dir()])
    else:
        counts['skills'] = 0

    # 에이전트 수 (폴더 또는 .md 파일, _legacy 제외)
    agents_dir = vault_root / '.claude' / 'agents'
    if agents_dir.exists():
        # 폴더 또는 .md 파일 모두 카운트 (_legacy 접미사 제외)
        agent_folders = [d for d in agents_dir.iterdir()
                        if d.is_dir() and '_legacy' not in d.name]
        agent_files = [f for f in agents_dir.iterdir()
                      if f.is_file() and f.suffix == '.md' and '_legacy' not in f.stem]
        counts['agents'] = len(agent_folders) if agent_folders else len(agent_files)
    else:
        counts['agents'] = 0

    # 활성 프로젝트 수 (Archive 제외)
    projects_dir = vault_root / '1_Projects'
    if projects_dir.exists():
        counts['projects'] = len([d for d in projects_dir.iterdir()
                                  if d.is_dir() and d.name.startswith('P-')])
    else:
        counts['projects'] = 0

    # 활성 영역 수
    areas_dir = vault_root / '2_Areas'
    if areas_dir.exists():
        counts['areas'] = len([d for d in areas_dir.iterdir()
                               if d.is_dir() and d.name.startswith('A-')])
    else:
        counts['areas'] = 0

    # 리소스 수
    resources_dir = vault_root / '3_Resources'
    if resources_dir.exists():
        counts['resources'] = len([d for d in resources_dir.iterdir()
                                   if d.is_dir() and d.name.startswith('R-')])
    else:
        counts['resources'] = 0

    return counts


def fix_root_stats(filepath: Path, stats_comparison: List[Dict]) -> bool:
    """Root CLAUDE.md의 통계 불일치 자동 수정

    Args:
        filepath: Root CLAUDE.md 파일 경로
        stats_comparison: 통계 비교 결과 리스트

    Returns:
        수정 여부 (True: 수정함, False: 수정 없음)
    """
    content = read_file_safe(filepath)
    if content is None:
        print(f"[ERR] 파일 읽기 실패: {filepath}")
        return False

    modified = False
    new_content = content

    # 항목별 패턴과 대체 형식
    patterns = {
        'skills': (r'커스텀 스킬\s*\|\s*\d+개', '커스텀 스킬 | {actual}개'),
        'agents': (r'커스텀 에이전트\s*\|\s*\d+개', '커스텀 에이전트 | {actual}개'),
        'projects': (r'활성 프로젝트\s*\|\s*\d+개', '활성 프로젝트 | {actual}개'),
        'areas': (r'활성 영역\s*\|\s*\d+개', '활성 영역 | {actual}개'),
        'resources': (r'리소스\s*\|\s*\d+개', '리소스 | {actual}개'),
    }

    for stat in stats_comparison:
        if not stat['match']:
            item = stat['item']
            actual = stat['actual']

            if item in patterns:
                pattern, replacement = patterns[item]
                replacement_str = replacement.format(actual=actual)
                new_content, count = re.subn(pattern, replacement_str, new_content, count=1)

                if count > 0:
                    print(f"  [FIX] {item}: {stat['documented']} → {actual}")
                    modified = True

    if modified:
        # 최종 업데이트 날짜도 갱신
        today = datetime.now().strftime('%Y-%m-%d')
        new_content = re.sub(
            r'\*최종 업데이트:\s*\d{4}-\d{2}-\d{2}\*',
            f'*최종 업데이트: {today}*',
            new_content
        )

        # 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"  [INFO] Root CLAUDE.md 저장 완료")

    return modified


def check_file(filepath: Path, is_root: bool = False, verbose: bool = False) -> Dict:
    """단일 CLAUDE.md 파일 점검"""
    result = {
        'path': filepath,
        'relative_path': filepath.relative_to(VAULT_ROOT),
        'status': 'ok',
        'issues': [],
        'warnings': []
    }

    content = read_file_safe(filepath)
    if content is None:
        result['status'] = 'error'
        result['issues'].append('파일 읽기 실패 (인코딩 문제)')
        return result

    # 1. 필수 섹션 점검
    for name, pattern in REQUIRED_PATTERNS.items():
        if not re.search(pattern, content):
            result['issues'].append(f'필수 섹션 누락: {name}')

    # 2. 날짜 점검 (4_Archive 폴더는 완료된 프로젝트이므로 날짜 경과 경고 제외)
    is_archive = '4_Archive' in str(filepath)
    file_date = extract_date(content)
    if file_date:
        days_old = (datetime.now() - file_date).days
        if days_old > DATE_WARNING_THRESHOLD and not is_archive:
            result['warnings'].append(f'날짜 {days_old}일 경과')
    else:
        if not is_archive:
            result['warnings'].append('날짜 형식 없음')

    # 3. 링크 유효성 점검
    links = extract_links(content)
    for link_path, display_text in links:
        is_valid, error_msg = check_link_validity(link_path, filepath.parent)
        if not is_valid:
            result['issues'].append(f'링크 오류: [[{link_path}]] - {error_msg}')

    # 4. Root 전용: 통계 검증
    if is_root:
        doc_stats = extract_stats_from_root(content)
        actual_stats = count_actual_items(VAULT_ROOT)

        result['stats_comparison'] = []
        for key in ['skills', 'agents', 'projects', 'areas', 'resources']:
            doc_val = doc_stats.get(key, '?')
            actual_val = actual_stats.get(key, '?')
            match = doc_val == actual_val
            result['stats_comparison'].append({
                'item': key,
                'documented': doc_val,
                'actual': actual_val,
                'match': match
            })
            if not match:
                result['warnings'].append(f'통계 불일치: {key} (문서: {doc_val}, 실제: {actual_val})')

        # 5. Root 전용: 분류별 스킬 개수 검증
        category_counts = extract_category_skill_counts(content)
        result['category_skill_counts'] = category_counts
        for cat in category_counts:
            if not cat['match']:
                result['warnings'].append(
                    f"분류별 스킬 불일치: {cat['category']} (문서: {cat['documented']}개, 실제: {cat['actual']}개)"
                )

    # 최종 상태 결정
    if result['issues']:
        result['status'] = 'critical'
    elif result['warnings']:
        result['status'] = 'warning'

    return result


def generate_report(results: List[Dict], output_path: Path) -> str:
    """마크다운 리포트 생성"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    total = len(results)
    critical = sum(1 for r in results if r['status'] == 'critical')
    warning = sum(1 for r in results if r['status'] == 'warning')
    ok = sum(1 for r in results if r['status'] == 'ok')

    lines = [
        "# CLAUDE.md 점검 리포트",
        "",
        f"*생성일: {now}*",
        "",
        "## 요약",
        "",
        f"- 점검 파일: {total}개",
        f"- 정상: {ok}개",
        f"- Critical: {critical}개",
        f"- Warning: {warning}개",
        ""
    ]

    # Critical 이슈
    lines.extend([
        "## 이슈 목록",
        "",
        "### Critical",
        ""
    ])

    critical_issues = [r for r in results if r['status'] == 'critical']
    if critical_issues:
        lines.extend([
            "| 파일 | 문제 | 권장 조치 |",
            "|------|------|----------|"
        ])
        for r in critical_issues:
            for issue in r['issues']:
                lines.append(f"| `{r['relative_path']}` | {issue} | 즉시 수정 필요 |")
        lines.append("")
    else:
        lines.extend(["(없음)", ""])

    # Warning
    lines.extend([
        "### Warning",
        ""
    ])

    warning_items = [r for r in results if r['status'] == 'warning']
    if warning_items:
        lines.extend([
            "| 파일 | 문제 | 권장 조치 |",
            "|------|------|----------|"
        ])
        for r in warning_items:
            for warn in r['warnings']:
                lines.append(f"| `{r['relative_path']}` | {warn} | 업데이트 권장 |")
        lines.append("")
    else:
        lines.extend(["(없음)", ""])

    # 통계 검증 (Root 파일 결과에서)
    root_result = next((r for r in results if str(r['relative_path']) == 'CLAUDE.md'), None)
    if root_result and 'stats_comparison' in root_result:
        lines.extend([
            "## 통계 검증",
            "",
            "| 항목 | 문서 기재 | 실제 | 상태 |",
            "|------|----------|------|------|"
        ])

        item_names = {
            'skills': '스킬',
            'agents': '에이전트',
            'projects': '프로젝트',
            'areas': '영역',
            'resources': '리소스'
        }

        for stat in root_result['stats_comparison']:
            status = "OK" if stat['match'] else "MISMATCH"
            name = item_names.get(stat['item'], stat['item'])
            lines.append(f"| {name} | {stat['documented']}개 | {stat['actual']}개 | {status} |")
        lines.append("")

    # 분류별 스킬 검증 (Root 파일 결과에서)
    if root_result and 'category_skill_counts' in root_result:
        category_counts = root_result['category_skill_counts']
        if category_counts:
            lines.extend([
                "## 분류별 스킬 검증",
                "",
                "| 분류 | 문서 기재 | 실제 | 상태 |",
                "|------|----------|------|------|"
            ])

            for cat in category_counts:
                status = "OK" if cat['match'] else "MISMATCH"
                lines.append(f"| {cat['category']} | {cat['documented']}개 | {cat['actual']}개 | {status} |")
            lines.append("")

    # 전체 파일 목록
    lines.extend([
        "## 전체 파일 목록",
        "",
        "| # | 파일 | 상태 |",
        "|---|------|------|"
    ])

    for i, r in enumerate(results, 1):
        status_icon = {"ok": "OK", "warning": "WARN", "critical": "ERR", "error": "ERR"}.get(r['status'], '?')
        lines.append(f"| {i} | `{r['relative_path']}` | {status_icon} |")

    lines.append("")

    report_content = '\n'.join(lines)

    # 파일 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return report_content


def main():
    parser = argparse.ArgumentParser(description='CLAUDE.md 파일 점검')
    parser.add_argument('--file', type=str, help='특정 파일만 점검')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 출력')
    parser.add_argument('--no-report', action='store_true', help='리포트 파일 생성 안함')
    parser.add_argument('--fix', action='store_true', help='Root CLAUDE.md 통계 불일치 자동 수정')
    args = parser.parse_args()

    print("=== CLAUDE.md 점검 시작 ===")

    if args.file:
        # 특정 파일만 점검
        filepath = VAULT_ROOT / args.file
        if not filepath.exists():
            print(f"[ERR] 파일 없음: {args.file}")
            sys.exit(1)
        files = [filepath]
    else:
        # 전체 파일 점검
        files = find_claude_files(VAULT_ROOT)

    print(f"[INFO] 발견된 파일: {len(files)}개")

    results = []
    for filepath in files:
        is_root = (filepath == VAULT_ROOT / 'CLAUDE.md')
        result = check_file(filepath, is_root=is_root, verbose=args.verbose)
        results.append(result)

        # 콘솔 출력
        rel_path = result['relative_path']
        if result['status'] == 'ok':
            print(f"[OK] {rel_path}")
        elif result['status'] == 'warning':
            warns = '; '.join(result['warnings'][:2])
            print(f"[WARN] {rel_path} - {warns}")
        else:
            issues = '; '.join(result['issues'][:2])
            print(f"[ERR] {rel_path} - {issues}")

    # 요약
    total = len(results)
    critical = sum(1 for r in results if r['status'] == 'critical')
    warning = sum(1 for r in results if r['status'] == 'warning')
    ok = sum(1 for r in results if r['status'] == 'ok')

    print(f"\n=== 점검 완료: {ok} 정상, {warning} 경고, {critical} 오류 ===")

    # 리포트 생성
    if not args.no_report:
        generate_report(results, REPORT_PATH)
        print(f"[INFO] 리포트 생성: {REPORT_PATH.relative_to(VAULT_ROOT)}")

    # --fix 옵션: Root CLAUDE.md 통계 자동 수정
    if args.fix:
        root_result = next((r for r in results if str(r['relative_path']) == 'CLAUDE.md'), None)
        if root_result and 'stats_comparison' in root_result:
            # 불일치 항목이 있는지 확인
            mismatches = [s for s in root_result['stats_comparison'] if not s['match']]
            if mismatches:
                print("\n=== 통계 불일치 자동 수정 ===")
                root_path = VAULT_ROOT / 'CLAUDE.md'
                fixed = fix_root_stats(root_path, root_result['stats_comparison'])
                if fixed:
                    print("[INFO] Root CLAUDE.md 통계가 수정되었습니다.")
                else:
                    print("[INFO] 수정할 항목이 없습니다.")
            else:
                print("\n[INFO] 통계 불일치 없음 - 수정 불필요")

    # 종료 코드
    sys.exit(1 if critical > 0 else 0)


if __name__ == '__main__':
    main()
