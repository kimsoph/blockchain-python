# -*- coding: utf-8 -*-
"""
Wallet 및 암호화 유틸리티 테스트

지갑 생성, 서명, 검증 기능을 테스트합니다.
"""

import pytest
from src.wallet import Wallet
from src.transaction import Transaction
from src.crypto_utils import (
    generate_private_key,
    private_key_to_public_key,
    public_key_to_address,
    sign_message,
    verify_signature,
    SECP256K1_N
)


class TestCryptoUtils:
    """암호화 유틸리티 테스트"""

    def test_generate_private_key(self):
        """개인키 생성"""
        key1 = generate_private_key()
        key2 = generate_private_key()

        # 키는 유효 범위 내
        assert 0 < key1 < SECP256K1_N
        assert 0 < key2 < SECP256K1_N

        # 매번 다른 키 생성
        assert key1 != key2

    def test_private_key_to_public_key(self):
        """공개키 생성"""
        private_key = generate_private_key()
        public_key = private_key_to_public_key(private_key)

        assert isinstance(public_key, tuple)
        assert len(public_key) == 2
        assert public_key[0] > 0
        assert public_key[1] > 0

    def test_public_key_to_address(self):
        """주소 생성"""
        private_key = generate_private_key()
        public_key = private_key_to_public_key(private_key)
        address = public_key_to_address(public_key)

        # 주소는 40자리 16진수 (20바이트)
        assert len(address) == 40
        assert all(c in '0123456789abcdef' for c in address)

    def test_sign_and_verify_message(self):
        """메시지 서명 및 검증"""
        private_key = generate_private_key()
        public_key = private_key_to_public_key(private_key)
        message = "테스트 메시지"

        signature = sign_message(private_key, message)

        assert isinstance(signature, tuple)
        assert len(signature) == 2

        # 검증
        assert verify_signature(public_key, message, signature) is True

    def test_verify_with_wrong_message(self):
        """잘못된 메시지로 검증 실패"""
        private_key = generate_private_key()
        public_key = private_key_to_public_key(private_key)

        signature = sign_message(private_key, "원본 메시지")
        assert verify_signature(public_key, "변조된 메시지", signature) is False

    def test_verify_with_wrong_public_key(self):
        """잘못된 공개키로 검증 실패"""
        private_key1 = generate_private_key()
        private_key2 = generate_private_key()
        public_key2 = private_key_to_public_key(private_key2)

        message = "테스트"
        signature = sign_message(private_key1, message)

        # 다른 공개키로 검증 시도
        assert verify_signature(public_key2, message, signature) is False


class TestWalletCreation:
    """지갑 생성 테스트"""

    def test_create_new_wallet(self):
        """새 지갑 생성"""
        wallet = Wallet()

        assert wallet.private_key > 0
        assert len(wallet.public_key) == 2
        assert len(wallet.address) == 40

    def test_create_wallet_with_private_key(self):
        """기존 개인키로 지갑 생성"""
        original = Wallet()
        restored = Wallet(original.private_key)

        assert restored.private_key == original.private_key
        assert restored.public_key == original.public_key
        assert restored.address == original.address

    def test_wallet_address_consistency(self):
        """같은 개인키는 항상 같은 주소"""
        wallet1 = Wallet()
        wallet2 = Wallet(wallet1.private_key)

        assert wallet1.address == wallet2.address

    def test_different_wallets_different_addresses(self):
        """다른 지갑은 다른 주소"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        assert wallet1.address != wallet2.address


class TestWalletSigning:
    """지갑 서명 테스트"""

    def test_sign_message(self):
        """메시지 서명"""
        wallet = Wallet()
        message = "테스트 메시지"

        signature = wallet.sign(message)

        assert isinstance(signature, tuple)
        assert len(signature) == 2

    def test_sign_hex(self):
        """16진수 서명"""
        wallet = Wallet()
        message = "테스트"

        signature_hex = wallet.sign_hex(message)

        # 서명은 128자리 (r: 64 + s: 64)
        assert len(signature_hex) == 128
        assert all(c in '0123456789abcdef' for c in signature_hex)

    def test_verify_signature(self):
        """서명 검증"""
        wallet = Wallet()
        message = "테스트 메시지"

        signature = wallet.sign(message)
        is_valid = Wallet.verify(wallet.public_key, message, signature)

        assert is_valid is True

    def test_verify_hex_signature(self):
        """16진수 서명 검증"""
        wallet = Wallet()
        message = "테스트"

        signature_hex = wallet.sign_hex(message)
        is_valid = Wallet.verify_hex(wallet.public_key_hex, message, signature_hex)

        assert is_valid is True

    def test_verify_fails_with_wrong_message(self):
        """잘못된 메시지로 검증 실패"""
        wallet = Wallet()
        signature = wallet.sign("원본")

        is_valid = Wallet.verify(wallet.public_key, "변조", signature)
        assert is_valid is False


class TestWalletSerialization:
    """지갑 직렬화 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        wallet = Wallet()
        data = wallet.to_dict()

        assert 'private_key' in data
        assert 'public_key' in data
        assert 'address' in data

    def test_to_public_dict(self):
        """공개 정보만 딕셔너리 변환"""
        wallet = Wallet()
        data = wallet.to_public_dict()

        assert 'private_key' not in data
        assert 'public_key' in data
        assert 'address' in data

    def test_export_import_private_key(self):
        """개인키 내보내기/가져오기"""
        original = Wallet()
        json_str = original.export_private_key()

        restored = Wallet.from_json(json_str)

        assert restored.private_key == original.private_key
        assert restored.address == original.address

    def test_from_private_key_hex(self):
        """16진수 개인키로 복원"""
        original = Wallet()
        restored = Wallet.from_private_key_hex(original.private_key_hex)

        assert restored.address == original.address

    def test_private_key_hex_format(self):
        """개인키 16진수 형식"""
        wallet = Wallet()

        # 64자리 16진수
        assert len(wallet.private_key_hex) == 64

    def test_public_key_hex_format(self):
        """공개키 16진수 형식"""
        wallet = Wallet()

        # 128자리 16진수 (x: 64 + y: 64)
        assert len(wallet.public_key_hex) == 128


