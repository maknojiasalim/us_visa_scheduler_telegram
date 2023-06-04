FROM python:3
WORKDIR /app
COPY . .

# Install some libs for chromedriver
RUN apt-get update && apt-get install -y chromium

# Pip reqs
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Run script
CMD [ "python", "./visa.py" ]
