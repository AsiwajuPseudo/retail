from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_utils import keccak, to_bytes, to_int
from eth_account.messages import encode_defunct
import json
import time
import secrets
import os

class Wallet:
    def __init__(self):
        # Set wallet address
        acc,ky=self._load('../keys.json')
        self.account_address = acc
        self.account_key = ky

        networks=[
            {'network':'Abitrum One','rpc':'https://arb-mainnet.g.alchemy.com/v2/55OWPHL5xT8wdS_8gqR3Xn3kBoYhNZnq','contract':'0xaf88d065e77c8cC2239327C5EDb3A432268e5831','gas_price':4000},
            #{'network':'Polygon','rpc':'https://polygon-mainnet.g.alchemy.com/v2/55OWPHL5xT8wdS_8gqR3Xn3kBoYhNZnq','contract':'0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359','gas_price':0.7},
            #{'network':'Polygon Amoy','rpc':'https://polygon-amoy.g.alchemy.com/v2/55OWPHL5xT8wdS_8gqR3Xn3kBoYhNZnq','contract':'0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582','gas_price':0.7}
        ]

        erc20_abi = '../TetherToken.json'
        
        with open(erc20_abi) as file:
            erc_json = json.load(file)
            erc_abi = erc_json

        self.ercs=[]
        for net in networks:
            rpc_handle = Web3(Web3.HTTPProvider(net['rpc']))
            rpc_handle.middleware_onion.inject(ExtraDataToPOAMiddleware,layer=0)
            contract = rpc_handle.eth.contract(address=net['contract'], abi=erc_abi)
            print('Network=> '+ net['network'] + '; Symbol ' + contract.functions.symbol().call()+'; Balance: '+str(contract.functions.balanceOf(self.account_address).call()))
            self.ercs.append({'network':net['network'],'handle':rpc_handle,'contract':contract,'price':net['gas_price']})

    #load keys from file
    def _load(self, key_file):
        try:
            with open(key_file, "r") as f:
                data = json.load(f)
                return data.get("address"), data.get("key")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    def getBalance(self, address, network):
        handle=next(net['handle'] for net in self.ercs if net['network']==network)
        bal = float(handle.eth.get_balance(address)/(10**18))
        return bal

    def balance(self,address, network):
        handle=next(net['handle'] for net in self.ercs if net['network']==network)
        contract=next(net['contract'] for net in self.ercs if net['network']==network)
        bal = contract.functions.balanceOf(address).call()
        return bal/1000000

    def deposit(self, receiver, amount, network):
        # Deposit money into user address
        try:
            #j
            handle=next(net['handle'] for net in self.ercs if net['network']==network)
            contract=next(net['contract'] for net in self.ercs if net['network']==network)
            gas_price_wei = handle.eth.gas_price
            nonce = handle.eth.get_transaction_count(self.account_address)
            tx_meta = {'from': self.account_address, 'nonce': nonce}
            tx = contract.functions.transfer(receiver, amount).build_transaction(tx_meta)
            signed_tx = handle.eth.account.sign_transaction(tx, private_key=self.account_key)
            process = handle.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = handle.eth.wait_for_transaction_receipt(process)
            if receipt['status'] == 1:
                return 'success'
            else:
                print(f"Transaction failed. Receipt: {receipt}")
                return 'Failed to send, try again'
        except Exception as e:
            err = str(e)
            if 'insufficient' in err:
                return 'Insufficient gas on the admin account, contact admin'
            else:
                print(err)
                return str(err)

    def send(self, sender, key, receiver, amount, network):
        # Send money from user address #1,889,280,001,889,280. #1,000,000,000,000,000.
        try:
            #g
            handle=next(net['handle'] for net in self.ercs if net['network']==network)
            contract=next(net['contract'] for net in self.ercs if net['network']==network)
            gas_price_wei = handle.eth.gas_price
            nonce = handle.eth.get_transaction_count(sender)
            tx_meta = {'from': sender, 'nonce': nonce}
            tx = contract.functions.transfer(receiver, amount).build_transaction(tx_meta)
            signed_tx = handle.eth.account.sign_transaction(tx, private_key=key)
            process = handle.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt= handle.eth.wait_for_transaction_receipt(process)
            if receipt['status'] == 1:
            	return 'success'
            else:
            	print(f"Transaction failed. Receipt: {receipt}")
            	return 'Failed to send, try again'
        except Exception as e:
            err = str(e)
            if 'insufficient' in err:
                return 'Insufficient gas, you should buy some gas'
            else:
                print(err)
                return str(err)

    def gasfilling(self, tank, amount, network):
        # by gas for a user
        try:
        	#first send money for gas
            handle=next(net['handle'] for net in self.ercs if net['network']==network)
            price=next(net['price'] for net in self.ercs if net['network']==network)
            am=amount/price
            amount_to_send = handle.to_wei(am, 'ether')
            gas_nonce = handle.eth.get_transaction_count(self.account_address)
            gas=estimate = handle.eth.estimate_gas({'from': self.account_address, 'to':tank, 'value': amount_to_send})
            tx_gas = {'from': self.account_address, 'to':tank,'value':amount_to_send, 'nonce': gas_nonce,'gas':int(gas*1.1),'gasPrice':int(handle.eth.gas_price*1.1),'chainId':handle.eth.chain_id}
            signed_gas = handle.eth.account.sign_transaction(tx_gas, private_key=self.account_key)
            spend_gas = handle.eth.send_raw_transaction(signed_gas.raw_transaction)
            spend_receipt= handle.eth.wait_for_transaction_receipt(spend_gas)
            if spend_receipt['status'] == 1:
                print("Gas fee was sent successfuly")
                return "success"
            else:
                print(f"Transaction failed. Receipt: {spend_receipt}")
                return 'Failed to acquire gas, try again'
        except Exception as e:
        	print('Gas error: ' + str(e))
        	return str(e)

    def approve(self, owner, key, amount, network):
        # Approve spender to spend user funds
        try:
        	#h
            handle=next(net['handle'] for net in self.ercs if net['network']==network)
            contract=next(net['contract'] for net in self.ercs if net['network']==network)
            nonce = handle.eth.get_transaction_count(owner)
            tx_meta = {'from': owner, 'nonce': nonce}
            tx = contract.functions.approve(self.account_address, amount).build_transaction(tx_meta)
            signed_tx = handle.eth.account.sign_transaction(tx, private_key=key)
            process = handle.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = handle.eth.wait_for_transaction_receipt(process)
            if receipt['status'] == 1:
                return "success"
            else:
                print(f"Failed to grant approval {receipt}")
                return 'Failed to grant approval'
        except Exception as e:
        	print(str(e))
        	return str(e)

    def approve_for(self, owner, key, spender, amount, network):
        # Approve spender to spend user funds
        try:
        	#approved
            handle=next(net['handle'] for net in self.ercs if net['network']==network)
            contract=next(net['contract'] for net in self.ercs if net['network']==network)
            nonce = handle.eth.get_transaction_count(owner)
            tx_meta = {'from': owner, 'nonce': nonce}
            tx = contract.functions.approve(spender, amount).build_transaction(tx_meta)
            signed_tx = handle.eth.account.sign_transaction(tx, private_key=key)
            process = handle.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = handle.eth.wait_for_transaction_receipt(process)
            if receipt['status'] == 1:
                return "success"
            else:
                print(f"Failed to grant approval {receipt}")
                return 'Failed to grant approval'
        except Exception as e:
        	print(str(e))
        	return str(e)
