docker build -t usvs --network=host .
docker run -it --rm --net=host --name usvs_container -v "$PWD":/app -w /app usvs python visa_reschedule.py --config config.ini
