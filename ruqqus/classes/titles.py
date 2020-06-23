from sqlalchemy import Column, Integer, Boolean, String
from ruqqus.application import Base

class Title(Base):

    __tablename__="titles"
    id=Column(Integer, primary_key=True)
    is_before=Column(Boolean, default=True)
    text=Column(String(64))
    qualification_expr = Column(String(256))
    requirement_string = Column(String(512))
    color=Column(String(6), default="888888")
    kind=Column(Integer, default=1)


    def check_eligibility(self, v):

        return bool(eval(self.qualification_expr, {}, {"v":v}))

    @property
    def json(self):

        return {'id': self.id,
                'text':self.text,
                'color':f'#{self.color}',
                'kind':self.kind
                }
