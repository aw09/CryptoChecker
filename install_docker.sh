#!/bin/bash

sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo systemctl status docker --no-pager
sudo groupadd docker
sudo usermod -aG docker $USER
echo "Docker installed successfully"