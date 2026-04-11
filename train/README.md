# train/ — YOLO 训练环境

## 目录结构

```
train/
├── config.yaml          # 统一基础配置 (设备/优化器/增强等)
├── train.py             # 训练入口 (内置 F1Trainer 自定义训练器)
├── setup_comet.py       # Comet ML 一键安装+登录
├── profiles/            # 模型专属配置 (覆盖 config.yaml)
│   ├── yolo26n.yaml
│   ├── yolo26s.yaml
│   ├── yolo11n.yaml
│   └── yolo11s.yaml
└── README.md
```

## 配置层级 (优先级从低到高)

1. `config.yaml` — 基础配置 (所有模型共享)
2. `profiles/*.yaml` — 模型专属覆盖
3. CLI `--key value` — 命令行覆盖 (最高优先级)

## 快速开始

### 1. 初始化 Comet ML (可选, 首次执行一次)

```bash
python train/setup_comet.py
```

或手动:
```bash
pip install comet_ml
export COMET_API_KEY=你的API密钥
```

### 2. 选择 profile 开始训练

```bash
# 使用 yolo26n profile 训练
python train/train.py --profile yolo26n

# 使用 yolo26s profile + 自定义数据集
python train/train.py --profile yolo26s --data path/to/dataset.yaml

# 使用 yolo11n profile + 覆盖参数
python train/train.py --profile yolo11n --epochs 200 --batch 8 --imgsz 1024
```

### 3. 不使用 profile, 直接指定模型

```bash
python train/train.py --model models/yolo26n.pt --data coco8.yaml --epochs 50
```

### 4. 恢复中断的训练

```bash
python train/train.py --profile yolo26n --resume
```

### 5. 禁用 Comet 日志

```bash
python train/train.py --profile yolo26n --no-comet
```

## Comet ML 自动记录的指标

| 指标类型 | 详情 | 来源 |
|---------|------|------|
| 训练损失 | box_loss, cls_loss, dfl_loss | 内置回调 |
| 验证指标 | mAP50, mAP50-95, precision, recall | 内置回调 |
| **F1 分数** | **每 epoch 平均 F1 (标量)** | **F1Trainer** |
| 模型信息 | **GFLOPs**, 参数量, **推理时间(ms)** | 内置回调 (首 epoch) |
| 学习率 | lr/pg0, lr/pg1, lr/pg2 | 内置回调 |
| 曲线图 | F1_curve, P_curve, R_curve, PR_curve | 内置回调 |
| 混淆矩阵 | 交互式混淆矩阵 | 内置回调 |
| 预测样本 | 验证集图像+边界框 | 内置回调 |
| 模型权重 | best.pt, last.pt | 内置回调 |
| 系统资源 | GPU/CPU 利用率, 内存 | 内置回调 |

> GFLOPs 和 inference_time 在首个 epoch 由 Comet 内置回调自动记录 (`model/GFLOPs`, `model/speed_PyTorch(ms)`)。
> F1 标量由自定义 `F1Trainer` 在每个 epoch 注入到 `trainer.metrics`，Comet 回调自动拾取。

## 如何添加新模型 profile

在 `profiles/` 下创建 `<model_name>.yaml`, 只需写覆盖项:

```yaml
# profiles/yolo26m.yaml
model: models/yolo26m.pt
name: yolo26m
batch: 8
epochs: 200
```

然后: `python train/train.py --profile yolo26m`

## 修改基础配置

编辑 `config.yaml` 即可全局生效。常见调整:

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `device` | 训练设备 | `mps` |
| `batch` | 批大小 | `16` |
| `epochs` | 训练轮数 | `100` |
| `imgsz` | 图像尺寸 | `640` |
| `optimizer` | 优化器 | `auto` |
| `workers` | 数据加载线程 | `4` |
| `patience` | 早停耐心值 | `20` |

## 切换设备

编辑 `config.yaml` 中的 `device` 字段, 或通过 CLI 覆盖:

```bash
python train/train.py --profile yolo26n --device cpu      # CPU
python train/train.py --profile yolo26n --device mps      # Apple Silicon
python train/train.py --profile yolo26n --device 0        # CUDA GPU 0
python train/train.py --profile yolo26n --device 0,1      # 多 GPU
```
