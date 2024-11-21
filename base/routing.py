# routing.py
from django.urls import path, re_path
from .consumers import *

websocket_urlpatterns = [
    path("ws/chatroom/<chatroom_name>", ChatroomConsumer.as_asgi()),
    path("ws/room/<str:room_name>/", BracketConsumer.as_asgi()),
    path("ws/online/", OnlineConsumer.as_asgi()),
    path("ws/pong/<room_no>/<split_no>", PongConsumerTournament.as_asgi()),
    path("ws/pong/<room_no>", PongConsumer.as_asgi()),
]