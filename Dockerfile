FROM python:3.11
WORKDIR /app
# Install some libs for chromedriver. run this as docker. session timeout is 2hrs
#sudo docker run --network=myipvlan --name=selenium-chrome --ip=192.168.0.210 -e SE_NODE_SESSION_TIMEOUT=7200 -d -p 4444:4444 selenium/standalone-chrome
RUN apt-get update

# Pip reqs
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# COPY . .
