# -*- coding: utf-8 -*-
"""
P2P 노드 관리 모듈

블록체인 네트워크의 노드 관리 기능을 제공합니다.
"""

import requests
from typing import Set, List, Dict, Any, Optional
from urllib.parse import urlparse


class Node:
    """
    블록체인 네트워크 노드 관리 클래스

    피어 노드 등록, 체인 동기화, 합의 알고리즘을 처리합니다.

    Attributes:
        nodes: 등록된 피어 노드 집합
    """

    def __init__(self):
        """노드 초기화"""
        self.nodes: Set[str] = set()

    def register_node(self, address: str) -> bool:
        """
        새 노드 등록

        Args:
            address: 노드 주소 (예: 'http://localhost:5001')

        Returns:
            등록 성공 여부
        """
        try:
            parsed_url = urlparse(address)
            if parsed_url.netloc:
                # 'http://localhost:5001' -> 'localhost:5001'
                self.nodes.add(parsed_url.netloc)
                return True
            elif parsed_url.path:
                # 'localhost:5001' 형태로 입력된 경우
                self.nodes.add(parsed_url.path)
                return True
            return False
        except Exception:
            return False

    def unregister_node(self, address: str) -> bool:
        """
        노드 등록 해제

        Args:
            address: 노드 주소

        Returns:
            해제 성공 여부
        """
        try:
            parsed_url = urlparse(address)
            node = parsed_url.netloc if parsed_url.netloc else parsed_url.path

            if node in self.nodes:
                self.nodes.remove(node)
                return True
            return False
        except Exception:
            return False

    def get_nodes(self) -> List[str]:
        """
        등록된 모든 노드 반환

        Returns:
            노드 주소 리스트
        """
        return list(self.nodes)

    def clear_nodes(self) -> None:
        """모든 노드 등록 해제"""
        self.nodes.clear()

    def fetch_chain(self, node: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        특정 노드에서 체인 가져오기

        Args:
            node: 노드 주소
            timeout: 요청 타임아웃 (초)

        Returns:
            체인 정보 또는 None (실패 시)
        """
        try:
            response = requests.get(
                f'http://{node}/chain',
                timeout=timeout
            )
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None

    def broadcast_transaction(self, transaction: Dict[str, Any], timeout: int = 5) -> Dict[str, bool]:
        """
        모든 노드에 트랜잭션 브로드캐스트

        Args:
            transaction: 트랜잭션 데이터
            timeout: 요청 타임아웃 (초)

        Returns:
            노드별 성공/실패 결과
        """
        results = {}
        for node in self.nodes:
            try:
                response = requests.post(
                    f'http://{node}/transactions/new',
                    json=transaction,
                    timeout=timeout
                )
                results[node] = response.status_code == 201
            except requests.RequestException:
                results[node] = False
        return results

    def broadcast_block(self, block: Dict[str, Any], timeout: int = 5) -> Dict[str, bool]:
        """
        모든 노드에 새 블록 브로드캐스트

        Args:
            block: 블록 데이터
            timeout: 요청 타임아웃 (초)

        Returns:
            노드별 성공/실패 결과
        """
        results = {}
        for node in self.nodes:
            try:
                response = requests.post(
                    f'http://{node}/blocks/new',
                    json=block,
                    timeout=timeout
                )
                results[node] = response.status_code == 201
            except requests.RequestException:
                results[node] = False
        return results

    def find_longest_chain(self, current_length: int, current_chain: List[Dict],
                           timeout: int = 5) -> Optional[List[Dict]]:
        """
        네트워크에서 가장 긴 유효한 체인 찾기 (합의 알고리즘)

        Args:
            current_length: 현재 체인 길이
            current_chain: 현재 체인
            timeout: 요청 타임아웃

        Returns:
            더 긴 유효한 체인 또는 None (교체 불필요 시)
        """
        longest_chain = None
        max_length = current_length

        for node in self.nodes:
            chain_data = self.fetch_chain(node, timeout)

            if chain_data and chain_data.get('length', 0) > max_length:
                chain = chain_data.get('chain', [])
                # 체인 유효성은 호출자가 검증해야 함
                max_length = chain_data['length']
                longest_chain = chain

        return longest_chain

    def health_check(self, timeout: int = 2) -> Dict[str, bool]:
        """
        모든 노드 상태 확인

        Args:
            timeout: 요청 타임아웃

        Returns:
            노드별 상태 (True=정상, False=비정상)
        """
        results = {}
        for node in self.nodes:
            try:
                response = requests.get(
                    f'http://{node}/health',
                    timeout=timeout
                )
                results[node] = response.status_code == 200
            except requests.RequestException:
                results[node] = False
        return results

    def __len__(self) -> int:
        """등록된 노드 수"""
        return len(self.nodes)

    def __contains__(self, address: str) -> bool:
        """노드 등록 여부 확인"""
        parsed = urlparse(address)
        node = parsed.netloc if parsed.netloc else parsed.path
        return node in self.nodes
