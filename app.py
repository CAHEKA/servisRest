from flask import Flask, jsonify, request, render_template
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import sqlite3
import hashlib

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret'
jwt = JWTManager(app)


conn = sqlite3.connect('myapp.db', check_same_thread=False)
cursor = conn.cursor()


cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS products
                  (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL, discount REAL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS carts
                  (id INTEGER PRIMARY KEY, user_id INTEGER, total_price REAL, total_discount REAL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS cart_items
                  (id INTEGER PRIMARY KEY, cart_id INTEGER, product_id INTEGER, quantity INTEGER)''')


products = [
    ('HP Pavilion Laptop', 'Electronics', 10.99, 10),
    ('Samsung Galaxy Smartphone', 'Electronics', 15.99, None),
    ('Adidas T-shirt', 'Clothing', 8.99, 2.50),
    ('Levis Jeans', 'Clothing', 12.99, 15)
]
cursor.executemany("INSERT INTO products (name, category, price, discount) VALUES (?, ?, ?, ?)", products)

conn.commit()

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    if cursor.fetchone():
        return jsonify({'message': 'User already exists'}), 400

    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()

    return jsonify({'message': 'User registered successfully'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, hashed_password))
    user = cursor.fetchone()

    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200


@app.route('/products', methods=['GET'])
def get_products(product_id=None):
    if product_id is None:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        if products:
            return jsonify(add_product_list(products)), 200
        else:
            return jsonify({'message': 'No products found'}), 404
    else:
        cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
        product = cursor.fetchone()
        if product:
            return jsonify(add_product_list([product])), 200
        else:
            return jsonify({'message': 'Product not found'}), 404

@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = cursor.fetchone()
    if product:
        return jsonify(add_product_list([product])), 200
    else:
        return jsonify({'message': 'Product not found'}), 404
def add_product_list(products):
    product_list = []
    for product in products:
        product_list.append({
            'id': product[0],
            'name': product[1],
            'category': product[2],
            'price': product[3],
            'discount': product[4]
        })
    return product_list


@app.route('/cart', methods=['GET', 'POST'])
@jwt_required()
def shopping_cart():
    current_user = get_jwt_identity()
    user = cursor.execute("SELECT id FROM users WHERE username=?", (current_user,)).fetchone()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if request.method == 'GET':
        cart = cursor.execute("SELECT * FROM carts WHERE user_id=?", (user[0],)).fetchone()
        if not cart:
            return jsonify({'message': 'Cart not found'}), 404

        cart_items = cursor.execute("SELECT * FROM cart_items WHERE cart_id=?", (cart[0],)).fetchall()

        cart_contents = []
        total_price = 0
        total_discount = 0
        for cart_item in cart_items:
            product = cursor.execute("SELECT * FROM products WHERE id=?", (cart_item[2],)).fetchone()
            if product:
                item_price = product[3] * cart_item[3]
                total_price += item_price
                if product[4] is not None:
                    item_discount = item_price * (product[4] / 100)
                    total_discount += item_discount

                cart_contents.append({
                    'id': product[0],
                    'name': product[1],
                    'category': product[2],
                    'price': product[3],
                    'discount': product[4],
                    'quantity': cart_item[3]
                })

        response = {
            'cart': cart_contents,
            'total_price': total_price,
            'total_discount': round(total_discount, 2)
        }

        return jsonify(response), 200

    elif request.method == 'POST':
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        product = cursor.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not product:
            return jsonify({'message': 'Product not found'}), 404

        cart = cursor.execute("SELECT * FROM carts WHERE user_id=?", (user[0],)).fetchone()
        if not cart:
            cursor.execute("INSERT INTO carts (user_id, total_price, total_discount) VALUES (?, ?, ?)",
                           (user[0], 0.0, 0.0))
            conn.commit()
            cart_id = cursor.lastrowid
        else:
            cart_id = cart[0]

        cart_item = cursor.execute("SELECT * FROM cart_items WHERE cart_id=? AND product_id=?",
                                   (cart_id, product_id)).fetchone()

        if cart_item:
            cursor.execute("UPDATE cart_items SET quantity = quantity + ? WHERE cart_id=? AND product_id=?",
                           (quantity, cart_id, product_id))
        else:
            cursor.execute("INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, ?)",
                           (cart_id, product_id, quantity))

        conn.commit()
        return jsonify({'message': 'Product added to cart successfully'}), 201


@app.route('/cart/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product_from_cart(product_id):
    current_user = get_jwt_identity()
    user = cursor.execute("SELECT id FROM users WHERE username=?", (current_user,)).fetchone()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    cart = cursor.execute("SELECT * FROM carts WHERE user_id=?", (user[0],)).fetchone()
    if not cart:
        return jsonify({'message': 'Cart not found for this user'}), 404

    cart_item = cursor.execute("SELECT * FROM cart_items WHERE cart_id=? AND product_id=?",
                               (cart[0], product_id)).fetchone()
    if not cart_item:
        return jsonify({'message': 'Product not found in cart'}), 404

    if cart_item[3] > 1:
        cursor.execute("UPDATE cart_items SET quantity = quantity - 1 WHERE cart_id=? AND product_id=?",
                       (cart[0], product_id))
    else:
        cursor.execute("DELETE FROM cart_items WHERE cart_id=? AND product_id=?", (cart[0], product_id))

    conn.commit()
    return jsonify({'message': 'Product removed from cart'}), 200
@app.route('/swagger/')
def swagger_ui():
    return render_template('swagger.html')


if __name__ == '__main__':
    app.run(debug=True)
