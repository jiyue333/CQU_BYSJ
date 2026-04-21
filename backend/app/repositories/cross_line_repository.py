"""CrossLine Repository"""

from sqlalchemy.orm import Session

from app.models.cross_line import CrossLine


class CrossLineRepository:
    """计数线段数据仓库"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, cross_line: CrossLine) -> CrossLine:
        self.db.add(cross_line)
        self.db.commit()
        self.db.refresh(cross_line)
        return cross_line

    def get_by_id(self, line_id: str) -> CrossLine | None:
        return self.db.query(CrossLine).filter(CrossLine.line_id == line_id).first()

    def get_by_source_id(self, source_id: str) -> list[CrossLine]:
        return (
            self.db.query(CrossLine)
            .filter(CrossLine.source_id == source_id, CrossLine.is_active == 1)
            .all()
        )

    def update(self, cross_line: CrossLine, **kwargs) -> CrossLine:
        for key, value in kwargs.items():
            if hasattr(cross_line, key):
                setattr(cross_line, key, value)
        self.db.commit()
        self.db.refresh(cross_line)
        return cross_line

    def delete(self, line_id: str) -> None:
        self.db.query(CrossLine).filter(CrossLine.line_id == line_id).delete()
        self.db.commit()
