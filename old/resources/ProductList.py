from flask_jwt_extended import jwt_required
from flask_restful import Resource
from old.REST_API.models import *

class ProductList(Resource):
    @jwt_required()
    def get(self):
        products = Product.query.all()
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