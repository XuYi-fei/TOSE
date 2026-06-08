# Proposal: 添加异常检测框架

## 问题陈述

当前系统包含聚类分析框架用于从trace数据中自动发现分布参数，但缺少以下关键能力：

1. **聚类结果无法持久化**：聚类发现的分布参数只存在于内存和报告中，无法被其他模块重用
2. **缺少异常检测能力**：无法基于已知分布检测未知trace数据中的异常行为
3. **无法评估检测性能**：缺少FP（假阳性）/FN（假阴性）统计机制

这导致无法完成"辨识→检测"的完整工作流程。

## 变更内容

本提案在现有聚类框架基础上，添加以下功能：

### 1. 聚类结果持久化 (Clustering Result Persistence)
- 将聚类发现的分布参数自动保存为YAML配置文件
- 配置文件格式与validation框架兼容
- 支持保存多个算法的结果供用户选择

### 2. 异常检测引擎 (Anomaly Detection Engine)
- 读取聚类结果配置，初始化已知分布参数
- 实时读取trace数据，逐点计算偏离度
- 使用3-sigma规则检测异常（超出所有已知分布3倍标准差）
- 支持RUBIS和BSN两种系统类型
- 可扩展到其他系统类型

### 3. 异常检测配置 (Anomaly Detection Config)
- YAML配置文件指定：
  - 系统类型（rubis/bsn）
  - 聚类结果路径（learned_distributions）
  - 测试数据路径（eval_abn_traces）
  - 异常检测阈值（sigma倍数，默认3）
  - 输出目录

### 4. 异常检测报告 (Anomaly Detection Reporting)
- 记录每个trace文件的异常检测结果
- 统计FP/FN率：
  - FP：正常段被误判为异常的比例
  - FN：异常段未被检测出的比例
- 生成详细Markdown报告和可视化图表
- 显示检测延迟（从异常开始到检测出的时间）

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│  1. Clustering Phase (Discovery)                    │
│     cluster.py → ClusteringEngine                   │
│     ├─ 发现分布参数                                  │
│     └─ 保存为 learned_distributions.yaml           │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓ learned_distributions.yaml
┌─────────────────────────────────────────────────────┐
│  2. Detection Phase (Anomaly Detection)             │
│     detect.py → AnomalyDetector                     │
│     ├─ 加载已知分布                                  │
│     ├─ 实时读取trace数据                             │
│     ├─ 3-sigma异常判定                               │
│     └─ 记录异常位置、FP/FN统计                        │
└─────────────────────────────────────────────────────┘
```

## 数据格式

### 聚类结果配置 (learned_distributions.yaml)
```yaml
system_type: rubis
learned_at: "2024-01-15T23:44:00"
algorithm: hdbscan
silhouette_score: 0.9915

distributions:
  norm1:
    mu: 0.052544
    sigma: 0.002449  # sqrt(variance)
    sample_count: 164

  norm2:
    mu: 0.115244
    sigma: 0.012884
    sample_count: 174

  norm3:
    mu: 0.028450
    sigma: 0.001732
    sample_count: 166
```

### 异常trace文件格式
```
文件名示例：
eval_abn_trace-cnt-000-duration-64800-config_num-3-trace_config-norm3,norm1,abn1-start_time-960,23100,52740.txt

解析规则：
- trace_config: [norm3, norm1, abn1] （3个阶段）
- start_time: [960, 23100, 52740] （3个开始时间）
- abn1对应第3个时间点52740，预期在此处检测到异常
```

## 影响范围

### 新增模块
- `anomaly_detection/` 包（新增）
  - `core/detector.py`: 异常检测引擎
  - `core/evaluator.py`: FP/FN评估器
  - `config/config.py`: 检测配置
  - `visualization/reporter.py`: 检测报告生成器
  - `cli.py`: 命令行接口

- `detect.py` 脚本（新增）

### 修改模块
- `cluster_analysis/core/engine.py`: 添加结果保存逻辑
- `cluster_analysis/visualization/reporter.py`: 添加配置文件生成
- `common/adapters/`: 支持解析abn标签的trace文件

### 配置文件
- 新增 `configs/rubis_detection_config.yaml`
- 新增 `configs/bsn_detection_config.yaml`

## 成功标准

1. ✅ 聚类分析后自动生成`learned_distributions.yaml`配置文件
2. ✅ 检测框架能正确读取聚类结果配置
3. ✅ 支持RUBIS和BSN的abnormal trace文件解析
4. ✅ 正确识别abn1段并检测异常
5. ✅ 准确统计FP/FN率
6. ✅ 生成详细的检测报告（Markdown + 可视化）
7. ✅ <10秒完成200个trace文件的异常检测
8. ✅ 可扩展到其他系统类型

## 兼容性

- ✅ 不破坏现有validation和clustering框架
- ✅ 共享`common/`数据层
- ✅ 配置文件格式向后兼容
- ✅ 独立的CLI入口（detect.py）

## 风险与限制

1. **检测延迟**：实际检测可能晚于异常开始时间（数据点累积效应）
2. **3-sigma限制**：固定阈值可能不适合所有场景，未来可配置化
3. **分布假设**：假设数据服从高斯分布，非高斯数据可能误判
4. **单点检测**：当前逐点检测，未来可考虑滑动窗口

## 后续可能的扩展

1. 可配置的异常阈值（2-sigma, 3-sigma, 4-sigma）
2. 多种检测算法（Isolation Forest, LOF, DBSCAN outlier detection）
3. 滑动窗口检测（减少单点噪声影响）
4. 实时流式检测（当前是批处理）
5. 异常类型分类（幅值异常、趋势异常、周期异常）
