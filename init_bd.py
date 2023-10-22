from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'  # Укажите путь к вашей базе данных
db = SQLAlchemy(app)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(80))
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Генерация 5 продуктов
    products = [
        Product(id=1, name='HP Pavilion Laptop', category='Electronics', price=10.99, discount=10),
        Product(id=2, name='Samsung Galaxy Smartphone', category='Electronics', price=15.99),
        Product(id=3, name='Adidas T-shirt', category='Clothing', price=8.99, discount=2.50),
        Product(id=4, name='Levis Jeans', category='Clothing', price=12.99, discount=15)
    ]

    # Добавление продуктов в базу данных
    with app.app_context():
        for product in products:
            db.session.add(product)
        db.session.commit()

    print("5 products have been generated and added to the database.")
