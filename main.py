from flask import Flask, jsonify, request, send_from_directory
from web3.middleware import ExtraDataToPOAMiddleware
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename
from eth_account import Account
from datetime import datetime
from flask_cors import CORS
from web3 import Web3
import requests
import uuid
import os

from auth import auth
from utils import Utils
from admin import Admin
from wallet import Wallet
from market import Market
from payment import Payment
from database import Database
from verification import Verification
from notifications import Notifications

app = Flask(__name__)
CORS(app)

admin=Admin()
wallet=Wallet()
market=Market()
database= Database()
verify= Verification()
notify= Notifications()

@app.route('/ping', methods=['GET'])
def ping():
    return {'status':'running'}


# ========================
# User Registration & Login
# ========================

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    private_key = os.urandom(32).hex()
    account = Account.from_key(private_key)
    required = ["name", "surname", "address", "email", "phone", "password"]
    if not all(k in data for k in required):
        raise BadRequest("Missing fields")

    success = database.register_user(
        data["name"], data["surname"], data["address"],
        data["email"], data["phone"], data["password"],
        account.address, private_key
    )
    if success['status']=='Email already exists':
        return jsonify({"error": "Email already exists"}), 400
    else:
        token = auth.generate_token(success['user_id'])
        success['token']=token
        return success, 201

@app.route("/admin_register", methods=["POST"])
def admin_register():
    data = request.json
    required = ["name", "surname", "email", "password"]
    if not all(k in data for k in required):
        raise BadRequest("Missing fields")

    check=admin.check(data['user_id'])
    if check==False:
        return {'status':'Unauthorised access'}

    success = admin.register_user(data["name"], data["surname"],data["email"], data["password"] )
    if success:
        return {"status": "success"}
    else:
        return {"status": "Email already exists"}

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user_id = database.login_user(data.get("email"), data.get("password"))
    if user_id['status'] =='Incorrect password' or user_id['status'] =='Email does not exist':
        return jsonify({"error": user_id['status']}), 401
    else:
        token = auth.generate_token(user_id)
        return jsonify({"status": "Login successful","token":token, "user_id": user_id['status'][0],'name':user_id['status'][1]}), 200

@app.route("/admin_login", methods=["POST"])
def admin_login():
    data = request.json
    user_id = admin.login_user(data.get("email"), data.get("password"))
    if user_id['status'] =='Incorrect password' or user_id['status'] =='Email does not exist':
        return jsonify({"error": user_id['status']}), 401
    else:
        return jsonify({"status": "Login successful", "user_id": user_id['status'][0],'name':user_id['status'][1]}), 200


@app.route("/account/<user_id>", methods=["GET"])
def account_full(user_id):
    u=database.account(user_id)
    return {'name':u[0],'surname':u[1],'email':u[2], 'phone': u[3], 'verification':u[4]}

@app.route("/update_account", methods=["POST"])
@auth.jwt_required()
def update_account(decoded_token):
    data = request.json
    up = database.update_account(data.get("user_id"), data.get("name"),data.get("surname"), data.get("email"), data.get("phone"))
    return up

@app.route("/change_password", methods=["POST"])
@auth.jwt_required()
def change_password(decoded_token):
    data = request.json
    up = database.change_password( data.get("user_id"), data.get("old"), data.get("new_pass"))
    return up


@app.route("/verification", methods=["POST"])
def verification():
    data = request.json
    check=admin.check(data.get("admin_id"))
    result=data.get('result')
    if check==True:
        if result=='success':
            up = database.verify(data.get("user_id"))
            verify.finish(data.get("user_id"))
            return up
        else:
            deli=verify.delete_verification_data(data.get("user_id"))
            return deli
    else:
        return {'status':'Unauthorised access'}


@app.route("/delete_verification", methods=["POST"])
def delete_verification():
    data = request.json
    check=admin.check(data.get("admin_id"))
    if check==True:
        deli=verify.delete_verification_data(data.get("user_id"))
        return deli
    else:
        return {'status':'Unauthorised access'}

