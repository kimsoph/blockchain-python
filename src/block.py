# -*- coding: utf-8 -*-
"""
블록 클래스 모듈

블록체인의 기본 단위인 블록을 정의합니다.
각 블록은 index, timestamp, data, previous_hash, nonce, hash를 포함합니다.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict


class Block:
    """
    블록체인의 개별 블록을 나타내는 클래스

    Attributes:
        index: 블록 번호 (체인에서의 위치)
        timestamp: 블록 생성 시간
        data: 블록에 저장된 데이터 (트랜잭션 등)
        previous_hash: 이전 블록의 해시값
        nonce: 작업 증명(PoW)에 사용되는 숫자
        hash: 현재 블록의 해시값
    """

    def __init__(self, index: int, data: Any, previous_hash: str):
        """
        새 블록을 초기화합니다.

        Args:
            index: 블록 번호
            data: 저장할 데이터
            previous_hash: 이전 블록의 해시
        """
        self.index = index
        self.timestamp = datetime.now().isoformat()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """
        블록의 모든 데이터를 기반으로 SHA-256 해시를 계산합니다.

        블록의 내용이 조금이라도 변경되면 완전히 다른 해시가 생성됩니다.
        이것이 블록체인의 무결성을 보장하는 핵심 원리입니다.

        Returns:
            블록의 SHA-256 해시값 (16진수 문자열)
        """
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }
        # JSON으로 직렬화 (정렬하여 일관성 보장)
        block_string = json.dumps(block_data, sort_keys=True, ensure_ascii=False)
        # SHA-256 해시 계산
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()

    def mine_block(self, difficulty: int) -> None:
        """
        작업 증명(Proof of Work)을 수행하여 블록을 채굴합니다.

        난이도(difficulty)만큼의 0으로 시작하는 해시를 찾을 때까지
        nonce를 증가시키며 해시를 재계산합니다.

        Args:
            difficulty: 해시가 시작해야 하는 0의 개수
        """
        target = '0' * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        print(f"블록 #{self.index} 채굴 완료! Nonce: {self.nonce}, Hash: {self.hash}")

    def to_dict(self) -> Dict[str, Any]:
        """
        블록을 딕셔너리로 변환합니다.

        Returns:
            블록의 모든 속성을 담은 딕셔너리
        """
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash
        }

    def __str__(self) -> str:
        """블록의 문자열 표현을 반환합니다."""
        return (
            f"Block #{self.index}\n"
            f"  Timestamp: {self.timestamp}\n"
            f"  Data: {self.data}\n"
            f"  Previous Hash: {self.previous_hash[:16]}...\n"
            f"  Nonce: {self.nonce}\n"
            f"  Hash: {self.hash[:16]}..."
        )

    def __repr__(self) -> str:
        return f"Block(index={self.index}, hash={self.hash[:8]}...)"
