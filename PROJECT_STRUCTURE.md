# CQU_BYSJ - Project Structure Analysis

## Project Overview
**CrowdFlow**: A real-time crowd density detection and analysis system based on YOLO, with a full-stack web application (FastAPI backend + Vue 3 frontend).

### Technologies
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: Vue 3 + TypeScript + Vite
- **Detection Engine**: Ultralytics YOLO (custom vendored + pip-installed)
- **Deployment**: Docker + Docker Compose

---

## 1. Top-Level Directory Structure

```
CQU_BYSJ/
├── README.md                  # Project overview
├── docker-compose.yml         # Docker Compose configuration
├── .env.example              # Environment template
├── .env                       # Local environment (gitignored)
│
├── YOLO-CROWD/               # Legacy YOLO-v5 crowd detection (archived branch)
│   ├── train.py              # Old training script
│   ├── test.py               # Old testing script
│   ├── detect.py             # Old detection script
│   ├── models/               # YOLOv5 model definitions
│   ├── utils/                # YOLOv5 utilities (loss.py, metrics.py)
│   ├── data/                 # Dataset configs
│   └── weights/              # Pretrained weights
│
├── yolo/                     # **CUSTOM VENDORED ULTRALYTICS** (Main detection code)
│   ├── __init__.py           # Module entry point (version 8.4.36)
│   ├── cfg/                  # Model configurations (YAML)
│   │   ├── models/           # Model architecture configs
│   │   │   ├── 26/           # YOLO26 architectures
│   │   │   ├── 11/           # YOLO11 architectures
│   │   │   ├── 12/           # YOLO12 architectures
│   │   │   └── ...
│   │   └── default.yaml      # Default training config
│   ├── nn/                   # Neural network modules
│   │   ├── tasks.py          # **Task-specific models** (DetectionModel, etc.)
│   │   ├── modules/
│   │   │   ├── block.py      # **Custom blocks** (C3k2, C2PSA, SPPF, DFL, etc.)
│   │   │   ├── head.py       # **Detection/Segmentation heads**
│   │   │   ├── conv.py       # Convolution modules
│   │   │   ├── transformer.py # Transformer blocks
│   │   │   └── activation.py
│   │   └── autobackend.py    # Backend inference support
│   ├── models/               # **Model implementations**
│   │   ├── yolo/
│   │   │   ├── model.py      # YOLO base model class
│   │   │   ├── detect/
│   │   │   │   ├── train.py  # Detection training logic
│   │   │   │   ├── val.py    # **Validation + Metrics**
│   │   │   │   └── predict.py
│   │   │   ├── classify/
│   │   │   ├── segment/
│   │   │   ├── pose/
│   │   │   ├── obb/
│   │   │   └── yoloe/        # YOLO-E variants
│   │   ├── nas/              # NAS (Neural Architecture Search) models
│   │   ├── rtdetr/           # RT-DETR models
│   │   ├── sam/              # Segment Anything Model
│   │   ├── fastsam/
│   │   └── utils/
│   │       └── loss.py       # **DETR loss functions**
│   ├── engine/               # Training/inference engines
│   │   ├── trainer.py        # **Training orchestration**
│   │   ├── validator.py      # **Validation logic**
│   │   ├── predictor.py      # Inference/prediction
│   │   ├── exporter.py       # Model export (ONNX, TensorRT, etc.)
│   │   ├── model.py          # High-level model API
│   │   ├── results.py        # Detection results handling
│   │   └── tuner.py          # Hyperparameter tuning
│   ├── utils/
│   │   ├── loss.py           # **Loss functions** (FocalLoss, VarifocalLoss, etc.)
│   │   ├── metrics.py        # **Metrics** (mAP, precision, recall, F1, etc.)
│   │   ├── torch_utils.py    # PyTorch utilities
│   │   ├── ops.py            # Bounding box ops
│   │   └── ...
│   ├── optim/                # Optimizers
│   ├── trackers/             # Object tracking (ByteTrack, etc.)
│   ├── solutions/            # Domain-specific solutions
│   ├── hub/                  # Ultralytics Hub integration
│   ├── assets/               # Sample images/media
│   └── py.typed              # Type hints marker
│
├── train/                    # **Training configuration & scripts**
│   ├── config.yaml           # **Base training config** (device, batch, epochs, etc.)
│   ├── train.py              # **Main training entry point** (unified CLI)
│   ├── val.py                # Validation script
│   ├── setup_comet.py        # Comet ML integration
│   ├── profiles/             # Model-specific configs
│   │   ├── yolo26n.yaml
│   │   ├── yolo26s.yaml
│   │   ├── yolo11n.yaml
│   │   └── yolo11s.yaml
│   ├── dataset/              # Dataset configs
│   └── README.md             # Training documentation
│
├── models/                   # **Pretrained model weights**
│   ├── yolo11n.pt            # YOLO11 nano (~5.6MB)
│   ├── yolo11n_tune1.pt
│   ├── yolo11s.pt            # YOLO11 small (~19MB)
│   ├── yolo26n.pt            # YOLO26 nano (~5.5MB)
│   ├── yolo26n-tune1.pt
│   ├── yolo26n_tune2.pt
│   ├── yolo26s.pt            # YOLO26 small (~20MB)
│   ├── yolo26m.pt            # YOLO26 medium (~40MB)
│   ├── yolo11m_tune1.pt
│   └── yolo_nas_s.pt         # NAS model (~87MB)
│
├── backend/                  # **FastAPI application**
│   ├── app/
│   │   ├── main.py
│   │   ├── api/              # API routes
│   │   ├── core/             # Configuration, dependencies
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── repositories/     # Database access layer
│   │   ├── schemas/          # Pydantic schemas (request/response)
│   │   ├── services/         # Business logic (YOLO inference, detection, etc.)
│   │   └── utils/            # Helper functions
│   ├── pyproject.toml
│   └── .venv/                # Python virtual environment
│
├── frontend/                 # **Vue 3 application**
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/           # Pinia state management
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   └── vite.config.ts
│
├── scripts/                  # **Development utilities**
│   └── dev.sh                # Unified dev startup script
│
├── docs/                     # **Documentation**
│   ├── core-logic.md         # Core implementation details
│   ├── dataset-survey.md     # Dataset information
│   ├── execution-plan.md     # Execution strategy
│   ├── optimization-plan.md  # Performance optimization
│   ├── yolo26-crowd-improvement-plan.md
│   ├── info/                 # Info documents
│   ├── paper/                # Research papers
│   └── ultralytics/          # **Vendored Ultralytics source** (backup reference)
│       ├── README.md
│       ├── pyproject.toml
│       ├── mkdocs.yml
│       └── examples/         # Example notebooks
│
├── data/                     # **SQLite database & exports**
├── uploads/                  # **Uploaded files**
├── logs/                     # **Training/inference logs**
├── runs/                     # **Training results** (checkpoints, metrics)
├── downloads/                # **Downloaded models**
├── .github/                  # GitHub Actions workflows
├── .vscode/                  # VSCode settings
├── docker/                   # Docker configs
└── .omc/                     # OMC (oh-my-claudecode) settings
```

