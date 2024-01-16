FROM python:3.11
WORKDIR /app
RUN apt-get update

# Pip reqs
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# COPY . .
