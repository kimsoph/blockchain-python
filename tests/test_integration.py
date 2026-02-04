# -*- coding: utf-8 -*-
"""
통합 테스트

전체 워크플로우 및 시나리오 기반 테스트입니다.
"""

import pytest
from src.blockchain import Blockchain
from src.transaction import Transaction
from src.block import Block


class TestFullWorkflow:
    """전체 워크플로우 테스트"""

    def test_complete_workflow(self, capsys):
        """전체 워크플로우 시뮬레이션"""
        # 1. 블록체인 생성 (난이도 2로 빠른 테스트)
        bc = Blockchain(difficulty=2)
        capsys.readouterr()

        assert len(bc) == 1  # 제네시스 블록

        # 2. 트랜잭션 생성 및 추가
        tx1 = Transaction("SYSTEM", "Alice", 100)
        tx2 = Transaction("Alice", "Bob", 30)
        tx3 = Transaction("Bob", "Charlie", 10)

        bc.add_transaction(tx1)
        bc.add_transaction(tx2)
        bc.add_transaction(tx3)

        assert len(bc.pending_transactions) == 3

        # 3. 채굴
        block = bc.mine_pending_transactions("Miner")
        capsys.readouterr()

        assert block is not None
        assert len(bc) == 2
        assert len(bc.pending_transactions) == 1  # 채굴 보상만 남음

        # 4. 채굴 보상 트랜잭션 처리
        bc.add_transaction(Transaction("Charlie", "Alice", 5))
        bc.mine_pending_transactions("Miner")
        capsys.readouterr()

        assert len(bc) == 3

        # 5. 잔액 확인
        assert bc.get_balance("Alice") == 70 + 5  # 100-30+5 = 75
        assert bc.get_balance("Bob") == 20  # 30-10
        assert bc.get_balance("Charlie") == 5  # 10-5
        assert bc.get_balance("Miner") == 100  # 채굴 보상 1회분

        # 6. 체인 유효성 검증
        capsys.readouterr()
        assert bc.is_chain_valid() is True


class TestMultipleTransactions:
    """다중 트랜잭션 테스트"""

    def test_many_transactions_in_one_block(self, capsys):
        """하나의 블록에 많은 트랜잭션"""
        bc = Blockchain(difficulty=2)
        capsys.readouterr()

        # 10개의 트랜잭션 추가
        for i in range(10):
            bc.add_transaction(Transaction(f"User{i}", f"User{i+1}", 10))

        assert len(bc.pending_transactions) == 10

        bc.mine_pending_transactions("Miner")
        capsys.readouterr()

        # 모든 트랜잭션이 블록에 포함됨
        assert len(bc.chain[1].data) == 10

    def test_transactions_across_multiple_blocks(self, capsys):
        """여러 블록에 걸친 트랜잭션"""
        bc = Blockchain(difficulty=2)
        capsys.readouterr()

        # 블록 1
        bc.add_transaction(Transaction("SYSTEM", "Alice", 100))
        bc.mine_pending_transactions("Miner")

        # 블록 2
        bc.add_transaction(Transaction("Alice", "Bob", 50))
        bc.mine_pending_transactions("Miner")

        # 블록 3
        bc.add_transaction(Transaction("Bob", "Charlie", 25))
        bc.mine_pending_transactions("Miner")

        capsys.readouterr()

        assert len(bc) == 4  # Genesis + 3 블록
        assert bc.is_chain_valid() is True


class TestBalanceCalculation:
    """잔액 계산 테스트"""

    def test_balance_after_complex_transactions(self, capsys):
        """복잡한 거래 후 잔액 확인"""
        bc = Blockchain(difficulty=2)
        capsys.readouterr()

        # 초기 자금 분배
        bc.add_transaction(Transaction("SYSTEM", "Alice", 1000))
        bc.add_transaction(Transaction("SYSTEM", "Bob", 500))
        bc.mine_pending_transactions("Miner")

        # 거래
        bc.add_transaction(Transaction("Alice", "Bob", 200))
        bc.add_transaction(Transaction("Bob", "Alice", 100))
        bc.add_transaction(Transaction("Alice", "Charlie", 150))
        bc.mine_pending_transactions("Miner")

        # 보상 채굴
        bc.mine_pending_transactions("Miner")
        capsys.readouterr()

        # Alice: 1000 - 200 + 100 - 150 = 750
        # Bob: 500 + 200 - 100 = 600
        # Charlie: 150
        assert bc.get_balance("Alice") == 750
        assert bc.get_balance("Bob") == 600
        assert bc.get_balance("Charlie") == 150

    def test_balance_with_mining_rewards(self, capsys):
        """채굴 보상 포함 잔액 확인"""
        bc = Blockchain(difficulty=2)
        bc.mining_reward = 50
        capsys.readouterr()

        # 3번 채굴
        for _ in range(3):
            bc.add_transaction(Transaction("SYSTEM", "User", 10))
            bc.mine_pending_transactions("Miner")

        # 마지막 보상 채굴
        bc.mine_pending_transactions("Miner")
        capsys.readouterr()

        # Miner는 3번 채굴 보상 = 50 * 3 = 150
        assert bc.get_balance("Miner") == 150


