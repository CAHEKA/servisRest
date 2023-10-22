from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_swagger_ui import get_swaggerui_blueprint


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Секретный ключ для JWT
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'  # Путь к базе данных
db = SQLAlchemy(app)
jwt = JWTManager(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.String(50), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    discount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)


with app.app_context():
    db.create_all()

products = [
  {
    "id": "12345",
    "name": "HP Pavilion Laptop",
    "category": "Electronics",
    "price": 599.99,
    "discounted": True,
    "discount": {
      "type": "Percentage",
      "amount": 10
    }
  },
  {
    "id": "67890",
    "name": "Adidas T-shirt",
    "category": "Clothing",
    "price": 29.99,
    "discounted": False
  },
  {
    "id": "54321",
    "name": "Samsung Galaxy Smartphone",
    "category": "Electronics",
    "price": 799.99,
    "discounted": True,
    "discount": {
      "type": "Fixed",
      "amount": 50
    }
  },
  {
    "id": "98765",
    "name": "Levi's Jeans",
    "category": "Clothing",
    "price": 69.99,
    "discounted": True,
    "discount": {
      "type": "Percentage",
      "amount": 20
    }
  }
]

# flask swagger configs
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Todo List API"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)


def calculate_cart_total(cart_items):
    total_price = sum(item.price * item.quantity for item in cart_items)
    total_discount = sum(item.discount * item.quantity for item in cart_items)
    return total_price, total_discount


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    # Дополнительные поля пользователя

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists"}), 400

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username, password=password).first()

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({"access_token": access_token}), 200


@app.route('/products', methods=['GET'])
@jwt_required()
def get_products():
    return products


@app.route('/cart', methods=['GET', 'POST', 'PUT', 'DELETE'])
@jwt_required()
def cart():
    current_user_id = get_jwt_identity()

    if request.method == 'GET':
        cart_items = Cart.query.filter_by(user_id=current_user_id).all()
        cart_data = [{
            "product_id": item.product_id,
            "product_name": item.product_name,
            "quantity": item.quantity,
            "discount": round(item.discount * item.quantity, 2),
            "price": round(item.price * item.quantity, 2)

        } for item in cart_items]

        total_price, total_discount = calculate_cart_total(cart_items)
        cart_summary = {
            "cart_items": cart_data,
            "total_price": round(total_price, 2),
            "total_discount": round(total_discount, 2),
            "total_price_with_discount": round(total_price - total_discount, 2)
        }

        return jsonify(cart_summary), 200

    elif request.method == 'POST':
        data = request.get_json()
        product_id = data.get('product_id')
        product_quantity = data.get('quantity')
        product = next((p for p in products if p['id'] == product_id), None)

        if not product:
            return jsonify({"message": "Product not found"}), 404

        cart_item = Cart.query.filter_by(user_id=current_user_id, product_id=product_id).first()

        if cart_item:
            cart_item.quantity += product_quantity
        else:
            price = product['price']
            discount = 0
            if product.get('discounted') and product['discount']['type'] == 'Percentage':
                discount = price * (product['discount']['amount'] / 100)
            elif product.get('discounted') and product['discount']['type'] == 'Fixed':
                discount = product['discount']['amount']

            cart_item = Cart(
                user_id=current_user_id,
                product_id=product_id,
                product_name=product['name'],
                discount=discount,
                price=price,
                quantity=product_quantity
            )
            db.session.add(cart_item)

        db.session.commit()

        return jsonify({"message": "Product added to cart"}), 201

    elif request.method == 'DELETE':
        data = request.get_json()
        product_id = data.get('product_id')

        cart_item = Cart.query.filter_by(user_id=current_user_id, product_id=product_id).first()

        if not cart_item:
            return jsonify({"message": "Product not found in cart"}), 404

        db.session.delete(cart_item)
        db.session.commit()

        return jsonify({"message": "Product removed from cart"}), 200


if __name__ == '__main__':
    app.run(debug=True)
