#!/bin/bash

# Navigate to your repository
cd $HOME/CryptoChecker

# Add all changes to staging
git add balance_vs_btc.csv

# Commit changes
git commit -m "Auto push balance_vs_btc.csv"

# Push changes to GitHub
git push origin master
