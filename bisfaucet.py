# Bismuth Faucet Main App
# Version 1.00
# Date 28/07/2017
# Copyright Maccaspacca 2017
# Copyright Hclivess 2016 to 2017
# Author Maccaspacca

from bottle import route, run, get, post, request, static_file
import sqlite3
import time
import re
import os
import base64
import hashlib
import logging
import random
import platform
import string
from captcha.image import ImageCaptcha
import shutil

try:
    # For Python 3.0 and later
	import configparser as cp
except ImportError:
    # Fall back to Python 2's ConfigParser
	import ConfigParser as cp

# globals
global my_os
global bis_root
global bis_path
global fau_root
global myblocked
global myrate
global bis_mem
global pubpath

logging.basicConfig(level=logging.INFO, 
                    filename='faucet.log', # log to this file
                    format='%(asctime)s %(message)s') # include timestamp

logging.info("logging initiated")

config = cp.ConfigParser()
config.read('faucetconfig.ini')
# config.readfp(open(r'faucetconfig.ini'))
logging.info("Reading config file.....")
bis_root = config.get('My Bismuth', 'dbpath')
bis_path = config.get('My Bismuth', 'bispath')
myrate = int(config.get('My Faucet', 'myrate'))
myblocked = config.get('My Faucet', 'myblocked')
fau_root = config.get('My Faucet', 'mydbpath')
logging.info("Config file read completed")
config = None

my_os = platform.system()
my_os = my_os.lower()

if "linux" in my_os:
	fau_root = os.path.expanduser('{}'.format(fau_root))
	bis_root = os.path.expanduser('{}'.format(bis_root))
	bis_path = os.path.expanduser('{}'.format(bis_path))
elif "windows" in my_os:
	pass
else: # if its not windows then probably a linux or unix variant
	pass

bis_mem = "{}mempool.db".format(bis_path)
pubpath = "{}pubkey.der".format(bis_path)

print("Faucet path = {}".format(fau_root))

mip = sqlite3.connect(':memory:')
mip.text_factory = str
p = mip.cursor()
p.execute("CREATE TABLE IF NOT EXISTS sessions (timestamp, custip, captcha)")
mip.commit()

def purge(pattern):
	import glob
	for f in glob.glob(pattern):
		os.remove(f)

# def getcaptcha(length = 6, char = string.ascii_uppercase + string.digits + string.ascii_lowercase ):
def getcaptcha(length = 10, char = string.digits):

	return ''.join(random.choice( char) for x in range(length))

def myoginfo():

	doda = []

	doconfig = cp.ConfigParser()
	doconfig.read('faucetconfig.ini')
	# doconfig.readfp(open(r'faucetconfig.ini'))
	logging.info("Reading config file.....")
	doda.append(doconfig.get('My Oginfo', 'og_title'))
	doda.append(doconfig.get('My Oginfo', 'og_description'))
	doda.append(doconfig.get('My Oginfo', 'og_url'))
	doda.append(doconfig.get('My Oginfo', 'og_site_name'))
	doda.append(doconfig.get('My Oginfo', 'og_image'))

	logging.info("Config file read completed")
	
	doconfig = None
	
	return doda

def checkstart():

	if not os.path.exists(fau_root):
		# create empty miners database
		logging.info("Faucet DB: Create New as none exists")
		mlist = sqlite3.connect(fau_root)
		mlist.text_factory = str
		m = mlist.cursor()
		m.execute("CREATE TABLE IF NOT EXISTS requesters (timestamp, addy, amount, paid, custip)")
		mlist.commit()
		mlist.close()
		# create empty faucet.db

