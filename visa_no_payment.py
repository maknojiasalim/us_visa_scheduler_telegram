import argparse
import time
import json
import random
import requests
import configparser
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from embassy import *

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.ini')
args = parser.parse_args()

config = configparser.ConfigParser()
config.read(args.config)

# Personal Info:
# Account and current appointment info from https://ais.usvisa-info.com
USERNAME = config['PERSONAL_INFO']['USERNAME']
PASSWORD = config['PERSONAL_INFO']['PASSWORD']
# Find SCHEDULE_ID in re-schedule page link:
# https://ais.usvisa-info.com/en-am/niv/schedule/{SCHEDULE_ID}/appointment
SCHEDULE_ID = config['PERSONAL_INFO']['SCHEDULE_ID']
GROUP_ID = config['PERSONAL_INFO']['GROUP_ID']
# Embassy Section:
YOUR_EMBASSY = config['PERSONAL_INFO']['YOUR_EMBASSY']
EMBASSY = Embassies[YOUR_EMBASSY][0]
FACILITY_ID = Embassies[YOUR_EMBASSY][1]
REGEX_CONTINUE = Embassies[YOUR_EMBASSY][2]

# Notification:
TELEGRAM_BOT_TOKEN = config['NOTIFICATION']['TELEGRAM_BOT_TOKEN']
TELEGRAM_CHAT_ID = config['NOTIFICATION']['TELEGRAM_CHAT_ID']
# TELEGRAM_MESSAGE_THREAD_ID = config['NOTIFICATION']['TELEGRAM_MESSAGE_THREAD_ID']

# Time Section:
minute = 60
hour = 60 * minute
# Time between steps (interactions with forms)
STEP_TIME = 0.5
# Time between retries/checks for available dates (seconds)
RETRY_TIME_L_BOUND = config['TIME'].getfloat('RETRY_TIME_L_BOUND')
RETRY_TIME_U_BOUND = config['TIME'].getfloat('RETRY_TIME_U_BOUND')
# Cooling down after WORK_LIMIT_TIME hours of work (Avoiding Ban)
WORK_LIMIT_TIME = config['TIME'].getfloat('WORK_LIMIT_TIME')
WORK_COOLDOWN_TIME = config['TIME'].getfloat('WORK_COOLDOWN_TIME')
# Temporary Banned (empty list): wait COOLDOWN_TIME hours
BAN_COOLDOWN_TIME = config['TIME'].getfloat('BAN_COOLDOWN_TIME')

# CHROMEDRIVER
# Details for the script to control Chrome
LOCAL_USE = config['CHROMEDRIVER'].getboolean('LOCAL_USE')
# Optional: HUB_ADDRESS is mandatory only when LOCAL_USE = False
HUB_ADDRESS = config['CHROMEDRIVER']['HUB_ADDRESS']

SIGN_IN_LINK = f"https://ais.usvisa-info.com/{EMBASSY}/niv/users/sign_in"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment"
PAYMENT_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/payment"
DATE_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"
SIGN_OUT_LINK = f"https://ais.usvisa-info.com/{EMBASSY}/niv/users/sign_out"
GROUP_LINK = f"https://ais.usvisa-info.com/en-il/niv/groups/{GROUP_ID}"


def send_notification(title, msg):
    print(f"Sending notification!")
    if TELEGRAM_BOT_TOKEN:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            # 'message_thread_id': TELEGRAM_MESSAGE_THREAD_ID,
            'text': msg,
        }
        requests.post(url, data)


def auto_action(label, find_by, el_type, action, value, sleep_time=0):
    print("\t"+ label +":", end="")
    # Find Element By
    match find_by.lower():
        case 'id':
            item = driver.find_element(By.ID, el_type)
        case 'name':
            item = driver.find_element(By.NAME, el_type)
        case 'class':
            item = driver.find_element(By.CLASS_NAME, el_type)
        case 'xpath':
            item = driver.find_element(By.XPATH, el_type)
        case _:
            return 0
    # Do Action:
    match action.lower():
        case 'send':
            item.send_keys(value)
        case 'click':
            item.click()
        case _:
            return 0
    print("\t\tCheck!")
    if sleep_time:
        time.sleep(sleep_time)


