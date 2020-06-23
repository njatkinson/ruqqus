from ruqqus.application import make_session
from ruqqus import classes

import time

db=make_session()

def recompute():

    while True:

        db.begin()

        now=int(time.time())

        cutoff=now-(60860*24*180)

        print("Beginning post recompute")
        i=0
        for post in db.query(classes.submission.Submission
                       ).filter_by(is_banned=False, is_deleted=False
                                   ).filter(classes.submission.Submission.created_utc>cutoff
                                            ).order_by(classes.submission.Submission.id.desc()
                                                       ).all():
            i+=1

            post.score_hot = post.rank_hot
            post.score_disputed=post.rank_fiery
            #post.score_top=post.score
            post.score_activity=post.rank_activity

            db.add(post)
            

            #print(f"{i}/{total} - {post.base36id}")

        print(f"Scored {i} posts. Beginning comment recompute")


        i=0
        p=db.query(classes.submission.Submission
                   ).filter(classes.submission.Submission.created_utc>cutoff
                            ).subquery()
        
        for comment in db.query(classes.comment.Comment
                             ).join(p,
                                    classes.comment.Comment.parent_submission==p.c.id
                                    ).filter(p.c.id != None,
                                             p.c.created_utc>cutoff,
                                             classes.comment.Comment.is_deleted==False,
                                             classes.comment.Comment.is_banned==False
                                             ).all():
            i+=1
            
            comment.score_disputed=comment.rank_fiery
            comment.score_hot=comment.rank_hot
            #comment.score_top=comment.score

            db.add(comment)
            
        db.commit()

        print(f"Scored {i} comments. Sleeping 1min")

        #time.sleep(60)


recompute()
