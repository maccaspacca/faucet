# Bismuth Faucet Main App
# Version 2.00
# Date 16/08/2018
# Copyright Maccaspacca 2017 to 2018
# Copyright The Bismuth Foundation 2016 to 2018
# Author Maccaspacca

from bottle import route, run, get, post, request, static_file
from random import getrandbits
import sqlite3, time, re, os, logging, random, platform, shutil, connections, socks, fprocs, socket, sys
from captcha.image import ImageCaptcha

import configparser as cp

logging.basicConfig(level=logging.INFO, 
                    filename='faucet.log', # log to this file
                    format='%(asctime)s %(message)s') # include timestamp

logging.info("logging initiated")

try:
	faucet_port = int(sys.argv[1])
except Exception as e:
	faucet_port = 8183
	
print("Faucet port is {}".format(str(faucet_port)))

config = cp.ConfigParser()
config.read('faucetconfig.ini')

logging.info("Reading config file.....")
myrate = int(config.get('My Faucet', 'myrate'))
myblocked = config.get('My Faucet', 'myblocked')
fau_root = config.get('My Faucet', 'mydbpath')
port = config.get('My Faucet', 'nodeport')
ip = config.get('My Faucet', 'nodeip')
max_ip_visit = int(config.get('My Faucet', 'maxvisits')) # maximum payouts per IP or hostname - need code to check hostname and store in requesters along with IP
valid_chars = config.get('My Faucet', 'v_chars')
capt_length = int(config.get('My Faucet', 'c_length'))

c_list = list(valid_chars)

c_str = ""

for cs in c_list:

	c_str = c_str + cs + ","
	
c_str = c_str[:-1]

# print(c_str)

if config.get('My Faucet', 'bestrict') == "true":
	f_strict = True
	logging.info("Strict Mode is ON")
	print("Strict Mode is ON")
else:
	f_strict = False
	logging.info("Strict Mode is OFF")
	print("Strict Mode is OFF")
	
spamtime = int(config.get('My Faucet', 'spamtime'))
address = config.get('My Faucet', 'faddy')

logging.info("Config file read completed")
config = None

my_os = platform.system()
my_os = my_os.lower()

myversion = "2.0.0" # hardcode the version

if "linux" in my_os:
	fau_root = os.path.expanduser('{}'.format(fau_root))
elif "windows" in my_os:
	pass
else: # if its not windows then probably a linux or unix variant
	pass

print("Faucet path = {}".format(fau_root))

mip = sqlite3.connect(':memory:')
mip.text_factory = str
p = mip.cursor()
p.execute("CREATE TABLE IF NOT EXISTS sessions (timestamp, custip, captcha, png)")
mip.commit()

def purge(pattern):
	import glob
	for f in glob.glob(pattern):
		os.remove(f)

# def getcaptcha(length = 6, char = string.ascii_uppercase + string.digits + string.ascii_lowercase ):
def getcaptcha(length = capt_length, char = valid_chars):

	return ''.join(random.choice(char) for x in range(length))

def myoginfo():

	doda = []

	doconfig = cp.ConfigParser()
	doconfig.read('faucetconfig.ini')
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
		# create empty faucet.db
		logging.info("Faucet DB: Create New as none exists")
		mlist = sqlite3.connect(fau_root)
		mlist.text_factory = str
		m = mlist.cursor()
		m.execute("CREATE TABLE IF NOT EXISTS requesters (timestamp, addy, amount, paid, custip, custhost)")
		mlist.commit()
		mlist.close()
		# create empty faucet.db

def balcheck():

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


def iplog(tempip,tempcaptcha,pngname):
	
	temptime = time.time()
	p.execute("INSERT INTO sessions VALUES (?,?,?,?)", (temptime, str(tempip), tempcaptcha, pngname))
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
		if t3 < spamtime:
			return False
		else:
			return True

def getcp(tempip):

	p.execute("SELECT * FROM sessions WHERE custip = ? ORDER BY timestamp DESC LIMIT 1;", (tempip,))
	checkcp = p.fetchall()
	#print(checkcp)
	
	cp = str(checkcp[0][2])
	pn = str(checkcp[0][3])
	
	return cp,pn

