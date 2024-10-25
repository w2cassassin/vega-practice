import datetime

from sqlalchemy import BigInteger, Column, DateTime
from sqlalchemy.orm import as_declarative


@as_declarative()
class Base:
    __abstract__ = True
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.now,
    )
