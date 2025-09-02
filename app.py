from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# -------------------- App Setup --------------------
app = Flask(__name__)
# URL-encode special chars in your password (like @ -> %40)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:%40Fakedeviantgrowl17777@localhost/ecommerce_api'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------- Association Table --------------------
order_product = db.Table(
    'order_product',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
)

# -------------------- Models --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    email = db.Column(db.String(100), unique=True)
    orders = db.relationship('Order', backref='user', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "email": self.email
        }


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), unique=True)
    price = db.Column(db.Float)

    def to_dict(self):
        return {
            "id": self.id,
            "product_name": self.product_name,
            "price": self.price
        }


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    products = db.relationship('Product', secondary=order_product, backref='orders')

    def to_dict(self):
        return {
            "id": self.id,
            "order_date": self.order_date.isoformat(),
            "user_id": self.user_id,
            "products": [p.to_dict() for p in self.products],
            "total": sum(p.price for p in self.products)
        }

# -------------------- Error Handler --------------------
@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"error": str(e)}), 500

# -------------------- User Endpoints --------------------
@app.route('/users', methods=['GET'])
def get_users():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    users = User.query.paginate(page=page, per_page=limit, error_out=False)
    return jsonify({
        "page": page,
        "limit": limit,
        "total": users.total,
        "items": [u.to_dict() for u in users.items]
    })

@app.route('/users/<int:id>', methods=['GET'])
def get_user(id):
    return jsonify(User.query.get_or_404(id).to_dict())

@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    if not data or not all(k in data for k in ("name", "address", "email")):
        return jsonify({"error": "Missing required fields"}), 400
    try:
        new_user = User(name=data['name'], address=data['address'], email=data['email'])
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email already exists"}), 400

@app.route('/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.json
    try:
        user.name = data.get('name', user.name)
        user.address = data.get('address', user.address)
        user.email = data.get('email', user.email)
        db.session.commit()
        return jsonify(user.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email already exists"}), 400

@app.route('/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'})

# -------------------- Product Endpoints --------------------
@app.route('/products', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    products = Product.query.paginate(page=page, per_page=limit, error_out=False)
    return jsonify({
        "page": page,
        "limit": limit,
        "total": products.total,
        "items": [p.to_dict() for p in products.items]
    })

@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    return jsonify(Product.query.get_or_404(id).to_dict())

@app.route('/products', methods=['POST'])
def create_product():
    data = request.json
    if not data or "product_name" not in data or "price" not in data:
        return jsonify({"error": "Missing required fields"}), 400
    if not isinstance(data["price"], (int, float)):
        return jsonify({"error": "Price must be a number"}), 400
    try:
        new_product = Product(product_name=data['product_name'], price=data['price'])
        db.session.add(new_product)
        db.session.commit()
        return jsonify(new_product.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Product already exists"}), 400

@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = Product.query.get_or_404(id)
    data = request.json
    try:
        if "price" in data and not isinstance(data["price"], (int, float)):
            return jsonify({"error": "Price must be a number"}), 400
        product.product_name = data.get('product_name', product.product_name)
        product.price = data.get('price', product.price)
        db.session.commit()
        return jsonify(product.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Product already exists"}), 400

@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Product deleted'})

# -------------------- Order Endpoints --------------------
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.json
    if not data or "user_id" not in data:
        return jsonify({"error": "Missing user_id"}), 400
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404
    try:
        order_date = datetime.fromisoformat(data['order_date']) if "order_date" in data else datetime.utcnow()
        new_order = Order(user_id=data['user_id'], order_date=order_date)
        db.session.add(new_order)
        db.session.commit()
        return jsonify(new_order.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Invalid data"}), 400

@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product_to_order(order_id, product_id):
    order = Order.query.get_or_404(order_id)
    product = Product.query.get_or_404(product_id)
    if product not in order.products:
        order.products.append(product)
        db.session.commit()
    return jsonify(order.to_dict())

@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['PUT'])
def remove_product_from_order(order_id, product_id):
    order = Order.query.get_or_404(order_id)
    product = Product.query.get_or_404(product_id)
    if product in order.products:
        order.products.remove(product)
        db.session.commit()
    return jsonify(order.to_dict())

@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_by_user(user_id):
    return jsonify([o.to_dict() for o in Order.query.filter_by(user_id=user_id).all()])

@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_products_in_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify([p.to_dict() for p in order.products])

# -------------------- Run App --------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
