from sqlalchemy import *
from ruqqus.__main__ import Base

class Domain(Base):

    __tablename__="domains"
    id=Column(Integer, primary_key=True)
    domain=Column(String)
    can_submit=Column(Boolean, default=False)
    can_comment=Column(Boolean, default=False)
    reason=Column(String)
    show_thumbnail=Column(Boolean, default=False)
    embed_function=Column(String(64), default=None)
    
