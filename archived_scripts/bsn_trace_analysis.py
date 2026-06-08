#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSN Trace数据质量分析脚本
用于检测BSN传感器数据中的分布异常问题
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

@dataclass
class BSNTraceMetadata:
    """BSN trace文件的元数据"""
    cnt: int
    duration: int
    sensor_index: int
    config_num: int
    trace_config: List[str]
    start_time: List[int]
    filename: str

@dataclass
class BSNDistributionParameters:
    """BSN分布参数"""
    norm_label: str
    mean: float
    variance: float
    std_dev: float
    sample_count: int
    position: int  # norm标签在trace_config中的位置(1,2,3)
    sensor_index: int
    file_id: str
    start_time: int
    end_time: int

# 期望的分布参数
EXPECTED_DISTRIBUTIONS = {
    'norm1': {'mu': 0.8999, 'sigma': 0.0107, 'sigma_sq': 0.0107**2},
    'norm2': {'mu': 1.0349, 'sigma': 0.0108, 'sigma_sq': 0.0108**2},
    'norm3': {'mu': 0.9674, 'sigma': 0.0108, 'sigma_sq': 0.0108**2}
}

class BSNTraceParser:
    """BSN trace文件解析器"""

    # 文件名正则表达式
    FILENAME_PATTERN = re.compile(
        r'eval_ident_trace-cnt-(?P<cnt>\d+)'
        r'-duration-(?P<duration>\d+)'
        r'-sensor_index-(?P<sensor_index>\d+)'
        r'-config_num-(?P<config_num>\d+)'
        r'-trace_config-(?P<trace_config>[^-]+)'
        r'-start_time-(?P<start_time>[^-]+)'
    )

    def parse_filename(self, filename: str) -> Optional[BSNTraceMetadata]:
        """
        解析BSN trace文件名

        Args:
            filename: 文件名字符串

        Returns:
            BSNTraceMetadata对象,如果解析失败返回None
        """
        match = self.FILENAME_PATTERN.search(filename)
        if not match:
            return None

        groups = match.groupdict()

        # 解析trace_config为列表
        trace_config = groups['trace_config'].split(',')

        # 解析start_time为整数列表
        start_time = [int(x) for x in groups['start_time'].split(',')]

        return BSNTraceMetadata(
            cnt=int(groups['cnt']),
            duration=int(groups['duration']),
            sensor_index=int(groups['sensor_index']),
            config_num=int(groups['config_num']),
            trace_config=trace_config,
            start_time=start_time,
            filename=filename
        )

    def parse_trace_file(self, filepath: Path) -> Dict[str, pd.DataFrame]:
        """
        解析BSN trace文件内容,按norm标签分段

        Args:
            filepath: trace文件路径

        Returns:
            字典: {norm_label: DataFrame}
        """
        # 解析文件名
        metadata = self.parse_filename(filepath.name)
        if not metadata:
            raise ValueError(f"无法解析文件名: {filepath.name}")

        # 读取CSV数据
        df = pd.read_csv(filepath)

        # 根据sensor_index确定要提取的传感器
        # sensor_index=0 -> /g3t1_1, sensor_index=1 -> /g3t1_2, 等等
        target_component = f'/g3t1_{metadata.sensor_index + 1}'

        # 只保留目标传感器的数据
        df_filtered = df[df['component'] == target_component].copy()

        if len(df_filtered) == 0:
            raise ValueError(f"文件{filepath.name}中未找到传感器{target_component}的数据")

        # 按norm标签分段
        segments = {}
        start_times = metadata.start_time + [df_filtered['logicalTime(s)'].max() + 1]

        for i, norm_label in enumerate(metadata.trace_config):
            start = start_times[i]
            end = start_times[i + 1]

            segment_mask = (df_filtered['logicalTime(s)'] >= start) & (df_filtered['logicalTime(s)'] < end)
            segment_df = df_filtered[segment_mask].copy()

            if len(segment_df) >= 10:  # 最少10个数据点
                segments[norm_label] = segment_df

        return segments, metadata

    def extract_distribution_parameters(
        self,
        segments: Dict[str, pd.DataFrame],
        metadata: BSNTraceMetadata
    ) -> List[BSNDistributionParameters]:
        """
        从分段数据中提取分布参数

        Args:
            segments: 按norm标签分段的数据
            metadata: trace文件元数据

        Returns:
            分布参数列表
        """
        parameters = []
        start_times = metadata.start_time + [999999]

        for i, norm_label in enumerate(metadata.trace_config):
            if norm_label not in segments:
                continue

            segment_df = segments[norm_label]
            cost_values = segment_df['cost'].values

            mean = np.mean(cost_values)
            variance = np.var(cost_values, ddof=1)  # 样本方差
            std_dev = np.sqrt(variance)

            parameters.append(BSNDistributionParameters(
                norm_label=norm_label,
                mean=mean,
                variance=variance,
                std_dev=std_dev,
                sample_count=len(cost_values),
                position=i + 1,  # 位置从1开始
                sensor_index=metadata.sensor_index,
                file_id=f"{metadata.cnt:03d}",
                start_time=start_times[i],
                end_time=start_times[i + 1]
            ))

        return parameters


