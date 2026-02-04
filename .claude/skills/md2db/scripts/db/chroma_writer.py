# -*- coding: utf-8 -*-
"""
ChromaDB Writer for md2db v2

SQLite DB에서 ChromaDB로 변환합니다.
--to-chroma 명령어로 호출됩니다.

의존성:
    pip install chromadb sentence-transformers
"""

from pathlib import Path
from typing import List, Optional

# 선택적 임포트
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

# 진행률 표시 (선택적)
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class ChromaDBWriter:
    """SQLite DB에서 ChromaDB로 변환

    사용법:
        writer = ChromaDBWriter('chroma_dir/')
        writer.connect()
        writer.from_sqlite('source.db', chunk_size=1000)
    """

    DEFAULT_MODEL = 'jhgan/ko-sroberta-multitask'
    DEFAULT_CHUNK_SIZE = 1000

    def __init__(self, chroma_path: str, model_name: str = None,
                 collection_name: str = None):
        """
        Args:
            chroma_path: ChromaDB 저장 디렉토리
            model_name: 임베딩 모델명 (기본: ko-sroberta)
            collection_name: 컬렉션 이름 (기본: DB 파일명)
        """
        if not HAS_CHROMA:
            raise ImportError(
                "ChromaDB 기능을 사용하려면 chromadb, sentence-transformers 패키지가 필요합니다.\n"
                "pip install chromadb sentence-transformers"
            )

        self.chroma_path = chroma_path
        self.model_name = model_name or self.DEFAULT_MODEL
        self.collection_name = collection_name
        self.model = None
        self.client = None

    def connect(self) -> None:
        """ChromaDB 및 임베딩 모델 초기화"""
        # ChromaDB 클라이언트 생성
        Path(self.chroma_path).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.chroma_path)

        # 임베딩 모델 로드
        print(f"[INFO] 임베딩 모델 로드 중: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

    def from_sqlite(self, sqlite_path: str, chunk_size: int = None,
                    show_progress: bool = True) -> int:
        """SQLite DB에서 블록을 읽어 ChromaDB로 변환

        Args:
            sqlite_path: 소스 SQLite DB 경로
            chunk_size: 최대 청크 크기 (자동 분할)
            show_progress: 진행률 표시 여부

        Returns:
            임베딩된 청크 수
        """
        from db.sqlite_reader import DatabaseReader

        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE

        with DatabaseReader(sqlite_path) as reader:
            info = reader.get_info()

            # 컬렉션명 결정
            if not self.collection_name:
                if info['documents']:
                    doc = info['documents'][0]
                    self.collection_name = doc.get('filename', 'default').replace('.', '_')
                else:
                    self.collection_name = Path(sqlite_path).stem

            # 기존 컬렉션 삭제 후 재생성
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass

            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            # 블록 수집 및 청킹
            all_chunks = self._collect_and_chunk_blocks(reader, chunk_size)

            if not all_chunks:
                print("[WARN] 변환할 블록이 없습니다.")
                return 0

            # 임베딩 및 저장
            return self._embed_and_save(collection, all_chunks, show_progress)

    def _collect_and_chunk_blocks(self, reader, max_size: int) -> List[dict]:
        """모든 블록을 수집하고 필요시 분할"""
        chunks = []

        for section in reader.get_sections():
            for block in reader.get_blocks(section['id']):
                content = block.get('content', '')
                if not content or not content.strip():
                    continue

                raw_md = block.get('raw_markdown', content)

                if len(content) <= max_size:
                    chunks.append({
                        'content': content,
                        'raw_markdown': raw_md,
                        'section_path': section.get('path', ''),
                        'section_title': section.get('title', ''),
                        'block_type': block.get('type', 'paragraph'),
                        'block_id': block.get('id', 0),
                        'document_id': section.get('document_id', 0)
                    })
                else:
                    # 큰 블록 분할
                    for i, sub_chunk in enumerate(self._split_content(content, max_size)):
                        chunks.append({
                            'content': sub_chunk,
                            'raw_markdown': raw_md if i == 0 else '',
                            'section_path': section.get('path', ''),
                            'section_title': section.get('title', ''),
                            'block_type': block.get('type', 'paragraph'),
                            'block_id': block.get('id', 0),
                            'document_id': section.get('document_id', 0),
                            'sub_index': i
                        })

        return chunks

    def _split_content(self, content: str, max_size: int) -> List[str]:
        """긴 콘텐츠를 문단 단위로 분할"""
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if current_size + para_size > max_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0

            current_chunk.append(para)
            current_size += para_size

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _embed_and_save(self, collection, chunks: List[dict],
                        show_progress: bool) -> int:
        """임베딩 생성 및 ChromaDB 저장"""
        documents = [c['content'] for c in chunks]

        # 배치 임베딩
        batch_size = 100
        all_embeddings = []

        if show_progress and HAS_TQDM:
            iterator = tqdm(range(0, len(documents), batch_size),
                           desc="Embedding", unit="batch")
        else:
            iterator = range(0, len(documents), batch_size)

        for i in iterator:
            batch = documents[i:i+batch_size]
            embeddings = self.model.encode(batch)
            all_embeddings.extend(embeddings.tolist())

        # ChromaDB에 추가
        ids = []
        metadatas = []

        for i, c in enumerate(chunks):
            sub_idx = c.get('sub_index', 0)
            chunk_id = f"doc{c['document_id']}_blk{c['block_id']}_{sub_idx}"
            ids.append(chunk_id)

            metadatas.append({
                'section_path': c['section_path'],
                'section_title': c['section_title'],
                'block_type': c['block_type'],
                'document_id': str(c['document_id']),
                'block_id': str(c['block_id'])
            })

        # ChromaDB 배치 크기 제한 (최대 5461, 안전하게 5000)
        chroma_batch_size = 5000
        total_items = len(documents)

        for start in range(0, total_items, chroma_batch_size):
            end = min(start + chroma_batch_size, total_items)
            collection.add(
                documents=documents[start:end],
                embeddings=all_embeddings[start:end],
                metadatas=metadatas[start:end],
                ids=ids[start:end]
            )

        return len(chunks)

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """의미 기반 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수

        Returns:
            검색 결과 목록
        """
        if not self.client or not self.collection_name:
            raise ValueError("connect() 호출 후 사용하세요.")

        collection = self.client.get_collection(self.collection_name)

        # 쿼리 임베딩
        query_embedding = self.model.encode(query).tolist()

        # 검색 실행
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        # 결과 정리
        output = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                output.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0,
                    'id': results['ids'][0][i] if results['ids'] else ''
                })

        return output