---

## 2. Custom YOLO Model Definitions

### **Key Files**:

#### **Core Model Class**
- **`yolo/nn/tasks.py`** (73KB)
  - `BaseModel` - Base class for all YOLO models
  - `DetectionModel` - Object detection model (used for crowd counting)
  - `SegmentationModel`, `ClassificationModel`, `PoseModel`, `OBBModel`
  - **Loads architectures from YAML configs**

#### **Model Implementation**
- **`yolo/models/yolo/model.py`** (18.6KB)
  - `YOLO` class - High-level API
  - Model loading, training, inference interface

#### **Architecture Blocks**
- **`yolo/nn/modules/block.py`** (74.8KB) - **EXTENSIVE CUSTOM BLOCKS**
  - `DFL` - Distribution Focal Loss integral module
  - `C3k2` - Modified bottleneck with kernel size 2
  - `C2PSA` - Pyramid Split Attention
  - `SPPF` - Spatial Pyramid Pooling Fast
  - `C2f`, `C2fAttn`, `C2fPSA` - Various C2 variants with attention
  - `Bottleneck`, `BottleneckCSP`, `C3Ghost`
  - `PSA` - Parallel Spatial Attention
  - And 40+ more specialized blocks

#### **Detection Head**
- **`yolo/nn/modules/head.py`** (78.3KB) - **DETECTION/SEGMENTATION HEADS**
  - `Detect` - Object detection head (outputs bbox + confidence)
  - `YOLOEDetect` - YOLO-E detection variant
  - `Segment` - Instance segmentation head
  - `Pose` - Keypoint detection head
  - `OBB` - Oriented bounding box head
  - Support for different output formats (end-to-end, DFL-based)

---

## 3. YAML Model Architecture Files

### **Location**: `yolo/cfg/models/`