def analyze_bsn_traces(trace_dir: Path) -> Dict[str, List[BSNDistributionParameters]]:
    """
    分析所有BSN trace文件

    Args:
        trace_dir: trace文件目录

    Returns:
        字典: {norm_label: [分布参数列表]}
    """
    parser = BSNTraceParser()

    # 按norm标签收集所有分布参数
    distributions_by_label = defaultdict(list)

    # 获取所有txt文件
    trace_files = sorted(trace_dir.glob('*.txt'))
    print(f"找到 {len(trace_files)} 个BSN trace文件")

    success_count = 0
    failed_files = []

    for trace_file in trace_files:
        try:
            segments, metadata = parser.parse_trace_file(trace_file)
            params_list = parser.extract_distribution_parameters(segments, metadata)

            for params in params_list:
                distributions_by_label[params.norm_label].append(params)

            success_count += 1

        except Exception as e:
            failed_files.append((trace_file.name, str(e)))
            continue

    print(f"成功处理: {success_count}/{len(trace_files)} 个文件")
    if failed_files:
        print(f"失败文件数: {len(failed_files)}")
        for fname, error in failed_files[:5]:  # 只显示前5个
            print(f"  - {fname}: {error}")

    return dict(distributions_by_label)


def analyze_distribution_quality(
    distributions: Dict[str, List[BSNDistributionParameters]]
) -> Dict[str, Dict]:
    """
    分析分布质量并识别异常

    Args:
        distributions: 按norm标签分组的分布参数

    Returns:
        详细的质量分析结果
    """
    results = {}

    for norm_label, params_list in distributions.items():
        if norm_label not in EXPECTED_DISTRIBUTIONS:
            continue

        expected = EXPECTED_DISTRIBUTIONS[norm_label]

        # 计算所有样本的统计信息
        means = np.array([p.mean for p in params_list])
        variances = np.array([p.variance for p in params_list])

        overall_mean = np.mean(means)
        overall_std = np.std(means)
        deviation_from_expected = abs(overall_mean - expected['mu'])
        deviation_percent = (deviation_from_expected / expected['mu']) * 100

        # 按位置分组分析
        by_position = defaultdict(list)
        for p in params_list:
            by_position[p.position].append(p)

        position_analysis = {}
        for position, pos_params in by_position.items():
            pos_means = np.array([p.mean for p in pos_params])
            pos_mean = np.mean(pos_means)
            pos_std = np.std(pos_means)
            pos_deviation = abs(pos_mean - expected['mu'])
            pos_deviation_percent = (pos_deviation / expected['mu']) * 100

            position_analysis[position] = {
                'count': len(pos_params),
                'mean': pos_mean,
                'std': pos_std,
                'deviation': pos_deviation,
                'deviation_percent': pos_deviation_percent,
                'is_normal': pos_deviation_percent < 10.0,  # 10%容差
                'params': pos_params
            }

        # 识别异常样本
        normal_samples = []
        abnormal_samples = []

        for p in params_list:
            deviation = abs(p.mean - expected['mu'])
            deviation_percent = (deviation / expected['mu']) * 100

            if deviation_percent < 10.0:  # 10%容差
                normal_samples.append(p)
            else:
                abnormal_samples.append(p)

        results[norm_label] = {
            'expected_mu': expected['mu'],
            'expected_sigma': expected['sigma'],
            'total_samples': len(params_list),
            'overall_mean': overall_mean,
            'overall_std': overall_std,
            'deviation_from_expected': deviation_from_expected,
            'deviation_percent': deviation_percent,
            'by_position': position_analysis,
            'normal_samples': normal_samples,
            'abnormal_samples': abnormal_samples,
            'normal_count': len(normal_samples),
            'abnormal_count': len(abnormal_samples)
        }

    return results