@app.route("/delete_account", methods=["POST"])
def delete_account():
    data = request.json
    check=admin.check(data.get("admin_id"))
    if check==True:
        up = database.delete_account(data.get("user_id"))
        return up
    else:
        return {'status':'Unauthorised access'}

# ========================
# Admin methods
# ========================


@app.route("/all_admins/<user_id>", methods=["GET"])
def all_admins(user_id):
    check=admin.check(user_id)
    if check==True:
        a=admin.admins()
        return [{'id':i[0],'name':i[1],'surname':i[2], 'email':i[3]} for i in a]
    else:
        return []

@app.route("/delete_admin", methods=["POST"])
def delete_admin():
    data = request.json
    user_id=data.get('user_id')
    admin_id=data.get('admin_id')
    check=admin.check(user_id)
    if check==True:
        admin.delete_admin(admin_id)
        return {'status':'success'}
    else:
        return {'status': 'Unauthorised access'}

@app.route("/all_users/<user_id>", methods=["GET"])
def all_users(user_id):
    check=admin.check(user_id)
    if check==True:
        a=database.user_accounts()
        return [{ 'id':u[0], 'name':u[1], 'surname':u[2], 'email':u[4], 'fiat': u[10], 'tether': u[11], 'verified':u[9]} for u in a ]
    else:
        return []

@app.route("/all_noti/<user_id>", methods=["GET"])
def all_notifications(user_id):
    if admin.check(user_id):
        raw_notifications = notify.admin_noti()
        noti_dict = {}
        viewed_counts = {}
        for noti in raw_notifications:
            noti_id, stamp, content, viewed = noti
            if noti_id not in noti_dict:
                noti_dict[noti_id] = {'id': noti_id,'stamp': stamp,'content': content,'viewed': viewed}

            # Count the number of times viewed is 'true'
            if viewed.lower() == 'true':
                viewed_counts[noti_id] = viewed_counts.get(noti_id, 0) + 1

        # Merge viewed_true_count into the notification dict
        result = []
        for noti_id, data in noti_dict.items():
            data['viewed_true_count'] = viewed_counts.get(noti_id, 0)
            result.append(data)

        return result
    else:
        return []

@app.route("/add_noti", methods=["POST"])
def add_notification():
    data = request.json
    content=data.get('content')
    admin_id=data.get('admin_id')
    check=admin.check(admin_id)
    if check==True:
        id_=str(uuid.uuid4())
        users=database.user_accounts()
        for i in users:
            notify.add(id_, i[0], content, 'admin')
        return {'status':'success'}
    else:
        return {'status': 'Unauthorised access'}

@app.route("/delete_noti", methods=["POST"])
def delete_notification():
    data = request.json
    id_=data.get('noti_id')
    admin_id=data.get('admin_id')
    check=admin.check(admin_id)
    if check==True:
        notify.delete_noti(id_)
        return {'status':'success'}
    else:
        return {'status': 'Unauthorised access'}

# ========================
# Balance Endpoint
# ========================

@app.route("/balances/<user_id>", methods=["GET"])
def balances(user_id):
    balances = database.get_balances(user_id)
    if balances:
        return jsonify({
            "fiat": balances[0],
            "tether": balances[1]
        })
    else:
        return jsonify({"error": "User not found"}), 404

# ========================
# Deposit and Withdraw Cash
# ========================

@app.route("/available_balances", methods=["GET"])
def available_balances():
    balances = database.get_total_balances()
    if balances:
        return jsonify({
            "fiat": balances[0],
            "tether": balances[1]
        })
    else:
        return jsonify({"error": "User not found"}), 404

@app.route("/user_balance/<user_id>", methods=["GET"])
def user_wallet(user_id):
    balance=database.get_balances(user_id)
    return { 'fiat':balance[0], 'tether':balance[1] }

