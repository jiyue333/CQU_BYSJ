"""
导出任务 Repository

ExportTask 的数据库操作
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.export_task import ExportTask


class ExportTaskRepository:
    """导出任务仓储"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, task: ExportTask) -> ExportTask:
        """创建导出任务"""
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: str) -> Optional[ExportTask]:
        """根据 ID 获取任务"""
        return self.db.get(ExportTask, task_id)

    def get_by_source_id(
        self,
        source_id: str,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> list[ExportTask]:
        """获取数据源的导出任务列表"""
        stmt = select(ExportTask).where(ExportTask.source_id == source_id)
        if status:
            stmt = stmt.where(ExportTask.status == status)
        stmt = stmt.order_by(ExportTask.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_pending_tasks(self) -> list[ExportTask]:
        """获取所有待处理的任务"""
        stmt = (
            select(ExportTask)
            .where(ExportTask.status == "pending")
            .order_by(ExportTask.created_at)
        )
        return list(self.db.scalars(stmt).all())

    def get_processing_tasks(self) -> list[ExportTask]:
        """获取正在处理的任务"""
        stmt = select(ExportTask).where(ExportTask.status == "processing")
        return list(self.db.scalars(stmt).all())

    def update_status(
        self,
        task_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[ExportTask]:
        """更新任务状态"""
        task = self.get_by_id(task_id)
        if not task:
            return None

        task.status = status
        if error_message:
            task.error_message = error_message
        if status in ("completed", "failed"):
            task.completed_at = datetime.utcnow().isoformat() + "Z"

        self.db.commit()
        self.db.refresh(task)
        return task

    def complete_task(
        self,
        task_id: str,
        file_path: str,
        file_url: str,
        file_size: int,
    ) -> Optional[ExportTask]:
        """完成任务"""
        task = self.get_by_id(task_id)
        if not task:
            return None

        task.status = "completed"
        task.file_path = file_path
        task.file_url = file_url
        task.file_size = file_size
        task.completed_at = datetime.utcnow().isoformat() + "Z"

        self.db.commit()
        self.db.refresh(task)
        return task

    def fail_task(self, task_id: str, error_message: str) -> Optional[ExportTask]:
        """标记任务失败"""
        return self.update_status(task_id, "failed", error_message)

    def delete(self, task_id: str) -> bool:
        """删除任务"""
        task = self.get_by_id(task_id)
        if task:
            self.db.delete(task)
            self.db.commit()
            return True
        return False

    def delete_completed_tasks(self, source_id: str, before: str) -> int:
        """删除已完成的旧任务"""
        stmt = select(ExportTask).where(
            ExportTask.source_id == source_id,
            ExportTask.status == "completed",
            ExportTask.created_at < before,
        )
        tasks = list(self.db.scalars(stmt).all())
        count = len(tasks)
        for task in tasks:
            self.db.delete(task)
        self.db.commit()
        return count
