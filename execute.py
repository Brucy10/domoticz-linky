#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""

@author: k20human
Based on https://github.com/Asdepique777/jeedom_linky

"""

#
# Copyright (C) 2017 Kévin Mathieu
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.
#

import linky
import json
import os
import sys
import logging
import datetime
import url
import time
from dateutil.relativedelta import relativedelta
from logging.handlers import RotatingFileHandler

# Configuration file path
configurationFile = './config.json'

# Configure logs
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')

file_handler = RotatingFileHandler('linky.log', 'a', 1000000, 1)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

steam_handler = logging.StreamHandler()
steam_handler.setLevel(logging.INFO)
steam_handler.setFormatter(formatter)
logger.addHandler(steam_handler)

# Check if configuration file exists
if os.path.isfile(configurationFile):
    # Import configuration file
    with open(configurationFile) as data_file:
        config = json.load(data_file)
else:
    logger.error('Your configuration file doesn\'t exists')
    sys.exit('Your configuration file doesn\'t exists')

# Domoticz server & port information
domoticzServer = config['domoticz_server']

# Domoticz IDX
domoticzIdx = config['domoticz_idx']

# Enedis Login
enedisLogin = config['login']

# Enedis password
enedisPassword = config['password']

# Domoticz API
domoticzApi = url.URL(domoticzServer)

# Export data to Domoticz
def export_days_values(res):
    value = res['graphe']['data'][-1]['valeur']

    if value < 0:
        raise linky.LinkyLoginException('Value is less than 0, error in API')

    # Get value from Domoticz
    counter = domoticzApi.call({
        'type': 'devices',
        'rid': domoticzIdx
    }).json()

    lastUpdate = counter['result'][0]['LastUpdate'].split(' ')[0]
    counterValue = int(float(counter['result'][0]['Counter'].replace(' kWh', '')) * 1000)

    # Send to Domoticz only if data not send today
    if lastUpdate != time.strftime("%Y-%m-%d"):
        res = domoticzApi.call({
            'type': 'command',
            'param': 'udevice',
            'idx': domoticzIdx,
            'svalue': counterValue + int(value * 1000)
        })

        if res.status_code == 200:
            logger.info('Data successfully send to Domoticz')
        else:
            raise linky.LinkyLoginException('Can\'t add data to Domoticz')
    else:
        logger.info('Data already successfully send to Domoticz today')

# Date formatting
def dtostr(date):
    return date.strftime("%d/%m/%Y")

def get_data_per_day(token):
    today = datetime.date.today()

    return linky.get_data_per_day(token, dtostr(today - relativedelta(days=1, months=1)),
                                     dtostr(today - relativedelta(days=1)))

def call_enedis_api():
    token = linky.login(enedisLogin, enedisPassword)

    res_day = get_data_per_day(token)

    # If cookie has expired retry
    if res_day is None:
        logger.info("Cookie has expired")
        token = linky.login(enedisLogin, enedisPassword)
        res_day = get_data_per_day(token)

    return res_day

# Main script
def main():
    try:
        logger.info("Logging in as %s", enedisLogin)
        logger.info("Logged in successfully!")
        logger.info("Retreiving data...")

        # Get datas
        res_day = call_enedis_api()

        logger.info("Got datas!")

        # Send to Domoticz
        export_days_values(res_day)

    except linky.LinkyLoginException as exc:
        logger.error(exc)
        sys.exit(1)

if __name__ == "__main__":
    main()
