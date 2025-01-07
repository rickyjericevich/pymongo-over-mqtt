# Use the latest Python slim image as the base image
FROM python:3.13-slim

ARG LOG_LEVEL=INFO BROKER_HOST=localhost MQTT_PORT=1883 MONGODB_URI=mongodb://localhost:27017 BASE_TOPIC=mongodb

# Set the working directory to /app
WORKDIR /app

COPY requirements.txt .

# Install the grpcio-tools package
RUN pip install -r requirements.txt

# Copy the python files from to the working directory
COPY . .

# Set the environment variable for Python logging
ENV PYTHONUNBUFFERED=1 LOG_LEVEL=$LOG_LEVEL BROKER_HOST=$BROKER_HOST MQTT_PORT=$MQTT_PORT MONGODB_URI=$MONGODB_URI BASE_TOPIC=$BASE_TOPIC

# Run the exhook_server.py file
CMD ["python", "main.py"]
