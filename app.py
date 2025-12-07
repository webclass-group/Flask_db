# app.py

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash # برای هش کردن پسورد
import os

# --- ۱. پیکربندی و راه‌اندازی ---
app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- ۲. تعریف مدل‌های داده (جداول) ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
    
    
# --- ۳. دستور CLI برای ساخت دیتابیس ---
# برای اجرای 'flask create-db'
@app.cli.command("create-db")
def create_db():
    db.create_all()
    print('Database tables created successfully!')

# --- ۴. تعریف مسیرها (Routes) ---

@app.route('/')
def home():
    # به طور پیش فرض کاربر را به صفحه ثبت نام هدایت می کنیم
    return redirect(url_for('register')) 

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # منطق بررسی وجود کاربر (برای جلوگیری از ثبت نام تکراری)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            # در اینجا بهتر است یک پیام فلش (flash message) به کاربر نمایش داده شود
            print("Error: Username already exists.") 
            return redirect(url_for('register'))

        # ایجاد شیء کاربر جدید، هش کردن پسورد و ذخیره
        new_user = User(username=username, email=email)
        new_user.set_password(password) # هش کردن پسورد
        
        db.session.add(new_user)
        db.session.commit()
        
        # هدایت به صفحه نمایش کاربران پس از ثبت موفقیت‌آمیز
        return redirect(url_for('users_list'))
    # نمایش فرم ثبت نام برای متد GET
    return render_template('register.html')


@app.route('/users')
def users_list():
    # خواندن تمام کاربران از پایگاه داده
    users = User.query.all() 
    return render_template('users_list.html', users=users)


# --- ۵. اجرای برنامه ---
if __name__ == '__main__':
    app.run(debug=True)