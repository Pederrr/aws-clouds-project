#!/usr/bin/env python3
import argparse
import csv
import math
import os
import statistics
from typing import Optional

import matplotlib.pyplot as plt
from tabulate import tabulate


Metric = dict[str, float]


def parse_float(value: str) -> Optional[float]:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        try:
            return float(cleaned.replace(",", ""))
        except ValueError:
            return None


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return (math.nan, math.nan)
    if len(values) == 1:
        return (values[0], 0.0)
    return (statistics.mean(values), statistics.stdev(values))


def read_aggregated_metrics(csv_path: str) -> Optional[Metric]:
    with open(csv_path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("Name", "").strip() == "Aggregated":
                request_count = parse_float(row.get("Request Count", ""))
                failure_count = parse_float(row.get("Failure Count", ""))
                requests_per_s = parse_float(row.get("Requests/s", ""))
                median_rt = parse_float(row.get("Median Response Time", ""))
                if median_rt is None:
                    median_rt = parse_float(row.get("50%", ""))
                p95_rt = parse_float(row.get("95%", ""))
                if request_count is None or request_count == 0:
                    error_rate = None
                else:
                    if failure_count is None:
                        error_rate = None
                    else:
                        error_rate = failure_count / request_count
                if (
                    requests_per_s is None
                    or median_rt is None
                    or p95_rt is None
                    or error_rate is None
                ):
                    return None
                return {
                    "requests_per_s": requests_per_s,
                    "error_rate": error_rate,
                    "median_ms": median_rt,
                    "p95_ms": p95_rt,
                }
    return None


def gather_runs(data_dir: str) -> dict[int, dict[str, list[Metric]]]:
    results: dict[int, dict[str, list[Metric]]] = {}
    for entry in os.listdir(data_dir):
        entry_path = os.path.join(data_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        if "-" not in entry:
            continue
        concurrency_str, config = entry.split("-", 1)
        if not concurrency_str.isdigit():
            continue
        concurrency = int(concurrency_str)
        config = config.strip().lower()
        if config not in {"rds", "aurora"}:
            continue
        metrics: list[Metric] = []
        for filename in sorted(os.listdir(entry_path)):
            if not filename.endswith("_requests.csv"):
                continue
            csv_path = os.path.join(entry_path, filename)
            metric = read_aggregated_metrics(csv_path)
            if metric is None:
                print(f"Warning: missing aggregated metrics in {csv_path}")
                continue
            metrics.append(metric)
        if not metrics:
            continue
        results.setdefault(concurrency, {}).setdefault(config, []).extend(metrics)
    return results


def ensure_output_dir(output_dir: str) -> None:
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)


def plot_requests_per_s(
    data: dict[int, dict[str, list[Metric]]], output_dir: str
) -> None:
    concurrencies = sorted(data.keys())
    plt.figure(figsize=(9, 5))
    for config, color in [("rds", "#1f77b4"), ("aurora", "#ff7f0e")]:
        means = []
        stds = []
        xs = []
        for concurrency in concurrencies:
            runs = data.get(concurrency, {}).get(config, [])
            values = [m["requests_per_s"] for m in runs]
            if not values:
                continue
            mean_val, std_val = mean_std(values)
            xs.append(concurrency)
            means.append(mean_val)
            stds.append(std_val)
        if xs:
            lower = [mean - std for mean, std in zip(means, stds)]
            upper = [mean + std for mean, std in zip(means, stds)]
            plt.plot(
                xs,
                means,
                marker="o",
                label=config.upper(),
                color=color,
            )
            plt.fill_between(
                xs,
                lower,
                upper,
                color=color,
                alpha=0.18,
                linewidth=0,
            )
    plt.title("Requests per Second")
    plt.xlabel("Concurrent Users")
    plt.ylabel("Requests/s")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "requests_per_second.png"), dpi=200)
    plt.close()


