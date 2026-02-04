# -*- coding: utf-8 -*-
"""
WordCloud 생성 스킬
마크다운 문서에서 핵심 키워드를 추출하여 워드클라우드 이미지 생성
"""

import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union
from collections import Counter

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from wordcloud import WordCloud

from utils import (
    get_korean_font,
    get_korean_font_path,
    get_output_dir,
    generate_filename,
    setup_mecab,
    get_mecab_dicpath,
    get_stopwords,
)


class WordCloudDrawer:
    """워드클라우드 생성 클래스"""

    def __init__(
        self,
        max_words: int = 100,
        width: int = 1200,
        height: int = 800,
        background_color: str = 'white',
        colormap: str = 'viridis',
        dpi: int = 300,
        min_font_size: int = 10,
        max_font_size: int = 150,
    ):
        """
        Args:
            max_words: 최대 단어 수 (기본: 100)
            width: 이미지 너비 (기본: 1200)
            height: 이미지 높이 (기본: 800)
            background_color: 배경색 (기본: 'white')
            colormap: matplotlib 컬러맵 (기본: 'viridis')
            dpi: 출력 해상도 (기본: 300)
            min_font_size: 최소 폰트 크기 (기본: 10)
            max_font_size: 최대 폰트 크기 (기본: 150)
        """
        self.max_words = max_words
        self.width = width
        self.height = height
        self.background_color = background_color
        self.colormap = colormap
        self.dpi = dpi
        self.min_font_size = min_font_size
        self.max_font_size = max_font_size

        self.word_freq: Dict[str, int] = {}
        self.title: Optional[str] = None
        self.mask: Optional[np.ndarray] = None

        # Mecab 설정
        setup_mecab()

        # 한글 폰트 설정
        self.font_path = get_korean_font_path()
        rcParams['font.family'] = get_korean_font()
        rcParams['axes.unicode_minus'] = False

        # Mecab 로드 시도 (직접 MeCab 모듈 사용)
        self.mecab_tagger = None
        try:
            import MeCab
            dicpath = get_mecab_dicpath()
            self.mecab_tagger = MeCab.Tagger(f'-d {dicpath}')
            print(f"[OK] Mecab 로드 성공 (버전: {MeCab.VERSION})")
        except Exception as e:
            print(f"[WARN] Mecab 로드 실패, 공백 분리 방식 사용: {e}")

    def set_title(self, title: str) -> 'WordCloudDrawer':
        """제목 설정"""
        self.title = title
        return self

    def set_mask(self, mask_path: str) -> 'WordCloudDrawer':
        """마스크 이미지 설정"""
        from PIL import Image
        mask_image = Image.open(mask_path).convert('L')
        self.mask = np.array(mask_image)
        return self

    def set_colormap(self, colormap: str) -> 'WordCloudDrawer':
        """컬러맵 설정"""
        self.colormap = colormap
        return self

    def from_text(self, text: str, use_stopwords: bool = True) -> 'WordCloudDrawer':
        """텍스트에서 단어 빈도 추출"""
        words = self._tokenize(text)

        if use_stopwords:
            stopwords = get_stopwords(include_speech=True)
            words = [w for w in words if w not in stopwords and len(w) > 1]

        self.word_freq = Counter(words)
        return self

    def from_file(self, file_path: str, use_stopwords: bool = True) -> 'WordCloudDrawer':
        """마크다운 파일에서 단어 빈도 추출"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # YAML 프론트매터 제거
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

        # 마크다운 문법 제거
        content = self._clean_markdown(content)

        return self.from_text(content, use_stopwords)

    def from_dict(self, word_freq: Dict[str, Union[int, float]]) -> 'WordCloudDrawer':
        """딕셔너리에서 단어 빈도 설정"""
        self.word_freq = {k: int(v) for k, v in word_freq.items()}
        return self

    def from_keywords(self, keywords: List[str], weights: Optional[List[int]] = None) -> 'WordCloudDrawer':
        """키워드 리스트에서 단어 빈도 설정"""
        if weights is None:
            weights = [1] * len(keywords)
        self.word_freq = dict(zip(keywords, weights))
        return self

    def _tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화 (Mecab 또는 공백 분리)"""
        if self.mecab_tagger:
            # Mecab 형태소 분석 (직접 parse 사용)
            try:
                words = []
                parsed = self.mecab_tagger.parse(text)
                for line in parsed.split('\n'):
                    if line == 'EOS' or not line.strip():
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        word = parts[0]
                        pos_info = parts[1].split(',')[0]  # 첫 번째 품사 태그
                        # 명사(NN*), 동사(VV), 형용사(VA) 추출
                        if pos_info.startswith('NN') or pos_info.startswith('VV') or pos_info.startswith('VA'):
                            # 동사/형용사는 어간만 (1글자 이상)
                            if pos_info.startswith('VV') or pos_info.startswith('VA'):
                                if len(word) > 1:
                                    words.append(word)
                            else:
                                words.append(word)
                return words
            except Exception as e:
                print(f"[WARN] Mecab 분석 실패, 공백 분리 사용: {e}")

        # Fallback: 공백 분리
        # 한글만 추출
        text = re.sub(r'[^가-힣\s]', ' ', text)
        words = text.split()
        return [w for w in words if len(w) > 1]

    def _clean_markdown(self, text: str) -> str:
        """마크다운 문법 제거"""
        # 코드 블록 제거
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # 인라인 코드 제거
        text = re.sub(r'`[^`]+`', '', text)
        # 링크 제거 (텍스트만 유지)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # 이미지 제거
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
        # 헤더 마커 제거
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        # 볼드/이탤릭 제거
        text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
        text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
        # 리스트 마커 제거
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
        # 인용구 마커 제거
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        # 수평선 제거
        text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)

        return text

    def generate(self) -> WordCloud:
        """워드클라우드 생성"""
        if not self.word_freq:
            raise ValueError("단어 빈도 데이터가 없습니다. from_text(), from_file(), from_dict() 중 하나를 먼저 호출하세요.")

        wc = WordCloud(
            font_path=self.font_path,
            width=self.width,
            height=self.height,
            max_words=self.max_words,
            background_color=self.background_color,
            colormap=self.colormap,
            min_font_size=self.min_font_size,
            max_font_size=self.max_font_size,
            mask=self.mask,
            prefer_horizontal=0.7,
            relative_scaling=0.5,
        )

        wc.generate_from_frequencies(self.word_freq)
        return wc

    def save(self, name: str, output_dir: Optional[str] = None) -> str:
        """워드클라우드 이미지 저장"""
        wc = self.generate()

        # 출력 경로 설정
        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = get_output_dir()

        filename = generate_filename(name, prefix='wc')
        output_path = out_dir / filename

        # Figure 생성 및 저장
        fig, ax = plt.subplots(figsize=(self.width / 100, self.height / 100))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')

        if self.title:
            ax.set_title(self.title, fontsize=16, fontweight='bold', pad=10)

        plt.tight_layout(pad=0.5)
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)

        # 결과 출력
        print(f"[OK] 워드클라우드 저장 완료: {output_path}")
        print(f"[INFO] 옵시디언 삽입: ![[images/{out_dir.name}/{filename}]]")

        return str(output_path)

    def show(self) -> 'WordCloudDrawer':
        """워드클라우드 미리보기"""
        wc = self.generate()

        fig, ax = plt.subplots(figsize=(self.width / 100, self.height / 100))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')

        if self.title:
            ax.set_title(self.title, fontsize=16, fontweight='bold', pad=10)

        plt.tight_layout(pad=0.5)
        plt.show()

        return self

    def get_top_words(self, n: int = 20) -> List[tuple]:
        """상위 N개 단어 반환"""
        return Counter(self.word_freq).most_common(n)


