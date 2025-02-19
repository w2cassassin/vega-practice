from sqlalchemy import JSON, Boolean, Column, Integer, LargeBinary, String

from core.db.base_class import BaseWithTimestamp


class ScheduleFile(BaseWithTimestamp):
    __tablename__ = "schedule_files"

    original_name = Column(String, nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    visible = Column(Boolean, default=True)
    standardized_content = Column(JSON, nullable=True)
    group_count = Column(Integer, default=0)  # New field
