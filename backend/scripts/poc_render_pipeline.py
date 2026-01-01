#!/usr/bin/env python
"""方案 F PoC：验证 ffmpeg subprocess 解码/编码链路

验证目标：
1. 用 ffmpeg 从 ZLM 拉 RTSP 流，解码输出 raw frames 到 pipe
2. Python 读取 pipe，叠加简单图形
3. 通过 ffmpeg 编码推 RTMP 到 ZLM
4. 验证 24fps 输出与延迟

使用方法：
    python scripts/poc_render_pipeline.py --src rtsp://zlmediakit:554/live/test --dst rtmp://zlmediakit:1935/live/test_heatmap

验收标准：
- 单路 720p 流，CPU 占用 <150% 单核
- 端到端延迟 <5s
"""

import argparse
import subprocess
import sys
import time
from typing import Optional

import cv2
import numpy as np


def create_ffmpeg_reader(
    src_url: str,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
) -> subprocess.Popen:
    """创建 ffmpeg 拉流解码进程
    
    Args:
        src_url: RTSP 源地址
        width: 输出宽度
        height: 输出高度
        fps: 输出帧率
        
    Returns:
        ffmpeg 子进程
    """
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "tcp",  # 使用 TCP 传输，更稳定
        "-i", src_url,
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-an",  # 禁用音频
        "-sn",  # 禁用字幕
        "-loglevel", "warning",
        "pipe:1"  # 输出到 stdout
    ]
    
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=width * height * 3 * 2  # 2 帧缓冲
    )


def create_ffmpeg_writer(
    dst_url: str,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
) -> subprocess.Popen:
    """创建 ffmpeg 编码推流进程
    
    Args:
        dst_url: RTMP 目标地址
        width: 输入宽度
        height: 输入高度
        fps: 输入帧率
        
    Returns:
        ffmpeg 子进程
    """
    cmd = [
        "ffmpeg",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "pipe:0",  # 从 stdin 读取
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-g", str(fps * 2),  # GOP = 2 秒
        "-bf", "0",  # 禁用 B 帧
        "-f", "flv",
        "-loglevel", "warning",
        dst_url
    ]
    
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=width * height * 3 * 2
    )


def draw_simple_overlay(frame: np.ndarray, frame_count: int) -> np.ndarray:
    """在帧上绘制简单叠加图形（模拟热力图）
    
    Args:
        frame: BGR 图像
        frame_count: 帧计数
        
    Returns:
        叠加后的图像
    """
    h, w = frame.shape[:2]
    
    # 创建简单的热力图效果（渐变色块）
    overlay = np.zeros((h, w, 3), dtype=np.uint8)
    
    # 绘制移动的色块模拟热力图
    cx = int((frame_count * 5) % w)
    cy = int(h / 2)
    cv2.circle(overlay, (cx, cy), 100, (0, 0, 255), -1)  # 红色圆
    cv2.circle(overlay, (w - cx, cy), 80, (0, 255, 255), -1)  # 黄色圆
    
    # 高斯模糊使其更像热力图
    overlay = cv2.GaussianBlur(overlay, (51, 51), 0)
    
    # 叠加到原图
    alpha = 0.4
    result = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)
    
    # 添加帧计数和时间戳
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(
        result, f"Frame: {frame_count} | {timestamp}",
        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
    )
    
    return result