def getlinks():

	theselinks = []
	doconfig = cp.ConfigParser()
	doconfig.read('faucetconfig.ini')
	logging.info("Reading config file for web links.....")
	theselinks.append(doconfig.get('My Bismuth', 'website'))
	theselinks.append(doconfig.get('My Bismuth', 'wallet'))
	theselinks.append(doconfig.get('My Bismuth', 'source'))
	theselinks.append(doconfig.get('My Bismuth', 'discord'))
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
	mhead.append('ul {list-style-type: none;margin: 0;padding: 0;overflow: hidden;background-color: #600080;}\n')
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
	mhead.append('<title>{} v{}</title>\n'.format(dado[0],myversion))
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

	#print(balcheck())
	myip = request.environ.get('REMOTE_ADDR')
	
	myhost = socket.gethostbyaddr(myip)
	# print(myhost[0])
	
	currcaptcha = getcaptcha()
	seed = ('%0x' % getrandbits(64))
	iplog(myip,currcaptcha,seed)
	
	initial = my_head('table, th, td {border: 1px solid black;border-collapse: collapse;padding: 5px;-webkit-column-width: 100%;-moz-column-width: 100%;column-width: 100%;}')

	initial.append('<table ><tbody><tr>\n')
	initial.append('<td align="center" style="border:hidden;">\n')
	initial.append('<h1>Bismuth Cryptocurrency</h1>\n')
	
	if ipcheck(myip):
	
		if fprocs.balcheck(address,ip,port,fau_root,myrate)[0]:
	
			purge("static/*{}.png".format(myip))
			image = ImageCaptcha()
			data = image.generate(currcaptcha)
			image.write(currcaptcha, '{}{}.png'.format(seed,myip))
			src = "{}{}.png".format(seed,myip)
			dest = "static"
			shutil.move(src,dest)

			initial.append('<h2>Welcome to the Bismuth Faucet</h2>\n')
			# initial.append('<p>Hello {} ({})<p>\n'.format(myhost[0],myip))
			initial.append('<p>Enter your details below and click submit</p>\n')
			initial.append('<p>Valid characters are {}</p>\n'.format(c_str))
			if f_strict:
				initial.append('<p><b>One payout per address or IP</b></p>\n'.format(str(myrate),str(myblocked)))
			else:
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
			initial.append('<p>&copy; Copyright: Maccaspacca and The Bismuth Foundation, 2018</p>')
			initial.append('</center>\n')
			initial.append('</body>\n')
			initial.append('</html>')
			
		else:
			initial.append('<h2>Welcome to the Bismuth Faucet</h2>\n')
			initial.append('<p></p>\n')
			initial.append('<p><b>Not enough BIS in the faucet - come back later</b></p>\n')
			initial.append('<p></p>\n')
			initial.append('<p>&copy; Copyright: Maccaspacca and The Bismuth Foundation, 2018</p>')
			initial.append('</center>\n')
			initial.append('</body>\n')
			initial.append('</html>')
		
	else:
	
		initial.append('<h2>Welcome to the Bismuth Faucet</h2>\n')
		initial.append('<p></p>\n')
		initial.append('<p><b>Spam protection started, please come back later</b></p>\n')
		initial.append('<p></p>\n')
		initial.append('<p>&copy; Copyright: Maccaspacca and The Bismuth Foundation, 2018</p>')
		initial.append('</center>\n')
		initial.append('</body>\n')
		initial.append('</html>')
		# print("Not OK")

	starter = "" + str(''.join(initial))

	return starter
		
