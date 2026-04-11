"""
Comet ML 初始化工具
首次使用前运行此脚本完成 Comet 登录和配置:
    python train/setup_comet.py
"""

from __future__ import annotations

import subprocess
import sys


def check_comet():
    try:
        import comet_ml
        print(f"[OK] comet_ml 已安装, 版本: {comet_ml.__version__}")
        return True
    except ImportError:
        return False


def install_comet():
    print("[安装] 正在安装 comet_ml ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "comet_ml"])
    print("[OK] comet_ml 安装完成")


def init_comet():
    import comet_ml

    print("\n" + "=" * 50)
    print("Comet ML 初始化向导")
    print("=" * 50)
    print("\n步骤:")
    print("  1. 在 https://www.comet.com/signup 注册账号")
    print("  2. 获取 API Key: https://www.comet.com/account/apiKeys")
    print()

    api_key = input("请输入 Comet API Key (或回车跳过用浏览器登录): ").strip()

    if api_key:
        import os
        os.environ["COMET_API_KEY"] = api_key
        # 写入 shell profile
        shell_rc = os.path.expanduser("~/.zshrc")
        print(f"\n[提示] 建议将以下行添加到 {shell_rc}:")
        print(f'  export COMET_API_KEY="{api_key}"')
    else:
        print("\n[登录] 通过浏览器登录...")
        comet_ml.login(project_name="CQU_BYSJ-test")

    # 验证
    print("\n[验证] 测试 Comet 连接...")
    try:
        experiment = comet_ml.start(project_name="CQU_BYSJ-test")
        experiment.log_parameter("test", True)
        experiment.end()
        print("[OK] Comet 连接成功! 可以在 Comet Web UI 查看测试实验")
    except Exception as e:
        print(f"[警告] 连接测试失败: {e}")
        print("请检查 API Key 后重试")

    print("\nComet 自动记录的指标:")
    print("  - 训练损失 (box/cls/dfl)")
    print("  - 验证指标 (mAP50, mAP50-95, precision, recall)")
    print("  - 学习率曲线")
    print("  - 模型 GFLOPs, 参数量, 推理时间 (首个 epoch)")
    print("  - F1/P/R/PR 曲线图")
    print("  - 混淆矩阵, 预测样本, 模型权重")
    print("  - 系统资源 (GPU/CPU/内存)")
    print("  - F1 标量 (通过自定义训练器)")


def main():
    if not check_comet():
        install = input("[未安装] 是否安装 comet_ml? [Y/n]: ").strip().lower()
        if install in ("", "y", "yes"):
            install_comet()
        else:
            print("跳过安装, Comet 日志功能不可用")
            return

    init_comet()
    print("\n[完成] Comet 配置完成, 训练时将自动记录日志")


if __name__ == "__main__":
    main()
