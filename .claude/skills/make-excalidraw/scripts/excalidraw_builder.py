# -*- coding: utf-8 -*-
"""
make-excalidraw 스킬 핵심 빌더 클래스
Excalidraw JSON 파일을 생성하는 빌더 패턴 구현
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from .utils import (
    generate_id,
    generate_seed,
    generate_filename,
    get_output_dir,
    get_vault_root,
    get_theme,
    calculate_text_dimensions,
    FILL_STYLES,
    ARROWHEAD_TYPES,
    FONT_FAMILIES,
    FONT_SIZES,
    ROUGHNESS_LEVELS,
    DEFAULT_FILL_STYLE
)


class ExcalidrawBuilder:
    """
    Excalidraw JSON 파일을 생성하는 빌더 클래스.
    메서드 체이닝을 지원하여 유연하게 다이어그램을 구성할 수 있다.
    """

    def __init__(self, theme: str = 'minimal'):
        """
        ExcalidrawBuilder 초기화.

        Args:
            theme: 테마 이름 (minimal, elegant, clean, corporate, dark)
        """
        self.theme = get_theme(theme)
        self.theme_name = theme
        self.elements: List[Dict[str, Any]] = []
        self.files: Dict[str, Any] = {}
        self._element_map: Dict[str, Dict[str, Any]] = {}  # ID로 요소 빠른 검색

    def _create_base_element(
        self,
        element_type: str,
        x: float,
        y: float,
        width: float,
        height: float,
        **kwargs
    ) -> Dict[str, Any]:
        """
        기본 요소 딕셔너리를 생성한다.

        Args:
            element_type: 요소 유형 (rectangle, ellipse, diamond, text, arrow, line)
            x, y: 위치 좌표
            width, height: 크기
            **kwargs: 추가 속성

        Returns:
            Dict: Excalidraw 요소 딕셔너리
        """
        element_id = kwargs.pop('id', generate_id())

        element = {
            'id': element_id,
            'type': element_type,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'angle': 0,
            'strokeColor': kwargs.get('strokeColor', self.theme['strokeColor']),
            'backgroundColor': kwargs.get('backgroundColor', self.theme['backgroundColor']),
            'fillStyle': kwargs.get('fillStyle', DEFAULT_FILL_STYLE),
            'strokeWidth': kwargs.get('strokeWidth', 2),
            'strokeStyle': kwargs.get('strokeStyle', 'solid'),
            'roughness': kwargs.get('roughness', 1),
            'opacity': kwargs.get('opacity', 100),
            'groupIds': kwargs.get('groupIds', []),
            'frameId': kwargs.get('frameId', None),
            'roundness': kwargs.get('roundness', {'type': 3}),
            'seed': generate_seed(),
            'version': 1,
            'versionNonce': generate_seed(),
            'isDeleted': False,
            'boundElements': kwargs.get('boundElements', None),
            'updated': 1,
            'link': kwargs.get('link', None),
            'locked': kwargs.get('locked', False),
        }

        return element

    def add_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        text: Optional[str] = None,
        **kwargs
    ) -> 'ExcalidrawBuilder':
        """
        사각형 요소를 추가한다.

        Args:
            x, y: 위치 좌표
            width, height: 크기
            text: 내부 텍스트 (선택)
            **kwargs: 추가 스타일 속성

        Returns:
            ExcalidrawBuilder: 메서드 체이닝을 위한 self
        """
        rect_id = kwargs.pop('id', generate_id())
        bound_elements = []

        if text:
            text_id = generate_id()
            bound_elements.append({'id': text_id, 'type': 'text'})

        rect = self._create_base_element(
            'rectangle', x, y, width, height,
            id=rect_id,
            boundElements=bound_elements if bound_elements else None,
            **kwargs
        )
        self.elements.append(rect)
        self._element_map[rect_id] = rect

        if text:
            self._add_bound_text(rect_id, text_id, text, x, y, width, height, **kwargs)

        return self

    def add_ellipse(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        text: Optional[str] = None,
        **kwargs
    ) -> 'ExcalidrawBuilder':
        """
        타원 요소를 추가한다.

        Args:
            x, y: 위치 좌표
            width, height: 크기
            text: 내부 텍스트 (선택)
            **kwargs: 추가 스타일 속성

        Returns:
            ExcalidrawBuilder: 메서드 체이닝을 위한 self
        """
        ellipse_id = kwargs.pop('id', generate_id())
        bound_elements = []

        if text:
            text_id = generate_id()
            bound_elements.append({'id': text_id, 'type': 'text'})

        ellipse = self._create_base_element(
            'ellipse', x, y, width, height,
            id=ellipse_id,
            boundElements=bound_elements if bound_elements else None,
            **kwargs
        )
        self.elements.append(ellipse)
        self._element_map[ellipse_id] = ellipse

        if text:
            self._add_bound_text(ellipse_id, text_id, text, x, y, width, height, **kwargs)

        return self

    def add_diamond(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        text: Optional[str] = None,
        **kwargs
    ) -> 'ExcalidrawBuilder':
        """
        마름모 요소를 추가한다.

        Args:
            x, y: 위치 좌표
            width, height: 크기
            text: 내부 텍스트 (선택)
            **kwargs: 추가 스타일 속성

        Returns:
            ExcalidrawBuilder: 메서드 체이닝을 위한 self
        """
        diamond_id = kwargs.pop('id', generate_id())
        bound_elements = []

        if text:
            text_id = generate_id()
            bound_elements.append({'id': text_id, 'type': 'text'})

        diamond = self._create_base_element(
            'diamond', x, y, width, height,
            id=diamond_id,
            boundElements=bound_elements if bound_elements else None,
            **kwargs
        )
        self.elements.append(diamond)
        self._element_map[diamond_id] = diamond

        if text:
            self._add_bound_text(diamond_id, text_id, text, x, y, width, height, **kwargs)

        return self

    def _add_bound_text(
        self,
        container_id: str,
        text_id: str,
        text: str,
        x: float,
        y: float,
        width: float,
        height: float,
        **kwargs
    ) -> None:
        """
        컨테이너에 바인딩된 텍스트를 추가한다.

        Args:
            container_id: 컨테이너 요소 ID
            text_id: 텍스트 요소 ID
            text: 텍스트 내용
            x, y: 컨테이너 위치
            width, height: 컨테이너 크기
            **kwargs: 추가 스타일 속성
        """
        font_size = kwargs.get('fontSize', 20)
        text_width, text_height = calculate_text_dimensions(text, font_size)

        # 텍스트를 컨테이너 중앙에 배치
        text_x = x + (width - text_width) / 2
        text_y = y + (height - text_height) / 2

        text_element = {
            'id': text_id,
            'type': 'text',
            'x': text_x,
            'y': text_y,
            'width': text_width,
            'height': text_height,
            'angle': 0,
            'strokeColor': kwargs.get('textColor', self.theme['textColor']),
            'backgroundColor': 'transparent',
            'fillStyle': 'solid',
            'strokeWidth': 1,
            'strokeStyle': 'solid',
            'roughness': 1,
            'opacity': 100,
            'groupIds': kwargs.get('groupIds', []),
            'frameId': kwargs.get('frameId', None),
            'roundness': None,
            'seed': generate_seed(),
            'version': 1,
            'versionNonce': generate_seed(),
            'isDeleted': False,
            'boundElements': None,
            'updated': 1,
            'link': None,
            'locked': False,
            'text': text,
            'fontSize': font_size,
            'fontFamily': kwargs.get('fontFamily', FONT_FAMILIES['hand']),
            'textAlign': 'center',
            'verticalAlign': 'middle',
            'baseline': font_size,
            'containerId': container_id,
            'originalText': text,
            'lineHeight': 1.25,
        }
        self.elements.append(text_element)
        self._element_map[text_id] = text_element

    def add_text(
        self,
        x: float,
        y: float,
        text: str,
        **kwargs
    ) -> 'ExcalidrawBuilder':
        """
        독립 텍스트 요소를 추가한다.

        Args:
            x, y: 위치 좌표
            text: 텍스트 내용
            **kwargs: 추가 스타일 속성

        Returns:
            ExcalidrawBuilder: 메서드 체이닝을 위한 self
        """
        text_id = kwargs.pop('id', generate_id())
        font_size = kwargs.get('fontSize', 20)
        text_width, text_height = calculate_text_dimensions(text, font_size)

        text_element = {
            'id': text_id,
            'type': 'text',
            'x': x,
            'y': y,
            'width': text_width,
            'height': text_height,
            'angle': 0,
            'strokeColor': kwargs.get('textColor', self.theme['textColor']),
            'backgroundColor': 'transparent',
            'fillStyle': 'solid',
            'strokeWidth': 1,
            'strokeStyle': 'solid',
            'roughness': 1,
            'opacity': 100,
            'groupIds': kwargs.get('groupIds', []),
            'frameId': kwargs.get('frameId', None),
            'roundness': None,
            'seed': generate_seed(),
            'version': 1,
            'versionNonce': generate_seed(),
            'isDeleted': False,
            'boundElements': None,
            'updated': 1,
            'link': None,
            'locked': False,
            'text': text,
            'fontSize': font_size,
            'fontFamily': kwargs.get('fontFamily', FONT_FAMILIES['hand']),
            'textAlign': kwargs.get('textAlign', 'left'),
            'verticalAlign': kwargs.get('verticalAlign', 'top'),
            'baseline': font_size,
            'containerId': None,
            'originalText': text,
            'lineHeight': 1.25,
        }
        self.elements.append(text_element)
        self._element_map[text_id] = text_element

        return self

    def add_arrow(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        label: Optional[str] = None,
        start_binding: Optional[str] = None,
        end_binding: Optional[str] = None,
        **kwargs
    ) -> 'ExcalidrawBuilder':
        """
        화살표를 추가한다.

        Args:
            start: 시작 좌표 (x, y)
            end: 끝 좌표 (x, y)
            label: 화살표 라벨 (선택)
            start_binding: 시작점에 연결할 요소 ID (선택)
            end_binding: 끝점에 연결할 요소 ID (선택)
            **kwargs: 추가 스타일 속성
                - startArrowhead: 시작점 화살표 타입 (None, 'arrow', 'triangle', 'dot', 'bar', 'diamond')
                - endArrowhead: 끝점 화살표 타입 (기본: 'arrow')
                - strokeColor, strokeWidth, strokeStyle, roughness 등

        Returns:
            ExcalidrawBuilder: 메서드 체이닝을 위한 self

        화살표 끝점 타입:
            - None: 끝점 없음
            - 'arrow': 기본 화살표
            - 'triangle': 채워진 삼각형
            - 'dot': 원형 끝점
            - 'bar': 직선 막대
            - 'diamond': 마름모 끝점
        """
        arrow_id = kwargs.pop('id', generate_id())

        # 화살표의 점들 계산
        x = start[0]
        y = start[1]
        width = end[0] - start[0]
        height = end[1] - start[1]

        # 바인딩 정보 구성
        start_binding_obj = None
        end_binding_obj = None

        if start_binding and start_binding in self._element_map:
            start_element = self._element_map[start_binding]
            start_binding_obj = {
                'elementId': start_binding,
                'focus': 0,
                'gap': 8
            }
            # 시작 요소에 arrow 바인딩 추가
            if start_element.get('boundElements') is None:
                start_element['boundElements'] = []
            start_element['boundElements'].append({'id': arrow_id, 'type': 'arrow'})

        if end_binding and end_binding in self._element_map:
            end_element = self._element_map[end_binding]
            end_binding_obj = {
                'elementId': end_binding,
                'focus': 0,
                'gap': 8
            }
            # 끝 요소에 arrow 바인딩 추가
            if end_element.get('boundElements') is None:
                end_element['boundElements'] = []
            end_element['boundElements'].append({'id': arrow_id, 'type': 'arrow'})

        bound_elements = []
        if label:
            label_id = generate_id()
            bound_elements.append({'id': label_id, 'type': 'text'})

        arrow = {
            'id': arrow_id,
            'type': 'arrow',
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'angle': 0,
            'strokeColor': kwargs.get('strokeColor', self.theme['arrowColor']),
            'backgroundColor': 'transparent',
            'fillStyle': 'solid',
            'strokeWidth': kwargs.get('strokeWidth', 2),
            'strokeStyle': kwargs.get('strokeStyle', 'solid'),
            'roughness': kwargs.get('roughness', 1),
            'opacity': 100,
            'groupIds': kwargs.get('groupIds', []),
            'frameId': None,
            'roundness': {'type': 2},
            'seed': generate_seed(),
            'version': 1,
            'versionNonce': generate_seed(),
            'isDeleted': False,
            'boundElements': bound_elements if bound_elements else None,
            'updated': 1,
            'link': None,
            'locked': False,
            'points': [[0, 0], [width, height]],
            'lastCommittedPoint': None,
            'startBinding': start_binding_obj,
            'endBinding': end_binding_obj,
            'startArrowhead': kwargs.get('startArrowhead', None),
            'endArrowhead': kwargs.get('endArrowhead', 'arrow'),
        }
        self.elements.append(arrow)
        self._element_map[arrow_id] = arrow

        # 라벨 추가
        if label:
            label_x = x + width / 2 - 30
            label_y = y + height / 2 - 10
            self._add_arrow_label(arrow_id, label_id, label, label_x, label_y, **kwargs)

        return self

    def _add_arrow_label(
        self,
        arrow_id: str,
        label_id: str,
        text: str,
        x: float,
        y: float,
        **kwargs
    ) -> None:
        """
        화살표에 바인딩된 라벨을 추가한다.
        """
        font_size = kwargs.get('fontSize', 16)
        text_width, text_height = calculate_text_dimensions(text, font_size)

        label_element = {
            'id': label_id,
            'type': 'text',
            'x': x,
            'y': y,
            'width': text_width,
            'height': text_height,
            'angle': 0,
            'strokeColor': kwargs.get('textColor', self.theme['textColor']),
            'backgroundColor': 'transparent',
            'fillStyle': 'solid',
            'strokeWidth': 1,
            'strokeStyle': 'solid',
            'roughness': 1,
            'opacity': 100,
            'groupIds': [],
            'frameId': None,
            'roundness': None,
            'seed': generate_seed(),
            'version': 1,
            'versionNonce': generate_seed(),
            'isDeleted': False,
            'boundElements': None,
            'updated': 1,
            'link': None,
            'locked': False,
            'text': text,
            'fontSize': font_size,
            'fontFamily': kwargs.get('fontFamily', FONT_FAMILIES['hand']),
            'textAlign': 'center',
            'verticalAlign': 'middle',
            'baseline': font_size,
            'containerId': arrow_id,
            'originalText': text,
            'lineHeight': 1.25,
        }
        self.elements.append(label_element)
        self._element_map[label_id] = label_element

    def add_line(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        **kwargs
    ) -> 'ExcalidrawBuilder':
        """
        선을 추가한다.

        Args:
            start: 시작 좌표 (x, y)
            end: 끝 좌표 (x, y)
            **kwargs: 추가 스타일 속성

        Returns:
            ExcalidrawBuilder: 메서드 체이닝을 위한 self
        """
        line_id = kwargs.pop('id', generate_id())

        x = start[0]
        y = start[1]
        width = end[0] - start[0]
        height = end[1] - start[1]

        line = {
            'id': line_id,
            'type': 'line',
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'angle': 0,
            'strokeColor': kwargs.get('strokeColor', self.theme['arrowColor']),
            'backgroundColor': 'transparent',
            'fillStyle': 'solid',
            'strokeWidth': kwargs.get('strokeWidth', 2),
            'strokeStyle': kwargs.get('strokeStyle', 'solid'),
            'roughness': kwargs.get('roughness', 1),
            'opacity': 100,
            'groupIds': kwargs.get('groupIds', []),
            'frameId': None,
            'roundness': {'type': 2},
            'seed': generate_seed(),
            'version': 1,
            'versionNonce': generate_seed(),
            'isDeleted': False,
            'boundElements': None,
            'updated': 1,
            'link': None,
            'locked': False,
            'points': [[0, 0], [width, height]],
            'lastCommittedPoint': None,
            'startBinding': None,
            'endBinding': None,
            'startArrowhead': None,
            'endArrowhead': None,
        }
        self.elements.append(line)
        self._element_map[line_id] = line

        return self

    def add_group(self, element_ids: List[str]) -> str:
        """
        요소들을 그룹화한다.

        Args:
            element_ids: 그룹화할 요소 ID 목록

        Returns:
            str: 생성된 그룹 ID
        """
        group_id = generate_id()

        for elem_id in element_ids:
            if elem_id in self._element_map:
                element = self._element_map[elem_id]
                if 'groupIds' not in element:
                    element['groupIds'] = []
                element['groupIds'].append(group_id)

        return group_id

    def add_frame(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        name: str = ''
    ) -> str:
        """
        프레임을 추가한다.

        Args:
            x, y: 위치 좌표
            width, height: 크기
            name: 프레임 이름

        Returns:
            str: 생성된 프레임 ID
        """
        frame_id = generate_id()

        frame = {
            'id': frame_id,
            'type': 'frame',
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'angle': 0,
            'strokeColor': '#bbb',
            'backgroundColor': 'transparent',
            'fillStyle': 'solid',
            'strokeWidth': 1,
            'strokeStyle': 'solid',
            'roughness': 0,
            'opacity': 100,
            'groupIds': [],
            'frameId': None,
            'roundness': None,
            'seed': generate_seed(),
            'version': 1,
            'versionNonce': generate_seed(),
            'isDeleted': False,
            'boundElements': None,
            'updated': 1,
            'link': None,
            'locked': False,
            'name': name,
        }
        self.elements.append(frame)
        self._element_map[frame_id] = frame

        return frame_id

    def get_element(self, element_id: str) -> Optional[Dict[str, Any]]:
        """
        ID로 요소를 조회한다.

        Args:
            element_id: 요소 ID

        Returns:
            Dict or None: 요소 딕셔너리 또는 None
        """
        return self._element_map.get(element_id)

    def clear(self) -> 'ExcalidrawBuilder':
        """
        모든 요소를 초기화한다.

        Returns:
            ExcalidrawBuilder: 메서드 체이닝을 위한 self
        """
        self.elements = []
        self._element_map = {}
        return self

    def to_json(self) -> Dict[str, Any]:
        """
        Excalidraw JSON 객체를 반환한다.

        Returns:
            Dict: Excalidraw JSON 딕셔너리
        """
        return {
            'type': 'excalidraw',
            'version': 2,
            'source': 'https://excalidraw.com',
            'elements': self.elements,
            'appState': {
                'viewBackgroundColor': self.theme['background'],
                'gridSize': None,
                'theme': 'dark' if self.theme_name == 'dark' else 'light',
            },
            'files': self.files
        }

    def save(self, filename: str = None, output_dir: str = None) -> str:
        """
        Excalidraw 파일을 저장한다.

        Args:
            filename: 파일명 (확장자 제외, 기본: 자동 생성)
            output_dir: 출력 디렉토리 (기본: 9_Attachments/images/{YYYYMM}/)

        Returns:
            str: 저장된 파일의 절대 경로
        """
        # 출력 디렉토리 결정
        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = get_output_dir()

        # 파일명 생성
        if filename:
            if not filename.endswith('.excalidraw'):
                full_filename = generate_filename(filename)
            else:
                full_filename = filename
        else:
            full_filename = generate_filename()

        # 전체 경로
        file_path = out_dir / full_filename

        # JSON 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_json(), f, ensure_ascii=False, indent=2)

        # 옵시디언 삽입 코드 출력
        vault_root = get_vault_root()
        try:
            relative_path = file_path.relative_to(vault_root)
            obsidian_path = str(relative_path).replace('\\', '/')
            print(f"[OK] Excalidraw 저장 완료: {file_path}")
            print(f"[INFO] 옵시디언 삽입: ![[{obsidian_path}]]")
        except ValueError:
            print(f"[OK] Excalidraw 저장 완료: {file_path}")

        return str(file_path)


# 편의 함수
def create_mindmap(nodes: List[Dict], theme: str = 'minimal', filename: str = None) -> str:
    """
    마인드맵을 생성하는 편의 함수.
    실제 레이아웃은 layouts.py의 layout_mindmap 사용 권장.

    Args:
        nodes: 노드 데이터 리스트
        theme: 테마 이름
        filename: 파일명

    Returns:
        str: 저장된 파일 경로
    """
    from .layouts import layout_mindmap
    builder = ExcalidrawBuilder(theme=theme)
    layout_mindmap(builder, nodes)
    return builder.save(filename)


def create_flowchart(nodes: List[Dict], edges: List[Tuple], theme: str = 'minimal', filename: str = None) -> str:
    """
    플로우차트를 생성하는 편의 함수.
    실제 레이아웃은 layouts.py의 layout_flowchart 사용 권장.

    Args:
        nodes: 노드 데이터 리스트
        edges: 엣지 (연결) 리스트
        theme: 테마 이름
        filename: 파일명

    Returns:
        str: 저장된 파일 경로
    """
    from .layouts import layout_flowchart
    builder = ExcalidrawBuilder(theme=theme)
    layout_flowchart(builder, nodes, edges)
    return builder.save(filename)


if __name__ == '__main__':
    # 간단한 테스트
    builder = ExcalidrawBuilder(theme='clean')

    # 테스트 다이어그램 생성
    rect1_id = generate_id()
    rect2_id = generate_id()

    (builder
        .add_rectangle(100, 100, 150, 60, text='시작', id=rect1_id, backgroundColor='#D1FAE5')
        .add_rectangle(100, 250, 150, 60, text='종료', id=rect2_id, backgroundColor='#FEE2E2')
        .add_arrow((175, 160), (175, 250), start_binding=rect1_id, end_binding=rect2_id))

    # JSON 출력
    import json
    print(json.dumps(builder.to_json(), ensure_ascii=False, indent=2)[:500])
    print("...")