def plot_error_rate(data: dict[int, dict[str, list[Metric]]], output_dir: str) -> None:
    concurrencies = sorted(data.keys())
    plt.figure(figsize=(9, 5))
    for config, color in [("rds", "#1f77b4"), ("aurora", "#ff7f0e")]:
        means = []
        stds = []
        xs = []
        for concurrency in concurrencies:
            runs = data.get(concurrency, {}).get(config, [])
            values = [m["error_rate"] for m in runs]
            if not values:
                continue
            mean_val, std_val = mean_std(values)
            xs.append(concurrency)
            means.append(mean_val)
            stds.append(std_val)
        if xs:
            lower = [mean - std for mean, std in zip(means, stds)]
            upper = [mean + std for mean, std in zip(means, stds)]
            plt.plot(
                xs,
                means,
                marker="o",
                label=config.upper(),
                color=color,
            )
            plt.fill_between(
                xs,
                lower,
                upper,
                color=color,
                alpha=0.18,
                linewidth=0,
            )
    plt.title("Error Rate")
    plt.xlabel("Concurrent Users")
    plt.ylabel("Error Rate")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "error_rate.png"), dpi=200)
    plt.close()


def plot_latency(data: dict[int, dict[str, list[Metric]]], output_dir: str) -> None:
    concurrencies = sorted(data.keys())
    plt.figure(figsize=(9, 5))
    series = [
        ("rds", "median_ms", "RDS median", "#1f77b4"),
        ("rds", "p95_ms", "RDS p95", "#1f77b4"),
        ("aurora", "median_ms", "Aurora median", "#ff7f0e"),
        ("aurora", "p95_ms", "Aurora p95", "#ff7f0e"),
    ]
    for config, key, label, color in series:
        means = []
        stds = []
        xs = []
        for concurrency in concurrencies:
            runs = data.get(concurrency, {}).get(config, [])
            values = [m[key] for m in runs]
            if not values:
                continue
            mean_val, std_val = mean_std(values)
            xs.append(concurrency)
            means.append(mean_val)
            stds.append(std_val)
        if xs:
            line_style = "--" if "p95" in label.lower() else "-"
            lower = [mean - std for mean, std in zip(means, stds)]
            upper = [mean + std for mean, std in zip(means, stds)]
            plt.plot(
                xs,
                means,
                marker="o",
                label=label,
                color=color,
                linestyle=line_style,
            )
            plt.fill_between(
                xs,
                lower,
                upper,
                color=color,
                alpha=0.14 if "p95" in label.lower() else 0.18,
                linewidth=0,
            )
    plt.title("Latency")
    plt.xlabel("Concurrent Users")
    plt.ylabel("Latency (ms)")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "latency.png"), dpi=200)
    plt.close()


def format_value(mean_val: float, std_val: float, suffix: str = "") -> str:
    if math.isnan(mean_val):
        return "n/a"
    if std_val == 0:
        return f"{mean_val:.3f}{suffix}"
    return f"{mean_val:.3f} ± {std_val:.3f}{suffix}"


def print_table(data: dict[int, dict[str, list[Metric]]]) -> None:
    rows = []
    for concurrency in sorted(data.keys()):
        for config in ["rds", "aurora"]:
            runs = data.get(concurrency, {}).get(config, [])
            if not runs:
                continue
            req_mean, req_std = mean_std([m["requests_per_s"] for m in runs])
            err_mean, err_std = mean_std([m["error_rate"] for m in runs])
            med_mean, med_std = mean_std([m["median_ms"] for m in runs])
            p95_mean, p95_std = mean_std([m["p95_ms"] for m in runs])
            rows.append(
                [
                    concurrency,
                    config.upper(),
                    format_value(req_mean, req_std),
                    format_value(err_mean, err_std),
                    format_value(med_mean, med_std, " ms"),
                    format_value(p95_mean, p95_std, " ms"),
                    len(runs),
                ]
            )

    headers = [
        "Users",
        "Config",
        "Requests/s",
        "Error Rate",
        "Median",
        "P95",
        "Runs",
    ]

    print("\nMetrics summary")
    print(tabulate(rows, headers=headers, tablefmt="github"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot Locust results for RDS vs Aurora."
    )
    parser.add_argument(
        "--data-dir",
        default=os.path.join(os.path.dirname(__file__), "data"),
        help="Path to the data directory containing *-rds and *-aurora folders.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "plots"),
        help="Directory to write plots into.",
    )
    args = parser.parse_args()

    data = gather_runs(args.data_dir)
    if not data:
        raise SystemExit("No valid data found. Check your data directory.")

    ensure_output_dir(args.output_dir)

    plot_requests_per_s(data, args.output_dir)
    plot_error_rate(data, args.output_dir)
    plot_latency(data, args.output_dir)
    print_table(data)


if __name__ == "__main__":
    main()
