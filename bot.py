import os
from slack_sdk import WebClient
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
import openai

#Environment
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

#keys
slack_token = os.environ['SLACK_TOKEN']
openai.api_key = os.environ["OPENAI_API_KEY"]

#API slack
client = WebClient(slack_token)

#Pido los canales del server de slack
response = client.conversations_list(types="public_channel,private_channel")
channels = response['channels']
if not channels:
    exit(0)

#Pido el id del bot
BOT_ID = client.api_call('auth.test')['user_id']

timestamp = datetime.now() - timedelta(hours=24)
timestamp = str(timestamp.timestamp())

for channel in channels:
    channel_id = channel['id']

    conversation = client.conversations_history(channel=channel_id, oldest=timestamp)

    messages = conversation['messages']
    user_ids = set()
    user_map = {}
    if not messages:
        continue
    
    print(f'current channel: #{channel["name"]}')
    prompt = ''
    for message in messages:
        if 'user' in message:
            user_id = message['user']
            if BOT_ID == user_id:
                continue
            if user_id not in user_map:
                user_map[user_id] = client.users_info(user=user_id)['user']['name']
            
            if 'thread_ts' in message: #Si el mensaje tiene respuestas (hilo)
                thread = ''
                for reply in client.conversations_replies(channel=channel_id, ts=message['thread_ts'])['messages']:
                    reply_user_id = reply['user']
                    text = reply['text'].replace('\n', '\n\t\t')
                    if reply_user_id not in user_map:
                        user_map[reply_user_id] = client.users_info(user=reply_user_id)['user']['name']
                    if reply['thread_ts'] != reply['ts']: #Si es una respuesta
                        thread = thread + (f"\t-{user_map[reply_user_id]}: {text}\n")
                    else: #Si es el mensaje original del hilo
                        thread = thread + (f"-{user_map[reply_user_id]}: {text}\n")
                prompt = thread + prompt
            else:
                text = message['text'].replace('\n', '\n\t')
                prompt = (f"-{user_map[message['user']]}: {text}\n") + prompt 


    prompt = "Resumime la siguiente conversación de un canal de slack. Resumila lo máximo posible y mostrame solo la información mas importante. Si el texto está indentado significa que ese mensaje pertenece a un hilo (iniciado en el último mensaje no indentado):\n\n" + prompt
    response = openai.ChatCompletion.create(model='gpt-3.5-turbo',
                                        messages=[{"role": "system", "content": prompt}],
                                        max_tokens=512)
    print("------------------------- prompt -------------------------")
    print(prompt)
    client.chat_postMessage(channel=channel_id, text=f"Resumen diario:\n\n {response['choices'][0]['message']['content']}")

exit(1)
