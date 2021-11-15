FROM debian:buster-slim

RUN apt-get update
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get install python3-pip libmariadb-dev -y

WORKDIR /var/www/html
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
#RUN pip3 install python-binance mariadb pandas pandas-ta

ENTRYPOINT ["python3", "-u"]
CMD ["code/sistema.py", "david", "dbWorker"]