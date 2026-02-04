# -*- coding: utf-8 -*-
"""
Markdown Exporter for md2db v2

DB에서 마크다운으로 복원합니다.
"""

import re
from typing import Optional

from db.sqlite_reader import DatabaseReader


class MarkdownExporter:
    """DB에서 마크다운으로 복원"""

    def __init__(self, reader: DatabaseReader):
        """
        Args:
            reader: DatabaseReader 인스턴스
        """
        self.reader = reader

    def export(self, output_path: str, section_path: str = None,
               max_level: int = None, document_id: int = None) -> None:
        """마크다운 파일로 내보내기

        Args:
            output_path: 출력 파일 경로
            section_path: 특정 섹션 경로 (예: "1.2") - 하위 섹션 포함
            max_level: 최대 헤더 레벨
            document_id: 문서 ID (None이면 첫 번째 문서)
        """
        cursor = self.reader.conn.cursor()

        # 기본 문서 ID (첫 번째 문서)
        if document_id is None:
            cursor.execute("SELECT id FROM documents LIMIT 1")
            row = cursor.fetchone()
            if not row:
                raise ValueError("DB에 문서가 없습니다.")
            document_id = row['id']

        # 섹션 필터링
        if section_path:
            cursor.execute("""
                SELECT id, path FROM sections
                WHERE document_id = ? AND (path = ? OR path LIKE ?)
                ORDER BY position
            """, (document_id, section_path, f'{section_path}.%'))
        else:
            cursor.execute("""
                SELECT id, path FROM sections
                WHERE document_id = ?
                ORDER BY position
            """, (document_id,))

        section_ids = [(r['id'], r['path']) for r in cursor.fetchall()]

        # 마크다운 생성
        output_lines = []

        for section_id, path in section_ids:
            # 블록 조회
            cursor.execute("""
                SELECT raw_markdown, type FROM blocks
                WHERE section_id = ?
                ORDER BY position
            """, (section_id,))

            for block in cursor.fetchall():
                # 레벨 필터링
                if max_level and block['type'] == 'header':
                    level = block['raw_markdown'].count('#', 0, 7)
                    if level > max_level:
                        continue

                output_lines.append(block['raw_markdown'])
                output_lines.append('')  # 블록 간 빈 줄

        # 연속 빈 줄 정리
        content = '\n'.join(output_lines)
        content = re.sub(r'\n{3,}', '\n\n', content)

        # 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def export_section(self, section_id: int) -> str:
        """특정 섹션만 마크다운으로 반환

        Args:
            section_id: 섹션 ID

        Returns:
            마크다운 문자열
        """
        blocks = self.reader.get_blocks(section_id)

        lines = []
        for block in blocks:
            lines.append(block['raw_markdown'])
            lines.append('')

        content = '\n'.join(lines)
        return re.sub(r'\n{3,}', '\n\n', content)

    def export_blocks(self, block_ids: list) -> str:
        """특정 블록들만 마크다운으로 반환

        Args:
            block_ids: 블록 ID 목록

        Returns:
            마크다운 문자열
        """
        cursor = self.reader.conn.cursor()

        lines = []
        for block_id in block_ids:
            cursor.execute("SELECT raw_markdown FROM blocks WHERE id = ?", (block_id,))
            row = cursor.fetchone()
            if row:
                lines.append(row['raw_markdown'])
                lines.append('')

        content = '\n'.join(lines)
        return re.sub(r'\n{3,}', '\n\n', content)
