from channels.generic.websocket import WebsocketConsumer
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string, get_template
from asgiref.sync import async_to_sync
import json
from .models import *
import requests
from django.core.cache import cache
from .utils import check_if_friend, check_friend_request_sent
from time import sleep

class ChatroomConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope['user']
        self.chatroom_name = self.scope['url_route']['kwargs']['chatroom_name'] 
        self.chatroom = get_object_or_404(ChatGroup, group_name=self.chatroom_name)
        
        async_to_sync(self.channel_layer.group_add)(
            self.chatroom_name, self.channel_name
        )
        
        # add and update online users
        if self.user not in self.chatroom.users_online.all():
            self.chatroom.users_online.add(self.user)
            self.update_online_count()
        
        self.accept()
        
        
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.chatroom_name, self.channel_name
        )
        # remove and update online users
        if self.user in self.chatroom.users_online.all():
            self.chatroom.users_online.remove(self.user)
            self.update_online_count() 
        
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        body = text_data_json['body']
        
        message = GroupMessage.objects.create(
            body = body,
            author = self.user, 
            group = self.chatroom 
        )
        event = {
            'type': 'message_handler',
            'message_id': message.id,
        }
        async_to_sync(self.channel_layer.group_send)(
            self.chatroom_name, event
        )
        
    def message_handler(self, event):
        message_id = event['message_id']
        message = GroupMessage.objects.get(id=message_id)
        context = {
            'message': message,
            'user': self.user,
            'chat_group': self.chatroom
        }
        html = render_to_string("private_message/partials/chat_message_p.html", context=context)
        self.send(text_data=html)
        
        
    def update_online_count(self):
        online_count = self.chatroom.users_online.count() -1
        
        event = {
            'type': 'online_count_handler',
            'online_count': online_count
        }
        async_to_sync(self.channel_layer.group_send)(self.chatroom_name, event)
        
    def online_count_handler(self, event):
        online_count = event['online_count']
        
        chat_messages = ChatGroup.objects.get(group_name=self.chatroom_name).chat_messages.all()[:30]
        author_ids = set([message.author.id for message in chat_messages])
        users = User.objects.filter(id__in=author_ids)
        
        context = {
            'online_count' : online_count,
            'chat_group' : self.chatroom,
            'users': users
        }
        html = render_to_string("chat/partials/online_count.html", context)
        self.send(text_data=html) 


class PongConsumer(WebsocketConsumer):
    players = []
    score = {'player1': 0, 'player2': 0}
    game_active = True
    room_no = 0
    room = None
    player1_name = None
    player2_name = None

    def connect(self):
        # Initialize user and room
        self.user = self.scope['user']
        self.room_no = self.scope['url_route']['kwargs']['room_no']
        self.room = get_object_or_404(Room, id=self.room_no)

        # Add player to the game
        if len(self.players) < 2:
            self.players.append(self)
            self.accept()

            # Assign player number and name
            if len(self.players) == 1:
                self.player = 1
                PongConsumer.player1_name = self.user.username
                self.user.matches_played += 1
                self.user.save()
                print(PongConsumer.player1_name)
            else:
                self.player = 2
                PongConsumer.player2_name = self.user.username
                self.user.matches_played += 1
                self.user.save()
                print(PongConsumer.player2_name)

            if len(self.players) == 2:
                self.start_game()
        else:
            self.close()

    def disconnect(self, close_code):
        if self in self.players:
            self.players.remove(self)

    def receive(self, text_data):
        if not self.game_active:
            return

        data = json.loads(text_data)

        # Check if ball reset event and update scores
        if 'reset' in data:
            if data['reset'] == 'player1':
                self.score['player1'] += 1
            elif data['reset'] == 'player2':
                self.score['player2'] += 1

            # Check if either player has reached the points limit
            if self.score['player1'] >= self.room.points or self.score['player2'] >= self.room.points:
                self.end_game()

            # Broadcast score update to all players
            score_update = {
                'type': 'score_update',
                'player1_score': self.score['player1'],
                'player2_score': self.score['player2']
            }
            for player in self.players:
                player.send(text_data=json.dumps(score_update))

        # Broadcast the received data to both players
        for player in self.players:
            player.send(text_data=json.dumps(data))

    def start_game(self):
        # Send initial state to both players
        initial_state = {
            'paddle1': {'y': 0},
            'paddle2': {'y': 0},
            'ball': {'x': 0, 'y': 0},
            'score': self.score
        }
        for player in self.players:
            player.send(text_data=json.dumps({'type': 'start_game', **initial_state}))
            player.send(text_data=json.dumps({'type': 'state_update', **initial_state}))

    def end_game(self):
        # Mark game as inactive
        self.game_active = False

        # Determine the winner
        winner = PongConsumer.player1_name if self.score['player1'] >= self.room.points else PongConsumer.player2_name

        if self.user.username == winner:
            self.user.wins += 1
            self.user.save()
            opp = None
            if self.user.username == PongConsumer.player1_name:
                opp = User.objects.get(username=PongConsumer.player2_name)
            else:
                opp = User.objects.get(username=PongConsumer.player1_name)
            opp.losses += 1
            opp.save()
        else:
            self.user.losses += 1
            self.user.save()
            opp = None
            if self.user.username == PongConsumer.player1_name:
                opp = User.objects.get(username=PongConsumer.player2_name)  
            else:
                opp = User.objects.get(username=PongConsumer.player1_name)
            opp.wins += 1
            opp.save()

        # Broadcast game-over message to all players
        game_over_message = {
            'type': 'game_over',
            'winner': winner,
            'player1_score': self.score['player1'],
            'player2_score': self.score['player2']
        }
        for player in self.players:
            player.send(text_data=json.dumps(game_over_message))

        # Get the match ID
        match_id = self.room.matches.get('id')

        # Prepare and send result to the server
        url = "http://thirdweb:3333/store_results"
        payload = json.dumps({
            "id": match_id, 
            "player1": PongConsumer.player1_name,
            "player2": PongConsumer.player2_name,
            "score1": self.score['player1'],
            "score2": self.score['player2'],
            "winner": winner
        })
        print(payload)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=payload)
        print(response.text)

        # Mark room as expired and save
        self.room.is_expired = True
        self.room.save()


