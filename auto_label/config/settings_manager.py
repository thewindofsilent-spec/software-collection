"""
配置管理器
负责保存和加载用户配置
"""

import os
import json
from typing import Dict, Any, Optional


class SettingsManager:
    """配置管理器，单例模式"""

    _instance = None
    _config_path: str = ""
    _config: Dict[str, Any] = {}

    # 默认配置
    DEFAULT_CONFIG = {
        # 训练参数
        "training": {
            "epochs": 100,
            "batch": 16,
            "imgsz": 640,
            "workers": 8,
            "patience": 50,
            "project": "runs/detect",
            "name": "train",
        },
        # 自动标注参数
        "auto_label": {
            "conf": 0.25,
            "iou": 0.45,
            "max_det": 300,
        },
        # 路径配置
        "paths": {
            "last_image_dir": "",
            "last_model_path": "",
            "last_output_dir": "",
            "last_dataset_yaml": "",
        },
        # 窗口配置
        "window": {
            "width": 1400,
            "height": 900,
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = cls._instance.DEFAULT_CONFIG.copy()
        return cls._instance

    def set_config_path(self, path: str):
        """设置配置文件路径"""
        self._config_path = path

    def get_config_path(self) -> str:
        """获取配置文件路径"""
        return self._config_path

    def load(self, path: Optional[str] = None) -> bool:
        """
        加载配置文件
        :param path: 配置文件路径，如果为None则使用之前设置的路径
        :return: 是否加载成功
        """
        if path:
            self._config_path = path

        if not self._config_path or not os.path.exists(self._config_path):
            # 如果没有配置文件或文件不存在，使用默认配置
            self._config = self.DEFAULT_CONFIG.copy()
            return False

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
                # 合并配置，保留默认配置中的所有键
                self._config = self._merge_config(self.DEFAULT_CONFIG, loaded_config)
            return True
        except Exception as e:
            print(f"配置加载错误: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
            return False

    def save(self, path: Optional[str] = None) -> bool:
        """
        保存配置文件
        :param path: 配置文件路径，如果为None则使用之前设置的路径
        :return: 是否保存成功
        """
        if path:
            self._config_path = path

        if not self._config_path:
            print("未设置配置文件路径")
            return False

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"配置保存错误: {e}")
            return False

    def _merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """递归合并配置"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的路径，如 "training.epochs"
        :param key_path: 配置路径
        :param default: 默认值
        :return: 配置值
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置值，支持点号分隔的路径
        :param key_path: 配置路径
        :param value: 配置值
        """
        keys = key_path.split(".")
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()

    def update(self, updates: Dict[str, Any]) -> None:
        """批量更新配置"""
        for key, value in updates.items():
            self.set(key, value)


# 全局配置管理器实例
settings = SettingsManager()
