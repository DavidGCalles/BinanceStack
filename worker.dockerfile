FROM debian:buster-slim

RUN apt-get update
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get install python3-pip libmariadb-dev -y

WORKDIR /var/www/html

COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "-u"]
CMD ["code/testDeploy.py", "david", "dbWorker"]