### **YOLO26 Architectures** (`yolo/cfg/models/26/`)
- `yolo26.yaml` - **Base YOLO26 detection** (CUSTOM VERSION)
  - Scales: n (nano), s (small), m (medium), l (large), x (extra-large)
  - Backbone: C3k2 blocks, SPPF, C2PSA
  - Head: Detect layer
  - P3/8, P4/16, P5/32 outputs
  - `end2end: True` - Uses end-to-end detection mode
  - `reg_max: 1` - DFL bins (simplified from standard 16)

- `yolo26-seg.yaml` - Segmentation variant
- `yolo26-pose.yaml` - Pose estimation variant
- `yolo26-obb.yaml` - Oriented bounding boxes
- `yoloe-26.yaml` - YOLO-E detection (anchorfree)
- `yolo26-p2.yaml`, `yolo26-p6.yaml` - Extended scales

### **YOLO11 Architectures** (`yolo/cfg/models/11/`)
- `yolo11.yaml` - Latest YOLO11
- Similar structure with different depth/width scaling

### **Other Versions**
- YOLO12, YOLOv10, YOLOv9, YOLOv8, YOLOv5, etc.
- RT-DETR transformers

### **Configuration Format**
```yaml
nc: 80                    # Number of classes
end2end: True            # End-to-end detection mode
reg_max: 1               # DFL bins
scales:
  n: [0.50, 0.25, 1024]  # depth, width, max_channels

backbone:               # List of layers [from, repeats, module, args]
  - [-1, 1, Conv, [64, 3, 2]]
  - [-1, 2, C3k2, [256, False, 0.25]]
  
head:
  - [[16, 19, 22], 1, Detect, [nc]]
```

---

## 4. Ultralytics Installation

### **Status**: BOTH VENDORED & PIP-INSTALLED

#### **Vendored Source** (Reference/Development)
- **`docs/ultralytics/`** - Full Ultralytics repository snapshot
  - Complete source code for reference
  - mkdocs documentation
  - GitHub workflows, tests
  - **NOT used at runtime** (just reference)

#### **Pip Installation** (Runtime)
- **Location**: `backend/.venv/lib/python3.14/site-packages/ultralytics/`
- **Version**: Latest installed in virtual environment
- **Why both?**
  - Project extends/customizes Ultralytics → vendored copy for tracking changes
  - Runtime uses pip package for dependencies and updates
  - Custom `yolo/` folder overrides/extends the pip version

#### **Custom Yolo Module**
- **`yolo/` folder** - **Custom wrapper/extension** of Ultralytics
  - Not a direct fork, but a curated subset with customizations
  - Key customizations in:
    - `yolo/nn/modules/block.py` - Custom blocks (C3k2, C2PSA, etc.)
    - `yolo/models/yolo/detect/` - Detection-specific training logic
    - Loss functions for crowd detection task

---

## 5. Training Configuration & Scripts

### **Main Training Entry Points**

#### **`train/train.py`** - **Unified CLI**
- **Purpose**: Simplified training interface with config layers
- **Config Hierarchy**:
  1. `train/config.yaml` - Base config (all models)
  2. `train/profiles/<name>.yaml` - Model-specific overrides
  3. CLI args `--key value` - Runtime overrides (highest priority)
- **Features**:
  - Automatic Comet ML integration (experiment tracking)
  - F1 score tracking per epoch
  - Resume support (`--resume`)
  - Profile-based training (`--profile yolo26n`)
- **Usage**:
  ```bash
  python train/train.py --profile yolo26n --epochs 200
  python train/train.py --profile yolo26s --data custom.yaml --device 0
  python train/train.py --model models/yolo26n.pt --resume
  ```

#### **`train/config.yaml`** - **Base Configuration**
- Device: mps (Apple Silicon), cuda, cpu
- Batch size: 16
- Epochs: 100
- Image size: 640
- Optimizer: auto (AdamW/SGD)
- Data augmentation, learning rate scheduling
- Early stopping (patience: 20)

#### **`train/profiles/*.yaml`** - **Model-Specific Config**
- Example: `yolo26n.yaml`
  - `model: models/yolo26n.pt`
  - `batch: 8` (override)
  - `epochs: 200` (override)

#### **`train/val.py`** - **Validation Script**
- Standalone validation on trained models
- Metric computation (mAP, precision, recall, F1)

