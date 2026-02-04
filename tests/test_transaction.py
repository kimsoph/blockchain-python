# -*- coding: utf-8 -*-
"""
Transaction 클래스 테스트

트랜잭션 생성, 유효성 검사 기능을 테스트합니다.
"""

import pytest
from src.transaction import Transaction


class TestTransactionCreation:
    """트랜잭션 생성 관련 테스트"""

    def test_transaction_creation(self, sample_transaction):
        """트랜잭션 생성 확인"""
        assert sample_transaction.sender == "Alice"
        assert sample_transaction.recipient == "Bob"
        assert sample_transaction.amount == 50.0
        assert sample_transaction.timestamp is not None

    def test_transaction_with_korean(self):
        """한글 주소로 트랜잭션 생성"""
        tx = Transaction("김철수", "이영희", 100)
        assert tx.sender == "김철수"
        assert tx.recipient == "이영희"
        assert tx.amount == 100

    def test_transaction_with_float_amount(self):
        """소수점 금액 트랜잭션"""
        tx = Transaction("A", "B", 99.99)
        assert tx.amount == 99.99


class TestSerialization:
    """직렬화 관련 테스트"""

    def test_to_dict(self, sample_transaction):
        """딕셔너리 변환 검증"""
        tx_dict = sample_transaction.to_dict()

        assert tx_dict['sender'] == "Alice"
        assert tx_dict['recipient'] == "Bob"
        assert tx_dict['amount'] == 50.0
        assert 'timestamp' in tx_dict

    def test_to_dict_keys(self, sample_transaction):
        """딕셔너리 키 확인"""
        tx_dict = sample_transaction.to_dict()
        expected_keys = {'sender', 'recipient', 'amount', 'timestamp'}
        assert set(tx_dict.keys()) == expected_keys


class TestValidation:
    """유효성 검사 테스트"""

    def test_is_valid_normal(self, sample_transaction):
        """정상 트랜잭션 유효성"""
        assert sample_transaction.is_valid() is True

    def test_is_valid_no_sender(self):
        """발신자 없음 → 무효"""
        tx = Transaction("", "Bob", 50)
        assert tx.is_valid() is False

    def test_is_valid_none_sender(self):
        """발신자 None → 무효"""
        tx = Transaction(None, "Bob", 50)
        assert tx.is_valid() is False

    def test_is_valid_no_recipient(self):
        """수신자 없음 → 무효"""
        tx = Transaction("Alice", "", 50)
        assert tx.is_valid() is False

    def test_is_valid_none_recipient(self):
        """수신자 None → 무효"""
        tx = Transaction("Alice", None, 50)
        assert tx.is_valid() is False

    def test_is_valid_zero_amount(self):
        """금액 0 → 무효"""
        tx = Transaction("Alice", "Bob", 0)
        assert tx.is_valid() is False

    def test_is_valid_negative_amount(self):
        """음수 금액 → 무효"""
        tx = Transaction("Alice", "Bob", -10)
        assert tx.is_valid() is False

    def test_is_valid_self_transfer(self):
        """자기전송 금지 (일반 사용자)"""
        tx = Transaction("Alice", "Alice", 50)
        assert tx.is_valid() is False

    def test_is_valid_system_self_transfer(self):
        """SYSTEM 자기전송 허용"""
        tx = Transaction("SYSTEM", "SYSTEM", 100)
        assert tx.is_valid() is True

    def test_is_valid_system_transaction(self, system_transaction):
        """시스템 보상 트랜잭션 유효성"""
        assert system_transaction.is_valid() is True


class TestStringRepresentation:
    """문자열 표현 테스트"""

    def test_transaction_str(self, sample_transaction):
        """__str__ 메서드 테스트"""
        str_repr = str(sample_transaction)

        assert "Transaction:" in str_repr
        assert "From:" in str_repr
        assert "To:" in str_repr
        assert "Amount:" in str_repr
        assert "Alice" in str_repr
        assert "Bob" in str_repr
        assert "50" in str_repr

    def test_transaction_repr(self, sample_transaction):
        """__repr__ 메서드 테스트"""
        repr_str = repr(sample_transaction)

        assert "Transaction(" in repr_str
        assert "Alice" in repr_str
        assert "Bob" in repr_str
        assert "50" in str(repr_str)
