from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4

import numpy as np

from processing.operation import Operation, OperationError
from processing.registry import operation_from_dict


class PipelineError(RuntimeError):
    """Raised when a pipeline cannot be executed or modified."""


@dataclass
class PipelineStep:
    operation: Operation
    enabled: bool = True
    step_id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> Dict[str, Any]:
        data = self.operation.to_dict()
        data["enabled"] = self.enabled
        data["step_id"] = self.step_id
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PipelineStep":
        return cls(
            operation=operation_from_dict(data),
            enabled=bool(data.get("enabled", True)),
            step_id=str(data.get("step_id") or uuid4().hex),
        )


@dataclass
class PipelineRunResult:
    original: np.ndarray
    output: np.ndarray
    snapshots: List[np.ndarray]
    step_ids: List[str]

    def undo(self) -> np.ndarray:
        if len(self.snapshots) <= 1:
            return self.original.copy()
        self.snapshots.pop()
        self.step_ids.pop()
        return self.snapshots[-1].copy()


class Pipeline:
    """Ordered image processing pipeline with snapshot-based undo."""

    def __init__(self, steps: Optional[List[PipelineStep]] = None) -> None:
        self.steps: List[PipelineStep] = steps or []
        self._last_result: Optional[PipelineRunResult] = None

    def add(self, operation: Operation, index: Optional[int] = None, *, enabled: bool = True) -> str:
        step = PipelineStep(operation=operation, enabled=enabled)
        if index is None:
            self.steps.append(step)
        else:
            if index < 0 or index > len(self.steps):
                raise PipelineError(f"插入位置超出范围：{index}")
            self.steps.insert(index, step)
        return step.step_id

    def remove(self, step_id: str) -> PipelineStep:
        index = self.index_of(step_id)
        return self.steps.pop(index)

    def reorder(self, step_id: str, new_index: int) -> None:
        if new_index < 0 or new_index >= len(self.steps):
            raise PipelineError(f"新的位置超出范围：{new_index}")
        old_index = self.index_of(step_id)
        step = self.steps.pop(old_index)
        self.steps.insert(new_index, step)

    def set_enabled(self, step_id: str, enabled: bool) -> None:
        self.steps[self.index_of(step_id)].enabled = enabled

    def clear(self) -> None:
        self.steps.clear()
        self._last_result = None

    def execute(self, mat: np.ndarray, *, keep_snapshots: bool = True) -> np.ndarray:
        if mat is None or mat.size == 0:
            raise PipelineError("处理流程输入图像为空")

        current = mat.copy()
        snapshots: List[np.ndarray] = [current.copy()]
        step_ids: List[str] = ["original"]

        for step in self.steps:
            if not step.enabled:
                continue

            try:
                current = step.operation.apply(current)
            except Exception as exc:
                raise OperationError(f"处理步骤 {step.operation.name!r} 执行失败") from exc

            if keep_snapshots:
                snapshots.append(current.copy())
                step_ids.append(step.step_id)

        self._last_result = PipelineRunResult(
            original=mat.copy(),
            output=current.copy(),
            snapshots=snapshots if keep_snapshots else [mat.copy(), current.copy()],
            step_ids=step_ids if keep_snapshots else ["original", "output"],
        )
        return current

    def undo(self) -> np.ndarray:
        if self._last_result is None:
            raise PipelineError("当前没有可撤销内容，请先运行处理流程")
        return self._last_result.undo()

    def index_of(self, step_id: str) -> int:
        for index, step in enumerate(self.steps):
            if step.step_id == step_id:
                return index
        raise PipelineError(f"未找到处理步骤：{step_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Pipeline":
        steps_data = data.get("steps", [])
        if not isinstance(steps_data, list):
            raise ValueError("处理流程 steps 必须是列表")
        return cls(steps=[PipelineStep.from_dict(step_data) for step_data in steps_data])
