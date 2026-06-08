"""
适配器模块

提供解析器工厂和适配器注册机制
"""
from typing import Dict, Type

from .parser import TraceParser
from .rubis import RUBISParser
from .bsn import BSNParser
from .swat import SWATParser
from .wadi import WADIParser


class ParserFactory:
    """解析器工厂

    根据系统类型创建相应的解析器
    """

    # 解析器注册表
    _registry: Dict[str, Type[TraceParser]] = {
        'rubis': RUBISParser,
        'bsn': BSNParser,
        'swat': SWATParser,
        'wadi': WADIParser
    }

    @classmethod
    def create(cls, system_type: str, **parser_kwargs) -> TraceParser:
        """根据系统类型创建解析器

        Args:
            system_type: 系统类型（'rubis', 'bsn', 'swat' 或 'wadi'）

        Returns:
            TraceParser实例

        Raises:
            ValueError: 未知的系统类型
        """
        parser_class = cls._registry.get(system_type)
        if not parser_class:
            supported_types = list(cls._registry.keys())
            raise ValueError(f"未知系统类型: {system_type}，支持的类型: {supported_types}")

        return parser_class(**parser_kwargs)

    @classmethod
    def register(cls, system_type: str, parser_class: Type[TraceParser]) -> None:
        """注册新的解析器

        用于扩展框架，添加新的数据集支持

        Args:
            system_type: 系统类型标识
            parser_class: 解析器类（需继承TraceParser）
        """
        cls._registry[system_type] = parser_class

    @classmethod
    def list_supported_types(cls) -> list:
        """列出所有支持的系统类型

        Returns:
            系统类型列表
        """
        return list(cls._registry.keys())


__all__ = ['ParserFactory', 'RUBISParser', 'BSNParser', 'SWATParser', 'WADIParser']
