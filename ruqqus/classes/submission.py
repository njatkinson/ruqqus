import time
import re
from urllib.parse import urlparse
from flask import render_template, request, abort, g
from sqlalchemy import Column, BigInteger, ForeignKey, String, Boolean, Integer, Float, FetchedValue
from sqlalchemy.orm import relationship, deferred
from ruqqus.application import Base
from ruqqus.helpers.lazy import lazy
from ruqqus.helpers.base36 import base36encode
from ruqqus.classes.flags import Report
from .flags import Flag
from .badwords import BadWord
from .mix_ins import Stndrd, Age_times, Scores, Fuzzing


class Submission(Base, Stndrd, Age_times, Scores, Fuzzing):
 
    __tablename__="submissions"

    id = Column(BigInteger, primary_key=True)
    author_id = Column(BigInteger, ForeignKey("users.id"))
    repost_id = Column(BigInteger, ForeignKey("submissions.id"), default=0)
    title = Column(String(500), default=None)
    url = Column(String(500), default=None)
    edited_utc = Column(BigInteger, default=0)
    created_utc = Column(BigInteger, default=0)
    is_banned = Column(Boolean, default=False)
    is_deleted=Column(Boolean, default=False)
    distinguish_level=Column(Integer, default=0)
    created_str=Column(String(255), default=None)
    stickied=Column(Boolean, default=False)
    _comments=relationship("Comment", lazy="dynamic", primaryjoin="Comment.parent_submission==Submission.id", backref="submissions")
    body=Column(String(10000), default="")
    body_html=Column(String(20000), default="")
    embed_url=Column(String(256), default="")
    domain_ref=Column(Integer, ForeignKey("domains.id"))
    domain_obj=relationship("Domain", lazy="joined", innerjoin=False)
    flags=relationship("Flag", lazy="dynamic", backref="submission")
    is_approved=Column(Integer, ForeignKey("users.id"), default=0)
    approved_utc=Column(Integer, default=0)
    board_id=Column(Integer, ForeignKey("boards.id"), default=None)
    original_board_id=Column(Integer, ForeignKey("boards.id"), default=None)
    over_18=Column(Boolean, default=False)
    original_board=relationship("Board", lazy="subquery", primaryjoin="Board.id==Submission.original_board_id")
    ban_reason=Column(String(128), default="")
    creation_ip=Column(String(64), default="")
    mod_approved=Column(Integer, default=None)
    accepted_utc=Column(Integer, default=0)
    is_image=Column(Boolean, default=False)
    has_thumb=Column(Boolean, default=False)
    post_public=Column(Boolean, default=True)
    score_hot=Column(Float, default=0)
    score_disputed=Column(Float, default=0)
    score_top=Column(Float, default=1)
    score_activity=Column(Float, default=0)
    author_name=Column(String(64), default="")
    guild_name=Column(String(64), default="")
    is_offensive=Column(Boolean, default=False)
    is_nsfl=Column(Boolean, default=False)
    board=relationship("Board", lazy="joined", innerjoin=True, primaryjoin="Submission.board_id==Board.id")
    author=relationship("User", lazy="joined", innerjoin=True, primaryjoin="Submission.author_id==User.id")
    is_pinned=Column(Boolean, default=False)

    approved_by=relationship("User", uselist=False, primaryjoin="Submission.is_approved==User.id")

    # not sure if we need this
    reposts = relationship("Submission", lazy="joined", remote_side=[id])


    #These are virtual properties handled as postgres functions server-side
    #There is no difference to SQLAlchemy, but they cannot be written to

    ups = deferred(Column(Integer, server_default=FetchedValue()))
    downs=deferred(Column(Integer, server_default=FetchedValue()))
    age=deferred(Column(Integer, server_default=FetchedValue()))
    comment_count=Column(Integer, server_default=FetchedValue())
    flag_count=deferred(Column(Integer, server_default=FetchedValue()))
    report_count=deferred(Column(Integer, server_default=FetchedValue()))
    score=Column(Float, server_default=FetchedValue())
    is_public=Column(Boolean, server_default=FetchedValue())

    rank_hot=deferred(Column(Float, server_default=FetchedValue()))
    rank_fiery=deferred(Column(Float, server_default=FetchedValue()))
    rank_activity=deferred(Column(Float, server_default=FetchedValue()))    

    def __init__(self, *args, **kwargs):

        if "created_utc" not in kwargs:
            kwargs["created_utc"]=int(time.time())
            kwargs["created_str"]=time.strftime("%I:%M %p on %d %b %Y", time.gmtime(kwargs["created_utc"]))

        kwargs["creation_ip"]=request.remote_addr

        super().__init__(*args, **kwargs)
        
    def __repr__(self):
        return f"<Submission(id={self.id})>"

    @property
    @lazy
    def board_base36id(self):
        return base36encode(self.board_id)

    @property
    def is_repost(self):
        return bool(self.repost_id)

    @property
    def is_archived(self):
        return int(time.time()) - self.created_utc > 60*60*24*180

    @property
    @lazy
    def fullname(self):
        return f"t2_{self.base36id}"

    @property
    @lazy
    def permalink(self):

        output=self.title.lower()

        output=re.sub('&\w{2,3};', '', output)

        output=[re.sub('\W', '', word) for word in output.split()[0:6]]

        output='-'.join(output)

        if not output:
            output='-'


        return f"/post/{self.base36id}/{output}"

    @property
    def is_archived(self):

        now=int(time.time())

        cutoff=now-(60*60*24*180)

        return self.created_utc < cutoff
                                      
    def rendered_page(self, comment=None, comment_info=None, v=None):

        #check for banned
        if self.is_deleted:
            template="submission_deleted.html"
        elif v and v.admin_level>=3:
            template="submission.html"
        elif self.is_banned:
            template="submission_banned.html"
        else:
            template="submission.html"

        private=not self.is_public and not self.board.can_view(v)

        if private and not self.author_id==v.id:
            abort(403)
        elif private:
            self.__dict__["replies"]=[]
        else:
            #load and tree comments
            #calling this function with a comment object will do a comment permalink thing
            self.tree_comments(comment=comment)

        
        #return template
        is_allowed_to_comment = self.board.can_comment(v) and not self.is_archived

        return render_template(template,
                               v=v,
                               p=self,
                               sort_method=request.args.get("sort","Hot").capitalize(),
                               linked_comment=comment,
                               comment_info=comment_info,
                               is_allowed_to_comment=is_allowed_to_comment,
                               render_replies=True
                               )


    @property
    @lazy
    def domain(self):

        if not self.url:
            return "text post"
        domain= urlparse(self.url).netloc
        if domain.startswith("www."):
            domain=domain.split("www.")[1]
        return domain



    def tree_comments(self, comment=None, v=None):

                
        
        comments=self._preloaded_comments

        index={}
        for c in comments:
            if c.parent_fullname in index:
                index[c.parent_fullname].append(c)
            else:
                index[c.parent_fullname]=[c]

        for c in comments:
            c.__dict__["replies"]=index.get(c.fullname, [])

        if comment:
            self.__dict__["replies"]=[comment]
        else:
            self.__dict__["replies"]=index.get(self.fullname, [])
        


    @property
    def active_flags(self):
        if self.is_approved:
            return 0
        else:
            return self.flags.filter(Flag.created_utc>self.approved_utc).count()

    @property
    def active_reports(self):
        if self.mod_approved:
            return 0
        else:
            return self.reports.filter(Report.created_utc>self.accepted_utc).count()


    @property
    #@lazy
    def thumb_url(self):
    
        if self.has_thumb:
            return f"https://i.ruqqus.com/posts/{self.base36id}/thumb.png"
        elif self.is_image:
            return self.url
        else:
            return None

    def visibility_reason(self, v):

        if self.author_id==v.id:
            return "this is your content."
        elif self.board.has_mod(v):
            return f"you are a guildmaster of +{self.board.name}."
        elif self.board.has_contributor(v):
            return f"you are an approved contributor in +{self.board.name}."
        elif v.admin_level >= 4:
            return "you are a Ruqqus admin."


    def determine_offensive(self):

        for x in g.db.query(BadWord).all():
            if (self.body and x.check(self.body)) or x.check(self.title):
                self.is_offensive=True
                break
        else:
            self.is_offensive=False


    @property
    def json(self):

        if self.is_banned:
            return {'is_banned':True,
                    'is_deleted':self.is_deleted,
                    'ban_reason': self.ban_reason,
                    'id':self.base36id,
                    'title':self.title,
                    'permalink':self.permalink,
                    'guild_name':self.guild_name
                    }
        elif self.is_deleted:
            return {'is_banned':bool(self.is_banned),
                    'is_deleted':True,
                    'id':self.base36id,
                    'title':self.title,
                    'permalink':self.permalink,
                    'guild_name':self.guild_name
                    }
        data= {'author':self.author_name if not self.author.is_deleted else None,
                'permalink':self.permalink,
                'is_banned':False,
                'is_deleted':False,
                'created_utc':self.created_utc,
                'id':self.base36id,
                'title':self.title,
                'is_nsfw':self.over_18,
                'is_offensive':self.is_offensive,
                'is_nsfl':self.is_nsfl,
                'thumb_url':self.thumb_url,
                'domain':self.domain,
                'is_archived':self.is_archived,
                'url':self.url,
                'body':self.body,
                'body_html':self.body_html,
                'created_utc':self.created_utc,
                'edited_utc':self.edited_utc,
                'guild_name':self.guild_name,
                'embed_url':self.embed_url,
                'is_archived':self.is_archived,
                'author_title':self.author.title.json if self.author.title else None
                }

        if "_voted" in self.__dict__:
            data["voted"]=self._voted

        return data

    @property
    def voted(self):
        return self._voted if "_voted" in self.__dict__ else 0

    @property
    def user_title(self):
        return self._title if "_title" in self.__dict__ else self.author.title
    