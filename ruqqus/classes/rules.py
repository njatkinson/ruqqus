from .mix_ins import Stndrd, Age_times
import time
from sqlalchemy import Column, BigInteger, Integer, ForeignKey, String
from ruqqus.application import Base


class Rules(Base, Stndrd, Age_times):

    __tablename__="rules"
    id = Column(BigInteger, primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.id"))
    rule_body = Column(String(256))
    rule_html = Column(String)
    created_utc = Column(BigInteger, default=0)
    edited_utc = Column(BigInteger, default=0)

    def __init__(self, *args, **kwargs):
        if "created_utc" not in kwargs:
            kwargs["created_utc"] = int(time.time())
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<Rule(id={self.id}, board_id={self.board_id})>"