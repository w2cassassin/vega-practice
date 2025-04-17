from sqlalchemy import ARRAY, Column, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from core.db.base_class import BaseWithId


class ScDisc(BaseWithId):
    __tablename__ = "sc_disc"
    title = Column(Text, nullable=False)
    rasp7_entries = relationship(
        "ScRasp7", back_populates="discipline", cascade="all, delete"
    )
    rasp18_entries = relationship(
        "ScRasp18", back_populates="discipline", cascade="all, delete"
    )


class ScGroup(BaseWithId):
    __tablename__ = "sc_group"
    title = Column(Text, nullable=False)
    rasp7_groups = relationship(
        "ScRasp7Groups", back_populates="group", cascade="all, delete"
    )
    rasp18_groups = relationship(
        "ScRasp18Groups", back_populates="group", cascade="all, delete"
    )


class ScPrep(BaseWithId):
    __tablename__ = "sc_prep"
    fio = Column(Text, nullable=False)
    chair = Column(Text)
    degree = Column(Text)
    photo = Column(Text)
    rasp7_entries = relationship(
        "ScRasp7Preps", back_populates="prep", cascade="all, delete"
    )
    rasp18_entries = relationship(
        "ScRasp18Preps", back_populates="prep", cascade="all, delete"
    )


class Students(BaseWithId):
    __tablename__ = "students"
    subgroup = Column(Integer)


