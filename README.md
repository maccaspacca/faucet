# faucet
Bismuth Faucet

A reference faucet for the Bismuth cryptocurrency

The application consists of two parts - a main faucet application and a payment processing module

# bisfaucet.py

This is the main application. Dependencies are as the main Bismuth client plus the captcha module (pip3 install captcha) and bottle (pip3 install bottle)

The default port is 8183 but this can be adjusted on line 543

Place the file in a folder of your choosing together with the faucetconfig.ini file.

Adjust the faucetconfig.ini with the paths to your Bismuth folder and faucet database paths

On first run it will create a new faucet database file in the database path location specified in the faucetconfig.ini file

# payout.py

This is the payout application and should be placed and run from the main Bismuth folder with the file faucet.ini

The file faucet.ini should be edited with the faucet database location and the same Bismuth payout rate as that in the faucetconfig.ini file

The file should be run with the Bismuth node application and the wallet being used for payment. Once running it will run the payout routine every 60 minutes.

The faucet and payout applications should not be run on your main node and you should use a dedicated node and wallet address for the faucet.