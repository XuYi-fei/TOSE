# Anomaly Detection Reporting Spec

## ADDED Requirements

### Requirement: FP/FN性能指标计算
**ID**: ADR-001
**Priority**: High

系统SHALL准确计算并报告异常检测的性能指标，包括混淆矩阵、FP率、FN率、精确率、召回率等。

#### Scenario: 计算单个trace的混淆矩阵
**Given** trace包含2段：norm1(0-1000s, 500个点), abn1(1000-2000s, 500个点)
**And** norm1段中检测到10个异常点（FP）
**And** norm1段中490个点正常（TN）
**And** abn1段中检测到450个异常点（TP）
**And** abn1段中50个点未检测到（FN）
**When** 计算混淆矩阵
**Then** TP=450, FP=10, TN=490, FN=50
**And** Precision = TP/(TP+FP) = 450/460 = 0.978
**And** Recall = TP/(TP+FN) = 450/500 = 0.900
**And** F1 = 2*P*R/(P+R) = 0.937
**And** FP_rate = FP/(FP+TN) = 10/500 = 0.020
**And** FN_rate = FN/(TP+FN) = 50/500 = 0.100

#### Scenario: 处理无异常段的trace
**Given** trace只包含正常段（norm1, norm2, norm3）
**And** 检测到5个误报点
**When** 计算混淆矩阵
**Then** TP=0, FP=5, TN=(总点数-5), FN=0
**And** Precision=0 (无真阳性)
**And** Recall=undefined (除零，应处理为N/A)
**And** FP_rate = 5/总点数

#### Scenario: 处理全异常段的trace
**Given** trace只包含异常段abn1
**And** 检测到900个异常点，漏检100个
**When** 计算混淆矩阵
**Then** TP=900, FP=0, TN=0, FN=100
**And** Precision=1.0 (无误报)
**And** Recall=0.900
**And** FN_rate=0.100

---

### Requirement: 聚合多trace的统计结果
**ID**: ADR-002
**Priority**: High

系统SHALL聚合所有trace文件的检测结果，计算总体性能指标。

#### Scenario: 聚合200个trace的结果
**Given** 检测了200个trace文件
**And** 每个trace计算了独立的TP/FP/TN/FN
**When** 聚合所有结果
**Then** 总TP = sum(所有trace的TP)
**And** 总FP = sum(所有trace的FP)
**And** 总TN = sum(所有trace的TN)
**And** 总FN = sum(所有trace的FN)
**And** 总体Precision = 总TP/(总TP+总FP)
**And** 总体Recall = 总TP/(总TP+总FN)

#### Scenario: 计算平均检测延迟
**Given** 200个trace文件，其中180个包含异常段
**And** 每个异常trace记录了检测延迟（秒）
**When** 聚合结果
**Then** 平均检测延迟 = sum(所有延迟) / 180
**And** 最小检测延迟 = min(所有延迟)
**And** 最大检测延迟 = max(所有延迟)
**And** 应过滤未检测到的trace（延迟=无穷大）

#### Scenario: 计算检测成功率
**Given** 200个trace文件，其中180个包含异常段
**And** 150个trace成功检测到异常（TP>0）
**And** 30个trace完全漏检（FN=异常段点数）
**When** 聚合结果
**Then** 检测成功率 = 150/180 = 83.3%
**And** 完全漏检率 = 30/180 = 16.7%

---

### Requirement: 生成Markdown格式报告
**ID**: ADR-003
**Priority**: High

系统SHALL生成详细的Markdown格式检测报告，包含性能指标、案例展示和统计分析。

#### Scenario: 报告包含检测概览
**Given** 检测完成
**When** 生成报告
**Then** 报告应包含"检测概览"部分
**And** 显示系统类型、测试数据路径
**And** 显示总trace数、包含异常的trace数
**And** 显示检测阈值(sigma_threshold)
**And** 显示处理时间

