#!/usr/bin/env python

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)

allUsers = dict()

class User:
    def __init__(self, userId):
        self.id = userId
        self.balance = 0.0
        self.credit = 0.0

def getUser(userId):
    user = allUsers.get(userId)
    if user is None:
        user = User(userId)
        allUsers[userId] = user
    return user

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    #userId = req.get("originalRequest").get("data").get("user").get("user_id")
    userId = req.get("sessionId")
    if userId is None:
        return {}

    user = getUser(userId)

    res = processRequest(req, user)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req, user):
    action = req.get("result").get("action")
    params = req.get("result").get("parameters")
    if action == "addBalance":
        return doAddBalance(params, user)
    elif action == "charge":
        return doCharge(params, user)

    if req.get("result").get("action") != "yahooWeatherForecast":
        return {}
    baseurl = "https://query.yahooapis.com/v1/public/yql?"
    yql_query = makeYqlQuery(req)
    if yql_query is None:
        return {}
    yql_url = baseurl + urlencode({'q': yql_query}) + "&format=json"
    result = urlopen(yql_url).read()
    data = json.loads(result)
    res = makeWebhookResult(data)
    return res


def doAddBalance(params, user):
    unitCurrency = params.get("unit-currency")
    if unitCurrency is None:
        return {}

    amount = float(unitCurrency.get("amount"))
    if amount <= 0:
        return {}

    user.balance += amount

    speech = "Successfully added {} to your balance. Your balance is now {}".format(amount, user.balance)

    return makeResponse(speech)


def doCharge(params, user):
    unitCurrency = params.get("unit-currency")
    if unitCurrency is None:
        return {}

    amount = float(unitCurrency.get("amount"))
    if amount <= 0:
        return {}

    if user.balance < amount:
        speech = "Sorry but your balance {} is insufficient for this charge".format(user.balance)
    else:
        user.balance -= amount
        user.credit += amount
        speech = "Successfully charged {} to your credit. Your credit is now {}".format(amount, user.credit)

    return makeResponse(speech)


def makeResponse(speech):
    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "myriad-assistant-demo-webhook"
    }


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    city = parameters.get("geo-city")
    if city is None:
        return None

    return "select * from weather.forecast where woeid in (select woeid from geo.places(1) where text='" + city + "')"


def makeWebhookResult(data):
    query = data.get('query')
    if query is None:
        return {}

    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    condition = item.get('condition')
    if condition is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Today in " + location.get('city') + ": " + condition.get('text') + \
             ", the temperature is " + condition.get('temp') + " " + units.get('temperature')

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "apiai-weather-webhook-sample"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
