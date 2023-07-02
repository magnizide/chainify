# built-in imports
import os, sys, json
from ast import literal_eval
from datetime import datetime, timezone
from re import match as re_match, split as re_split

# local imports

# external imports
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from bson import json_util, decode as bdecode
from flask import Flask, jsonify, request, abort


app = Flask(__name__)

app.config['MONGO_URI'] = 'mongodb://{0}:{1}@{2}:27017/{3}'.format(
    os.environ['MONGODB_USERNAME'],
    os.environ['MONGODB_PASSWORD'],
    os.environ['MONGODB_HOSTNAME'],
    os.environ['MONGODB_DATABASE']
)

client = MongoClient(app.config['MONGO_URI'])
db = client.appdb

CHAIN_INTERFACE = {
    'slug': None, # Required: custom identifare made up of name and mongo _id last 4 characters, autocomputed
    'titulo': None, # Required: Title of the chain. 
    'fecha_inicio': None, # Required: start date of the chain
    'fecha_fin': None, # # Required: end date of the chain
    'aviso': 2, # Optional: numbers of days in which the notification message will be sent
    'activo': True, # Optional: whether the chain will be active or not. Default value true or computed according to dates
    'mensaje': # Optional: message that will be sent ro all of the participants
    '''¡Saludos! Este mensaje es para recordar el pago de la cadena.''',
    'sub_div': 1, # Optional: to sub divide the participants in a month. Available opts are 1 or 2
    'participantes': [] # Required: List of dictionaries containing the information of the participants
}

PARTICIPANT_INTERFACE = {
    'nombre': None, # Required: name of the participant
    'numero': None, # Required: contact number of the participant
    'puesto': None, # Required: position in the chain.
}

REQUIRED_VALUES = (
    'titulo',
    'fecha_inicio',
    'fecha_fin',
    'participantes'
)

DATE_REGEX = r"^(0?[1-9]|[12][0-9]|3[01])[\/\-](0?[1-9]|1[012])[\/\-]\d{4}$"


# Debug and Helper functions
def my_print(*to_print):
    print(*to_print, file=sys.stderr)

def dict_diff_key_rm(dictionary: dict, fixed_keys: dict):
    
    differed_keys = {k:v for k,v in dictionary.items() if k not in fixed_keys}

    new_cp_dict = dictionary.copy()

    for k in differed_keys:
        new_cp_dict.pop(k)
    
    return new_cp_dict

# Error handlers
@app.errorhandler(422)
def unprocessable_entity(e):
    return jsonify(error=str(e)), 422

@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(404)
def bad_request(e):
    return jsonify(error=str(e)), 404


# GET Routes
@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'hola moshi'})

@app.route('/cadenas', methods=['GET'])
def get_cadenas():
    req = request.args
    res = { 'cadenas': [] }
    query = {'activo': literal_eval(req['activo'].title())} if 'activo' in req else {}
    
    for document in db.cadenas.find(query):
        document['_id'] = str(document['_id'])
        res['cadenas'].append(document)
    
    return jsonify(res)


@app.route('/cadenas/<slug>', methods=['GET'])
def get_one_cadena(slug):
    query = {'slug': slug}
    res = db.cadenas.find_one(query)

    if res is None:
        abort(404, ' there is no chain with slug \'{}\''.format(slug)) 

    return jsonify(json.loads(json_util.dumps(res)))

# DELETE Routes
@app.route('/cadenas/<slug>', methods=['DELETE'])
def disable_cadena(slug):
    print(slug,file=sys.stderr)
    query = {'slug': slug}
    res = db.cadenas.find_one_and_update(
        query, 
        {'$set': {'activo': False}},
        return_document=ReturnDocument.AFTER
    )
    
    if res is None:
        return jsonify({'error': 404, 'message': 'No hay cadena: {}'.format(id)})

    return jsonify(json.loads(json_util.dumps(res)))

# POST Routes
@app.route('/cadenas', methods=['POST'])
def create_cadena():
    req = request.json
    query = {'_id': None}
    res = CHAIN_INTERFACE.copy()

    # Ensure required values are present
    for k in REQUIRED_VALUES:
        if k not in req.keys():
            abort(422, 'key \'{}\' is required.'.format(k))
        
        # Ensure participantes values are present
        if k == 'participantes':  
            if not isinstance(req[k], list) or len(req[k]) == 0:
                abort(422, '\'{}\' is a JSON list of objects with at least 1 item.'.format(k))
            # Erroring on empty objects in the list and forcing to have all fields
            for i in PARTICIPANT_INTERFACE:
                for p in req[k]:
                    if i not in p:
                        # my_print(i)
                        abort(400, 'key \'{}\' is required in \'{}\''.format(i, k))
        
    # Creating response
    for k in CHAIN_INTERFACE:
        res[k] = req[k] if k in req else CHAIN_INTERFACE[k]                    

    # Sanitizings and initialisings
    sanitized_participants = []
    for k in res:
        # Erroring wrong dates
        if k in ('fecha_inicio', 'fecha_fin'):
            if not re_match(DATE_REGEX, res[k]):
                abort(422, '\'{}\' malformed, supported formats are DD-MM-YYYY or DD/MM/YYYY.'.format(k))
            # Sanitizing dates
            tuple_date = tuple(map(int, re_split(r"-+|\/+",res[k])[::-1]))
            res[k] = datetime(*tuple_date)
        # Sanitizing titulo and Initialize slug
        if k == 'titulo':
            if not re_match(r'^[a-z\d\-_\s]+$', res[k]):
                abort(422, '\'{}\' malformed, parameter can only contain alphanumeric characters.'.format(k))
            
            res['slug'] = res[k].replace(' ', '_').lower()
        # Sanitizing participantes
        if k == 'participantes':
            for p in res[k]:
                clean_dict = dict_diff_key_rm(p, PARTICIPANT_INTERFACE)
                sanitized_participants.append(clean_dict)
    # Sanitizing participantes 
    res['participantes'] = sanitized_participants

    # Creating record without final slug
    insert_result = db.cadenas.insert_one(res)

    # Updating record with final slug
    query['_id'] = insert_result.inserted_id
    query_result = db.cadenas.find_one_and_update(
        query,
        {'$set':
            {'slug': res['slug'] + '_' + str(insert_result.inserted_id)[-4:]}
        },
        return_document=ReturnDocument.AFTER
    )

    res = query_result
    

    return jsonify(json.loads(json_util.dumps(res)))

if __name__ == '__main__':
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 8080)
    app.run(host='0.0.0.0', port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)