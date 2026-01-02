"""ROI 模板服务

提供预设模板列表与查询能力。
"""

from typing import Optional

from app.schemas.roi import ROITemplate, ROITemplateRegion, Point


class ROITemplateService:
    """ROI 模板服务（静态模板库）"""

    def __init__(self) -> None:
        self._templates = [
            ROITemplate(
                id="entry_double",
                name="双入口分区",
                description="适合双入口/双通道场景",
                tags=["入口", "通道"],
                regions=[
                    ROITemplateRegion(
                        name="入口左",
                        points=[
                            Point(x=0.05, y=0.15),
                            Point(x=0.48, y=0.15),
                            Point(x=0.48, y=0.85),
                            Point(x=0.05, y=0.85),
                        ],
                    ),
                    ROITemplateRegion(
                        name="入口右",
                        points=[
                            Point(x=0.52, y=0.15),
                            Point(x=0.95, y=0.15),
                            Point(x=0.95, y=0.85),
                            Point(x=0.52, y=0.85),
                        ],
                    ),
                ],
            ),
            ROITemplate(
                id="plaza_quadrant",
                name="广场四象限",
                description="适合广场或大厅四分区",
                tags=["广场"],
                regions=[
                    ROITemplateRegion(
                        name="左上",
                        points=[
                            Point(x=0.05, y=0.05),
                            Point(x=0.48, y=0.05),
                            Point(x=0.48, y=0.48),
                            Point(x=0.05, y=0.48),
                        ],
                    ),
                    ROITemplateRegion(
                        name="右上",
                        points=[
                            Point(x=0.52, y=0.05),
                            Point(x=0.95, y=0.05),
                            Point(x=0.95, y=0.48),
                            Point(x=0.52, y=0.48),
                        ],
                    ),
                    ROITemplateRegion(
                        name="左下",
                        points=[
                            Point(x=0.05, y=0.52),
                            Point(x=0.48, y=0.52),
                            Point(x=0.48, y=0.95),
                            Point(x=0.05, y=0.95),
                        ],
                    ),
                    ROITemplateRegion(
                        name="右下",
                        points=[
                            Point(x=0.52, y=0.52),
                            Point(x=0.95, y=0.52),
                            Point(x=0.95, y=0.95),
                            Point(x=0.52, y=0.95),
                        ],
                    ),
                ],
            ),
        ]

    def list_templates(self) -> list[ROITemplate]:
        """获取模板列表"""
        return self._templates

    def get_template(self, template_id: str) -> Optional[ROITemplate]:
        """获取指定模板"""
        for template in self._templates:
            if template.id == template_id:
                return template
        return None


_roi_template_service: Optional[ROITemplateService] = None


def get_roi_template_service() -> ROITemplateService:
    """获取 ROI 模板服务单例"""
    global _roi_template_service
    if _roi_template_service is None:
        _roi_template_service = ROITemplateService()
    return _roi_template_service
