"""
YOLO 统一训练入口
用法:
    python train/train.py --profile yolo26n              # 使用预置模型配置
    python train/train.py --profile yolo26n --data crowdhuman.yaml --epochs 200
    python train/train.py --profile yolo26n --resume     # 恢复训练
    python train/train.py --model models/yolo26n.pt      # 直接指定模型, 不用 profile
    python train/train.py --profile yolo26n --no-comet   # 禁用 Comet 日志

Comet ML 集成说明:
    Ultralytics 内置 Comet 回调, 安装 comet_ml 并设置 API Key 后自动记录:
    - 训练损失 (box_loss, cls_loss, dfl_loss)
    - 验证指标 (mAP50, mAP50-95, precision, recall)
    - 学习率曲线
    - 模型参数量、GFLOPs、PyTorch 推理速度 (首个 epoch)
    - 模型权重 (best.pt, last.pt)
    - 混淆矩阵、F1/P/R/PR 曲线图
    - 图像预测样本、系统资源使用

    注意: Comet 内置回调已记录 GFLOPs 和 inference_time,
    F1 曲线图也会自动上传, 但 F1 数值不作为标量指标记录。
    本脚本通过自定义训练器在每个 epoch 额外记录 F1 标量到 Comet。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
TRAIN_DIR = ROOT / "train"
PROFILES_DIR = TRAIN_DIR / "profiles"
BASE_CONFIG = TRAIN_DIR / "config.yaml"


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_configs(base: dict, override: dict) -> dict:
    """用 override 中的非 None 值覆盖 base"""
    merged = base.copy()
    for k, v in override.items():
        if v is not None:
            merged[k] = v
    return merged


def parse_cli_overrides(args: list[str]) -> dict:
    """解析 --key value 形式的 CLI 覆盖参数"""
    overrides = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i].lstrip("-")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                val = args[i + 1]
                # 简单类型推断
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


def init_comet(config: dict):
    """初始化 Comet ML (可选, 安装了 comet_ml 才启用)"""
    try:
        import comet_ml

        project_name = config.get("name", "yolo-train")
        comet_ml.login(project_name=f"CQU_BYSJ-{project_name}")
        print(f"[Comet] 已登录, project=CQU_BYSJ-{project_name}")
        print("[Comet] Ultralytics 内置回调将自动记录所有训练指标")
    except ImportError:
        print("[Comet] 未安装 comet_ml, 跳过日志. 安装: pip install comet_ml")
    except Exception as e:
        print(f"[Comet] 初始化失败: {e}, 继续训练...")


def get_custom_trainer():
    """
    返回自定义训练器类, 在每个 epoch 额外记录 F1 标量指标到 Comet。

    Comet 内置回调已自动记录:
    - model/GFLOPs (首个 epoch)
    - model/speed_PyTorch(ms) (推理时间, 首个 epoch)
    - F1_curve 图片 (训练结束)

    此自定义训练器补充记录:
    - metrics/F1(B): 每个 epoch 的平均 F1 分数 (标量)
    """
    sys.path.insert(0, str(ROOT))
    import numpy as np
    from yolo.models.yolo.detect import DetectionTrainer
    from yolo.utils import LOGGER

    class F1Trainer(DetectionTrainer):
        """在每个验证 epoch 后额外记录 F1 标量到 Comet"""

        def validate(self):
            metrics, fitness = super().validate()
            if metrics is None:
                return metrics, fitness

            if hasattr(self.validator, "metrics") and hasattr(self.validator.metrics, "box"):
                f1_per_class = self.validator.metrics.box.f1
                valid_f1 = f1_per_class[f1_per_class > 0]
                mean_f1 = float(np.mean(valid_f1)) if len(valid_f1) > 0 else 0.0

                # 注入到 trainer.metrics 供 Comet 回调自动拾取
                if isinstance(self.metrics, dict):
                    self.metrics["metrics/F1(B)"] = round(mean_f1, 5)

                LOGGER.info(f"Mean F1: {mean_f1:.4f}")

            return metrics, fitness

    return F1Trainer


def main():
    parser = argparse.ArgumentParser(description="YOLO 统一训练脚本")
    parser.add_argument("--profile", type=str, help="模型配置名 (profiles/ 下的文件名, 不含 .yaml)")
    parser.add_argument("--no-comet", action="store_true", help="禁用 Comet ML 日志")
    # 其余参数作为覆盖项直接传递
    known, remaining = parser.parse_known_args()

    # 1. 加载基础配置
    config = load_yaml(BASE_CONFIG)

    # 2. 加载 profile 覆盖
    if known.profile:
        profile_path = PROFILES_DIR / f"{known.profile}.yaml"
        if not profile_path.exists():
            available = [p.stem for p in PROFILES_DIR.glob("*.yaml")]
            print(f"[错误] 找不到 profile: {known.profile}")
            print(f"[可用] {', '.join(available)}")
            sys.exit(1)
        profile = load_yaml(profile_path)
        config = merge_configs(config, profile)

    # 3. CLI 覆盖 (最高优先级)
    cli_overrides = parse_cli_overrides(remaining)
    config = merge_configs(config, cli_overrides)

    # 处理 resume 特殊参数
    if "resume" in cli_overrides and cli_overrides["resume"] is True:
        config["resume"] = True

    # 4. 初始化 Comet ML (Ultralytics 会自动检测并使用内置回调记录)
    if not known.no_comet:
        init_comet(config)

    # 5. 启动训练
    sys.path.insert(0, str(ROOT))
    from yolo import YOLO

    model_path = config.pop("model", None)
    if not model_path:
        print("[错误] 未指定模型, 请通过 --profile 或 --model 指定")
        sys.exit(1)

    # 相对路径转为项目根目录下的绝对路径
    model_path = Path(model_path)
    if not model_path.is_absolute():
        model_path = ROOT / model_path

    # 获取自定义训练器 (额外记录 F1 标量)
    CustomTrainer = get_custom_trainer()

    print(f"\n{'=' * 60}")
    print(f"  模型: {model_path}")
    print(f"  数据: {config.get('data', 'N/A')}")
    print(f"  设备: {config.get('device', 'auto')}")
    print(f"  轮数: {config.get('epochs', 100)}")
    print(f"  批大小: {config.get('batch', 16)}")
    print(f"  图像尺寸: {config.get('imgsz', 640)}")
    print(f"  输出: {config.get('project', 'runs/train')}/{config.get('name', 'exp')}")
    print(f"  日志: {'Comet ML' if not known.no_comet else '无'}")
    print(f"  自定义: F1Trainer (记录 F1 标量)")
    print(f"{'=' * 60}\n")

    model = YOLO(str(model_path))

    # 从 config 中移除非训练参数
    train_kwargs = {k: v for k, v in config.items() if v is not None}
    train_kwargs["trainer"] = CustomTrainer

    results = model.train(**train_kwargs)
    return results


if __name__ == "__main__":
    main()
