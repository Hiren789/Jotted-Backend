from flask import request
from app import app
from app.utils import APIResponse
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
    t = int(data.get('t'))
    d = data.get('d')
    pricing = {0: {"s": {10: 0, 30: 5, 150: 10, 10000000: 25}},
           1: {"s": {30: 15, 50: 25, 100: 40, 250: 75, 500: 150, 1000: 300, 1500: 450, 2000: 600, 2500: 750, 3000: 1000, 3500: 1250, 4000: 1500, 4500: 1750, 5000: 2000, 6000: 2700, 7000: 3400, 8000: 4100, 9000: 4800, 10000: 5500, 12500: 7250, 15000: 9000, 10000000: 12500},
               "sf": {30: 5, 50: 5, 100: 8, 250: 10, 500: 15, 1000: 25, 1500: 25, 2000: 25, 2500: 30, 3000: 30, 3500: 30, 4000: 30, 4500: 30, 5000: 50, 6000: 50, 7000: 50, 8000: 75, 9000: 75, 10000: 100, 12500: 125, 15000: 150, 10000000: 150},
               "sa": {5: 5, 8: 5, 10: 5, 15: 5, 25: 5, 30: 5, 50: 7.50, 75: 7.50, 100: 10, 125: 10, 150: 10, 10000000:0}}}

    discounts = {0: {"m": 1, "1y": 10/12},
                1: {"m": 1, "1y": 0.9, "2y": 0.85, "3y": 0.8},
                2: {"m": 1, "1y": 12, "2y": 24, "3y": 36}}
    if it not in pricing:
        return APIResponse.success("Success", 422, data="Invalid institute type") 
    if s not in pricing[it]["s"]:
        return APIResponse.success("Success", 422, data="Invalid Students count") 
    if d not in discounts[it]:
        return APIResponse.success("Success", 422, data="Invalid Duration")
    k = discounts[it][d]
    price = pricing[it]["s"][s]
    if it == 1:
        if t not in pricing[it]["sa"]:
            return APIResponse.success("Success", 422, data="Invalid Team Member Count")
        if pricing[it]["sf"][s] <= t:
            price += 1000 if t == 10000000 else (
                t-pricing[it]["sf"][s])*pricing[it]["sa"][pricing[it]["sf"][s]]
    price *= discounts[2][d]
    data = {"origional_price":int(price), "discounted_price":int(price*k), "price_per_month_per_student":round(price*k/(discounts[2][d]*s), 2), "price_per_year_per_student":round(price*k*12/(discounts[2][d]*s), 2)}
    return APIResponse.success("Success", 200, data=data)