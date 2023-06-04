docker build -t us_visa_scheduler --network=host .
docker run -it --rm --net=host --name shch_us_visa_scheduler us_visa_scheduler
