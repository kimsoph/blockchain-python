#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_report_versions 단위 테스트
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from archive_report_versions import VersionedFile, ReportArchiver


class TestVersionedFile:
    """VersionedFile 클래스 테스트"""

    def test_version_number_none(self):
        """suffix 없는 파일은 v0"""
        vf = VersionedFile(
            path=Path("20260114_분석.md"),
            date_str="20260114",
            title="분석",
            version=None
        )
        assert vf.version_number == 0.0

    def test_version_number_simple(self):
        """단순 버전 번호"""
        vf = VersionedFile(
            path=Path("20260114_분석_v1.md"),
            date_str="20260114",
            title="분석",
            version="1"
        )
        assert vf.version_number == 1.0

    def test_version_number_decimal(self):
        """소수점 버전 번호"""
        vf = VersionedFile(
            path=Path("20260114_분석_v2.5.md"),
            date_str="20260114",
            title="분석",
            version="2.5"
        )
        assert vf.version_number == 2.5

    def test_base_key(self):
        """그룹화 키 생성"""
        vf = VersionedFile(
            path=Path("20260114_IBK_분석_v1.md"),
            date_str="20260114",
            title="IBK_분석",
            version="1"
        )
        assert vf.base_key == "20260114_IBK_분석"


class TestReportArchiverPattern:
    """파일명 패턴 매칭 테스트"""

    @pytest.fixture
    def archiver(self, tmp_path):
        """임시 아카이버 생성"""
        return ReportArchiver(tmp_path, dry_run=True)

    def test_pattern_simple(self, archiver):
        """기본 파일명 패턴"""
        match = archiver.VERSION_PATTERN.match("20260114_분석.md")
        assert match is not None
        assert match.group('date') == "20260114"
        assert match.group('title') == "분석"
        assert match.group('version') is None

    def test_pattern_with_version(self, archiver):
        """버전 포함 파일명"""
        match = archiver.VERSION_PATTERN.match("20260114_분석_v1.md")
        assert match is not None
        assert match.group('version') == "1"

    def test_pattern_with_decimal_version(self, archiver):
        """소수점 버전 파일명"""
        match = archiver.VERSION_PATTERN.match("20260114_분석_v2.5.md")
        assert match is not None
        assert match.group('version') == "2.5"

    def test_pattern_complex_title(self, archiver):
        """복잡한 제목 파일명"""
        match = archiver.VERSION_PATTERN.match("20260114_IBK_임금수준_적정성_분석_v2.5.md")
        assert match is not None
        assert match.group('date') == "20260114"
        assert match.group('title') == "IBK_임금수준_적정성_분석"
        assert match.group('version') == "2.5"

    def test_pattern_no_match(self, archiver):
        """패턴 불일치"""
        match = archiver.VERSION_PATTERN.match("CLAUDE.md")
        assert match is None

        match = archiver.VERSION_PATTERN.match("readme.md")
        assert match is None


class TestReportArchiverGrouping:
    """버전 그룹화 테스트"""

    def test_group_versions(self):
        """버전 그룹화 및 정렬"""
        files = [
            VersionedFile(Path("20260114_분석.md"), "20260114", "분석", None),
            VersionedFile(Path("20260114_분석_v1.md"), "20260114", "분석", "1"),
            VersionedFile(Path("20260114_분석_v2.5.md"), "20260114", "분석", "2.5"),
        ]

        archiver = ReportArchiver(Path("."), dry_run=True)
        groups = archiver.group_versions(files)

        assert len(groups) == 1
        assert "20260114_분석" in groups

        group = groups["20260114_분석"]
        assert len(group) == 3

        # 정렬 확인: v0 < v1 < v2.5
        assert group[0].version_number == 0.0
        assert group[1].version_number == 1.0
        assert group[2].version_number == 2.5