class PongConsumerTournament(WebsocketConsumer):
    rooms = {}  # Dictionary to store players for each room and split
    games = {}  # Dictionary to store game state per room_key
    user = None
    room_no = 0
    split_no = 0
    room = None
    matches = None

    def connect(self):
        self.user = self.scope['user']
        self.room_no = self.scope['url_route']['kwargs']['room_no']
        self.split_no = self.scope['url_route']['kwargs']['split_no']
        self.room = get_object_or_404(Room, id=self.room_no)
        self.matches = self.room.matches

        room_key = f"{self.room_no}_{self.split_no}"

        if room_key not in self.rooms:
            self.rooms[room_key] = []
            self.games[room_key] = {
                'score': {'player1': 0, 'player2': 0},
                'game_active': True,
                'players': {},
            }

        current_match = None
        if self.room.is_final:
            current_match = self.matches['final']
            print("final match")
        elif int(self.split_no) < len(self.matches['semifinals']) + 1:
            current_match = self.matches['semifinals'][int(self.split_no) - 1]

        if not current_match:
            self.close()
            return

        if len(self.rooms[room_key]) < 2:
            self.rooms[room_key].append(self)
            self.accept()

            if self.user.username == current_match['player1']:
                self.player = 'player1'
                self.user.matches_played += 1
                self.user.save()
                self.games[room_key]['players']['player1'] = self.user.username
            elif self.user.username == current_match['player2']:
                self.player = 'player2'
                self.user.matches_played += 1
                self.user.save()
                self.games[room_key]['players']['player2'] = self.user.username
            else:
                self.close()
                return

            if len(self.rooms[room_key]) == 2:
                self.start_game()
        else:
            self.close()

    def disconnect(self, close_code):
        room_key = f"{self.room_no}_{self.split_no}"
        if room_key in self.rooms and self in self.rooms[room_key]:
            self.rooms[room_key].remove(self)
            if not self.rooms[room_key]:
                # Clean up room and game state if no players are left
                del self.rooms[room_key]
                del self.games[room_key]

    def receive(self, text_data):
        room_key = f"{self.room_no}_{self.split_no}"

        if not self.games.get(room_key, {}).get('game_active', False):
            return

        data = json.loads(text_data)

        if 'reset' in data:
            if data['reset'] == 'player1':
                self.games[room_key]['score']['player1'] += 1
            elif data['reset'] == 'player2':
                self.games[room_key]['score']['player2'] += 1

            # Check if either player has reached the points limit
            if (self.games[room_key]['score']['player1'] >= self.room.points or
                self.games[room_key]['score']['player2'] >= self.room.points):
                self.end_game()

            # Broadcast score update to all players in this room
            score_update = {
                'type': 'score_update',
                'player1_score': self.games[room_key]['score']['player1'],
                'player2_score': self.games[room_key]['score']['player2']
            }
            for player in self.rooms[room_key]:
                player.send(text_data=json.dumps(score_update))

        # Broadcast the received data to both players in this room
        for player in self.rooms[room_key]:
            player.send(text_data=json.dumps(data))

    def start_game(self):
        room_key = f"{self.room_no}_{self.split_no}"
        # Send initial state to both players
        initial_state = {
            'paddle1': {'y': 0},
            'paddle2': {'y': 0},
            'ball': {'x': 0, 'y': 0},
            'score': self.games[room_key]['score']
        }
        for player in self.rooms[room_key]:
            player.send(text_data=json.dumps({'type': 'start_game', **initial_state}))
            player.send(text_data=json.dumps({'type': 'state_update', **initial_state}))

    def end_game(self):
        room_key = f"{self.room_no}_{self.split_no}"

        # Mark game as inactive
        self.games[room_key]['game_active'] = False

        if self.room.is_final:
            current_match = self.matches['final']
            self.room.is_completed = True
            self.room.save()
            print("setting final match as completed")
        elif int(self.split_no) < len(self.matches['semifinals']) + 1:
            current_match = self.matches['semifinals'][int(self.split_no) - 1]

        match_id = current_match['id']
        print(match_id)

        # Determine the winner
        score = self.games[room_key]['score']
        winner = 'player1' if self.games[room_key]['score']['player1'] >= self.room.points else 'player2'
        winner_name = self.games[room_key]['players'].get(winner, 'Unknown')

        if self.user.username == winner:
            self.user.wins += 1
            self.user.save()
            opp = None
            if self.user.username == self.games[room_key]['players'].get('player1', 'Unknown'):
                opp = User.objects.get(username=self.games[room_key]['players'].get('player2', 'Unknown'))
            else:
                opp = User.objects.get(username=self.games[room_key]['players'].get('player1', 'Unknown'))
            opp.losses += 1
            opp.save()
        else:
            self.user.losses += 1
            self.user.save()
            opp = None
            if self.user.username == self.games[room_key]['players'].get('player1', 'Unknown'):
                opp = User.objects.get(username=self.games[room_key]['players'].get('player2', 'Unknown'))
            else:
                opp = User.objects.get(username=self.games[room_key]['players'].get('player1', 'Unknown'))
            opp.wins += 1
            opp.save()

        # Broadcast game-over message to all players in this room
        game_over_message = {
            'type': 'game_over',
            'winner': winner_name,
            'player1_score': score['player1'],
            'player2_score': score['player2']
        }
        for player in self.rooms[room_key]:
            player.send(text_data=json.dumps(game_over_message))

        # Optionally, send game results to the server or store them
        url = "http://thirdweb:3333/store_results"
        payload = json.dumps({
            "id": match_id, 
            "player1": self.games[room_key]['players'].get('player1', 'Unknown'),
            "player2": self.games[room_key]['players'].get('player2', 'Unknown'),
            "score1": score['player1'],
            "score2": score['player2'],
            "winner": winner_name
        })
        print(payload)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=payload)
        print(response.text)

        self.room.is_expired = True
        self.room.is_final = True
        self.room.save()

        # Clean up room and game state
        del self.rooms[room_key]
        del self.games[room_key]