def generate_analysis_report(
    distributions: Dict[str, List[BSNDistributionParameters]],
    quality_analysis: Dict[str, Dict],
    output_file: Path
):
    """
    生成详细的分析报告

    Args:
        distributions: 分布参数字典
        quality_analysis: 质量分析结果
        output_file: 输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("BSN Trace数据质量分析报告\n")
        f.write("=" * 80 + "\n\n")

        # 1. 总体概况
        f.write("一、总体概况\n")
        f.write("-" * 80 + "\n")

        total_distributions = sum(len(params) for params in distributions.values())
        f.write(f"总分布样本数: {total_distributions}\n")

        for norm_label in sorted(distributions.keys()):
            params_list = distributions[norm_label]
            f.write(f"  - {norm_label}: {len(params_list)} 个样本\n")
        f.write("\n")

        # 2. 期望分布参数
        f.write("二、期望分布参数\n")
        f.write("-" * 80 + "\n")
        for norm_label, expected in EXPECTED_DISTRIBUTIONS.items():
            f.write(f"{norm_label}:\n")
            f.write(f"  - 期望均值(μ): {expected['mu']:.4f}\n")
            f.write(f"  - 期望标准差(σ): {expected['sigma']:.4f}\n")
            f.write(f"  - 期望方差(σ²): {expected['sigma_sq']:.8f}\n")
        f.write("\n")

        # 3. 实际分布分析
        f.write("三、实际分布分析\n")
        f.write("-" * 80 + "\n")

        for norm_label in sorted(quality_analysis.keys()):
            analysis = quality_analysis[norm_label]

            f.write(f"\n【{norm_label}】\n")
            f.write(f"总样本数: {analysis['total_samples']}\n")
            f.write(f"实际均值: {analysis['overall_mean']:.6f}\n")
            f.write(f"标准差: {analysis['overall_std']:.6f}\n")
            f.write(f"偏离期望值: {analysis['deviation_from_expected']:.6f} ({analysis['deviation_percent']:.2f}%)\n")

            status = "✅ 正常" if analysis['deviation_percent'] < 10.0 else "❌ 异常"
            f.write(f"状态: {status}\n")

            # 按位置分析
            f.write(f"\n按位置分析:\n")
            for position in sorted(analysis['by_position'].keys()):
                pos_analysis = analysis['by_position'][position]
                status = "✅" if pos_analysis['is_normal'] else "❌"
                f.write(f"  位置{position}: {status}\n")
                f.write(f"    - 样本数: {pos_analysis['count']}\n")
                f.write(f"    - 均值: {pos_analysis['mean']:.6f}\n")
                f.write(f"    - 标准差: {pos_analysis['std']:.6f}\n")
                f.write(f"    - 偏离: {pos_analysis['deviation']:.6f} ({pos_analysis['deviation_percent']:.2f}%)\n")

            # 异常样本统计
            f.write(f"\n正常样本: {analysis['normal_count']} ({analysis['normal_count']/analysis['total_samples']*100:.1f}%)\n")
            f.write(f"异常样本: {analysis['abnormal_count']} ({analysis['abnormal_count']/analysis['total_samples']*100:.1f}%)\n")

        # 4. 异常文件详情
        f.write("\n\n四、异常文件详情\n")
        f.write("-" * 80 + "\n")

        for norm_label in sorted(quality_analysis.keys()):
            analysis = quality_analysis[norm_label]

            if analysis['abnormal_count'] > 0:
                f.write(f"\n【{norm_label}异常文件】\n")
                f.write(f"共{analysis['abnormal_count']}个异常样本\n\n")

                # 按偏离程度排序
                abnormal_sorted = sorted(
                    analysis['abnormal_samples'],
                    key=lambda p: abs(p.mean - analysis['expected_mu']),
                    reverse=True
                )

                f.write(f"{'文件ID':<10} {'位置':<6} {'传感器':<8} {'起止时间':<20} {'样本数':<8} {'均值':<12} {'偏离':<12} {'偏离%':<10}\n")
                f.write("-" * 100 + "\n")

                for p in abnormal_sorted[:30]:  # 最多显示30个
                    deviation = abs(p.mean - analysis['expected_mu'])
                    deviation_percent = (deviation / analysis['expected_mu']) * 100

                    f.write(f"{p.file_id:<10} {p.position:<6} {p.sensor_index:<8} "
                           f"{p.start_time}-{p.end_time:<15} {p.sample_count:<8} "
                           f"{p.mean:<12.6f} {deviation:<12.6f} {deviation_percent:<10.2f}\n")

        # 5. 结论与建议
        f.write("\n\n五、结论与建议\n")
        f.write("-" * 80 + "\n")

        all_normal = all(
            analysis['deviation_percent'] < 10.0
            for analysis in quality_analysis.values()
        )

        if all_normal:
            f.write("✅ 所有norm标签的分布均符合期望值(偏离<10%)\n")
            f.write("✅ BSN数据质量良好,未发现系统性错误\n")
        else:
            f.write("❌ 发现分布异常问题:\n")
            for norm_label, analysis in quality_analysis.items():
                if analysis['deviation_percent'] >= 10.0:
                    f.write(f"  - {norm_label}: 偏离期望值{analysis['deviation_percent']:.2f}%\n")

            # 检查是否有位置依赖问题
            has_position_dependency = False
            for norm_label, analysis in quality_analysis.items():
                by_pos = analysis['by_position']
                if len(by_pos) > 1:
                    normal_positions = [pos for pos, pa in by_pos.items() if pa['is_normal']]
                    abnormal_positions = [pos for pos, pa in by_pos.items() if not pa['is_normal']]
                    if normal_positions and abnormal_positions:
                        has_position_dependency = True
                        f.write(f"\n⚠️ {norm_label}存在位置依赖性问题:\n")
                        f.write(f"  - 正常位置: {normal_positions}\n")
                        f.write(f"  - 异常位置: {abnormal_positions}\n")

            if has_position_dependency:
                f.write("\n建议:\n")
                f.write("1. 检查数据生成脚本中不同时间段的分布参数设置\n")
                f.write("2. 验证norm标签与时间段的映射关系是否正确\n")
                f.write("3. 参考RUBIS数据集的类似问题分析\n")


if __name__ == '__main__':
    # BSN trace文件目录
    trace_dir = Path('bsn_evaluation_data/eval_ident_traces')

    print("开始分析BSN trace数据...")
    print("=" * 80)

    # 分析所有trace文件
    distributions = analyze_bsn_traces(trace_dir)

    # 质量分析
    print("\n执行质量分析...")
    quality_analysis = analyze_distribution_quality(distributions)

    # 生成报告
    output_file = Path('BSN_DATA_QUALITY_REPORT.md')
    generate_analysis_report(distributions, quality_analysis, output_file)

    print(f"\n报告已生成: {output_file}")
    print("\n分析完成!")

    # 打印快速摘要
    print("\n" + "=" * 80)
    print("快速摘要:")
    print("=" * 80)
    for norm_label, analysis in sorted(quality_analysis.items()):
        status = "✅ 正常" if analysis['deviation_percent'] < 10.0 else "❌ 异常"
        print(f"{norm_label}: {status}")
        print(f"  实际均值: {analysis['overall_mean']:.6f} (期望: {analysis['expected_mu']:.4f})")
        print(f"  偏离: {analysis['deviation_percent']:.2f}%")
        print(f"  正常/异常样本: {analysis['normal_count']}/{analysis['abnormal_count']}")
