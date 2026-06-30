import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate

app = Flask(__name__)

#app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'random-number123')
#app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
#    'DATABASE_URL', 'postgresql://test:python123@localhost:5432/sales'
#)
app.config['SECRET_KEY'] = 'random-number123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://test:python123@localhost:5432/sales'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler('logs/dashboard.log', maxBytes=1024000, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Sales Dashboard startup configuration initialised.')

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_view'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            app.logger.info(f"User '{username}' logged in cleanly from IP: {request.remote_addr}")
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard_view'))
        
        app.logger.warning(f"Failed login attempt for user '{username}' from IP: {request.remote_addr}")
        flash('Invalid username or password.', 'danger')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    user_left = current_user.username
    logout_user()
    app.logger.info(f"User '{user_left}' logged out cleanly.")
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard_view():
    return render_template('dashboard.html')

@app.route('/api/dashboard')
@login_required
def dashboard_api():
    try:
        total_sales = db.session.query(db.func.sum(Order.amount)).scalar() or 0.0
        total_orders = db.session.query(db.func.count(Order.id)).scalar() or 0
        total_customers = db.session.query(db.func.count(db.func.distinct(Order.customer_name))).scalar() or 0

        recent_orders_query = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        recent_list = [{
            "id": o.id,
            "customer": o.customer_name,
            "product": o.product_name,
            "amount": f"${o.amount:,.2f}"
        } for o in recent_orders_query]

        return jsonify({
            "sales": f"${total_sales:,.2f}",
            "customers": total_customers,
            "orders": total_orders,
            "recent": recent_list
        })
    except Exception as e:
        app.logger.error(f"Error compiling dashboard metrics: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error Processing Metrics"}), 500

#
@app.route('/add-order', methods=['GET', 'POST'])
@login_required
def add_order_page():
    if request.method == 'POST':
        try:
            # 1. Pull data directly from the standard HTML form fields
            customer = request.form.get('customer')
            product = request.form.get('product')
            amount = request.form.get('amount')
            
            # 2. Map and save into your PostgreSQL Order rows
            new_order = Order(
                customer_name=customer,
                product_name=product,
                amount=float(amount)
            )
            db.session.add(new_order)
            db.session.commit()
            
            # 3. Log activity and flash a success alert notice on the dashboard
            app.logger.info(f"User {current_user.username} successfully added an order via dedicated page.")
            flash('Transaction logged successfully!', 'success')
            return redirect(url_for('dashboard_view'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to save order via page view: {str(e)}")
            flash('Error logging transaction. Please verify input data.', 'danger')
            
    return render_template('add_order.html')


@app.route('/api/orders/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_order_api(order_id):
    try:
        order_to_delete = Order.query.get_or_404(order_id)
        db.session.delete(order_to_delete)
        db.session.commit()
        
        app.logger.info(f"User {current_user.username} deleted Order ID #{order_id}")
        return jsonify({"message": "Order removed successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to delete Order ID #{order_id}: {str(e)}")
        return jsonify({"error": "Database deletion failure"}), 500



#

#@app.line_magic # Used for click framework integration
@app.cli.command("seed-db")
def seed_db():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        db.session.add(Order(customer_name="Alice Smith", product_name="Enterprise Laptop", amount=1200.00))
        db.session.add(Order(customer_name="Bob Jones", product_name="Mechanical Keyboard", amount=150.50))
        db.session.add(Order(customer_name="Charlie Brown", product_name="27-inch Monitor", amount=350.00))
        
        db.session.commit()
        print("Database initialized, user 'admin' with password 'admin123' created alongside sample metrics.")
    else:
        print("Database already provisioned.")

if __name__ == '__main__':
        # 1. Open an application context link so Flask knows where the DB is
    with app.app_context():
        # 2. Tell SQLAlchemy to physically build the tables inside Postgres
        db.create_all()

        # 3. Check if the admin user exists; if missing, seed the database
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)

            db.session.add(Order(customer_name="Alice Smith", product_name="Enterprise Laptop", amount=1200.00))
            db.session.add(Order(customer_name="Bob Jones", product_name="Mechanical Keyboard", amount=150.50))
            db.session.add(Order(customer_name="Charlie Brown", product_name="27-inch Monitor", amount=350.00))

            db.session.commit()
            print(" Tables successfully built and sample metrics seeded!")

    # 4. Start the Flask server engine
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    

