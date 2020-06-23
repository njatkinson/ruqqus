from flask import *
from sqlalchemy import *
from sqlalchemy.orm import relationship, deferred
from sqlalchemy.ext.associationproxy import association_proxy
from .mix_ins import *
from ruqqus.helpers.base36 import base36decode
from ruqqus.helpers.lazy import lazy
from ruqqus.__main__ import Base
from .votes import CommentVote
from .badwords import BadWord


class Comment(Base, Age_times, Scores, Stndrd, Fuzzing):

    __tablename__="comments"

    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("users.id"))
    body = Column(String(10000), default=None)
    parent_submission = Column(Integer, ForeignKey("submissions.id"))
    parent_fullname = Column(Integer) #this column is foreignkeyed to comment(id) but we can't do that yet as "comment" class isn't yet defined
    created_utc = Column(Integer, default=0)
    edited_utc = Column(Integer, default=0)
    is_banned = Column(Boolean, default=False)
    body_html = Column(String(20000))
    distinguish_level=Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    is_approved = Column(Integer, default=0)
    approved_utc=Column(Integer, default=0)
    ban_reason=Column(String(256), default='')
    creation_ip=Column(String(64), default='')
    score_disputed=Column(Float, default=0)
    score_hot=Column(Float, default=0)
    score_top=Column(Integer, default=1)
    level=Column(Integer, default=0)
    parent_comment_id=Column(Integer, ForeignKey("comments.id"))
    author_name=Column(String(64), default="")

    over_18=Column(Boolean, default=False)
    is_op=Column(Boolean, default=False)
    is_offensive=Column(Boolean, default=False)
    is_nsfl=Column(Boolean, default=False)

    post=relationship("Submission", lazy="joined")
    flags=relationship("CommentFlag", lazy="joined", backref="comment")
    author=relationship("User", lazy="joined", innerjoin=True, primaryjoin="User.id==Comment.author_id")
    board=association_proxy("post", "board")

    #These are virtual properties handled as postgres functions server-side
    #There is no difference to SQLAlchemy, but they cannot be written to
    ups = deferred(Column(Integer, server_default=FetchedValue()))
    downs=deferred(Column(Integer, server_default=FetchedValue()))
    is_public=Column(Boolean, server_default=FetchedValue())

    score=deferred(Column(Integer, server_default=FetchedValue()))
    

    rank_fiery=deferred(Column(Float, server_default=FetchedValue()))
    rank_hot=deferred(Column(Float, server_default=FetchedValue()))

    flag_count=deferred(Column(Integer, server_default=FetchedValue()))

    board_id=Column(Integer, server_default=FetchedValue())
    
    

    def __init__(self, *args, **kwargs):
                   

        if "created_utc" not in kwargs:
            kwargs["created_utc"]=int(time.time())

        kwargs["creation_ip"]=request.remote_addr
            
        super().__init__(*args, **kwargs)
                
    def __repr__(self):

        return f"<Comment(id={self.id})>"

    @property
    @lazy
    def fullname(self):
        return f"t3_{self.base36id}"

    @property
    @lazy
    def is_top_level(self):
        return self.parent_fullname and self.parent_fullname.startswith("t2_")

    @property
    def is_archived(self):
        return self.post.is_archived
    
    @property
    @lazy
    def parent(self):

        if not self.parent_submission:
            return None

        if self.is_top_level:
            return self.post

        else:
            return self.__dict__.get("parent",
                                     g.db.query(Comment).filter_by(id=base36decode(self.parent_fullname.split(sep="_")[1])).first()
                                     )

    @property
    def children(self):

        return g.db.query(Comment).filter_by(parent_comment=self.id).all()

    @property
    def replies(self):

        return self.__dict__.get("replies", g.db.query(Comment).filter_by(parent_fullname=self.fullname).all())

    @property
    @lazy
    def permalink(self):

        return f"{self.post.permalink}/{self.base36id}"

    @property
    def any_descendants_live(self):

        if self.replies==[]:
            return False

        if any([not x.is_banned and not x.is_deleted for x in self.replies]):
            return True

        else:
            return any([x.any_descendants_live for x in self.replies])
        

    def rendered_comment(self, v=None, render_replies=True, standalone=False, level=1, **kwargs):

        kwargs["post_base36id"]=kwargs.get("post_base36id", self.post.base36id if self.post else None)

        if self.is_banned or self.is_deleted:
            if v and v.admin_level>1:
                return render_template("single_comment.html",
                                       v=v,
                                       c=self,
                                       render_replies=render_replies,
                                       standalone=standalone,
                                       level=level,
                                       **kwargs)
                
            elif self.any_descendants_live:
                return render_template("single_comment_removed.html",
                                       c=self,
                                       render_replies=render_replies,
                                       standalone=standalone,
                                       level=level,
                                       **kwargs)
            else:
                return ""

        
        return render_template("single_comment.html",
                               v=v,
                               c=self,
                               render_replies=render_replies,
                               standalone=standalone,
                               level=level,
                               **kwargs)

    @property
    def active_flags(self):
        if self.is_approved:
            return 0
        else:
            return self.flag_count

    def visibility_reason(self, v):
        if self.author_id==v.id:
            return "this is your content."
        elif self.board.has_mod(v):
            return f"you are a guildmaster of +{self.board.name}."
        elif self.board.has_contributor(v):
            return f"you are an approved contributor in +{self.board.name}."
        elif self.parent.author_id==v.id:
            return "this is a reply to your content."
        elif v.admin_level >= 4:
            return "you are a Ruqqus admin."


    def determine_offensive(self):

        for x in g.db.query(BadWord).all():
            if x.check(self.body):
                self.is_offensive=True
                
                break
        else:
            self.is_offensive=False
            

    @property
    def json(self):
        if self.is_banned:
            return {'is_banned':True,
                    'ban_reason':self.ban_reason,
                    'id':self.base36id,
                    'post':self.post.base36id,
                    'level':self.level,
                    'parent':self.parent_fullname
                    }
        elif self.is_deleted:
            return {'is_deleted':True,
                    'id':self.base36id,
                    'post':self.post.base36id,
                    'level':self.level,
                    'parent':self.parent_fullname
                    }
        return {'id':self.base36id,
                'post':self.post.base36id,
                'level':self.level,
                'parent':self.parent_fullname,
                'author':self.author_name if not self.author.is_deleted else None,
                'body':self.body,
                'body_html':self.body_html,
            #   'replies': [x.json for x in self.replies]
                'is_archived':self.is_archived,
                'title': self.title.json if self.title else None
                }
            
    @property
    def voted(self):
        
        x=self.__dict__.get("_voted")
        if x != None:
            return x

        if g.v:
            x=g.db.query(CommentVote).filter_by(
                comment_id=self.id,
                user_id=g.v.id
                ).first()

            if x:
                x=x.vote_type
            else:
                x=0
        else:
            x=0
        return x

    @property
    def title(self):
        return self.__dict__.get("_title", self.author.title)
    
        
class Notification(Base):

    __tablename__="notifications"

    id=Column(Integer, primary_key=True)
    user_id=Column(Integer, ForeignKey("users.id"))
    comment_id=Column(Integer, ForeignKey("comments.id"))
    read=Column(Boolean, default=False)

    comment=relationship("Comment", lazy="joined", innerjoin=True)

    #Server side computed values (copied from corresponding comment)
    created_utc=Column(Integer, server_default=FetchedValue())

    def __repr__(self):

        return f"<Notification(id={self.id})"

    @property
    def voted(self):
        return 0
    