class TestTamperingDetection:
    """변조 감지 테스트"""

    def test_detect_data_tampering(self, capsys):
        """데이터 변조 감지"""
        bc = Blockchain(difficulty=2)
        bc.add_transaction(Transaction("SYSTEM", "Alice", 100))
        bc.mine_pending_transactions("Miner")
        capsys.readouterr()

        assert bc.is_chain_valid() is True

        # 트랜잭션 금액 변조 시도
        bc.chain[1].data[0]['amount'] = 10000  # 100 -> 10000

        capsys.readouterr()
        assert bc.is_chain_valid() is False

    def test_detect_block_insertion(self, capsys):
        """블록 삽입 변조 감지"""
        bc = Blockchain(difficulty=2)
        bc.add_block("블록 1")
        bc.add_block("블록 2")
        capsys.readouterr()

        # 중간에 블록 삽입 시도 (링크 깨짐)
        fake_block = Block(1, "위조 블록", bc.chain[0].hash)
        fake_block.mine_block(2)
        bc.chain.insert(1, fake_block)

        capsys.readouterr()
        assert bc.is_chain_valid() is False

    def test_detect_genesis_tampering(self, capsys):
        """제네시스 블록 변조 감지"""
        bc = Blockchain(difficulty=2)
        bc.add_block("블록 1")
        capsys.readouterr()

        # 제네시스 블록 데이터 변조 후 해시 재계산
        # (공격자가 변조 후 해시를 다시 계산한 시나리오)
        bc.chain[0].data = "변조된 제네시스"
        bc.chain[0].hash = bc.chain[0].calculate_hash()

        # 블록 1의 previous_hash가 변조된 제네시스 해시와 불일치
        capsys.readouterr()
        assert bc.is_chain_valid() is False


class TestEdgeCases:
    """경계 조건 테스트"""

    def test_zero_difficulty(self, capsys):
        """난이도 0 테스트"""
        bc = Blockchain(difficulty=0)
        capsys.readouterr()

        # 난이도 0은 모든 해시가 조건을 만족
        bc.add_block("테스트")
        assert len(bc) == 2
        assert bc.is_chain_valid() is True

    def test_high_difficulty(self, capsys):
        """높은 난이도 테스트 (1로 제한)"""
        # 실제로 높은 난이도는 시간이 오래 걸리므로 1로 테스트
        bc = Blockchain(difficulty=1)
        capsys.readouterr()

        bc.add_block("테스트")
        assert bc.chain[-1].hash.startswith("0")

    def test_unicode_in_transactions(self, capsys):
        """유니코드 트랜잭션 테스트"""
        bc = Blockchain(difficulty=2)
        capsys.readouterr()

        # 한글, 이모지 등 포함
        bc.add_transaction(Transaction("김철수", "이영희", 100))
        bc.add_transaction(Transaction("User_テスト", "用户", 50))
        bc.mine_pending_transactions("채굴자")

        capsys.readouterr()
        assert bc.is_chain_valid() is True
        assert bc.get_balance("이영희") == 100
        assert bc.get_balance("用户") == 50

    def test_large_amount_transaction(self, capsys):
        """큰 금액 트랜잭션"""
        bc = Blockchain(difficulty=2)
        capsys.readouterr()

        large_amount = 999999999999.99
        bc.add_transaction(Transaction("SYSTEM", "Rich", large_amount))
        bc.mine_pending_transactions("Miner")
        bc.mine_pending_transactions("Miner")

        capsys.readouterr()
        assert bc.get_balance("Rich") == large_amount

    def test_small_amount_transaction(self, capsys):
        """작은 금액 트랜잭션"""
        bc = Blockchain(difficulty=2)
        capsys.readouterr()

        small_amount = 0.00001
        bc.add_transaction(Transaction("SYSTEM", "User", small_amount))
        bc.mine_pending_transactions("Miner")
        bc.mine_pending_transactions("Miner")

        capsys.readouterr()
        assert bc.get_balance("User") == small_amount