def run_pipeline(
    src_url: str,
    dst_url: str,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
    duration: int = 30,
) -> dict:
    """运行渲染管线
    
    Args:
        src_url: RTSP 源地址
        dst_url: RTMP 目标地址
        width: 视频宽度
        height: 视频高度
        fps: 帧率
        duration: 运行时长（秒）
        
    Returns:
        性能统计
    """
    print(f"启动渲染管线...")
    print(f"  源: {src_url}")
    print(f"  目标: {dst_url}")
    print(f"  分辨率: {width}x{height} @ {fps}fps")
    print(f"  时长: {duration}s")
    print()
    
    frame_size = width * height * 3
    frame_count = 0
    start_time = time.time()
    
    # 性能统计
    read_times = []
    process_times = []
    write_times = []
    
    reader: Optional[subprocess.Popen] = None
    writer: Optional[subprocess.Popen] = None
    
    try:
        # 启动 ffmpeg 进程
        print("启动 ffmpeg reader...")
        reader = create_ffmpeg_reader(src_url, width, height, fps)
        
        print("启动 ffmpeg writer...")
        writer = create_ffmpeg_writer(dst_url, width, height, fps)
        
        print("管线启动成功，开始处理帧...")
        print()
        
        while time.time() - start_time < duration:
            # 读取帧
            t0 = time.time()
            raw_frame = reader.stdout.read(frame_size)
            
            if len(raw_frame) != frame_size:
                print(f"读取帧失败: 期望 {frame_size} 字节，实际 {len(raw_frame)} 字节")
                break
            
            t1 = time.time()
            read_times.append(t1 - t0)
            
            # 转换为 numpy 数组
            frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3))
            
            # 处理帧（叠加图形）
            processed = draw_simple_overlay(frame, frame_count)
            t2 = time.time()
            process_times.append(t2 - t1)
            
            # 写入帧
            writer.stdin.write(processed.tobytes())
            t3 = time.time()
            write_times.append(t3 - t2)
            
            frame_count += 1
            
            # 每秒打印一次统计
            if frame_count % fps == 0:
                elapsed = time.time() - start_time
                actual_fps = frame_count / elapsed
                avg_read = sum(read_times[-fps:]) / fps * 1000
                avg_process = sum(process_times[-fps:]) / fps * 1000
                avg_write = sum(write_times[-fps:]) / fps * 1000
                print(
                    f"帧 {frame_count:5d} | "
                    f"实际 FPS: {actual_fps:.1f} | "
                    f"读取: {avg_read:.1f}ms | "
                    f"处理: {avg_process:.1f}ms | "
                    f"写入: {avg_write:.1f}ms"
                )
    
    except KeyboardInterrupt:
        print("\n用户中断")
    
    except Exception as e:
        print(f"错误: {e}")
        if reader and reader.stderr:
            stderr = reader.stderr.read()
            if stderr:
                print(f"Reader stderr: {stderr.decode()}")
        if writer and writer.stderr:
            stderr = writer.stderr.read()
            if stderr:
                print(f"Writer stderr: {stderr.decode()}")
    
    finally:
        # 清理
        if reader:
            reader.terminate()
            reader.wait()
        if writer:
            if writer.stdin:
                writer.stdin.close()
            writer.terminate()
            writer.wait()
    
    # 计算统计
    elapsed = time.time() - start_time
    stats = {
        "total_frames": frame_count,
        "elapsed_sec": elapsed,
        "actual_fps": frame_count / elapsed if elapsed > 0 else 0,
        "avg_read_ms": sum(read_times) / len(read_times) * 1000 if read_times else 0,
        "avg_process_ms": sum(process_times) / len(process_times) * 1000 if process_times else 0,
        "avg_write_ms": sum(write_times) / len(write_times) * 1000 if write_times else 0,
    }
    
    print()
    print("=" * 60)
    print("性能统计:")
    print(f"  总帧数: {stats['total_frames']}")
    print(f"  运行时长: {stats['elapsed_sec']:.1f}s")
    print(f"  实际 FPS: {stats['actual_fps']:.1f}")
    print(f"  平均读取耗时: {stats['avg_read_ms']:.2f}ms")
    print(f"  平均处理耗时: {stats['avg_process_ms']:.2f}ms")
    print(f"  平均写入耗时: {stats['avg_write_ms']:.2f}ms")
    print(f"  总延迟估算: {stats['avg_read_ms'] + stats['avg_process_ms'] + stats['avg_write_ms']:.2f}ms/帧")
    print("=" * 60)
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="方案 F PoC：ffmpeg 渲染管线验证")
    parser.add_argument("--src", required=True, help="RTSP 源地址")
    parser.add_argument("--dst", required=True, help="RTMP 目标地址")
    parser.add_argument("--width", type=int, default=1280, help="视频宽度")
    parser.add_argument("--height", type=int, default=720, help="视频高度")
    parser.add_argument("--fps", type=int, default=24, help="帧率")
    parser.add_argument("--duration", type=int, default=30, help="运行时长（秒）")
    
    args = parser.parse_args()
    
    stats = run_pipeline(
        src_url=args.src,
        dst_url=args.dst,
        width=args.width,
        height=args.height,
        fps=args.fps,
        duration=args.duration,
    )
    
    # 验收判断
    print()
    if stats["actual_fps"] >= args.fps * 0.9:
        print("✓ FPS 达标")
    else:
        print(f"✗ FPS 不达标: {stats['actual_fps']:.1f} < {args.fps * 0.9:.1f}")
    
    total_latency = stats["avg_read_ms"] + stats["avg_process_ms"] + stats["avg_write_ms"]
    if total_latency < 100:  # 单帧处理 <100ms
        print("✓ 单帧延迟达标")
    else:
        print(f"✗ 单帧延迟过高: {total_latency:.1f}ms")


if __name__ == "__main__":
    main()
