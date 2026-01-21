#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert MATLAB point annotations (*.mat) to Ultralytics YOLO detection labels (*.txt)
and optionally export visualization images.

This script is designed for datasets where the .mat file contains an Nx2 array of points
(e.g., crowd counting annotations). YOLO expects bounding boxes, so each point is converted
to a small box of fixed size (configurable).

Ultralytics YOLO label format (per line):
<class_id> <x_center> <y_center> <width> <height>    (all normalized to [0,1])

Output folder structure:
out_dir/
  images/  (copied images)
  labels/  (YOLO txt labels)
  vis/     (visualization images)

Dependencies:
  pip install numpy scipy pillow
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw
from scipy.io import loadmat


def get_adaptive_box_size(num_points: int) -> float:
    """
    根据画面中的人数动态计算 box 大小。
    人数越多通常意味着拍摄距离越远，人越小，box 应该越小。

    阈值规则：
      0-50:    100px
      51-100:   50px
      101-150:  40px
      151-250:  30px
      251+:     20px
    """
    thresholds = [
        (50, 200),
        (100, 150),
        (150, 130),
        (300, 80),
        (500, 40),
        (1000, 20),
    ]
    for threshold, size in thresholds:
        if num_points <= threshold:
            return float(size)
    return 15.0  # 超过 400 人使用最小 box


def find_points_in_mat(mat: dict) -> np.ndarray:
    """
    Find an Nx2 float array in .mat.
    Priority:
      1) key 'annPoints'
      2) any array with shape (N,2) or (2,N)
    """
    if "annPoints" in mat:
        pts = mat["annPoints"]
    else:
        pts = None
        for k, v in mat.items():
            if k.startswith("__"):
                continue
            if isinstance(v, np.ndarray) and v.ndim == 2 and 2 in v.shape:
                pts = v
                break
        if pts is None:
            raise KeyError("No point array found in .mat (expected 'annPoints' or any Nx2 array).")

    pts = np.asarray(pts, dtype=np.float64)
    if pts.shape[1] != 2 and pts.shape[0] == 2:
        pts = pts.T
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"Point array must be Nx2, got {pts.shape}")
    return pts


def inside_ratio(pts_xy: np.ndarray, w: int, h: int) -> float:
    return float(((pts_xy[:, 0] >= 0) & (pts_xy[:, 0] < w) & (pts_xy[:, 1] >= 0) & (pts_xy[:, 1] < h)).mean())


def transform_points(
    pts: np.ndarray,
    w: int,
    h: int,
    coord_mode: str = "auto",
    scale_mode: str = "auto",
) -> Tuple[np.ndarray, str, str]:
    """
    Transform points into current image coordinate system.

    coord_mode:
      - 'xy'  : pts[:,0]=x, pts[:,1]=y
      - 'yx'  : pts[:,0]=y, pts[:,1]=x
      - 'auto': try both, pick best by heuristic

    scale_mode:
      - 'none' : no scaling
      - 'max'  : x*=w/max(x); y*=h/max(y)
      - 'range': (x-minx)*w/(maxx-minx), similarly y
      - 'auto' : prefer no scaling if most points in-bounds; otherwise pick best scaling
    """
    def apply_orient(p: np.ndarray, orient: str) -> np.ndarray:
        return p if orient == "xy" else p[:, [1, 0]]

    def apply_scale(p: np.ndarray, scale: str) -> np.ndarray:
        q = p.copy()
        if scale == "none":
            return q
        if scale == "max":
            q[:, 0] *= w / max(q[:, 0].max(), 1e-6)
            q[:, 1] *= h / max(q[:, 1].max(), 1e-6)
            return q
        if scale == "range":
            mins = q.min(axis=0)
            maxs = q.max(axis=0)
            rng = np.maximum(maxs - mins, 1e-6)
            q = (q - mins) * np.array([w, h], dtype=np.float64) / rng
            return q
        raise ValueError(f"Unknown scale_mode={scale}")

    orients = ["xy", "yx"] if coord_mode == "auto" else [coord_mode]
    scales = ["none", "max", "range"] if scale_mode == "auto" else [scale_mode]

    candidates = []
    for orient in orients:
        p0 = apply_orient(pts, orient)
        for scale in scales:
            q = apply_scale(p0, scale)
            r = inside_ratio(q, w, h)
            candidates.append((r, orient, scale, q))

    # tie-break: highest in-bounds -> prefer none > max > range -> prefer xy > yx
    scale_rank = {"none": 0, "max": 1, "range": 2}
    orient_rank = {"xy": 0, "yx": 1}
    candidates.sort(key=lambda t: (-t[0], scale_rank[t[2]], orient_rank[t[1]]))
    best_r, best_orient, best_scale, best_q = candidates[0]

    # special-case: if xy+none already很好，强行用它（避免过度“拉伸”）
    if scale_mode == "auto" and coord_mode in ("auto", "xy"):
        q_xy_none = apply_scale(apply_orient(pts, "xy"), "none")
        if inside_ratio(q_xy_none, w, h) >= 0.90:
            return q_xy_none, "xy", "none"

    return best_q, best_orient, best_scale


