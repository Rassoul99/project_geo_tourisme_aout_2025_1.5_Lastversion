FROM locustio/locust:2.20.0

WORKDIR /mnt/locust

COPY locustfile.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8089
