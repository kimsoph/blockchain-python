# -*- coding: utf-8 -*-
"""
BlockchainStorage 클래스 테스트

SQLite 저장소 기능을 테스트합니다.
"""

import pytest
import os
import tempfile
from src.storage import BlockchainStorage


@pytest.fixture
def storage():
    """임시 DB 파일을 사용하는 저장소"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    store = BlockchainStorage(path)
    yield store

    store.close()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_block():
    """테스트용 블록 데이터"""
    return {
        'index': 0,
        'timestamp': '2025-01-01T00:00:00',
        'data': 'Genesis Block',
        'previous_hash': '0',
        'nonce': 12345,
        'hash': '0000abcd1234567890'
    }


@pytest.fixture
def sample_transaction():
    """테스트용 트랜잭션 데이터"""
    return {
        'sender': 'Alice',
        'recipient': 'Bob',
        'amount': 100.0,
        'timestamp': '2025-01-01T00:00:00'
    }


class TestBlockStorage:
    """블록 저장 테스트"""

    def test_save_block(self, storage, sample_block):
        """블록 저장"""
        block_id = storage.save_block(sample_block)
        assert block_id > 0

    def test_get_block(self, storage, sample_block):
        """블록 조회"""
        storage.save_block(sample_block)
        block = storage.get_block(0)

        assert block is not None
        assert block['index'] == sample_block['index']
        assert block['hash'] == sample_block['hash']

    def test_get_nonexistent_block(self, storage):
        """존재하지 않는 블록 조회"""
        block = storage.get_block(999)
        assert block is None

    def test_get_block_by_hash(self, storage, sample_block):
        """해시로 블록 조회"""
        storage.save_block(sample_block)
        block = storage.get_block_by_hash(sample_block['hash'])

        assert block is not None
        assert block['index'] == 0

    def test_get_all_blocks(self, storage):
        """모든 블록 조회"""
        blocks_data = [
            {'index': 0, 'timestamp': '2025-01-01T00:00:00', 'data': 'Block 0',
             'previous_hash': '0', 'nonce': 1, 'hash': 'hash0'},
            {'index': 1, 'timestamp': '2025-01-01T00:01:00', 'data': 'Block 1',
             'previous_hash': 'hash0', 'nonce': 2, 'hash': 'hash1'},
            {'index': 2, 'timestamp': '2025-01-01T00:02:00', 'data': 'Block 2',
             'previous_hash': 'hash1', 'nonce': 3, 'hash': 'hash2'},
        ]

        for block in blocks_data:
            storage.save_block(block)

        all_blocks = storage.get_all_blocks()
        assert len(all_blocks) == 3
        assert all_blocks[0]['index'] == 0
        assert all_blocks[2]['index'] == 2

    def test_get_latest_block(self, storage):
        """최신 블록 조회"""
        blocks_data = [
            {'index': 0, 'timestamp': '2025-01-01T00:00:00', 'data': 'Block 0',
             'previous_hash': '0', 'nonce': 1, 'hash': 'hash0'},
            {'index': 1, 'timestamp': '2025-01-01T00:01:00', 'data': 'Block 1',
             'previous_hash': 'hash0', 'nonce': 2, 'hash': 'hash1'},
        ]

        for block in blocks_data:
            storage.save_block(block)

        latest = storage.get_latest_block()
        assert latest['index'] == 1

    def test_get_block_count(self, storage, sample_block):
        """블록 수 조회"""
        assert storage.get_block_count() == 0

        storage.save_block(sample_block)
        assert storage.get_block_count() == 1

    def test_save_block_with_json_data(self, storage):
        """JSON 데이터 포함 블록 저장"""
        block = {
            'index': 1,
            'timestamp': '2025-01-01T00:00:00',
            'data': [
                {'sender': 'Alice', 'recipient': 'Bob', 'amount': 50},
                {'sender': 'Bob', 'recipient': 'Charlie', 'amount': 25}
            ],
            'previous_hash': 'prev_hash',
            'nonce': 100,
            'hash': 'block_hash'
        }

        storage.save_block(block)
        retrieved = storage.get_block(1)

        assert retrieved['data'] == block['data']
        assert len(retrieved['data']) == 2

    def test_save_block_with_korean_data(self, storage):
        """한글 데이터 포함 블록 저장"""
        block = {
            'index': 0,
            'timestamp': '2025-01-01T00:00:00',
            'data': '제네시스 블록 - 블록체인의 시작',
            'previous_hash': '0',
            'nonce': 1,
            'hash': 'hash_korean'
        }

        storage.save_block(block)
        retrieved = storage.get_block(0)

        assert '제네시스' in retrieved['data']


class TestTransactionStorage:
    """트랜잭션 저장 테스트"""

    def test_save_transaction(self, storage, sample_block, sample_transaction):
        """트랜잭션 저장"""
        storage.save_block(sample_block)
        tx_id = storage.save_transaction(sample_transaction, block_index=0)

        assert tx_id > 0

    def test_get_transactions_by_block(self, storage, sample_block):
        """블록별 트랜잭션 조회"""
        storage.save_block(sample_block)

        tx1 = {'sender': 'A', 'recipient': 'B', 'amount': 10, 'timestamp': '2025-01-01'}
        tx2 = {'sender': 'B', 'recipient': 'C', 'amount': 20, 'timestamp': '2025-01-01'}

        storage.save_transaction(tx1, block_index=0)
        storage.save_transaction(tx2, block_index=0)

        txs = storage.get_transactions_by_block(0)
        assert len(txs) == 2

    def test_get_transactions_by_address(self, storage, sample_block):
        """주소별 트랜잭션 조회"""
        storage.save_block(sample_block)

        txs_data = [
            {'sender': 'Alice', 'recipient': 'Bob', 'amount': 50, 'timestamp': '2025-01-01'},
            {'sender': 'Bob', 'recipient': 'Charlie', 'amount': 30, 'timestamp': '2025-01-02'},
            {'sender': 'Alice', 'recipient': 'Charlie', 'amount': 20, 'timestamp': '2025-01-03'},
        ]

        for tx in txs_data:
            storage.save_transaction(tx, block_index=0)

        alice_txs = storage.get_transactions_by_address('Alice')
        assert len(alice_txs) == 2  # 보낸 2건

        bob_txs = storage.get_transactions_by_address('Bob')
        assert len(bob_txs) == 2  # 받은 1건 + 보낸 1건

    def test_save_transaction_with_signature(self, storage, sample_block):
        """서명 포함 트랜잭션 저장"""
        storage.save_block(sample_block)

        tx = {
            'sender': 'Alice',
            'recipient': 'Bob',
            'amount': 100,
            'timestamp': '2025-01-01',
            'signature': 'sig_abc123',
            'sender_public_key': 'pub_key_xyz'
        }

        storage.save_transaction(tx, block_index=0)
        txs = storage.get_transactions_by_block(0)

        assert txs[0]['signature'] == 'sig_abc123'
        assert txs[0]['sender_public_key'] == 'pub_key_xyz'


class TestPendingTransactions:
    """펜딩 트랜잭션 테스트"""

    def test_save_pending_transaction(self, storage, sample_transaction):
        """펜딩 트랜잭션 저장"""
        tx_id = storage.save_transaction(sample_transaction)  # block_index 없음
        assert tx_id > 0

    def test_get_pending_transactions(self, storage):
        """펜딩 트랜잭션 조회"""
        tx1 = {'sender': 'A', 'recipient': 'B', 'amount': 10, 'timestamp': '2025-01-01'}
        tx2 = {'sender': 'C', 'recipient': 'D', 'amount': 20, 'timestamp': '2025-01-02'}

        storage.save_transaction(tx1)
        storage.save_transaction(tx2)

        pending = storage.get_pending_transactions()
        assert len(pending) == 2

    def test_clear_pending_transactions(self, storage):
        """펜딩 트랜잭션 삭제"""
        tx = {'sender': 'A', 'recipient': 'B', 'amount': 10, 'timestamp': '2025-01-01'}
        storage.save_transaction(tx)
        storage.save_transaction(tx)

        count = storage.clear_pending_transactions()
        assert count == 2

        pending = storage.get_pending_transactions()
        assert len(pending) == 0


class TestBalance:
    """잔액 계산 테스트"""

    def test_get_balance(self, storage, sample_block):
        """잔액 계산"""
        storage.save_block(sample_block)

        # SYSTEM -> Alice: 100
        storage.save_transaction(
            {'sender': 'SYSTEM', 'recipient': 'Alice', 'amount': 100, 'timestamp': '2025-01-01'},
            block_index=0
        )
        # Alice -> Bob: 30
        storage.save_transaction(
            {'sender': 'Alice', 'recipient': 'Bob', 'amount': 30, 'timestamp': '2025-01-02'},
            block_index=0
        )

        assert storage.get_balance('Alice') == 70  # 100 - 30
        assert storage.get_balance('Bob') == 30
        assert storage.get_balance('Unknown') == 0

    def test_balance_multiple_transactions(self, storage, sample_block):
        """다중 트랜잭션 잔액"""
        storage.save_block(sample_block)

        txs = [
            {'sender': 'SYSTEM', 'recipient': 'Alice', 'amount': 1000, 'timestamp': '1'},
            {'sender': 'Alice', 'recipient': 'Bob', 'amount': 200, 'timestamp': '2'},
            {'sender': 'Alice', 'recipient': 'Charlie', 'amount': 300, 'timestamp': '3'},
            {'sender': 'Bob', 'recipient': 'Alice', 'amount': 50, 'timestamp': '4'},
        ]

        for tx in txs:
            storage.save_transaction(tx, block_index=0)

        assert storage.get_balance('Alice') == 550  # 1000 - 200 - 300 + 50
        assert storage.get_balance('Bob') == 150  # 200 - 50
        assert storage.get_balance('Charlie') == 300


class TestMetadata:
    """메타데이터 테스트"""

    def test_set_and_get_metadata(self, storage):
        """메타데이터 저장/조회"""
        storage.set_metadata('difficulty', '4')
        storage.set_metadata('version', '1.0')

        assert storage.get_metadata('difficulty') == '4'
        assert storage.get_metadata('version') == '1.0'

    def test_get_nonexistent_metadata(self, storage):
        """존재하지 않는 메타데이터"""
        assert storage.get_metadata('nonexistent') is None

    def test_update_metadata(self, storage):
        """메타데이터 업데이트"""
        storage.set_metadata('key', 'value1')
        storage.set_metadata('key', 'value2')

        assert storage.get_metadata('key') == 'value2'


class TestClearAll:
    """전체 삭제 테스트"""

    def test_clear_all(self, storage, sample_block, sample_transaction):
        """모든 데이터 삭제"""
        storage.save_block(sample_block)
        storage.save_transaction(sample_transaction, block_index=0)
        storage.save_transaction(sample_transaction)  # pending
        storage.set_metadata('key', 'value')

        storage.clear_all()

        assert storage.get_block_count() == 0
        assert len(storage.get_pending_transactions()) == 0
        assert storage.get_metadata('key') is None


class TestStorageIntegration:
    """저장소 통합 테스트"""

    def test_full_blockchain_storage(self, storage):
        """전체 블록체인 저장 시나리오"""
        # 1. 제네시스 블록
        genesis = {
            'index': 0,
            'timestamp': '2025-01-01T00:00:00',
            'data': 'Genesis Block',
            'previous_hash': '0',
            'nonce': 1000,
            'hash': '0000genesis'
        }
        storage.save_block(genesis)

        # 2. 트랜잭션이 포함된 블록
        block1 = {
            'index': 1,
            'timestamp': '2025-01-01T01:00:00',
            'data': [
                {'sender': 'SYSTEM', 'recipient': 'Alice', 'amount': 100},
                {'sender': 'Alice', 'recipient': 'Bob', 'amount': 50}
            ],
            'previous_hash': '0000genesis',
            'nonce': 2000,
            'hash': '0000block1'
        }
        storage.save_block(block1)

        # 트랜잭션도 별도 저장
        for tx_data in block1['data']:
            tx_data['timestamp'] = '2025-01-01T01:00:00'
            storage.save_transaction(tx_data, block_index=1)

        # 3. 검증
        assert storage.get_block_count() == 2
        assert len(storage.get_transactions_by_block(1)) == 2
        assert storage.get_balance('Alice') == 50  # 100 - 50
        assert storage.get_balance('Bob') == 50

        # 4. 체인 무결성 확인
        all_blocks = storage.get_all_blocks()
        assert all_blocks[1]['previous_hash'] == all_blocks[0]['hash']
