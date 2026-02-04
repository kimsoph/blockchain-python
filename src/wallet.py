# -*- coding: utf-8 -*-
"""
지갑 클래스 모듈

암호화폐 지갑 기능을 제공합니다.
개인키/공개키 관리, 트랜잭션 서명 기능을 포함합니다.
"""

import json
from typing import Dict, Any, Optional, Tuple
from .crypto_utils import (
    generate_private_key,
    private_key_to_public_key,
    public_key_to_address,
    sign_message,
    verify_signature,
    int_to_hex,
    hex_to_int
)


class Wallet:
    """
    암호화폐 지갑 클래스

    ECDSA 키 쌍을 관리하고 트랜잭션에 서명하는 기능을 제공합니다.

    Attributes:
        private_key: 개인키 (정수)
        public_key: 공개키 (x, y 튜플)
        address: 지갑 주소 (공개키 해시)
    """

    def __init__(self, private_key: Optional[int] = None):
        """
        지갑 초기화

        Args:
            private_key: 기존 개인키 (없으면 새로 생성)
        """
        if private_key is None:
            self._private_key = generate_private_key()
        else:
            self._private_key = private_key

        self._public_key = private_key_to_public_key(self._private_key)
        self._address = public_key_to_address(self._public_key)

    @property
    def private_key(self) -> int:
        """개인키 반환 (주의: 보안상 민감한 정보)"""
        return self._private_key

    @property
    def private_key_hex(self) -> str:
        """개인키를 16진수 문자열로 반환"""
        return int_to_hex(self._private_key)

    @property
    def public_key(self) -> Tuple[int, int]:
        """공개키 반환"""
        return self._public_key

    @property
    def public_key_hex(self) -> str:
        """공개키를 16진수 문자열로 반환"""
        x_hex = int_to_hex(self._public_key[0])
        y_hex = int_to_hex(self._public_key[1])
        return x_hex + y_hex

    @property
    def address(self) -> str:
        """지갑 주소 반환"""
        return self._address

    def sign(self, message: str) -> Tuple[int, int]:
        """
        메시지에 서명

        Args:
            message: 서명할 메시지

        Returns:
            (r, s) 서명 튜플
        """
        return sign_message(self._private_key, message)

    def sign_hex(self, message: str) -> str:
        """
        메시지에 서명하고 16진수 문자열로 반환

        Args:
            message: 서명할 메시지

        Returns:
            서명의 16진수 문자열 (r + s)
        """
        r, s = self.sign(message)
        return int_to_hex(r) + int_to_hex(s)

    @staticmethod
    def verify(public_key: Tuple[int, int], message: str, signature: Tuple[int, int]) -> bool:
        """
        서명 검증

        Args:
            public_key: 공개키
            message: 원본 메시지
            signature: (r, s) 서명

        Returns:
            유효하면 True
        """
        return verify_signature(public_key, message, signature)

    @staticmethod
    def verify_hex(public_key_hex: str, message: str, signature_hex: str) -> bool:
        """
        16진수 형식의 서명 검증

        Args:
            public_key_hex: 공개키 16진수 문자열
            message: 원본 메시지
            signature_hex: 서명 16진수 문자열

        Returns:
            유효하면 True
        """
        # 공개키 파싱
        x = hex_to_int(public_key_hex[:64])
        y = hex_to_int(public_key_hex[64:])
        public_key = (x, y)

        # 서명 파싱
        r = hex_to_int(signature_hex[:64])
        s = hex_to_int(signature_hex[64:])
        signature = (r, s)

        return verify_signature(public_key, message, signature)

    def to_dict(self) -> Dict[str, Any]:
        """
        지갑 정보를 딕셔너리로 변환 (개인키 포함 - 주의!)

        Returns:
            지갑 정보 딕셔너리
        """
        return {
            'private_key': self.private_key_hex,
            'public_key': self.public_key_hex,
            'address': self.address
        }

    def to_public_dict(self) -> Dict[str, str]:
        """
        공개 정보만 딕셔너리로 변환 (개인키 제외)

        Returns:
            공개 정보 딕셔너리
        """
        return {
            'public_key': self.public_key_hex,
            'address': self.address
        }

    def export_private_key(self) -> str:
        """
        개인키를 JSON 형식으로 내보내기

        Returns:
            개인키 JSON 문자열
        """
        return json.dumps({
            'private_key': self.private_key_hex
        }, ensure_ascii=False)

    @classmethod
    def from_private_key_hex(cls, private_key_hex: str) -> 'Wallet':
        """
        16진수 개인키로부터 지갑 복원

        Args:
            private_key_hex: 개인키 16진수 문자열

        Returns:
            복원된 지갑
        """
        private_key = hex_to_int(private_key_hex)
        return cls(private_key)

    @classmethod
    def from_json(cls, json_str: str) -> 'Wallet':
        """
        JSON에서 지갑 복원

        Args:
            json_str: 개인키가 포함된 JSON 문자열

        Returns:
            복원된 지갑
        """
        data = json.loads(json_str)
        return cls.from_private_key_hex(data['private_key'])

    def __str__(self) -> str:
        return (
            f"Wallet:\n"
            f"  Address: {self.address}\n"
            f"  Public Key: {self.public_key_hex[:16]}..."
        )

    def __repr__(self) -> str:
        return f"Wallet(address={self.address[:16]}...)"
