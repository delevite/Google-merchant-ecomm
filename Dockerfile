# Dockerfile
# Use a slim Python image for smaller size
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port Flask runs on
EXPOSE 8000

# Command to run the application using Gunicorn
# Adjust 'server:app' if your Flask app instance is named differently
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "server:app"]