@app.route("/user_noti/<user_id>", methods=["GET"])
def user_notifications(user_id):
    n=notify.user_noti(user_id)
    noti=[i[1] for i in n]
    return noti

@app.route("/wallet/<user_id>", methods=["GET"])
def wallet_user(user_id):
    dep=database.get_user_deposits(user_id)
    wit=database.get_user_withdrawals(user_id)
    deposits=[{'amount':row[2],'status':'closed','date':row[3],'type':'deposit'} for row in dep]
    withdrawls=[{'amount':row[5],'status':row[6],'date':row[7], 'type':'withdraw'} for row in wit]
    deposits.extend(withdrawls)
    return deposits

@app.route("/deposit", methods=["POST"])
@auth.jwt_required()
def deposit(decoded_token):
    data = request.get_json()
    amount=float(data.get('amount'))
    user_id=data.get('user_id')
    email="admin@retailbets.com"
    pay=Payment()
    method=data.get('method')
    phone=data.get('phone')
    items=[{'name':'deposit','price':amount}]
    go=pay.mobile(user_id, email, phone, method, items)
    return {'status':'success'}

@app.route("/admin_deposit", methods=["POST"])
def admin_deposit():
    data = request.get_json()
    amount=float(data.get('amount'))
    user_id=data.get('user_id')
    admin_id=data.get('admin_id')
    check=admin.check(admin_id)
    if check==False:
        return {'status':'Unauthorised access'}
    database.deposit_fiat(user_id, amount)
    return {'status':'success'}

@app.route('/finish_deposit', methods=['GET'])
def finish_deposit():
    user_id=request.args.get('user_id')
    pay=Payment()
    logs=pay.check_status(user_id)
    processed=0
    for log in logs:
        try:
            amount=float(log['amount'])
            database.deposit_fiat(user_id, amount)
            processed=processed+1
        except Exception as e:
            print('Error with transaction:'+str(e))

    return {'status':'success','i':processed}


@app.route("/withdraw", methods=["POST"])
@auth.jwt_required()
def withdraw(decoded_token):
    data = request.json
    user_id = data.get("user_id")
    amount = float(data.get("amount"))
    account=data.get('account')
    bank=data.get('bank')
    method=data.get('method')
    #take withdrawal charges
    if method=='bank':
        new_amount=amount*0.965
    else:
        new_amount=amount*0.955
    success = database.withdraw_fiat(user_id, method, bank, account, new_amount, amount)
    if success:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"error": "Insufficient funds"}), 400


@app.route("/withdrawals/<user_id>", methods=["GET"])
def withdrawals(user_id):
    check=admin.check(user_id)
    if check==True:
        w=database.withdrawals()
        pending= [{'id':i[0], 'user_id':i[1], 'method':i[2],'bank':i[3],'amount':i[5],'date':i[7],'account':i[4]} for i in w if i[6]=='open']
        closed=[{'id':i[0], 'user_id':i[1], 'method':i[2],'bank':i[3],'amount':i[5],'date':i[7],'account':i[4]} for i in w if i[6]=='closed']
        return {'pending':pending,'closed':closed}
    else:
        return {'pending':[],'closed':[]}

@app.route("/process_withdraw/<user_id>/<id_>", methods=["GET"])
def process_withdraw(user_id,id_):
    check=admin.check(user_id)
    if check==True:
        database.withdraw_process(id_)
        i=str(uuid.uuid4())
        notify.add(i, id_, 'Your withdrawal request was processed, you should receive your money through the payment option your selected.', 'system')
        return {'status':'success'}
    else:
        return {'status':'Unauthorised access'}



# ========================
# Send / Receive Crypto
# ========================


@app.route("/networks/<user_id>", methods=["GET"])
def networks(user_id):
    nets=[network['network'] for network in wallet.ercs]
    acc=database.user_account(user_id)
    return jsonify({'networks':nets,'address':acc[0]})