def start_process():
    # Bypass reCAPTCHA
    driver.get(SIGN_IN_LINK)
    time.sleep(STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))
    auto_action("Click bounce", "xpath", '//a[@class="down-arrow bounce"]', "click", "", STEP_TIME)
    auto_action("Email", "id", "user_email", "send", USERNAME, STEP_TIME)
    auto_action("Password", "id", "user_password", "send", PASSWORD, STEP_TIME)
    auto_action("Privacy", "class", "icheckbox", "click", "", STEP_TIME)
    auto_action("Enter Panel", "name", "commit", "click", "", STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), '" + REGEX_CONTINUE + "')]")))
    print("\n\tlogin successful!\n")
    print(f'Cookies: {driver.get_cookies()}')


def get_first_available_appointments():
    driver.get(PAYMENT_URL)
    res = {}
    for i in range(1, 3):
        location = driver.find_elements(by=By.XPATH, value=f'//*[@id="paymentOptions"]/div[2]/table/tbody/tr[{i}]/td[1]')
        status = driver.find_elements(by=By.XPATH, value=f'//*[@id="paymentOptions"]/div[2]/table/tbody/tr[{i}]/td[2]')
        if not location or not status:
            return None
        location = location[0].text
        status = status[0].text
        res[location] = status
    return res


if LOCAL_USE:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
else:
    driver = webdriver.Remote(command_executor=HUB_ADDRESS, options=webdriver.ChromeOptions())


if __name__ == "__main__":
    first_loop = True
    prev_available_appointments = None
    while 1:
        try:
            if first_loop:
                t0 = time.time()
                total_time = 0
                Req_count = 0
                start_process()
                first_loop = False

            Req_count += 1
            msg = "-" * 60 + f"\nRequest count: {Req_count}, Log time: {datetime.today()}\n"
            print(msg)
            appointments = get_first_available_appointments()
            if all(x == "No Appointments Available" for x in appointments.values()):
                print(f'Probably banned, cooldown for {BAN_COOLDOWN_TIME}h')
                time.sleep(BAN_COOLDOWN_TIME * hour)
            if appointments is not None and appointments != prev_available_appointments:
                send_notification('SUCCESS', json.dumps(appointments, sort_keys=True))
            else:
                RETRY_WAIT_TIME = random.randint(RETRY_TIME_L_BOUND, RETRY_TIME_U_BOUND)
                t1 = time.time()
                total_time = t1 - t0
                msg = "\nWorking Time:  ~ {:.2f} minutes".format(total_time/minute)
                print(msg)
                if total_time > WORK_LIMIT_TIME * hour:
                    # Let program rest a little
                    print("REST", f"Break-time after {WORK_LIMIT_TIME} hours | Repeated {Req_count} times")
                    driver.get(SIGN_OUT_LINK)
                    time.sleep(WORK_COOLDOWN_TIME * hour)
                    first_loop = True
                else:
                    msg = "Retry Wait Time: "+ str(RETRY_WAIT_TIME)+ " seconds"
                    print(msg)
                    time.sleep(RETRY_WAIT_TIME)
            if appointments is not None:
                prev_available_appointments = appointments
        except:
            # Exception Occured
            msg = f"Break the loop after exception! I will continue in a few minutes\n"
            END_MSG_TITLE = "EXCEPTION"
            traceback.print_exc()
            # send_notification(END_MSG_TITLE, msg)
            time.sleep(random.randint(RETRY_TIME_L_BOUND, RETRY_TIME_U_BOUND))

print(msg)
send_notification(END_MSG_TITLE, msg)
driver.get(SIGN_OUT_LINK)
driver.stop_client()
driver.quit()
