# Simple web-scraper to check pick-up / delivery queue status of Indian grocery stores in the SF Bay Area during the COVID-19 quarantine

This is a simple web-scraper using basic selenium and python-3 to check the pick-up / delivery status of grocery stores, which are blocked / queued most of the time during the COVID-19 crisis.

### USAGE:

```python check_grocery_slots.py [-t]```

(The ```-t``` flag is specific for tests with Chrome on Mac OSX, but it is all that is implemented right now)

### NOTE
1) This is NOT a shopping service, i.e. you'll have to log-in to the store website and fill in your cart yourself. Basically go through all the steps before the payment (in some cases the payment will not go through unless the queue is open so that's good!) This script will then keep monitoring the queue status and send you emails if the queue opens. Of course you'll have to keep your laptops switched on throughout the day. 

2) Once a hit is found (i.e. store is open for pickup or delivery, your inbox will start getting spammed). This is the part where you kill the script and rush over to the store website (or the store itself if you aren't too keen on social distancing, pro tip: don't do it) to order your groceries!

### CONFIGURATION

All you need is a gmail email id from which the notifications will be sent. 

You need a configuration file called ```config.json``` that contains the sender and receiver emails for the notifications to be communicated. In addition it also needs a username and password for logging on to the store website. It is suggested that you keep a single username and password for all the stores if you want to add more store website scrapers to the script.  A template for this json file is supplied.

The ```GMAIL_TOKEN``` field in the configuration is a  16 character app password generated by Google for the account belonging to the sender email (gmail) id (```EMAIL_SRC``). To do this you need to first enable two-factor authentication for this account. (Further details can be  found [here](https://support.google.com/accounts/answer/185833?hl=en)).

## Development and Contribution

1) The actual scraper function/(s) are (obviously) incredibly specific to the website/(s). Currently only written for [Bharat Bazar in the San Francisco Bay Area](https://www.shopbharatbazar.com/), since I'm regular (read: strongly dependent) on the Indian  groceries from this place. Other stores will be added soon. Please feel free to fork and add other stores as you see fit!

2) I'd eventually like to get this deployed on a Raspberry Pi (running raspbian-jessie) server but can't seem to get selenium working with Chromium or other browsers available on a Rpi arm7 config. 

3) Once any queue opens in the list of all stores, an email message will be triggered. This means that if queues open at certain times of the day, expect your inbox to be spammed. This can be taken care of with periodic notifications, but too lazy to do that now. 