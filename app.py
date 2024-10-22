from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Product, Location, Measurement, add_default_measurements, Supplier, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from forms import LoginForm, RegistrationForm
from decorators import role_required
from werkzeug.security import generate_password_hash


import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'sfkmskjnkj2kj4n234j'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()
    add_default_measurements()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/user_list')
@login_required
@role_required('admin')  # Только администраторы могут видеть этот список
def user_list():
    users = User.query.all()
    return render_template('user_list.html', users=users)

@app.route('/set_role/<int:user_id>', methods=['POST'])
@login_required
def set_role(user_id):
    # Проверяем, что текущий пользователь - администратор
    if current_user.role != 'admin':
        abort(403)

    # Находим пользователя, которому нужно изменить роль
    user = User.query.get_or_404(user_id)
    
    # Получаем новую роль из формы
    new_role = request.form.get('role')  # 'admin', 'user', etc.
    
    if new_role:
        user.role = new_role
        db.session.commit()
        flash(f'Роль пользователя {user.username} изменена на {new_role}', 'success')
    
    return redirect(url_for('user_list'))  # Перенаправляем на список пользователей или другую страницу



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = form.role.data  # Получаем роль из формы
        
        # Хешируем пароль
        hashed_password = generate_password_hash(password)
        
        # Создаем нового пользователя
        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Пользователь успешно зарегистрирован!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Вы успешно вошли в систему!')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.')
    return redirect(url_for('login'))

@app.route('/home_page')
@login_required
def home_page():
    return f'Привет, {current_user.username}! Это домашняя страница.'

@app.route('/products', methods=['GET', 'POST'])
def products_page():
    locations = Location.query.all()
    measurements = Measurement.query.all()

    if request.method == 'POST':
        product_name = request.form.get('product')
        location_id = request.form.get('location')
        measurement_id = request.form.get('measurement')

        if product_name and location_id and measurement_id:
            product = Product(name=product_name, location_id=location_id, measurement_id=measurement_id)
            db.session.add(product)
            db.session.commit()
            return redirect(url_for('products_page'))

    products = Product.query.all()
    return render_template('products.html', products=products, locations=locations, measurements=measurements)

@app.route('/locations', methods=['GET', 'POST'])
def locations_page():
    if request.method == 'POST':
        location_name = request.form.get('location')
        if location_name:
            location = Location(name=location_name)
            db.session.add(location)
            db.session.commit()
            return redirect(url_for('locations_page'))
    locations = Location.query.all()
    return render_template('locations.html', locations=locations)

@app.route('/suppliers', methods=['GET', 'POST'])
def suppliers_page():
    if request.method == 'POST':
        supplier_name = request.form.get('supplier')
        if supplier_name:
            supplier = Supplier(name=supplier_name)
            db.session.add(supplier)
            db.session.commit()
            return redirect(url_for('suppliers_page'))

    suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    locations = Location.query.all()
    measurements = Measurement.query.all()

    if request.method == 'POST':
        product.name = request.form.get('product')
        product.location_id = request.form.get('location')
        product.measurement_id = request.form.get('measurement')
        db.session.commit()
        return redirect(url_for('products_page'))

    return render_template('edit_product.html', product=product, locations=locations, measurements=measurements)

@app.route('/locations/<int:location_id>/edit', methods=['GET', 'POST'])
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)

    if request.method == 'POST':
        location.name = request.form.get('location')
        db.session.commit()
        return redirect(url_for('locations_page'))

    return render_template('edit_location.html', location=location)

@app.route('/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    products = Product.query.all()

    if request.method == 'POST':
        product_ids = request.form.getlist('products')
        supplier.products = Product.query.filter(Product.id.in_(product_ids)).all()
        db.session.commit()
        return redirect(url_for('suppliers_page'))

    return render_template('edit_supplier.html', supplier=supplier, products=products)


@app.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('products_page'))

@app.route('/locations/<int:location_id>/delete', methods=['POST'])
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)

    # Проверяем, используется ли расположение в продуктах
    products_using_location = Product.query.filter_by(location_id=location_id).all()

    if products_using_location:
        error_message = "Cannot delete this location because it is used in one or more products."
        locations = Location.query.all()
        return render_template('locations.html', locations=locations, error_message=error_message)

    db.session.delete(location)
    db.session.commit()
    return redirect(url_for('locations_page'))

@app.route('/suppliers/<int:supplier_id>/delete', methods=['POST'])
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    products_using_supplier = Product.query.filter_by(supplier_id=supplier_id).all()
    
    if products_using_supplier:
        error_message = "Cannot delete this suppliar because it is used in one or more products."
        suppliers = Supplier.query.all()
        return render_template('suppliers.html', suppliers=suppliers, error_message=error_message)
    
    db.session.delete(supplier)
    db.session.commit()
    return redirect(url_for('suppliers_page'))

@app.route('/supplier/<int:supplier_id>/product/<int:product_id>/remove', methods=['POST'])
def remove_product_from_supplier(supplier_id, product_id):
    supplier = Supplier.query.get(supplier_id)
    product = Product.query.get(product_id)

    if supplier and product:
        # Удаление связи между поставщиком и продуктом
        supplier.products.remove(product)
        db.session.commit()
        flash('Продукт успешно удален из списка поставщика.', 'success')
    else:
        flash('Не удалось найти поставщика или продукт.', 'error')

    # Возвращаемся на страницу поставщика
    return redirect(url_for('suppliers_page', supplier_id=supplier_id))





@app.route('/inventory', methods=['GET', 'POST'])
def inventory_page():
    locations = Location.query.all()

    if request.method == 'POST':
        data = []
        for location in locations:
            for product in location.products:
                quantity = request.form.get(f'quantity_{product.id}')
                if quantity:
                    data.append({
                        'Product Name': product.name,
                        'Location': product.location.name,
                        'Measurement': product.measurement.name,
                        'Quantity': float(quantity)
                    })

        df = pd.DataFrame(data)
        file_path = os.path.join('static', 'inventory.xlsx')
        df.to_excel(file_path, index=False)

        return redirect(url_for('inventory_page'))

    return render_template('inventory.html', locations=locations)

@app.route('/suppliers/<int:supplier_id>/add_product', methods=['GET', 'POST'])
def add_product_to_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    products = Product.query.all()
    measurements = Measurement.query.all()

    if request.method == 'POST':
        product_id = request.form.get('product')
        measurement_id = request.form.get('measurement')

        if product_id and measurement_id:
            product = Product.query.get_or_404(product_id)
            supplier.products.append(product)  # Добавляем продукт к поставщику
            db.session.commit()
            return redirect(url_for('suppliers_page'))  # Перенаправляем на страницу поставщиков

    return render_template('add_product_to_supplier.html', supplier=supplier, products=products, measurements=measurements)



@app.route('/orders', methods=['GET', 'POST'])
def order_page():
    suppliers = Supplier.query.all()

    if request.method == 'POST':
        data = []
        for supplier in suppliers:
            for product in supplier.products:
                quantity = request.form.get(f'quantity_{supplier.id}_{product.id}')
                if quantity:
                    data.append({
                        'Supplier': supplier.name,
                        'Product': product.name,
                        'Quantity': float(quantity)
                    })

        # Сохранение данных в Excel
        df = pd.DataFrame(data)
        file_path = os.path.join('static', 'orders.xlsx')
        df.to_excel(file_path, index=False)

        return redirect(url_for('order_page'))

    return render_template('order_form.html', suppliers=suppliers)



if __name__ == '__main__':
    app.run(debug=True)





