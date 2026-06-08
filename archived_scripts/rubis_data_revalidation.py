#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RUBIS数据重新验证脚本
使用更新的期望参数和响应时间范围约束
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

@dataclass
class TraceMetadata:
    """Trace文件元数据"""
    cnt: int
    config_num: int
    trace_config: List[str]
    start_time: List[int]
    filename: str

@dataclass
class DistributionParameters:
    """分布参数"""
    norm_label: str
    mean: float
    variance: float
    std_dev: float
    sample_count: int
    position: int
    file_id: str
    start_time: int
    end_time: int
    min_value: float
    max_value: float

# 更新的期望分布参数
EXPECTED_DISTRIBUTIONS = {
    'norm1': {
        'mu': 0.0526,
        'sigma': 0.0024,
        'sigma_sq': 0.0024**2,
        'min_max': (0.0454, 0.0598)
    },
    'norm2': {
        'mu': 0.1154,
        'sigma': 0.0127,
        'sigma_sq': 0.0127**2,
        'min_max': (0.0773, 0.1535)
    },
    'norm3': {
        'mu': 0.0378,
        'sigma': 0.002,
        'sigma_sq': 0.002**2,
        'min_max': (0.0318, 0.0438)
    }
}

class RUBISTraceParser:
    """RUBIS trace文件解析器"""

    FILENAME_PATTERN = re.compile(
        r'eval_ident_trace-cnt-(?P<cnt>\d+)'
        r'-duration-(?P<duration>\d+)'
        r'-config_num-(?P<config_num>\d+)'
        r'-trace_config-(?P<trace_config>[^-]+)'
        r'-start_time-(?P<start_time>[^.]+)'
    )

    def parse_filename(self, filename: str) -> Optional[TraceMetadata]:
        """解析trace文件名"""
        match = self.FILENAME_PATTERN.search(filename)
        if not match:
            return None

        groups = match.groupdict()
        trace_config = groups['trace_config'].split(',')
        start_time = [int(x) for x in groups['start_time'].split(',')]

        return TraceMetadata(
            cnt=int(groups['cnt']),
            config_num=int(groups['config_num']),
            trace_config=trace_config,
            start_time=start_time,
            filename=filename
        )

    def parse_trace_file(self, filepath: Path) -> Tuple[Dict[str, pd.DataFrame], TraceMetadata]:
        """解析trace文件内容"""
        metadata = self.parse_filename(filepath.name)
        if not metadata:
            raise ValueError(f"无法解析文件名: {filepath.name}")

        # 读取CSV数据
        df = pd.read_csv(filepath)

        # 清理数据
        df_clean = df.dropna()

        # 按norm标签分段
        segments = {}
        start_times = metadata.start_time + [df_clean['simTime'].max() + 1]

        for i, norm_label in enumerate(metadata.trace_config):
            start = start_times[i]
            end = start_times[i + 1]

            segment_mask = (df_clean['simTime'] >= start) & (df_clean['simTime'] < end)
            segment_df = df_clean[segment_mask].copy()

            if len(segment_df) >= 10:
                segments[norm_label] = segment_df

        return segments, metadata

    def extract_distribution_parameters(
        self,
        segments: Dict[str, pd.DataFrame],
        metadata: TraceMetadata
    ) -> List[DistributionParameters]:
        """提取分布参数"""
        parameters = []
        start_times = metadata.start_time + [999999]

        for i, norm_label in enumerate(metadata.trace_config):
            if norm_label not in segments:
                continue

            segment_df = segments[norm_label]

            # 获取最后一列的列名（measuredAvgRespTime）
            last_column = segment_df.columns[-1]
            values = segment_df[last_column].values

            mean = np.mean(values)
            variance = np.var(values, ddof=1)
            std_dev = np.sqrt(variance)
            min_value = np.min(values)
            max_value = np.max(values)

            parameters.append(DistributionParameters(
                norm_label=norm_label,
                mean=mean,
                variance=variance,
                std_dev=std_dev,
                sample_count=len(values),
                position=i + 1,
                file_id=f"{metadata.cnt:03d}",
                start_time=start_times[i],
                end_time=start_times[i + 1],
                min_value=min_value,
                max_value=max_value
            ))

        return parameters


def analyze_rubis_data(trace_dir: Path) -> Dict[str, List[DistributionParameters]]:
    """分析RUBIS数据"""
    parser = RUBISTraceParser()
    distributions_by_label = defaultdict(list)

    trace_files = sorted(trace_dir.glob('*.txt'))
    print(f"找到 {len(trace_files)} 个RUBIS trace文件")

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

    return dict(distributions_by_label)