def balcheck():

	with open(pubpath, 'r') as f:
		public_key_readable = f.read()
	public_key_hashed = base64.b64encode(public_key_readable.encode("utf-8"))
	address = hashlib.sha224(public_key_readable.encode("utf-8")).hexdigest()
	f.close()

	mempool = sqlite3.connect(bis_mem)
	mempool.text_factory = str
	m = mempool.cursor()
	m.execute("SELECT sum(amount) FROM transactions WHERE address = ?;", (address,))
	debit_mempool = m.fetchone()[0]
	mempool.close()
	if debit_mempool == None:
		debit_mempool = 0

	conn = sqlite3.connect(bis_root)
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
	tbal = credit - debit - fees + rewards - debit_mempool
	
	pay = sqlite3.connect(fau_root)
	pay.text_factory = str
	p = pay.cursor()
	p.execute("SELECT * FROM requesters WHERE paid = 'No';")
	tp = p.fetchall()
	owed = float(len(tp)) + ((float(len(tp)) * (float(myrate))) * 0.001)
	pay.close()
	
	mybal = tbal - owed
	# print(mybal)
	mymin = float(myrate) + ((float(myrate)) * 0.001)
	# print(mymin)
	
	if mybal > mymin:
		return True
	else:
		return False


def iplog(tempip,tempcaptcha):
	
	temptime = time.time()
	p.execute("INSERT INTO sessions VALUES (?,?,?)", (temptime, str(tempip), tempcaptcha))
	mip.commit()

# get faucet balance

def ipcheck(tempip):

	p.execute("SELECT * FROM sessions WHERE custip = ? ORDER BY timestamp DESC;", (tempip,))
	checkip = p.fetchall()
	
	if len(checkip) < 10:
		return True
	else:
		t1 = checkip[0][0]
		# print(t1)
		t2 = checkip[9][0]
		# print(t2)
		t3 = t1 - t2
		# print(t3)
		if t3 < 300:
			return False
		else:
			return True

def getcp(tempip):

	p.execute("SELECT * FROM sessions WHERE custip = ? ORDER BY timestamp DESC LIMIT 1;", (tempip,))
	checkcp = p.fetchall()
	
	cp = str(checkcp[0][2])
	
	return cp

def getlinks():

	theselinks = []
	doconfig = cp.ConfigParser()
	# doconfig.readfp(open(r'faucetconfig.ini'))
	doconfig.read('faucetconfig.ini')
	logging.info("Reading config file for web links.....")
	theselinks.append(doconfig.get('My Bismuth', 'website'))
	theselinks.append(doconfig.get('My Bismuth', 'wallet'))
	theselinks.append(doconfig.get('My Bismuth', 'source'))
	theselinks.append(doconfig.get('My Bismuth', 'slack'))
	theselinks.append(doconfig.get('My Bismuth', 'explorer'))
	theselinks.append(doconfig.get('My Bismuth', 'bct'))

	logging.info("Web links read completed")
	
	doconfig = None
	
	return theselinks

def test(testString):

	if (re.search('[abcdef]',testString)):
		if len(testString) == 56:
			test_result = 1
		else:
			test_result = 2
	else:
		test_result = 2
		
	return test_result	

