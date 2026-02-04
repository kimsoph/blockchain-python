#!/usr/bin/env python3
"""
CHANGELOG 자동 갱신 스크립트

Git 커밋 메시지를 파싱하여 _Docs/CHANGELOG.md를 자동 업데이트합니다.
"""

import subprocess
import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional


def get_vault_path() -> Path:
    """스크립트 위치에서 vault 경로 계산"""
    script_path = Path(__file__).resolve()
    # .claude/skills/changelog-generator/scripts/generate_changelog.py
    return script_path.parent.parent.parent.parent.parent


def load_tracking(tracking_path: Path) -> dict:
    """추적 파일 로드"""
    if not tracking_path.exists():
        return {
            "last_processed_commit": None,
            "last_update_date": None
        }

    with open(tracking_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_tracking(tracking_path: Path, data: dict):
    """추적 파일 저장"""
    with open(tracking_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def get_current_head() -> str:
    """현재 HEAD 커밋 해시 조회"""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


def commit_exists(commit_hash: str) -> bool:
    """커밋 존재 여부 확인

    리베이스나 삭제로 인해 커밋이 사라졌을 수 있으므로 사전 확인.

    Args:
        commit_hash: 확인할 커밋 해시 (short 또는 full)

    Returns:
        커밋 존재 여부
    """
    result = subprocess.run(
        ["git", "cat-file", "-t", commit_hash],
        capture_output=True, text=True, encoding="utf-8"
    )
    return result.returncode == 0


def get_commits_since(last_commit: Optional[str], fallback_count: int = 10) -> list:
    """마지막 처리 커밋 이후의 커밋 목록 조회

    Args:
        last_commit: 마지막 처리 커밋 해시
        fallback_count: 커밋이 존재하지 않을 때 조회할 최근 커밋 수

    Returns:
        커밋 정보 리스트
    """
    if last_commit:
        # 커밋 존재 여부 확인 (리베이스/삭제 대비)
        if not commit_exists(last_commit):
            print(f"[WARN] 커밋 {last_commit}이 존재하지 않음. 최근 {fallback_count}개 커밋 조회로 전환.")
            last_commit = None
            cmd = ["git", "log", f"-{fallback_count}", "--format=%H|%h|%ai|%s|%b|||COMMIT_END|||"]
        else:
            # 마지막 커밋 이후부터 현재까지
            cmd = ["git", "log", f"{last_commit}..HEAD", "--format=%H|%h|%ai|%s|%b|||COMMIT_END|||"]
    else:
        # 처음 실행 시 - HEAD만 가져옴 (초기화용)
        cmd = ["git", "log", "-1", "--format=%H|%h|%ai|%s|%b|||COMMIT_END|||"]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if not result.stdout.strip():
        return []

    commits = []
    raw_commits = result.stdout.split("|||COMMIT_END|||")

    for raw in raw_commits:
        raw = raw.strip()
        if not raw:
            continue

        parts = raw.split("|", 4)
        if len(parts) < 5:
            continue

        full_hash, short_hash, date_str, subject, body = parts

        # 날짜 파싱 (2026-01-13 09:37:42 +0900 형식)
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
        date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

        commits.append({
            "hash": short_hash.strip(),
            "full_hash": full_hash.strip(),
            "date": date,
            "subject": subject.strip(),
            "body": body.strip()
        })

    return commits


def parse_commit_type(subject: str) -> tuple:
    """커밋 subject에서 타입과 메시지 추출"""
    # "type: message" 또는 "type(scope): message" 패턴
    match = re.match(r"^(\w+)(?:\([^)]+\))?:\s*(.+)$", subject)
    if match:
        return match.group(1).lower(), match.group(2)
    return "other", subject


def should_include_commit(commit_type: str) -> bool:
    """커밋 타입이 CHANGELOG에 포함되어야 하는지 확인"""
    # chore는 제외 (자동 생성 파일 동기화)
    included_types = {"feat", "refactor", "docs", "fix", "perf", "style", "test", "build"}
    return commit_type in included_types


def extract_body_details(body: str) -> list:
    """커밋 body에서 세부사항 추출"""
    if not body:
        return []

    details = []
    lines = body.split("\n")

    for line in lines:
        line = line.strip()
        # Co-Authored-By 제외
        if line.startswith("Co-Authored-By"):
            continue
        # 빈 줄 제외
        if not line:
            continue
        # 마크다운 리스트 항목이면 추가
        if line.startswith("- ") or line.startswith("* "):
            details.append(line[2:].strip())
        # 섹션 헤더 (삭제:, 수정: 등)
        elif line.endswith(":"):
            continue
        # 일반 문장 (첫 줄만)
        elif len(details) == 0 and len(line) > 10:
            details.append(line)

    return details[:3]  # 최대 3개까지


def transform_commit_to_entry(commit: dict) -> Optional[str]:
    """커밋을 CHANGELOG 엔트리로 변환"""
    commit_type, message = parse_commit_type(commit["subject"])

    if not should_include_commit(commit_type):
        return None

    # 기본 엔트리
    entry = f"- **{message}**"

    # body에서 세부사항 추출
    details = extract_body_details(commit["body"])

    if details:
        entry += "\n"
        for detail in details:
            entry += f"  - {detail}\n"
    else:
        entry += "\n"

    return entry


def load_changelog(changelog_path: Path) -> str:
    """기존 CHANGELOG 로드"""
    if not changelog_path.exists():
        return ""

    with open(changelog_path, "r", encoding="utf-8") as f:
        return f.read()


def find_date_section_position(content: str, date: str) -> tuple:
    """CHANGELOG에서 특정 날짜 섹션의 위치 찾기"""
    pattern = rf"^## {re.escape(date)}\s*$"
    match = re.search(pattern, content, re.MULTILINE)

    if match:
        # 해당 날짜 섹션 찾음
        section_start = match.end()

        # 다음 ## 섹션 또는 파일 끝 찾기
        next_section = re.search(r"^## \d{4}-\d{2}-\d{2}", content[section_start:], re.MULTILINE)
        if next_section:
            section_end = section_start + next_section.start()
        else:
            # 다음 --- 구분선 찾기
            separator = content.find("\n---\n", section_start)
            section_end = separator if separator != -1 else len(content)

        return (match.start(), section_end, True)

    return (-1, -1, False)


def insert_entry_to_changelog(content: str, date: str, entry: str) -> str:
    """CHANGELOG에 엔트리 삽입"""
    start, end, exists = find_date_section_position(content, date)

    if exists:
        # 기존 날짜 섹션에 추가
        # 섹션 시작 직후에 삽입
        insert_pos = start + len(f"## {date}") + 1
        # 이미 있는 내용 확인하여 중복 방지
        existing_section = content[insert_pos:end]
        if entry.strip().split("\n")[0] in existing_section:
            return content  # 이미 있으면 스킵

        new_content = content[:insert_pos] + "\n" + entry + content[insert_pos:]
        return new_content
    else:
        # 새 날짜 섹션 생성
        # 헤더 이후 첫 번째 --- 찾기
        header_end = content.find("\n---\n")
        if header_end == -1:
            # 헤더가 없으면 맨 앞에
            new_section = f"\n## {date}\n\n{entry}\n---\n"
            return new_section + content

        # 헤더 다음에 새 섹션 삽입
        insert_pos = header_end + 5  # "\n---\n" 길이
        new_section = f"\n## {date}\n\n{entry}\n---"
        new_content = content[:insert_pos] + new_section + content[insert_pos:]
        return new_content


def update_changelog_header(content: str, date: str) -> str:
    """CHANGELOG 헤더의 최종 업데이트 날짜 갱신"""
    pattern = r"\*최종 업데이트: \d{4}-\d{2}-\d{2}\*"
    replacement = f"*최종 업데이트: {date}*"
    return re.sub(pattern, replacement, content)


def main():
    vault_path = get_vault_path()
    changelog_path = vault_path / "_Docs" / "CHANGELOG.md"
    tracking_path = vault_path / ".claude" / "skills" / "changelog-generator" / "data" / "changelog_tracking.yml"

    # 1. 추적 파일 로드
    tracking = load_tracking(tracking_path)
    last_commit = tracking.get("last_processed_commit")

    # 2. 새 커밋 조회
    commits = get_commits_since(last_commit)

    if not commits:
        print("No new commits to process.")
        # 추적 파일이 없으면 초기화
        if not tracking_path.exists():
            current_head = get_current_head()
            save_tracking(tracking_path, {
                "last_processed_commit": current_head,
                "last_update_date": datetime.now().strftime("%Y-%m-%d")
            })
            print(f"Initialized tracking with HEAD: {current_head}")
        return

    # 3. CHANGELOG 로드
    content = load_changelog(changelog_path)

    # 4. 커밋 처리
    processed_count = 0
    latest_date = None

    for commit in commits:
        entry = transform_commit_to_entry(commit)
        if entry:
            content = insert_entry_to_changelog(content, commit["date"], entry)
            processed_count += 1
            if not latest_date or commit["date"] > latest_date:
                latest_date = commit["date"]
            print(f"  Added: {commit['subject'][:50]}...")

    if processed_count == 0:
        print("No relevant commits (chore commits excluded).")
        # 추적 파일 업데이트
        if commits:
            save_tracking(tracking_path, {
                "last_processed_commit": commits[0]["hash"],
                "last_update_date": datetime.now().strftime("%Y-%m-%d")
            })
        return

    # 5. 헤더 업데이트
    if latest_date:
        content = update_changelog_header(content, latest_date)

    # 6. CHANGELOG 저장
    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 7. 추적 파일 업데이트
    save_tracking(tracking_path, {
        "last_processed_commit": commits[0]["hash"],
        "last_update_date": datetime.now().strftime("%Y-%m-%d")
    })

    print(f"CHANGELOG updated: {processed_count} entries added")
    print(f"  Last processed commit: {commits[0]['hash']}")


if __name__ == "__main__":
    main()
