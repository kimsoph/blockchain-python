# -*- coding: utf-8 -*-
"""
BlockchainVisualizer 클래스 테스트

시각화 기능을 테스트합니다.
"""

import pytest
import os
import tempfile
import shutil
from src.visualizer import BlockchainVisualizer, MATPLOTLIB_AVAILABLE


@pytest.fixture
def visualizer():
    """임시 디렉토리를 사용하는 시각화 클래스"""
    temp_dir = tempfile.mkdtemp()
    viz = BlockchainVisualizer(output_dir=temp_dir)
    yield viz

    # 정리
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_blocks():
    """테스트용 블록 데이터"""
    return [
        {
            'index': 0,
            'timestamp': '2025-01-01T00:00:00',
            'data': 'Genesis Block',
            'previous_hash': '0',
            'nonce': 1000,
            'hash': '0000abcd1234567890abcdef1234567890abcdef1234567890abcdef12345678'
        },
        {
            'index': 1,
            'timestamp': '2025-01-01T01:00:00',
            'data': [{'sender': 'A', 'recipient': 'B', 'amount': 50}],
            'previous_hash': '0000abcd1234567890abcdef1234567890abcdef1234567890abcdef12345678',
            'nonce': 2500,
            'hash': '0000efgh5678901234abcdef5678901234abcdef5678901234abcdef56789012'
        },
        {
            'index': 2,
            'timestamp': '2025-01-01T02:00:00',
            'data': [{'sender': 'B', 'recipient': 'C', 'amount': 25}],
            'previous_hash': '0000efgh5678901234abcdef5678901234abcdef5678901234abcdef56789012',
            'nonce': 3200,
            'hash': '0000ijkl9012345678abcdef9012345678abcdef9012345678abcdef90123456'
        }
    ]


@pytest.fixture
def sample_transactions():
    """테스트용 트랜잭션 데이터"""
    return [
        {'sender': 'SYSTEM', 'recipient': 'Alice', 'amount': 100, 'timestamp': '2025-01-01'},
        {'sender': 'Alice', 'recipient': 'Bob', 'amount': 50, 'timestamp': '2025-01-02'},
        {'sender': 'Bob', 'recipient': 'Charlie', 'amount': 25, 'timestamp': '2025-01-03'},
        {'sender': 'Alice', 'recipient': 'Charlie', 'amount': 20, 'timestamp': '2025-01-04'},
    ]


