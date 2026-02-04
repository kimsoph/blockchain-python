# -*- coding: utf-8 -*-
"""Data processors for IBK HR data."""

from .employee_processor import EmployeeProcessor
from .promotion_processor import PromotionProcessor
from .ceo_processor import CEOProcessor

__all__ = [
    'EmployeeProcessor',
    'PromotionProcessor',
    'CEOProcessor'
]
