# Bismuth Faucet Payout App
# Version 1.00
# Date 28/07/2017
# Copyright Maccaspacca 2017
# Copyright Hclivess 2016 to 2017
# Author Maccaspacca

from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
import base64, time, sqlite3, keys, sys

import logging
import configparser as cp

logging.basicConfig(level=logging.INFO, 
                    filename='payout.log', # log to this file
                    format='%(asctime)s %(message)s') # include timestamp

logging.info("logging initiated")

config = cp.ConfigParser()
config.read("faucet.ini")
fpath = config.get('My Faucet','mydbpath')
frate = float(config.get('My Faucet','myrate'))

(key, private_key_readable, public_key_readable, public_key_hashed, address) = keys.read()

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

	#get balance
	mempool = sqlite3.connect('mempool.db')
	mempool.text_factory = str
	m = mempool.cursor()
	m.execute("SELECT sum(amount) FROM transactions WHERE address = ?;", (address,))
	debit_mempool = m.fetchone()[0]
	mempool.close()
	if debit_mempool == None:
		debit_mempool = 0

	conn = sqlite3.connect('static/ledger.db')
	conn.text_factory = str
	c = conn.cursor()
	c.execute("SELECT sum(amount) FROM transactions WHERE recipient = ?;", (address,))
	credit = c.fetchone()[0]
	c.execute("SELECT sum(amount) FROM transactions WHERE address = ?;", (address,))
	debit = c.fetchone()[0]
	c.execute("SELECT sum(fee) FROM transactions WHERE address = ?;", (address,))
	fees = c.fetchone()[0]
	c.execute("SELECT sum(reward) FROM transactions WHERE address = ?;", (address,))
	rewards = c.fetchone()[0]
	c.execute("SELECT MAX(block_height) FROM transactions")
	bl_height = c.fetchone()[0]

	if debit == None:
		debit = 0
	if fees == None:
		fees = 0
	if rewards == None:
		rewards = 0
	if credit == None:
		credit = 0
	balance = credit - debit - fees + rewards - debit_mempool
	logging.info("Transaction address: {}".format(address))
	logging.info("Transaction address balance: {}".format(balance))
	#get balance

	amount_input = frate
	keep_input = 0
	openfield_input = ""
	fee = '%.8f' % float(0.01 + (float(amount_input) * 0.001) + (float(len(openfield_input)) / 100000) + (float(keep_input) / 10))  # 0.1% + 0.01 dust

	paylist = []
	paylist = payees()

	if paylist:

		try:

			for d in paylist:
				recipient_input = str(d[1])
				print("{} is being be paid {} BIS, with {} fee".format(recipient_input,str(amount_input),str(fee)))
				logging.info("{} is being be paid {} BIS, with {} fee".format(recipient_input,str(amount_input),str(fee)))
				timestamp = '%.2f' % time.time()
				transaction = (str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input), str(keep_input), str(openfield_input)) #this is signed
				#print transaction

				h = SHA.new(str(transaction).encode("utf-8"))
				signer = PKCS1_v1_5.new(key)
				signature = signer.sign(h)
				signature_enc = base64.b64encode(signature)
				logging.info("Encoded Signature: {}".format(signature_enc.decode("utf-8")))

				verifier = PKCS1_v1_5.new(key)
				if verifier.verify(h, signature) == True:
					if float(amount_input) < 0:
						logging.info("Signature OK, but cannot use negative amounts")

					elif (float(amount_input) > float(balance)):
						logging.info("Mempool: Sending more than owned")

					else:
						logging.info("The signature is valid, proceeding to save transaction to mempool")

						mempool = sqlite3.connect('mempool.db')
						mempool.text_factory = str
						m = mempool.cursor()

						m.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",(str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input),str(signature_enc.decode("utf-8")), str(public_key_hashed), str(keep_input), str(openfield_input)))
						mempool.commit()  # Save (commit) the changes
						mempool.close()
						logging.info("Mempool updated with a received transaction")
						
					
						#refresh() experimentally disabled
				else:
					logging.info("Invalid signature")
				#enter transaction end

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
	
		
	
