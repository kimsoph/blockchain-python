#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R-reports 이전 버전 자동 아카이빙 스크립트

버전 규칙: suffix 번호가 높을수록 최신
  _v3.0 > _v2.5 > _v1 > suffix 없음 (v0)

사용법:
    python archive_report_versions.py [--dry-run] [--file FILE] [--verbose]
"""

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

# 한글 인코딩 설정
os.environ['PYTHONUTF8'] = '1'


@dataclass
class VersionedFile:
    """버전 정보를 담은 파일 객체"""
    path: Path
    date_str: str
    title: str
    version: Optional[str]

    @property
    def version_number(self) -> float:
        """버전 번호를 숫자로 변환 (suffix 없음 = 0)"""
        if self.version is None:
            return 0.0
        try:
            return float(self.version)
        except ValueError:
            # "1.2.3" 같은 경우 첫 두 부분만 사용
            parts = self.version.split('.')
            if len(parts) >= 2:
                try:
                    return float(f"{parts[0]}.{parts[1]}")
                except ValueError:
                    return 0.0
            return 0.0

    @property
    def base_key(self) -> str:
        """그룹화 키 (날짜_제목)"""
        return f"{self.date_str}_{self.title}"


@dataclass
class ArchiveResult:
    """아카이빙 결과"""
    success: bool
    archived_count: int = 0
    skipped_count: int = 0
    errors: list = field(default_factory=list)
    archived_files: list = field(default_factory=list)


class ReportArchiver:
    """보고서 버전 아카이버"""

    # 파일명 패턴: YYYYMMDD_제목_v버전.md
    VERSION_PATTERN = re.compile(
        r'^(?P<date>\d{8})_(?P<title>.+?)(?:_v(?P<version>[\d.]+))?\.md$'
    )

    # 제외할 파일
    EXCLUDED_FILES = {'CLAUDE.md', 'prompts.md'}

    def __init__(self, vault_root: Path, dry_run: bool = False, verbose: bool = False):
        self.vault_root = vault_root
        self.dry_run = dry_run
        self.verbose = verbose
        self.reports_dir = vault_root / "3_Resources" / "R-reports"
        self.archive_dir = vault_root / "4_Archive" / "Resources" / "R-reports"

    def log(self, message: str, level: str = "INFO"):
        """로그 출력"""
        if level == "DEBUG" and not self.verbose:
            return
        prefix = {"INFO": "", "DEBUG": "[DEBUG] ", "WARN": "[경고] ", "ERROR": "[오류] "}
        print(f"{prefix.get(level, '')}{message}")

    def scan_reports(self) -> list[VersionedFile]:
        """R-reports 폴더 스캔"""
        files = []

        if not self.reports_dir.exists():
            self.log(f"R-reports 폴더가 없습니다: {self.reports_dir}", "ERROR")
            return files

        for f in self.reports_dir.glob("*.md"):
            if f.name in self.EXCLUDED_FILES:
                self.log(f"제외: {f.name}", "DEBUG")
                continue

            match = self.VERSION_PATTERN.match(f.name)
            if match:
                vf = VersionedFile(
                    path=f,
                    date_str=match.group('date'),
                    title=match.group('title'),
                    version=match.group('version')
                )
                files.append(vf)
                self.log(f"발견: {f.name} (v{vf.version_number})", "DEBUG")
            else:
                self.log(f"패턴 불일치: {f.name}", "DEBUG")

        return files

    def group_versions(self, files: list[VersionedFile]) -> dict[str, list[VersionedFile]]:
        """버전별 그룹화"""
        groups: dict[str, list[VersionedFile]] = {}

        for f in files:
            key = f.base_key
            if key not in groups:
                groups[key] = []
            groups[key].append(f)

        # 각 그룹 내에서 버전 번호 순으로 정렬 (높은 것이 뒤로)
        for key in groups:
            groups[key].sort(key=lambda x: x.version_number)

        return groups

    def find_archive_targets(self) -> tuple[list[VersionedFile], list[VersionedFile]]:
        """아카이브 대상 파일 찾기

        Returns:
            (아카이브 대상 목록, 유지 대상 목록)
        """
        files = self.scan_reports()
        self.log(f"\n[스캔] R-reports 폴더: {len(files)}개 파일 발견")

        groups = self.group_versions(files)
        multi_version_groups = {k: v for k, v in groups.items() if len(v) > 1}
        self.log(f"[그룹화] {len(multi_version_groups)}개 버전 그룹 감지 (2개 이상 버전)")

        targets = []
        keeps = []

        for key, group in multi_version_groups.items():
            # 가장 높은 버전 = 최신 (유지)
            latest = group[-1]
            old_versions = group[:-1]

            keeps.append(latest)
            targets.extend(old_versions)

            self.log(f"\n  그룹: {key}", "DEBUG")
            self.log(f"    최신: {latest.path.name} (v{latest.version_number})", "DEBUG")
            for old in old_versions:
                self.log(f"    이전: {old.path.name} (v{old.version_number})", "DEBUG")

        return targets, keeps

    def update_frontmatter(self, content: str, original_path: str) -> str:
        """프론트매터에 아카이빙 정보 추가"""
        archive_info = {
            'archived': True,
            'archived_date': date.today().isoformat(),
            'archived_reason': '구버전',
            'original_path': original_path
        }

        # YAML frontmatter 파싱
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                # 기존 frontmatter에 추가
                fm_lines = parts[1].strip().split('\n')
                for key, value in archive_info.items():
                    if isinstance(value, bool):
                        fm_lines.append(f"{key}: {str(value).lower()}")
                    elif isinstance(value, str):
                        fm_lines.append(f'{key}: "{value}"')
                    else:
                        fm_lines.append(f"{key}: {value}")

                return f"---\n{chr(10).join(fm_lines)}\n---{parts[2]}"

        # frontmatter 없으면 새로 생성
        fm_lines = []
        for key, value in archive_info.items():
            if isinstance(value, bool):
                fm_lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, str):
                fm_lines.append(f'{key}: "{value}"')
            else:
                fm_lines.append(f"{key}: {value}")

        return f"---\n{chr(10).join(fm_lines)}\n---\n\n{content}"

    def get_archive_path(self, source_path: Path) -> Path:
        """아카이브 경로 생성"""
        return self.archive_dir / source_path.name

    def handle_existing_file(self, target_path: Path) -> Path:
        """대상 경로에 파일 존재 시 처리"""
        if not target_path.exists():
            return target_path

        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        stem = target_path.stem
        suffix = target_path.suffix
        return target_path.parent / f"{stem}_{timestamp}{suffix}"

    def archive_file(self, vf: VersionedFile, latest: VersionedFile) -> bool:
        """파일 아카이빙 실행"""
        source_path = vf.path
        target_path = self.get_archive_path(source_path)
        target_path = self.handle_existing_file(target_path)

        original_path = f"3_Resources/R-reports/{source_path.name}"

        try:
            # 파일 읽기
            try:
                content = source_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # 다른 인코딩 시도
                import chardet
                with open(source_path, 'rb') as f:
                    raw = f.read()
                    detected = chardet.detect(raw)
                    encoding = detected.get('encoding', 'cp949')
                content = raw.decode(encoding)
                self.log(f"  인코딩 변환: {encoding} → UTF-8", "WARN")

            # 프론트매터 업데이트
            updated_content = self.update_frontmatter(content, original_path)

            if self.dry_run:
                self.log(f"  [DRY-RUN] {source_path.name} → {target_path}")
                return True

            # 아카이브 폴더 생성
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일 쓰기
            target_path.write_text(updated_content, encoding='utf-8')

            # 원본 삭제
            source_path.unlink()

            self.log(f"  [OK] {source_path.name} → {target_path.relative_to(self.vault_root)}")
            return True

        except Exception as e:
            self.log(f"  [실패] {source_path.name}: {e}", "ERROR")
            return False

    def run(self, target_file: Optional[str] = None) -> ArchiveResult:
        """메인 실행"""
        result = ArchiveResult(success=True)

        targets, keeps = self.find_archive_targets()

        if not targets:
            self.log("\n아카이브 대상이 없습니다.")
            return result

        # 특정 파일만 처리
        if target_file:
            targets = [t for t in targets if t.path.name == target_file]
            if not targets:
                self.log(f"\n지정한 파일이 아카이브 대상이 아닙니다: {target_file}")
                return result

        self.log(f"\n[아카이브 대상] {len(targets)}개 파일")

        # 대상별로 최신 버전 찾기
        files = self.scan_reports()
        groups = self.group_versions(files)

        for vf in targets:
            group = groups.get(vf.base_key, [])
            latest = group[-1] if group else None

            version_str = f"v{vf.version_number}" if vf.version else "v0 (초기)"
            latest_str = f"v{latest.version_number}" if latest else "?"

            self.log(f"\n  {vf.path.name} ({version_str})")
            self.log(f"    → 최신: {latest.path.name} ({latest_str})")

            if self.archive_file(vf, latest):
                result.archived_count += 1
                result.archived_files.append(str(vf.path.name))
            else:
                result.errors.append(str(vf.path.name))

        # 결과 요약
        self.log(f"\n[완료] {result.archived_count}개 파일 아카이빙")
        if result.errors:
            self.log(f"[오류] {len(result.errors)}개 파일 실패", "ERROR")
            result.success = False

        return result


def main():
    parser = argparse.ArgumentParser(
        description='R-reports 이전 버전 자동 아카이빙'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='실제 이동 없이 대상만 확인'
    )
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='특정 파일만 처리'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )

    args = parser.parse_args()

    # Vault 루트 찾기
    script_path = Path(__file__).resolve()
    vault_root = script_path.parents[3]  # scripts → archive-report-versions → skills → .claude → vault_root

    # 실제로는 .claude가 vault 내부에 있으므로 4단계 위
    if not (vault_root / "3_Resources").exists():
        vault_root = script_path.parents[4]

    if not (vault_root / "3_Resources").exists():
        print(f"[오류] Vault 루트를 찾을 수 없습니다: {vault_root}")
        return 1

    print(f"Vault: {vault_root}")

    archiver = ReportArchiver(vault_root, dry_run=args.dry_run, verbose=args.verbose)
    result = archiver.run(target_file=args.file)

    return 0 if result.success else 1


if __name__ == '__main__':
    sys.exit(main())
