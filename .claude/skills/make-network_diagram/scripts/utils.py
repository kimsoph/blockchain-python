# -*- coding: utf-8 -*-
"""
make-network_diagram 스킬 유틸리티
- 한글 폰트 설정
- 출력 경로 관리
- 테마 정의
- DSL 파서
"""

import platform
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import Counter


def get_korean_font() -> str:
    """운영체제별 한글 폰트 반환"""
    system = platform.system()
    if system == 'Windows':
        return 'Malgun Gothic'
    elif system == 'Darwin':  # macOS
        return 'AppleGothic'
    else:  # Linux
        return 'NanumGothic'


def get_output_dir() -> Path:
    """출력 디렉토리 경로 반환: 9_Attachments/images/{YYYYMM}/"""
    current = Path(__file__).resolve()
    # .claude/skills/make-network_diagram/scripts/utils.py → ZK-PARA/
    vault_root = current.parents[4]

    output_dir = vault_root / '9_Attachments' / 'images' / datetime.now().strftime('%Y%m')
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def generate_filename(name: str, prefix: str = 'net') -> str:
    """타임스탬프가 포함된 파일명 생성"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에 사용 불가능한 문자 제거
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')
    return f"{prefix}_{safe_name}_{timestamp}.png"


# 테마 정의 (v2.0: 12개 속성으로 확장)
THEMES = {
    'minimal': {
        # 기본 속성
        'node_color': '#E8E8E8',
        'node_edge_color': '#333333',
        'edge_color': '#999999',
        'font_color': '#333333',
        'background': 'white',
        'title_color': '#333333',
        # 확장 속성 (v2.0)
        'node_shadow_color': '#00000018',
        'label_bg_color': '#FFFFFFEE',
        'label_border_color': '#888888',
        'accent_color': '#FF6B6B',
        'node_gradient_start': '#F5F5F5',
        'node_gradient_end': '#D0D0D0',
    },
    'elegant': {
        # 기본 속성
        'node_color': '#F5F5DC',
        'node_edge_color': '#8B4513',
        'edge_color': '#D2B48C',
        'font_color': '#4A3728',
        'background': '#FFFEF5',
        'title_color': '#4A3728',
        # 확장 속성 (v2.0)
        'node_shadow_color': '#8B451320',
        'label_bg_color': '#FFFEF5EE',
        'label_border_color': '#C4A35A',
        'accent_color': '#CD853F',
        'node_gradient_start': '#FAF0E6',
        'node_gradient_end': '#DEB887',
    },
    'clean': {
        # 기본 속성
        'node_color': '#E3F2FD',
        'node_edge_color': '#1976D2',
        'edge_color': '#90CAF9',
        'font_color': '#0D47A1',
        'background': 'white',
        'title_color': '#0D47A1',
        # 확장 속성 (v2.0)
        'node_shadow_color': '#1976D220',
        'label_bg_color': '#FFFFFFEE',
        'label_border_color': '#64B5F6',
        'accent_color': '#2196F3',
        'node_gradient_start': '#E3F2FD',
        'node_gradient_end': '#BBDEFB',
    },
    'corporate': {
        # 기본 속성
        'node_color': '#1E3A5F',
        'node_edge_color': '#0F1E30',
        'edge_color': '#4A6FA5',
        'font_color': 'white',
        'background': '#F5F5F5',
        'title_color': '#1E3A5F',
        # 확장 속성 (v2.0)
        'node_shadow_color': '#00000030',
        'label_bg_color': '#1E3A5FEE',
        'label_border_color': '#4A6FA5',
        'accent_color': '#FFA726',
        'node_gradient_start': '#2E5A8F',
        'node_gradient_end': '#1E3A5F',
    },
    'dark': {
        # 기본 속성
        'node_color': '#2D2D2D',
        'node_edge_color': '#4A4A4A',
        'edge_color': '#666666',
        'font_color': '#E0E0E0',
        'background': '#1A1A1A',
        'title_color': '#E0E0E0',
        # 확장 속성 (v2.0)
        'node_shadow_color': '#000000',
        'label_bg_color': '#2D2D2DEE',
        'label_border_color': '#555555',
        'accent_color': '#BB86FC',
        'node_gradient_start': '#404040',
        'node_gradient_end': '#2D2D2D',
    },
}


# v3.1: 컬러맵 정의 (빈도 기반 노드 색상용)
COLORMAPS = {
    'viridis': [
        '#440154', '#482878', '#3E4A89', '#31688E', '#26828E',
        '#1F9E89', '#35B779', '#6DCD59', '#B4DE2C', '#FDE725'
    ],
    'plasma': [
        '#0D0887', '#46039F', '#7201A8', '#9C179E', '#BD3786',
        '#D8576B', '#ED7953', '#FB9F3A', '#FDC328', '#F0F921'
    ],
    'coolwarm': [
        '#3B4CC0', '#5977E3', '#7B9FF9', '#9EBEFF', '#C0D4F5',
        '#F2CBB7', '#F7A889', '#EE8468', '#D65244', '#B40426'
    ],
    'blues': [
        '#F7FBFF', '#DEEBF7', '#C6DBEF', '#9ECAE1', '#6BAED6',
        '#4292C6', '#2171B5', '#08519C', '#08306B', '#041F4A'
    ],
    'greens': [
        '#F7FCF5', '#E5F5E0', '#C7E9C0', '#A1D99B', '#74C476',
        '#41AB5D', '#238B45', '#006D2C', '#00441B', '#002D12'
    ],
    'oranges': [
        '#FFF5EB', '#FEE6CE', '#FDD0A2', '#FDAE6B', '#FD8D3C',
        '#F16913', '#D94801', '#A63603', '#7F2704', '#5F1B02'
    ],
    'rainbow': [
        '#FF0000', '#FF7F00', '#FFFF00', '#7FFF00', '#00FF00',
        '#00FF7F', '#00FFFF', '#007FFF', '#0000FF', '#7F00FF'
    ],
    'pastel': [
        '#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF',
        '#D4BAFF', '#FFBAF2', '#FFE4BA', '#C9FFBA', '#BAF2FF'
    ],
    'ibk': [
        '#E3F2FD', '#BBDEFB', '#90CAF9', '#64B5F6', '#42A5F5',
        '#2196F3', '#1E88E5', '#1976D2', '#1565C0', '#0D47A1'
    ],
    'warm': [
        '#FFFFCC', '#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C',
        '#FC4E2A', '#E31A1C', '#BD0026', '#800026', '#4A0013'
    ],
}


def get_colormap_colors(
    values: List[float],
    colormap: str = 'viridis',
    reverse: bool = False
) -> List[str]:
    """
    값 목록을 컬러맵에 따라 색상 목록으로 변환

    Args:
        values: 정규화할 값 목록
        colormap: 컬러맵 이름
        reverse: 색상 순서 반전 여부

    Returns:
        HEX 색상 코드 목록
    """
    if not values:
        return []

    colors = COLORMAPS.get(colormap, COLORMAPS['viridis'])
    if reverse:
        colors = colors[::-1]

    n_colors = len(colors)

    # 값 정규화 (0~1 범위)
    min_val, max_val = min(values), max(values)
    if max_val == min_val:
        # 모든 값이 동일하면 중간 색상 사용
        mid_idx = n_colors // 2
        return [colors[mid_idx]] * len(values)

    normalized = [(v - min_val) / (max_val - min_val) for v in values]

    # 정규화된 값을 색상 인덱스로 변환
    result = []
    for norm_val in normalized:
        idx = int(norm_val * (n_colors - 1))
        idx = max(0, min(n_colors - 1, idx))
        result.append(colors[idx])

    return result


def assign_node_colors(
    nodes_with_freq: List[Tuple[str, Dict[str, Any]]],
    colormap: str = 'viridis',
    reverse: bool = True
) -> Dict[str, str]:
    """
    노드 빈도에 따라 색상 할당

    빈도가 높을수록 진한 색상 (reverse=True 기본)

    Args:
        nodes_with_freq: (노드명, {freq: 빈도, ...}) 튜플 목록
        colormap: 컬러맵 이름
        reverse: 색상 순서 반전 (True면 높은 빈도=진한색)

    Returns:
        노드명 -> 색상 매핑 딕셔너리
    """
    if not nodes_with_freq:
        return {}

    # 빈도 값 추출
    node_names = [n for n, _ in nodes_with_freq]
    frequencies = [attrs.get('freq', 1) for _, attrs in nodes_with_freq]

    # 컬러맵 적용
    colors = get_colormap_colors(frequencies, colormap, reverse)

    return dict(zip(node_names, colors))


def get_theme(theme_name: str) -> Dict[str, str]:
    """테마 설정 반환"""
    return THEMES.get(theme_name, THEMES['minimal'])


def parse_dsl(dsl_text: str) -> Dict[str, Any]:
    """
    DSL 텍스트를 파싱하여 네트워크 구조 반환

    DSL 형식:
    ```
    title: 제목
    layout: spring

    # 노드 정의 (선택)
    [노드1]
    [노드2] size=100 color=#FF0000

    # 엣지 정의
    [노드1] -- [노드2]           # 무방향
    [노드1] -> [노드2]           # 방향
    [노드1] --> [노드2]          # 점선 방향
    [노드1] -> [노드2]: 라벨     # 라벨 포함
    ```
    """
    result = {
        'title': None,
        'layout': 'spring',
        'nodes': [],  # [(name, attrs), ...]
        'edges': [],  # [(from, to, attrs), ...]
    }

    lines = dsl_text.strip().split('\n')

    for line in lines:
        line = line.strip()

        # 빈 줄, 주석 무시
        if not line or line.startswith('#'):
            continue

        # 메타데이터: title, layout
        if line.lower().startswith('title:'):
            result['title'] = line.split(':', 1)[1].strip()
            continue
        if line.lower().startswith('layout:'):
            result['layout'] = line.split(':', 1)[1].strip()
            continue

        # 엣지 패턴: [A] -> [B] 또는 [A] -- [B] 또는 [A] --> [B]
        edge_pattern = r'\[([^\]]+)\]\s*(--|->|-->|<->|<-->)\s*\[([^\]]+)\](?:\s*:\s*(.+))?'
        edge_match = re.match(edge_pattern, line)
        if edge_match:
            from_node = edge_match.group(1).strip()
            edge_type = edge_match.group(2).strip()
            to_node = edge_match.group(3).strip()
            label = edge_match.group(4).strip() if edge_match.group(4) else None

            attrs = {'label': label}

            # 엣지 타입 해석
            if edge_type == '--':
                attrs['directed'] = False
                attrs['style'] = 'solid'
            elif edge_type == '->':
                attrs['directed'] = True
                attrs['style'] = 'solid'
            elif edge_type == '-->':
                attrs['directed'] = True
                attrs['style'] = 'dashed'
            elif edge_type == '<->':
                attrs['directed'] = False  # 양방향은 무방향으로
                attrs['style'] = 'solid'
                attrs['bidirectional'] = True
            elif edge_type == '<-->':
                attrs['directed'] = False
                attrs['style'] = 'dashed'
                attrs['bidirectional'] = True

            result['edges'].append((from_node, to_node, attrs))

            # 노드 자동 추가 (없으면)
            existing_nodes = [n[0] for n in result['nodes']]
            if from_node not in existing_nodes:
                result['nodes'].append((from_node, {}))
            if to_node not in existing_nodes:
                result['nodes'].append((to_node, {}))
            continue

        # 단독 노드 패턴: [노드명] attr1=val1 attr2=val2
        node_pattern = r'^\[([^\]]+)\](.*)$'
        node_match = re.match(node_pattern, line)
        if node_match:
            node_name = node_match.group(1).strip()
            attrs_str = node_match.group(2).strip()

            attrs = {}
            if attrs_str:
                # 속성 파싱: size=100 color=#FF0000
                attr_pattern = r'(\w+)=([^\s]+)'
                for match in re.finditer(attr_pattern, attrs_str):
                    key = match.group(1)
                    value = match.group(2)
                    # 숫자 변환 시도
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                    attrs[key] = value

            # 기존 노드 업데이트 또는 추가
            existing_nodes = [n[0] for n in result['nodes']]
            if node_name in existing_nodes:
                idx = existing_nodes.index(node_name)
                result['nodes'][idx] = (node_name, {**result['nodes'][idx][1], **attrs})
            else:
                result['nodes'].append((node_name, attrs))

    return result


def extract_keywords_from_markdown(content: str) -> List[str]:
    """
    마크다운 파일에서 키워드 추출

    - ## 키워드 섹션 파싱
    - 해시태그 추출
    """
    keywords = []

    # ## 키워드 섹션 찾기
    keyword_section = re.search(
        r'^##\s*키워드.*?\n(.*?)(?=^##|\Z)',
        content,
        re.MULTILINE | re.DOTALL
    )

    if keyword_section:
        section_text = keyword_section.group(1)
        # 해시태그 추출: #단어
        hashtags = re.findall(r'#([가-힣A-Za-z0-9_]+)', section_text)
        keywords.extend(hashtags)

    # 본문에서 해시태그 추출 (키워드 섹션 외)
    hashtags = re.findall(r'#([가-힣A-Za-z0-9_]+)', content)
    for tag in hashtags:
        if tag not in keywords:
            keywords.append(tag)

    return keywords


def build_network_from_keywords(keywords: List[str], center_node: str = None) -> Dict[str, Any]:
    """
    키워드 목록에서 네트워크 구조 생성

    중심 노드가 있으면 별 모양(star), 없으면 완전 그래프(complete)
    """
    result = {
        'title': None,
        'layout': 'spring',
        'nodes': [],
        'edges': [],
    }

    if not keywords:
        return result

    # 노드 추가
    for kw in keywords:
        result['nodes'].append((kw, {}))

    # 중심 노드가 있으면 star 형태
    if center_node and center_node in keywords:
        for kw in keywords:
            if kw != center_node:
                result['edges'].append((center_node, kw, {'directed': False, 'style': 'solid'}))
    else:
        # 키워드 간 관계 (인접 키워드끼리 연결)
        for i in range(len(keywords) - 1):
            result['edges'].append((
                keywords[i],
                keywords[i + 1],
                {'directed': False, 'style': 'solid'}
            ))

        # 처음과 마지막 연결 (원형)
        if len(keywords) > 2:
            result['edges'].append((
                keywords[-1],
                keywords[0],
                {'directed': False, 'style': 'solid'}
            ))

    return result


# ============================================================================
# 의미연결망 (Semantic Network) 분석 함수들 (v3.0)
# ============================================================================

def setup_mecab():
    """Windows MeCab DLL 경로 설정"""
    mecab_path = r'C:\mecab'
    mecab_bin = r'C:\mecab\bin'
    if platform.system() == 'Windows' and os.path.exists(mecab_path):
        if hasattr(os, 'add_dll_directory') and os.path.exists(mecab_bin):
            os.add_dll_directory(mecab_bin)


def get_mecab_dicpath() -> str:
    """MeCab 사전 경로 반환"""
    return 'C:/mecab/mecab-ko-dic'


# 한국어 불용어 목록 (127개+)
KOREAN_STOPWORDS: Set[str] = {
    # 대명사/지시어
    '것', '수', '등', '및', '위', '더', '또', '그', '이', '저',
    '무엇', '어디', '누구', '언제', '어떻게', '왜', '뭐', '거',
    # 시간 관련
    '년', '월', '일', '때', '시', '분', '초', '오늘', '내일', '어제',
    # 장소/방향
    '곳', '안', '밖', '중', '전', '후', '위', '아래', '앞', '뒤',
    '속', '데', '쪽', '편', '측',
    # 단위/수량
    '점', '바', '말', '분', '명', '원', '개', '번', '회', '차',
    '배', '건', '가지', '종', '줄', '통', '권', '장', '페이지',
    # 접속/조사 역할
    '로서', '로써', '에서', '까지', '부터', '만큼', '처럼', '같이',
    '대로', '만', '뿐', '도', '은', '는', '이', '가', '을', '를',
    # 동사/형용사 어간
    '하다', '되다', '있다', '없다', '같다', '보다', '주다', '받다',
    '가다', '오다', '나다', '들다', '말하다', '알다', '모르다',
    # 일반 불용어
    '매우', '정말', '아주', '너무', '조금', '약간', '다소', '꽤',
    '제', '각', '당', '본', '동', '타', '기타', '여러', '모든',
    '어떤', '아무', '다른', '새', '옛', '첫', '끝', '마지막',
    # 서술/연결
    '그리고', '그러나', '그래서', '따라서', '하지만', '그런데',
    '또한', '그러면', '그렇지만', '즉', '곧', '바로',
    # 형식적 표현
    '경우', '부분', '관련', '통해', '대해', '대한', '위한', '의한',
    '따른', '관한', '향한', '기반', '바탕', '기준', '근거',
    # 추가 일반어
    '사실', '문제', '상황', '방법', '결과', '이유', '목적', '의미',
    '내용', '형태', '종류', '정도', '과정', '단계', '수준', '범위',
}


def extract_nouns_with_mecab(text: str, min_length: int = 2) -> List[str]:
    """
    MeCab으로 명사(NN*) 추출

    Args:
        text: 분석할 텍스트
        min_length: 최소 글자 수 (기본 2자 이상)

    Returns:
        추출된 명사 리스트 (중복 포함)
    """
    setup_mecab()
    try:
        import MeCab
    except ImportError:
        # MeCab이 없으면 간단한 한글 단어 추출로 대체
        words = re.findall(r'[가-힣]{2,}', text)
        return [w for w in words if w not in KOREAN_STOPWORDS and len(w) >= min_length]

    tagger = MeCab.Tagger(f'-d {get_mecab_dicpath()}')
    nouns = []

    parsed = tagger.parse(text)
    if not parsed:
        return nouns

    for line in parsed.split('\n'):
        if '\t' not in line:
            continue
        word, features = line.split('\t', 1)
        pos = features.split(',')[0]
        # NN으로 시작하는 품사: NNG(일반명사), NNP(고유명사), NNB(의존명사)
        if pos.startswith('NN') and len(word) >= min_length:
            if word not in KOREAN_STOPWORDS:
                nouns.append(word)

    return nouns


def clean_markdown(text: str) -> str:
    """
    마크다운 문법을 제거하고 순수 텍스트만 추출

    Args:
        text: 마크다운 텍스트

    Returns:
        정제된 텍스트
    """
    # 코드 블록 제거
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)

    # 마크다운 링크/이미지 제거
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)  # 이미지
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)   # 링크

    # 헤더 마커 제거
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)

    # 강조 마커 제거
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # 볼드
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # 이탤릭
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # 리스트 마커 제거
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

    # 인용구 마커 제거
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)

    # 수평선 제거
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # 테이블 구분선 제거
    text = re.sub(r'\|[-:]+\|', '', text)
    text = re.sub(r'\|', ' ', text)

    # YAML 프론트매터 제거
    text = re.sub(r'^---[\s\S]*?---', '', text)

    # 여러 공백/줄바꿈 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    return text.strip()


def calculate_keyword_frequencies(
    text: str,
    min_freq: int = 2,
    max_keywords: int = 30,
    use_stopwords: bool = True
) -> Dict[str, int]:
    """
    MeCab으로 명사 추출 후 빈도 계산

    Args:
        text: 분석할 텍스트
        min_freq: 최소 빈도 (이 값 이상만 포함)
        max_keywords: 최대 키워드 개수
        use_stopwords: 불용어 제거 여부

    Returns:
        {키워드: 빈도} 딕셔너리
    """
    nouns = extract_nouns_with_mecab(text)
    freq = Counter(nouns)

    # 최소 빈도 필터링
    filtered = {k: v for k, v in freq.items() if v >= min_freq}

    # 상위 N개 선택
    top_keywords = sorted(filtered.items(), key=lambda x: -x[1])[:max_keywords]

    return dict(top_keywords)


def split_into_sentences(text: str) -> List[str]:
    """
    텍스트를 문장 단위로 분리

    Args:
        text: 분리할 텍스트

    Returns:
        문장 리스트
    """
    # 마침표, 물음표, 느낌표, 한국어 마침표(。)로 분리
    sentences = re.split(r'[.?!。]\s*', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]


def build_cooccurrence_matrix(
    text: str,
    keywords: List[str],
    window_type: str = 'sentence'
) -> Dict[Tuple[str, str], int]:
    """
    키워드 간 동시출현 빈도 계산

    Args:
        text: 분석할 텍스트
        keywords: 대상 키워드 리스트
        window_type: 'sentence' (문장) 또는 'paragraph' (문단)

    Returns:
        {(키워드1, 키워드2): 동시출현 빈도} 딕셔너리
    """
    from collections import defaultdict

    cooccurrence = defaultdict(int)
    keyword_set = set(keywords)

    if window_type == 'sentence':
        units = split_into_sentences(text)
    else:  # paragraph
        units = [p.strip() for p in text.split('\n\n') if p.strip()]

    for unit in units:
        # 해당 단위에서 발견된 키워드들
        found_keywords = [kw for kw in keywords if kw in unit]

        # 중복 제거 후 조합 생성
        unique_found = list(set(found_keywords))

        for i, kw1 in enumerate(unique_found):
            for kw2 in unique_found[i + 1:]:
                # 정렬된 튜플로 저장 (순서 무관하게 동일 쌍 처리)
                pair = tuple(sorted([kw1, kw2]))
                cooccurrence[pair] += 1

    return dict(cooccurrence)


def normalize_frequencies_to_sizes(
    frequencies: Dict[str, int],
    min_size: int = 30,
    max_size: int = 150
) -> Dict[str, int]:
    """
    빈도를 노드 크기로 변환 (선형 정규화)

    Args:
        frequencies: {키워드: 빈도} 딕셔너리
        min_size: 최소 노드 크기
        max_size: 최대 노드 크기

    Returns:
        {키워드: 크기} 딕셔너리
    """
    if not frequencies:
        return {}

    values = list(frequencies.values())
    min_val, max_val = min(values), max(values)

    if min_val == max_val:
        mid_size = (min_size + max_size) // 2
        return {k: mid_size for k in frequencies}

    return {
        k: int(min_size + (v - min_val) / (max_val - min_val) * (max_size - min_size))
        for k, v in frequencies.items()
    }


def normalize_cooccurrence_to_weights(
    cooccurrence: Dict[Tuple[str, str], int],
    min_weight: float = 0.5,
    max_weight: float = 3.0
) -> Dict[Tuple[str, str], float]:
    """
    동시출현 빈도를 엣지 가중치(두께)로 변환

    Args:
        cooccurrence: {(키워드1, 키워드2): 빈도} 딕셔너리
        min_weight: 최소 두께
        max_weight: 최대 두께

    Returns:
        {(키워드1, 키워드2): 가중치} 딕셔너리
    """
    if not cooccurrence:
        return {}

    values = list(cooccurrence.values())
    min_val, max_val = min(values), max(values)

    if min_val == max_val:
        mid_weight = (min_weight + max_weight) / 2
        return {k: mid_weight for k in cooccurrence}

    return {
        k: min_weight + (v - min_val) / (max_val - min_val) * (max_weight - min_weight)
        for k, v in cooccurrence.items()
    }


def build_semantic_network(
    content: str,
    min_freq: int = 2,
    max_keywords: int = 30,
    min_cooccurrence: int = 2,
    max_edges: int = 50,
    window_type: str = 'sentence'
) -> Dict[str, Any]:
    """
    마크다운 콘텐츠에서 의미연결망 구축

    Args:
        content: 마크다운 콘텐츠
        min_freq: 최소 키워드 빈도
        max_keywords: 최대 키워드 개수
        min_cooccurrence: 최소 동시출현 빈도
        max_edges: 최대 엣지 개수
        window_type: 동시출현 분석 단위 ('sentence' 또는 'paragraph')

    Returns:
        네트워크 구조 딕셔너리
    """
    result = {
        'title': None,
        'layout': 'spring',
        'nodes': [],
        'edges': [],
    }

    # 1. 마크다운 정리
    clean_text = clean_markdown(content)

    if not clean_text:
        return result

    # 2. 키워드 빈도 계산
    frequencies = calculate_keyword_frequencies(
        clean_text,
        min_freq=min_freq,
        max_keywords=max_keywords
    )

    if not frequencies:
        return result

    keywords = list(frequencies.keys())

    # 3. 동시출현 분석
    cooccurrence = build_cooccurrence_matrix(clean_text, keywords, window_type)

    # 4. 최소 동시출현 필터링
    filtered_cooc = {k: v for k, v in cooccurrence.items() if v >= min_cooccurrence}

    # 5. 상위 N개 엣지 선택
    sorted_edges = sorted(filtered_cooc.items(), key=lambda x: -x[1])[:max_edges]

    # 6. 노드/엣지 크기 정규화
    node_sizes = normalize_frequencies_to_sizes(frequencies)
    edge_weights = normalize_cooccurrence_to_weights(dict(sorted_edges))

    # 7. 결과 구성
    # 노드: 엣지에 등장하는 키워드만 포함
    nodes_in_edges = set()
    for (kw1, kw2), _ in sorted_edges:
        nodes_in_edges.add(kw1)
        nodes_in_edges.add(kw2)

    result['nodes'] = [
        (kw, {
            'size': node_sizes.get(kw, 50),
            'freq': frequencies.get(kw, 1)
        })
        for kw in keywords if kw in nodes_in_edges
    ]

    result['edges'] = [
        (pair[0], pair[1], {
            'weight': edge_weights.get(pair, 1.0),
            'cooccurrence': cooccurrence.get(pair, 1),
            'directed': False,
            'style': 'solid'
        })
        for pair, _ in sorted_edges
    ]

    return result