def main():
    """CLI 진입점"""
    parser = argparse.ArgumentParser(
        description='마크다운 파일에서 워드클라우드 생성',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python draw_wordcloud.py --file "취임사.md" --name "이재명취임사"
  python draw_wordcloud.py --text "단어1 단어2 단어3" --name "테스트"
  python draw_wordcloud.py --file "취임사.md" --max-words 50 --colormap plasma
        """
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--file', '-f', help='입력 마크다운 파일 경로')
    input_group.add_argument('--text', '-t', help='직접 텍스트 입력')

    parser.add_argument('--name', '-n', required=True, help='출력 파일명 (확장자 제외)')
    parser.add_argument('--title', help='워드클라우드 제목')
    parser.add_argument('--max-words', type=int, default=100, help='최대 단어 수 (기본: 100)')
    parser.add_argument('--width', type=int, default=1200, help='이미지 너비 (기본: 1200)')
    parser.add_argument('--height', type=int, default=800, help='이미지 높이 (기본: 800)')
    parser.add_argument('--colormap', default='viridis',
                        help='컬러맵 (viridis, plasma, Blues, Reds 등)')
    parser.add_argument('--background', default='white', help='배경색 (기본: white)')
    parser.add_argument('--mask', help='마스크 이미지 경로')
    parser.add_argument('--no-stopwords', action='store_true', help='불용어 제거 비활성화')
    parser.add_argument('--output-dir', '-o', help='출력 디렉토리 (기본: 9_Attachments/images/YYYYMM/)')
    parser.add_argument('--top-words', type=int, help='상위 N개 단어 출력')

    args = parser.parse_args()

    # WordCloudDrawer 생성
    drawer = WordCloudDrawer(
        max_words=args.max_words,
        width=args.width,
        height=args.height,
        background_color=args.background,
        colormap=args.colormap,
    )

    # 제목 설정
    if args.title:
        drawer.set_title(args.title)

    # 마스크 설정
    if args.mask:
        drawer.set_mask(args.mask)

    # 입력 처리
    use_stopwords = not args.no_stopwords
    if args.file:
        drawer.from_file(args.file, use_stopwords=use_stopwords)
    else:
        drawer.from_text(args.text, use_stopwords=use_stopwords)

    # 상위 단어 출력
    if args.top_words:
        print(f"\n[INFO] 상위 {args.top_words}개 단어:")
        for word, freq in drawer.get_top_words(args.top_words):
            print(f"  {word}: {freq}")
        print()

    # 저장
    drawer.save(args.name, output_dir=args.output_dir)


if __name__ == '__main__':
    main()
