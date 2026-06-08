# BOCPD Detection Mode Design

## Context

当前统一异常检测框架已经支持：

- 从 `learned_distributions*.yaml` 读取已辨识分布
- 基于边缘概率做点级检测
- 基于 trace 级容忍计数做统一 `TP/FP/FN/TN` 评估
- 上下文匹配与 `mu` 线性校准

当前检测模式的核心是静态点级判别：每个点独立地和候选分布比较，然后由 trace 级容忍逻辑决定是否报警。

本次变更要新增一种 `BOCPD` 检测模式，使系统在保留统一评估和输出框架的前提下，显式维护：

- 运行长度后验 `P(r_t | x_1:t)`
- 变点后验 `P(r_t = 0 | x_1:t)`
- 当前 run 对各个已辨识分布的后验权重

目标不是实现一个独立的分段实验脚本，而是把 BOCPD 作为当前统一检测框架中的一种可切换检测模式。

## Goals

- 在现有 `detect.py` 主链路中新增 `detection.mode: bocpd`
- 复用现有 `learned_distributions`、上下文匹配和 trace 级评估逻辑
- 在不修改训练端输出格式的前提下，将论文中的 BOCPD 递推过程映射到“已知分布集合上的在线检测”
- 将 BOCPD 的状态和报警原因输出到 JSON/CSV/后续 HTML 分析链路

## Non-Goals

- 不替换当前 `pointwise` 检测模式
- 不修改当前聚类、二阶段分布拟合或 `learned_distributions.yaml` 的导出格式
- 不把 BOCPD 作为新的 clustering 算法加入 RQ1 的 4x4 聚类矩阵
- 不在第一版引入非恒定 hazard function、粒子近似或多步前瞻推断

## Approaches Considered

### Option 1: BOCPD as a segmentation preprocessor

先用 BOCPD 做变点检测与分段，再复用当前分布检测逻辑。

优点：

- 接近 `wadi-original` 中已有的参考代码
- 便于做段级可视化

缺点：

- 不能直接表达“当前点对已知分布解释概率很低，所以出现异常”
- 更像在线分段，而不是统一检测模式

### Option 2: BOCPD with best-match emission only

每个点只取当前最匹配分布的概率，直接驱动 BOCPD。

优点：

- 实现简单
- 和当前 `max_p_value` 语义接近

缺点：

- 不能维护 run 内“属于哪个已知分布”的后验权重
- BOCPD 会退化为“阈值化的低概率检测 + 变点平滑”

### Option 3: BOCPD over learned distributions with per-run state weights

对每个 run-length 假设，同时维护“该 run 属于哪些已知分布”的后验权重；BOCPD 的 predictive probability 由这些权重与候选分布 likelihood 加权得到。

优点：

- 最贴近论文中“对 run 的预测分布进行递推”的思想
- 能区分“正常切换到另一个已知分布”和“切换到无法解释的未知状态”
- 可以直接并入当前统一检测与评估框架

缺点：

- 实现复杂度高于单一 best-match 方案
- 需要新增 BOCPD 状态输出字段

## Decision

采用 Option 3。

第一版 BOCPD 检测模式保持以下原则：

- 训练端不变，只读取现有 `learned_distributions`
- 检测时先做上下文匹配，再对候选分布计算 likelihood 与 tail probability
- BOCPD 内部维护：
  - run-length posterior
  - changepoint posterior
  - per-run distribution posterior weights
- 点级 raw anomaly 默认采用联合条件：
  - `changepoint_probability >= threshold`
  - `best_tail_probability < alpha`
- trace 级报警仍复用现有容忍计数策略

## Detection Model

### Candidate distributions

对每个点 `x_t`，先复用当前检测链路中的上下文逻辑：

1. 按 `context_key` exact match 选候选分布
2. 若没有 exact match，则按 `context_features` 做 nearest 匹配
3. 若 learned YAML 顶层存在上下文校准模型，则对候选分布应用位置平移

因此，BOCPD 不直接在所有分布上做推断，而是在“当前上下文允许的候选分布集合”上做推断。

### Emission score

每个候选分布需要提供两个分数：

- `tail_probability`
  - 复用现有 `LearnedDistribution.tail_probability`
  - 用于异常语义判别
- `log_likelihood`
  - 由分布的 `pdf/logpdf` 计算得到
  - 用于 BOCPD 递推

`tail_probability` 和 `log_likelihood` 语义不同，不能混用。

### State prior

changepoint 分支在 run 重置时，需要为已知分布提供先验 `pi(k)`。

第一版支持两种模式：

- `uniform`
- `sample_count`

默认使用 `sample_count`，即按辨识阶段该分布对应的样本量归一化为先验权重。

## BOCPD Recursion

记：

- `R_t(r) = P(r_t = r | x_1:t)`
- `w_t(r, k) = P(z_t = k | r_t = r, x_1:t)`
- `D_k` 为第 `k` 个已知分布
- `H = 1 / hazard_lambda`

### Growth predictive probability

对于上一时刻的某个运行长度 `r`：

```text
pred_grow_t(r) = Σ_k w_{t-1}(r, k) * p(x_t | D_k)
```

### Changepoint predictive probability

