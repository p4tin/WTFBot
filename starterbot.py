import os
import time
from slackclient import SlackClient
import requests
import json
import plotly.plotly as py
import plotly.graph_objs as go

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
SLACK_TOKEN = os.environ.get('SLACK_BOT_TOKEN')

# constants
AT_BOT = "<@" + BOT_ID + ">"
HELP_COMMAND = "help"
LEVEL_COMMAND = "level"
STATUS_COMMAND = "status"

# instantiate Slack & Twilio clients
slack_client = SlackClient(SLACK_TOKEN)

# user cache
user_cache = dict()
cache_changed = True

def post_wtf_status_graph(channel):
    global cache_changed
    if cache_changed == True:
        py.sign_in(os.environ.get('PLOTLY_USER'), os.environ.get('PLOTLY_TOKEN'))
        x = []
        y = []
        for key in user_cache:
            if 'wtf_level' in user_cache[key]:
                x.append(user_cache[key]['user']['name'])
                y.append(user_cache[key]['wtf_level'])
        trace = go.Bar(x=x, y=y)
        data = [trace]
        layout = go.Layout(title='WTF Bar Chart - ' + time.strftime("%c"),
            width=600,
            height=250,
            xaxis=dict(title="Team Members"),
            yaxis=dict(title="WTF Level (0-100)", range=[0, 100]))
        fig = go.Figure(data=data, layout=layout)

        py.image.save_as(fig, filename='wtf-barchart.png')

    f = {'file': ('wtf-barchart.png', open('wtf-barchart.png', 'rb'), 'image/png', {'Expires':'0'})}
    response = requests.post(url='https://slack.com/api/files.upload', data=
       {'token': SLACK_TOKEN, 'title': 'WTF!?! Status Graph', 'initial_comment': 'Help your teammates with a big WTF Factor to make the team stronger.', 'channels': channel, 'media': f},
       headers={'Accept': 'application/json'}, files=f)
    cache_changed = False

def parse_level(command):
    try:
        lvl_str = command.split()[1]
    except IndexError:
        lvl_str = -2
    try:
        lvl = int(lvl_str)
    except ValueError:
        lvl = -1
    return lvl

def handle_command(command, channel, username, user_id):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    global cache_changed
    response = "Not sure what you mean _<@" + username + ">_. Use the *" + HELP_COMMAND + \
               "* to get a list of what you can do with me."
    if command.startswith(HELP_COMMAND):
        response = "Help is on the way!!!"
        resp_attach = [{'color': '#36a64f',
                        'title': 'Available Commands:', 'fields': [
                        {
                            'title': 'level',
                            'value': 'A number from 0 to 99',
                            'short': False
                        },
                        {
                            'title': 'status',
                            'value': 'No parameters required',
                            'short': False
                        }
                    ]}]
        slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, attachments=json.dumps(resp_attach), as_user=True)
    elif command.startswith(LEVEL_COMMAND):
        lvl = parse_level(command)
        user_cache[user_id]['wtf_level'] = lvl
        cache_changed = True
        response = "_<@" + username + ">_, level " + str(lvl) + " recorded.  Thanks!"
        slack_client.api_call("chat.postMessage", channel=channel,
            text=response, as_user=True)
    elif command.startswith(STATUS_COMMAND):
        post_wtf_status_graph(channel)

def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                user = []
                if output['user'] in user_cache:
                    user = user_cache[output['user']]
                if user == []:
                    payload = {'token': SLACK_TOKEN, 'user': output['user']}
                    resp = requests.get('https://slack.com/api/users.info', params=payload)
                    user = resp.json()
                    user_cache[output['user']] = user
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                       output['channel'], user['user']['name'], output['user']
            elif output and 'message' in output:
                if 'text' in output['message'] and AT_BOT in output['message']['text']:
                    user = []
                    if output['message']['user'] in user_cache:
                        user = user_cache[output['message']['user']]
                    if user == []:
                        payload = {'token': SLACK_TOKEN, 'user': output['message']['user']}
                        resp = requests.get('https://slack.com/api/users.info', params=payload)
                        user = resp.json()
                        user_cache[output['message']['user']] = user
                    return output['message']['text'].split(AT_BOT)[1].strip().lower(), \
                           output['channel'], user['user']['name'], output['message']['user']
    return None, None, None, None

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("StarterBot connected and running!")
        while True:
            message = slack_client.rtm_read()
            command, channel, username, user_id = parse_slack_output(message)
            if command and channel and username and user_id:
                handle_command(command, channel, username, user_id)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