@pytest.fixture
def sample_balance_history():
    """테스트용 잔액 히스토리"""
    return {
        'Alice': [(0, 0), (1, 100), (2, 50), (3, 30)],
        'Bob': [(0, 0), (1, 0), (2, 50), (3, 25)],
        'Charlie': [(0, 0), (1, 0), (2, 0), (3, 45)],
    }


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestVisualizerAvailability:
    """시각화 가용성 테스트"""

    def test_is_available(self, visualizer):
        """matplotlib 가용성 확인"""
        assert visualizer.is_available() is True

    def test_output_dir_created(self, visualizer):
        """출력 디렉토리 생성 확인"""
        assert os.path.exists(visualizer.output_dir)


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestBlockchainStructure:
    """블록체인 구조 시각화 테스트"""

    def test_draw_blockchain_structure(self, visualizer, sample_blocks):
        """블록체인 구조 다이어그램 생성"""
        filepath = visualizer.draw_blockchain_structure(sample_blocks)

        assert os.path.exists(filepath)
        assert filepath.endswith('.png')

    def test_draw_single_block(self, visualizer):
        """단일 블록 다이어그램"""
        blocks = [{
            'index': 0,
            'timestamp': '2025-01-01',
            'data': 'Genesis',
            'previous_hash': '0',
            'nonce': 100,
            'hash': '0000' + 'a' * 60
        }]

        filepath = visualizer.draw_blockchain_structure(blocks)
        assert os.path.exists(filepath)

    def test_draw_empty_blocks_error(self, visualizer):
        """빈 블록 리스트 에러"""
        with pytest.raises(ValueError, match="블록이 없습니다"):
            visualizer.draw_blockchain_structure([])

    def test_custom_filename(self, visualizer, sample_blocks):
        """사용자 정의 파일명"""
        filepath = visualizer.draw_blockchain_structure(
            sample_blocks,
            filename="custom_structure.png"
        )

        assert 'custom_structure.png' in filepath


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestTransactionFlow:
    """트랜잭션 흐름 시각화 테스트"""

    def test_draw_transaction_flow(self, visualizer, sample_transactions):
        """트랜잭션 흐름 다이어그램 생성"""
        filepath = visualizer.draw_transaction_flow(sample_transactions)

        assert os.path.exists(filepath)
        assert filepath.endswith('.png')

    def test_draw_single_transaction(self, visualizer):
        """단일 트랜잭션 다이어그램"""
        transactions = [
            {'sender': 'A', 'recipient': 'B', 'amount': 100, 'timestamp': '2025-01-01'}
        ]

        filepath = visualizer.draw_transaction_flow(transactions)
        assert os.path.exists(filepath)

    def test_empty_transactions_error(self, visualizer):
        """빈 트랜잭션 리스트 에러"""
        with pytest.raises(ValueError, match="트랜잭션이 없습니다"):
            visualizer.draw_transaction_flow([])

    def test_long_address_truncation(self, visualizer):
        """긴 주소 잘림 처리"""
        transactions = [
            {
                'sender': 'very_long_address_that_should_be_truncated_123456',
                'recipient': 'another_very_long_address_for_testing_789012',
                'amount': 50,
                'timestamp': '2025-01-01'
            }
        ]

        filepath = visualizer.draw_transaction_flow(transactions)
        assert os.path.exists(filepath)


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestBalanceChart:
    """잔액 차트 테스트"""

    def test_draw_balance_chart(self, visualizer, sample_balance_history):
        """잔액 변화 차트 생성"""
        filepath = visualizer.draw_balance_chart(sample_balance_history)

        assert os.path.exists(filepath)
        assert filepath.endswith('.png')

    def test_single_address_balance(self, visualizer):
        """단일 주소 잔액"""
        history = {
            'Alice': [(0, 0), (1, 100), (2, 150)]
        }

        filepath = visualizer.draw_balance_chart(history)
        assert os.path.exists(filepath)

    def test_empty_balance_error(self, visualizer):
        """빈 잔액 데이터 에러"""
        with pytest.raises(ValueError, match="잔액 데이터가 없습니다"):
            visualizer.draw_balance_chart({})


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestMiningStats:
    """채굴 통계 테스트"""

    def test_draw_mining_stats(self, visualizer, sample_blocks):
        """채굴 통계 차트 생성"""
        filepath = visualizer.draw_mining_stats(sample_blocks)

        assert os.path.exists(filepath)
        assert filepath.endswith('.png')

    def test_insufficient_blocks_error(self, visualizer):
        """블록 부족 에러"""
        blocks = [{
            'index': 0, 'timestamp': '2025-01-01', 'data': 'G',
            'previous_hash': '0', 'nonce': 1, 'hash': '0000' + 'a' * 60
        }]

        with pytest.raises(ValueError, match="최소 2개"):
            visualizer.draw_mining_stats(blocks)


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestNetworkTopology:
    """네트워크 토폴로지 테스트"""

    def test_draw_network_topology(self, visualizer):
        """네트워크 토폴로지 다이어그램 생성"""
        nodes = ['localhost:5000', 'localhost:5001', 'localhost:5002']

        filepath = visualizer.draw_network_topology(nodes)

        assert os.path.exists(filepath)
        assert filepath.endswith('.png')

    def test_single_node(self, visualizer):
        """단일 노드 토폴로지"""
        nodes = ['localhost:5000']

        filepath = visualizer.draw_network_topology(nodes)
        assert os.path.exists(filepath)

    def test_empty_nodes_error(self, visualizer):
        """빈 노드 리스트 에러"""
        with pytest.raises(ValueError, match="노드가 없습니다"):
            visualizer.draw_network_topology([])

    def test_custom_connections(self, visualizer):
        """사용자 정의 연결"""
        nodes = ['A', 'B', 'C', 'D']
        connections = [('A', 'B'), ('B', 'C'), ('C', 'D')]

        filepath = visualizer.draw_network_topology(nodes, connections=connections)
        assert os.path.exists(filepath)


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestGenerateAllVisualizations:
    """전체 시각화 생성 테스트"""

    def test_generate_all(self, visualizer, sample_blocks, sample_transactions,
                          sample_balance_history):
        """모든 시각화 생성"""
        data = {
            'blocks': sample_blocks,
            'transactions': sample_transactions,
            'balance_history': sample_balance_history,
            'nodes': ['node1', 'node2', 'node3']
        }

        results = visualizer.generate_all_visualizations(data)

        assert 'structure' in results
        assert 'transaction_flow' in results
        assert 'balance' in results
        assert 'mining_stats' in results
        assert 'network' in results

    def test_partial_data(self, visualizer, sample_blocks):
        """부분 데이터로 시각화"""
        data = {
            'blocks': sample_blocks
        }

        results = visualizer.generate_all_visualizations(data)

        assert 'structure' in results
        assert 'mining_stats' in results
        # transactions, balance_history, nodes 없으므로 해당 항목 없음

    def test_empty_data(self, visualizer):
        """빈 데이터"""
        results = visualizer.generate_all_visualizations({})

        # 모든 항목이 없거나 에러
        assert len([k for k in results if not k.endswith('_error')]) == 0 or results == {}


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestKoreanSupport:
    """한글 지원 테스트"""

    def test_korean_in_transactions(self, visualizer):
        """한글 트랜잭션"""
        transactions = [
            {'sender': '김철수', 'recipient': '이영희', 'amount': 100, 'timestamp': '2025-01-01'},
            {'sender': '이영희', 'recipient': '박민수', 'amount': 50, 'timestamp': '2025-01-02'},
        ]

        filepath = visualizer.draw_transaction_flow(transactions)
        assert os.path.exists(filepath)

    def test_korean_in_balance(self, visualizer):
        """한글 주소 잔액"""
        history = {
            '김철수': [(0, 0), (1, 100), (2, 50)],
            '이영희': [(0, 0), (1, 0), (2, 50)],
        }

        filepath = visualizer.draw_balance_chart(history)
        assert os.path.exists(filepath)


class TestWithoutMatplotlib:
    """matplotlib 없을 때 테스트"""

    def test_is_available_flag(self):
        """가용성 플래그 확인"""
        # MATPLOTLIB_AVAILABLE은 임포트 시 결정됨
        from src.visualizer import MATPLOTLIB_AVAILABLE
        # 테스트 환경에서는 True여야 함
        assert isinstance(MATPLOTLIB_AVAILABLE, bool)