当 run 在当前点重置时：

```text
pred_cp_t = Σ_k pi(k) * p(x_t | D_k)
```

### Run-length update

```text
R_t(r+1) ∝ R_{t-1}(r) * pred_grow_t(r) * (1 - H)
R_t(0)   ∝ Σ_r R_{t-1}(r) * pred_cp_t * H
```

之后对 `R_t` 做归一化。

### Distribution weight update

```text
w_t(r+1, k) ∝ w_{t-1}(r, k) * p(x_t | D_k)
w_t(0, k)   ∝ pi(k) * p(x_t | D_k)
```

之后对每个 `r` 下的 `w_t(r, :)` 做归一化。

### Truncation

第一版使用 `max_run_length` 截断状态长度，避免每条 trace 状态线性膨胀。

## Raw Anomaly Rules

第一版支持三种点级 raw anomaly 规则：

- `cp_and_tail`
- `cp_only`
- `tail_only`

默认规则为 `cp_and_tail`。

含义如下：

- `cp_only`
  - 只依赖 `changepoint_probability`
- `tail_only`
  - 只依赖当前点对最佳匹配分布的 tail probability
- `cp_and_tail`
  - 只有当变点后验高，且所有候选中最佳分布的 tail probability 仍然低时，才记为 raw anomaly

默认推荐 `cp_and_tail`，因为它能过滤正常的已知分布切换。

## Configuration

新增配置字段：

```yaml
detection:
  mode: bocpd
  bocpd:
    hazard_lambda: 50
    max_run_length: 200
    state_prior: sample_count
    changepoint_posterior_threshold: 0.5
    raw_anomaly_rule: cp_and_tail
```

说明：

- `mode`
  - `pointwise | bocpd`
- `hazard_lambda`
  - 常数危险率参数
- `max_run_length`
  - run-length 截断上限
- `state_prior`
  - `uniform | sample_count`
- `changepoint_posterior_threshold`
  - 变点后验阈值
- `raw_anomaly_rule`
  - 点级异常生成规则

## Framework Integration

### Config layer

`DetectionConfig` 需要支持：

- `detection.mode`
- `detection.bocpd.*`

并保证默认值兼容现有配置。

### Detector layer

保留当前 `AnomalyDetector`，新增 `BOCPDDetector`。

`BOCPDDetector` 需要暴露与当前评估器兼容的接口：

- `detect_point(...) -> DetectionResult`
- `reset_trace_state() -> None`

### Evaluator layer

每条 trace 开始前调用一次 `reset_trace_state()`。

trace 级评估口径不变：

- 点级先生成 raw anomaly
- 再按容忍次数策略聚合为 trace 级报警
- 仍产出统一的 `TP/FP/FN/TN` 结果

### Reporter layer

JSON、CSV、Markdown 结果需要增加 BOCPD 元数据与点级状态字段。

## Output Changes

### Metadata / summary

新增字段：

- `detection_mode`
- `bocpd.hazard_lambda`
- `bocpd.max_run_length`
- `bocpd.state_prior`
- `bocpd.changepoint_posterior_threshold`
- `bocpd.raw_anomaly_rule`

### Anomaly point details

每个 anomaly point 增加：

- `best_tail_p_value`
- `best_log_likelihood`
- `changepoint_probability`
- `most_likely_run_length`
- `raw_anomaly_reasons`
- `candidate_distribution_count`
- `top_matches`

其中 `top_matches` 至少包含：

- `distribution_label`
- `tail_probability`
- `log_likelihood`

### Trace details

每条 trace 建议增加：

- `first_detection_changepoint_probability`
- `first_detection_run_length`
- `first_detection_best_distribution`
- `first_detection_best_tail_p_value`

## Error Handling

- 当候选分布为空时，回退到全局分布集合
- 当某个分布的 `pdf/logpdf` 下溢时，使用带下界裁剪的 log likelihood
- 当 `max_run_length < 1`、`hazard_lambda <= 1`、非法 `state_prior` 或非法 `raw_anomaly_rule` 出现时，配置加载直接报错

## Testing Strategy

需要覆盖：

- 配置加载与默认值兼容
- `pointwise` 模式行为不回归
- `BOCPDDetector` 的 run 状态重置
- 候选分布 likelihood 与 tail probability 计算
- 正常已知分布切换不应默认触发异常
- 无法被任一已知分布解释的点应提升 `changepoint_probability`
- JSON/CSV 输出新增字段

## Risks

- 若只使用单点 best-match probability 而不维护 `w_t(r, k)`，算法会退化，无法体现 run-length 语义
- 若 `hazard_lambda` 过小，会导致大量伪变点
- 若上下文匹配错误，会直接影响候选分布集合与后续 BOCPD 推断

## Expected Outcome

完成后，系统将拥有两个并列的统一检测模式：

- `pointwise`
- `bocpd`

两者共享：

- 相同的 `learned_distributions` 输入
- 相同的上下文匹配机制
- 相同的 trace 级评估口径
- 相同的结果导出与后续可视化入口

这使后续可以在统一实验框架中直接比较 BOCPD 与当前点级概率检测模式的 `fp` / `fn` 表现。
