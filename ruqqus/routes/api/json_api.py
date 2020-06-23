from flask import jsonify, abort
from ruqqus.helpers.wrappers import auth_desired
from ruqqus.helpers.get import get_guild, get_user, get_post, get_comment
from ruqqus.application import app



@app.route("/api/v1/guild/<boardname>", methods=["GET"])
def guild_info(boardname):
    guild = get_guild(boardname)

    return jsonify(guild.json)


@app.route("/api/v1/user/<username>", methods=["GET"])
def user_info(username):

    user=get_user(username)
    return jsonify(user.json)

@app.route("/api/v1/post/<pid>", methods=["GET"])
@auth_desired
def post_info(v, pid):

    post=get_post(pid)

    if not post.is_public and post.board.is_private and not post.board.can_view(v):
        abort(403)
        
    return jsonify(post.json)

@app.route("/api/v1/comment/<cid>", methods=["GET"])
@auth_desired
def comment_info(v, cid):

    comment=get_comment(cid)

    post=comment.post
    if not post.is_public and post.board.is_private and not post.board.can_view(v):
        abort(403)
        
    return jsonify(comment.json)
