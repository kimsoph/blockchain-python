# -*- coding: utf-8 -*-
"""
블록체인 REST API 서버 모듈

Flask를 사용한 HTTP API를 제공합니다.
"""

import json
from typing import Optional
from flask import Flask, jsonify, request

from .blockchain import Blockchain
from .transaction import Transaction
from .node import Node


def create_app(blockchain: Optional[Blockchain] = None,
               node: Optional[Node] = None,
               difficulty: int = 2) -> Flask:
    """
    Flask 앱 생성

    Args:
        blockchain: 사용할 블록체인 (없으면 새로 생성)
        node: 노드 관리자 (없으면 새로 생성)
        difficulty: 블록체인 난이도 (새로 생성 시)

    Returns:
        Flask 앱 인스턴스
    """
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False  # 한글 지원

    # 블록체인 및 노드 초기화
    if blockchain is None:
        # 출력 억제를 위해 난이도 낮게 설정
        blockchain = Blockchain(difficulty=difficulty)
    if node is None:
        node = Node()

    # 앱에 저장
    app.blockchain = blockchain
    app.node = node

    @app.route('/health', methods=['GET'])
    def health():
        """서버 상태 확인"""
        return jsonify({
            'status': 'healthy',
            'chain_length': len(blockchain)
        }), 200

    @app.route('/chain', methods=['GET'])
    def get_chain():
        """전체 체인 조회"""
        chain_data = [block.to_dict() for block in blockchain.chain]
        return jsonify({
            'chain': chain_data,
            'length': len(blockchain)
        }), 200

    @app.route('/chain/valid', methods=['GET'])
    def validate_chain():
        """체인 유효성 검증"""
        is_valid = blockchain.is_chain_valid()
        return jsonify({
            'valid': is_valid,
            'length': len(blockchain)
        }), 200

    @app.route('/blocks/<int:index>', methods=['GET'])
    def get_block(index: int):
        """특정 블록 조회"""
        if 0 <= index < len(blockchain):
            return jsonify(blockchain[index].to_dict()), 200
        return jsonify({'error': '블록을 찾을 수 없습니다'}), 404

    @app.route('/blocks/latest', methods=['GET'])
    def get_latest_block():
        """최신 블록 조회"""
        return jsonify(blockchain.get_latest_block().to_dict()), 200

    @app.route('/transactions/new', methods=['POST'])
    def new_transaction():
        """새 트랜잭션 생성"""
        data = request.get_json()

        required = ['sender', 'recipient', 'amount']
        if not all(k in data for k in required):
            return jsonify({'error': '필수 필드가 누락되었습니다: sender, recipient, amount'}), 400

        try:
            tx = Transaction(
                sender=data['sender'],
                recipient=data['recipient'],
                amount=float(data['amount'])
            )

            # 서명 정보가 있으면 추가
            if 'signature' in data:
                tx.signature = data['signature']
            if 'sender_public_key' in data:
                tx.sender_public_key = data['sender_public_key']

            next_block = blockchain.add_transaction(tx)

            return jsonify({
                'message': '트랜잭션이 추가되었습니다',
                'transaction': tx.to_dict(),
                'block_index': next_block
            }), 201

        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/transactions/pending', methods=['GET'])
    def get_pending_transactions():
        """펜딩 트랜잭션 조회"""
        pending = [tx.to_dict() for tx in blockchain.pending_transactions]
        return jsonify({
            'pending_transactions': pending,
            'count': len(pending)
        }), 200

    @app.route('/mine', methods=['POST'])
    def mine():
        """채굴 수행"""
        data = request.get_json() or {}
        miner_address = data.get('miner_address', 'anonymous_miner')

        block = blockchain.mine_pending_transactions(miner_address)

        if block is None:
            return jsonify({
                'message': '채굴할 트랜잭션이 없습니다'
            }), 200

        # 다른 노드에 새 블록 브로드캐스트
        if len(node) > 0:
            node.broadcast_block(block.to_dict())

        return jsonify({
            'message': '새 블록이 채굴되었습니다',
            'block': block.to_dict(),
            'reward': blockchain.mining_reward
        }), 201

    @app.route('/balance/<address>', methods=['GET'])
    def get_balance(address: str):
        """잔액 조회"""
        balance = blockchain.get_balance(address)
        return jsonify({
            'address': address,
            'balance': balance
        }), 200

    @app.route('/nodes', methods=['GET'])
    def get_nodes():
        """등록된 노드 목록 조회"""
        return jsonify({
            'nodes': node.get_nodes(),
            'count': len(node)
        }), 200

    @app.route('/nodes/register', methods=['POST'])
    def register_nodes():
        """노드 등록"""
        data = request.get_json()

        nodes_list = data.get('nodes', [])
        if not nodes_list:
            return jsonify({'error': '등록할 노드 목록이 필요합니다'}), 400

        registered = []
        for node_addr in nodes_list:
            if node.register_node(node_addr):
                registered.append(node_addr)

        return jsonify({
            'message': '노드가 등록되었습니다',
            'registered': registered,
            'total_nodes': node.get_nodes()
        }), 201

    @app.route('/nodes/resolve', methods=['GET'])
    def resolve_conflicts():
        """합의 알고리즘 실행 (가장 긴 체인 채택)"""
        current_chain = [b.to_dict() for b in blockchain.chain]
        new_chain = node.find_longest_chain(len(blockchain), current_chain)

        if new_chain:
            # 체인 교체 로직 (여기서는 단순히 알림만)
            return jsonify({
                'message': '체인이 교체되었습니다',
                'replaced': True,
                'new_length': len(new_chain)
            }), 200
        else:
            return jsonify({
                'message': '현재 체인이 가장 깁니다',
                'replaced': False,
                'length': len(blockchain)
            }), 200

    @app.route('/nodes/health', methods=['GET'])
    def nodes_health():
        """모든 노드 상태 확인"""
        health_status = node.health_check()
        return jsonify({
            'nodes_health': health_status,
            'healthy_count': sum(1 for v in health_status.values() if v),
            'total_count': len(health_status)
        }), 200

    return app


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False,
               difficulty: int = 2):
    """
    서버 실행

    Args:
        host: 바인딩 호스트
        port: 포트 번호
        debug: 디버그 모드
        difficulty: 블록체인 난이도
    """
    app = create_app(difficulty=difficulty)
    print(f"\n블록체인 노드가 {host}:{port}에서 실행 중입니다...")
    print(f"API 문서: http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    run_server(debug=True)
