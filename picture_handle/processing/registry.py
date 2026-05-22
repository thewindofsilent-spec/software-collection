from __future__ import annotations

from typing import Any, Dict, Mapping, Type

from processing.background import BackgroundSubtractor
from processing.morphology import Dilate, Erode
from processing.operation import Operation


OPERATION_REGISTRY: Dict[str, Type[Operation]] = {
    Erode.operation_type: Erode,
    Dilate.operation_type: Dilate,
    BackgroundSubtractor.operation_type: BackgroundSubtractor,
}


def operation_from_dict(data: Mapping[str, Any]) -> Operation:
    operation_type = str(data.get("type", ""))
    operation_cls = OPERATION_REGISTRY.get(operation_type)
    if operation_cls is None:
        raise ValueError(f"未知操作类型：{operation_type}")
    return operation_cls.from_dict(data)
