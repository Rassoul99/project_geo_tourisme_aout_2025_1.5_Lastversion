FROM python:3.9-slim

WORKDIR /mnt/locust

# Install Locust and dependencies
RUN pip install locust==2.20.0

# Copy locust files
COPY locustfile.py .
COPY requirements.txt .

# Install any additional requirements
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

EXPOSE 8089