@app.route("/deposit_crypto", methods=["POST"])
@auth.jwt_required()
def deposit_crypto(decoded_token):
    data = request.json
    required = ["user_id", "network"]
    if not all(k in data for k in required):
        raise BadRequest("Missing order fields")

    user_id = data["user_id"]
    network = data["network"]
    acc=database.user_account(user_id)
    bal=wallet.balance(acc[0],network)
    if bal<=0:
        return jsonify({'error':'No deposit yet, try again after sending to the address.'}),400
    #send
    am=bal*1000000
    gas_bal=wallet.getBalance(acc[0], network)
    if gas_bal<0.01:
        gas=wallet.gasfilling(acc[0],0.02, network)
        if gas!='success':
            return jsonify({'error':gas}),402
    #send
    send=wallet.send(acc[0], acc[1],wallet.account_address,int(am), network)
    if send!='success':
        return jsonify({'error':send}),401
    #update crypto balance
    database.deposit_tether(user_id,bal)
    return jsonify({'status':'success'}),200

@app.route("/send_crypto", methods=["POST"])
@auth.jwt_required()
def send_crypto(decoded_token):
    data = request.json
    required = ["user_id", "address", "amount","network"]
    if not all(k in data for k in required):
        raise BadRequest("Missing order fields")

    user_id = data["user_id"]
    receiver = data["address"]
    amount = float(data["amount"])
    network = data["network"]
    acc=database.get_balances(user_id)
    if amount<=0:
        return jsonify({'error':'Amount is below minimum'}),400
    #send
    if acc[1]>=amount:
        am=amount*1000000
        send=wallet.send( wallet.account_address, wallet.account_key, receiver,int(am), network)
        if send!='success':
            return jsonify({'error':send}),401
        #remove money from crypto balance
        database.withdraw_tether(user_id, amount)
        return jsonify({'status':'success'}),200
    else:
        return jsonify({'error':'Insuficient crypto balance'}),400

# ========================
# Orders (Buy/Sell)
# ========================

@app.route("/order", methods=["POST"])
@auth.jwt_required()
def place_order(decoded_token):
    data = request.json
    required = ["user_id", "mode", "amount", "ticker"]
    if not all(k in data for k in required):
        raise BadRequest("Missing order fields")

    user_id = data["user_id"]
    order_type = data["mode"]
    amount = float(data["amount"])
    price = float(data["price"])
    ticker= data['ticker']
    is_market_order = data.get("is_market_order")

    if is_market_order=='limit' and price <= 0:
        return {'status':'Invalid price for this order type'}
    elif amount <=0 :
        return {'status':'Invalid amount'}

    market_maker=database.is_market_maker(user_id)
    total_placed=amount*price
    #add collective orders
    past_orders=[]
    if order_type=='buy':
        past_orders=database.get_user_buy_orders(user_id)
    elif order_type=='sell':
        past_orders=database.get_user_sell_orders(user_id)
    for n in past_orders:
        total_placed=total_placed+(n[4]*n[3])
    #check limit
    if not market_maker and total_placed > 1000:
        return {'status':'Total order volume reached, your total orders can not be more than $500 in total.'}

    order = database.place_order(user_id, order_type, amount, price, is_market_order)
    if order['status']=='success':
        #calculate price
        orders_=database.get_all_orders()
        sell_orders=[[i[4],i[3]] for i in orders_ if i[2]=='sell' and i[6]=='open']
        buy_orders=[[i[4],i[3]] for i in orders_ if i[2]=='buy' and i[6]=='open']
        if len(sell_orders)==0 and len(buy_orders)>0:
            price=buy_orders[0][0]
        elif len(buy_orders)==0 and len(sell_orders)>0:
            price=sell_orders[len(sell_orders)-1][0]
        elif len(buy_orders)>0 and len(sell_orders)>0:
            #mid-price
            price=((sell_orders[len(sell_orders)-1][0]-buy_orders[0][0])/2) + buy_orders[0][0]
        #no need for else
        market.add_price(ticker, price)
    return order