#### Scenario: 报告包含性能指标表格
**Given** 检测完成
**When** 生成报告
**Then** 报告应包含"性能指标"部分
**And** 表格显示：TP, FP, TN, FN, Precision, Recall, F1, FP_rate, FN_rate
**And** 每个指标应有数值和百分比（如适用）
**And** 应高亮关键指标（如FP_rate < 5%为绿色）

#### Scenario: 报告包含检测延迟统计
**Given** 检测完成
**When** 生成报告
**Then** 报告应包含"检测延迟分析"部分
**And** 显示平均、最小、最大检测延迟
**And** 显示延迟分布直方图（如果生成了可视化）
**And** 列出前10个延迟最长的trace

#### Scenario: 报告包含异常案例展示
**Given** 检测到异常trace
**When** 生成报告
**Then** 报告应包含"异常案例"部分
**And** 展示前10个最典型的异常trace
**And** 每个案例显示：文件名、异常点数、首次检测时间、检测延迟
**And** 包含指向详细时间线图的链接（如果生成了）

---

### Requirement: 生成可视化图表
**ID**: ADR-004
**Priority**: Medium

系统SHALL生成可视化图表辅助理解检测结果。

#### Scenario: 绘制检测时间线图
**Given** 某个trace包含异常段
**When** 生成可视化
**Then** 应生成时间线散点图
**And** X轴为时间，Y轴为响应时间值
**And** 不同段用不同颜色标记（norm1=蓝, norm2=绿, abn1=红）
**And** 检测到的异常点用红色X标记
**And** 标注异常段开始时间（垂直虚线）
**And** 图表标题包含文件名和检测统计

#### Scenario: 绘制混淆矩阵热力图
**Given** 检测完成
**When** 生成可视化
**Then** 应生成混淆矩阵热力图
**And** 2x2矩阵显示TP, FP, TN, FN
**And** 颜色深浅表示数值大小
**And** 每个格子显示数值和百分比

#### Scenario: 绘制检测延迟分布图
**Given** 检测完成，有多个trace包含异常
**When** 生成可视化
**Then** 应生成检测延迟直方图
**And** X轴为延迟时间（秒），Y轴为trace数量
**And** 显示平均延迟线（垂直虚线）
**And** 标注最小和最大延迟

#### Scenario: 绘制FP/FN率对比图
**Given** 检测完成
**When** 生成可视化
**Then** 应生成柱状图对比FP率和FN率
**And** 标注目标线（如FP<5%, FN<10%）
**And** 超过目标用红色，达标用绿色

---

### Requirement: 保存异常点详细信息
**ID**: ADR-005
**Priority**: Medium

系统SHALL可选地保存所有异常点的详细信息为CSV格式，供进一步分析。

#### Scenario: 生成anomaly_points.csv
**Given** 配置启用save_anomaly_points
**When** 检测完成
**Then** 应生成anomaly_points.csv文件
**And** 包含列：filename, time, value, segment_label, is_anomaly, closest_distribution, z_scores
**And** 每行对应一个检测到的异常点

#### Scenario: CSV格式正确可导入
**Given** 已生成anomaly_points.csv
**When** 使用pandas读取
**Then** 应成功解析所有行
**And** z_scores应为JSON格式字符串（可解析为字典）
**And** 数值字段应为float类型

---

### Requirement: 中文报告支持
**ID**: ADR-006
**Priority**: Low

生成的报告SHALL支持中文标题和说明，与现有可视化风格一致。

#### Scenario: 报告标题和章节名中文化
**Given** 生成检测报告
**When** 查看报告内容
**Then** 章节标题应为中文（检测概览、性能指标、异常案例等）
**And** 表格标题应为中文（准确率、召回率等）
**And** 图表标题应为中文

#### Scenario: 可视化图表中文化
**Given** 生成可视化图表
**When** 查看图表
**Then** 轴标签应为中文（时间、响应时间、数量等）
**And** 图例应为中文（正常、异常、检测点等）
**And** 标题应为中文
