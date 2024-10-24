from sqlalchemy import Column, LargeBinary, String, Boolean

from core.db.base_class import Base


class ScheduleFile(Base):
    __tablename__ = "schedule_files"

    original_name = Column(String, nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    visible = Column(Boolean, default=True)
