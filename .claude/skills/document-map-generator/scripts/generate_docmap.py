#!/usr/bin/env python3
"""
document-map 자동 생성 스크립트
ZK-PARA Vault의 문서 인덱스를 자동으로 생성합니다.

사용법:
    python generate_docmap.py [vault_path]

기본값: 현재 디렉토리의 상위 4단계 (스크립트 위치 기준)
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def get_vault_path(script_path: Path) -> Path:
    """스크립트 위치에서 vault 경로 추출"""
    # .claude/skills/document-map-generator/scripts/generate_docmap.py
    return script_path.parent.parent.parent.parent.parent


def scan_markdown_files(folder_path: Path) -> list[dict]:
    """폴더 내 마크다운 파일 스캔"""
    files = []
    if not folder_path.exists():
        return files

    for md_file in folder_path.rglob("*.md"):
        # CLAUDE.md, tasks.md, prompts.md 등 시스템 파일 제외
        if md_file.name in ["CLAUDE.md", "tasks.md", "prompts.md", "task.md"]:
            continue

        rel_path = md_file.relative_to(folder_path)
        files.append({
            "name": md_file.stem,
            "path": str(rel_path),
            "full_path": md_file,
            "parent": str(rel_path.parent) if str(rel_path.parent) != "." else "",
        })

    return sorted(files, key=lambda x: x["path"])


def extract_description_from_claude_md(claude_md_path: Path) -> str:
    """CLAUDE.md에서 설명 추출"""
    if not claude_md_path.exists():
        return ""

    try:
        content = claude_md_path.read_text(encoding="utf-8")

        # ## 목표 또는 ## 주제 설명 섹션에서 설명 추출
        patterns = [
            r"## 목표\s*\n([^\n#]+)",
            r"## 주제 설명\s*\n([^\n#]+)",
            r"## 영역 정의\s*\n([^\n#]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()

        return ""
    except Exception:
        return ""


def get_project_info(project_path: Path) -> dict:
    """프로젝트 정보 추출"""
    claude_md = project_path / "CLAUDE.md"
    description = extract_description_from_claude_md(claude_md)

    # 폴더명에서 날짜 추출
    folder_name = project_path.name
    date_match = re.match(r"P-(\d{8})_", folder_name)
    date_str = date_match.group(1) if date_match else ""

    return {
        "name": folder_name,
        "description": description,
        "date": date_str,
    }


def get_area_info(area_path: Path) -> dict:
    """영역 정보 추출"""
    claude_md = area_path / "CLAUDE.md"
    description = extract_description_from_claude_md(claude_md)

    return {
        "name": area_path.name,
        "description": description,
    }


def get_resource_info(resource_path: Path) -> dict:
    """리소스 정보 추출"""
    claude_md = resource_path / "CLAUDE.md"
    description = extract_description_from_claude_md(claude_md)

    return {
        "name": resource_path.name,
        "description": description,
    }


def generate_progress_bar(percentage: int, total_width: int = 20) -> str:
    """ASCII 프로그레스 바 생성"""
    filled = int(percentage / 100 * total_width)
    bar = "█" * filled + "░" * (total_width - filled)
    return bar


def generate_document_map(vault_path: Path) -> str:
    """document-map.md 내용 생성"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 대상 폴더 정의
    target_folders = {
        "1_Projects": vault_path / "1_Projects",
        "2_Areas": vault_path / "2_Areas",
        "3_Resources": vault_path / "3_Resources",
        "4_Archive": vault_path / "4_Archive",
        "5_Zettelkasten": vault_path / "5_Zettelkasten",
    }

    # 각 폴더별 문서 수집
    folder_stats = {}
    folder_files = {}
    total_docs = 0

    for folder_name, folder_path in target_folders.items():
        files = scan_markdown_files(folder_path)
        folder_files[folder_name] = files
        folder_stats[folder_name] = len(files)
        total_docs += len(files)

    # 프로젝트 정보 수집
    projects = []
    projects_path = target_folders["1_Projects"]
    if projects_path.exists():
        for item in sorted(projects_path.iterdir()):
            if item.is_dir() and item.name.startswith("P-"):
                projects.append(get_project_info(item))

    # 영역 정보 수집
    areas = []
    areas_path = target_folders["2_Areas"]
    if areas_path.exists():
        for item in sorted(areas_path.iterdir()):
            if item.is_dir() and item.name.startswith("A-"):
                areas.append(get_area_info(item))

    # 리소스 정보 수집
    resources = []
    resources_path = target_folders["3_Resources"]
    if resources_path.exists():
        for item in sorted(resources_path.iterdir()):
            if item.is_dir() and item.name.startswith("R-"):
                resources.append(get_resource_info(item))

    # 마크다운 생성
    lines = []
    lines.append("# Document Map")
    lines.append("")
    lines.append(f"ZK-PARA Vault 전체 문서 인덱스 (최종 업데이트: {today})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 개요 섹션
    lines.append("## 개요")
    lines.append("")
    lines.append("| 항목 | 수치 |")
    lines.append("|------|------|")
    lines.append(f"| 총 문서 수 | {total_docs}개 |")
    lines.append(f"| 프로젝트 | {len(projects)}개 |")
    lines.append(f"| 영역 | {len(areas)}개 |")
    lines.append(f"| 리소스 | {len(resources)}개 |")
    lines.append("")

    # 폴더별 분포
    lines.append("### 폴더별 분포")
    lines.append("")
    lines.append("```")

    max_name_len = max(len(name) for name in folder_stats.keys())
    for folder_name, count in folder_stats.items():
        percentage = (count / total_docs * 100) if total_docs > 0 else 0
        bar = generate_progress_bar(int(percentage), 20)
        lines.append(f"{folder_name:<{max_name_len}} {bar} {count}개 ({percentage:.0f}%)")

    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1_Projects 섹션
    lines.append("## 1_Projects (진행 중 프로젝트)")
    lines.append("")

    for project in projects:
        lines.append(f"### {project['name']}")
        if project['description']:
            lines.append(f"> {project['description']}")
        lines.append("")

        # 해당 프로젝트의 파일 목록
        project_path = projects_path / project['name']
        project_files = scan_markdown_files(project_path)

        if project_files:
            # 서브폴더별로 그룹화
            by_subfolder = defaultdict(list)
            for f in project_files:
                subfolder = f["parent"].split("/")[0] if f["parent"] else "root"
                by_subfolder[subfolder].append(f)

            for subfolder, files in sorted(by_subfolder.items()):
                if subfolder != "root" and len(by_subfolder) > 1:
                    lines.append(f"**{subfolder}/**")

                lines.append("| 문서 | 경로 |")
                lines.append("|------|------|")
                for f in files[:10]:  # 최대 10개까지만 표시
                    lines.append(f"| {f['name']} | {f['path']} |")

                if len(files) > 10:
                    lines.append(f"| ... | 외 {len(files) - 10}개 |")
                lines.append("")
        else:
            lines.append("*문서 없음*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 2_Areas 섹션
    lines.append("## 2_Areas (지속 관리 영역)")
    lines.append("")

    for area in areas:
        lines.append(f"### {area['name']}")
        if area['description']:
            lines.append(f"> {area['description']}")
        lines.append("")

        area_path = areas_path / area['name']
        area_files = scan_markdown_files(area_path)

        if area_files:
            lines.append("| 문서 | 경로 |")
            lines.append("|------|------|")
            for f in area_files[:10]:
                lines.append(f"| {f['name']} | {f['path']} |")
            if len(area_files) > 10:
                lines.append(f"| ... | 외 {len(area_files) - 10}개 |")
            lines.append("")
        else:
            lines.append("*문서 없음*")
            lines.append("")

    lines.append("---")
    lines.append("")

    # 3_Resources 섹션
    lines.append("## 3_Resources (참고 지식)")
    lines.append("")

    for resource in resources:
        lines.append(f"### {resource['name']}")
        if resource['description']:
            lines.append(f"> {resource['description']}")
        lines.append("")

        resource_path = resources_path / resource['name']
        resource_files = scan_markdown_files(resource_path)

        if resource_files:
            # 서브폴더별로 그룹화
            by_subfolder = defaultdict(list)
            for f in resource_files:
                subfolder = f["parent"].split("/")[0] if f["parent"] else "root"
                by_subfolder[subfolder].append(f)

            for subfolder, files in sorted(by_subfolder.items()):
                if subfolder != "root" and len(by_subfolder) > 1:
                    lines.append(f"**{subfolder}/**")

                lines.append("| 문서 | 경로 |")
                lines.append("|------|------|")
                for f in files[:10]:
                    lines.append(f"| {f['name']} | {f['path']} |")
                if len(files) > 10:
                    lines.append(f"| ... | 외 {len(files) - 10}개 |")
                lines.append("")
        else:
            lines.append("*문서 없음*")
            lines.append("")

    lines.append("---")
    lines.append("")

    # 4_Archive 섹션
    lines.append("## 4_Archive (보관)")
    lines.append("")

    archive_path = target_folders["4_Archive"]
    if archive_path.exists():
        # 연도별 폴더 스캔
        year_folders = sorted([d for d in archive_path.iterdir() if d.is_dir()], reverse=True)

        for year_folder in year_folders:
            year_files = scan_markdown_files(year_folder)
            if year_files:
                lines.append(f"### {year_folder.name}")
                lines.append("")
                lines.append("| 문서 | 경로 |")
                lines.append("|------|------|")
                for f in year_files[:10]:
                    lines.append(f"| {f['name']} | {f['path']} |")
                if len(year_files) > 10:
                    lines.append(f"| ... | 외 {len(year_files) - 10}개 |")
                lines.append("")

    lines.append("---")
    lines.append("")

    # 5_Zettelkasten 섹션
    lines.append("## 5_Zettelkasten (지식 엔진)")
    lines.append("")

    zk_path = target_folders["5_Zettelkasten"]
    zk_subfolders = ["1_Fleeting", "2_Literature", "3_Permanent"]

    for subfolder in zk_subfolders:
        subfolder_path = zk_path / subfolder
        if subfolder_path.exists():
            zk_files = scan_markdown_files(subfolder_path)

            lines.append(f"### {subfolder}")
            lines.append("")

            if zk_files:
                # 카테고리별 그룹화
                by_category = defaultdict(list)
                for f in zk_files:
                    category = f["parent"].split("/")[0] if f["parent"] else "기타"
                    by_category[category].append(f)

                for category, files in sorted(by_category.items()):
                    if len(by_category) > 1 and category != "기타":
                        lines.append(f"**{category}/** ({len(files)}개)")
                        lines.append("")

                    lines.append("| 문서 | 경로 |")
                    lines.append("|------|------|")
                    for f in files[:15]:
                        lines.append(f"| {f['name']} | {f['path']} |")
                    if len(files) > 15:
                        lines.append(f"| ... | 외 {len(files) - 15}개 |")
                    lines.append("")
            else:
                lines.append("*문서 없음*")
                lines.append("")

    lines.append("---")
    lines.append("")

    # 통계 요약
    lines.append("## 통계 요약")
    lines.append("")
    lines.append("| 카테고리 | 문서 수 | 비고 |")
    lines.append("|----------|---------|------|")
    lines.append(f"| 프로젝트 문서 | {folder_stats['1_Projects']}개 | {len(projects)}개 프로젝트 |")
    lines.append(f"| 영역 문서 | {folder_stats['2_Areas']}개 | {len(areas)}개 영역 |")
    lines.append(f"| 리소스 문서 | {folder_stats['3_Resources']}개 | {len(resources)}개 리소스 |")
    lines.append(f"| 아카이브 | {folder_stats['4_Archive']}개 | 완료/비활성 |")
    lines.append(f"| Zettelkasten | {folder_stats['5_Zettelkasten']}개 | 지식 노트 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*이 문서는 `/update_git` 명령 실행 시 자동으로 업데이트됩니다.*")
    lines.append("")

    return "\n".join(lines)


def main():
    # 경로 결정
    if len(sys.argv) > 1:
        vault_path = Path(sys.argv[1])
    else:
        script_path = Path(__file__).resolve()
        vault_path = get_vault_path(script_path)

    if not vault_path.exists():
        print(f"Error: Vault path not found: {vault_path}", file=sys.stderr)
        sys.exit(1)

    # document-map 생성
    content = generate_document_map(vault_path)

    # 파일 저장
    output_path = vault_path / "_Docs" / "document-map.md"
    output_path.write_text(content, encoding="utf-8")

    print(f"Document map generated: {output_path}")


if __name__ == "__main__":
    main()
