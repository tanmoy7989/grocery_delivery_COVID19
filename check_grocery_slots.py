import os
import argparse
import time
from datetime import datetime
import pandas as pd
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart

WAIT = 3 # wait for 4 secs after web events (such as mouse clicks)
N_ATTEMPT = 4 # number of re-tries before giving up

DATE_TIME_FMT = "%d/%m/%Y %H:%M:%S"
LOG_FN = os.path.join(os.getcwd(), "log.csv")


def _init_browser(test=True):
    """
    Initializes a browser instance for Google Chrome (for testing from a
    laptop: in my case a macbook)
    or some headless driver (for deploying on a server such as a raspberry pi)

    :param test: (bool) True if this is a test

    :return: selenium webdriver instance
    """

    if test:
        CHROMEDRIVER = os.path.join(os.getcwd(), "drivers", "chromedriver")
        options = ChromeOptions()
        options.headless = True
        browser = webdriver.Chrome(CHROMEDRIVER, options=options)
    else:
        raise NotImplementedError("Still testing!")
    return browser


def _delay(func, *args, **kwargs):
    """
    Helper function to put a small delay before or after a browser event
    such as a mouse-click

    :param func: function / method to delay

    :param args: args used by above function / method

    :param kwargs: keyword args used by above function / method
    """

    before = kwargs.pop("before", 0)
    after = kwargs.pop("after", 0)
    time.sleep(before)
    func(*args, **kwargs)
    time.sleep(after)


def _make_status_msg(s=None):
    """
    Helper function to raise a print a pretty status message

    :param s: (dict) dict containing store name, pickup and delivery status

    :return: (str) pretty printable status msg
    """

    status = ""

    if s is None:
        return status

    if "yes" in s["pickup"]:
        status += "pickup"
    if "yes" in s["delivery"]:
        if status:
            status += ", "
        status += "delivery"

    if status:
        status = s["store"].upper() + " (" + status + ")" + "   "
    return status


def _check_Bharat_Bazar(browser, username, password, location="FREMONT"):
    """
    Check Bharat Bazar in SF Bay area locations

    :param browser: (selenium webdriver instance)

    :param username: (str) username to login

    :param password: (str) password to login

    :param location: (str) one of "FREMONT", "UNION CITY" or "SUNNYVALE"

    :return: (dict) pickup / delivery status
    """

    login_url = "https://www.shopbharatbazar.com/login"
    checkout_url = "https://www.shopbharatbazar.com/cart/checkout"

    all_locations = ["FREMONT", "UNION CITY", "SUNNYVALE"]
    if location not in all_locations:
        s_all_locations = ", ".join(all_locations)
        raise TypeError("Bharat Bazar located only in ", s_all_locations)

    status = {"pickup": {"code": 0, "msg": "closed"},
              "delivery": {"code": 0, "msg": "closed"}
              }

    # login
    _delay(browser.get, login_url, after=WAIT)
    browser.find_element_by_id("email").send_keys(username)
    browser.find_element_by_name("password").send_keys(password)
    login_selector_xpath = ".//button[@type='submit'][contains(., 'Log In')]"
    login_selector = browser.find_element_by_xpath(login_selector_xpath)
    _delay(login_selector.click, after=WAIT)

    # select location
    loc_selector_tag = [e for e in browser.find_elements_by_tag_name("h4")
                        if location in e.text][0]
    loc_selector = loc_selector_tag.find_elements_by_tag_name("a")[0]
    _delay(loc_selector.click, after=WAIT)

    # select groceries
    grocery_selector = [e for e in browser.find_elements_by_tag_name("h5")
                        if e.text == "Groceries"][0]
    _delay(grocery_selector.click, after=WAIT)

    _delay(browser.get, checkout_url, after=WAIT)

    # check pick up status
    pickup_selector = [e for e in browser.find_elements_by_tag_name("h3")
                       if "Pick Up" in e.text][0]
    _delay(pickup_selector.click, after=WAIT)
    no_pickup = [e for e in browser.find_elements_by_tag_name("h4")
                 if "All pickup windows are full at the moment" in e.text]
    if not (no_pickup):
        status["pickup"]["code"] = 1
        status["pickup"]["msg"] = "open"

    # check delivery status
    delivery_selector = [e for e in browser.find_elements_by_tag_name("h3")
                         if "Delivery" in e.text][0]
    _delay(delivery_selector.click, after=WAIT)
    no_order_min = [e for e in browser.find_elements_by_tag_name("span")
                    if "All Delivery orders must be $30 or more" in e.text]
    no_within_distance = [e for e in browser.find_elements_by_tag_name("span")
                          if "Delivery is not available to the address"
                          in e.text]

    if no_order_min:
        no_order_min = no_order_min[0]
        status["delivery"]["msg"] = "min $30 needed for delivery"
    elif no_within_distance:
        status["delivery"]["msg"] = "not within delivery distance"
    else:
        no_delivery = [e for e in browser.find_elements_by_tag_name("h4")
                       if "All delivery windows are full at the moment"
                       in e.text]
        if not (no_delivery):
            status["delivery"]["code"] = 1
            status["delivery"]["msg"] = "open"

    browser.close()
    return status


