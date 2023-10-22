from flask_restful import Resource, reqparse

from REST_API import db
from old.REST_API.models import User


class UserRegistration(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', help='This field cannot be blank', required=True)
        parser.add_argument('password', help='This field cannot be blank', required=True)
        data = parser.parse_args()

        if User.query.filter_by(username=data['username']).first():
            return {'message': 'User already exists'}, 400

        new_user = User(username=data['username'], password=data['password'])
        db.session.add(new_user)
        db.session.commit()

        return {'message': 'User registered successfully'}, 201