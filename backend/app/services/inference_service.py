"""YOLO 推理服务

负责加载 YOLOv8 模型并执行人体检测推理。
"""

import io
import time
from typing import Optional

import cv2
import numpy as np
import structlog
from PIL import Image
from ultralytics import YOLO

from app.core.config import settings
from app.schemas.detection import Detection

logger = structlog.get_logger(__name__)

# COCO 数据集中 person 类别的 ID
PERSON_CLASS_ID = 0


class InferenceService:
    """YOLO 推理服务
    
    负责：
    1. 加载 YOLOv8n 预训练模型
    2. 执行人体检测推理
    3. 置信度过滤
    """
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: Optional[float] = None,
        device: str = "cpu",
    ):
        """初始化推理服务
        
        Args:
            model_path: 模型路径，默认使用 YOLOv8n
            confidence_threshold: 置信度阈值，默认使用配置值
            device: 推理设备，"cpu" 或 "cuda"
        """
        self.model_path = model_path
        self.confidence_threshold = (
            settings.confidence_threshold if confidence_threshold is None else confidence_threshold
        )
        self.device = device
        self._model: Optional[YOLO] = None
        self._warmup_done = False
        
    def load_model(self) -> None:
        """加载 YOLO 模型
        
        Raises:
            RuntimeError: 模型加载失败
        """
        try:
            start_time = time.time()
            logger.info("loading_yolo_model", model_path=self.model_path, device=self.device)
            
            self._model = YOLO(self.model_path)
            
            load_time = time.time() - start_time
            logger.info("yolo_model_loaded", load_time_sec=round(load_time, 3))
            
        except Exception as e:
            logger.error("yolo_model_load_failed", error=str(e))
            raise RuntimeError(f"Failed to load YOLO model: {e}") from e
    
    def warmup(self, image_size: tuple[int, int] = (640, 480)) -> None:
        """模型预热
        
        执行一次空推理以预热模型，减少首次推理延迟。
        
        Args:
            image_size: 预热图像尺寸 (width, height)
        """
        if self._model is None:
            self.load_model()
        
        if self._warmup_done:
            return
            
        try:
            start_time = time.time()
            logger.info("warming_up_model", image_size=image_size)
            
            # 创建空白图像进行预热
            dummy_image = np.zeros((image_size[1], image_size[0], 3), dtype=np.uint8)
            self._model.predict(
                dummy_image,
                classes=[PERSON_CLASS_ID],
                conf=self.confidence_threshold,
                device=self.device,
                verbose=False,
            )
            
            warmup_time = time.time() - start_time
            self._warmup_done = True
            logger.info("model_warmup_complete", warmup_time_sec=round(warmup_time, 3))
            
        except Exception as e:
            logger.warning("model_warmup_failed", error=str(e))
    
    def infer_from_bytes(
        self,
        image_bytes: bytes,
        confidence_threshold: Optional[float] = None,
    ) -> list[Detection]:
        """从 JPEG bytes 执行推理
        
        Args:
            image_bytes: JPEG 图像字节数据
            confidence_threshold: 置信度阈值，None 则使用默认值
            
        Returns:
            检测结果列表
            
        Raises:
            ValueError: 图像解码失败
            RuntimeError: 推理失败
        """
        if self._model is None:
            self.load_model()
            self.warmup()
        
        conf_threshold = (
            self.confidence_threshold if confidence_threshold is None else confidence_threshold
        )
        
        # 解码图像
        try:
            image = self._decode_image(image_bytes)
        except Exception as e:
            logger.error("image_decode_failed", error=str(e))
            raise ValueError(f"Failed to decode image: {e}") from e
        
        # 执行推理
        try:
            start_time = time.time()
            
            results = self._model.predict(
                image,
                classes=[PERSON_CLASS_ID],
                conf=conf_threshold,
                device=self.device,
                verbose=False,
            )
            
            inference_time = time.time() - start_time
            
            # 解析检测结果
            detections = self._parse_results(results, conf_threshold)
            
            logger.debug(
                "inference_complete",
                inference_time_ms=round(inference_time * 1000, 2),
                detection_count=len(detections),
                confidence_threshold=conf_threshold,
            )
            
            return detections
            
        except Exception as e:
            logger.error("inference_failed", error=str(e))
            raise RuntimeError(f"Inference failed: {e}") from e
    
    def infer_from_numpy(
        self,
        image: np.ndarray,
        confidence_threshold: Optional[float] = None,
    ) -> list[Detection]:
        """从 numpy 数组执行推理
        
        Args:
            image: BGR 格式的图像数组
            confidence_threshold: 置信度阈值
            
        Returns:
            检测结果列表
        """
        if self._model is None:
            self.load_model()
            self.warmup()
        
        conf_threshold = (
            self.confidence_threshold if confidence_threshold is None else confidence_threshold
        )
        
        try:
            start_time = time.time()
            
            results = self._model.predict(
                image,
                classes=[PERSON_CLASS_ID],
                conf=conf_threshold,
                device=self.device,
                verbose=False,
            )
            
            inference_time = time.time() - start_time
            detections = self._parse_results(results, conf_threshold)
            
            logger.debug(
                "inference_complete",
                inference_time_ms=round(inference_time * 1000, 2),
                detection_count=len(detections),
            )
            
            return detections
            
        except Exception as e:
            logger.error("inference_failed", error=str(e))
            raise RuntimeError(f"Inference failed: {e}") from e
    
    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        """解码 JPEG 图像
        
        Args:
            image_bytes: JPEG 图像字节数据
            
        Returns:
            BGR 格式的 numpy 数组
            
        Raises:
            ValueError: 解码失败
        """
        # 方法1: 使用 OpenCV 解码
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            # 方法2: 尝试使用 PIL 解码
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            except Exception:
                raise ValueError("Failed to decode image with both OpenCV and PIL")
        
        return image
    
    def _parse_results(
        self,
        results: list,
        confidence_threshold: float,
    ) -> list[Detection]:
        """解析 YOLO 推理结果
        
        Args:
            results: YOLO 推理结果
            confidence_threshold: 置信度阈值
            
        Returns:
            Detection 对象列表
        """
        detections: list[Detection] = []
        
        if not results or len(results) == 0:
            return detections
        
        result = results[0]  # 单张图像只有一个结果
        
        if result.boxes is None or len(result.boxes) == 0:
            return detections
        
        boxes = result.boxes
        
        for i in range(len(boxes)):
            # 获取边界框坐标 (xyxy 格式)
            box = boxes.xyxy[i].cpu().numpy()
            conf = float(boxes.conf[i].cpu().numpy())
            cls_id = int(boxes.cls[i].cpu().numpy())
            
            # 只处理 person 类别且置信度满足阈值
            if cls_id != PERSON_CLASS_ID or conf < confidence_threshold:
                continue
            
            x1, y1, x2, y2 = box
            
            detection = Detection(
                x=int(x1),
                y=int(y1),
                width=int(x2 - x1),
                height=int(y2 - y1),
                confidence=round(conf, 4),
            )
            detections.append(detection)
        
        return detections
    
    def get_image_size(self, image_bytes: bytes) -> tuple[int, int]:
        """获取图像尺寸
        
        Args:
            image_bytes: JPEG 图像字节数据
            
        Returns:
            (width, height) 元组
        """
        image = self._decode_image(image_bytes)
        height, width = image.shape[:2]
        return (width, height)
    
    def infer_with_size(
        self,
        image_bytes: bytes,
        confidence_threshold: Optional[float] = None,
    ) -> tuple[list[Detection], tuple[int, int]]:
        """从 JPEG bytes 执行推理并返回图像尺寸
        
        避免重复解码图像。
        
        Args:
            image_bytes: JPEG 图像字节数据
            confidence_threshold: 置信度阈值
            
        Returns:
            (检测结果列表, (width, height)) 元组
        """
        if self._model is None:
            self.load_model()
            self.warmup()
        
        conf_threshold = (
            self.confidence_threshold if confidence_threshold is None else confidence_threshold
        )
        
        # 解码图像（只解码一次）
        try:
            image = self._decode_image(image_bytes)
        except Exception as e:
            logger.error("image_decode_failed", error=str(e))
            raise ValueError(f"Failed to decode image: {e}") from e
        
        height, width = image.shape[:2]
        
        # 执行推理
        try:
            start_time = time.time()
            
            results = self._model.predict(
                image,
                classes=[PERSON_CLASS_ID],
                conf=conf_threshold,
                device=self.device,
                verbose=False,
            )
            
            inference_time = time.time() - start_time
            detections = self._parse_results(results, conf_threshold)
            
            logger.debug(
                "inference_with_size_complete",
                inference_time_ms=round(inference_time * 1000, 2),
                detection_count=len(detections),
                image_size=(width, height),
            )
            
            return detections, (width, height)
            
        except Exception as e:
            logger.error("inference_failed", error=str(e))
            raise RuntimeError(f"Inference failed: {e}") from e
    
    @property
    def is_loaded(self) -> bool:
        """模型是否已加载"""
        return self._model is not None
    
    def update_confidence_threshold(self, threshold: float) -> None:
        """更新置信度阈值
        
        Args:
            threshold: 新的置信度阈值 (0.0-1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        self.confidence_threshold = threshold
        logger.info("confidence_threshold_updated", threshold=threshold)


# 全局单例
_inference_service: Optional[InferenceService] = None


def get_inference_service() -> InferenceService:
    """获取推理服务单例"""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service


def filter_by_confidence(
    detections: list[Detection],
    threshold: float,
) -> list[Detection]:
    """按置信度过滤检测结果
    
    这是一个纯函数，用于属性测试。
    
    Args:
        detections: 检测结果列表
        threshold: 置信度阈值
        
    Returns:
        过滤后的检测结果列表，所有结果的置信度 >= threshold
    """
    return [d for d in detections if d.confidence >= threshold]
