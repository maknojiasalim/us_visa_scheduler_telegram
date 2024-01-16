# visa_rescheduler
The visa_rescheduler is a bot for US VISA (usvisa-info.com) appointment rescheduling. This bot can help you reschedule your appointment to your desired time period.

## How to use
1. Install some libs for chromedriver. run this as docker. session timeout is 2hrs
sudo docker run --network=XXXXX --name=selenium-chrome --ip=192.168.0.XX -e SE_NODE_SESSION_TIMEOUT=7200 -d -p 4444:4444 selenium/standalone-chrome

2. remove .example from config.ini and edit required config

3. ./run_docker_rechedule.sh


FACILITY_ID = 17 for London

Schedule ID and Country code

Once sign in and go to the page where you can reschedule the appointment, you can find it on the URL

country_code can be easily found from the URL prefix. For example https://ais.usvisa-info.com/es-co/, the country-code is es-coFACILITY_ID = 17 for London

Schedule ID and Country code

Once sign in and go to the page where you can reschedule the appointment, you can find it on the URL

country_code can be easily found from the URL prefix. For example https://ais.usvisa-info.com/es-co/, the country-code is es-co