def my_head(bo):

	mhead = []
	dado = myoginfo()
	
	mhead.append('<!doctype html>\n')
	mhead.append('<html>\n')
	mhead.append('<head>\n')
	mhead.append('<link rel = "icon" href = "static/explorer.ico" type = "image/x-icon" />\n')
	mhead.append('<style>\n')
	mhead.append('h1, h2, p, li, td, label {font-family: Verdana;}\n')
	mhead.append('body {font-size: 100%;}\n')
	mhead.append('ul {list-style-type: none;margin: 0;padding: 0;overflow: hidden;background-color: #333;}\n')
	mhead.append('li {float: left;}\n')
	mhead.append('li a {display: inline-block;color: white;text-align: center;padding: 14px 16px;text-decoration: none;}\n')
	mhead.append('li a:hover {background-color: #111;}\n')
	mhead.append('.btn-link{border:none;outline:none;background:none;cursor:pointer;color:#0000EE;padding:0;text-decoration:underline;font-family:inherit;font-size:inherit;}\n')
	mhead.append(bo + '\n')
	mhead.append('</style>\n')
	mhead.append('<meta property="og:type" content="website" />\n')
	mhead.append('<meta property="og:title" content="{}" />\n'.format(dado[0]))
	mhead.append('<meta property="og:description" content="{}" />\n'.format(dado[1]))
	mhead.append('<meta property="og:url" content="{}" />\n'.format(dado[2]))
	mhead.append('<meta property="og:site_name" content="{}" />\n'.format(dado[3]))
	mhead.append('<meta property="og:image" content="{}" />\n'.format(dado[4]))
	mhead.append('<meta property="og:image:width" content="200" />\n')
	mhead.append('<meta property="og:image:height" content="200" />\n')
	mhead.append('<meta property="og:locale" content="en_US" />\n')
	mhead.append('<meta property="xbm:version" content="201" />\n')
	mhead.append('<meta name="description" content="{}" />\n'.format(dado[1]))
	mhead.append('<title>{}</title>\n'.format(dado[0]))
	mhead.append('</head>\n')
	mhead.append('<body background="static/explorer_bg.png">\n')
	mhead.append('<center>\n')
	mhead.append('<table style="border:0;font-size:75%">\n')
	mhead.append('<tr style="border:0"><td style="border:0">\n')
	mhead.append('<ul>\n')
	mhead.append('<li><a href="">Menu:</a></li>\n')
	mhead.append('<li><a href="/">Home</a></li>\n')
	mhead.append('<li><a href="/links">Links</a></li>\n')
	mhead.append('</ul>\n')
	mhead.append('</td></tr>\n')
	mhead.append('</table>\n')

	return mhead
	
#////////////////////////////////////////////////////////////
#                       MAIN APP
# ///////////////////////////////////////////////////////////

@route('/static/<filename>')
def server_static(filename):
	return static_file(filename, root='static/')

@get('/')
def home_form():

	print(balcheck())
	myip = request.environ.get('REMOTE_ADDR')
	currcaptcha = getcaptcha()
	iplog(myip,currcaptcha)
	
	initial = my_head('table, th, td {border: 1px solid black;border-collapse: collapse;padding: 5px;-webkit-column-width: 100%;-moz-column-width: 100%;column-width: 100%;}')

	initial.append('<table ><tbody><tr>\n')
	initial.append('<td align="center" style="border:hidden;">\n')
	initial.append('<h1>Bismuth Cryptocurrency</h1>\n')
	
	if balcheck():
	
		if ipcheck(myip):
			# print("OK")

			purge("static/*{}.png".format(myip))
			image = ImageCaptcha()
			data = image.generate(currcaptcha)
			image.write(currcaptcha, '{}{}.png'.format(currcaptcha,myip))
			src = "{}{}.png".format(currcaptcha,myip)
			dest = "static"
			shutil.move(src,dest)

			initial.append('<h2>Welcome to the Bismuth Faucet</h2>\n')
			initial.append('<p>Enter your details below and click submit</p>\n')
			initial.append('<p><b>The payout is {} BIS every {} hours</b></p>\n'.format(str(myrate),str(myblocked)))
			initial.append('<p></p>\n')
			initial.append('<p><img src="static/{}" alt="captcha"></p>\n'.format(src))
			initial.append('</td>\n')
			initial.append('</tr></tbody></table>\n')
			initial.append('<form method="post" action="/">\n')
			initial.append('<table>\n')
			initial.append('<tr><th align="left"><label for="addy">1. Enter Your Address</label></th><td><input type="text" id="addy" name="addy" size="64"/></td></tr>\n')
			initial.append('<tr><th align="left"><label for="captcha">2. Type in the text from the image above</label></th><td><input type="text" id="captcha" name="captcha" size="15"/></td></tr>\n')
			initial.append('<tr><th align="left"><label for="Submit Request">3. Click Submit to claim Bismuth</label></th><td><button id="Submit" name="Submit">Submit</button></td></tr>\n')
			initial.append('</table>\n')
			initial.append('</form>\n')
			initial.append('<p>&copy; Copyright: Maccaspacca and HCLivess, 2017</p>')
			initial.append('</center>\n')
			initial.append('</body>\n')
			initial.append('</html>')
		
		else:
		
			initial.append('<h2>Welcome to the Bismuth Faucet</h2>\n')
			initial.append('<p></p>\n')
			initial.append('<p><b>Too Many Visits - come back later</b></p>\n')
			initial.append('<p></p>\n')
			initial.append('<p>&copy; Copyright: Maccaspacca and HCLivess, 2017</p>')
			initial.append('</center>\n')
			initial.append('</body>\n')
			initial.append('</html>')
			# print("Not OK")
	else:
		initial.append('<h2>Welcome to the Bismuth Faucet</h2>\n')
		initial.append('<p></p>\n')
		initial.append('<p><b>Not enough BIS in the faucet - come back later</b></p>\n')
		initial.append('<p></p>\n')
		initial.append('<p>&copy; Copyright: Maccaspacca and HCLivess, 2017</p>')
		initial.append('</center>\n')
		initial.append('</body>\n')
		initial.append('</html>')

	starter = "" + str(''.join(initial))

	return starter
		
