import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, Thread


class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        other_user = self.scope['url_route']['kwargs']['username']
        me = self.scope['user']
        thread_obj = await database_sync_to_async(self.get_thread)(me, other_user)
        self.thread_obj = thread_obj
        chat_room = f"thread_{thread_obj.id}"  # (f string)for format method in python 3.6 and above
        self.chat_room = chat_room
        await self.channel_layer.group_add(
            self.chat_room,
            # channel_name is default attribute of channels which comes from
            # channel layers setup in settings.py this channel name is the
            # current user's channel
            self.channel_name
        )
        await self.send({
            "type": "websocket.accept"
        })

    async def websocket_receive(self, event):
        print("recivdsvsd", event)
        front_text = event.get('text', None)
        # import pdb; pdb.set_trace()
        if front_text:
            loaded_data = json.loads(front_text)
            msg = loaded_data.get('message')
            print(msg)
            user = self.scope['user']
            response = {
                'message': msg,
                'username': user.username
            }
            await database_sync_to_async(self.create_message)(msg)
            new_event = {
                "type": "websocket.send",
                "text": json.dumps(response)
            }

            # broadcasts the message(by triggering chat_message method for whole group)
            await self.channel_layer.group_send(
                self.chat_room,
                {
                    "type": "chat.message",
                    "message": new_event
                }
            )

    # actually sends the broadcasted message
    async def chat_message(self, event):
        print('chat_message', event)
        message = event['message']

        await self.send(message)

        # Send message to WebSocket
        # await self.send(text_data=json.dumps({       this didn't work coz it's
        #     'message': message                       for AsyncWebsocketConsumer
        # }))

    async def websocket_disconnect(self, event):
        print("shit", event)
        await self.channel_layer.group_discard(
            self.chat_room,
            self.channel_name
        )

    @staticmethod
    def get_thread(user, other_username):
        return Thread.objects.get_or_new(user, other_username)[0]

    def create_message(self, msg):
        return ChatMessage.objects.create(thread=self.thread_obj, user=self.scope['user'], message=msg)
