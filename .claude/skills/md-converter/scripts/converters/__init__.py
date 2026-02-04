# -*- coding: utf-8 -*-
"""
md-converter: 문서 포맷 변환 모듈

지원 포맷:
- HWPX: ZIP + XML 직접 파싱
- PDF: markitdown CLI 래핑 (v1.1+)
- DOCX: markitdown CLI 래핑 (v1.2+)
"""

from .base import BaseConverter, ConversionResult
from .hwpx import HWPXConverter

__all__ = ['BaseConverter', 'ConversionResult', 'HWPXConverter']
