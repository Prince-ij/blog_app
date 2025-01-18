from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, Register, LoginForm, CommentForm


app = Flask(__name__)
base_url = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
login_manager = LoginManager()
Bootstrap(app)

login_manager.init_app(app)


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('postgresql://my_first_db_zoii_user:fy6cWNOWXjwOMaAYWMRtNNZ6fCp6JzEP@dpg-cu5s2aogph6c73c0pao0-a.oregon-postgres.render.com/my_first_db_zoii')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


def gravatar_url(email, size=100):
    email = email.strip().lower()
    hash_email = hashlib.md5(email.encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash_email}?s={size}"


@app.context_processor
def utility_processor():
    return dict(gravatar_url=gravatar_url)


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    posts = db.relationship('BlogPost', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)

    def __repr__(self):
        return f'<User {self.id}: {self.name}>'


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = db.relationship('Comment', backref='blog_post', lazy=True)

    def __repr__(self):
        return f'<BlogPost {self.id}: {self.title}>'


class Comment(UserMixin, db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    blog_post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} by User {self.author_id}>'




with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = Register()

    if form.validate_on_submit():
        password = form.password.data
        password_hash = generate_password_hash(password=password, method='pbkdf2:sha256', salt_length=8)
        if db.session.query(User).filter_by(email=request.form['email']).first():
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('login'))
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=password_hash
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("register.html", form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            flash('Email not found, try another one', 'error')
            return redirect(url_for('login'))
        password = form.password.data
        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        else:
            flash('Incorrect password', 'error')
            return redirect(url_for('login'))
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form=CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = db.session.query(Comment).filter_by(blog_post_id=requested_post.id).all()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        new_comment = Comment(
            text=form.comment.data,
            author_id=current_user.id,
            blog_post_id=requested_post.id
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))

    return render_template("post.html", post=requested_post, form=form, comments=comments)




@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=['GET', 'POST'])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
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
@login_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
