from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Expense
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense_tracker.db'
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

'''@app.before_first_request
def create_tables():
    with app.app_context():
        db.create_all()'''

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('login'))

@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        date = request.form['date'] or datetime.today().strftime('%Y-%m-%d')
        expense = Expense(
            amount=amount,
            category=category,
            date=date,
            user_id=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        flash('Expense added!')
        return redirect(url_for('view_expenses'))
    return render_template('add_expense.html', today=datetime.today().strftime('%Y-%m-%d'))

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def view_expenses():
    query = Expense.query.filter_by(user_id=current_user.id)
    category = request.args.get('category', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    if category:
        query = query.filter(Expense.category.ilike(f'%{category}%'))
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)

    expenses = query.all()
    total = sum(exp.amount for exp in expenses)
    return render_template('view_expenses.html', expenses=expenses, total=total, 
                           category=category, start_date=start_date, end_date=end_date)

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        flash("Unauthorized access.")
        return redirect(url_for('view_expenses'))
    if request.method == 'POST':
        expense.amount = request.form['amount']
        expense.category = request.form['category']
        expense.date = request.form['date']
        db.session.commit()
        flash('Expense updated!')
        return redirect(url_for('view_expenses'))
    return render_template('edit_expense.html', expense=expense)

@app.route('/delete_expense/<int:expense_id>')
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        flash("Unauthorized access.")
        return redirect(url_for('view_expenses'))
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted!')
    return redirect(url_for('view_expenses'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
