from flask import Flask,request,render_template,flash,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user,LoginManager,UserMixin
from datetime import datetime


import os
import secrets
from PIL import Image

app = Flask(__name__)

db = SQLAlchemy()

app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

db = SQLAlchemy(app)


UPLOAD_FOLDER = './static/post_pics'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/post_pics', picture_fn)

    output_size = (300,300)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i = i.resize((150, 150), Image.ANTIALIAS)
    i.save(picture_path)

    return picture_fn

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(), unique=True,nullable = False)
    password = db.Column(db.String(),nullable = False)
    username = db.Column(db.String(),nullable = False)
    name = db.Column(db.String(1000),nullable = False)
    followed = db.relationship('User', 
                               secondary=followers, 
                               primaryjoin=(followers.c.follower_id == id), 
                               secondaryjoin=(followers.c.followed_id == id), 
                               backref=db.backref('followers', lazy='dynamic'), 
                               lazy='dynamic')

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
            return self

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
            return self

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

class Posts(db.Model):
    post_id = db.Column(db.Integer, autoincrement=True, primary_key = True)
    id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    title = db.Column(db.String(20), nullable = False)
    username = db.Column(db.String(20), nullable = False)
    caption = db.Column(db.String(200), nullable = False)
    image = db.Column(db.String(), nullable = False, default = 'default.jpg')
    date_posted = db.Column(db.DateTime, nullable = False, default = datetime.utcnow)


@app.route('/')
@login_required
def index():
    result = db.session.query(followers).filter_by(follower_id = current_user.id).all()
    followers_u = []
    for f in result:
        followers_u.append(f[1])
    resa = []
    print(followers_u)
    result = Posts.query.filter(Posts.id.in_(followers_u)).all()

    result.reverse()
    print(result)
   
    if len(resa) == 0:
            resa = 0
    
    return render_template('index.html',user=current_user,Post = result)

@app.route('/profile')
@login_required
def profile():
    nposts = Posts.query.filter_by(id = current_user.id).count()
    nfollowed = db.session.query(followers).filter_by(follower_id = current_user.id).count()
    nfollowers = db.session.query(followers).filter_by(followed_id = current_user.id).count()
    posts = Posts.query.filter_by(id = current_user.id).all()
    return render_template('profile.html',id=current_user.id,name=current_user.name,user = current_user,nposts=nposts,nfollowed=nfollowed,nfollowers=nfollowers,Post=posts)

@app.route('/signup')
def signup():
    return render_template('signup.html',user=None)

@app.route('/signup', methods=['POST'])
def signup_post():
   
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    username = request.form.get('username')

    user = User.query.filter_by(email=email).first()
   
    if user:
        flash('Email address already exists')
        return redirect(url_for('signup'))
    

    new_user = User(email=email, name=name,username=username, password=generate_password_hash(password, method='sha256'))
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html',user=None)

@app.route('/login', methods=['POST'])
def login_post():
   
   
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()


    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('login'))

    login_user(user, remember=remember)

    
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/createPost',methods=['GET','POST'])
@login_required
def cPost():
    if request.method == 'GET':
        
        return render_template("createPost.html",user=current_user)
    else:
        title = request.form.get('title') 
        caption = request.form.get('caption')
        file = request.files['file']
        username = current_user.username
    if file:
            picture_file = save_picture(file)
            post = Posts(id = current_user.id,title = title,caption = caption, image = picture_file,username = username)
            db.session.add(post)
            db.session.commit()
    
    return redirect('/')

@app.route('/search',methods=['GET','POST'])
def search():
    if request.method == 'GET':
        q = request.args.get('q')
        f =  db.session.query(followers).filter_by(follower_id = current_user.id).all()
        x = []
        for i in f:
            x.append(i[1])
        if q == None:
            return render_template('search.html',user=current_user)
            
        if q:
            users = User.query.filter(User.name.startswith(q)) 
            
                

        return render_template('search.html',Users = users, x = x,user=current_user)
    else:
        return redirect('/login')


@app.route('/particulars',methods=['GET','POST'])
def particulars():
    if request.method == 'GET':
        return render_template('particular.html')


