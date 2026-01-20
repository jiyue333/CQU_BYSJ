#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShanghaiTech -> YOLO (Ultralytics Platform/HUB ready)

Input (your structure):
  data/ShanghaiTech/
    part_A/
      train_data/{images,ground-truth}
      test_data/{images,ground-truth}
    part_B/
      train_data/{images,ground-truth}
      test_data/{images,ground-truth}

Images:
  processed_IMG_99.jpg  (or IMG_99.jpg)
GT mats:
  GT_IMG_99.mat  with image_info.location = (N,2) points (x,y)

Output (HUB-ready dataset folder):
  <dst_dataset_name>/
    <dst_dataset_name>.yaml   (MUST match folder/zip name for HUB)
    images/train/*.jpg
    images/val/*.jpg
    labels/train/*.txt
    labels/val/*.txt

Label format:
  YOLO Detect: class x_center y_center w h  (all normalized 0-1)

Default box generation:
  kNN-adaptive square boxes around each point (better than fixed box size for density/perspective changes)

Optional:
  --patch-size + --patch-overlap to generate overlapped patches (helps dense small targets but increases size)
"""

from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from scipy.io import loadmat
from scipy.spatial import cKDTree
import yaml


IMG_ID_RE = re.compile(r"(?:processed_)?IMG_(\d+)$", re.IGNORECASE)


@dataclass
class BoxCfg:
    # Adaptive box parameters
    k: int = 3
    alpha: float = 0.8
    s_min: float = 8.0
    s_max: float = 80.0
    # Fixed box fallback
    fixed_size: int | None = None  # if set, use fixed instead of adaptive


@dataclass
class PatchCfg:
    patch_size: int | None = None  # e.g. 640; if None, no patching
    overlap: float = 0.25          # 0~0.9, stride = patch*(1-overlap)


def extract_img_id(stem: str) -> int | None:
    """stem: processed_IMG_99 or IMG_99 -> 99"""
    m = IMG_ID_RE.match(stem)
    return int(m.group(1)) if m else None


def load_points_from_mat(mat_path: Path) -> np.ndarray:
    """
    ShanghaiTech GT mat:
      image_info.location -> (N,2) points (x,y) in pixels
    Robustly parse common MATLAB cell/struct encodings.
    """
    m = loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)
    if "image_info" not in m:
        raise KeyError(f"Missing 'image_info' in {mat_path}")

    info = m["image_info"]
    if hasattr(info, "location"):
        loc = info.location
    else:
        # legacy indexing fallback
        cell = info[0, 0]  # type: ignore[index]
        loc = cell["location"][0, 0]  # type: ignore[index]

    pts = np.asarray(loc, dtype=np.float32)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"Unexpected location shape {pts.shape} in {mat_path}")
    return pts  # (N,2), (x,y)


def maybe_fix_matlab_1based(points: np.ndarray, w: int, h: int) -> np.ndarray:
    """
    Conservative heuristic for MATLAB 1-based coords:
    - if any coord > image boundary, subtract 1
    - OR if min>=1 and any coord hits exactly w/h, subtract 1
    """
    pts = points.copy()
    if pts.size == 0:
        return pts
    if np.any(pts[:, 0] > w) or np.any(pts[:, 1] > h):
        return pts - 1.0
    if (pts.min() >= 1.0) and (np.any(pts[:, 0] == w) or np.any(pts[:, 1] == h)):
        return pts - 1.0
    return pts


def clip_points(points: np.ndarray, w: int, h: int) -> np.ndarray:
    """Clip to valid pixel range [0, w-1]/[0, h-1]."""
    if points.size == 0:
        return points
    pts = points.copy()
    pts[:, 0] = np.clip(pts[:, 0], 0, w - 1)
    pts[:, 1] = np.clip(pts[:, 1], 0, h - 1)
    return pts


def adaptive_sizes_knn(points: np.ndarray, cfg: BoxCfg) -> np.ndarray:
    """
    Compute per-point box size using kNN mean distance:
      s = clip(alpha * mean(d_knn), s_min, s_max)
    Uses cKDTree for efficiency.
    """
    n = len(points)
    if n == 0:
        return np.zeros((0,), dtype=np.float32)
    if n == 1:
        return np.array([float(np.clip(cfg.s_min, cfg.s_min, cfg.s_max))], dtype=np.float32)

    kk = min(cfg.k + 1, n)  # include self in query
    tree = cKDTree(points)
    dists, _ = tree.query(points, k=kk, workers=-1)  # (N,kk)
    # dists[:,0] is 0 (self); use neighbors
    neigh = dists[:, 1:] if kk > 1 else dists
    mean_d = neigh.mean(axis=1)

    s = cfg.alpha * mean_d
    s = np.clip(s, cfg.s_min, cfg.s_max)
    return s.astype(np.float32)


def yolo_lines_from_points(points: np.ndarray, w: int, h: int, cfg: BoxCfg, class_id: int = 0) -> list[str]:
    """
    Generate YOLO detect labels from points:
      class x_center y_center w h (normalized)
    """
    n = len(points)
    if n == 0:
        return []

    if cfg.fixed_size is not None:
        sizes = np.full((n,), float(cfg.fixed_size), dtype=np.float32)
        sizes = np.clip(sizes, 1.0, float(min(w, h)))
    else:
        sizes = adaptive_sizes_knn(points, cfg)
        sizes = np.clip(sizes, 1.0, float(min(w, h)))

    lines: list[str] = []
    for (x, y), s in zip(points, sizes):
        half = s / 2.0
        # keep bbox inside image
        x = float(np.clip(x, half, w - half))
        y = float(np.clip(y, half, h - half))

        xc = x / w
        yc = y / h
        wn = min(float(s / w), 1.0)
        hn = min(float(s / h), 1.0)

        lines.append(f"{class_id} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}")
    return lines


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def iter_patches(w: int, h: int, patch: PatchCfg):
    """
    Yield patch boxes: (x0,y0,x1,y1) in pixel coords.
    """
    ps = patch.patch_size
    if ps is None:
        yield (0, 0, w, h)
        return

    ps = int(ps)
    stride = max(1, int(ps * (1.0 - patch.overlap)))
    # Ensure last patch reaches boundary
    xs = list(range(0, max(1, w - ps + 1), stride))
    ys = list(range(0, max(1, h - ps + 1), stride))
    if xs[-1] != w - ps:
        xs.append(max(0, w - ps))
    if ys[-1] != h - ps:
        ys.append(max(0, h - ps))

    for y0 in ys:
        for x0 in xs:
            x1 = min(w, x0 + ps)
            y1 = min(h, y0 + ps)
            # If near boundary, force exact size if possible
            if (x1 - x0) < ps and w >= ps:
                x0 = w - ps
                x1 = w
            if (y1 - y0) < ps and h >= ps:
                y0 = h - ps
                y1 = h
            yield (x0, y0, x1, y1)


def convert_split(
    part: str,                    # "part_A"/"part_B"
    split_name: str,              # "train"/"val"
    src_images: Path,
    src_gt: Path,
    dst_images: Path,
    dst_labels: Path,
    box_cfg: BoxCfg,
    patch_cfg: PatchCfg,
    class_id: int,
    class_name: str,
) -> tuple[int, int, int]:
    """
    Returns: (images_written, labels_written, missing_gt)
    """
    ensure_dir(dst_images)
    ensure_dir(dst_labels)

    part_short = "A" if part.lower().endswith("a") else "B"
    images_written = 0
    labels_written = 0
    missing_gt = 0

    for img_path in sorted(src_images.glob("*.jpg")):
        img_id = extract_img_id(img_path.stem)
        if img_id is None:
            print(f"[WARN] Skip unknown filename: {img_path.name}")
            continue

        gt_path = src_gt / f"GT_IMG_{img_id}.mat"
        if not gt_path.exists():
            missing_gt += 1
            print(f"[WARN] Missing GT: {img_path.name} -> {gt_path.name}")
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            print(f"[WARN] Cannot read image: {img_path}")
            continue
        h, w = img.shape[:2]

        try:
            pts = load_points_from_mat(gt_path)
            pts = maybe_fix_matlab_1based(pts, w, h)
            pts = clip_points(pts, w, h)
        except Exception as e:
            print(f"[WARN] Bad mat {gt_path.name}: {e}")
            continue

        # For each patch (or full image as one patch)
        for pi, (x0, y0, x1, y1) in enumerate(iter_patches(w, h, patch_cfg)):
            crop = img[y0:y1, x0:x1]
            ch, cw = crop.shape[:2]

            # points inside patch
            if len(pts) > 0:
                inside = (pts[:, 0] >= x0) & (pts[:, 0] < x1) & (pts[:, 1] >= y0) & (pts[:, 1] < y1)
                p_patch = pts[inside].copy()
                p_patch[:, 0] -= x0
                p_patch[:, 1] -= y0
            else:
                p_patch = pts

            lines = yolo_lines_from_points(p_patch, cw, ch, box_cfg, class_id=class_id)

            # Unique naming: avoid collisions across part/split and patch index
            # Example: A_train_IMG_000099_p000.jpg
            if patch_cfg.patch_size is None:
                out_stem = f"{part_short}_{split_name}_IMG_{img_id:06d}"
            else:
                out_stem = f"{part_short}_{split_name}_IMG_{img_id:06d}_p{pi:03d}"

            out_img = dst_images / f"{out_stem}.jpg"
            out_lbl = dst_labels / f"{out_stem}.txt"

            # write image
            ok = cv2.imwrite(str(out_img), crop)
            if not ok:
                print(f"[WARN] Failed to write image: {out_img}")
                continue
            images_written += 1

            # write label (empty file is allowed)
            out_lbl.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            labels_written += 1

    print(f"[INFO] {part} {split_name}: images={images_written}, labels={labels_written}, missing_gt={missing_gt}")
    return images_written, labels_written, missing_gt


def write_dataset_yaml(dst_root: Path, dataset_name: str, class_name: str) -> Path:
    """
    HUB requires yaml inside root, and yaml/dir/zip share same name. :contentReference[oaicite:2]{index=2}
    """
    data = {
        "path": str(dst_root.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": [class_name],
    }
    yaml_path = dst_root / f"{dataset_name}.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return yaml_path


def zip_dataset(dst_root: Path, dataset_name: str) -> Path:
    """
    Create <dataset_name>.zip next to dataset folder.
    ZIP should share the same name as folder and yaml. :contentReference[oaicite:3]{index=3}
    """
    zip_path = dst_root.parent / f"{dataset_name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in dst_root.rglob("*"):
            if p.is_file():
                # keep top-level folder inside zip
                arcname = str(Path(dataset_name) / p.relative_to(dst_root))
                z.write(p, arcname=arcname)
    return zip_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("./data/ShanghaiTech"), help="ShanghaiTech root")
    ap.add_argument(
        "--dst",
        type=Path,
        default=Path("./data/shanghaitech_head"),
        help="Output dataset folder (folder name will be used as dataset name)",
    )

    # Adaptive box params (default recommended)
    ap.add_argument("--k", type=int, default=3, help="kNN neighbors for adaptive box size")
    ap.add_argument("--alpha", type=float, default=0.8, help="box size = alpha * mean_knn_distance")
    ap.add_argument("--s-min", type=float, default=8.0, help="min box size (pixels)")
    ap.add_argument("--s-max", type=float, default=80.0, help="max box size (pixels)")
    ap.add_argument("--fixed-box", type=int, default=None, help="If set, use fixed box size (pixels) instead of adaptive")

    # Optional patching
    ap.add_argument("--patch-size", type=int, default=None, help="If set, crop overlapped patches of this size (e.g. 640)")
    ap.add_argument("--patch-overlap", type=float, default=0.25, help="Patch overlap ratio (0~0.9), default 0.25")

    ap.add_argument("--class-id", type=int, default=0, help="class id (default 0)")
    ap.add_argument("--class-name", type=str, default="person", help="class name in yaml")

    ap.add_argument("--make-zip", action="store_true", help="Also create <dataset_name>.zip for HUB upload")
    args = ap.parse_args()

    src_root: Path = args.src
    dst_root: Path = args.dst

    if not src_root.exists():
        raise SystemExit(f"[ERROR] src not found: {src_root}")

    # HUB naming rule: folder name is dataset name, yaml name must match folder
    dataset_name = dst_root.name

    # Clean/create output
    if dst_root.exists():
        # safer: refuse by default to avoid accidental overwrite
        # user can delete manually
        raise SystemExit(f"[ERROR] dst already exists: {dst_root}\nDelete it first, or choose another --dst.")

    (dst_root / "images" / "train").mkdir(parents=True, exist_ok=True)
    (dst_root / "images" / "val").mkdir(parents=True, exist_ok=True)
    (dst_root / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (dst_root / "labels" / "val").mkdir(parents=True, exist_ok=True)

    box_cfg = BoxCfg(k=args.k, alpha=args.alpha, s_min=args.s_min, s_max=args.s_max, fixed_size=args.fixed_box)
    patch_cfg = PatchCfg(patch_size=args.patch_size, overlap=args.patch_overlap)

    # Convert part_A and part_B
    totals = {"train": 0, "val": 0}
    missing = 0

    for part in ["part_A", "part_B"]:
        part_dir = src_root / part
        if not part_dir.exists():
            print(f"[WARN] Skip missing part: {part}")
            continue

        # train_data -> train
        tr_imgs = part_dir / "train_data" / "images"
        tr_gt = part_dir / "train_data" / "ground-truth"
        if tr_imgs.exists() and tr_gt.exists():
            n_img, _, m = convert_split(
                part=part,
                split_name="train",
                src_images=tr_imgs,
                src_gt=tr_gt,
                dst_images=dst_root / "images" / "train",
                dst_labels=dst_root / "labels" / "train",
                box_cfg=box_cfg,
                patch_cfg=patch_cfg,
                class_id=args.class_id,
                class_name=args.class_name,
            )
            totals["train"] += n_img
            missing += m
        else:
            print(f"[WARN] Missing train folders in {part}")

        # test_data -> val
        te_imgs = part_dir / "test_data" / "images"
        te_gt = part_dir / "test_data" / "ground-truth"
        if te_imgs.exists() and te_gt.exists():
            n_img, _, m = convert_split(
                part=part,
                split_name="val",
                src_images=te_imgs,
                src_gt=te_gt,
                dst_images=dst_root / "images" / "val",
                dst_labels=dst_root / "labels" / "val",
                box_cfg=box_cfg,
                patch_cfg=patch_cfg,
                class_id=args.class_id,
                class_name=args.class_name,
            )
            totals["val"] += n_img
            missing += m
        else:
            print(f"[WARN] Missing test folders in {part}")

    yaml_path = write_dataset_yaml(dst_root, dataset_name, args.class_name)

    print("\n[DONE] Dataset created for Ultralytics Platform/HUB upload.")
    print(f"  dataset_dir: {dst_root}")
    print(f"  yaml:        {yaml_path}")
    print(f"  train imgs:  {totals['train']}")
    print(f"  val imgs:    {totals['val']}")
    print(f"  missing gt:  {missing}")

    if args.make_zip:
        zip_path = zip_dataset(dst_root, dataset_name)
        print(f"  zip:         {zip_path}")
        print("\nUpload the ZIP to Ultralytics Platform -> Datasets -> Upload Dataset.")


if __name__ == "__main__":
    main()
