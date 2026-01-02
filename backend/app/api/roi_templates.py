"""ROI 模板 REST API"""

from fastapi import APIRouter

from app.schemas.roi import ROITemplateListResponse
from app.services.roi_template_service import get_roi_template_service

router = APIRouter()


@router.get(
    "/templates",
    response_model=ROITemplateListResponse,
    summary="获取 ROI 模板列表",
    description="获取预设 ROI 模板库"
)
async def list_roi_templates() -> ROITemplateListResponse:
    """获取 ROI 模板列表"""
    service = get_roi_template_service()
    templates = service.list_templates()
    return ROITemplateListResponse(templates=templates, total=len(templates))
