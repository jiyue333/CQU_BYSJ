"""
VLM 面积估算服务

通过视觉大模型（VLM）分析场景截图，估算各区域的物理面积（m²）。
用于将像素密度转换为有物理意义的 人/m² 密度。
"""

import base64
import json
import re

import cv2
import httpx
import numpy as np

from app.core.config import settings
from app.core.logger import logger


class VLMAreaEstimator:
    """VLM 面积估算器 — 调用视觉大模型估算场景区域的物理面积"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or settings.VLM_API_KEY
        self.model = model or settings.VLM_MODEL
        self.base_url = (base_url or settings.VLM_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.VLM_TIMEOUT

    def _draw_regions_on_frame(
        self,
        frame: np.ndarray,
        regions: dict[str, list[tuple[float, float]]],
    ) -> np.ndarray:
        """
        在帧上绘制区域多边形并标注名称，供 VLM 识别。
        """
        annotated = frame.copy()
        colors = [
            (0, 255, 0),
            (255, 0, 0),
            (0, 0, 255),
            (255, 255, 0),
            (0, 255, 255),
            (255, 0, 255),
        ]

        for idx, (name, polygon) in enumerate(regions.items()):
            color = colors[idx % len(colors)]
            pts = np.array(polygon, dtype=np.int32)

            # 绘制多边形
            cv2.polylines(annotated, [pts], isClosed=True, color=color, thickness=3)

            # 半透明填充
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, annotated)

            # 标注区域名称（在多边形质心处）
            cx = int(pts[:, 0].mean())
            cy = int(pts[:, 1].mean())

            label = name
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0
            thickness = 2
            (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)

            # 背景
            cv2.rectangle(
                annotated,
                (cx - tw // 2 - 4, cy - th // 2 - 4),
                (cx + tw // 2 + 4, cy + th // 2 + 4),
                color,
                -1,
            )
            # 文字
            cv2.putText(
                annotated,
                label,
                (cx - tw // 2, cy + th // 2),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )

        return annotated

    def _encode_frame(self, frame: np.ndarray, quality: int = 85) -> str:
        """将帧编码为 base64 字符串"""
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer).decode("utf-8")

    def _build_prompt(self, region_names: list[str]) -> str:
        """构建发送给 VLM 的 prompt"""
        names_str = "、".join(f'"{n}"' for n in region_names)
        return f"""你是一个专业的场景空间分析专家。请分析这张监控画面截图。

画面中用彩色多边形标注了以下区域：{names_str}

请根据画面中的视觉线索（如地砖大小、门框宽度、走道宽度、家具尺寸、人体比例等参照物）来估算每个标注区域的真实物理面积（单位：平方米）。

要求：
1. 仔细观察画面中的参照物来推断尺度
2. 考虑相机的透视效果（近大远小）
3. 给出每个区域的物理面积估算值
4. 只需要给出合理的估算，不要求精确

请严格按以下 JSON 格式输出，不要包含其他内容：
{{"areas": {{{", ".join(f'"{n}": <面积数值>' for n in region_names)}}}}}

