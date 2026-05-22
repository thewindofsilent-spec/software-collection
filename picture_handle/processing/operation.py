from __future__ import annotations

from copy import deepcopy
from typing import Any, ClassVar, Dict, Iterable, Mapping, Optional

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QWidget,
)


ParameterValue = int | float | str | bool
ParameterDict = Dict[str, ParameterValue]


class OperationError(RuntimeError):
    """Raised when an image operation fails."""


class Operation(QObject):
    """Base class for all pipeline image operations.

    Subclasses should define:
        - operation_type: stable serialization key
        - name: human-readable display name
        - default_parameters: default parameter values
        - parameter_specs: UI metadata for get_widget()

    Undo strategy:
        Operation itself is stateless with respect to undo. The Pipeline records
        every intermediate image after each operation, so undo can restore the
        previous snapshot without trying to mathematically invert an operation.
    """

    parameterChanged = Signal(dict)

    operation_type: ClassVar[str] = "Operation"
    name: ClassVar[str] = "Operation"
    default_parameters: ClassVar[ParameterDict] = {}
    parameter_specs: ClassVar[Dict[str, Dict[str, Any]]] = {}

    def __init__(self, parameters: Optional[Mapping[str, ParameterValue]] = None) -> None:
        super().__init__()
        self.parameters: ParameterDict = deepcopy(self.default_parameters)
        if parameters:
            self.parameters.update(dict(parameters))

    def apply(self, mat: np.ndarray) -> np.ndarray:
        """Apply this operation and return a new image."""
        raise NotImplementedError("Operation 子类必须实现 apply() 方法")

    def get_widget(self) -> QWidget:
        """Return a QWidget for editing operation parameters.

        The default implementation builds a compact form from parameter_specs.
        Subclasses may override this for richer custom controls.
        """

        panel = QWidget()
        layout = QFormLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        for key, value in self.parameters.items():
            spec = self.parameter_specs.get(key, {})
            label = str(spec.get("label", key.replace("_", " ").title()))
            widget = self._create_parameter_editor(key, value, spec)
            layout.addRow(label, widget)

        return panel

    def set_parameter(self, key: str, value: ParameterValue) -> None:
        if key not in self.parameters:
            raise KeyError(f"未知参数：{key}")
        self.parameters[key] = value
        self.parameterChanged.emit(deepcopy(self.parameters))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.operation_type,
            "name": self.name,
            "parameters": deepcopy(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Operation":
        parameters = data.get("parameters", {})
        if not isinstance(parameters, Mapping):
            raise ValueError("操作参数必须是字典结构")
        return cls(parameters=parameters)

    def clone(self) -> "Operation":
        return self.from_dict(self.to_dict())

    def _create_parameter_editor(
        self,
        key: str,
        value: ParameterValue,
        spec: Mapping[str, Any],
    ) -> QWidget:
        kind = str(spec.get("type", self._infer_editor_type(value)))

        if kind == "int":
            editor = QSpinBox()
            editor.setRange(int(spec.get("min", -999_999)), int(spec.get("max", 999_999)))
            editor.setSingleStep(int(spec.get("step", 1)))
            editor.setValue(int(value))
            editor.valueChanged.connect(lambda new_value, k=key: self.set_parameter(k, int(new_value)))
            return editor

        if kind == "float":
            editor = QDoubleSpinBox()
            editor.setRange(float(spec.get("min", -999_999.0)), float(spec.get("max", 999_999.0)))
            editor.setSingleStep(float(spec.get("step", 0.1)))
            editor.setDecimals(int(spec.get("decimals", 3)))
            editor.setValue(float(value))
            editor.valueChanged.connect(lambda new_value, k=key: self.set_parameter(k, float(new_value)))
            return editor

        if kind == "bool":
            editor = QCheckBox()
            editor.setChecked(bool(value))
            editor.toggled.connect(lambda checked, k=key: self.set_parameter(k, bool(checked)))
            return editor

        if kind == "choice":
            editor = QComboBox()
            options: Iterable[str] = spec.get("options", [])
            for option in options:
                editor.addItem(str(option))
            index = editor.findText(str(value))
            editor.setCurrentIndex(max(index, 0))
            editor.currentTextChanged.connect(lambda text, k=key: self.set_parameter(k, text))
            return editor

        editor = QComboBox()
        editor.addItem(str(value))
        return editor

    @staticmethod
    def _infer_editor_type(value: ParameterValue) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        return "choice"
