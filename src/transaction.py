# -*- coding: utf-8 -*-
"""
트랜잭션 클래스 모듈

블록체인에서 거래를 나타내는 트랜잭션을 정의합니다.
각 트랜잭션은 발신자, 수신자, 금액 정보를 포함합니다.
ECDSA 서명을 통한 트랜잭션 인증을 지원합니다.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .wallet import Wallet


class Transaction:
    """
    블록체인의 트랜잭션(거래)을 나타내는 클래스

    Attributes:
        sender: 보내는 사람의 주소
        recipient: 받는 사람의 주소
        amount: 거래 금액
        timestamp: 트랜잭션 생성 시간
        signature: ECDSA 서명 (선택적)
        sender_public_key: 발신자 공개키 (선택적)
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
        self.signature: Optional[str] = None
        self.sender_public_key: Optional[str] = None

    def get_hash(self) -> str:
        """
        트랜잭션 해시 계산 (서명 대상)

        Returns:
            트랜잭션 해시 문자열
        """
        tx_data = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp
        }
        tx_string = json.dumps(tx_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(tx_string.encode('utf-8')).hexdigest()

    def sign(self, wallet: 'Wallet') -> None:
        """
        지갑으로 트랜잭션에 서명

        Args:
            wallet: 서명에 사용할 지갑

        Raises:
            ValueError: 지갑 주소와 발신자가 일치하지 않을 때
        """
        if wallet.address != self.sender:
            raise ValueError("지갑 주소와 트랜잭션 발신자가 일치하지 않습니다.")

        tx_hash = self.get_hash()
        self.signature = wallet.sign_hex(tx_hash)
        self.sender_public_key = wallet.public_key_hex

    def verify_signature(self) -> bool:
        """
        트랜잭션 서명 검증

        Returns:
            서명이 유효하면 True
        """
        # 시스템 트랜잭션은 서명 불필요
        if self.sender == "SYSTEM":
            return True

        # 서명이 없으면 무효
        if not self.signature or not self.sender_public_key:
            return False

        # 지연 임포트로 순환 참조 방지
        from .wallet import Wallet

        tx_hash = self.get_hash()
        return Wallet.verify_hex(self.sender_public_key, tx_hash, self.signature)

    def to_dict(self) -> Dict[str, Any]:
        """
        트랜잭션을 딕셔너리로 변환합니다.

        Returns:
            트랜잭션의 모든 속성을 담은 딕셔너리
        """
        result = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp
        }
        if self.signature:
            result['signature'] = self.signature
        if self.sender_public_key:
            result['sender_public_key'] = self.sender_public_key
        return result

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
