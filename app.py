# app.py (بخش‌های تغییر یافته و جدید)

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload
import os
# --- NEW IMPORTS ---
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required 
# -------------------

# --- ۱. پیکربندی و راه‌اندازی ---
app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_super_secret_key' 

db = SQLAlchemy(app)

# --- NEW: Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # تعیین نام تابع View برای صفحه ورود
login_manager.login_message = "لطفاً برای دسترسی به این صفحه وارد شوید." # پیام پیش‌فرض


# -------------------- Google OAuth --------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


# --- ۲. تعریف مدل‌های داده (UserMixin اضافه شد) ---

class Role(db.Model):
    # ... (بدون تغییر) ...
    __tablename__ = 'Role'
    RoleId = db.Column(db.Integer, primary_key=True)
    Rolename = db.Column(db.String(50), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy=True) 

class City(db.Model):
    # ... (بدون تغییر) ...
    __tablename__ = 'City'
    Zipcode = db.Column(db.String(10), primary_key=True)
    City = db.Column(db.String(100), nullable=False)
    users = db.relationship('User', backref='city', lazy=True)

# UserMixin برای سازگاری با Flask-Login اضافه شد
class User(db.Model, UserMixin): 
    __tablename__ = 'User'
    UserId = db.Column(db.Integer, primary_key=True) 
    Email = db.Column(db.String(120), unique=True, nullable=False)
    Firstname = db.Column(db.String(80), nullable=False)
    Lastname = db.Column(db.String(80), nullable=False)
    Address = db.Column(db.String(200), nullable=True)
    Zipcode = db.Column(db.String(10), db.ForeignKey('City.Zipcode'), nullable=False) 
    Role = db.Column(db.Integer, db.ForeignKey('Role.RoleId'), nullable=False) 
    Password = db.Column(db.String(128), nullable=False) 

    def set_password(self, password):
        self.Password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.Password, password)
    
    # NEW: متد مورد نیاز Flask-Login برای بازیابی کلید اصلی
    def get_id(self):
        return str(self.UserId) 

    def __repr__(self):
        return f'<User {self.Firstname} {self.Lastname}>'


# --- NEW: User Loader برای Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    # Flask-Login از این تابع برای بازیابی کاربر از دیتابیس بر اساس ID ذخیره شده در کوکی استفاده می‌کند.
    return User.query.get(int(user_id))
# ----------------------------------------


# --- ۳. دستور CLI برای ساخت دیتابیس و پر کردن داده‌های اولیه (بدون تغییر) ---
@app.cli.command("create-db")
def create_db():
    # ... (بدون تغییر) ...
    db.drop_all()
    db.create_all()
    
    if not Role.query.first():
        admin_role = Role(RoleId=1, Rolename='Admin')
        user_role = Role(RoleId=2, Rolename='User')
        db.session.add_all([admin_role, user_role])
        
    if not City.query.first():
        tehran = City(Zipcode='13185', City='تهران')
        mashhad = City(Zipcode='91735', City='مشهد')
        esfahan = City(Zipcode='81667', City='اصفهان')
        db.session.add_all([tehran, mashhad, esfahan])

    db.session.commit()
    print('Database tables created and default data added successfully!')


# --- ۴. تعریف مسیرها (Routes) ---

@app.route('/')
def home():
    # اگر کاربر لاگین بود، به لیست کاربران هدایت می‌شود. در غیر این صورت به صفحه ورود می‌رود.
    if current_user.is_authenticated:
        return redirect(url_for('users_list'))
    return redirect(url_for('login')) 


@app.route('/register', methods=['GET', 'POST'])
def register():
    # اگر کاربر از قبل وارد شده باشد، به لیست هدایت می‌شود
    if current_user.is_authenticated:
        return redirect(url_for('users_list'))
        
    cities = City.query.order_by(City.City).all() 
    # ... (منطق POST بدون تغییر باقی می‌ماند) ...
    if request.method == 'POST':
        # ... (دریافت اطلاعات) ...
        email = request.form.get('email')
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        address = request.form.get('address')
        zipcode = request.form.get('zipcode')
        password = request.form.get('password')

        if User.query.filter_by(Email=email).first():
            flash("خطا: این ایمیل قبلاً ثبت نام کرده است.", 'error') 
            return redirect(url_for('register'))
        
        default_role = Role.query.filter_by(Rolename='User').first()

        new_user = User(
            Email=email, 
            Firstname=firstname, 
            Lastname=lastname,
            Address=address,
            Zipcode=zipcode,
            Role=default_role.RoleId
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        try:
            db.session.commit()
            flash("✅ ثبت نام با موفقیت انجام شد! اکنون می‌توانید وارد شوید.", 'success')
            return redirect(url_for('login')) # هدایت به صفحه ورود پس از ثبت نام موفق
        except Exception as e:
            db.session.rollback()
            flash(f"❌ خطایی در ثبت نام رخ داد: {e}", 'error')
            return redirect(url_for('register'))
            
    return render_template('register.html', cities=cities)


# --- NEW: مسیر ورود (Login Route) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('users_list'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(Email=email).first()
        
        # ۱. بررسی وجود کاربر
        if user is None:
            flash('ایمیل یا رمز عبور اشتباه است.', 'error')
            return redirect(url_for('login'))
        
        # ۲. بررسی صحت رمز عبور
        if not user.check_password(password):
            flash('ایمیل یا رمز عبور اشتباه است.', 'error')
            return redirect(url_for('login'))
            
        # ۳. ورود موفقیت آمیز کاربر و ذخیره نشست (Session)
        login_user(user)
        # اگر کاربر سعی کرده بود به صفحه‌ای خاص برود (next_page) به آنجا هدایت می‌شود
        next_page = request.args.get('next')
        return redirect(next_page or url_for('users_list'))

    return render_template('login.html')
    
# --- NEW: مسیر خروج (Logout Route) ---
@app.route('/logout')
def logout():
    logout_user()
    flash("شما با موفقیت خارج شدید.", 'info')
    return redirect(url_for('login'))


@app.route('/users')
@login_required # NEW: این صفحه فقط برای کاربران وارد شده قابل دسترسی است
def users_list():
    users = User.query.options(joinedload(User.role), joinedload(User.city)).all() 
    return render_template('users_list.html', users=users)


# --- ۵. اجرای برنامه (بدون تغییر) ---
if __name__ == '__main__':
    app.run(debug=True)