from os import environ
from ruqqus.classes.user import User
from .get import get_mod
from ruqqus.application import app



@app.template_filter("total_users")
def total_users(x):
    # TODO: Reference to db is bad. Does this need to be fixed or can this code go away?
    return db.query(User).filter_by(is_banned=0).count()


@app.template_filter("source_code")
def source_code(file_name):

    return open("/app/"+file_name, mode="r+").read()

@app.template_filter("full_link")
def full_link(url):

    return f"https://{app.config['SERVER_NAME']}{url}"

@app.template_filter("env")
def env_var_filter(x):

    x=environ.get(x, 1)

    try:
        return int(x)
    except:
        try:
            return float(x)
        except:
            return x
        
@app.template_filter("js_str_escape")
def js_str_escape(s):
    
    s=s.replace("'", r"\'")

    return s

@app.template_filter("is_mod")
def jinja_is_mod(uid, bid):

    return bool(get_mod(uid, bid))
