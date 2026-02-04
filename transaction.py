# -*- coding: utf-8 -*-
"""
트랜잭션 클래스 모듈

블록체인에서 거래를 나타내는 트랜잭션을 정의합니다.
각 트랜잭션은 발신자, 수신자, 금액 정보를 포함합니다.
"""

from datetime import datetime
from typing import Any, Dict


class Transaction:
    """
    블록체인의 트랜잭션(거래)을 나타내는 클래스

    Attributes:
        sender: 보내는 사람의 주소
        recipient: 받는 사람의 주소
        amount: 거래 금액
        timestamp: 트랜잭션 생성 시간
    """

    def __init__(self, sender: str, recipient: str, amount: float):
        """
        새 트랜잭션을 생성합니다.

        Args:
            sender: 보내는 주소 (시스템 보상의 경우 "SYSTEM")
            recipient: 받는 주소
            amount: 전송할 금액
        """
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        트랜잭션을 딕셔너리로 변환합니다.

        Returns:
            트랜잭션의 모든 속성을 담은 딕셔너리
        """
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp
        }

    def is_valid(self) -> bool:
        """
        트랜잭션의 유효성을 검사합니다.

        Returns:
            유효한 트랜잭션이면 True
        """
        # 기본 유효성 검사
        if not self.sender or not self.recipient:
            return False
        if self.amount <= 0:
            return False
        # 자기 자신에게 보내는 것 금지 (시스템 보상 제외)
        if self.sender != "SYSTEM" and self.sender == self.recipient:
            return False
        return True

    def __str__(self) -> str:
        """트랜잭션의 문자열 표현을 반환합니다."""
        return (
            f"Transaction:\n"
            f"  From: {self.sender}\n"
            f"  To: {self.recipient}\n"
            f"  Amount: {self.amount}\n"
            f"  Time: {self.timestamp}"
        )

    def __repr__(self) -> str:
        return f"Transaction({self.sender} -> {self.recipient}: {self.amount})"
