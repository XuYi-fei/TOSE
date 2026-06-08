# 归档脚本说明

本目录包含已被新的通用验证框架替代的旧脚本。

## 归档文件

### rubis_data_revalidation.py
- **功能**: RUBIS数据验证
- **替代方案**: 使用 `python validate.py --config configs/rubis_config.yaml`
- **归档原因**: 功能已集成到通用框架中

### bsn_trace_analysis.py
- **功能**: BSN数据验证
- **替代方案**: 使用 `python validate.py --config configs/bsn_config.yaml`
- **归档原因**: 功能已集成到通用框架中

## 新框架优势

1. **统一接口**: 一个命令支持多种数据集
2. **配置驱动**: 无需修改代码即可切换参数
3. **易于扩展**: 添加新数据集只需实现适配器
4. **一致输出**: 报告格式统一，便于对比分析

## 迁移指南

详见[验证框架使用指南](../README_VALIDATION.md)

---
归档日期: 2026-01-14