@post('/')
def home_query():
	
	myip = request.environ.get('REMOTE_ADDR')
	
	myhost = socket.gethostbyaddr(myip)
	# print(myhost[0])
	
	t_cap = getcp(myip)
	currcaptcha = t_cap[0]
	seed = t_cap[1]
	
	myblock = request.forms.get('addy')
	myanswer = request.forms.get('captcha')
	goodtogo = False

	replot = my_head('table, th, td {border: 1px solid black;border-collapse: collapse;padding: 5px;-webkit-column-width: 100%;-moz-column-width: 100%;column-width: 100%;}')

	replot.append('<table ><tbody><tr>\n')
	replot.append('<td align="center" style="border:hidden;">\n')
	replot.append('<h1>Bismuth Cryptocurrency</h1>\n')
	replot.append('<h2>Welcome to the Bismuth Faucet</h2>\n')

	if ipcheck(myip):

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
					if f_strict:
						myresponse = "<p>{}</p><p>Sorry - only one payment per Bismuth address</p>".format(myblock)
						try:
							os.remove("static/{}{}.png".format(seed,myip))
						except Exception as e:
							pass
						goodtogo = False
					else:
						# print("checkit")
						old = float(checkit[0][0])
						new = float(thistime)
						ruok = float(myblocked) * 3600
						if ruok >= (new - old):
							myresponse = "<p>{}</p><p>Too early - try later</p>".format(myblock)
							try:
								os.remove("static/{}{}.png".format(seed,myip))
							except Exception as e:
								pass
							goodtogo = False
				
				if checkip and goodtogo:
					if f_strict and len(checkip) > max_ip_visit:
						myresponse = "<p>{}</p><p>Sorry - only {} payment(s) per host or IP</p>".format(myblock,str(max_ip_visit))
						try:
							os.remove("static/{}{}.png".format(seed,myip))
						except Exception as e:
							pass
						goodtogo = False
					else:					
						old = float(checkip[0][0])
						new = float(thistime)
						ruok = float(myblocked) * 3600
						if ruok >= (new - old):
							myresponse = "<p>{}</p><p>Too early - try later</p>".format(myip)
							try:
								os.remove("static/{}{}.png".format(seed,myip))
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
			f.execute('INSERT INTO requesters VALUES (?,?,?,?,?,?)', (thistime, myblock, str(1), "No", str(myip), str(myhost[0])))
			faucet.commit()
			f.close()
			faucet.close()
			myresponse = "<p>Correct!</p><p>Your Bismuth will sent to you soon</p>"
			os.remove("static/{}{}.png".format(seed,myip))
		
		replot.append(str(myresponse))
		replot.append('<p></p>')
		replot.append('</td>\n')
		replot.append('</tr></tbody></table>\n')
		replot.append('<p>&copy; Copyright: Maccaspacca and The Bismuth Foundation, 2018</p>')
		replot.append('</center>\n')
		replot.append('</body>\n')
		replot.append('</html>')

	else:

		replot.append('<p></p>\n')
		replot.append('<p><b>Spam protection started, please come back later</b></p>\n')
		replot.append('<p></p>\n')
		replot.append('<p>&copy; Copyright: Maccaspacca and The Bismuth Foundation, 2018</p>')
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
	initial.append('<p><a href="{}" style="text-decoration:none;">Discord Channel</a></p>\n'.format(str(mylinks[3])))
	initial.append('<p></p>')
	initial.append('<p><a href="{}" style="text-decoration:none;">Explorer, ledger query, richlist and miner info</a></p>\n'.format(str(mylinks[4])))
	initial.append('<p></p>')
	initial.append('<p><a href="{}" style="text-decoration:none;">Bitcoin Talk Announcement</a></p>\n'.format(str(mylinks[5])))
	initial.append('</td>\n')
	initial.append('<td align="center" style="border:hidden;">')
	initial.append('<p></p>')
	initial.append('</td>\n')
	initial.append('</tr></tbody></table>\n')
	initial.append('<p>&copy; Copyright: Maccaspacca and The Bismuth Foundation, 2018</p>')
	initial.append('</center>\n')
	initial.append('</body>\n')
	initial.append('</html>')

	starter = "" + str(''.join(initial))

	return starter

urls = (
    '/', 'index',
	'/links', 'links'
)

if __name__ == "__main__":
	checkstart()
	# insert other start procedures here
	run(host='0.0.0.0', port=faucet_port, debug=True)
