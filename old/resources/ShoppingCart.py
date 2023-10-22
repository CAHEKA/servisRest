from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Resource, reqparse

from REST_API import db
from old.REST_API.models import User, CartItem, Product


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
