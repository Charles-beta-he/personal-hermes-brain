#!/usr/bin/env python3
"""
pricing.py — 多模型成本感知引擎
从 config.yaml pricing 块加载定价元数据, 提供时间感知的成本估算

核心函数:
  load_pricing(config_path)     → PricingTable
  effective_rate(model, now_utc)→ (input_rate, output_rate, schedule_label)
  is_off_peak(model, now_utc)  → bool
  is_free_active(model, now_utc)→ bool
  estimate_cost(model, tokens_in, tokens_out, now_utc) → float (USD)

用法:
  from pricing import load_pricing
  pt = load_pricing()
  cost = pt.estimate_cost("mimo-v2.5-pro", 1000, 500)
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import yaml


class PricingTable:
    """多模型定价表 — 从 config.yaml pricing 块加载"""

    def __init__(self, raw: dict):
        self.defaults = raw.get("defaults", {})
        self.schedules = raw.get("schedules", {})
        self.models = raw.get("models", {})

    def __repr__(self):
        return f"PricingTable({len(self.models)} models)"

    def _get_schedule_multiplier(self, model_name: str, now_utc: datetime) -> Tuple[float, str]:
        """获取当前时段的费率乘数"""
        model = self.models.get(model_name, {})
        schedule_ref = model.get("schedule_ref")
        if not schedule_ref or schedule_ref not in self.schedules:
            return 1.0, "default"

        now_hour = now_utc.hour
        for slot in self.schedules[schedule_ref]:
            window = slot.get("window", "")
            try:
                start_str, end_str = window.split("-")
                start = int(start_str.split(":")[0])
                end = int(end_str.split(":")[0])
                
                # 处理跨日窗口 (如 22:00-06:00)
                if start <= end:
                    in_window = start <= now_hour < end
                else:
                    in_window = now_hour >= start or now_hour < end
                
                if in_window:
                    return slot.get("multiplier", 1.0), slot.get("label", "unknown")
            except (ValueError, AttributeError):
                continue

        return 1.0, "default"

    def effective_rate(
        self, model_name: str, now_utc: Optional[datetime] = None
    ) -> Tuple[float, float, str]:
        """获取有效费率 (考虑时段乘数 + promotion + free 状态)
        
        Returns: (input_rate_per_1m, output_rate_per_1m, schedule_label)
        """
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)

        model = self.models.get(model_name, {})
        
        # 检查 free 状态
        free_info = model.get("free", {})
        if free_info.get("active"):
            expires_str = free_info.get("expires_at", "")
            if expires_str:
                try:
                    expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                    if now_utc < expires:
                        return 0.0, 0.0, "free"
                except (ValueError, TypeError):
                    pass

        # 检查 promotion 状态
        promo = model.get("promotion", {})
        if promo.get("active"):
            expires_str = promo.get("expires_at", "")
            if expires_str:
                try:
                    expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                    if now_utc < expires:
                        # TTL warning: within 7 days of expiry
                        days_left = (expires - now_utc).total_seconds() / 86400
                        if days_left <= 7:
                            import logging
                            logging.getLogger("pricing").warning(
                                "PROMO_EXPIRING_SOON: %s promotion expires in %.1f days (%s). "
                                "Post-promo rate will be ~%.1fx higher. Consider shifting workload.",
                                model_name, days_left, expires_str,
                                (model.get("output", 1) / max(promo.get("promo_output", 1), 0.01)),
                            )
                        return (
                            round(promo.get("promo_input", 0), 4),
                            round(promo.get("promo_output", 0), 4),
                            promo.get("label", "promo"),
                        )
                except (ValueError, TypeError):
                    pass

        # 正常费率
        base_in = model.get("input", 0.0)
        base_out = model.get("output", 0.0)
        multiplier, label = self._get_schedule_multiplier(model_name, now_utc)
        
        return (
            round(base_in * multiplier, 4),
            round(base_out * multiplier, 4),
            label,
        )

    def is_off_peak(self, model_name: str, now_utc: Optional[datetime] = None) -> bool:
        """判断当前是否为 off-peak 时段"""
        _, _, label = self.effective_rate(model_name, now_utc)
        return label == "off_peak"

    def is_free_active(self, model_name: str, now_utc: Optional[datetime] = None) -> bool:
        """判断模型当前是否免费"""
        _, _, label = self.effective_rate(model_name, now_utc)
        return label == "free"

    def estimate_cost(
        self,
        model_name: str,
        tokens_in: int,
        tokens_out: int = 0,
        now_utc: Optional[datetime] = None,
    ) -> float:
        """估算调用成本 (USD)"""
        in_rate, out_rate, _ = self.effective_rate(model_name, now_utc)
        # 费率是 per 1M tokens
        cost = (tokens_in * in_rate + tokens_out * out_rate) / 1_000_000
        return round(cost, 6)

    def get_candidate_models(self, task_tier: str) -> List[str]:
        """获取指定任务层级的候选模型列表"""
        candidates = []
        for model_name, model_info in self.models.items():
            groups = model_info.get("candidate_groups", [])
            if task_tier in groups:
                candidates.append(model_name)
        return candidates

    def get_cache_hit_rates(self, model_name: str) -> Tuple[float, float]:
        """获取缓存命中费率 (1/10 of base)"""
        model = self.models.get(model_name, {})
        return (
            model.get("cache_hit_input", 0.0),
            model.get("cache_hit_output", 0.0),
        )

    def get_tier(self, model_name: str) -> str:
        """获取模型层级"""
        return self.models.get(model_name, {}).get("tier", "unknown")

    def get_provider(self, model_name: str) -> str:
        """获取模型 provider"""
        return self.models.get(model_name, {}).get("provider", "unknown")


def load_pricing(config_path: str = None) -> Optional[PricingTable]:
    """从 config.yaml 加载定价表"""
    if config_path is None:
        config_path = os.path.expanduser(
            os.environ.get("HERMES_CONFIG", "~/.hermes/config.yaml")
        )
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        pricing_raw = config.get("pricing", {})
        if not pricing_raw.get("models"):
            return None
        return PricingTable(pricing_raw)
    except (yaml.YAMLError, FileNotFoundError, OSError) as e:
        print(f"Warning: failed to load pricing: {e}", file=sys.stderr)
        return None


# ── CLI ──
def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Pricing — 多模型成本感知")
    sub = parser.add_subparsers(dest="cmd")

    rate = sub.add_parser("rate", help="查询有效费率")
    rate.add_argument("--model", required=True)
    rate.add_argument("--hour", type=int, default=None, help="模拟 UTC 小时 (0-23)")

    cost = sub.add_parser("cost", help="估算调用成本")
    cost.add_argument("--model", required=True)
    cost.add_argument("--tokens-in", type=int, default=1000)
    cost.add_argument("--tokens-out", type=int, default=500)
    cost.add_argument("--hour", type=int, default=None)

    ls = sub.add_parser("list", help="列出所有模型定价")
    ls.add_argument("--tier", default=None)
    ls.add_argument("--hour", type=int, default=None)

    free = sub.add_parser("free", help="列出当前免费模型")

    args = parser.parse_args()
    pt = load_pricing()
    if pt is None:
        print("No pricing config found.")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    if hasattr(args, "hour") and args.hour is not None:
        now = now.replace(hour=args.hour, minute=0, second=0, microsecond=0)

    if args.cmd == "rate":
        in_r, out_r, label = pt.effective_rate(args.model, now)
        print(f"model={args.model}  hour={now.hour:02d}:00 UTC  label={label}")
        print(f"  input:  ${in_r}/1M tokens")
        print(f"  output: ${out_r}/1M tokens")
        print(f"  free:   {pt.is_free_active(args.model, now)}")
        print(f"  off-peak: {pt.is_off_peak(args.model, now)}")

    elif args.cmd == "cost":
        c = pt.estimate_cost(args.model, args.tokens_in, args.tokens_out, now)
        in_r, out_r, label = pt.effective_rate(args.model, now)
        print(f"model={args.model}  tokens={args.tokens_in}/{args.tokens_out}  hour={now.hour:02d}:00 UTC")
        print(f"  rate: ${in_r}/${out_r}/1M ({label})")
        print(f"  estimated cost: ${c}")

    elif args.cmd == "list":
        for model_name, info in pt.models.items():
            tier = info.get("tier", "?")
            if args.tier and tier != args.tier:
                continue
            in_r, out_r, label = pt.effective_rate(model_name, now)
            free_flag = " FREE" if pt.is_free_active(model_name, now) else ""
            print(f"  {model_name:25s} {tier:10s} ${in_r:6.2f}/${out_r:6.2f}/1M ({label:8s}){free_flag}")

    elif args.cmd == "free":
        print(f"Free models at {now.strftime('%Y-%m-%d %H:00 UTC')}:")
        for model_name in pt.models:
            if pt.is_free_active(model_name, now):
                info = pt.models[model_name]
                expires = info.get("free", {}).get("expires_at", "?")
                print(f"  {model_name}  expires={expires}")

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
