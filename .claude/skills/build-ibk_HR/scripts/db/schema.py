# -*- coding: utf-8 -*-
"""
IBK HR DB 스키마 정의

HR 테이블과 promotion_list 테이블의 스키마를 정의합니다.
"""

from typing import Dict, List

# 스키마 버전
SCHEMA_VERSION = "1.0.0"

# HR 테이블 스키마 (33개 컬럼)
HR_SCHEMA = {
    'table_name': 'HR',
    'columns': [
        {'name': '직번', 'type': 'INTEGER', 'description': '사원번호'},
        {'name': '이름', 'type': 'TEXT', 'description': '성명'},
        {'name': '성별', 'type': 'TEXT', 'description': 'M/F'},
        {'name': '직급', 'type': 'INTEGER', 'description': '0~5'},
        {'name': '직위', 'type': 'TEXT', 'description': '직위명'},
        {'name': '레벨', 'type': 'TEXT', 'description': '임원, 부행장, 본부장, 부점장1~3, 팀장, 책임자, 행원, 기타'},
        {'name': '승진직급', 'type': 'TEXT', 'description': '현재 승진 단계'},
        {'name': '직급연차', 'type': 'REAL', 'description': '현 직급 연차'},
        {'name': '그룹', 'type': 'TEXT', 'description': '소속 그룹'},
        {'name': '부점', 'type': 'TEXT', 'description': '소속 부점'},
        {'name': '팀명', 'type': 'TEXT', 'description': '소속 팀'},
        {'name': '서열', 'type': 'INTEGER', 'description': '직원명부순서'},
        {'name': '랭킹', 'type': 'INTEGER', 'description': '랭킹 (999999=제외)'},
        {'name': '출생년월', 'type': 'INTEGER', 'description': 'YYYYMM'},
        {'name': '입행년월', 'type': 'INTEGER', 'description': 'YYYYMM'},
        {'name': '현재나이', 'type': 'REAL', 'description': '기준년월 기준'},
        {'name': '입행연차', 'type': 'REAL', 'description': '기준년월 기준'},
        {'name': '입행나이', 'type': 'REAL', 'description': '입행 당시 나이'},
        {'name': '임피년월', 'type': 'INTEGER', 'description': '만 57세 도달 년월'},
        {'name': '승진경로', 'type': 'TEXT', 'description': '예: "승1←승2←승3"'},
        {'name': '소요기간경로', 'type': 'TEXT', 'description': '각 승진 소요기간'},
        {'name': '승진부점경로', 'type': 'TEXT', 'description': '승진 당시 부점 이력'},
        {'name': '세분', 'type': 'TEXT', 'description': '지점/지본/본영/본점/해외'},
        {'name': '본점여부', 'type': 'INTEGER', 'description': '0/1'},
        {'name': '남성여부', 'type': 'INTEGER', 'description': '0/1'},
        {'name': '인원포함여부', 'type': 'INTEGER', 'description': '0/1'},
        {'name': '승진대상여부', 'type': 'INTEGER', 'description': '0/1'},
        {'name': '실제생년월일', 'type': 'TEXT', 'description': 'YYYY-MM-DD'},
        {'name': '직위년월', 'type': 'INTEGER', 'description': 'YYYYMM'},
        {'name': '소속년월', 'type': 'INTEGER', 'description': 'YYYYMM'},
        {'name': '소속연차', 'type': 'REAL', 'description': '현 소속 연차'},
        {'name': '오류여부', 'type': 'INTEGER', 'description': '0/1'},
        {'name': '오류사유', 'type': 'TEXT', 'description': '오류 상세'}
    ]
}

# promotion_list 테이블 스키마 (8개 컬럼)
PROMOTION_SCHEMA = {
    'table_name': 'promotion_list',
    'columns': [
        {'name': '직번', 'type': 'INTEGER', 'description': '사원번호'},
        {'name': '이름', 'type': 'TEXT', 'description': '성명'},
        {'name': '승진직급', 'type': 'TEXT', 'description': '승0~승4, PCEO'},
        {'name': '소요기간', 'type': 'REAL', 'description': '년 단위'},
        {'name': '승진년월', 'type': 'INTEGER', 'description': 'YYYYMM'},
        {'name': '승진부점', 'type': 'TEXT', 'description': '승진 당시 소속'},
        {'name': '오류여부', 'type': 'INTEGER', 'description': '0/1'},
        {'name': '오류사유', 'type': 'TEXT', 'description': '(미사용)'}
    ]
}

# HR 테이블 인덱스
HR_INDEXES = [
    {'name': 'idx_HR_직번', 'column': '직번'},
    {'name': 'idx_HR_이름', 'column': '이름'},
    {'name': 'idx_HR_직급', 'column': '직급'},
    {'name': 'idx_HR_레벨', 'column': '레벨'},
    {'name': 'idx_HR_출생년월', 'column': '출생년월'},
    {'name': 'idx_HR_입행년월', 'column': '입행년월'}
]

# promotion_list 테이블 인덱스
PROMOTION_INDEXES = [
    {'name': 'idx_promotion_list_직번', 'column': '직번'},
    {'name': 'idx_promotion_list_이름', 'column': '이름'},
    {'name': 'idx_promotion_list_승진직급', 'column': '승진직급'},
    {'name': 'idx_promotion_list_승진년월', 'column': '승진년월'},
    {'name': 'idx_promotion_list_승진부점', 'column': '승진부점'}
]


def get_hr_column_names() -> List[str]:
    """HR 테이블 컬럼명 목록 반환"""
    return [col['name'] for col in HR_SCHEMA['columns']]


def get_promotion_column_names() -> List[str]:
    """promotion_list 테이블 컬럼명 목록 반환"""
    return [col['name'] for col in PROMOTION_SCHEMA['columns']]