def validate_distribution(
    norm_label: str,
    params_list: List[DistributionParameters]
) -> Dict:
    """验证单个分布"""
    expected = EXPECTED_DISTRIBUTIONS[norm_label]

    # 计算总体统计
    means = np.array([p.mean for p in params_list])
    overall_mean = np.mean(means)
    overall_std = np.std(means)

    # 均值偏离检查
    mean_deviation = abs(overall_mean - expected['mu'])
    mean_deviation_percent = (mean_deviation / expected['mu']) * 100

    # 按位置分组
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

        # 响应时间范围检查
        range_violations = []
        for p in pos_params:
            expected_min, expected_max = expected['min_max']
            if p.min_value < expected_min or p.max_value > expected_max:
                range_violations.append({
                    'file_id': p.file_id,
                    'min': p.min_value,
                    'max': p.max_value,
                    'expected_min': expected_min,
                    'expected_max': expected_max
                })

        position_analysis[position] = {
            'count': len(pos_params),
            'mean': pos_mean,
            'std': pos_std,
            'deviation': pos_deviation,
            'deviation_percent': pos_deviation_percent,
            'is_normal': pos_deviation_percent < 10.0,
            'range_violations': range_violations,
            'params': pos_params
        }

    # 分类正常/异常样本
    normal_samples = []
    abnormal_samples = []

    for p in params_list:
        deviation = abs(p.mean - expected['mu'])
        deviation_percent = (deviation / expected['mu']) * 100

        expected_min, expected_max = expected['min_max']
        range_ok = (p.min_value >= expected_min and p.max_value <= expected_max)

        if deviation_percent < 10.0 and range_ok:
            normal_samples.append(p)
        else:
            abnormal_samples.append(p)

    return {
        'expected_mu': expected['mu'],
        'expected_sigma': expected['sigma'],
        'expected_range': expected['min_max'],
        'total_samples': len(params_list),
        'overall_mean': overall_mean,
        'overall_std': overall_std,
        'mean_deviation': mean_deviation,
        'mean_deviation_percent': mean_deviation_percent,
        'by_position': position_analysis,
        'normal_samples': normal_samples,
        'abnormal_samples': abnormal_samples,
        'normal_count': len(normal_samples),
        'abnormal_count': len(abnormal_samples)
    }


