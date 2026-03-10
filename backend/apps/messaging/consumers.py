"""
WebSocket consumer for real-time chat.
Messages are moderated before being broadcast to other participants.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        user = self.scope['user']

        if not user.is_authenticated:
            await self.close()
            return

        # Verify user is a participant
        is_participant = await self._is_participant(user, self.conversation_id)
        if not is_participant:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        body = data.get('body', '').strip()
        if not body:
            return

        user = self.scope['user']
        message, result = await self._create_and_moderate(user, self.conversation_id, body)

        if result.status == 'blocked':
            await self.send(text_data=json.dumps({
                'type': 'message_blocked',
                'reason': 'Your message contained inappropriate content and could not be sent.',
            }))
            return

        if result.status == 'flagged':
            await self.send(text_data=json.dumps({
                'type': 'message_flagged',
                'message': 'Your message is being reviewed by a moderator.',
            }))
            return

        # Broadcast delivered message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.pk,
                'body': body,
                'sender_id': user.pk,
                'sender_name': user.full_name,
                'sent_at': message.sent_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def _is_participant(self, user, conversation_id):
        from .models import Conversation
        return Conversation.objects.filter(pk=conversation_id, participants=user).exists()

    @database_sync_to_async
    def _create_and_moderate(self, user, conversation_id, body):
        from .models import Conversation, Message, MessageRead
        from apps.moderation.service import ModerationService
        conv = Conversation.objects.get(pk=conversation_id)
        message = Message.objects.create(conversation=conv, sender=user, body=body)
        MessageRead.objects.create(message=message, user=user)
        result = ModerationService.screen(message)
        return message, result
