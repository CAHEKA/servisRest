from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

from REST_API import db
from old.REST_API.models import User, CartItem, Product, OrderItem


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