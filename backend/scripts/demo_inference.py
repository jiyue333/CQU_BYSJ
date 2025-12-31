#!/usr/bin/env python
"""YOLO 推理演示脚本

下载测试图片，执行人体检测，并保存带标注的结果图片。
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import requests
from pathlib import Path

from app.services.inference_service import InferenceService
from app.services.heatmap_generator import HeatmapGenerator


def download_test_image(url: str, save_path: Path) -> bool:
    """下载测试图片"""
    try:
        print(f"下载测试图片: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        save_path.write_bytes(response.content)
        print(f"✓ 图片已保存到: {save_path}")
        return True
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        return False


def draw_detections(image: np.ndarray, detections: list, color=(0, 255, 0)) -> np.ndarray:
    """在图片上绘制检测框"""
    result = image.copy()
    
    for i, det in enumerate(detections):
        x, y, w, h = det.x, det.y, det.width, det.height
        conf = det.confidence
        
        # 绘制边界框
        cv2.rectangle(result, (x, y), (x + w, y + h), color, 2)
        
        # 绘制标签背景
        label = f"person {conf:.2f}"
        (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(result, (x, y - label_h - 10), (x + label_w + 5, y), color, -1)
        
        # 绘制标签文字
        cv2.putText(result, label, (x + 2, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    return result


def draw_heatmap_overlay(image: np.ndarray, heatmap: list[list[float]], alpha: float = 0.4) -> np.ndarray:
    """在图片上叠加热力图"""
    h, w = image.shape[:2]
    grid_h, grid_w = len(heatmap), len(heatmap[0])
    
    # 创建热力图
    heatmap_array = np.array(heatmap, dtype=np.float32)
    heatmap_resized = cv2.resize(heatmap_array, (w, h), interpolation=cv2.INTER_LINEAR)
    
    # 归一化到 0-255
    heatmap_normalized = (heatmap_resized * 255).astype(np.uint8)
    
    # 应用颜色映射 (COLORMAP_JET: 蓝->绿->黄->红)
    heatmap_colored = cv2.applyColorMap(heatmap_normalized, cv2.COLORMAP_JET)
    
    # 叠加到原图
    result = cv2.addWeighted(image, 1 - alpha, heatmap_colored, alpha, 0)
    
    return result


def main():
    # 创建输出目录
    output_dir = Path("demo_output")
    output_dir.mkdir(exist_ok=True)
    
    # 测试图片 URL（人群图片）
    test_images = [
        {
            "name": "crowd_street",
            "url": "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?w=800",
            "description": "街道人群"
        },
        {
            "name": "crowd_event", 
            "url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800",
            "description": "活动人群"
        },
    ]
    
    # 初始化推理服务
    print("\n" + "="*60)
    print("初始化 YOLO 推理服务...")
    print("="*60)
    
    service = InferenceService(confidence_threshold=0.3)
    service.load_model()
    service.warmup()
    print("✓ 模型加载完成\n")
    
    # 初始化热力图生成器
    heatmap_gen = HeatmapGenerator(grid_size=20, alpha=1.0)  # alpha=1.0 表示不使用 EMA
    
    # 处理每张测试图片
    for img_info in test_images:
        print("="*60)
        print(f"处理图片: {img_info['description']}")
        print("="*60)
        
        # 下载图片
        img_path = output_dir / f"{img_info['name']}_input.jpg"
        if not img_path.exists():
            if not download_test_image(img_info["url"], img_path):
                continue
        
        # 读取图片
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"✗ 无法读取图片: {img_path}")
            continue
        
        h, w = image.shape[:2]
        print(f"图片尺寸: {w}x{h}")
        
        # 编码为 JPEG bytes（模拟从网关获取的快照）
        _, jpeg_bytes = cv2.imencode('.jpg', image)
        jpeg_bytes = jpeg_bytes.tobytes()
        
        # 执行推理
        print("执行 YOLO 推理...")
        detections, (frame_w, frame_h) = service.infer_with_size(jpeg_bytes)
        
        print(f"\n检测结果:")
        print(f"  - 检测到 {len(detections)} 个人")
        for i, det in enumerate(detections):
            print(f"  - 人物 {i+1}: 位置=({det.x}, {det.y}), 尺寸={det.width}x{det.height}, 置信度={det.confidence:.3f}")
        
        # 生成热力图
        heatmap = heatmap_gen.generate(img_info["name"], detections, frame_w, frame_h)
        
        # 绘制检测结果
        result_detections = draw_detections(image, detections)
        
        # 绘制热力图叠加
        result_heatmap = draw_heatmap_overlay(image, heatmap, alpha=0.4)
        
        # 绘制检测框 + 热力图
        result_combined = draw_heatmap_overlay(result_detections, heatmap, alpha=0.3)
        
        # 保存结果
        det_path = output_dir / f"{img_info['name']}_detections.jpg"
        heatmap_path = output_dir / f"{img_info['name']}_heatmap.jpg"
        combined_path = output_dir / f"{img_info['name']}_combined.jpg"
        
        cv2.imwrite(str(det_path), result_detections)
        cv2.imwrite(str(heatmap_path), result_heatmap)
        cv2.imwrite(str(combined_path), result_combined)
        
        print(f"\n输出文件:")
        print(f"  - 检测结果: {det_path}")
        print(f"  - 热力图: {heatmap_path}")
        print(f"  - 组合图: {combined_path}")
        print()
    
    print("="*60)
    print("✓ 演示完成！")
    print(f"结果保存在: {output_dir.absolute()}")
    print("="*60)


if __name__ == "__main__":
    main()