@app.route("/cancel_order", methods=["POST"])
@auth.jwt_required()
def cancel_order(decoded_token):
    data = request.json
    required = ["user_id", "order_id"]
    if not all(k in data for k in required):
        raise BadRequest("Missing order fields")

    user_id = data["user_id"]
    order_id = data["order_id"]
    ticker=data["ticker"]
    database.cancel_order(user_id,order_id)
    #update market price
    orders_=database.get_all_orders()
    sell_orders=[[i[4],i[3]] for i in orders_ if i[2]=='sell' and i[6]=='open']
    buy_orders=[[i[4],i[3]] for i in orders_ if i[2]=='buy' and i[6]=='open']
    price=0
    if len(sell_orders)==0 and len(buy_orders)>0:
        price=buy_orders[0][0]
    elif len(buy_orders)==0 and len(sell_orders)>0:
        price=sell_orders[len(sell_orders)-1][0]
    elif len(buy_orders)>0 and len(sell_orders)>0:
        #mid-price
        price=((sell_orders[len(sell_orders)-1][0]-buy_orders[0][0])/2) + buy_orders[0][0]
    #no need for else
    if price!=0:
        market.add_price(ticker, price)
    return {'status':'success'}

@app.route('/orders/<ticker>/<user_id>', methods=['GET'])
def user_orders(ticker,user_id):
    bids_=database.get_user_buy_orders(user_id)
    asks_=database.get_user_sell_orders(user_id)
    bids=[{'id':i[0],'time':i[7],'price':i[4],'volume':i[3]} for i in bids_ if i[6]=='open']
    asks=[{'id':i[0],'time':i[7],'price':i[4],'volume':i[3]} for i in asks_ if i[6]=='open']
    filled=[{'id':i[0],'time':i[7],'price':i[4],'volume':i[3]} for i in asks_ if i[6]=='filled']
    return jsonify({ 'asks': asks, 'bids': bids, 'filled': filled })

@app.route('/tether_orders/<ticker>', methods=['GET'])
def tether_orders(ticker):
    orders_=database.get_all_orders()
    sell_orders=[[i[4],i[3]] for i in orders_ if i[2]=='sell' and i[6]=='open']
    buy_orders=[[i[4],i[3]] for i in orders_ if i[2]=='buy' and i[6]=='open']
    asks=Utils.group_orderbook_levels(sell_orders,0.01)
    bids=Utils.group_orderbook_levels(buy_orders, 0.01)
    return {'asks':asks,'bids':bids}

@app.route('/tether_market/<ticker>', methods=['GET'])
def tether_market(ticker):
    data=market.get_market_data(ticker)
    data=[{'price':i[0],'timestamp':i[1]} for i in data]
    candles=Utils.get_candlesticks(data)
    return candles

@app.route('/tether_data/<ticker>', methods=['GET'])
def tether_data(ticker):
    return {'ticker':ticker,'name':'USD Tether'}




#=====================
# Verification
#=====================

@app.route('/upload', methods=['POST'])
@auth.jwt_required()
def upload_id(decoded_token):
    data = request.json
    id_file = data['id_file']
    selfie = data['selfie']
    national_id = data.get('national_id')
    user_id = data.get('user_id')

    profile = database.account(user_id)
    if not profile:
        return {'status': 'Invalid user'}

    name = profile[0]
    surname = profile[1]
    add = verify.start(user_id, name, surname, national_id, id_file, selfie)
    if add:
        return {'status': 'success'}
    else:
        return {'status': 'Verification files already exist, wait for response first.'}

@app.route('/all_verifications/<user_id>', methods=['GET'])
def all_verifications(user_id):
    check=admin.check(user_id)
    if check==True:
        a=verify.all()
        return [{'id':i[0],'name':i[1],'surname':i[2], 'national_id':i[3], 'id_file':i[4],'selfie':i[5]} for i in a]
    else:
        return []

@app.route('/view/<filename>')
def view_id(filename):
    return send_from_directory('../verify', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port='8080')
