# Bismuth Faucet Payout App
# Version 2.00
# Date 16/08/2018
# Copyright Maccaspacca 2017 to 2018
# Copyright The Bismuth Foundation 2016 to 2018
# Author Maccaspacca

from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import PKCS1_v1_5
from Cryptodome.Hash import SHA

import base64, time, sqlite3, sys, fprocs, json, platform, os

import logging
import configparser as cp

logging.basicConfig(level=logging.INFO, 
                    filename='payout.log', # log to this file
                    format='%(asctime)s %(message)s') # include timestamp

logging.info("logging initiated")

config = cp.ConfigParser()
config.read("faucetconfig.ini")
fpath = config.get('My Faucet','mydbpath')
frate = float(config.get('My Faucet','myrate'))
port = config.get('My Faucet', 'nodeport')
ip = config.get('My Faucet', 'nodeip')
wallet = config.get('My Bismuth', 'mywallet')

logging.info("Config file read completed")
config = None

my_os = platform.system()
my_os = my_os.lower()

myversion = "2.0.0" # hardcode the version

if "linux" in my_os:
	wallet = os.path.expanduser('{}'.format(wallet))
elif "windows" in my_os:
	pass
else: # if its not windows then probably a linux or unix variant
	pass
	
myversion = "2.0.0" # hardcode the version


def keys_load_new(wallet_file=wallet):
    # import keys

    with open (wallet_file, 'r') as wallet_file:
        wallet_dict = json.load (wallet_file)

    private_key_readable = wallet_dict['Private Key']
    public_key_readable = wallet_dict['Public Key']
    address = wallet_dict['Address']

    key = RSA.importKey(private_key_readable)
 
    # public_key_readable = str(key.publickey().exportKey())
    if (len(public_key_readable)) != 271 and (len(public_key_readable)) != 799:
        raise ValueError("Invalid public key length: {}".format(len(public_key_readable)))

    public_key_hashed = base64.b64encode(public_key_readable.encode('utf-8'))

    return key, public_key_readable, private_key_readable, public_key_hashed, address

(key, private_key_readable, public_key_readable, public_key_hashed, address) = keys_load_new(wallet)

def payees():
	pay = sqlite3.connect(fpath)
	pay.text_factory = str
	p = pay.cursor()
	p.execute("SELECT * FROM requesters WHERE paid = 'No';")
	tp = p.fetchall()
	pay.close()
	
	return tp
	
def dopaid():
	pay = sqlite3.connect(fpath)
	pay.text_factory = str
	p = pay.cursor()
	p.execute("UPDATE requesters SET paid = 'Yes' WHERE paid = 'No';")
	pay.commit()
	pay.close()
	
def payme():

	amount_input = frate
	operation_input = 0
	openfield_input = "faucet"
	fee = '%.8f' % float(0.01 + (float(len(openfield_input)) / 100000) + (float(operation_input) / 10))  # 0.1% + 0.01 dust

	paylist = []
	paylist = payees()
	
	if paylist:

		try:

			for d in paylist:
				d_check = fprocs.balcheck(address,ip,port,fpath,frate)				
				if d_check[0]:
					balance = d_check[1]
					recipient_input = str(d[1])
					print("{} is being be paid {} BIS, with {} fee".format(recipient_input,str(amount_input),str(fee)))
					logging.info("{} is being be paid {} BIS, with {} fee".format(recipient_input,str(amount_input),str(fee)))
					timestamp = '%.2f' % time.time()
				
					transaction = (str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input), str(operation_input), str(openfield_input))  # this is signed
					#print(str(transaction).encode("utf-8"))

					h = SHA.new(str(transaction).encode("utf-8"))
					signer = PKCS1_v1_5.new(key)
					signature = signer.sign(h)
					signature_enc = base64.b64encode(signature)
					txid = signature_enc[:56]
					mytxid = txid.decode("utf-8")
					logging.info("Transaction ID: {}".format(mytxid))
					
					verifier = PKCS1_v1_5.new(key)
					if verifier.verify(h, signature):
						if float(amount_input) < 0:
							logging.info("Signature OK, but cannot use negative amounts")

						elif (float(amount_input) + float(fee)) > float(balance):
							logging.info("Payout: Sending more than owned")

						else:
							logging.info("The signature is valid, proceeding to send the transaction to node")
							tx_submit = (str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input), str(signature_enc.decode("utf-8")), str(public_key_hashed), str(operation_input), str(openfield_input)) #float kept for compatibility
							#logging.info(tx_submit)
							
							reply = fprocs.tx_send(ip,port,tx_submit)
							
							logging.info(reply)
							logging.info("Transaction sent {} to node".format(mytxid))

					else:
						logging.info("Invalid signature")
					time.sleep(1)
					#enter transaction end
				else:
					logging.info("Not enough funds")

			dopaid()
			return True

		except Exception as e:
				logging.info("Payment Error {}".format(e))
				return False

	else:
		logging.info("No one to pay")
		print("No one to pay")
		return True
		
def updateme():

	time.sleep(5)
	bobble = payme()
	
	while bobble:
		print("Waiting for 60 minutes")
		time.sleep(3600)
		bobble = payme()

if __name__ == "__main__":
	updateme()
