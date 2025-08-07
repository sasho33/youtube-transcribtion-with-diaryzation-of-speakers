# backend/app.py

from flask import Flask
from flask_restx import Api, Resource

app = Flask(__name__)
api = Api(app, title='Armwrestling Prediction API', doc='/swagger/')

@api.route('/hello')
class HelloWorld(Resource):
    def get(self):
        return {'message': 'Hello, Armwrestling World!'}

if __name__ == '__main__':
    app.run(debug=True)
