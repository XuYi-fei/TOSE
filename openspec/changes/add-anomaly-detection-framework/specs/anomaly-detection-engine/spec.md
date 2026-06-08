# Anomaly Detection Engine Spec

## ADDED Requirements

### Requirement: 加载已学习的分布参数
**ID**: ADE-001
**Priority**: High

异常检测引擎SHALL能够从聚类结果配置文件中加载已知的分布参数，并初始化检测器。

#### Scenario: 成功加载RUBIS分布参数
**Given** 存在有效的`learned_distributions.yaml`文件
**And** 文件包含norm1、norm2、norm3三个分布
**When** 初始化AnomalyDetector
**Then** 应成功加载3个LearnedDistribution对象
**And** 每个分布应包含mu、sigma参数
**And** 所有sigma值应大于0

#### Scenario: 配置文件不存在
**Given** `learned_distributions.yaml`文件不存在
**When** 尝试初始化AnomalyDetector
**Then** 应抛出FileNotFoundError异常
**And** 错误信息应提示用户先运行聚类分析

#### Scenario: 配置文件格式错误
**Given** `learned_distributions.yaml`格式不正确
**When** 尝试加载分布参数
**Then** 应抛出ValueError异常
**And** 错误信息应明确指出格式问题

---

### Requirement: 解析包含异常段的trace文件
**ID**: ADE-002
**Priority**: High

系统SHALL扩展TraceParser以支持解析包含abn（anomaly）标签的trace文件，正确识别异常段的开始时间。

#### Scenario: 解析包含abn1的RUBIS trace文件
**Given** trace文件名为`eval_abn_trace-cnt-000-duration-64800-config_num-3-trace_config-norm3,norm1,abn1-start_time-960,23100,52740.txt`
**When** 使用RUBISParser解析文件名
**Then** 应识别trace_config为[norm3, norm1, abn1]
**And** 应识别start_time为[960, 23100, 52740]
**And** abn1段应从时间52740开始

#### Scenario: 解析包含多个异常段的trace
**Given** trace文件包含config: norm1,abn1,norm2,abn2
**When** 解析文件
**Then** 应正确识别4个段的边界
**And** abn1和abn2应被标记为异常段

#### Scenario: 向后兼容identity trace文件
**Given** trace文件只包含norm段（无abn）
**When** 解析文件
**Then** 应正常解析，不应报错
**And** 所有段应被标记为正常段

---

### Requirement: 3-Sigma异常检测
**ID**: ADE-003
**Priority**: High

检测器SHALL使用3-sigma规则判定数据点是否异常：当数据点偏离所有已知分布超过3倍标准差时，判定为异常。

#### Scenario: 检测到明显异常点
**Given** 已知分布norm1(mu=0.05, sigma=0.002), norm2(mu=0.11, sigma=0.01)
**And** 检测阈值为3-sigma
**When** 输入数据点value=0.5（远超所有分布）
**Then** 应计算z_scores: z1=(0.5-0.05)/0.002=225, z2=(0.5-0.11)/0.01=39
**And** min_abs_z=39 > 3
**And** 应判定为异常点

#### Scenario: 检测到接近已知分布的正常点
**Given** 已知分布norm1(mu=0.05, sigma=0.002)
**When** 输入数据点value=0.051
**Then** 应计算z_score=(0.051-0.05)/0.002=0.5
**And** 0.5 < 3
**And** 应判定为正常点，属于norm1分布

#### Scenario: 边界情况：恰好3-sigma
**Given** 已知分布norm1(mu=0.05, sigma=0.002)
**When** 输入数据点value=0.056 (恰好3倍标准差)
**Then** z_score=(0.056-0.05)/0.002=3.0
**And** 3.0 不大于 3（使用>而非>=）
**And** 应判定为正常点（边界包含在正常范围内）

---

### Requirement: 逐点实时检测trace数据
**ID**: ADE-004
**Priority**: High

检测器SHALL逐点读取trace文件数据，对每个时间点的响应时间值进行异常判定，模拟实时检测场景。

#### Scenario: 按时间顺序检测trace数据
**Given** trace文件包含500个时间点数据
**And** 已初始化AnomalyDetector
**When** 检测整个trace文件
**Then** 应按simTime(s)升序逐点处理
**And** 每个点应记录：时间、值、是否异常、z_scores
**And** 应识别每个点所属的段（norm1/abn1等）

