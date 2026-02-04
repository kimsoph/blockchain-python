# -*- coding: utf-8 -*-
"""
네트워크 및 REST API 테스트

Flask API 엔드포인트와 노드 관리 기능을 테스트합니다.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from src.network import create_app
from src.blockchain import Blockchain
from src.node import Node


@pytest.fixture
def app(capsys):
    """테스트용 Flask 앱"""
    blockchain = Blockchain(difficulty=2)
    capsys.readouterr()  # 제네시스 블록 출력 무시
    node = Node()
    return create_app(blockchain=blockchain, node=node)


@pytest.fixture
def client(app):
    """테스트 클라이언트"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    """헬스 체크 엔드포인트 테스트"""

    def test_health_check(self, client):
        """서버 상태 확인"""
        response = client.get('/health')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['status'] == 'healthy'
        assert 'chain_length' in data


class TestChainEndpoints:
    """체인 관련 엔드포인트 테스트"""

    def test_get_chain(self, client):
        """전체 체인 조회"""
        response = client.get('/chain')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert 'chain' in data
        assert 'length' in data
        assert len(data['chain']) == data['length']

    def test_validate_chain(self, client):
        """체인 유효성 검증"""
        response = client.get('/chain/valid')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['valid'] is True

    def test_get_block(self, client):
        """특정 블록 조회"""
        response = client.get('/blocks/0')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['index'] == 0

    def test_get_block_not_found(self, client):
        """존재하지 않는 블록 조회"""
        response = client.get('/blocks/999')

        assert response.status_code == 404

    def test_get_latest_block(self, client):
        """최신 블록 조회"""
        response = client.get('/blocks/latest')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert 'hash' in data


class TestTransactionEndpoints:
    """트랜잭션 관련 엔드포인트 테스트"""

    def test_new_transaction(self, client):
        """새 트랜잭션 생성"""
        tx_data = {
            'sender': 'Alice',
            'recipient': 'Bob',
            'amount': 100
        }
        response = client.post(
            '/transactions/new',
            data=json.dumps(tx_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        assert response.status_code == 201
        assert '추가' in data['message']
        assert data['transaction']['sender'] == 'Alice'

    def test_new_transaction_missing_fields(self, client):
        """필수 필드 누락 트랜잭션"""
        tx_data = {'sender': 'Alice'}
        response = client.post(
            '/transactions/new',
            data=json.dumps(tx_data),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_new_transaction_invalid_amount(self, client):
        """유효하지 않은 금액"""
        tx_data = {
            'sender': 'Alice',
            'recipient': 'Bob',
            'amount': -100
        }
        response = client.post(
            '/transactions/new',
            data=json.dumps(tx_data),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_get_pending_transactions(self, client):
        """펜딩 트랜잭션 조회"""
        # 트랜잭션 추가
        tx_data = {'sender': 'Alice', 'recipient': 'Bob', 'amount': 50}
        client.post(
            '/transactions/new',
            data=json.dumps(tx_data),
            content_type='application/json'
        )

        response = client.get('/transactions/pending')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['count'] >= 1

    def test_transaction_with_signature(self, client):
        """서명 포함 트랜잭션"""
        tx_data = {
            'sender': 'Alice',
            'recipient': 'Bob',
            'amount': 50,
            'signature': 'abc123',
            'sender_public_key': 'pubkey123'
        }
        response = client.post(
            '/transactions/new',
            data=json.dumps(tx_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        assert response.status_code == 201
        assert data['transaction']['signature'] == 'abc123'


class TestMiningEndpoint:
    """채굴 엔드포인트 테스트"""

    def test_mine_with_transactions(self, client, capsys):
        """트랜잭션 포함 채굴"""
        # 트랜잭션 추가
        tx_data = {'sender': 'Alice', 'recipient': 'Bob', 'amount': 50}
        client.post(
            '/transactions/new',
            data=json.dumps(tx_data),
            content_type='application/json'
        )

        # 채굴
        response = client.post(
            '/mine',
            data=json.dumps({'miner_address': 'Miner'}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        assert response.status_code == 201
        assert '채굴' in data['message']
        assert 'block' in data

    def test_mine_without_transactions(self, client):
        """트랜잭션 없이 채굴 시도"""
        # 펜딩 트랜잭션 없는 상태에서 채굴
        response = client.post(
            '/mine',
            data=json.dumps({'miner_address': 'Miner'}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        assert response.status_code == 200
        assert '없습니다' in data['message']

    def test_mine_default_miner(self, client):
        """기본 채굴자로 채굴"""
        tx_data = {'sender': 'Alice', 'recipient': 'Bob', 'amount': 50}
        client.post(
            '/transactions/new',
            data=json.dumps(tx_data),
            content_type='application/json'
        )

        # 빈 JSON 객체 전송
        response = client.post(
            '/mine',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 201


class TestBalanceEndpoint:
    """잔액 조회 엔드포인트 테스트"""

    def test_get_balance(self, client):
        """잔액 조회"""
        response = client.get('/balance/Alice')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['address'] == 'Alice'
        assert 'balance' in data

    def test_get_balance_unknown_address(self, client):
        """알 수 없는 주소 잔액"""
        response = client.get('/balance/UnknownUser')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['balance'] == 0


class TestNodeEndpoints:
    """노드 관리 엔드포인트 테스트"""

    def test_get_nodes_empty(self, client):
        """빈 노드 목록"""
        response = client.get('/nodes')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['count'] == 0

    def test_register_nodes(self, client):
        """노드 등록"""
        node_data = {
            'nodes': ['http://localhost:5001', 'http://localhost:5002']
        }
        response = client.post(
            '/nodes/register',
            data=json.dumps(node_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        assert response.status_code == 201
        assert len(data['registered']) == 2

    def test_register_nodes_empty(self, client):
        """빈 노드 목록 등록"""
        response = client.post(
            '/nodes/register',
            data=json.dumps({'nodes': []}),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_resolve_conflicts_no_nodes(self, client):
        """노드 없이 합의"""
        response = client.get('/nodes/resolve')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['replaced'] is False

    def test_nodes_health_empty(self, client):
        """빈 노드 상태 확인"""
        response = client.get('/nodes/health')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['total_count'] == 0


class TestNodeClass:
    """Node 클래스 단위 테스트"""

    def test_register_node(self):
        """노드 등록"""
        node = Node()
        assert node.register_node('http://localhost:5001') is True
        assert 'localhost:5001' in node.nodes

    def test_register_node_without_scheme(self):
        """스킴 없이 노드 등록"""
        node = Node()
        assert node.register_node('localhost:5001') is True

    def test_unregister_node(self):
        """노드 등록 해제"""
        node = Node()
        node.register_node('http://localhost:5001')
        assert node.unregister_node('http://localhost:5001') is True
        assert 'localhost:5001' not in node.nodes

    def test_get_nodes(self):
        """노드 목록 조회"""
        node = Node()
        node.register_node('http://localhost:5001')
        node.register_node('http://localhost:5002')

        nodes = node.get_nodes()
        assert len(nodes) == 2

    def test_clear_nodes(self):
        """모든 노드 삭제"""
        node = Node()
        node.register_node('http://localhost:5001')
        node.clear_nodes()

        assert len(node) == 0

    def test_node_contains(self):
        """노드 포함 여부"""
        node = Node()
        node.register_node('http://localhost:5001')

        assert 'http://localhost:5001' in node
        assert 'http://localhost:5002' not in node

    @patch('requests.get')
    def test_fetch_chain_success(self, mock_get):
        """체인 가져오기 성공"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'chain': [], 'length': 1}
        mock_get.return_value = mock_response

        node = Node()
        result = node.fetch_chain('localhost:5001')

        assert result is not None
        assert result['length'] == 1

    @patch('requests.get')
    def test_fetch_chain_failure(self, mock_get):
        """체인 가져오기 실패"""
        import requests
        mock_get.side_effect = requests.RequestException("Connection error")

        node = Node()
        result = node.fetch_chain('localhost:5001')

        assert result is None

    @patch('requests.post')
    def test_broadcast_transaction(self, mock_post):
        """트랜잭션 브로드캐스트"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        node = Node()
        node.register_node('http://localhost:5001')

        tx = {'sender': 'A', 'recipient': 'B', 'amount': 10}
        results = node.broadcast_transaction(tx)

        assert results['localhost:5001'] is True

    @patch('requests.get')
    def test_health_check(self, mock_get):
        """노드 상태 확인"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        node = Node()
        node.register_node('http://localhost:5001')

        health = node.health_check()
        assert health['localhost:5001'] is True


