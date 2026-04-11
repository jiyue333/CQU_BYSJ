"""
YOLO 统一验证入口 — 支持 .ndjson / ul:// / .yaml 数据源
用法:
    python train/val.py --profile yolo26n --data train/dataset/crowdhuman-dataset-people-and-faces-19k.ndjson
    python train/val.py --profile yolo26n --data ul://juliet-heath/datasets/crowdhuman-dataset-people-and-faces-19k
    python train/val.py --profile yolo26n --data crowdhuman.yaml
    python train/val.py --model models/yolo26n.pt --data ... --batch 16 --imgsz 640

NDJSON / ul:// 模式会自动调用框架内置 convert_ndjson_to_yolo:
    下载图片 → 生成标注 → 生成 dataset.yaml → 运行验证
    已下载的图片会被缓存, 重复运行不会重复下载。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
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


def resolve_data(data_path: str) -> str:
    """NDJSON / ul:// 自动转换为 YOLO dataset.yaml, 其他格式原样返回."""
    if data_path.endswith(".ndjson") or (data_path.startswith("ul://") and "/datasets/" in data_path):
        from yolo.data.converter import convert_ndjson_to_yolo
        from yolo.utils.checks import check_file

        output_dir = TRAIN_DIR / "dataset"
        yaml_path = asyncio.run(convert_ndjson_to_yolo(check_file(data_path), output_path=output_dir))
        print(f"[数据] 已转换为 YOLO 格式: {yaml_path}")
        return str(yaml_path)
    return data_path


def main():
    parser = argparse.ArgumentParser(description="YOLO 统一验证脚本")
    parser.add_argument("--profile", type=str, help="模型配置名 (profiles/ 下的文件名)")
    parser.add_argument("--model", type=str, help="直接指定模型路径 (覆盖 profile)")
    parser.add_argument("--data", type=str, help="数据源 (.ndjson / ul:// / .yaml)")
    parser.add_argument("--split", type=str, default="val", help="验证 split (default: val)")
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--imgsz", type=int, default=None)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--conf", type=float, default=None, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=None, help="NMS IoU 阈值")
    parser.add_argument("--no-comet", action="store_true", help="禁用 Comet ML")
    parser.add_argument("--name", type=str, default=None, help="输出目录名")
    args = parser.parse_args()

    # 1. 加载基础配置
    config = load_yaml(BASE_CONFIG)

    # 2. Profile 覆盖
    if args.profile:
        profile_path = PROFILES_DIR / f"{args.profile}.yaml"
        if not profile_path.exists():
            available = [p.stem for p in PROFILES_DIR.glob("*.yaml")]
            print(f"[错误] 找不到 profile: {args.profile}, 可用: {', '.join(available)}")
            sys.exit(1)
        config = merge_configs(config, load_yaml(profile_path))

    # 3. 确定模型
    model_path = args.model or config.get("model")
    if not model_path:
        print("[错误] 未指定模型, 请通过 --profile 或 --model 指定")
        sys.exit(1)
    model_path = Path(model_path)
    if not model_path.is_absolute():
        model_path = ROOT / model_path

    # 4. 准备数据 (NDJSON / ul:// 自动转换)
    sys.path.insert(0, str(ROOT))
    data_arg = args.data or config.get("data", "coco8.yaml")
    # 相对路径转绝对 (跳过 URL 和 ul:// 协议)
    if not data_arg.startswith(("http://", "https://", "ul://")) and not Path(data_arg).is_absolute():
        candidate = ROOT / data_arg
        if candidate.exists():
            data_arg = str(candidate)
    data_yaml = resolve_data(data_arg)

    # 5. Comet (可选)
    if not args.no_comet:
        try:
            import comet_ml
            project_name = args.name or config.get("name", "yolo-val")
            comet_ml.login(project_name=f"CQU_BYSJ-{project_name}")
            print(f"[Comet] 已登录, project=CQU_BYSJ-{project_name}")
        except Exception:
            pass

    # 6. 构造验证参数
    from yolo import YOLO

    val_kwargs = {
        "data": data_yaml,
        "split": args.split,
        "plots": True,
        "project": "runs/val",
        "name": args.name or config.get("name", "exp"),
    }
    for key, cli_val, cfg_key in [
        ("batch", args.batch, "batch"),
        ("imgsz", args.imgsz, "imgsz"),
        ("device", args.device, "device"),
        ("workers", args.workers, "workers"),
    ]:
        val_kwargs[key] = cli_val if cli_val is not None else config.get(cfg_key)
    if args.conf is not None:
        val_kwargs["conf"] = args.conf
    if args.iou is not None:
        val_kwargs["iou"] = args.iou

    print(f"\n{'=' * 60}")
    print(f"  模型: {model_path}")
    print(f"  数据: {data_yaml}")
    print(f"  Split: {args.split}")
    print(f"  设备: {val_kwargs.get('device', 'auto')}")
    print(f"  批大小: {val_kwargs.get('batch', 16)}")
    print(f"  图像尺寸: {val_kwargs.get('imgsz', 640)}")
    print(f"  输出: {val_kwargs['project']}/{val_kwargs['name']}")
    print(f"{'=' * 60}\n")

    model = YOLO(str(model_path))
    results = model.val(**val_kwargs)

    # 7. 打印摘要
    print(f"\n{'=' * 60}")
    print("  验证结果摘要")
    print(f"{'=' * 60}")
    if hasattr(results, "box"):
        box = results.box
        print(f"  mAP50:    {box.map50:.4f}")
        print(f"  mAP50-95: {box.map:.4f}")
        if hasattr(box, "mp") and hasattr(box, "mr"):
            print(f"  Precision: {box.mp:.4f}")
            print(f"  Recall:    {box.mr:.4f}")
        if hasattr(box, "f1") and len(box.f1) > 0:
            import numpy as np
            valid_f1 = box.f1[box.f1 > 0]
            if len(valid_f1) > 0:
                print(f"  F1 (mean): {float(np.mean(valid_f1)):.4f}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
