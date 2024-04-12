# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container to /app
WORKDIR /app
ADD requirements.txt /app

# Add the current directory contents into the container at /app
VOLUME /app

# Set the timezone in the Docker image
RUN echo "Asia/Jakarta" > /etc/timezone
RUN dpkg-reconfigure -f noninteractive tzdata
ENV TZ="Asia/Jakarta"

# Install gcc and python3-dev
RUN apt-get update && apt-get install -y gcc python3-dev

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 8080 available to the world outside this container
#EXPOSE 8080

# Run telegram_bot.py when the container launches
CMD ["python", "telegram_bot.py"]