@post('/')
def home_query():
	
	myip = request.environ.get('REMOTE_ADDR')
	currcaptcha = getcp(myip)
	
	myblock = request.forms.get('addy')
	myanswer = request.forms.get('captcha')
	goodtogo = False

	replot = my_head('table, th, td {border: 1px solid black;border-collapse: collapse;padding: 5px;-webkit-column-width: 100%;-moz-column-width: 100%;column-width: 100%;}')

	replot.append('<table ><tbody><tr>\n')
	replot.append('<td align="center" style="border:hidden;">\n')
	replot.append('<h1>Bismuth Cryptocurrency</h1>\n')
	replot.append('<h2>Welcome to the Bismuth Faucet</h2>\n')

	if ipcheck(myip):
		# print("OK")	

		if myanswer == currcaptcha:
					
			#Nonetype handling
			
			if not myblock:
				myresponse = "<p>Error</p><p>Invalid address</p>"
				goodtogo = False
			
			if not myblock.isalnum():
				myresponse = "<p>Error</p><p>Invalid address</p>"
				goodtogo = False
				#print("has dodgy characters but now fixed")
			
			my_type = test(myblock)
			
			if my_type == 2:
				myresponse = "<p>Error</p><p>Invalid address</p>"
				goodtogo = False

			if my_type == 1:
				thistime = time.time()
				goodtogo = True
				
				faucet = sqlite3.connect(fau_root)
				faucet.text_factory = str
				f = faucet.cursor()
				f.execute("SELECT * FROM requesters WHERE addy = ? ORDER BY timestamp DESC LIMIT 1;", (str(myblock),))
				checkit = f.fetchall()
				f.execute("SELECT * FROM requesters WHERE custip = ? ORDER BY timestamp DESC LIMIT 1;", (myip,))
				checkip = f.fetchall()
				f.close()
				faucet.close()
				
				if checkit:
					# print("checkit")
					old = float(checkit[0][0])
					new = float(thistime)
					ruok = float(myblocked) * 3600
					if ruok >= (new - old):
						myresponse = "<p>{}</p><p>Too early - try later</p>".format(myblock)
						try:
							os.remove("static/{}{}.png".format(currcaptcha,myip))
						except Exception as e:
							pass
						goodtogo = False
				if checkip and goodtogo:
					old = float(checkip[0][0])
					new = float(thistime)
					ruok = float(myblocked) * 3600
					if ruok >= (new - old):
						myresponse = "<p>{}</p><p>Too early - try later</p>".format(myip)
						try:
							os.remove("static/{}{}.png".format(currcaptcha,myip))
						except Exception as e:
							pass
						goodtogo = False
			
		else:
			myresponse = "<p>Error</p><p>Invalid Captcha - try again</p>"
			goodtogo = False
			
		# print(goodtogo)
		
		if goodtogo:
			faucet = sqlite3.connect(fau_root)
			faucet.isolation_level = None
			faucet.text_factory = str
			f = faucet.cursor()
			f.execute('INSERT INTO requesters VALUES (?,?,?,?,?)', (thistime, myblock, str(1), "No", str(myip)))
			faucet.commit()
			f.close()
			faucet.close()
			myresponse = "<p>Correct!</p><p>Your Bismuth will sent to you soon</p>"
			os.remove("static/{}{}.png".format(currcaptcha,myip))
		
		replot.append(str(myresponse))
		replot.append('<p></p>')
		replot.append('</td>\n')
		replot.append('</tr></tbody></table>\n')
		replot.append('<p>&copy; Copyright: Maccaspacca and HCLivess, 2017</p>')
		replot.append('</center>\n')
		replot.append('</body>\n')
		replot.append('</html>')

	else:

		replot.append('<p></p>\n')
		replot.append('<p><b>Too Many Visits - Come back later</b></p>\n')
		replot.append('<p></p>\n')
		replot.append('<p>&copy; Copyright: Maccaspacca and HCLivess, 2017</p>')
		replot.append('</center>\n')
		replot.append('</body>\n')
		replot.append('</html>')
		# print("Not OK")	

	starter = "" + str(''.join(replot))
	
	return starter

