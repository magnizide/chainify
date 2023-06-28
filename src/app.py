import json
from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('', )

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'hola'})


@app.route('/chain/<int:id>', methods=['GET'])
def get_chain(id):
    pass

if __name__ == '__main__':
    app.run()