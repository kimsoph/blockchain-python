# -*- coding: utf-8 -*-
"""
Utility classes for md2db v2

- FileHasher: 파일 해시 생성 (SHA256)
- EncodingDetector: 인코딩 자동 감지
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from core.models import SourceFile


class FileHasher:
    """파일 해시 생성기 (SHA256)"""

    BLOCK_SIZE = 65536  # 64KB 청크

    @classmethod
    def sha256(cls, filepath: str) -> str:
        """SHA256 해시 생성 (대용량 파일 지원)

        Args:
            filepath: 파일 경로

        Returns:
            SHA256 해시 문자열 (64자 hex)
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(cls.BLOCK_SIZE), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    @classmethod
    def md5(cls, filepath: str) -> str:
        """MD5 해시 생성 (빠른 비교용)

        Args:
            filepath: 파일 경로

        Returns:
            MD5 해시 문자열 (32자 hex)
        """
        md5_hash = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(cls.BLOCK_SIZE), b''):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    @classmethod
    def fingerprint(cls, filepath: str) -> SourceFile:
        """파일 전체 지문 생성

        Args:
            filepath: 파일 경로

        Returns:
            SourceFile 객체 (해시, 크기, 수정일 포함)
        """
        path = Path(filepath)
        stat = path.stat()

        return SourceFile(
            filepath=str(path.absolute()),
            filename=path.name,
            file_hash=cls.sha256(filepath),
            file_size=stat.st_size,
            updated_at=datetime.fromtimestamp(stat.st_mtime),
            created_at=datetime.now()
        )


class EncodingDetector:
    """인코딩 자동 감지"""

    # 시도할 인코딩 목록 (우선순위 순)
    ENCODINGS = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'latin-1']

    @classmethod
    def detect(cls, filepath: str, sample_size: int = 8192) -> str:
        """파일 인코딩 감지

        Args:
            filepath: 파일 경로
            sample_size: 샘플링할 바이트 수 (기본 8KB)

        Returns:
            감지된 인코딩 문자열
        """
        for enc in cls.ENCODINGS:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    f.read(sample_size)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue

        # 최후의 수단
        return 'utf-8'

    @classmethod
    def read_file(cls, filepath: str) -> Tuple[str, str]:
        """인코딩 자동 감지하여 파일 읽기

        Args:
            filepath: 파일 경로

        Returns:
            (파일 내용, 감지된 인코딩) 튜플
        """
        for enc in cls.ENCODINGS:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                return content, enc
            except (UnicodeDecodeError, UnicodeError):
                continue

        # 최후의 수단: 오류 무시
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read(), 'utf-8'


def count_words(text: str) -> int:
    """텍스트의 단어 수 계산 (한글/영어 혼합 지원)

    Args:
        text: 분석할 텍스트

    Returns:
        단어 수
    """
    if not text:
        return 0

    # 공백 기준 분할 + 비어있지 않은 토큰만 카운트
    return len([w for w in text.split() if w.strip()])


def count_chars(text: str, exclude_spaces: bool = True) -> int:
    """텍스트의 문자 수 계산

    Args:
        text: 분석할 텍스트
        exclude_spaces: 공백 제외 여부 (기본 True)

    Returns:
        문자 수
    """
    if not text:
        return 0

    if exclude_spaces:
        return len(text.replace(' ', '').replace('\n', '').replace('\t', ''))
    return len(text)
