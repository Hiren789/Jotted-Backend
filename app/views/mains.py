from flask import request
from app import app
from app.utils import APIResponse, calculate_price
from app.models import City

@app.route('/')
def status_check():
    return APIResponse.success("Running", 200)

@app.route('/get_states', methods=['POST'])
def get_states():
    distinct_states = City.query.with_entities(
        City.state).distinct().order_by(City.state).all()
    states_list = [state[0] for state in distinct_states]
    return APIResponse.success("Success", 200, data=states_list)

@app.route('/get_cities', methods=['POST'])
def get_cities():
    data = request.get_json()
    distinct_cities = City.query.with_entities(
        City.city).filter_by(state=data['state']).distinct().order_by(City.city).all()
    cities_list = [city[0] for city in distinct_cities]
    return APIResponse.success("Success", 200, data=cities_list)

@app.route('/get_price_plan', methods=['POST'])
def get_price_plan():
    data = request.get_json()
    it = int(data.get('it'))
    s = int(data.get('s'))
    t = int(data.get('t')) if data.get('t') else None
    d = data.get('d')
    data = calculate_price(it, s, t, d)
    if type(data) == str:
        return  APIResponse.error(data, status_code=403)
    return APIResponse.success("Success", 200, data=data)