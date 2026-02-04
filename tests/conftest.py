# -*- coding: utf-8 -*-
"""
pytest fixtures 정의

테스트에서 공통으로 사용하는 객체들을 fixture로 제공합니다.
"""

import pytest
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.block import Block
from src.transaction import Transaction
from src.blockchain import Blockchain


@pytest.fixture
def sample_block():
    """테스트용 블록 생성"""
    return Block(
        index=1,
        data="테스트 데이터",
        previous_hash="0" * 64
    )


@pytest.fixture
def sample_transaction():
    """테스트용 트랜잭션 생성"""
    return Transaction(
        sender="Alice",
        recipient="Bob",
        amount=50.0
    )


@pytest.fixture
def system_transaction():
    """시스템 보상 트랜잭션 생성"""
    return Transaction(
        sender="SYSTEM",
        recipient="Miner",
        amount=100.0
    )


@pytest.fixture
def blockchain(capsys):
    """난이도 2의 블록체인 (빠른 테스트용)"""
    bc = Blockchain(difficulty=2)
    capsys.readouterr()  # 제네시스 블록 출력 무시
    return bc


@pytest.fixture
def blockchain_with_blocks(blockchain, capsys):
    """블록이 추가된 블록체인"""
    # 트랜잭션 추가 및 채굴
    tx1 = Transaction("SYSTEM", "Alice", 100)
    tx2 = Transaction("Alice", "Bob", 30)

    blockchain.add_transaction(tx1)
    blockchain.add_transaction(tx2)
    blockchain.mine_pending_transactions("Miner")

    capsys.readouterr()  # 출력 무시
    return blockchain
