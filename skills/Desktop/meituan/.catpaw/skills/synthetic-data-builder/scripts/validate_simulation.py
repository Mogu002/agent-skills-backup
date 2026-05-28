#!/usr/bin/env python3
"""
validate_simulation.py — 仿真数据均衡态/全量验证工具

用法：
  # 均衡态验证（开发早期，无剧本时）
  python validate_simulation.py <output_dir> --baseline

  # 全量验证（剧本开发完成后）
  python validate_simulation.py <output_dir> --full

  # 指定具体文件（可选，默认自动查找）
  python validate_simulation.py <output_dir> --baseline \
      --orders orders.csv \
      --demand demand_daily.csv \
      --supply supply_daily.csv

output_dir: 模拟器导出的数据目录（包含交易明细表、需求侧日表、供给侧日表）

退出码：
  0 = 验证通过
  1 = 存在 WARNING（可接受，需人工判断）
  2 = 存在 ERROR（必须修复）
"""

import argparse
import sys
import os
import glob
from pathlib import Path

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: 缺少依赖，请运行: pip install pandas numpy")
    sys.exit(2)


# ─── 工具函数 ───────────────────────────────────────────────────────────────

def find_file(output_dir: str, patterns: list[str]) -> str | None:
    """在 output_dir 中按候选文件名模式查找文件。"""
    for pat in patterns:
        matches = glob.glob(os.path.join(output_dir, pat))
        if matches:
            return matches[0]
    return None


def load_table(path: str | None, name: str) -> pd.DataFrame | None:
    if not path or not os.path.exists(path):
        return None
    try:
        if path.endswith(".csv"):
            return pd.read_csv(path)
        elif path.endswith((".xlsx", ".xls")):
            return pd.read_excel(path)
        elif path.endswith(".parquet"):
            return pd.read_parquet(path)
    except Exception as e:
        print(f"  ⚠️  无法读取 {name}（{path}）: {e}")
    return None


class Validator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passes = []

    def ok(self, msg: str):
        self.passes.append(msg)
        print(f"  ✅  {msg}")

    def warn(self, msg: str):
        self.warnings.append(msg)
        print(f"  ⚠️   {msg}")

    def error(self, msg: str):
        self.errors.append(msg)
        print(f"  ❌  {msg}")

    def check(self, condition: bool, ok_msg: str, fail_msg: str, level: str = "error"):
        if condition:
            self.ok(ok_msg)
        else:
            if level == "warning":
                self.warn(fail_msg)
            else:
                self.error(fail_msg)

    def summary(self) -> int:
        print()
        print("=" * 60)
        print(f"验证结果：{len(self.passes)} 通过 / {len(self.warnings)} 警告 / {len(self.errors)} 错误")
        if self.errors:
            print("❌ 存在错误，必须修复后再开发剧本层。")
            return 2
        if self.warnings:
            print("⚠️  存在警告，建议人工确认后继续。")
            return 1
        print("✅ 全部通过，均衡态参数标定合理。")
        return 0


# ─── 验证模块 ───────────────────────────────────────────────────────────────

def validate_orders(v: Validator, df: pd.DataFrame):
    """验证交易明细表。"""
    print("\n【交易明细表】")
    total = len(df)
    v.check(total > 0, f"共 {total} 条交易记录", "交易明细表为空")

    # Ground Truth 字段完整性
    gt_cols = [c for c in df.columns if c.startswith("_")]
    if gt_cols:
        v.ok(f"包含 {len(gt_cols)} 个 Ground Truth 字段: {gt_cols[:5]}{'...' if len(gt_cols) > 5 else ''}")
    else:
        v.warn("未找到以 '_' 开头的 Ground Truth 字段，请确认是否为 Agent 可见层（已剥离）")

    # 成交率合理性
    if "_exit_reason" in df.columns:
        success_rate = (df["_exit_reason"].isna() | (df["_exit_reason"] == "success")).mean()
        v.check(
            0.10 <= success_rate <= 0.90,
            f"成交率 {success_rate:.1%}（合理区间 10%~90%）",
            f"成交率 {success_rate:.1%} 超出合理区间（10%~90%），请检查决策漏斗参数",
        )
    elif "is_completed" in df.columns or "status" in df.columns:
        col = "is_completed" if "is_completed" in df.columns else "status"
        rate = df[col].astype(str).str.lower().isin(["true", "1", "success", "completed"]).mean()
        v.check(
            0.10 <= rate <= 0.90,
            f"成交率 {rate:.1%}（合理区间 10%~90%）",
            f"成交率 {rate:.1%} 超出合理区间",
        )
    else:
        v.warn("未找到成交状态字段（_exit_reason / is_completed / status），跳过成交率验证")

    # 时间列检查
    date_cols = [c for c in df.columns if "day" in c.lower() or "date" in c.lower()]
    if date_cols:
        col = date_cols[0]
        days = df[col].nunique()
        v.check(days >= 5, f"数据覆盖 {days} 天", f"数据仅覆盖 {days} 天（建议 ≥5 天验证稳定性）", "warning")


