# Faucet proceedures
# Version 2.00
# Date 16/08/2018
# Copyright Maccaspacca 2017 to 2018
# Copyright The Bismuth Foundation 2016 to 2018
# Author Maccaspacca

import connections, socks, sqlite3

def balcheck(address,ip,port,fau_root,myrate):

	#print(address)
	s = socks.socksocket()
	s.settimeout(10)
	s.connect((ip, int(port)))
	connections.send(s, "balanceget", 10)
	connections.send(s, address, 10)
	mbal_get = connections.receive(s, 10)
	s.close()
	
	#print ("Current balance: {}".format(mbal_get[0]))
	
	tbal = float(mbal_get[0])
	
	pay = sqlite3.connect(fau_root)
	pay.text_factory = str
	p = pay.cursor()
	p.execute("SELECT * FROM requesters WHERE paid = 'No';")
	tp = p.fetchall()
	owed = float(len(tp)) + ((float(len(tp)) * (float(myrate))) * 0.01) + (float(len(tp)) * 0.00006)
	#print(owed)
	pay.close()
	
	mybal = tbal - owed
	#print(mybal)
	mymin = float(myrate) + ((float(myrate)) * 0.01) + 0.00006
	#print(mymin)
	
	if mybal > mymin:
		return True,mybal
	else:
		return False,mybal
		
def tx_send(ip,port,tx_submit):

	s = socks.socksocket()
	s.settimeout(10)
	s.connect((ip, int(port)))
	connections.send(s, "mpinsert", 10)
	connections.send(s, tx_submit, 10)
	reply = connections.receive(s, 10)
	s.close()
	
	return reply