def generate_validation_report(
    distributions: Dict[str, List[DistributionParameters]],
    validation_results: Dict[str, Dict],
    output_file: Path
):
    """生成验证报告"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RUBIS数据重新验证报告\n")
        f.write("=" * 80 + "\n\n")

        f.write("使用更新的期望参数：\n")
        f.write("-" * 80 + "\n")
        for norm_label, expected in EXPECTED_DISTRIBUTIONS.items():
            f.write(f"{norm_label}:\n")
            f.write(f"  期望均值(μ): {expected['mu']:.4f}\n")
            f.write(f"  期望标准差(σ): {expected['sigma']:.4f}\n")
            f.write(f"  期望方差(σ²): {expected['sigma_sq']:.8f}\n")
            f.write(f"  响应时间范围: {expected['min_max']}\n\n")

        # 总体概况
        f.write("一、总体概况\n")
        f.write("-" * 80 + "\n")
        total = sum(len(params) for params in distributions.values())
        f.write(f"总分布样本数: {total}\n")
        for norm_label in sorted(distributions.keys()):
            f.write(f"  {norm_label}: {len(distributions[norm_label])} 个样本\n")
        f.write("\n")

        # 各分布详细分析
        f.write("二、各分布详细分析\n")
        f.write("-" * 80 + "\n\n")

        for norm_label in sorted(validation_results.keys()):
            result = validation_results[norm_label]

            f.write(f"【{norm_label}】\n")
            f.write(f"总样本数: {result['total_samples']}\n")
            f.write(f"实际均值: {result['overall_mean']:.6f}\n")
            f.write(f"标准差: {result['overall_std']:.6f}\n")
            f.write(f"偏离期望均值: {result['mean_deviation']:.6f} ({result['mean_deviation_percent']:.2f}%)\n")

            status = "✅ 正常" if result['mean_deviation_percent'] < 10.0 else "❌ 异常"
            f.write(f"状态: {status}\n\n")

            # 按位置分析
            f.write("按位置分析:\n")
            for position in sorted(result['by_position'].keys()):
                pos_result = result['by_position'][position]
                status = "✅" if pos_result['is_normal'] else "❌"

                f.write(f"  位置{position}: {status}\n")
                f.write(f"    样本数: {pos_result['count']}\n")
                f.write(f"    均值: {pos_result['mean']:.6f}\n")
                f.write(f"    标准差: {pos_result['std']:.6f}\n")
                f.write(f"    偏离: {pos_result['deviation']:.6f} ({pos_result['deviation_percent']:.2f}%)\n")

                if pos_result['range_violations']:
                    f.write(f"    ⚠️ 响应时间范围违规: {len(pos_result['range_violations'])} 个文件\n")
                    for v in pos_result['range_violations'][:5]:  # 只显示前5个
                        f.write(f"      文件{v['file_id']}: 范围[{v['min']:.4f}, {v['max']:.4f}] "
                               f"(期望: [{v['expected_min']:.4f}, {v['expected_max']:.4f}])\n")
                f.write("\n")

            # 正常/异常统计
            f.write(f"正常样本: {result['normal_count']} ({result['normal_count']/result['total_samples']*100:.1f}%)\n")
            f.write(f"异常样本: {result['abnormal_count']} ({result['abnormal_count']/result['total_samples']*100:.1f}%)\n\n")

            # 异常样本详情
            if result['abnormal_count'] > 0:
                f.write(f"异常样本详情（前20个）:\n")
                abnormal_sorted = sorted(
                    result['abnormal_samples'],
                    key=lambda p: abs(p.mean - result['expected_mu']),
                    reverse=True
                )

                f.write(f"{'文件ID':<10} {'位置':<6} {'均值':<12} {'范围':<25} {'偏离%':<10}\n")
                f.write("-" * 70 + "\n")

                for p in abnormal_sorted[:20]:
                    deviation = abs(p.mean - result['expected_mu'])
                    deviation_percent = (deviation / result['expected_mu']) * 100
                    range_str = f"[{p.min_value:.4f}, {p.max_value:.4f}]"

                    f.write(f"{p.file_id:<10} {p.position:<6} {p.mean:<12.6f} {range_str:<25} {deviation_percent:<10.2f}\n")
                f.write("\n")

            f.write("\n")

        # 结论
        f.write("三、验证结论\n")
        f.write("-" * 80 + "\n")

        all_normal = all(
            result['mean_deviation_percent'] < 10.0
            for result in validation_results.values()
        )

        if all_normal:
            f.write("✅ 所有norm标签的分布均符合期望值(偏离<10%)\n")
            f.write("✅ RUBIS数据质量良好\n")
        else:
            f.write("❌ 发现分布异常问题:\n")
            for norm_label, result in validation_results.items():
                if result['mean_deviation_percent'] >= 10.0:
                    f.write(f"  {norm_label}: 偏离期望值{result['mean_deviation_percent']:.2f}%\n")

                    # 检查位置依赖
                    by_pos = result['by_position']
                    if len(by_pos) > 1:
                        normal_positions = [pos for pos, pa in by_pos.items() if pa['is_normal']]
                        abnormal_positions = [pos for pos, pa in by_pos.items() if not pa['is_normal']]
                        if normal_positions and abnormal_positions:
                            f.write(f"    ⚠️ 存在位置依赖性:\n")
                            f.write(f"      正常位置: {normal_positions}\n")
                            f.write(f"      异常位置: {abnormal_positions}\n")


if __name__ == '__main__':
    trace_dir = Path('rubis_evaluation_data/eval_ident_traces')

    print("=" * 80)
    print("开始RUBIS数据重新验证...")
    print("=" * 80)
    print()

    # 分析数据
    distributions = analyze_rubis_data(trace_dir)

    # 验证各分布
    print("\n执行验证分析...")
    validation_results = {}
    for norm_label, params_list in distributions.items():
        validation_results[norm_label] = validate_distribution(norm_label, params_list)

    # 生成报告
    output_file = Path('RUBIS数据重新验证报告.md')
    generate_validation_report(distributions, validation_results, output_file)

    print(f"\n报告已生成: {output_file}")
    print("\n" + "=" * 80)
    print("验证摘要:")
    print("=" * 80)

    for norm_label, result in sorted(validation_results.items()):
        status = "✅ 正常" if result['mean_deviation_percent'] < 10.0 else "❌ 异常"
        print(f"{norm_label}: {status}")
        print(f"  实际均值: {result['overall_mean']:.6f} (期望: {result['expected_mu']:.4f})")
        print(f"  偏离: {result['mean_deviation_percent']:.2f}%")
        print(f"  正常/异常样本: {result['normal_count']}/{result['abnormal_count']}")

        # 显示位置依赖性
        by_pos = result['by_position']
        if len(by_pos) > 1:
            for position, pos_result in sorted(by_pos.items()):
                pos_status = "✅" if pos_result['is_normal'] else "❌"
                print(f"    位置{position}: {pos_status} μ={pos_result['mean']:.6f} (偏离{pos_result['deviation_percent']:.2f}%)")
