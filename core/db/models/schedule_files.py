from sqlalchemy import Boolean, Column, LargeBinary, String, JSON

from core.db.base_class import Base


class ScheduleFile(Base):
    __tablename__ = "schedule_files"

    original_name = Column(String, nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    visible = Column(Boolean, default=True)
    standardized_content = Column(JSON, nullable=True)
