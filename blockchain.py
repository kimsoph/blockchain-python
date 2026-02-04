# -*- coding: utf-8 -*-
"""
블록체인 클래스 모듈

블록들을 연결하여 체인을 구성하고 관리합니다.
제네시스 블록 생성, 블록 추가, 작업 증명, 체인 검증 기능을 제공합니다.
"""

from typing import Any, List, Optional
from block import Block
from transaction import Transaction


class Blockchain:
    """
    블록체인을 관리하는 클래스

    Attributes:
        chain: 블록들의 리스트 (블록체인)
        difficulty: 채굴 난이도 (해시 앞에 붙어야 하는 0의 개수)
        pending_transactions: 아직 블록에 포함되지 않은 대기 중인 트랜잭션들
        mining_reward: 채굴 보상
    """

    def __init__(self, difficulty: int = 4):
        """
        블록체인을 초기화하고 제네시스 블록을 생성합니다.

        Args:
            difficulty: 채굴 난이도 (기본값: 4)
        """
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_transactions: List[Transaction] = []
        self.mining_reward = 100  # 채굴 보상

        # 제네시스 블록 생성
        self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        """
        제네시스 블록(첫 번째 블록)을 생성합니다.

        제네시스 블록은 이전 블록이 없으므로 previous_hash가 "0"입니다.
        """
        genesis_block = Block(
            index=0,
            data="Genesis Block - 블록체인의 시작",
            previous_hash="0"
        )
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        print("제네시스 블록이 생성되었습니다!\n")

    def get_latest_block(self) -> Block:
        """
        체인의 마지막 블록을 반환합니다.

        Returns:
            가장 최근에 추가된 블록
        """
        return self.chain[-1]

    def add_block(self, data: Any) -> Block:
        """
        새 블록을 생성하고 체인에 추가합니다.

        Args:
            data: 블록에 저장할 데이터

        Returns:
            새로 추가된 블록
        """
        new_block = Block(
            index=len(self.chain),
            data=data,
            previous_hash=self.get_latest_block().hash
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        print(f"블록 #{new_block.index}이(가) 체인에 추가되었습니다!\n")
        return new_block

    def add_transaction(self, transaction: Transaction) -> int:
        """
        새 트랜잭션을 펜딩 목록에 추가합니다.

        Args:
            transaction: 추가할 트랜잭션

        Returns:
            트랜잭션이 포함될 블록의 인덱스
        """
        if not transaction.sender or not transaction.recipient:
            raise ValueError("트랜잭션에는 발신자와 수신자가 필요합니다.")

        if transaction.amount <= 0:
            raise ValueError("트랜잭션 금액은 0보다 커야 합니다.")

        self.pending_transactions.append(transaction)
        return self.get_latest_block().index + 1

    def mine_pending_transactions(self, mining_reward_address: str) -> Optional[Block]:
        """
        펜딩 중인 트랜잭션들을 블록으로 만들어 채굴합니다.

        Args:
            mining_reward_address: 채굴 보상을 받을 주소

        Returns:
            채굴된 블록 (펜딩 트랜잭션이 없으면 None)
        """
        if not self.pending_transactions:
            print("채굴할 트랜잭션이 없습니다.")
            return None

        # 트랜잭션 데이터를 딕셔너리 리스트로 변환
        transactions_data = [tx.to_dict() for tx in self.pending_transactions]

        # 새 블록 생성 및 채굴
        block = self.add_block(transactions_data)

        # 펜딩 트랜잭션 초기화 및 채굴 보상 추가
        self.pending_transactions = [
            Transaction(
                sender="SYSTEM",
                recipient=mining_reward_address,
                amount=self.mining_reward
            )
        ]

        print(f"채굴 보상 {self.mining_reward}이(가) {mining_reward_address}에게 지급됩니다.\n")
        return block

    def get_balance(self, address: str) -> float:
        """
        특정 주소의 잔액을 계산합니다.

        Args:
            address: 잔액을 확인할 주소

        Returns:
            해당 주소의 잔액
        """
        balance = 0.0

        for block in self.chain:
            # 제네시스 블록이나 일반 데이터 블록은 건너뛰기
            if not isinstance(block.data, list):
                continue

            for tx_data in block.data:
                if isinstance(tx_data, dict):
                    if tx_data.get('sender') == address:
                        balance -= tx_data.get('amount', 0)
                    if tx_data.get('recipient') == address:
                        balance += tx_data.get('amount', 0)

        return balance

    def is_chain_valid(self) -> bool:
        """
        전체 블록체인의 무결성을 검증합니다.

        검증 항목:
        1. 각 블록의 해시가 올바르게 계산되었는지
        2. 각 블록의 previous_hash가 이전 블록의 해시와 일치하는지
        3. 각 블록이 난이도 조건을 만족하는지 (해시가 0으로 시작)

        Returns:
            체인이 유효하면 True, 그렇지 않으면 False
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # 1. 현재 블록의 해시가 올바른지 확인
            if current_block.hash != current_block.calculate_hash():
                print(f"블록 #{i}의 해시가 유효하지 않습니다!")
                print(f"  저장된 해시: {current_block.hash}")
                print(f"  계산된 해시: {current_block.calculate_hash()}")
                return False

            # 2. 이전 블록과의 연결이 올바른지 확인
            if current_block.previous_hash != previous_block.hash:
                print(f"블록 #{i}의 previous_hash가 이전 블록의 해시와 일치하지 않습니다!")
                print(f"  previous_hash: {current_block.previous_hash}")
                print(f"  이전 블록 해시: {previous_block.hash}")
                return False

            # 3. 작업 증명 조건을 만족하는지 확인
            if current_block.hash[:self.difficulty] != '0' * self.difficulty:
                print(f"블록 #{i}이(가) 작업 증명 조건을 만족하지 않습니다!")
                return False

        print("블록체인이 유효합니다!")
        return True

    def print_chain(self) -> None:
        """전체 블록체인을 출력합니다."""
        print("\n" + "=" * 60)
        print("                    블록체인 전체 조회")
        print("=" * 60)

        for block in self.chain:
            print(f"\n{block}")
            print("-" * 40)

        print(f"\n총 블록 수: {len(self.chain)}")
        print(f"채굴 난이도: {self.difficulty}")
        print("=" * 60 + "\n")

    def __len__(self) -> int:
        """체인의 길이를 반환합니다."""
        return len(self.chain)

    def __getitem__(self, index: int) -> Block:
        """인덱스로 블록에 접근합니다."""
        return self.chain[index]