def validate_demand_daily(v: Validator, df: pd.DataFrame):
    """验证需求侧日表。"""
    print("\n【需求侧日表】")
    v.check(len(df) > 0, f"共 {len(df)} 行记录", "需求侧日表为空")

    # 日活跃率波动
    active_cols = [c for c in df.columns if "active" in c.lower() or "活跃" in c]
    date_cols = [c for c in df.columns if "day" in c.lower() or "date" in c.lower()]
    if active_cols and date_cols:
        day_col = date_cols[0]
        active_col = active_cols[0]
        daily_rates = df.groupby(day_col)[active_col].mean()
        cv = daily_rates.std() / daily_rates.mean() if daily_rates.mean() > 0 else 0
        v.check(
            cv < 0.3,
            f"日活跃率变异系数 CV={cv:.2f}（<0.3，波动合理）",
            f"日活跃率波动过大 CV={cv:.2f}（≥0.3），均衡态下不应有剧烈波动",
            "warning",
        )

    # 新老用户比例检查
    lifecycle_cols = [c for c in df.columns if "lifecycle" in c.lower() or "new" in c.lower() or "生命周期" in c]
    if lifecycle_cols:
        col = lifecycle_cols[0]
        new_ratio = df[col].astype(str).str.lower().str.contains("new|新").mean()
        v.check(
            0.02 <= new_ratio <= 0.50,
            f"新用户占比 {new_ratio:.1%}（合理区间 2%~50%）",
            f"新用户占比 {new_ratio:.1%} 异常，请检查实体初始化参数",
            "warning",
        )


def validate_supply_daily(v: Validator, df: pd.DataFrame):
    """验证供给侧日表。"""
    print("\n【供给侧日表】")
    v.check(len(df) > 0, f"共 {len(df)} 行记录", "供给侧日表为空")

    # 供给侧 30 天留存率（以 lifecycle=active 估算）
    date_cols = [c for c in df.columns if "day" in c.lower() or "date" in c.lower()]
    lifecycle_cols = [c for c in df.columns if "lifecycle" in c.lower() or "status" in c.lower() or "active" in c.lower()]
    entity_cols = [c for c in df.columns if "id" in c.lower() or "driver" in c.lower() or "supply" in c.lower()]

    if date_cols and lifecycle_cols and entity_cols:
        day_col = date_cols[0]
        lc_col = lifecycle_cols[0]
        id_col = entity_cols[0]
        days = sorted(df[day_col].unique())
        if len(days) >= 2:
            day1_active = set(df[df[day_col] == days[0]][id_col])
            last_day_active = set(df[df[day_col] == days[-1]][id_col])
            # 只看在第1天就活跃的人，在最后一天还活跃的比例
            if day1_active:
                retention = len(day1_active & last_day_active) / len(day1_active)
                days_span = len(days)
                threshold = 0.7 if days_span >= 20 else 0.5
                v.check(
                    retention >= threshold,
                    f"供给侧 {days_span} 天留存率 {retention:.1%}（≥{threshold:.0%}）",
                    f"供给侧留存率 {retention:.1%} 过低，可能存在参数问题导致人口骤降",
                )

    # 满意度均衡区间检查
    satisfaction_cols = [c for c in df.columns if "satisfaction" in c.lower() or "满意度" in c]
    if satisfaction_cols:
        col = satisfaction_cols[0]
        mean_sat = df[col].mean()
        v.check(
            0.35 <= mean_sat <= 0.65,
            f"供给侧平均满意度 {mean_sat:.3f}（均衡区间 0.35~0.65）",
            f"供给侧满意度 {mean_sat:.3f} 偏离均衡区间，飞轮参数需调整",
            "warning",
        )

    # 收益指标合理性（不能有大量 0 或 NaN）
    revenue_cols = [c for c in df.columns if any(k in c.lower() for k in ["iph", "revenue", "income", "收入", "gmv"])]
    if revenue_cols:
        col = revenue_cols[0]
        zero_ratio = (df[col] == 0).mean()
        nan_ratio = df[col].isna().mean()
        v.check(
            zero_ratio < 0.5,
            f"供给侧收益指标（{col}）零值率 {zero_ratio:.1%}（<50%）",
            f"供给侧收益指标（{col}）有 {zero_ratio:.1%} 为零，请检查成交逻辑",
            "warning",
        )
        if nan_ratio > 0.1:
            v.warn(f"供给侧收益指标（{col}）有 {nan_ratio:.1%} 为 NaN，注意清洗")


