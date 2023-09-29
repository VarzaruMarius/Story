from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from form import CreatePGameForm, CreateUser, Login, Comments
from functools import wraps
from sqlalchemy import ForeignKey

# from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///game.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# CONFIGURE TABLES


class Comment(db.Model, UserMixin):
    __tablename__ = 'commnets'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(
        db.Integer, ForeignKey('user.id'))
    author = relationship("User", back_populates="comments")
    post_id = db.Column(
        db.Integer, ForeignKey('game_posts.id'))
    post = relationship("GamePost", back_populates="comments")


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    name = db.Column(db.String(250), nullable=False)
    posts = relationship("GamePost", back_populates="author")
    comments = relationship("Comment", back_populates="author")


class GamePost(db.Model):
    __tablename__ = "game_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(
        db.Integer, ForeignKey('user.id'))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="post")


def is_admin():
    if current_user.is_authenticated:
        return current_user.id == 1
    return False


def admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return f(*args, **kwargs)
        return "no permision"

    return decorated_function


@app.route('/')
def get_all_posts():
    posts = GamePost.query.all()
    return render_template("index.html", all_posts=posts, is_login=current_user.is_authenticated, is_admin=is_admin())


@app.route('/register', methods=["POST", "GET"])
def register():
    form = CreateUser()
    if form.validate_on_submit():
        na = form.name.data
        pa = form.password.data
        em = form.email.data
        if db.session.execute(db.select(User).where(User.email == em)).scalar():
            flash("You've already signed up with that email, log in instead!")
            return render_template("login.html", form=Login())

        pas = generate_password_hash(
            password=pa, method='pbkdf2:sha256', salt_length=8)
        u = User(email=em, password=pas, name=na)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = Login()
    if form.validate_on_submit():

        em = form.email.data
        pa = form.password.data
        with app.app_context():
            acount = db.session.execute(
                db.select(User).where(User.email == em)).scalar()
        if acount == None:
            flash("Acount not found")
            return render_template("login.html", form=form, is_login=current_user.is_authenticated)
        else:
            if check_password_hash(acount.password, pa):
                login_user(acount)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Incorect password")
                return render_template("login.html", form=form, is_login=current_user.is_authenticated)
    return render_template("login.html", form=form, is_login=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = GamePost.query.get(post_id)
    try:
        commentss = Comment.query.filter_by(post_id=post_id).all()
    except:
        commentss = None
    form = Comments()
    if form.validate_on_submit():
        coms = Comment(text=form.comment.data,
                       author_id=current_user.id, post_id=post_id)
        db.session.add(coms)
        db.session.commit()
        return redirect(url_for("show_post", post_id=post_id))

    return render_template("post.html", post=requested_post, is_admin=is_admin(), form=form, is_login=current_user.is_authenticated, com=commentss)


@app.route("/new-post",  methods=["POST", "GET"])
@admin
def add_new_post():
    form = CreatePGameForm()
    if form.validate_on_submit():
        new_post = GamePost(
            author_id=current_user.id,

            title=form.title.data,
            body=form.body.data,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin
def edit_post(post_id):
    post = GamePost.query.get(post_id)
    edit_form = CreatePGameForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin
def delete_post(post_id):
    post_to_delete = GamePost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


with app.app_context():
    db.create_all()
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
