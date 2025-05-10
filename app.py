from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
import os
from werkzeug.utils import secure_filename
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import TypeDecorator, DateTime

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')

# Initialize database
db = SQLAlchemy(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Custom SQLAlchemy Type for UTC Timezone Handling
class TimezoneUTC(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("created_at must be timezone-aware")
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=timezone.utc)
        return value

# Import models - defined here to avoid circular imports
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")
    
    #relationship to implement followers
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"
        
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
            return self
    
    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
            return self
    
    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0
            
    def followed_posts(self):
        """Get posts from followed users and own posts"""
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)
        ).filter(followers.c.follower_id == self.id)
        
        own = Post.query.filter_by(user_id=self.id)
        
        # Combine and sort by newest first
        return followed.union(own).order_by(Post.created_at.desc())

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(TimezoneUTC, default=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # New field for reply relationships
    parent_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    
    # Relationship to track replies to this post
    replies = db.relationship('Post', 
                             backref=db.backref('parent', remote_side=[id]),
                             lazy='dynamic',
                             cascade="all, delete-orphan")

    # This property will be calculated dynamically and is not stored in the database
    remaining_time = None

    def __repr__(self):
        return f"Post('{self.content[:20]}...', '{self.created_at}')"

    @hybrid_property
    def created_at_utc(self):
        return self.created_at
        
    @property
    def is_reply(self):
        """Check if this post is a reply to another post"""
        return self.parent_id is not None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize scheduler for post deletion
scheduler = BackgroundScheduler()
scheduler.start()

def delete_expired_posts():
    """Delete posts that are older than 3 hours"""
    expiration_time = datetime.now(timezone.utc) - timedelta(hours=3)
    expired_posts = Post.query.filter(Post.created_at < expiration_time).all()
    for post in expired_posts:
        db.session.delete(post)
    db.session.commit()
    print(f"Deleted {len(expired_posts)} expired posts")

# Schedule the delete_expired_posts function to run every 10 minutes
scheduler.add_job(delete_expired_posts, 'interval', minutes=10)

# Routes
@app.route('/')
def index():
    """Homepage route"""
    if current_user.is_authenticated:
        return redirect(url_for('feed'))
    return render_template('index.html', now=datetime.now(timezone.utc))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('feed'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered')
            return redirect(url_for('register'))
        new_user = User(username=username, email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html', now=datetime.now(timezone.utc))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('feed'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('feed'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/post', methods=['POST'])
@login_required
def create_post():
    """Create a new post or reply"""
    content = request.form.get('content')
    parent_id = request.form.get('parent_id')  # Get parent_id if this is a reply
    
    if not content:
        flash('Post cannot be empty')
        return redirect(url_for('feed'))
        
    # Create new post with parent_id if it's a reply
    new_post = Post(
        content=content, 
        user_id=current_user.id,
        parent_id=parent_id if parent_id else None
    )
    
    db.session.add(new_post)
    db.session.commit()
    
    # Redirect to the appropriate page
    if parent_id:
        # If this was a reply, redirect back to the post with the reply visible
        return redirect(url_for('feed') + f'#post-{parent_id}')
    else:
        return redirect(url_for('feed'))
@app.route('/api/post/<int:post_id>/replies')
@login_required
def get_post_replies(post_id):
    """API endpoint to get replies for a post"""
    post = Post.query.get_or_404(post_id)
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=3)
    
    # Get all replies that haven't expired
    replies = Post.query.filter(
        Post.parent_id == post_id,
        Post.created_at > cutoff
    ).order_by(Post.created_at.asc()).all()
    
    # Calculate remaining time for each reply
    replies_data = []
    for reply in replies:
        expiration_time = reply.created_at + timedelta(hours=3)
        remaining_seconds = (expiration_time - now_utc).total_seconds()
        
        reply_data = {
            'id': reply.id,
            'content': reply.content,
            'author': {
                'username': reply.author.username,
                'profile_pic': reply.author.profile_pic
            },
            'created_at': reply.created_at.strftime('%H:%M'),
            'remaining_seconds': max(0, remaining_seconds)
        }
        replies_data.append(reply_data)
        
    return jsonify({'replies': replies_data})

@app.route('/profile/<username>')
@login_required
def profile(username):
    """User profile page"""
    user = User.query.filter_by(username=username).first_or_404()
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=3)
    posts = Post.query.filter(Post.user_id == user.id, Post.created_at > cutoff).order_by(Post.created_at.desc()).all()
    for post in posts:
        expiration_time = post.created_at + timedelta(hours=3)
        remaining_seconds = (expiration_time - now_utc).total_seconds()
        post.remaining_time = max(0, remaining_seconds)
    return render_template('profile.html', user=user, posts=posts)

