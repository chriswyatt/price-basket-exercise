#!/usr/bin/env bash

if [[ ! -f price_basket.py ]]; then
  echo "Please run inside project directory"
fi

pip install --upgrade -r requirements.txt