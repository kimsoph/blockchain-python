# -*- coding: utf-8 -*-
"""
Blockchain 클래스 테스트

블록체인 관리, 트랜잭션 처리, 채굴, 검증 기능을 테스트합니다.
"""

import pytest
from src.blockchain import Blockchain
from src.transaction import Transaction
from src.block import Block


class TestBlockchainCreation:
    """블록체인 생성 관련 테스트"""

    def test_genesis_block(self, blockchain):
        """제네시스 블록 자동 생성 확인"""
        assert len(blockchain.chain) == 1
        assert blockchain.chain[0].index == 0
        assert blockchain.chain[0].previous_hash == "0"
        assert "Genesis" in blockchain.chain[0].data or "제네시스" in str(blockchain.chain[0].data)

    def test_default_difficulty(self, capsys):
        """기본 난이도 확인"""
        bc = Blockchain()
        assert bc.difficulty == 4

    def test_custom_difficulty(self, capsys):
        """사용자 정의 난이도"""
        bc = Blockchain(difficulty=3)
        assert bc.difficulty == 3

    def test_initial_pending_transactions(self, blockchain):
        """초기 펜딩 트랜잭션 비어있음"""
        assert len(blockchain.pending_transactions) == 0

    def test_mining_reward(self, blockchain):
        """채굴 보상 기본값"""
        assert blockchain.mining_reward == 100


class TestBlockOperations:
    """블록 작업 관련 테스트"""

    def test_add_block(self, blockchain, capsys):
        """블록 추가 테스트"""
        initial_length = len(blockchain.chain)
        blockchain.add_block("테스트 블록 데이터")

        assert len(blockchain.chain) == initial_length + 1
        assert blockchain.chain[-1].data == "테스트 블록 데이터"

    def test_get_latest_block(self, blockchain, capsys):
        """최신 블록 조회"""
        genesis = blockchain.get_latest_block()
        assert genesis.index == 0

        blockchain.add_block("새 블록")
        latest = blockchain.get_latest_block()
        assert latest.index == 1

    def test_block_chain_linking(self, blockchain, capsys):
        """블록 체인 연결 확인"""
        blockchain.add_block("블록 1")
        blockchain.add_block("블록 2")

        assert blockchain.chain[1].previous_hash == blockchain.chain[0].hash
        assert blockchain.chain[2].previous_hash == blockchain.chain[1].hash


class TestTransactionOperations:
    """트랜잭션 작업 관련 테스트"""

    def test_add_transaction(self, blockchain):
        """트랜잭션 추가"""
        tx = Transaction("Alice", "Bob", 50)
        next_block_index = blockchain.add_transaction(tx)

        assert len(blockchain.pending_transactions) == 1
        assert next_block_index == 1  # 제네시스 블록 다음

    def test_add_multiple_transactions(self, blockchain):
        """여러 트랜잭션 추가"""
        tx1 = Transaction("Alice", "Bob", 50)
        tx2 = Transaction("Bob", "Charlie", 30)
        tx3 = Transaction("Charlie", "Alice", 20)

        blockchain.add_transaction(tx1)
        blockchain.add_transaction(tx2)
        blockchain.add_transaction(tx3)

        assert len(blockchain.pending_transactions) == 3

    def test_add_transaction_no_sender(self, blockchain):
        """발신자 없는 트랜잭션 거부"""
        tx = Transaction("", "Bob", 50)
        with pytest.raises(ValueError, match="발신자"):
            blockchain.add_transaction(tx)

    def test_add_transaction_no_recipient(self, blockchain):
        """수신자 없는 트랜잭션 거부"""
        tx = Transaction("Alice", "", 50)
        with pytest.raises(ValueError, match="수신자"):
            blockchain.add_transaction(tx)

    def test_add_transaction_zero_amount(self, blockchain):
        """금액 0 트랜잭션 거부"""
        tx = Transaction("Alice", "Bob", 0)
        with pytest.raises(ValueError, match="금액"):
            blockchain.add_transaction(tx)

    def test_add_transaction_negative_amount(self, blockchain):
        """음수 금액 트랜잭션 거부"""
        tx = Transaction("Alice", "Bob", -10)
        with pytest.raises(ValueError, match="금액"):
            blockchain.add_transaction(tx)


