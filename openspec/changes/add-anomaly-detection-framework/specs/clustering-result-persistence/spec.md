# Clustering Result Persistence Spec

## ADDED Requirements

### Requirement: 自动保存聚类结果为YAML配置
**ID**: CRP-001
**Priority**: High

聚类分析完成后，系统SHALL自动将最佳算法发现的分布参数保存为YAML格式的配置文件，以便后续异常检测模块读取使用。

#### Scenario: 成功保存RUBIS聚类结果
**Given** 聚类分析已成功完成，发现3个分布簇
**And** 最佳算法为HDBSCAN，轮廓系数0.9915
**When** 系统保存聚类结果
**Then** 应在输出目录生成`learned_distributions.yaml`文件
**And** 文件应包含system_type、algorithm、distributions等字段
**And** distributions应包含norm1、norm2、norm3三个分布的mu、sigma、sample_count

#### Scenario: 保存多算法结果供选择
**Given** 配置启用了多算法结果保存
**When** 聚类分析完成
**Then** 应保存`learned_distributions_hdbscan.yaml`
**And** 应保存`learned_distributions_gmm.yaml`
**And** 应保存`learned_distributions_best.yaml`（最佳算法的软链接或副本）

#### Scenario: 配置文件格式验证
**Given** 聚类结果已保存
**When** 读取`learned_distributions.yaml`
**Then** 应成功解析YAML格式
**And** 所有必填字段应存在：system_type, distributions
**And** 每个distribution应包含：mu, sigma, sample_count
**And** sigma值应大于0

---

### Requirement: 配置文件向后兼容validation框架
**ID**: CRP-002
**Priority**: High

保存的分布参数配置MUST与现有validation框架的`expected_distributions`格式兼容，允许用户直接将聚类结果用于验证。

#### Scenario: 直接用于validation配置
**Given** 聚类生成了`learned_distributions.yaml`
**When** 用户复制distributions部分到`rubis_config.yaml`的expected_distributions
**Then** validation框架应能正确读取和使用这些参数
**And** 不应出现格式错误或解析失败

#### Scenario: Sigma和Variance的转换
**Given** 聚类结果中保存了sigma（标准差）
**When** validation框架需要variance（方差）
**Then** 配置文件应同时包含sigma和variance字段
**And** 满足关系：variance = sigma^2

---

### Requirement: 记录聚类元数据
**ID**: CRP-003
**Priority**: Medium

保存的配置SHALL包含聚类的元数据，用于追溯和审计。

#### Scenario: 记录聚类时间和算法信息
**Given** 聚类分析完成
**When** 保存结果配置
**Then** 应记录learned_at时间戳（ISO 8601格式）
**And** 应记录使用的algorithm名称
**And** 应记录silhouette_score质量指标
**And** 应记录clustering_config路径（可追溯聚类配置）

#### Scenario: 记录每个分布的簇信息
**Given** 聚类发现了3个簇
**When** 保存配置
**Then** 每个distribution应记录cluster_id
**And** 应记录sample_count（该簇的样本数）
**And** 应记录cluster中心的mean和variance

---

### Requirement: 可配置的保存行为
**ID**: CRP-004
**Priority**: Low

用户MUST能够通过配置控制结果保存的行为。

#### Scenario: 禁用自动保存
**Given** 配置文件中设置`output.save_learned_distributions: false`
**When** 聚类分析完成
**Then** 不应生成`learned_distributions.yaml`文件
**And** 报告中应提示用户未保存分布参数

#### Scenario: 自定义保存路径
**Given** 配置文件中设置`output.learned_distributions_path: custom/path.yaml`
**When** 聚类分析完成
**Then** 应将结果保存到指定路径
**And** 路径不存在时自动创建父目录
