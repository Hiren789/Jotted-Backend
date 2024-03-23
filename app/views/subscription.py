from flask import request, redirect
from flask_jwt_extended import get_jwt_identity, jwt_required
from app import app, db, stripe
from app.models import User
from app.utils import APIResponse, calculate_price

def search_for_price(ins_type, students, recurring, team=None):
    prices = []
    while True:
        start_from = None if prices == [] else prices[-1]['id']
        tmpdata = stripe.Price.list(type="recurring", active=True, limit=100, starting_after=start_from)
        prices += tmpdata["data"]
        if tmpdata["has_more"] == False:
            break
    prices = [i for i in prices if ('ins_type' in i['metadata']) and (i['metadata']['ins_type']==str(ins_type))]
    prices = [i for i in prices if ('students' in i['metadata']) and (i['metadata']['students']==str(students))]
    prices = [i for i in prices if ('recurring' in i['metadata']) and (i['metadata']['recurring']==str(recurring))]
    if team:
        prices = [i for i in prices if ('team' in i['metadata']) and (i['metadata']['team']==str(team))]
    if prices != []:
        return prices[0]["id"]
    else:
        md = {"ins_type": ins_type, "students": students, "recurring": recurring}
        if team:
            md["team"] = team
        
        data = calculate_price(ins_type, students, team, recurring)
        if type(data) == str:
            return data
        else:
            unit_amount = data["discounted_price"]
        plan_name = ""
        plan_name += "Individual " if ins_type == 0 else "Team "
        if ins_type == 0:
            if students == 10:
                plan_name += "Free "
            if students == 30:
                plan_name += "Basic "
            if students == 150:
                plan_name += "Standard "
            if students == 10000000:
                plan_name += "Unlimited "
        rrr = "month" if recurring == "m" else "year"
        rcc = 1 if recurring == "m" else int(recurring[0])
        new_price = stripe.Price.create(
          currency="usd",
          unit_amount=unit_amount*100,
          recurring={"interval": rrr, "interval_count": rcc},
          product_data={"name": f"{plan_name}Plan"},
          metadata=md
        )
        return new_price.id

@app.route('/set_payment', methods=['POST'])
@jwt_required()
def set_payment():
    current_user = get_jwt_identity()
    data = request.get_json()
    plan = data.get('plan')
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("Couldn't find a user account", 400)
    
    if not user.stripe_cus_id:
        tmpcus = stripe.Customer.create(email=user.email, name=f"{user.fn} {user.ln}")
        user.stripe_cus_id = tmpcus["id"]
        db.session.commit()
    
    itt = list(plan.keys())[0]
    ppi = search_for_price(int(itt), plan[itt]["s"], plan[itt]["d"], team=plan[itt].get("t"))
    if not user.stripe_sub_id:
        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_cus_id,
            line_items=[
                {
                    'price': ppi, "quantity": 1
                },
            ],
            metadata = {"user_id": current_user, "ins_type": itt, "students": plan[itt]["s"], "duration": plan[itt]["d"], "team": plan[itt].get("t")},
            mode='subscription',
            success_url = app.config.get("BACKEND_URL") + '/call/payment?session_id={CHECKOUT_SESSION_ID}',
            cancel_url = app.config.get("BACKEND_URL") + '/cancel.html',
        )
        return redirect(checkout_session.url)
        # return jsonify(checkout_session.url)
    else:
        sub = stripe.Subscription.retrieve(user.stripe_sub_id)
        sub_item_id = dict(sub)["items"]["data"][0]["id"]
        stripe.SubscriptionItem.modify(sub_item_id, price = ppi)
        return APIResponse.success("Plan updated successfully", 200)

@app.route('/call/payment', methods=['GET'])
def call_payment():
    chk_ses_id = request.args.get('session_id')
    checkout_session = stripe.checkout.Session.retrieve(id=chk_ses_id)
    sub = stripe.Subscription.retrieve(id=checkout_session.subscription)
    if sub.status == "active":
        user = User.query.get(checkout_session.metadata["user_id"])
        user.plan = {str(checkout_session.metadata["ins_type"]): { "c": 1, "s": int(checkout_session.metadata["students"]), "t": int(checkout_session.metadata.get("team")), "d": checkout_session.metadata["duration"]}}
        user.stripe_sub_id = checkout_session.subscription
        stripe.Subscription.modify(checkout_session.subscription, metadata=checkout_session.metadata)
        db.session.commit()
        return APIResponse.success("Plan updated successfully", 200)
    else:
        return APIResponse.success("Something went wrong with payment, Please contact technical support", 403)