def validate_ground_truth_consistency(v: Validator, orders: pd.DataFrame, demand: pd.DataFrame):
    """交叉验证：Ground Truth 字段与聚合表是否一致。"""
    print("\n【交叉一致性验证】")

    # 如果两张表都有日期列，比较日均成单量
    date_cols_o = [c for c in orders.columns if "day" in c.lower() or "date" in c.lower()]
    date_cols_d = [c for c in demand.columns if "day" in c.lower() or "date" in c.lower()]

    if not date_cols_o or not date_cols_d:
        v.warn("未找到日期字段，跳过交叉一致性验证")
        return

    # 从交易明细推算日均成单量
    orders_per_day = orders.groupby(date_cols_o[0]).size()
    avg_orders = orders_per_day.mean()
    v.ok(f"日均交易事件数 {avg_orders:.0f}（来自交易明细表）")

    # 检查日表行数与交易明细日期范围是否大体一致
    days_in_orders = orders[date_cols_o[0]].nunique()
    days_in_demand = demand[date_cols_d[0]].nunique()
    v.check(
        abs(days_in_orders - days_in_demand) <= 1,
        f"交易明细（{days_in_orders}天）与需求侧日表（{days_in_demand}天）天数一致",
        f"天数不一致：交易明细 {days_in_orders} 天，需求侧日表 {days_in_demand} 天",
        "warning",
    )


def validate_scenario_impact(v: Validator, df: pd.DataFrame, scenario_start_day: int | None):
    """验证剧本是否产生了可观察的指标变化（仅全量模式）。"""
    print("\n【剧本效果验证】")

    if scenario_start_day is None:
        v.warn("未指定 --scenario-day，跳过剧本效果验证")
        return

    date_cols = [c for c in df.columns if "day" in c.lower() or "date" in c.lower()]
    if not date_cols:
        v.warn("未找到日期字段，跳过剧本效果验证")
        return

    day_col = date_cols[0]
    pre = df[df[day_col] < scenario_start_day]
    post = df[df[day_col] >= scenario_start_day]

    if len(pre) == 0 or len(post) == 0:
        v.warn(f"按 --scenario-day={scenario_start_day} 分割后，前或后段数据为空")
        return

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != day_col and not c.startswith("_")]

    significant_changes = []
    for col in numeric_cols[:10]:  # 只检查前10个数值列
        pre_mean = pre[col].mean()
        post_mean = post[col].mean()
        if pre_mean != 0:
            change = (post_mean - pre_mean) / abs(pre_mean)
            if abs(change) >= 0.05:
                significant_changes.append((col, change))

    if significant_changes:
        v.ok(f"剧本生效后，{len(significant_changes)} 个指标发生 ≥5% 变化：")
        for col, change in significant_changes[:5]:
            direction = "↑" if change > 0 else "↓"
            print(f"      {col}: {change:+.1%} {direction}")
    else:
        v.warn(f"剧本生效后（第{scenario_start_day}天起），无明显指标变化，请检查剧本是否正确生效")


# ─── 主函数 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="仿真数据验证工具")
    parser.add_argument("output_dir", help="模拟器数据输出目录")
    parser.add_argument("--baseline", action="store_true", help="均衡态验证模式（无剧本）")
    parser.add_argument("--full", action="store_true", help="全量验证模式（含剧本效果）")
    parser.add_argument("--orders", help="交易明细表文件路径（可选，默认自动查找）")
    parser.add_argument("--demand", help="需求侧日表文件路径（可选，默认自动查找）")
    parser.add_argument("--supply", help="供给侧日表文件路径（可选，默认自动查找）")
    parser.add_argument("--scenario-day", type=int, help="剧本生效的天数（用于--full模式的效果验证）")
    args = parser.parse_args()

    if not args.baseline and not args.full:
        print("请指定验证模式：--baseline 或 --full")
        sys.exit(2)

    output_dir = args.output_dir
    if not os.path.isdir(output_dir):
        print(f"ERROR: 目录不存在: {output_dir}")
        sys.exit(2)

    # 自动查找文件
    orders_path = args.orders or find_file(output_dir, ["*order*", "*transaction*", "*交易*", "*.csv"])
    demand_path = args.demand or find_file(output_dir, ["*demand*daily*", "*乘客*日*", "*user*daily*", "*passenger*"])
    supply_path = args.supply or find_file(output_dir, ["*supply*daily*", "*司机*日*", "*driver*daily*"])

    print(f"验证目录：{output_dir}")
    print(f"模式：{'均衡态' if args.baseline else '全量'}")
    print(f"交易明细：{orders_path or '未找到'}")
    print(f"需求侧日表：{demand_path or '未找到'}")
    print(f"供给侧日表：{supply_path or '未找到'}")

    orders = load_table(orders_path, "交易明细表")
    demand = load_table(demand_path, "需求侧日表")
    supply = load_table(supply_path, "供给侧日表")

    if orders is None and demand is None and supply is None:
        print("\nERROR: 在目录中未找到任何可读数据文件（csv/xlsx/parquet）。")
        print("提示：可使用 --orders / --demand / --supply 显式指定文件路径。")
        sys.exit(2)

    v = Validator()

    if orders is not None:
        validate_orders(v, orders)

    if demand is not None:
        validate_demand_daily(v, demand)

    if supply is not None:
        validate_supply_daily(v, supply)

    if orders is not None and demand is not None:
        validate_ground_truth_consistency(v, orders, demand)

    if args.full and orders is not None:
        validate_scenario_impact(v, orders, args.scenario_day)

    exit_code = v.summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
