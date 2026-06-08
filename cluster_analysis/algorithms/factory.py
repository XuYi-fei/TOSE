"""
聚类算法工厂

提供算法注册、创建和管理功能
"""
from typing import Dict, Type, List, Optional
import logging
from .base import ClusteringAlgorithm

logger = logging.getLogger(__name__)


class ClusteringFactory:
    """聚类算法工厂类

    管理所有可用的聚类算法，支持动态注册和创建
    """

    # 算法注册表: {algorithm_name: AlgorithmClass}
    _registry: Dict[str, Type[ClusteringAlgorithm]] = {}

    @classmethod
    def register(cls, name: str, algorithm_class: Type[ClusteringAlgorithm]) -> None:
        """注册聚类算法

        Args:
            name: 算法名称（小写）
            algorithm_class: 算法类（必须继承ClusteringAlgorithm）

        Raises:
            ValueError: 算法类未继承ClusteringAlgorithm
        """
        if not issubclass(algorithm_class, ClusteringAlgorithm):
            raise ValueError(f"{algorithm_class.__name__}必须继承ClusteringAlgorithm")

        cls._registry[name.lower()] = algorithm_class
        logger.debug(f"已注册聚类算法: {name}")

    @classmethod
    def create(cls, name: str, **kwargs) -> ClusteringAlgorithm:
        """创建聚类算法实例

        Args:
            name: 算法名称
            **kwargs: 算法参数

        Returns:
            算法实例

        Raises:
            ValueError: 算法未注册
        """
        name_lower = name.lower()

        if name_lower not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise ValueError(
                f"未知的聚类算法: {name}。"
                f"可用算法: {available}"
            )

        algorithm_class = cls._registry[name_lower]
        return algorithm_class(name=name, **kwargs)

    @classmethod
    def list_algorithms(cls) -> List[str]:
        """列出所有已注册的算法名称

        Returns:
            算法名称列表
        """
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查算法是否已注册

        Args:
            name: 算法名称

        Returns:
            是否已注册
        """
        return name.lower() in cls._registry

    @classmethod
    def clear_registry(cls) -> None:
        """清空注册表（主要用于测试）"""
        cls._registry.clear()
        logger.debug("聚类算法注册表已清空")


# 自动注册内置算法的装饰器
def register_algorithm(name: str):
    """算法注册装饰器

    用法:
        @register_algorithm('hdbscan')
        class HDBSCANAlgorithm(ClusteringAlgorithm):
            ...

    Args:
        name: 算法名称
    """
    def decorator(algorithm_class: Type[ClusteringAlgorithm]):
        ClusteringFactory.register(name, algorithm_class)
        return algorithm_class
    return decorator
