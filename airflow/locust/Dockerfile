FROM python:3.9-slim

WORKDIR /mnt/locust

# Install Locust
RUN pip install locust==2.20.0

# Copy locust files
COPY locustfile.py .
COPY requirements.txt .

# Install additional requirements
RUN pip install -r requirements.txt

EXPOSE 8089

CMD ["locust", "-f", "/mnt/locust/locustfile.py", "--host=http://streamlit-service"]
