import pickle
import os
import time
from paynow import Paynow
import random

class Payment:
    def __init__(self):
        # Initialize Paynow
        self.paynow = Paynow('19677', 'dc1d13e5-4720-4769-b1b5-1dbd10ad8a61', 'http://google.com', 'http://google.com')
        self.poll_file = '../poll_data.pkl'
        if not os.path.exists(self.poll_file):
            with open(self.poll_file, 'wb') as f:
                pickle.dump([], f)

    def _load_poll_data(self):
        with open(self.poll_file, 'rb') as f:
            return pickle.load(f)

    def _save_poll_data(self, data):
        with open(self.poll_file, 'wb') as f:
            pickle.dump(data, f)

    def general(self, user_id, email, items):
        """Initiate a card payment."""
        order = 'Order #' + str(random.randint(10000000, 99999999))
        payment = self.paynow.create_payment(order, email)
        for item in items:
            payment.add(item.name, item.price)

        # Send transaction
        response = self.paynow.send(payment)
        if response.success:
            link = response.redirect_url
            poll_url = response.poll_url
            self._save_poll_entry(user_id, poll_url)
            return {'result': 'success'}
        else:
            return {'result': 'Error: could not create transaction'}

    def mobile(self, user_id, email, phone, method, items):
        """Initiate a mobile payment."""
        order = 'Order #' + str(random.randint(10000000, 99999999))
        payment = self.paynow.create_payment(order, email)
        total=0
        for item in items:
            payment.add(item['name'], item['price'])
            total=total+float(item['price'])

        # Send transaction
        response = self.paynow.send_mobile(payment, phone, method)
        if response.success:
            poll_url = response.poll_url
            self._save_poll_entry(user_id, poll_url, total)
            return {'result': 'success'}
        else:
            return {'result': 'Error: could not create transaction'}

    def _save_poll_entry(self, user_id, poll_url, amount):
        """Save a new poll entry."""
        poll_data = self._load_poll_data()
        poll_data.append({'user_id': user_id, 'poll_url': poll_url,'amount':amount, 'time': time.time()})
        self._save_poll_data(poll_data)

    def check_status(self, user_id):
        """Check the status of a user's transactions."""
        poll_data = self._load_poll_data()
        updated_poll_data = []
        current_time = time.time()
        results = []

        for entry in poll_data:
            if entry['user_id'] == user_id:
                poll_url = entry['poll_url']
                status = self.paynow.check_transaction_status(poll_url)

                if status.paid:
                    results.append({'poll_url': poll_url, 'status': 'success','amount':entry['amount']})
                elif current_time - entry['time'] > 300:
                    # Transaction expired (5 minutes)
                    continue
                else:
                    # Keep transaction for further checks
                    updated_poll_data.append(entry)
            else:
                updated_poll_data.append(entry)

        self._save_poll_data(updated_poll_data)

        return results