示例输出：
{{"areas": {{{", ".join(f'"{n}": 25.0' for n in region_names)}}}}}"""

    def _parse_response(self, text: str, region_names: list[str]) -> dict[str, float]:
        """解析 VLM 返回的 JSON 结果"""
        # 尝试从回复中提取 JSON
        # 先尝试直接解析
        try:
            data = json.loads(text)
            if "areas" in data:
                return {k: float(v) for k, v in data["areas"].items() if k in region_names}
            return {k: float(v) for k, v in data.items() if k in region_names}
        except (json.JSONDecodeError, ValueError):
            pass

        # 尝试匹配 JSON 代码块
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "areas" in data:
                    return {k: float(v) for k, v in data["areas"].items() if k in region_names}
                return {k: float(v) for k, v in data.items() if k in region_names}
            except (json.JSONDecodeError, ValueError):
                pass

        # 尝试匹配内联 JSON
        json_match = re.search(r"\{[^{}]*\}", text)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if "areas" in data:
                    return {k: float(v) for k, v in data["areas"].items() if k in region_names}
                return {k: float(v) for k, v in data.items() if k in region_names}
            except (json.JSONDecodeError, ValueError):
                pass

        logger.error(f"[VLM] 无法解析 VLM 响应: {text[:200]}")
        return {}

    async def estimate_areas(
        self,
        frame: np.ndarray,
        regions: dict[str, list[tuple[float, float]]],
    ) -> dict[str, float]:
        """
        估算各区域的物理面积（m²）

        Args:
            frame: BGR 图像帧
            regions: 区域定义 {"区域名": [(x1,y1), (x2,y2), ...]}

        Returns:
            各区域物理面积 {"区域名": 面积m²}
        """
        if not regions:
            return {}

        if not self.api_key:
            logger.warning("[VLM] 未配置 VLM_API_KEY，跳过面积估算")
            return {}

        region_names = list(regions.keys())

        # 在帧上绘制区域标注
        annotated_frame = self._draw_regions_on_frame(frame, regions)
        frame_b64 = self._encode_frame(annotated_frame)

        # 构建 API 请求
        prompt = self._build_prompt(region_names)

        # 检测是否为 reasoning 模型（o1/o3/gpt-5 系列），它们不支持 temperature 和 max_tokens
        model_lower = self.model.lower()
        is_reasoning = any(
            tag in model_lower
            for tag in ("o1", "o3", "o4", "gpt-5", "deepseek-r1", "deepseek-reasoner")
        )

        payload: dict = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{frame_b64}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        }

        if is_reasoning:
            # reasoning 模型使用 max_completion_tokens，不支持 temperature
            payload["max_completion_tokens"] = 1000
            logger.info(f"[VLM] 检测到 reasoning 模型: {self.model}，使用 max_completion_tokens")
        else:
            payload["max_tokens"] = 500
            payload["temperature"] = 0.1

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info(f"[VLM] 开始估算 {len(region_names)} 个区域的物理面积...")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

            result = response.json()
            logger.info(f"[VLM] API 原始响应: {json.dumps(result, ensure_ascii=False)[:1500]}")
            choice = result.get("choices", [{}])[0]
            message = choice.get("message", {})

            # 尝试多种方式获取内容（兼容各种模型/代理格式）
            content = None
            # 1. 标准 content 字段
            if message.get("content"):
                content = message["content"]
            # 2. reasoning_content（某些 reasoning 模型将最终回答放这里）
            if not content and message.get("reasoning_content"):
                content = message["reasoning_content"]
            # 3. 有些代理将 reasoning 输出单独放在 output 字段
            if not content and choice.get("text"):
                content = choice["text"]
            # 4. 某些 API 在 choices[0] 直接放 output
            if not content:
                for key in ("output", "result", "answer"):
                    if choice.get(key):
                        content = choice[key]
                        break

            if not content:
                logger.error(
                    f"[VLM] 响应中无可用 content。"
                    f"finish_reason={choice.get('finish_reason')}, "
                    f"message keys={list(message.keys())}, "
                    f"choice keys={list(choice.keys())}, "
                    f"full message={json.dumps(message, ensure_ascii=False)[:500]}"
                )
                return {}

            text = content
            logger.info(f"[VLM] 收到响应: {text[:300]}")

            areas = self._parse_response(text, region_names)

            if areas:
                for name, area in areas.items():
                    logger.info(f"[VLM] 区域 '{name}' 估算面积: {area:.1f} m²")
            else:
                logger.warning("[VLM] 未能解析出任何区域面积")

            return areas

        except httpx.TimeoutException:
            logger.error(f"[VLM] 请求超时（{self.timeout}s）")
            return {}
        except httpx.HTTPStatusError as e:
            logger.error(f"[VLM] HTTP 错误: {e.response.status_code} - {e.response.text[:200]}")
            return {}
        except Exception as e:
            logger.error(f"[VLM] 面积估算失败: {e}")
            return {}