class TestMining:
    """채굴 관련 테스트"""

    def test_mine_pending_transactions(self, blockchain, capsys):
        """펜딩 트랜잭션 채굴"""
        tx = Transaction("SYSTEM", "Alice", 100)
        blockchain.add_transaction(tx)

        initial_length = len(blockchain.chain)
        block = blockchain.mine_pending_transactions("Miner")

        assert block is not None
        assert len(blockchain.chain) == initial_length + 1
        # 채굴 후 펜딩에는 보상 트랜잭션만 남음
        assert len(blockchain.pending_transactions) == 1
        assert blockchain.pending_transactions[0].recipient == "Miner"

    def test_mine_no_transactions(self, blockchain, capsys):
        """펜딩 트랜잭션 없을 때"""
        block = blockchain.mine_pending_transactions("Miner")

        assert block is None
        captured = capsys.readouterr()
        assert "트랜잭션이 없습니다" in captured.out

    def test_mining_reward(self, blockchain, capsys):
        """채굴 보상 확인"""
        tx = Transaction("SYSTEM", "Alice", 50)
        blockchain.add_transaction(tx)
        blockchain.mine_pending_transactions("Miner")

        # 보상 트랜잭션이 펜딩에 추가됨
        reward_tx = blockchain.pending_transactions[0]
        assert reward_tx.sender == "SYSTEM"
        assert reward_tx.recipient == "Miner"
        assert reward_tx.amount == blockchain.mining_reward

    def test_mining_reward_in_next_block(self, blockchain, capsys):
        """채굴 보상이 다음 블록에 포함되는지 확인"""
        # 첫 번째 채굴
        tx1 = Transaction("SYSTEM", "Alice", 100)
        blockchain.add_transaction(tx1)
        blockchain.mine_pending_transactions("Miner1")

        # 두 번째 채굴 (첫 번째 보상이 포함됨)
        tx2 = Transaction("Alice", "Bob", 50)
        blockchain.add_transaction(tx2)
        blockchain.mine_pending_transactions("Miner2")

        # Miner1의 보상이 블록에 기록됨
        balance = blockchain.get_balance("Miner1")
        assert balance == blockchain.mining_reward


class TestBalance:
    """잔액 조회 관련 테스트"""

    def test_get_balance_no_transactions(self, blockchain):
        """거래 없는 주소 잔액"""
        balance = blockchain.get_balance("Unknown")
        assert balance == 0.0

    def test_get_balance_after_receiving(self, blockchain_with_blocks):
        """수신 후 잔액"""
        # fixture에서 SYSTEM -> Alice 100, Alice -> Bob 30
        # 다음 채굴로 잔액 반영
        blockchain_with_blocks.mine_pending_transactions("Miner")

        alice_balance = blockchain_with_blocks.get_balance("Alice")
        bob_balance = blockchain_with_blocks.get_balance("Bob")

        assert alice_balance == 100 - 30  # 70
        assert bob_balance == 30

    def test_get_balance_multiple_transactions(self, blockchain, capsys):
        """다중 거래 후 잔액"""
        # 트랜잭션 추가
        blockchain.add_transaction(Transaction("SYSTEM", "Alice", 100))
        blockchain.add_transaction(Transaction("Alice", "Bob", 30))
        blockchain.add_transaction(Transaction("Bob", "Charlie", 10))
        blockchain.mine_pending_transactions("Miner")

        # 보상 트랜잭션 채굴
        blockchain.mine_pending_transactions("Miner")

        assert blockchain.get_balance("Alice") == 70
        assert blockchain.get_balance("Bob") == 20
        assert blockchain.get_balance("Charlie") == 10


class TestChainValidation:
    """체인 검증 관련 테스트"""

    def test_is_chain_valid(self, blockchain, capsys):
        """체인 유효성 검증"""
        blockchain.add_block("블록 1")
        blockchain.add_block("블록 2")

        capsys.readouterr()  # 이전 출력 무시
        assert blockchain.is_chain_valid() is True

    def test_chain_invalid_after_data_tampering(self, blockchain, capsys):
        """데이터 변조 후 무효화 확인"""
        blockchain.add_block("원본 데이터")

        # 데이터 변조
        blockchain.chain[1].data = "변조된 데이터"

        capsys.readouterr()  # 이전 출력 무시
        assert blockchain.is_chain_valid() is False

    def test_chain_invalid_after_hash_tampering(self, blockchain, capsys):
        """해시 변조 후 무효화 확인"""
        blockchain.add_block("데이터")
        blockchain.add_block("데이터2")

        # 해시 직접 변조 (다음 블록의 previous_hash와 불일치)
        blockchain.chain[1].hash = "0" * 64

        capsys.readouterr()
        assert blockchain.is_chain_valid() is False


class TestSpecialMethods:
    """특수 메서드 테스트"""

    def test_len(self, blockchain, capsys):
        """__len__ 테스트"""
        assert len(blockchain) == 1

        blockchain.add_block("1")
        assert len(blockchain) == 2

        blockchain.add_block("2")
        assert len(blockchain) == 3

    def test_getitem(self, blockchain, capsys):
        """__getitem__ 테스트"""
        blockchain.add_block("블록 1")
        blockchain.add_block("블록 2")

        assert blockchain[0].index == 0
        assert blockchain[1].index == 1
        assert blockchain[2].index == 2
        assert blockchain[-1].index == 2

    def test_getitem_out_of_range(self, blockchain):
        """인덱스 범위 초과"""
        with pytest.raises(IndexError):
            _ = blockchain[100]