class TestReportArchiverFrontmatter:
    """프론트매터 처리 테스트"""

    def test_update_frontmatter_existing(self):
        """기존 프론트매터에 추가"""
        content = """---
id: "RPT-20260114-01"
title: "테스트"
---

# 본문
"""
        archiver = ReportArchiver(Path("."), dry_run=True)
        updated = archiver.update_frontmatter(content, "3_Resources/R-reports/test.md")

        assert 'archived: true' in updated
        assert f'archived_date: "{date.today().isoformat()}"' in updated
        assert 'archived_reason: "구버전"' in updated
        assert 'original_path: "3_Resources/R-reports/test.md"' in updated
        assert '# 본문' in updated

    def test_update_frontmatter_new(self):
        """프론트매터 없는 경우 새로 생성"""
        content = "# 본문 내용"

        archiver = ReportArchiver(Path("."), dry_run=True)
        updated = archiver.update_frontmatter(content, "3_Resources/R-reports/test.md")

        assert updated.startswith('---\n')
        assert 'archived: true' in updated
        assert '# 본문 내용' in updated


class TestReportArchiverIntegration:
    """통합 테스트"""

    @pytest.fixture
    def setup_vault(self, tmp_path):
        """테스트용 Vault 구조 생성"""
        # 폴더 구조 생성
        reports_dir = tmp_path / "3_Resources" / "R-reports"
        archive_dir = tmp_path / "4_Archive" / "Resources" / "R-reports"
        reports_dir.mkdir(parents=True)
        archive_dir.mkdir(parents=True)

        # 테스트 파일 생성
        (reports_dir / "CLAUDE.md").write_text("# CLAUDE.md", encoding='utf-8')
        (reports_dir / "20260114_분석.md").write_text("---\nid: test\n---\n# v0", encoding='utf-8')
        (reports_dir / "20260114_분석_v1.md").write_text("---\nid: test\n---\n# v1", encoding='utf-8')
        (reports_dir / "20260114_분석_v2.5.md").write_text("---\nid: test\n---\n# v2.5", encoding='utf-8')
        (reports_dir / "20260113_보고서.md").write_text("# 단일 파일", encoding='utf-8')

        return tmp_path

    def test_scan_reports(self, setup_vault):
        """파일 스캔"""
        archiver = ReportArchiver(setup_vault, dry_run=True)
        files = archiver.scan_reports()

        # CLAUDE.md 제외, 4개 파일
        assert len(files) == 4

    def test_find_archive_targets(self, setup_vault):
        """아카이브 대상 찾기"""
        archiver = ReportArchiver(setup_vault, dry_run=True)
        targets, keeps = archiver.find_archive_targets()

        # v0, v1이 아카이브 대상 (v2.5 유지)
        assert len(targets) == 2
        target_names = [t.path.name for t in targets]
        assert "20260114_분석.md" in target_names
        assert "20260114_분석_v1.md" in target_names

        # v2.5가 유지 대상
        assert len(keeps) == 1
        assert keeps[0].path.name == "20260114_분석_v2.5.md"

    def test_dry_run(self, setup_vault):
        """dry-run 모드"""
        archiver = ReportArchiver(setup_vault, dry_run=True)
        result = archiver.run()

        # dry-run이므로 파일이 실제로 이동되지 않음
        reports_dir = setup_vault / "3_Resources" / "R-reports"
        assert (reports_dir / "20260114_분석.md").exists()
        assert (reports_dir / "20260114_분석_v1.md").exists()

    def test_actual_archive(self, setup_vault):
        """실제 아카이빙"""
        archiver = ReportArchiver(setup_vault, dry_run=False)
        result = archiver.run()

        reports_dir = setup_vault / "3_Resources" / "R-reports"
        archive_dir = setup_vault / "4_Archive" / "Resources" / "R-reports"

        # 원본에서 삭제됨
        assert not (reports_dir / "20260114_분석.md").exists()
        assert not (reports_dir / "20260114_분석_v1.md").exists()

        # v2.5는 유지
        assert (reports_dir / "20260114_분석_v2.5.md").exists()

        # 아카이브로 이동됨
        assert (archive_dir / "20260114_분석.md").exists()
        assert (archive_dir / "20260114_분석_v1.md").exists()

        # 프론트매터에 아카이브 정보 추가 확인
        archived_content = (archive_dir / "20260114_분석.md").read_text(encoding='utf-8')
        assert 'archived: true' in archived_content

        # 결과 확인
        assert result.success
        assert result.archived_count == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
