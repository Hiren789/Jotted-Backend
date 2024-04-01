import stripe
stripe.api_key = "sk_test_51NP43WSBKP7HWVq0kCR9blgLUuCcR7A0hrRJoKFGWGfquNB9jVEixwcNPaKWfIPDy3LpRk6mODq5zePgWmQq3k4a00LMWbEwyC"

print(stripe.Invoice.upcoming(customer="cus_Po3RRyv3HTr9Jm"))

exit()

# # Set your secret key. Remember to switch to your live secret key in production.
# # See your keys here: https://dashboard.stripe.com/apikeys
# import stripe
# stripe.api_key = "sk_test_51NP43WSBKP7HWVq0kCR9blgLUuCcR7A0hrRJoKFGWGfquNB9jVEixwcNPaKWfIPDy3LpRk6mODq5zePgWmQq3k4a00LMWbEwyC"


# kk = stripe.Customer.create(
#   email="hirensavaliya24601@gmail.com",
#   name="Hiren Savaliya"
# )

# print(kk)



# kk = stripe.Price.create(
#   currency="usd",
#   unit_amount=1000,
#   recurring={"interval": "month"},
#   product_data={"name": "Basic Individual"},
#   metadata={"type":"individual","students":1000}
# )

# print(kk)

# price_1Owx2XSBKP7HWVq0mZ5duX6K


# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
# stripe.api_key = 'sk_test_51NP43WSBKP7HWVq0kCR9blgLUuCcR7A0hrRJoKFGWGfquNB9jVEixwcNPaKWfIPDy3LpRk6mODq5zePgWmQq3k4a00LMWbEwyC'

# subscription = stripe.Subscription.create(
#     customer="cus_PmVq13nGcPA3EK",
#     items=[{
#         'price': "price_1Owx2XSBKP7HWVq0mZ5duX6K",
#     }],
#     payment_behavior='default_incomplete',
#     payment_settings={'save_default_payment_method': 'on_subscription'},
#     expand=['latest_invoice.payment_intent'],
# )

# print(subscription)


# checkout_session = stripe.checkout.Session.create(
#         customer="cus_PmVq13nGcPA3EK",
#         line_items=[
#             {
#                 'price': "price_1Owx2XSBKP7HWVq0mZ5duX6K", "quantity": 1
#             },
#         ],
#         mode='subscription',
#         success_url="http://localhost:5000" + '/call/payment?session_id={CHECKOUT_SESSION_ID}',
#         cancel_url="http://localhost:5000" + '/cancel.html',
#     )

# print(checkout_session)



# def calculate_price(it, s, t, d):
#     pricing = {0: {"s": {10: 0, 30: 5, 150: 10, 10000000: 25}},
#            1: {"s": {30: 15, 50: 25, 100: 40, 250: 75, 500: 150, 1000: 300, 1500: 450, 2000: 600, 2500: 750, 3000: 1000, 3500: 1250, 4000: 1500, 4500: 1750, 5000: 2000, 6000: 2700, 7000: 3400, 8000: 4100, 9000: 4800, 10000: 5500, 12500: 7250, 15000: 9000, 10000000: 12500},
#                "sf": {30: 5, 50: 5, 100: 8, 250: 10, 500: 15, 1000: 25, 1500: 25, 2000: 25, 2500: 30, 3000: 30, 3500: 30, 4000: 30, 4500: 30, 5000: 50, 6000: 50, 7000: 50, 8000: 75, 9000: 75, 10000: 100, 12500: 125, 15000: 150, 10000000: 150},
#                "sa": {5: 5, 8: 5, 10: 5, 15: 5, 25: 5, 30: 5, 50: 7.50, 75: 7.50, 100: 10, 125: 10, 150: 10, 10000000:0}}}

#     discounts = {0: {"m": 1, "1y": 10/12},
#                 1: {"m": 1, "1y": 0.9, "2y": 0.85, "3y": 0.8},
#                 2: {"m": 1, "1y": 12, "2y": 24, "3y": 36}}
#     if it not in pricing:
#         return "Invalid institute type"
#     if s not in pricing[it]["s"]:
#         return "Invalid Students count"
#     if d not in discounts[it]:
#         return "Invalid Duration"
#     k = discounts[it][d]
#     price = pricing[it]["s"][s]
#     if it == 1:
#         if t not in pricing[it]["sa"]:
#             return "Invalid Team Member Count"
#         if pricing[it]["sf"][s] <= t:
#             price += 1000 if t == 10000000 else (
#                 t-pricing[it]["sf"][s])*pricing[it]["sa"][pricing[it]["sf"][s]]
#     price *= discounts[2][d]
#     data = {"origional_price":int(price), "discounted_price":int(price*k), "price_per_month_per_student":round(price*k/(discounts[2][d]*s), 2), "price_per_year_per_student":round(price*k*12/(discounts[2][d]*s), 2)}
#     return data


# session_id = "cs_test_a1PgZz4HFcCBDyno7ZImSFMPz49KZUFGHMSs2nZWbq2A4UzhAY5xeoTAop"

# checkout_session = stripe.checkout.Session.retrieve(id=session_id)
# print(checkout_session)
sub = stripe.Subscription.retrieve(id="sub_1OxbFiSBKP7HWVq0fwplelI0")
if sub.status == "past_due":
    print(stripe.Invoice.retrieve(sub.latest_invoice))
    # print(sub.latest_invoice)
    print("PAST DUE")
print(sub.status)

# sub_item_id = dict(sub)["items"]["data"][0]["id"]
# sub = stripe.SubscriptionItem.modify()
# sub.modify()

#         customer="cus_PmVq13nGcPA3EK",
#         line_items=[
#             {
#                 'price': "price_1Owx2XSBKP7HWVq0mZ5duX6K", "quantity": 1
#             },
#         ],
#         mode='subscription',
#         success_url="http://localhost:5000" + '/call/payment?session_id={CHECKOUT_SESSION_ID}',
#         cancel_url="http://localhost:5000" + '/cancel.html',
#     )

# print(checkout_session)