#### Scenario: 记录第一个异常点
**Given** trace包含3段：norm1(0-1000s), norm2(1000-2000s), abn1(2000-3000s)
**When** 检测整个trace
**Then** 应记录第一个检测到异常的时间点
**And** 该时间应 >= 2000s（abn1段开始时间）
**And** 应计算检测延迟 = 第一异常点时间 - 2000

#### Scenario: 处理无异常的trace文件
**Given** trace文件只包含正常段（norm1, norm2, norm3）
**When** 检测整个trace
**Then** 不应检测到任何异常点
**And** anomaly_points列表应为空
**And** 不应抛出错误

---

### Requirement: 支持可配置的检测阈值
**ID**: ADE-005
**Priority**: Medium

用户MUST能够配置异常判定的sigma阈值，默认为3.0。

#### Scenario: 使用默认3-sigma阈值
**Given** 配置文件未指定sigma_threshold
**When** 初始化AnomalyDetector
**Then** 应使用默认阈值3.0

#### Scenario: 自定义检测阈值
**Given** 配置文件设置`detection.sigma_threshold: 2.5`
**When** 初始化AnomalyDetector
**Then** 应使用阈值2.5进行异常判定
**And** 更多点可能被判定为异常（阈值降低）

#### Scenario: 阈值边界验证
**Given** 配置文件设置`detection.sigma_threshold: 0.5`
**When** 验证配置
**Then** 应警告阈值过低（<1.0），可能导致大量误报
**But** 不应阻止运行（允许用户自定义）

---

### Requirement: 识别最接近的分布
**ID**: ADE-006
**Priority**: Medium

对每个数据点，检测器SHALL识别它最接近哪个已知分布，即使该点被判定为异常。

#### Scenario: 正常点匹配最接近分布
**Given** 已知分布norm1(mu=0.05, sigma=0.002), norm2(mu=0.11, sigma=0.01)
**When** 输入数据点value=0.052
**Then** 计算z_scores: z1=1.0, z2=-5.8
**And** 最接近分布应为norm1（abs(z1) < abs(z2)）
**And** closest_distribution="norm1"

#### Scenario: 异常点仍能识别最接近分布
**Given** 已知分布norm1, norm2
**When** 输入异常点value=0.3
**Then** 虽然判定为异常（偏离所有分布>3sigma）
**And** 仍应识别最接近的分布（可能是norm2）
**And** 用于后续分析和可视化

---

### Requirement: 支持RUBIS和BSN系统类型
**ID**: ADE-007
**Priority**: High

异常检测引擎SHALL支持RUBIS和BSN两种系统类型，自动适配对应的TraceParser。

#### Scenario: 检测RUBIS abnormal traces
**Given** 配置文件system_type="rubis"
**And** test_data_path指向rubis_evaluation_data/eval_abn_traces
**When** 执行检测
**Then** 应使用RUBISParser解析trace文件
**And** 应提取measuredAvgRespTime_{k}列数据
**And** 应正确处理RUBIS文件命名格式

#### Scenario: 检测BSN abnormal traces
**Given** 配置文件system_type="bsn"
**And** test_data_path指向bsn_evaluation_data/eval_abn_traces
**When** 执行检测
**Then** 应使用BSNParser解析trace文件
**And** 应提取cost列数据
**And** 应正确处理BSN文件命名格式（含sensor_index）

#### Scenario: 系统类型不匹配检测
**Given** learned_distributions.yaml指定system_type="rubis"
**And** 检测配置指定system_type="bsn"
**When** 初始化检测器
**Then** 应抛出ValueError异常
**And** 提示系统类型不匹配

---

### Requirement: 性能要求
**ID**: ADE-008
**Priority**: Medium

异常检测SHALL高效执行，满足性能目标。

#### Scenario: 200个trace文件在10秒内完成
**Given** test_data_path包含200个abnormal trace文件
**And** 每个文件约500个数据点
**When** 执行完整检测流程
**Then** 总耗时应 < 10秒
**And** 平均每个文件 < 50ms

#### Scenario: 内存占用合理
**Given** 检测200个trace文件
**When** 执行检测
**Then** 内存占用应 < 500MB
**And** 不应一次性加载所有文件到内存
**And** 应采用流式处理