class ScRasp7(BaseWithId):
    __tablename__ = "sc_rasp7"
    semcode = Column(Integer, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    disc_id = Column(
        Integer, ForeignKey("sc_disc.id", ondelete="CASCADE"), nullable=False
    )
    weekday = Column(Integer, nullable=False)
    pair = Column(Integer, nullable=False)
    weeksarray = Column(ARRAY(Integer), nullable=False)
    weekstext = Column(String, nullable=False)
    worktype = Column(Integer, nullable=False)
    # removed lesson_type_id

    discipline = relationship("ScDisc", back_populates="rasp7_entries")
    groups = relationship(
        "ScRasp7Groups", back_populates="rasp7", cascade="all, delete"
    )
    rooms = relationship("ScRasp7Rooms", back_populates="rasp7", cascade="all, delete")
    preps = relationship("ScRasp7Preps", back_populates="rasp7", cascade="all, delete")

    __table_args__ = (Index("ix_sc_rasp7_semcode_version", "semcode", "version"),)


class ScRasp7Groups(BaseWithId):
    __tablename__ = "sc_rasp7_groups"
    rasp7_id = Column(
        Integer, ForeignKey("sc_rasp7.id", ondelete="CASCADE"), nullable=False
    )
    group_id = Column(
        Integer, ForeignKey("sc_group.id", ondelete="CASCADE"), nullable=False
    )
    subgroup = Column(Integer)

    rasp7 = relationship("ScRasp7", back_populates="groups")
    group = relationship("ScGroup", back_populates="rasp7_groups")

    __table_args__ = (Index("ix_sc_rasp7_groups_group_sem", "group_id", "rasp7_id"),)


class ScRasp7Rooms(BaseWithId):
    __tablename__ = "sc_rasp7_rooms"
    rasp7_id = Column(
        Integer, ForeignKey("sc_rasp7.id", ondelete="CASCADE"), nullable=False
    )
    room = Column(String, nullable=False)

    rasp7 = relationship("ScRasp7", back_populates="rooms")

    __table_args__ = (Index("ix_sc_rasp7_rooms_room_rasp", "room", "rasp7_id"),)


class ScRasp7Preps(BaseWithId):
    __tablename__ = "sc_rasp7_preps"
    rasp7_id = Column(
        Integer, ForeignKey("sc_rasp7.id", ondelete="CASCADE"), nullable=False
    )
    prep_id = Column(
        Integer, ForeignKey("sc_prep.id", ondelete="CASCADE"), nullable=False
    )

    rasp7 = relationship("ScRasp7", back_populates="preps")
    prep = relationship("ScPrep", back_populates="rasp7_entries")

    __table_args__ = (Index("ix_sc_rasp7_preps_prep_rasp", "prep_id", "rasp7_id"),)


class ScRasp18(BaseWithId):
    __tablename__ = "sc_rasp18"
    semcode = Column(Integer, nullable=False, index=True)
    day_id = Column(
        Integer, ForeignKey("sc_rasp18_days.id", ondelete="CASCADE"), nullable=False
    )
    pair = Column(Integer, nullable=False)
    kind = Column(Integer, nullable=False)
    worktype = Column(Integer, nullable=False)
    disc_id = Column(
        Integer, ForeignKey("sc_disc.id", ondelete="CASCADE"), nullable=False
    )
    timestart = Column(Text, nullable=False)
    timeend = Column(Text, nullable=False)

    day = relationship("ScRasp18Days", backref="lessons")
    discipline = relationship("ScDisc", back_populates="rasp18_entries")
    groups = relationship(
        "ScRasp18Groups", back_populates="rasp18", cascade="all, delete"
    )
    rooms = relationship(
        "ScRasp18Rooms", back_populates="rasp18", cascade="all, delete"
    )
    preps = relationship(
        "ScRasp18Preps", back_populates="rasp18", cascade="all, delete"
    )
    moves = relationship("ScRasp18Move", back_populates="rasp18", cascade="all, delete")
    info = relationship("ScRasp18Info", back_populates="rasp18", cascade="all, delete")


class ScRasp18Groups(BaseWithId):
    __tablename__ = "sc_rasp18_groups"
    rasp18_id = Column(
        Integer, ForeignKey("sc_rasp18.id", ondelete="CASCADE"), nullable=False
    )
    group_id = Column(
        Integer, ForeignKey("sc_group.id", ondelete="CASCADE"), nullable=False
    )
    subgroup = Column(Integer)

    rasp18 = relationship("ScRasp18", back_populates="groups")
    group = relationship("ScGroup", back_populates="rasp18_groups")

    __table_args__ = (Index("ix_sc_rasp18_groups_group_rasp", "group_id", "rasp18_id"),)


class ScRasp18Rooms(BaseWithId):
    __tablename__ = "sc_rasp18_rooms"
    rasp18_id = Column(
        Integer, ForeignKey("sc_rasp18.id", ondelete="CASCADE"), nullable=False
    )
    room = Column(String, nullable=False)

    rasp18 = relationship("ScRasp18", back_populates="rooms")

    __table_args__ = (Index("ix_sc_rasp18_rooms_room_rasp", "room", "rasp18_id"),)


class ScRasp18Preps(BaseWithId):
    __tablename__ = "sc_rasp18_preps"
    rasp18_id = Column(
        Integer, ForeignKey("sc_rasp18.id", ondelete="CASCADE"), nullable=False
    )
    prep_id = Column(
        Integer, ForeignKey("sc_prep.id", ondelete="CASCADE"), nullable=False
    )

    rasp18 = relationship("ScRasp18", back_populates="preps")
    prep = relationship("ScPrep", back_populates="rasp18_entries")

    __table_args__ = (Index("ix_sc_rasp18_preps_prep_rasp", "prep_id", "rasp18_id"),)


class ScRasp18Move(BaseWithId):
    __tablename__ = "sc_rasp18_move"
    rasp18_dest_id = Column(
        Integer, ForeignKey("sc_rasp18.id", ondelete="CASCADE"), nullable=False
    )
    src_day_id = Column(Integer, nullable=False)
    src_pair = Column(Integer, nullable=False)
    reason = Column(Text)
    comment = Column(Text)

    rasp18 = relationship("ScRasp18", back_populates="moves")


class ScRasp18Info(BaseWithId):
    __tablename__ = "sc_rasp18_info"
    rasp18_id = Column(
        Integer, ForeignKey("sc_rasp18.id", ondelete="CASCADE"), nullable=False
    )
    kind = Column(Integer, nullable=False)
    info = Column(Text, nullable=False)

    rasp18 = relationship("ScRasp18", back_populates="info")


class ScRasp18Days(BaseWithId):
    __tablename__ = "sc_rasp18_days"
    semcode = Column(Integer, nullable=False, index=True)
    day = Column(Date, nullable=False)
    weekday = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)

    __table_args__ = (Index("ix_sc_rasp18_days_semcode_day", "semcode", "day"),)
