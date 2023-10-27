from flask import Flask
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource, reqparse
from werkzeug.security import check_password_hash, generate_password_hash
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Секретный ключ для JWT (замените на свой)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'  # Используем SQLite базу данных
api = Api(app)
jwt = JWTManager(app)
db = SQLAlchemy(app)

swaggerui_blueprint = get_swaggerui_blueprint(
    '/swagger',
    '/static/swagger.json',
    config={
        'app_name': "My Flask Service"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix='/swagger')


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
    discount = db.Column(db.Float)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('CartItem', backref='cart', lazy=True)
    total_price = db.Column(db.Float, nullable=False)
    total_discount = db.Column(db.Float, nullable=False)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    total_price = db.Column(db.Float, nullable=False)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)


with app.app_context():
    db.create_all()

    # Проверим, есть ли уже продукты в базе данных
    if not Product.query.first():
        # Если нет, то сгенерируем и добавим несколько продуктов
        products = [
            Product(name='HP Pavilion Laptop', category='Electronics', price=10.99, discount=10),
            Product(name='Samsung Galaxy Smartphone', category='Electronics', price=15.99),
            Product(name='Adidas T-shirt', category='Clothing', price=8.99, discount=2.50),
            Product(name='Levis Jeans', category='Clothing', price=12.99, discount=15)
        ]

        for product in products:
            db.session.add(product)

        db.session.commit()

print("The application is ready to run.")

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
                'discount': product.discount
            })
        return product_list


class ShoppingCart(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        if not user:
            return {'message': 'User not found'}, 404

        # Найдем корзину пользователя
        cart = Cart.query.filter_by(user_id=user.id).first()
        if not cart:
            return {'message': 'Cart not found'}, 404

        # Получим все элементы корзины для этой корзины
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()

        # Соберем информацию о товарах в корзине
        cart_contents = []
        total_price = 0
        total_discount= 0
        for cart_item in cart_items:
            product = Product.query.get(cart_item.product_id)
            item_price = product.price * cart_item.quantity  # Цена товара умноженная на количество
            total_price += item_price  # Добавляем к total_price
            if product.discount is not None:
                item_discount = item_price * (product.discount / 100)  # Цена товара умноженная на количество
                total_discount += item_discount

            cart_contents.append({
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'price': product.price,
                'discount': product.discount,
                'quantity': cart_item.quantity
            })

        # Добавим total_price и total_discount в ответ
        response = {
            'cart': cart_contents,
            'total_price': total_price,
            'total_discount': round(total_discount, 2)
        }

        return response

    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()

        parser = reqparse.RequestParser()
        parser.add_argument('product_id', type=int, help='This field cannot be blank', required=True)
        parser.add_argument('quantity', type=int, default=1)  # По умолчанию количество равно 1
        data = parser.parse_args()

        product_id = data['product_id']
        quantity = data['quantity']

        product = Product.query.get(product_id)
        if not product:
            return {'message': 'Product not found'}, 404

        # Поиск существующей корзины пользователя
        cart = Cart.query.filter_by(user_id=user.id).first()

        # Если корзины пользователя нет, создайте ее
        if cart is None:
            cart = Cart(user_id=user.id, total_price=0.0, total_discount=0.0)
            db.session.add(cart)
            db.session.commit()

        # Проверим, есть ли уже такой товар в корзине пользователя
        existing_cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()

        if existing_cart_item:
            # Если товар уже есть в корзине, увеличим его количество на указанное количество
            existing_cart_item.quantity += quantity
        else:
            # Если товара нет в корзине, добавим его с указанным количеством
            cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)

        db.session.commit()

        return {'message': 'Product added to cart successfully'}, 201

    @jwt_required()
    def delete(self, product_id):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        if not user:
            return {'message': 'User not found'}, 404

        # Найдите корзину пользователя по user_id
        cart = Cart.query.filter_by(user_id=user.id).first()
        if not cart:
            return {'message': 'Cart not found for this user'}, 404

        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if not cart_item:
            return {'message': 'Product not found in cart'}, 404

        # Если у товара в корзине количество больше одного, уменьшим количество на 1
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            db.session.delete(cart_item)

        db.session.commit()
        return {'message': 'Product removed from cart'}, 200


# Добавьте ресурс в ваше приложение
api.add_resource(UserRegistration, '/register')
api.add_resource(UserLogin, '/login')
api.add_resource(ProductList, '/products', '/products/<int:product_id>')
api.add_resource(ShoppingCart, '/cart', '/cart/<int:product_id>')

if __name__ == '__main__':

    app.run(debug=True)
