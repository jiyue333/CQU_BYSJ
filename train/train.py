"""
YOLO 统一训练入口
用法:
    python train/train.py --profile yolo26n              # 使用预置模型配置
    python train/train.py --profile yolo26n --data crowdhuman.yaml --epochs 200
    python train/train.py --profile yolo26n --resume     # 恢复训练
    python train/train.py --model models/yolo26n.pt      # 直接指定模型, 不用 profile
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

# 在任何 ultralytics 导入之前设置 API Key
os.environ.setdefault("ULTRALYTICS_API_KEY", "ul_dbf802bcd5b59b673b530296a6afd64dc29569b5")


def _find_root() -> Path:
    """定位项目根目录：优先 PROJECT_ROOT 环境变量，其次从脚本位置推导。"""
    if "PROJECT_ROOT" in os.environ:
        return Path(os.environ["PROJECT_ROOT"]).resolve()
    return Path(__file__).resolve().parent.parent


ROOT = _find_root()
TRAIN_DIR = ROOT / "train"
PROFILES_DIR = TRAIN_DIR / "profiles"
BASE_CONFIG = TRAIN_DIR / "config.yaml"


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_configs(base: dict, override: dict) -> dict:
    merged = base.copy()
    for k, v in override.items():
        if v is not None:
            merged[k] = v
    return merged


def parse_cli_overrides(args: list[str]) -> dict:
    overrides = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i].lstrip("-")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                val = args[i + 1]
                if val.lower() in ("true", "false"):
                    val = val.lower() == "true"
                elif val.replace(".", "", 1).replace("-", "", 1).isdigit():
                    val = float(val) if "." in val else int(val)
                elif val == "null":
                    val = None
                overrides[key] = val
                i += 2
                continue
            else:
                overrides[key] = True
        i += 1
    return overrides


def main():
    parser = argparse.ArgumentParser(description="YOLO 统一训练脚本")
    parser.add_argument("--profile", type=str, help="模型配置名 (profiles/ 下的文件名, 不含 .yaml)")
    known, remaining = parser.parse_known_args()

    config = load_yaml(BASE_CONFIG)

    if known.profile:
        profile_path = PROFILES_DIR / f"{known.profile}.yaml"
        if not profile_path.exists():
            available = [p.stem for p in PROFILES_DIR.glob("*.yaml")]
            print(f"[错误] 找不到 profile: {known.profile}")
            print(f"[可用] {', '.join(available)}")
            sys.exit(1)
        config = merge_configs(config, load_yaml(profile_path))

    config = merge_configs(config, parse_cli_overrides(remaining))

    sys.path.insert(0, str(ROOT))
    from yolo import YOLO

    model_path = config.pop("model", None)
    if not model_path:
        print("[错误] 未指定模型, 请通过 --profile 或 --model 指定")
        sys.exit(1)

    model_path = Path(model_path)
    # .yaml 配置文件保留原名让 Ultralytics 内部搜索 cfg/ 目录解析；
    # .pt 权重文件才需要拼项目根路径
    if model_path.suffix != ".yaml" and not model_path.is_absolute():
        model_path = ROOT / model_path

    model = YOLO(str(model_path))
    results = model.train(**{k: v for k, v in config.items() if v is not None})
    return results


if __name__ == "__main__":
    main()
