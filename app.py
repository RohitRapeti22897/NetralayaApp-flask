from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from config import Config
from models import db, User, Product
from forms import LoginForm, RegistrationForm, ProductForm
from flask import request

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "You must be logged in to access the home page and offers."

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
@login_required
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        u = User(username=form.username.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/cart')
@login_required
def cart():
    cart = session.get('cart', {})
    items = []
    total = 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        subtotal = p.price * qty
        items.append({'product':p, 'quantity':qty, 'subtotal':subtotal})
        total += subtotal
    return render_template('cart.html', cart_items=items, total=total)

@app.route('/add_to_cart/<int:pid>')
@login_required
def add_to_cart(pid):
    cart = session.get('cart', {})
    cart[str(pid)] = cart.get(str(pid),0) + 1
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/checkout')
@login_required
def checkout():
    session.pop('cart', None)
    return render_template('checkout.html')

# Admin routes
@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('index'))
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/product/new', methods=['GET', 'POST'])
@app.route('/admin/product/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(pid=None):
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('index'))

    product = Product() if pid is None else Product.query.get_or_404(pid)
    form = ProductForm(obj=product)

    if form.validate_on_submit():
        form.populate_obj(product)
        db.session.add(product)
        db.session.commit()
        flash('Product saved.')
        return redirect(url_for('admin_products'))  # ← Redirect prevents duplicate submissions

    return render_template('product_form.html', form=form)

@app.route('/admin/product/<int:pid>/delete', methods=['POST'])
@login_required
def delete_product(pid):
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(pid)
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{product.name}" has been deleted.')
    return redirect(url_for('admin_products'))

@app.route('/remove_one/<int:pid>')
@login_required
def remove_one_from_cart(pid):
    cart = session.get('cart', {})
    pid_str = str(pid)
    if pid_str in cart:
        if cart[pid_str] > 1:
            cart[pid_str] -= 1
        else:
            cart.pop(pid_str)
        session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/clear_cart')
@login_required
def clear_cart():
    session.pop('cart', None)
    flash("Cart cleared.")
    return redirect(url_for('cart'))

if __name__ == '__main__':
    app.run(debug=True)