#### **`train/setup_comet.py`** - **Experiment Tracking**
- Integrates with Comet ML for metric logging
- Automatic recording of:
  - Training loss (box, cls, dfl)
  - Validation metrics (mAP50, mAP50-95, precision, recall)
  - Model info (GFLOPs, parameters, inference time)
  - Learning rate curves, confusion matrices

---

## 6. Training Directory Details

```
train/
├── config.yaml
├── train.py                 # Unified entry point (F1Trainer)
├── val.py
├── setup_comet.py
├── profiles/
│   ├── yolo26n.yaml
│   ├── yolo26s.yaml
│   ├── yolo11n.yaml
│   └── yolo11s.yaml
├── dataset/                 # Dataset YAML configs
└── README.md
```

### **Key Training Components**

#### **F1Trainer** (in `train/train.py`)
- Extends `DetectionTrainer`
- Custom validation hook to record **F1 score scalar** per epoch
- Comet ML automatically captures:
  - Standard losses
  - mAP curves
  - Model metadata
  - Hyperparameters

---

## 7. Custom Modules: block.py, loss.py, tasks.py, metrics.py

### **`yolo/nn/modules/block.py`** (74.8KB)
**Architectural building blocks for neural networks:**
- `DFL` - Distribution Focal Loss integral (quantized regression)
- `C1`, `C2`, `C3` - CSPBottleneck variants
- `C3k2` - **Custom bottleneck with kernel=2**
- `C2PSA` - **C2 with Pyramid Split Attention**
- `C2f`, `C2fAttn`, `C2fPSA` - Modern bottleneck variants
- `Bottleneck`, `BottleneckCSP` - ResNet-style
- `PSA` - Parallel Spatial Attention
- `SPP`, `SPPF` - Spatial Pyramid Pooling
- `AConv`, `ADown` - Attention-based convolution/downsample
- `HGBlock`, `HGStem` - High-resolution blocks
- `GhostBottleneck` - Lightweight bottleneck
- `CBLinear`, `CBFuse` - Channel/branch operations
- And 20+ more specialized blocks

### **`yolo/nn/tasks.py`** (73KB)
**Task-specific model definitions:**
- `BaseModel` - Base for all YOLO models
- `DetectionModel` - **Object detection** (used for crowd detection)
- `SegmentationModel` - Instance segmentation
- `ClassificationModel` - Image classification
- `PoseModel` - Keypoint detection
- `OBBModel` - Oriented bounding box detection
- `WorldModel` - YOLO-World open-vocabulary detection
- `RTDETRDetectionModel` - Transformer-based detection

**Key responsibilities:**
- Load architecture from YAML
- Build layer graph
- Initialize weights
- Handle forward/backward passes
- Fuse batch norm + conv
- Export models

### **`yolo/utils/loss.py`** (Shared loss functions)
**Location**: Both `yolo/utils/loss.py` and `yolo/models/utils/loss.py`

**Core Loss Functions**:
- `FocalLoss` - Focal loss for hard example mining
- `VarifocalLoss` - Varifocal loss (quality-focal loss variant)
- `v8DetectionLoss` - Standard YOLO detection loss
  - Box loss (MSE with DFL)
  - Confidence loss
  - Classification loss
- `v8SegmentationLoss` - Segmentation + box losses
- `v8PoseLoss` - Keypoint regression loss
- `v8ClassificationLoss` - Multi-class classification loss
- `v8OBBLoss` - Oriented bounding box loss

**RT-DETR Loss** (`yolo/models/utils/loss.py`):
- `DETRLoss` - Transformer-based detection loss
- `RTDETRDetectionLoss` - RT-DETR with denoising
- Hungarian matcher for bipartite matching
- GIoU, L1, BCE losses

### **`yolo/utils/metrics.py`** (69.8KB)
**Evaluation metrics:**
- `bbox_iou()` - Intersection over Union
- `bbox_ioa()` - Intersection over Area
- `DetMetrics` - **Object detection metrics**
  - AP (Average Precision)
  - mAP50, mAP50-95
  - Precision, Recall, F1-score per class
  - Confusion matrix
  - ROC-AUC curves
- `SegmentationMetrics` - Instance segmentation
- `PoseMetrics` - Keypoint detection
- `ClassifyMetrics` - Classification
- `OKS` - Object Keypoint Similarity

**Key outputs**:
- Per-class metrics
- Mean metrics (mAP, precision, recall)
- **F1 curve** (plotted but not scalar in standard Comet)

---

## 8. Backend Architecture