class BracketConsumer(WebsocketConsumer):
    def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'room_{self.room_name}'
            self.room = get_object_or_404(Room, id=self.room_name)

            # Join the WebSocket group
            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name,
                self.channel_name
            )

            self.accept()

            # Increment user count in cache
            user_count = cache.get(self.room_group_name + '_user_count', 0)
            user_count += 1
            cache.set(self.room_group_name + '_user_count', user_count)

            # Notify others about the new connection
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_user_count',
                }
            )
        except Exception as e:
            print(f"Exception in connect: {e}")
            self.close()


    def disconnect(self, close_code):
        # Leave the WebSocket group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

        # Decrement user count in cache
        user_count = cache.get(self.room_group_name + '_user_count', 0)
        user_count = max(user_count - 1, 0)
        cache.set(self.room_group_name + '_user_count', user_count)

        # Notify others about the disconnection
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_user_count',
            }
        )

    def update_user_count(self, event):
        # Get the user count from cache
        user_count = cache.get(self.room_group_name + '_user_count', 0)
        print(user_count)

        # Send the updated count to the client
        self.send(text_data=json.dumps({
            'type': 'user_count',
            'user_count': user_count,
        }))

        if self.room.is_final:
            # If 2 users are connected, broadcast a "start_countdown" message
            if user_count == 2:
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'start_countdown',
                    }
                )

        # If 4 users are connected, broadcast a "start_countdown" message
        if user_count == 4:
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'start_countdown',
                }
            )

    def start_countdown(self, event):
        # Send a message to the front end to start the countdown timer
        self.send(text_data=json.dumps({
            'type': 'start_countdown',
        }))


class OnlineConsumer(WebsocketConsumer):
    online_users = set()

    def connect(self):
        self.user = self.scope['user']
        if self.user.is_authenticated:
            OnlineConsumer.online_users.add(self.user.username)
            self.accept()

    def disconnect(self, close_code):
        if self.user.is_authenticated:
            OnlineConsumer.online_users.discard(self.user.username)

    def receive(self, text_data):
        data = json.loads(text_data)
        if data['type'] == 'check_user_online':
            response = {
                'type': 'user_online_status',
                'username': data['username'],
                'is_online': data['username'] in OnlineConsumer.online_users
            }
            self.send(text_data=json.dumps(response))
        