def _write_log(status, success_flag, store):
    """
    Helper function to write to a log file

    :param status: (dict) pickup / delivery status dict

    :param success_flag: (bool) whether the scraping went through

    :param store: (str) name of the store

    :return: (dict) trimmed status dict
    """

    now = datetime.now()
    dt_string = now.strftime(DATE_TIME_FMT)

    if not success_flag:
        pickup_code = 0
        delivery_code = 0
        pickup_msg = "Max attempts reached"
        delivery_msg = "Max attemps reached"
    else:
        pickup_code = status["pickup"]["code"]
        delivery_code = status["delivery"]["code"]
        pickup_msg = status["pickup"]["msg"]
        delivery_msg = status["delivery"]["msg"]

    log_fn = LOG_FN
    data = []
    if os.path.isfile(log_fn):
        df = pd.read_csv(log_fn)
        data = [tuple(df.loc[i]) for i in range(len(df))]

    data.append((dt_string, store, pickup_code, delivery_code,
                 pickup_msg, delivery_msg))
    df = pd.DataFrame(data,
                      columns=["t", "store",
                               "pickup_code", "delivery_code",
                               "pickup_msg", "delivery_msg"])
    df.to_csv(log_fn, index=False)

    mapint2str = {1: "yes", 0: "no"}
    out = {"store": store,
           "pickup": mapint2str[pickup_code],
           "delivery": mapint2str[delivery_code]}
    if success_flag:
        return out
    else:
        return None


def _send_email(config, msg=""):
    """
    Helper function to send the pickup / delivery status to selected email/(s)

    :param config: (dict) configuration dict
    containing sender / receiver details

    :param msg: (str) the message to send out
    """
    port = 587  # for SSL
    smtp_server = "smtp.gmail.com"
    sender_email = config["EMAIL_SRC"]
    sender_password = config["GMAIL_TOKEN"]
    receiver_emails = config["EMAIL_TARGETS"]
    if isinstance(receiver_emails, str):
        receiver_emails = list(receiver_emails)

    payload = MIMEMultipart()
    payload["From"] = sender_email
    payload["Subject"] = msg

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender_email, sender_password)
        for r in receiver_emails:
            payload["To"] = r
            _delay(server.sendmail,
                   sender_email, r, payload.as_string(),
                   after=2)


def main(config, test=True, **kwargs):
    """
    Main driver function for cycling through all shops that need to be checked

    :param config: (dict) configuration dict containing details of emailing

    :param test: (bool) True to use from laptop with Google Chrome

    :param kwargs: keyword args necessary for the different web-scrapers

    :return: (str) formatted status string
    """

    # Bharat_Bazar (any location)
    success = 0
    attempt = 0
    location = kwargs.pop("location", "FREMONT")

    browser = _init_browser(test=test)
    username = config["USERNAME"]
    password = config["PASSWORD"]

    while (attempt < N_ATTEMPT) and (not success):
        try:
            status = _check_Bharat_Bazar(browser=browser,
                                         username=username,
                                         password=password,
                                         location=location)
            success = 1
        except IndexError:
            print("Attempting again...")
            attempt += 1
            browser.quit()
            del browser
            browser = _init_browser(test=test)
            continue

    if not success:
        status = {"pickup": {"code": 0, "message": ""},
                  "delivery": {"code": 0, "message": ""}}

    # write to log-file
    out = _write_log(store="Bharat_Bazar_%s" % location,
                     status=status,
                     success_flag=success)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor for Indian grocery "
                                                 "delivery in SF Bay area")
    parser.add_argument("-c", "--config", default="config.json",
                        help="config json file")
    parser.add_argument("-t", "--test", action="store_true",
                        help="raise flag to indicate testing mode")
    args = parser.parse_args()

    # parse args
    config_fn = os.path.abspath(args.config)
    if not os.path.isfile(config_fn):
        raise IOError("Config file %s not found" % config_fn)
    with open(config_fn, "r") as of:
        config = json.load(of)

    # daemon
    while (1):
        status = []

        ## check stores one by one here

        # Bharat Bazar FREMONT
        s = main(config=config, location="FREMONT", test=args.test)
        status.append(_make_status_msg(s))

        # Bharat Bazar UNION CITY
        s = main(config=config, location="UNION CITY", test=args.test)
        status.append(_make_status_msg(s))

        # Bharat Bazar SUNNYVALE
        s = main(config=config, location="SUNNYVALE", test=args.test)
        status.append(_make_status_msg(s))

        # TODO: add other stores here later

        # send notification if any pickup opens
        msg = "".join(status)
        if msg:
            _send_email(config=config, msg=msg)