@app.route("/user/<int:user_id>")
def particular(user_id):
    if request.method == 'GET':
        nposts = Posts.query.filter_by(id = user_id).count()
        nfollowed = db.session.query(followers).filter_by(follower_id = user_id).count()
        nfollowers = db.session.query(followers).filter_by(followed_id = user_id).count()
        posts = Posts.query.filter_by(id = user_id).all()
        if len(posts) == 0:
            posts = 0
        return render_template('particular.html',nposts=nposts,nfollowed=nfollowed,nfollowers=nfollowers,Post=posts,user=current_user,user_id=user_id)

@app.route("/follow/<int:user_id>")
@login_required
def follow(user_id):
    g  = User.query.filter_by(id = current_user.id).first()
    user = User.query.filter_by(id = user_id).first()

    u = g.follow(user)
  
    db.session.add(u)
    db.session.commit()
    
    return redirect(url_for('search'))

@app.route('/unfollow/<int:user_id>')
@login_required
def unfollow(user_id):
    print(user_id)
    g  = User.query.filter_by(id = current_user.id).first()
    user = User.query.filter_by(id = user_id).first()
   
    u = g.unfollow(user)
    db.session.add(u)
    db.session.commit()
    return redirect(url_for('search'))

@app.route("/follower")
@app.route("/follower/<int:user_id>")
def follower(user_id=None):
    if user_id:
        f =  db.session.query(followers).filter_by(followed_id = user_id).all()
        x = []
        for i in f:
            x.append(i[0])
        
        a = []
        for k in x:
            z =  db.session.query(User).filter_by(id = k).first()
            a.append(z)
        
        l =  db.session.query(followers).filter_by(follower_id = current_user.id).all()
        m = []
        for i in l:
            m.append(i[1])

        return render_template('follower.html',a = a,user=current_user,user_id=user_id,m=m)

@app.route("/followed/<int:user_id>")
def followed(user_id=None):
    if user_id:
        f =  db.session.query(followers).filter_by(follower_id = user_id).all()
        x = []
        for i in f:
            x.append(i[1])
        
        a = []
        for k in x:
            z =  db.session.query(User).filter_by(id = k).first()
            a.append(z)
        
        l =  db.session.query(followers).filter_by(follower_id = current_user.id).all()
        m = []
        for i in l:
            m.append(i[1])

        return render_template('followed.html',a = a,user=current_user,user_id=user_id,m=m)




@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    posts = Posts.query.filter_by(id=user_id).all()
    x = db.session.query(followers).filter_by(follower_id = current_user.id).all()
    db.session.delete(user)
    for post in posts:
        db.session.delete(post)
    db.session.commit()
    
    return redirect(url_for('login'))

@app.route("/update_user",methods=['GET','POST'])
def update_user():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        username = request.form.get('username')
        if email=='':
            email = current_user.email
        if name=='':
            name = current_user.name
        if username=='':
            username = current_user.username       
        
        user = User.query.filter_by(id = current_user.id).first()
        user.email = email
        user.name = name
        user.username = username
        db.session.commit()
            
        return redirect(url_for('login'))
    else:
        return render_template('update.html',user=current_user)
@app.route('/update_post/<int:post_id>',methods=['GET','POST'])
def update_post(post_id):
    post_u = Posts.query.filter_by(post_id = post_id ).first()
    if request.method == 'POST':
        title = request.form.get('title')
        caption = request.form.get('caption')
        if title=='':
            title = post_u.title 
        if caption=='':
            caption = post_u.caption
        
        post_u = Posts.query.filter_by(post_id = post_id ).first()
        post_u.title = title
        post_u.caption = caption
        db.session.commit()

        return redirect(url_for('profile'))
    else:
        return render_template('update_post.html',user=current_user,post=post_u)

@app.route("/delete_post/<int:post_id>")
def delete_post(post_id):
    post = Posts.query.filter_by(post_id = post_id).first()
    db.session.delete(post)
    db.session.commit()
    
    return redirect(url_for('profile'))
if __name__ == "__main__":
    # run the flask app
    app.run(host='0.0.0.0', debug=True, port=5000)