class TestWalletStringRepresentation:
    """지갑 문자열 표현 테스트"""

    def test_str(self):
        """__str__ 테스트"""
        wallet = Wallet()
        str_repr = str(wallet)

        assert "Wallet" in str_repr
        assert "Address" in str_repr
        assert "Public Key" in str_repr

    def test_repr(self):
        """__repr__ 테스트"""
        wallet = Wallet()
        repr_str = repr(wallet)

        assert "Wallet(" in repr_str
        assert "address=" in repr_str


class TestTransactionSigning:
    """트랜잭션 서명 테스트"""

    def test_sign_transaction(self):
        """트랜잭션 서명"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient_address", 100)

        tx.sign(wallet)

        assert tx.signature is not None
        assert tx.sender_public_key is not None
        assert len(tx.signature) == 128

    def test_verify_transaction_signature(self):
        """트랜잭션 서명 검증"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient_address", 100)

        tx.sign(wallet)

        assert tx.verify_signature() is True

    def test_unsigned_transaction_invalid(self):
        """서명 없는 트랜잭션은 검증 실패"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient_address", 100)

        # 서명하지 않음
        assert tx.verify_signature() is False

    def test_system_transaction_no_signature_needed(self):
        """시스템 트랜잭션은 서명 불필요"""
        tx = Transaction("SYSTEM", "miner_address", 100)

        # 서명 없이도 검증 통과
        assert tx.verify_signature() is True

    def test_sign_with_wrong_wallet_fails(self):
        """잘못된 지갑으로 서명 시도 실패"""
        wallet1 = Wallet()
        wallet2 = Wallet()
        tx = Transaction(wallet1.address, "recipient", 100)

        with pytest.raises(ValueError, match="일치하지 않습니다"):
            tx.sign(wallet2)

    def test_tampered_transaction_invalid(self):
        """변조된 트랜잭션은 검증 실패"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 100)
        tx.sign(wallet)

        # 금액 변조
        tx.amount = 1000

        assert tx.verify_signature() is False

    def test_transaction_hash(self):
        """트랜잭션 해시"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 100)

        tx_hash = tx.get_hash()

        # SHA256 해시 = 64자리
        assert len(tx_hash) == 64

    def test_transaction_to_dict_with_signature(self):
        """서명된 트랜잭션 딕셔너리 변환"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 100)
        tx.sign(wallet)

        tx_dict = tx.to_dict()

        assert 'signature' in tx_dict
        assert 'sender_public_key' in tx_dict


class TestWalletIntegration:
    """지갑 통합 테스트"""

    def test_full_transaction_flow(self):
        """전체 트랜잭션 흐름"""
        # 1. 두 지갑 생성
        alice = Wallet()
        bob = Wallet()

        # 2. Alice가 Bob에게 송금 트랜잭션 생성
        tx = Transaction(alice.address, bob.address, 50)

        # 3. Alice가 트랜잭션에 서명
        tx.sign(alice)

        # 4. 트랜잭션 유효성 검증
        assert tx.is_valid() is True
        assert tx.verify_signature() is True

        # 5. 트랜잭션 데이터 확인
        tx_dict = tx.to_dict()
        assert tx_dict['sender'] == alice.address
        assert tx_dict['recipient'] == bob.address
        assert tx_dict['amount'] == 50

    def test_multiple_transactions_different_signatures(self):
        """여러 트랜잭션은 서로 다른 서명"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "recipient1", 10)
        tx2 = Transaction(wallet.address, "recipient2", 20)

        tx1.sign(wallet)
        tx2.sign(wallet)

        # 서명은 서로 달라야 함
        assert tx1.signature != tx2.signature
