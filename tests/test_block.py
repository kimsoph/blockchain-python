# -*- coding: utf-8 -*-
"""
Block 클래스 테스트

블록 생성, 해시 계산, 채굴 기능을 테스트합니다.
"""

import pytest
from src.block import Block


class TestBlockCreation:
    """블록 생성 관련 테스트"""

    def test_block_creation(self, sample_block):
        """블록 생성 확인"""
        assert sample_block.index == 1
        assert sample_block.data == "테스트 데이터"
        assert sample_block.previous_hash == "0" * 64
        assert sample_block.nonce == 0
        assert sample_block.hash is not None
        assert sample_block.timestamp is not None

    def test_block_creation_with_various_data(self):
        """다양한 데이터 타입으로 블록 생성"""
        # 문자열 데이터
        block1 = Block(0, "문자열 데이터", "0")
        assert block1.data == "문자열 데이터"

        # 리스트 데이터
        block2 = Block(1, [{"tx": "data"}], block1.hash)
        assert block2.data == [{"tx": "data"}]

        # 딕셔너리 데이터
        block3 = Block(2, {"key": "value", "한글": "테스트"}, block2.hash)
        assert block3.data == {"key": "value", "한글": "테스트"}


class TestHashCalculation:
    """해시 계산 관련 테스트"""

    def test_calculate_hash(self, sample_block):
        """해시 계산 검증"""
        original_hash = sample_block.hash
        recalculated_hash = sample_block.calculate_hash()
        assert original_hash == recalculated_hash

    def test_hash_is_64_characters(self, sample_block):
        """SHA-256 해시는 64자리 16진수"""
        assert len(sample_block.hash) == 64
        assert all(c in '0123456789abcdef' for c in sample_block.hash)

    def test_hash_changes_with_data(self):
        """데이터 변경 시 해시 변경 확인"""
        block1 = Block(0, "데이터1", "0")
        block2 = Block(0, "데이터2", "0")

        # 데이터가 다르면 해시도 달라야 함
        # (timestamp가 다를 수 있으므로 같은 timestamp로 테스트)
        block1.timestamp = "2025-01-01T00:00:00"
        block2.timestamp = "2025-01-01T00:00:00"
        block1.hash = block1.calculate_hash()
        block2.hash = block2.calculate_hash()

        assert block1.hash != block2.hash

    def test_hash_changes_with_nonce(self, sample_block):
        """nonce 변경 시 해시 변경 확인"""
        original_hash = sample_block.calculate_hash()
        sample_block.nonce = 1
        new_hash = sample_block.calculate_hash()
        assert original_hash != new_hash

    def test_hash_deterministic(self, sample_block):
        """동일한 데이터는 항상 같은 해시 생성"""
        hash1 = sample_block.calculate_hash()
        hash2 = sample_block.calculate_hash()
        hash3 = sample_block.calculate_hash()
        assert hash1 == hash2 == hash3


class TestMining:
    """채굴 관련 테스트"""

    def test_mine_block_difficulty_1(self, capsys):
        """난이도 1 채굴 테스트"""
        block = Block(0, "테스트", "0")
        block.mine_block(1)

        assert block.hash.startswith("0")
        assert block.nonce >= 0

    def test_mine_block_difficulty_2(self, capsys):
        """난이도 2 채굴 테스트"""
        block = Block(0, "테스트", "0")
        block.mine_block(2)

        assert block.hash.startswith("00")

    def test_mine_block_difficulty_3(self, capsys):
        """난이도 3 채굴 테스트"""
        block = Block(0, "테스트", "0")
        block.mine_block(3)

        assert block.hash.startswith("000")

    def test_mine_block_output(self, capsys):
        """채굴 완료 메시지 출력 확인"""
        block = Block(0, "테스트", "0")
        block.mine_block(1)

        captured = capsys.readouterr()
        assert "채굴 완료" in captured.out
        assert "Nonce" in captured.out
        assert "Hash" in captured.out


class TestSerialization:
    """직렬화 관련 테스트"""

    def test_to_dict(self, sample_block):
        """딕셔너리 변환 검증"""
        block_dict = sample_block.to_dict()

        assert block_dict['index'] == sample_block.index
        assert block_dict['timestamp'] == sample_block.timestamp
        assert block_dict['data'] == sample_block.data
        assert block_dict['previous_hash'] == sample_block.previous_hash
        assert block_dict['nonce'] == sample_block.nonce
        assert block_dict['hash'] == sample_block.hash

    def test_to_dict_keys(self, sample_block):
        """딕셔너리 키 확인"""
        block_dict = sample_block.to_dict()
        expected_keys = {'index', 'timestamp', 'data', 'previous_hash', 'nonce', 'hash'}
        assert set(block_dict.keys()) == expected_keys


class TestStringRepresentation:
    """문자열 표현 테스트"""

    def test_block_str(self, sample_block):
        """__str__ 메서드 테스트"""
        str_repr = str(sample_block)

        assert f"Block #{sample_block.index}" in str_repr
        assert "Timestamp" in str_repr
        assert "Data" in str_repr
        assert "Previous Hash" in str_repr
        assert "Nonce" in str_repr
        assert "Hash" in str_repr

    def test_block_repr(self, sample_block):
        """__repr__ 메서드 테스트"""
        repr_str = repr(sample_block)

        assert "Block(" in repr_str
        assert f"index={sample_block.index}" in repr_str
        assert "hash=" in repr_str
