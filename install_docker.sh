#!/bin/bash

sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates curl software-properties-common
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install docker-ce
sudo systemctl status docker
sudo groupadd docker
sudo usermod -aG docker $USER
echo "Docker installed successfully"