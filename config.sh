#!/usr/bin/env bash
export SLACK_BOT_ID='U3PAJ90AJ'
export SLACK_BOT_TOKEN='XXX'
export PLOTLY_USER='pafortin'
export PLOTLY_TOKEN='XXX'
pyvenv wtfbot-venv
source wtfbot-venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
