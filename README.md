# faucet
Bismuth Faucet

A reference faucet for the Bismuth cryptocurrency

The application consists of two parts - a main faucet application and a payment processing module

# bisfaucet.py

This is the main application.

The default port is 8183 but this can be adjusted by passing the port as an arguement on startup e.g. bisfaucet.py 8080

Place the file in a folder of your choosing together with the faucetconfig.ini file.

Adjust the faucetconfig.ini with the path to your faucet database paths

On first run it will create a new faucet database file in the database path location specified in the faucetconfig.ini file

The faucet will connect to the node ip configured in faucetconfig.ini which is usually 127.0.0.1

There is the possibility to connect to a suitable remote node but reliability cannot be guaranteed

# payout.py

The file faucetconfig.ini should be edited with the faucet database location and the Bismuth payout rate.

The file should be run with the wallet.der file being used for payment in the same folder. The wallet.der file should not be encrypted.

Once running it will run the payout routine every 60 minutes.

The faucet and payout applications should not be run on your main node and you should use a dedicated node and wallet address for the faucet.