@app.route('/edit_profile', methods=['POST'])
@login_required
def edit_profile():
    """Handle profile edit form submission"""
    bio = request.form.get('bio')
    profile_pic = request.files.get('profile_pic')
    user = User.query.get(current_user.id)

    if not user:
        flash('Error: User not found.', 'error')
        return redirect(url_for('profile', username=current_user.username))

    user.bio = bio

    if profile_pic:

        if allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            new_filename = f"{current_user.username}_profile.{file_extension}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

            try:
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                profile_pic.save(filepath)
                user.profile_pic = f'images/profile_pics/{new_filename}'
            except Exception as e:
                flash(f'Error saving profile picture: {e}', 'error')
                print(f"Error saving profile picture: {e}") # Log the exception
                return redirect(url_for('profile', username=current_user.username))
        else:
            flash('Invalid file type for profile picture. Allowed types are: png, jpg, jpeg, gif', 'warning')
            print('Error: Invalid file type.') # Log invalid type
    else:
        print("No profile picture was uploaded.") # Log if no file

    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile', username=current_user.username))

@app.route('/api/post/<int:post_id>/remaining')
def get_remaining_time(post_id):
    """API endpoint to get remaining time for a post"""
    post = Post.query.get_or_404(post_id)
    now_utc = datetime.now(timezone.utc)
    expiration_time = post.created_at + timedelta(hours=3)
    remaining_seconds = (expiration_time - now_utc).total_seconds()
    return jsonify({'remaining_seconds': max(0, remaining_seconds)})
@app.route('/follow/<username>')
@login_required
def follow(username):
    """Follow a user"""
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('profile', username=username))
    
    current_user.follow(user)
    db.session.commit()
    flash(f'You are now following {username}!')
    return redirect(url_for('profile', username=username))

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    """Unfollow a user"""
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('profile', username=username))
    
    current_user.unfollow(user)
    db.session.commit()
    flash(f'You have unfollowed {username}.')
    return redirect(url_for('profile', username=username))

@app.route('/search')
@login_required
def search():
    """Search for users and posts"""
    query = request.args.get('q', '')
    if not query:
        return render_template('search.html', query='', users=[], posts=[])
    
    # Search for users
    users = User.query.filter(User.username.ilike(f'%{query}%')).limit(10).all()
    
    # Search for posts
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=3)
    posts = Post.query.filter(
        Post.content.ilike(f'%{query}%'),
        Post.created_at > cutoff
    ).order_by(Post.created_at.desc()).limit(20).all()
    
    # Calculate remaining time for posts
    for post in posts:
        expiration_time = post.created_at + timedelta(hours=3)
        remaining_seconds = (expiration_time - now_utc).total_seconds()
        post.remaining_time = max(0, remaining_seconds)
    
    return render_template('search.html', query=query, users=users, posts=posts)

@app.route('/feed/followed')
@login_required
def followed_feed():
    """Show posts from followed users"""
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=3)
    
    # Get posts from followed users that haven't expired
    posts = current_user.followed_posts().filter(Post.created_at > cutoff).all()
    
    for post in posts:
        expiration_time = post.created_at + timedelta(hours=3)
        remaining_seconds = (expiration_time - now_utc).total_seconds()
        post.remaining_time = max(0, remaining_seconds)
    
    return render_template('feed.html', posts=posts, feed_type='followed')

@app.route('/feed')
@login_required
def feed():
    """Main feed of posts"""
    feed_type = request.args.get('type', 'all')  # 'all' or 'followed'
    
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=3)
    
    if feed_type == 'followed':
        posts = current_user.followed_posts().filter(Post.created_at > cutoff).all()
    else:
        posts = Post.query.filter(Post.created_at > cutoff).order_by(Post.created_at.desc()).all()
    
    for post in posts:
        expiration_time = post.created_at + timedelta(hours=3)
        remaining_seconds = (expiration_time - now_utc).total_seconds()
        post.remaining_time = max(0, remaining_seconds)
    
    return render_template('feed.html', posts=posts, feed_type=feed_type)

@app.route('/api/user/<int:user_id>/followers-count')
@login_required
def get_followers_count(user_id):
    """API endpoint to get number of followers"""
    user = User.query.get_or_404(user_id)
    followers_count = user.followers.count()
    following_count = user.followed.count()
    is_following = current_user.is_following(user) if current_user.is_authenticated else False
    
    return jsonify({
        'followers_count': followers_count,
        'following_count': following_count,
        'is_following': is_following
    })
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)