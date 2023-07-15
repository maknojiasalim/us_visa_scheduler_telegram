import argparse
import time
import json
import random
import requests
import configparser
import traceback
import yaml
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.ini')
args = parser.parse_args()

config = {}
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)

# Time Section:
minute = 60
hour = 60 * minute
# Time between steps (interactions with forms)
STEP_TIME = 3.0


def get_links_for_embassy(user_config, embassy_config):
    schedule_id = user_config['schedule_id']
    group_id = user_config['group_id']
    country_code = embassy_config['country_code']
    facility_id = embassy_config['facility_id']
    return {
        'sign_in_link': f"https://ais.usvisa-info.com/{country_code}/niv/users/sign_in",
        'appointment_url': f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/appointment",
        'payment_url': f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/payment",
        'date_url': f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/appointment/days/{facility_id}.json?appointments[expedite]=false",
        'time_url': f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/appointment/times/{facility_id}.json?date=%s&appointments[expedite]=false",
        'sign_out_link': f"https://ais.usvisa-info.com/{country_code}/niv/users/sign_out",
        'group_link': f"https://ais.usvisa-info.com/en-il/niv/groups/{group_id}",
    }


def send_notification(title, msg):
    data = {
        'chat_id': config['telegram']['chat_id'],
        'text': msg,
    }
    token = config['telegram']['bot_token']
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    if config['telegram']['thread_id']:
        data.update({'message_thread_id': config['telegram']['thread_id']})
    print(f"Sending notification {data}")
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


def start_process(user_config, embassy_config, embassy_links):
    # Bypass reCAPTCHA
    driver.get(embassy_links['sign_in_link'])
    time.sleep(STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))
    auto_action("Click bounce", "xpath", '//a[@class="down-arrow bounce"]', "click", "", STEP_TIME)
    auto_action("Email", "id", "user_email", "send", user_config['email'], STEP_TIME)
    auto_action("Password", "id", "user_password", "send", user_config['password'], STEP_TIME)
    auto_action("Privacy", "class", "icheckbox", "click", "", STEP_TIME)
    auto_action("Enter Panel", "name", "commit", "click", "", STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), '" + embassy_config['continue'] + "')]")))
    print("\n\tlogin successful!\n")
    print(f'Cookies: {driver.get_cookies()}')


def get_first_available_appointments(embassy_links):
    driver.get(embassy_links['payment_url'])
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


if config['chrome_driver']['local_use']:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
else:
    driver = webdriver.Remote(command_executor=config['chrome_driver']['hub_address'], options=webdriver.ChromeOptions())

def get_user_id():
    id = 0
    while True:
        yield id
        id = (id + 1) % len(config['users'])


if __name__ == "__main__":
    first_loop = True
    prev_available_appointments = None
    get_user = get_user_id()
    user_id = None
    banned_count = 0
    while 1:
        try:
            if first_loop:
                user_id = next(get_user)
                embassy_config = config['embassies'][0]
                links = get_links_for_embassy(config['users'][user_id], embassy_config)
                t0 = time.time()
                total_time = 0
                Req_count = 0
                start_process(
                    user_config=config['users'][user_id],
                    embassy_config=embassy_config,
                    embassy_links=links,
                )
                first_loop = False

            Req_count += 1
            print("-" * 60 + f"\nRequest count: {Req_count}, Log time: {datetime.today()}\n")
            appointments = get_first_available_appointments(links)
            if all(x == "No Appointments Available" for x in appointments.values()):
                print(f"Probably user {config['users'][user_id]['email']} is banned")
                banned_count += 1
                if banned_count == len(config['users']):
                    print(f"All users are banned, resting for {config['time']['ban_cooldown_hours']}h")
                    time.sleep(config['time']['ban_cooldown_hours'] * hour)
                    banned_count = 0
                driver.get(links['sign_out_link'])
                first_loop = True
                continue
            if appointments is not None and appointments != prev_available_appointments:
                send_notification('SUCCESS', json.dumps(appointments, sort_keys=True))
            else:
                RETRY_WAIT_TIME = random.randint(config['time']['retry_lower_bound'], config['time']['retry_upper_bound'])
                t1 = time.time()
                total_time = t1 - t0
                msg = "\nWorking Time:  ~ {:.2f} minutes".format(total_time/minute)
                print(msg)
                if total_time > config['time']['work_limit_hours'] * hour:
                    # Let program rest a little
                    print("REST", f"Break-time after {config['time']['work_limit_hours']} hours | Repeated {Req_count} times")
                    driver.get(links['sign_out_link'])
                    time.sleep(config['time']['work_cooldown_hours'] * hour)
                    first_loop = True
                else:
                    msg = "Retry Wait Time: "+ str(RETRY_WAIT_TIME)+ " seconds"
                    print(msg)
                    time.sleep(RETRY_WAIT_TIME)
            if appointments is not None:
                prev_available_appointments = appointments
        except:
            # Exception Occured
            print(f"Break the loop after exception! I will continue in a few minutes\n")
            END_MSG_TITLE = "EXCEPTION"
            traceback.print_exc()
            # send_notification(END_MSG_TITLE, msg)
            time.sleep(random.randint(config['time']['retry_lower_bound'], config['time']['retry_upper_bound']))
