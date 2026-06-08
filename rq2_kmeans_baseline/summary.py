"""
RQ2 baseline 结果汇总。
"""
from pathlib import Path
from typing import Dict, List
import csv
import json


def choose_best_result(results: List[Dict], best_k_metric: str) -> Dict:
    metric_key = {
        "f1": "f1_score",
        "recall": "recall",
        "precision": "precision",
    }[best_k_metric]
    return max(
        results,
        key=lambda item: (
            item[metric_key],
            item["recall"],
            -item["k"],
        ),
    )


def write_summary(output_dir: str, best_k_metric: str, results: List[Dict]) -> Dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    best_result = choose_best_result(results, best_k_metric)
    for item in results:
        item["is_best_k"] = item["k"] == best_result["k"]

    summary = {
        "best_k_metric": best_k_metric,
        "best_k": best_result["k"],
        "results": results,
    }

    (output_root / "rq2_kmeans_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with (output_root / "rq2_kmeans_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "k",
                "cluster_count",
                "tp_count",
                "fp_count",
                "fn_count",
                "tn_count",
                "precision",
                "recall",
                "f1_score",
                "avg_delay_loops",
                "model_path",
                "is_best_k",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    lines = [
        "# RQ2 KMeans Baseline 汇总",
        "",
        f"- best_k_metric: {best_k_metric}",
        f"- best_k: {best_result['k']}",
        "",
        "| k | clusters | TP | FP | FN | TN | Precision | Recall | F1 | Best |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['k']} | {item['cluster_count']} | {item['tp_count']} | {item['fp_count']} | "
            f"{item['fn_count']} | {item['tn_count']} | {item['precision']:.4f} | "
            f"{item['recall']:.4f} | {item['f1_score']:.4f} | {'yes' if item['is_best_k'] else 'no'} |"
        )
    (output_root / "rq2_kmeans_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return summary