def points_to_yolo_boxes(
    pts_xy: np.ndarray,
    w: int,
    h: int,
    box_w: float,
    box_h: float,
    class_id: int = 0,
) -> np.ndarray:
    """
    Convert point centers to YOLO boxes (normalized).
    Returns array shape (N, 5): [class, xc, yc, bw, bh]
    """
    half_w = box_w / 2.0
    half_h = box_h / 2.0

    out = []
    for x, y in pts_xy:
        x1 = max(0.0, x - half_w)
        y1 = max(0.0, y - half_h)
        x2 = min(float(w - 1), x + half_w)
        y2 = min(float(h - 1), y + half_h)
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        if bw <= 0 or bh <= 0:
            continue
        xc = ((x1 + x2) / 2.0) / w
        yc = ((y1 + y2) / 2.0) / h
        out.append([class_id, xc, yc, bw, bh])

    return np.asarray(out, dtype=np.float64)


def draw_boxes(image: Image.Image, yolo_boxes: np.ndarray, out_path: Path, color=(255, 0, 0), width=1) -> None:
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for cls, xc, yc, bw, bh in yolo_boxes:
        x = xc * w
        y = yc * h
        bwpx = bw * w
        bhpx = bh * h
        x1 = x - bwpx / 2.0
        y1 = y - bhpx / 2.0
        x2 = x + bwpx / 2.0
        y2 = y + bhpx / 2.0
        draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=90)


def process_one(
    img_path: Path,
    mat_path: Path,
    out_dir: Path,
    box_w: float | None,
    box_h: float | None,
    class_id: int,
    coord_mode: str,
    scale_mode: str,
    save_vis: bool,
    adaptive_box: bool,
) -> None:
    img = Image.open(img_path)
    w, h = img.size

    mat = loadmat(mat_path)
    pts = find_points_in_mat(mat)

    # 根据人数自适应 box 大小
    if adaptive_box:
        adaptive_size = get_adaptive_box_size(len(pts))
        actual_box_w = adaptive_size
        actual_box_h = adaptive_size
    else:
        actual_box_w = box_w
        actual_box_h = box_h

    pts_xy, used_orient, used_scale = transform_points(pts, w, h, coord_mode=coord_mode, scale_mode=scale_mode)
    boxes = points_to_yolo_boxes(pts_xy, w, h, box_w=actual_box_w, box_h=actual_box_h, class_id=class_id)

    out_images = out_dir / "images"
    out_labels = out_dir / "labels"
    out_vis = out_dir / "vis"

    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    (out_images / img_path.name).write_bytes(img_path.read_bytes())

    label_path = out_labels / (img_path.stem + ".txt")
    with label_path.open("w", encoding="utf-8") as f:
        for cls, xc, yc, bw, bh in boxes:
            f.write(f"{int(cls)} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")

    if save_vis:
        vis_path = out_vis / (img_path.stem + "_yolo_vis.jpg")
        draw_boxes(img, boxes, vis_path)

    print(f"[OK] {img_path.name}: 人数={len(pts)} boxes={len(boxes)} box_size={actual_box_w:.0f}x{actual_box_h:.0f} orient={used_orient} scale={used_scale}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=str, required=True, help="Image file or directory containing images.")
    ap.add_argument("--mats", type=str, default=None, help="Mat file or directory. If omitted, search next to image.")
    ap.add_argument("--mat-suffix", type=str, default="_ann.mat",
                    help="If mats is dir/omitted, mat name is <image_stem><mat_suffix>.")
    ap.add_argument("--out", type=str, required=True, help="Output directory.")
    ap.add_argument("--box-w", type=float, default=20, help="Box width in pixels.")
    ap.add_argument("--box-h", type=float, default=20, help="Box height in pixels.")
    ap.add_argument("--class-id", type=int, default=0, help="Class id.")
    ap.add_argument("--coord-mode", choices=["auto", "xy", "yx"], default="auto", help="Point order in mat.")
    ap.add_argument("--scale-mode", choices=["auto", "none", "max", "range"], default="auto",
                    help="Scale points if not matching image size.")
    ap.add_argument("--no-vis", action="store_true", help="Disable visualization.")
    ap.add_argument("--adaptive-box", action="store_true",
                    help="根据人数自适应调整 box 大小（忽略 --box-w/--box-h）。")
    args = ap.parse_args()

    img_in = Path(args.images)
    mats_in = Path(args.mats) if args.mats else None
    out_dir = Path(args.out)

    if img_in.is_file():
        img_list = [img_in]
    else:
        img_list = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"):
            img_list.extend(img_in.glob(ext))
        img_list = sorted(img_list)
        if not img_list:
            raise FileNotFoundError(f"No images found in {img_in}")

    for img_path in img_list:
        if mats_in is None:
            mat_path = img_path.with_name(img_path.stem + args.mat_suffix)
        elif mats_in.is_file():
            mat_path = mats_in
        else:
            mat_path = mats_in / (img_path.stem + args.mat_suffix)

        if not mat_path.exists():
            raise FileNotFoundError(f"Missing mat for {img_path.name}: {mat_path}")

        process_one(
            img_path=img_path,
            mat_path=mat_path,
            out_dir=out_dir,
            box_w=args.box_w,
            box_h=args.box_h,
            class_id=args.class_id,
            coord_mode=args.coord_mode,
            scale_mode=args.scale_mode,
            save_vis=not args.no_vis,
            adaptive_box=args.adaptive_box,
        )


if __name__ == "__main__":
    main()
