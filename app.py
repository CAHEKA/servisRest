from flask import Flask
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource, reqparse
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Секретный ключ для JWT (замените на свой)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'  # Используем SQLite базу данных
api = Api(app)
jwt = JWTManager(app)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    def set_password(self, secret):
        self.password = generate_password_hash(secret)

    def check_password(self, secret):
        return check_password_hash(self.password, secret)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(80))
    price = db.Column(db.Float, nullable=False)
    discounted = db.Column(db.Boolean, default=False)
    discount_type = db.Column(db.String(80))
    discount_amount = db.Column(db.Float)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('CartItem', backref='cart', lazy=True)
    total_price = db.Column(db.Float, nullable=False)
    total_discount = db.Column(db.Float, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    total_price = db.Column(db.Float, nullable=False)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)


with app.app_context():
    db.create_all()


class UserRegistration(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', help='This field cannot be blank', required=True)
        parser.add_argument('password', help='This field cannot be blank', required=True)
        data = parser.parse_args()

        if User.query.filter_by(username=data['username']).first():
            return {'message': 'User already exists'}, 400

        new_user = User(username=data['username'])
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()

        return {'message': 'User registered successfully'}, 201

class UserLogin(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', help='This field cannot be blank', required=True)
        parser.add_argument('password', help='This field cannot be blank', required=True)
        data = parser.parse_args()

        user = User.query.filter_by(username=data['username']).first()
        if not user or not user.check_password(data['password']):
            return {'message': 'Invalid credentials'}, 401

        access_token = create_access_token(identity=user.username)
        return {'access_token': access_token}, 200

class ProductList(Resource):
    @jwt_required()
    def get(self, product_id=None):
        if product_id is None:
            products = Product.query.all()
            return self.add_product_list(products)
        else:
            product = Product.query.get(product_id)
            if product is not None:
                return self.add_product_list([product])
            else:
                return {'message': 'Product not found'}, 404
    @staticmethod
    def add_product_list(products):
        product_list = []
        for product in products:
            product_list.append({
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'price': product.price,
                'discounted': product.discounted,
                'discount': {
                    'type': product.discount_type,
                    'amount': product.discount_amount
                } if product.discounted else None
            })
        return product_list

class ShoppingCart(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        if not user:
            return {'message': 'User not found'}, 404

        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        cart_contents = []

        for item in cart_items:
            product = Product.query.get(item.product_id)
            cart_contents.append({
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'price': product.price,
                'discounted': product.discounted,
                'discount': {
                    'type': product.discount_type,
                    'amount': product.discount_amount
                } if product.discounted else None
            })

        return {'cart': cart_contents}

    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()

        parser = reqparse.RequestParser()
        parser.add_argument('product_id', type=int, help='This field cannot be blank', required=True)
        data = parser.parse_args()

        product = Product.query.get(data['product_id'])
        if not product:
            return {'message': 'Product not found'}, 404

        cart_item = CartItem(user_id=user.id, product_id=data['product_id'])
        db.session.add(cart_item)
        db.session.commit()

        return {'message': 'Product added to cart successfully'}, 201

    @jwt_required()
    def delete(self, product_id):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        if not user:
            return {'message': 'User not found'}, 404

        cart_item = CartItem.query.filter_by(user_id=user.id, product_id=product_id).first()
        if not cart_item:
            return {'message': 'Product not found in cart'}, 404

        db.session.delete(cart_item)
        db.session.commit()
        return {'message': 'Product removed from cart'}, 200

class Checkout(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        if not user:
            return {'message': 'User not found'}, 404

        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        if not cart_items:
            return {'message': 'Cart is empty'}, 400

        total_price = 0
        ordered_items = []

        for item in cart_items:
            product = Product.query.get(item.product_id)
            price = product.price
            if product.discounted and product.discount_type == 'Percentage':
                price -= (product.discount_amount / 100) * price
            elif product.discounted and product.discount_type == 'Fixed':
                price -= product.discount_amount
            total_price += price
            ordered_items.append({
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'price': price,
                'discounted': product.discounted,
                'discount': {
                    'type': product.discount_type,
                    'amount': product.discount_amount
                } if product.discounted else None
            })

        # Создание записи заказа (примерное представление)
        order_id = user.orders.count() + 1
        for item in cart_items:
            product = Product.query.get(item.product_id)
            user.orders.append(OrderItem(product_id=product.id, order_id=order_id))
        db.session.delete(cart_items)  # Удаляем товары из корзины
        db.session.commit()

        return {
            'message': 'Order placed successfully',
            'order_id': order_id,
            'total_price': total_price,
            'ordered_items': ordered_items
        }, 201


# Добавьте ресурс в ваше приложение
api.add_resource(UserRegistration, '/register')
api.add_resource(UserLogin, '/login')
api.add_resource(ProductList, '/products', '/products/<int:product_id>')
# api.add_resource(ShoppingCart, '/cart', '/cart/<int:product_id>')
# api.add_resource(Checkout, '/checkout')


if __name__ == '__main__':
    app.run(debug=True)