@route('/links')
def links():

	mylinks = getlinks()

	initial = my_head('table, th, td {border: 1px solid black;border-collapse: collapse;padding: 5px;-webkit-column-width: 100%;-moz-column-width: 100%;column-width: 100%;}')

	initial.append('<table ><tbody><tr>\n')
	initial.append('<td align="center" style="border:hidden;">')
	initial.append('<p></p>')
	initial.append('</td>\n')
	initial.append('<td align="center" style="border:hidden;">\n')
	initial.append('<h1>Bismuth Cryptocurrency</h1>\n')
	initial.append('<h2>Useful Links</h2>\n')
	initial.append('<p>Use the following links for Bismuth information and resources</p>\n')
	initial.append('<p></p>')
	initial.append('<p><a href="{}" style="text-decoration:none;">Main Bismuth Website</a></p>\n'.format(str(mylinks[0])))
	initial.append('<p></p>')
	initial.append('<p><a href="{}" style="text-decoration:none;">Latest Wallet Releases</a></p>\n'.format(str(mylinks[1])))
	initial.append('<p></p>')
	initial.append('<p><a href="{}" style="text-decoration:none;">Wallet Source</a></p>\n'.format(str(mylinks[2])))
	initial.append('<p></p>')
	initial.append('<p><a href="{}" style="text-decoration:none;">Bismuth Slack</a></p>\n'.format(str(mylinks[3])))
	initial.append('<p></p>')
	initial.append('<p><a href="{}" style="text-decoration:none;">Explorer, ledger query, richlist and miner info</a></p>\n'.format(str(mylinks[4])))
	initial.append('<p></p>')
	initial.append('<p><a href="{}" style="text-decoration:none;">Bitcoin Talk Announcement</a></p>\n'.format(str(mylinks[5])))
	initial.append('</td>\n')
	initial.append('<td align="center" style="border:hidden;">')
	initial.append('<p></p>')
	initial.append('</td>\n')
	initial.append('</tr></tbody></table>\n')
	initial.append('<p>&copy; Copyright: Maccaspacca and HCLivess, 2017</p>')
	initial.append('</center>\n')
	initial.append('</body>\n')
	initial.append('</html>')

	starter = "" + str(''.join(initial))

	return starter

urls = (
    '/', 'index'
)

if __name__ == "__main__":
	checkstart()
	# insert other start procedures here
	run(host='0.0.0.0', port=8183, debug=True)
