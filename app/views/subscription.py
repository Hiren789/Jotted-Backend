from flask import request, redirect, jsonify
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
    
    try:
        kk = stripe.Customer.retrieve(user.stripe_cus_id)
        if "deleted" in kk:
            assert kk["deleted"] == False
    except:
        tmpcus = stripe.Customer.create(email=user.email, name=f"{user.fn} {user.ln}")
        user.stripe_cus_id = tmpcus["id"]
        db.session.commit()
    
    itt = list(plan.keys())[0]
    ppi = search_for_price(int(itt), plan[itt]["s"], plan[itt]["d"], team=plan[itt].get("t"))

    if user.stripe_sub_id:
        try:
            sub = stripe.Subscription.retrieve(user.stripe_sub_id)
            sub_item_id = dict(sub)["items"]["data"][0]["id"]
            stripe.SubscriptionItem.modify(sub_item_id, price = ppi, quantity = int(plan[itt]["c"]))
            sub = stripe.Subscription.retrieve(user.stripe_sub_id)
            if sub.status == "active":
                return APIResponse.success("Plan updated successfully", 200)
            elif sub.status == "past_due":
                return APIResponse.success("Success", 200, redirect=True, url=stripe.Invoice.retrieve(sub.latest_invoice).hosted_invoice_url)
                return redirect(stripe.Invoice.retrieve(sub.latest_invoice).hosted_invoice_url)
        except:
            pass

    checkout_session = stripe.checkout.Session.create(
        customer=user.stripe_cus_id,
        line_items=[
            {
                'price': ppi, "quantity": int(plan[itt]["c"])
            },
        ],
        metadata = {"user_id": current_user, "ins_type": itt, "students": plan[itt]["s"], "duration": plan[itt]["d"], "team": plan[itt].get("t"), "count": plan[itt]["c"]},
        mode='subscription',
        success_url = app.config.get("BACKEND_URL") + '/call/payment?session_id={CHECKOUT_SESSION_ID}',
        cancel_url = app.config.get("BACKEND_URL") + '/cancel.html',
    )
    return APIResponse.success("Success", 200, redirect=True, url=checkout_session.url)
    return redirect(checkout_session.url)

@app.route('/cancel_subscription', methods=['POST'])
@jwt_required()
def cancel_subscription():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("Couldn't find a user account", 400)
    
    if user.stripe_sub_id:
        try:
            stripe.Subscription.delete(user.stripe_sub_id)
            return APIResponse.success("Cancellation successfull", 200)
        except:
            return APIResponse.error("Something went wrong", 403)
    else:
        return APIResponse.error("Subscription not found", 403)

@app.route('/call/payment', methods=['GET'])
def call_payment():
    return redirect("https://jottedonline.com/organizer-dashboard")
    return APIResponse.success("Plan updated successfully", 200)
    chk_ses_id = request.args.get('session_id')
    checkout_session = stripe.checkout.Session.retrieve(id=chk_ses_id)
    sub = stripe.Subscription.retrieve(id=checkout_session.subscription)
    if sub.status == "active":
        user = User.query.get(checkout_session.metadata["user_id"])
        user.plan = {str(checkout_session.metadata["ins_type"]): { "c": int(checkout_session.metadata["count"]), "s": int(checkout_session.metadata["students"]), "t": int(checkout_session.metadata.get("team")), "d": checkout_session.metadata["duration"]}}
        user.stripe_sub_id = checkout_session.subscription
        stripe.Subscription.modify(checkout_session.subscription, metadata=checkout_session.metadata)
        db.session.commit()
        return APIResponse.success("Plan updated successfully", 200)
    else:
        return APIResponse.success("Something went wrong with payment, Please contact technical support", 403)

@app.route('/webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, app.config.get("STRIPE_ENDPOINT_SECRET")
        )
    except ValueError as e:
        raise e
    except stripe.error.SignatureVerificationError as e:
        raise e

    if event['type'] == 'customer.subscription.deleted':
        stripe_cus_id = event['data']['object']['customer']
        user = User.query.filter_by(stripe_cus_id = stripe_cus_id).first()
        if user:
            user.stripe_sub_id = None
            user.plan = {"0": {"c": 1, "d": "m", "s": 10}}
            db.session.commit()

    elif event['type'] == 'customer.subscription.updated':
        stripe_cus_id = event['data']['object']['customer']
        user = User.query.filter_by(stripe_cus_id = stripe_cus_id).first()
        if user:
            if event['data']['object']['status'] == "active":
                user.stripe_sub_id = event['data']['object']['id']
                md = event['data']['object']['items']['data'][0]['price']['metadata']
                qty = event['data']['object']['items']['data'][0]['quantity']
                user.plan = {str(md["ins_type"]): {"c": int(qty), "d": md["recurring"], "s": int(md["students"]), "t": int(md.get("team", 0))}}
                db.session.commit()
            else:
                user.plan = {"0": {"c": 1, "d": "m", "s": 10}}
                db.session.commit()

    return jsonify(success=True)