```
backend/app/
├── main.py               # FastAPI app setup
├── core/                 # Configuration & dependencies
│   ├── config.py
│   └── dependencies.py
├── api/                  # REST endpoints
│   ├── routes/
│   └── v1/
├── models/               # SQLAlchemy ORM
│   ├── detection.py
│   └── ...
├── repositories/         # Database access layer
├── schemas/              # Pydantic request/response
├── services/             # Business logic
│   ├── detection_service.py  # YOLO inference
│   ├── tracking_service.py   # Object tracking
│   └── analysis_service.py   # Analytics
└── utils/                # Helpers
```

### **Key Backend Features**
- YOLO model loading & inference
- Real-time crowd density analysis
- Alert management (density thresholds)
- REST API for web/mobile clients
- Database persistence (SQLite)

---

## 9. Environment Variables

```
DEBUG=true
HOST=0.0.0.0
PORT=8000
BACKEND_PORT=8000
FRONTEND_PORT=3000
DATABASE_URL=              # Auto-creates SQLite
YOLO_MODEL_PATH=           # Default: models/yolo11n.pt
YOLO_CONF_THRESHOLD=0.5
YOLO_DEVICE=cpu            # or cuda, mps
ALERT_COOLDOWN_SECONDS=30
DENSITY_FACTOR=10000
DENSITY_MAX=100
VITE_API_URL=              # Frontend backend URL
```

---

## 10. Key Customizations & Extensions

### **YOLO26 Architecture**
- Uses `end2end: True` mode (end-to-end detection)
- Simplified DFL with `reg_max: 1`
- Custom blocks: C3k2, C2PSA
- Optimized for both accuracy and speed

### **Crowd Counting Specific**
- Loss functions in `yolo/models/utils/loss.py` for DETR-based detection
- Density factor for converting count → density
- Alert cooldown to prevent over-alerting
- Multi-scale detection (P3, P4, P5 outputs)

### **Training Pipeline Enhancements**
- `F1Trainer` for per-epoch F1 tracking
- Comet ML integration for experiment management
- Profile-based configuration system
- Resume capability for long-running training

---

## 11. Summary Table

| Component | Location | Purpose |
|-----------|----------|---------|
| **YOLO Models** | `yolo/nn/tasks.py` | Model class definitions |
| **Architecture Blocks** | `yolo/nn/modules/block.py` | Custom neural network blocks |
| **Detection Head** | `yolo/nn/modules/head.py` | Detection/segmentation heads |
| **Model Configs** | `yolo/cfg/models/26/yolo26.yaml` | YAML architecture specifications |
| **Loss Functions** | `yolo/utils/loss.py` | Training objectives |
| **Metrics** | `yolo/utils/metrics.py` | Evaluation metrics (mAP, F1, etc.) |
| **Training Logic** | `yolo/models/yolo/detect/train.py` | Detection-specific training |
| **Training CLI** | `train/train.py` | Unified training entry point |
| **Base Config** | `train/config.yaml` | Global training parameters |
| **Model Profiles** | `train/profiles/*.yaml` | Model-specific overrides |
| **Validation** | `yolo/models/yolo/detect/val.py` | Metric computation |
| **Backend API** | `backend/app/api/` | REST endpoints for inference |
| **Frontend** | `frontend/src/` | Vue 3 web UI |
| **Experiment Tracking** | `train/setup_comet.py` | Comet ML integration |

---

## 12. File Statistics

- **Total model files**: 100+ (PyTorch models in `models/`)
- **Config files**: 50+ YAML files for different architectures
- **Source code**: ~500KB of Python code in `yolo/` folder
- **Ultralytics reference**: 20MB+ in `docs/ultralytics/`
- **Backend**: ~50KB of FastAPI code
- **Frontend**: ~100KB of Vue.js code

---

## 13. Is This a Fork or Custom Build?

**Answer: Custom wrapper/extension**
- NOT a direct Ultralytics fork (no git history from upstream)
- Vendored reference copy in `docs/ultralytics/` for documentation
- Runtime uses pip-installed `ultralytics` package
- Custom `yolo/` folder contains:
  - Curated subset of Ultralytics code
  - Custom blocks (C3k2, C2PSA)
  - Task-specific training logic (F1Trainer, Comet integration)
  - Crowd detection optimizations

**Why?**
- Allows rapid prototyping with latest Ultralytics
- Customizations isolated in `yolo/` namespace
- Easy to merge new Ultralytics updates
- Clean separation of concerns

---

**Generated**: 2026-04-11  
**Explorer**: Claude Code Agent  
