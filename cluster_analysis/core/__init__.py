"""
聚类分析核心模块

提供聚类引擎、结果和配置的核心功能
"""
from .engine import ClusteringEngine
from .result import ClusteringResult

__all__ = ['ClusteringEngine', 'ClusteringResult']
