#!/bin/bash

sudo apt-get update -y && \
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common && \
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" -y && \
sudo apt-get update -y && \
sudo apt-get install -y docker-ce && \
sudo systemctl status docker --no-pager && \
sudo groupadd docker && \
sudo usermod -aG docker $USER && \
echo "Docker installed successfully" 