class TestAPIIntegration:
    """API 통합 테스트"""

    def test_full_workflow(self, client, capsys):
        """전체 워크플로우"""
        # 1. 초기 상태 확인
        response = client.get('/chain')
        assert json.loads(response.data)['length'] == 1

        # 2. 트랜잭션 생성
        tx_data = {'sender': 'SYSTEM', 'recipient': 'Alice', 'amount': 100}
        response = client.post(
            '/transactions/new',
            data=json.dumps(tx_data),
            content_type='application/json'
        )
        assert response.status_code == 201

        # 3. 채굴
        response = client.post(
            '/mine',
            data=json.dumps({'miner_address': 'Miner'}),
            content_type='application/json'
        )
        assert response.status_code == 201

        # 4. 체인 길이 증가 확인
        response = client.get('/chain')
        assert json.loads(response.data)['length'] == 2

        # 5. 체인 유효성 확인
        response = client.get('/chain/valid')
        assert json.loads(response.data)['valid'] is True

    def test_korean_transaction(self, client):
        """한글 트랜잭션"""
        tx_data = {
            'sender': '김철수',
            'recipient': '이영희',
            'amount': 50
        }
        response = client.post(
            '/transactions/new',
            data=json.dumps(tx_data, ensure_ascii=False).encode('utf-8'),
            content_type='application/json'
        )
        data = json.loads(response.data)

        assert response.status_code == 201
        assert data['transaction']['sender'] == '김철수'
