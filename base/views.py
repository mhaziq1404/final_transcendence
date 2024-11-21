from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.http import Http404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from uuid import uuid4
from django.utils.text import slugify
import random
from web3 import Web3
import requests
import os
from .utils import check_if_friend, check_friend_request_sent

from .models import User, ChatGroup, Room, GroupMessage, Match, Friend, Notification
from .forms import MyUserCreationForm, ChatmessageCreateForm, RoomForm, UserForm, NewGroupForm, ChatRoomEditForm, MatchScoreForm

from rest_framework_simplejwt.tokens import RefreshToken

# <!-- /*==============================
# =>  Authentication Functions
# ================================*/ -->


from django.conf import settings

def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'base/login_register.html', {'page': 'login'})

        user = authenticate(request, email=email, password=password)

        if user:
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Set JWT tokens in cookies
            response = redirect('home')
            response.set_cookie('access_token', access_token, httponly=True, secure=settings.SECURE_SSL_REDIRECT)
            response.set_cookie('refresh_token', refresh_token, httponly=True, secure=settings.SECURE_SSL_REDIRECT)
            
            login(request, user)
            messages.success(request, 'Logged in successfully.')
            return response
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'base/login_register.html', {'page': 'login'})


def logoutUser(request):
    response = redirect('home')
    
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')

    logout(request)
    messages.success(request, 'Logged out successfully.')
    return response


def registerPage(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()

            login(request, user)
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            request.session['access_token'] = access_token
            request.session['refresh_token'] = refresh_token

            messages.success(request, 'Registration successful. Please Login.')
            return redirect('login')
        else:
            messages.error(request, 'An error occurred during registration. Please check the form and try again.')

    return render(request, 'base/login_register.html', {'form': form})



# <!-- /*==============================
# =>  Room Functions
# ================================*/ -->


@login_required(login_url='login')
def home(request, chatroom_name='public-chat'):

    chat_group, created = ChatGroup.objects.get_or_create(group_name=chatroom_name)
    if created:
        chat_group.group_name = chatroom_name
        chat_group.groupchat_name = chatroom_name
        chat_group.save()
    if chat_group.is_private and request.user not in chat_group.members.all():
        raise Http404()

    chat_messages = chat_group.chat_messages.all()[:30]
    form = ChatmessageCreateForm()
    other_user = next((member for member in chat_group.members.all() if member != request.user), None)
    q = request.GET.get('q', '')
    rooms = Room.objects.filter(
        Q(name__icontains=q) |
        Q(description__icontains=q) |
        Q(points__icontains=q)
    )
    room_count = Room.objects.filter(is_expired=False).count()

    if request.htmx and request.method == 'POST':
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.author = request.user
            message.group = chat_group
            message.save()
            return render(request, 'chat/partials/chat_message_p.html', {'message': message, 'user': request.user})

    context = {
        'chat_messages': chat_messages,
        'form': form,
        'other_user': other_user,
        'chatroom_name': chatroom_name,
        'chat_group': chat_group,
        'rooms': rooms,
        'room_count': room_count,
        'user': request.user,
        'chatroom_name_ws': chat_group.groupchat_name,
        'home_chat': "Public",
    }

    return render(request, 'base/home.html', context)


def room_list(request):
    rooms = Room.objects.filter(is_expired=False)
    if request.headers.get('HX-Request'):
        return render(request, 'room/partials/room_list.html', {'rooms': rooms})
    return render(request, 'base/home.html', {'rooms': rooms})


def player_list(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    participants = room.participants.all()
    other_player = participants[1] if len(participants) > 1 else None
    context = {
        'other_player': other_player,
        'room': room,
        'participants': participants,
        'participant': request.user,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'room/partials/vsplayer.html', context)
    return render(request, 'base/room.html', {'room': room})


def kick_player(request):
    if request.method == 'POST':
        player_id = request.POST.get('player_id')
        room_id = request.POST.get('room_id')

        if player_id and room_id:
            room = get_object_or_404(Room, id=room_id)
            player = get_object_or_404(User, id=player_id)
            if player in room.participants.all():
                room.participants.remove(player)
                room.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def leave_room(request):
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        if room_id:
            room = get_object_or_404(Room, id=room_id)
            user = request.user
            if user in room.participants.all():
                room.participants.remove(user)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def check_status(request):
    room_id = request.GET.get('room_id')
    player_id = request.GET.get('player_id')

    if room_id and player_id:
        room = get_object_or_404(Room, id=room_id)
        player = get_object_or_404(User, id=player_id)
        if player not in room.participants.all():
            return JsonResponse({'status': 'kickedout'})
        if room.is_started == True:
            return JsonResponse({'status': 'started'})
    return JsonResponse({'status': 'still_in_room'})


@login_required(login_url='login')
def room(request, pk):
    room = get_object_or_404(Room, id=pk)

    if(room.is_expired == True):
        messages.error(request, 'Room already expired.')
        return redirect('home')
    
    if room.opponent_type == "AI":
        return render(request, 'base/room.html', {'room': room})

    if request.user not in room.participants.all():
        room.participants.add(request.user)

    chat_group = get_object_or_404(ChatGroup, room=room)
    chat_messages = chat_group.chat_messages.all()[:30]
    form = ChatmessageCreateForm()
    other_user = next((member for member in chat_group.members.all() if member != request.user), None)

    if chat_group.is_private and request.user not in chat_group.members.all():
        raise Http404()

    myself = request.user
    friends = get_friends(myself)

    if request.htmx:
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.author = request.user
            message.group = chat_group
            message.room = room
            message.save()
            return render(request, 'chat/partials/chat_message_p.html', {'message': message, 'user': request.user})

    context = {
        'room': room,
        'participants': room.participants.all(),
        'chat_messages': chat_messages,
        'form': form,
        'other_user': other_user,
        'chatroom_name': room.name,
        'chatroom_name_ws': chat_group.groupchat_name,
        'chat_group': chat_group,
        'friends': friends,
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'leave-room':
            if request.user in room.participants.all():
                room.participants.remove(request.user)
                return redirect('home')
            else:
                messages.error(request, "You are not a participant of this room.")

        elif action == 'ready':
            if request.user in room.participants.all():
                room.opp_ready = True
                room.save()
                return render(request, 'base/room.html', context)
            else:
                messages.error(request, "You are not a participant of this room.")

        raise Http404()

    return render(request, 'base/room.html', context)
  


@login_required(login_url='login')
def createRoom(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.host = request.user
            room.is_2player = (form.cleaned_data['opponent_type'] == 'vs Player')
            room.save()
            
            unique_suffix = uuid4().hex[:6]

            formatted_name = room.name.replace(' ', '-')

            chat_group = ChatGroup.objects.create(
                admin=request.user,
                group_name=f"{formatted_name}-{unique_suffix}",
                groupchat_name=f"{formatted_name}-{unique_suffix}",
                room=room
            )

            chat_group.members.set([request.user])

            if request.htmx:
                rooms = Room.objects.filter(is_expired=False)
                return render(request, 'room/room_list.html', {'rooms': rooms})
            else:
                messages.success(request, 'Room Created successfully.')
                return redirect('home')
        messages.error(request, 'Cannot create Room')
    else:
        form = RoomForm()

    return render(request, 'base/room_form.html', {'form': form})


@login_required(login_url='login')
def updateRoom(request, pk):
    room = get_object_or_404(Room, id=pk)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')

    form = RoomForm(instance=room)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            return redirect('home')

    return render(request, 'base/room_form.html', {'form': form, 'room': room})


@login_required(login_url='login')
def deleteRoom(request, pk):
    room = get_object_or_404(Room, id=pk)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')

    return render(request, 'base/delete.html', {'obj': room})


@login_required(login_url='login')
def ai_playnow(request):
    room = Room.objects.create(
        host=request.user,
        opponent_type="AI",
        name="vsAIGame",
        description="vsAIGame",
        is_2player=True,
        points=11
    )

    room.participants.add(request.user)
    
    room.save()
    
    return redirect('room', pk=room.id)


@login_required(login_url='login')
def join_room(request):
    if request.method == "POST":
        invitation_link = request.POST.get('invitation_link')
        room = get_object_or_404(Room, invitation_link=invitation_link)
        room.participants.add(request.user)
        messages.success(request, 'Room Found. Joining the Room')
        return redirect('room', pk=room.id)
    messages.warning(request, 'Room not Found')
    return redirect('home')


@login_required(login_url='login')
def pongPageTournament(request, pk, split_no):
    room = get_object_or_404(Room, id=pk)
    webs_name = room.id

    if request.method == 'POST':
        winner = request.POST.get('winner')
        if winner:
            # General handling for AI and Player match types
            if room.opponent_type in ['AI', 'vs Player', 'Tournament']:
                room.won_by_user = request.user if winner != 'AI' else None
                room.won_by_ai = winner == 'AI'
                room.is_expired = True
                room.save()
                return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'failed', 'error': 'No winner specified'})

    # Only handle 'Tournament' opponent type
    if room.opponent_type == 'Tournament':
        if room.is_final == True:
            matches = room.matches.get('final')
            print(matches)
            try:
                player1 = User.objects.get(username=matches['player1'])
                player2 = User.objects.get(username=matches['player2'])
            except User.DoesNotExist:
                pass

            if request.user == player1 or request.user == player2:
                return render(request, 'pong/pong_game.html', {
                    'room': room,
                    'player1': player1.username,
                    'player2': player2.username,
                    'webs_name': webs_name, 
                    'split_no': 1
                })
        else:
            matches = room.matches.get('semifinals', [])  # Access semifinal matches from JSON
        split_no = 1
        
        for match in matches:
            try:
                player1 = User.objects.get(username=match['player1'])
                player2 = User.objects.get(username=match['player2'])
            except User.DoesNotExist:
                continue

            if request.user == player1 or request.user == player2:
                return render(request, 'pong/pong_game.html', {
                    'room': room,
                    'player1': player1.username,
                    'player2': player2.username,
                    'webs_name': webs_name, 
                    'split_no': split_no
                })
            split_no += 1

    return render(request, 'pong/pong_game.html', {
        'room': room,
        'webs_name': webs_name,
        'split_no': split_no
    })

@login_required(login_url='login')
def pongPage(request, pk):
    room = get_object_or_404(Room, id=pk)
    webs_name = room.id
    room.is_started = True
    room.save()

    if request.method == 'POST':
        winner = request.POST.get('winner')
        if winner:
            if winner == 'AI':
                room.won_by_ai = True
                room.won_by_user = None
            else:
                room.won_by_user = request.user
                room.won_by_ai = False

            room.is_expired = True
            room.save()

            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'failed', 'error': 'No winner specified'})

    player2 = room.participants.exclude(id=room.host.id).first()

    match = Match(
        player1=room.host,
        player2=player2,
        round='vsplayer'
    )
    match.save()

    matches = {
        'round': match.round,
        'player1': match.player1.username,
        'player2': match.player2.username,
        'id': match.id,
    }

    room.matches = matches
    room.save()

    context = {
        'room': room,
        'webs_name': webs_name,
        'player1': room.host.username,
        'player2': player2.username if player2 else 'AI',
    }

    return render(request, 'pong/pong_game_player.html', context)


# <!-- /*==============================
# =>  User Profile Functions
# ================================*/ -->
from datetime import datetime

def get_game_results_by_username(username):

    web3 = get_blockchain_connection()

    url = "http://thirdweb:3333/get_contractAddress"

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    response = response.json()

    if response.get('status') != 'success':
        return None

    address = response.get('address')
    contract_address = Web3.to_checksum_address(address)
    contract_abi = response.get('abi')

    contract = web3.eth.contract(address=contract_address, abi=contract_abi)

    try:
        # Call the contract function
        result = contract.functions.getGameResultsByUsername(username).call()

        # The function returns multiple arrays
        ids = result[0]
        player1s = result[1]
        player2s = result[2]
        score1s = result[3]
        score2s = result[4]
        winners = result[5]
        timestamps = result[6]

        # Combine the arrays into a list of game results
        game_results = []
        for i in range(len(ids)):
            game_result = {
                "id": ids[i],
                "player1": player1s[i],
                "player2": player2s[i],
                "score1": score1s[i],
                "score2": score2s[i],
                "winner": winners[i],
                "timestamp": timestamps[i]
            }
            game_results.append(game_result)
        return game_results
    except Exception as e:
        print(f"Error calling getGameResultsByUsername: {e}")
        return None


@login_required(login_url='login')
def userProfile(request, pk):
    user = get_object_or_404(User, id=pk)
    
    # Check friendship status
    is_friend = Friend.objects.filter(
        Q(user=request.user, friend=user, confirmed=True) |
        Q(user=user, friend=request.user, confirmed=True)
    ).exists()

    # Check if a friend request has been sent
    friend_request_sent = Friend.objects.filter(user=request.user, friend=user, confirmed=False).exists()

    # Confirm mutual friend requests
    mutual_requests = Friend.objects.filter(
        (Q(user=request.user, friend=user) & Q(confirmed=False)) |
        (Q(user=user, friend=request.user) & Q(confirmed=False))
    )

    if mutual_requests.count() == 2:  # Two pending requests indicate mutuality
        mutual_requests.update(confirmed=True)
        is_friend = True
        friend_request_sent = False

    # Fetch user's rooms
    rooms = user.room_set.all()

    # Fetch unread notifications
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')

    # User statistics
    total_matches = user.matches_played
    wins = user.wins
    losses = user.losses
    winrate = (wins / total_matches) * 100 if total_matches > 0 else 0

    user_stats = {
        'matches_played': total_matches,
        'wins': wins,
        'losses': losses,
        'winrate': round(winrate, 2),  # Round to two decimal places for display
    }

    # Match history
    match_history = get_game_results_by_username(user.username)
    # match_history = [{'id': 1, 'player1': 'mmuhamad', 'player2': 'mmuhamad2', 'score1': 19, 'score2': 21, 'winner': 'mmuhamad2', 'timestamp': 1731630422}, {'id': 1, 'player1': 'mmuhamad', 'player2': 'mmuhamad42', 'score1': 19, 'score2': 21, 'winner': 'mmuhamad42', 'timestamp': 1731630988}, {'id': 780, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 1, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731633082}, {'id': 990, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 1, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731634982}, {'id': 1423, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 1, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731635609}, {'id': 1431, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 2, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731636052}, {'id': 1446, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 0, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731636222}, {'id': 1462, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 1, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731672080}, {'id': 1472, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 2, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731673352}, {'id': 1486, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 0, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731673923}, {'id': 1498, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 1, 'score2': 7, 'winner': 'mmuhamad3', 'timestamp': 1731852314}, {'id': 1512, 'player1': 'mmuhamad', 'player2': 'mmuhamad3', 'score1': 1, 'score2': 5, 'winner': 'mmuhamad3', 'timestamp': 1731853012}]
    match_history.sort(key=lambda x: x['timestamp'], reverse=True)
    for match in match_history:
        match['timestamp'] = datetime.fromtimestamp(match['timestamp'])

    context = {
        'user': user,
        'is_friend': is_friend,
        'match_history': match_history,
        'friend_request_sent': friend_request_sent,
        'rooms': rooms,
        'notifications': notifications,
        'user_stats': user_stats,
    }

    return render(request, 'base/profile.html', context)


@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)
        else:
            print(form.errors)

    return render(request, 'base/update-user.html', {'form': form})


# <!-- /*==============================
# =>  Chat Functions
# ================================*/ -->


@login_required(login_url='login')
def get_or_create_chatroom(request, username):
    if request.user.username == username:
        return redirect('home')
    
    other_user = get_object_or_404(User, username=username)
    chatroom = ChatGroup.objects.filter(is_private=True, members=request.user).first()

    if chatroom and other_user in chatroom.members.all():
        return redirect('chatroom', chatroom.group_name)

    chatroom, created = ChatGroup.objects.get_or_create(is_private=True)
    chatroom.members.add(other_user, request.user)
    return redirect('chatroom', chatroom.group_name)


@login_required(login_url='login')
def create_groupchat(request):
    if request.method == 'POST':
        form = NewGroupForm(request.POST)
        if form.is_valid():
            unique_suffix = uuid4().hex[:6]
            formatted_name = slugify(form.cleaned_data['groupchat_name'])
            group_name = f"{formatted_name}-{unique_suffix}"

            chat_group = ChatGroup.objects.create(
                admin=request.user,
                group_name=group_name,
                groupchat_name=group_name,
            )
            
            chat_group.members.set([request.user])

            request.user.group_chats.add(chat_group)
            request.user.save()

            friends_list = form.cleaned_data.get('friends_list', '').strip().split('\n')
            for friend in friends_list:
                friend = friend.strip()
                print(friend)
                if friend:
                    try:
                        friend_user = User.objects.get(username=friend)
                        friend_user.group_chats.add(chat_group)
                        chat_group.members.add(friend_user)
                    except User.DoesNotExist:
                        pass
            
            return redirect('messages')

    else:
        form = NewGroupForm()

    return render(request, 'chat/create_groupchat.html', {'form': form})



@login_required(login_url='login')
def create_privatechat(request, user_id):
    user = get_object_or_404(User, id=user_id)

    group_name = f"{request.user.username}_{user.username}"
    group_name2 = f"{user.username}_{request.user.username}"

    if request.user.group_chats.filter(group_name=group_name2).exists():
        return redirect('chat_group_detail', id=request.user.group_chats.get(group_name=group_name2).id)
    if request.user.group_chats.filter(group_name=group_name).exists():
        return redirect('chat_group_detail', id=request.user.group_chats.get(group_name=group_name).id)

    chat_group = ChatGroup.objects.create(
        admin=request.user,
        group_name=group_name,
        groupchat_name=group_name,
        is_private = True,
    )

    chat_group.members.add(request.user)
    chat_group.members.add(user)

    request.user.group_chats.add(chat_group)
    user.group_chats.add(chat_group)

    request.user.save()
    user.save()

    return redirect('chat_group_detail', id=chat_group.id)


@login_required(login_url='login')
def chatroom_edit_view(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    if request.user != chat_group.admin:
        raise Http404()

    form = ChatRoomEditForm(instance=chat_group)

    if request.method == 'POST':
        form = ChatRoomEditForm(request.POST, instance=chat_group)
        if form.is_valid():
            form.save()
            remove_members = request.POST.getlist('remove_members')
            for member_id in remove_members:
                member = get_object_or_404(User, id=member_id)
                chat_group.members.remove(member)
            return redirect('chatroom', chatroom_name)

    return render(request, 'chat/chatroom_edit.html', {'form': form, 'chat_group': chat_group})


@login_required(login_url='login')
def chatroom_delete_view(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    if request.user != chat_group.admin:
        raise Http404()

    if request.method == "POST":
        chat_group.delete()
        messages.success(request, 'Chatroom deleted')
        return redirect('home')

    return render(request, 'chat/chatroom_delete.html', {'chat_group': chat_group})


@login_required(login_url='login')
def chatroom_leave_view(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    if request.user not in chat_group.members.all():
        raise Http404()

    if request.method == "POST":
        chat_group.members.remove(request.user)
        messages.success(request, 'You left the Chat')
        return redirect('home')


def chat_file_upload(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)

    if request.htmx and request.FILES:
        file = request.FILES['file']
        message = GroupMessage.objects.create(
            file=file,
            author=request.user,
            group=chat_group,
        )
        channel_layer = get_channel_layer()
        event = {'type': 'message_handler', 'message_id': message.id}
        async_to_sync(channel_layer.group_send)(chatroom_name, event)

    return HttpResponse()


def send_invitation_message(sender, recipient, room):
    message_content = f"You have been invited to join a {room.opponent_type} room. Click the button to join."

    all_chat_groups = sender.group_chats.all()
    
    private_chat_groups = all_chat_groups.filter(is_private=True)

    group = private_chat_groups.filter(members=recipient).first()

    if group:
        message = GroupMessage.objects.create(
            body = message_content,
            author=sender,
            group=group,
            is_invitation = True,
            room = room,
        )
        channel_layer = get_channel_layer()
        event = {'type': 'message_handler', 'message_id': message.id}
        async_to_sync(channel_layer.group_send)(group.group_name, event)
    else:
        raise ValueError("No suitable group found for sending the invitation")


@login_required(login_url='login')
def invite_through_message(request):
    if request.method == 'POST':
        # Get the room and selected friends from the request
        room_id = request.POST.get('room_id')
        room = get_object_or_404(Room, id=room_id)
        friend_ids = request.POST.get('friend_ids').split(',')  # List of selected friend IDs
        
        # Fetch friends from the database
        friends = User.objects.filter(id__in=friend_ids)
        
        # Send invitation messages
        for friend in friends:
            send_invitation_message(request.user, friend, room)
        
        messages.success(request, "Invitations sent successfully.")
        return redirect('room', pk=room_id)

    return HttpResponse("Invalid request method", status=405)


@login_required(login_url='login')
def chat_ui(request):
    all_chat_groups = request.user.group_chats.all()
    
    view = request.GET.get('view', 'all')

    if view == 'blocked':
        chat_groups = request.user.blocked_groups.all()
    else:
        chat_groups = all_chat_groups.filter(is_private=False) | all_chat_groups.filter(is_private=True)

    blocked_chat_groups = request.user.blocked_groups.all()

    public_chat_groups = all_chat_groups.filter(is_private=False) 
    private_chat_groups = all_chat_groups.filter(is_private=True).exclude(id__in=blocked_chat_groups.values_list('id', flat=True))
    
    context = {
        'chat_groups': chat_groups,
        'public_chat_groups': public_chat_groups,
        'private_chat_groups': private_chat_groups,
        'current_view': view
    }
    
    return render(request, 'base/private_messages.html', context)


@login_required(login_url='login')
def chat_group_detail(request, id):
    group = get_object_or_404(ChatGroup, id=id)
    all_chat_groups = request.user.group_chats.all()
    
    blocked_chat_groups = request.user.blocked_groups.all()
    public_chat_groups = all_chat_groups.filter(is_private=False) 
    private_chat_groups = all_chat_groups.filter(is_private=True)

    chat_messages = group.chat_messages.all()[:30]
    view = request.GET.get('view', 'all')

    if request.htmx:
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.author = request.user
            message.group = group
            message.room = room
            message.save()
            return render(request, 'private_message/partials/chat_message_p.html', {'message': message, 'user': request.user})

    context = {
        'group': group,
        'chat_groups': public_chat_groups,
        'private_chat_groups': private_chat_groups,
        'selected_group_id': group.id,
        'chatroom_name_ws': group.groupchat_name,
        'chat_messages': chat_messages,
        'current_view': view
    }
    
    return render(request, 'base/private_messages.html', context)


@login_required(login_url='login')
def block_group(request, pk):
    
    group_to_block = get_object_or_404(ChatGroup, group_name=pk)

    if request.user.blocked_groups.filter(id=group_to_block.id).exists():
        messages.info(request, "You have already blocked this chat group.")
    else:
        request.user.blocked_groups.add(group_to_block)
        messages.success(request, f"You have successfully blocked the chat group {group_to_block.group_name}.")

    return redirect('messages')


@login_required(login_url='login')
def unblock_group(request, pk):
    group_to_unblock = get_object_or_404(ChatGroup, group_name=pk)

    if request.user.blocked_groups.filter(id=group_to_unblock.id).exists():
        request.user.blocked_groups.remove(group_to_unblock)
        messages.success(request, f"You have successfully unblocked the chat group {group_to_unblock.group_name}.")
    else:
        messages.info(request, "This chat group is not currently blocked.")

    return redirect('messages')


# <!-- /*==============================
# =>  Tournament Functions
# ================================*/ -->

def get_blockchain_connection():
    # Set up web3 connection (use your own endpoint)
    rpc_url = os.environ.get("RPC_URL")  # or other RPC URL
    web3 = Web3(Web3.HTTPProvider(rpc_url))

    # Verify connection
    if not web3.is_connected():
        print("Failed to connect to the blockchain")
        return None

    return web3 

# Function to get game results by ID
def get_game_results(_id):

    web3 = get_blockchain_connection()

    url = "http://thirdweb:3333/get_contractAddress"

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    response = response.json()

    if response.get('status') != 'success':
        return None

    address = response.get('address')
    contract_address = Web3.to_checksum_address(address)
    contract_abi = response.get('abi')

    contract = web3.eth.contract(address=contract_address, abi=contract_abi)

    try:
        result = contract.functions.getGameResultsById(_id).call()
        game_result = {
            "id": result[0],
            "player1": result[1],
            "player2": result[2],
            "score1": result[3],
            "score2": result[4],
            "winner": result[5],
            "timestamp": result[6]
        }
        return game_result
    except Exception as e:
        print(f"Error calling contract: {e}")
        return None


@login_required(login_url='login')
def tournament_view(request, pk):
    room = get_object_or_404(Room, id=pk)
    room.is_started = True
    room.save()

    final_player1 = None
    final_player2 = None

    if room.is_completed:
        return redirect('podium_view', pk=pk)

    matches = {
        'quarterfinals': [],
        'semifinals': [],
        'final': None
    }

    matches_dup = {
        'quarterfinals': [],
        'semifinals': [],
        'final': None
    }

    # Ensure that room.matches is a dictionary and 'semifinals' key exists
    semifinal_matches = room.matches.get('semifinals', []) if room.matches else []

    participants = list(room.participants.all())
    opp_count = len(participants)

    # Check if semifinal_matches has at least two matches with valid IDs
    if room.is_final is True:
        print(f"{semifinal_matches[0].get('id')}")
        print(f"{semifinal_matches[1].get('id')}")

        matches['semifinals'] = semifinal_matches

        while not final_player1 or not final_player2:
            result = None
            while not result:
                result = get_game_results(semifinal_matches[0]['id'])

            if result:
                if not final_player1:
                    final_player1 = result['winner']
                    print(f"Final player 1: {final_player1}")
                else:
                    final_player2 = result['winner']
                    print(f"Final player 2: {final_player2}")

            result2 = None
            while not result:
                result = get_game_results(semifinal_matches[1]['id'])
            if result2:
                if not final_player1:
                    final_player1 = result2['winner']
                    print(f"Final player 1: {final_player1}")
                else:
                    final_player2 = result2['winner']
                    print(f"Final player 2: {final_player2}")

        print(f"Final players: {final_player1} and {final_player2}")
        final_match_object = Match(
            player1=get_object_or_404(User, username=final_player1),
            player2=get_object_or_404(User, username=final_player2),
            round='Final'
        )
        final_match_object.save()

        final_match = {
            'round': final_match_object.round,
            'player1': final_match_object.player1.username,
            'player2': final_match_object.player2.username,
            'id': final_match_object.id,
            'is_final': True,
        }

        matches['final'] = final_match
        matches_dup['final'] = final_match.copy()

        if request.user == final_match_object.player1 or request.user == final_match_object.player2:
            print(f"{matches}")
            context = {
                'matches': matches,
                'matches_dup': matches_dup,
                'opp_count': opp_count,
                'room': room,
                'split_no': 1,
            }
            room.matches = matches
            room.save()
            return render(request, 'tournament/bracket.html', context)
        else:
            return redirect('home')

    else:
        print("No game result found.")

    split_no = 1

    if opp_count == 4:
        for i in range(0, 4, 2):
            match = Match(
                player1=participants[i],
                player2=participants[i + 1],
                round='Semifinal'
            )
            match.save()

            match_data = {
                'player1': match.player1.username,
                'player2': match.player2.username,
                'round': match.round,
                'id': match.id
            }
            matches['semifinals'].append(match_data)
            matches_dup['semifinals'].append(match)

            final_match = {
                'round': 'Final',
                'is_final': True,
                'player1': None,
                'player2': None,
                'id': None
            }
            matches['final'] = final_match
            matches_dup['final'] = final_match.copy()

    # Iterate through the semifinal matches to find the current user's match
    for match_round in ['semifinals']:
        for match in matches[match_round]:
            try:
                player1 = User.objects.get(username=match['player1'])
                player2 = User.objects.get(username=match['player2'])
            except User.DoesNotExist:
                continue

            if request.user == player1 or request.user == player2:
                context = {
                    'matches': matches,
                    'matches_dup': matches_dup,
                    'opp_count': opp_count,
                    'room': room,
                    'split_no': split_no,
                }
                room.matches = matches
                room.save()
                return render(request, 'tournament/bracket.html', context)

            split_no += 1

    context = {
        'matches': matches,
        'matches_dup': matches_dup,
        'opp_count': opp_count,
        'room': room,
    }

    room.matches = matches
    room.save()

    return render(request, 'tournament/bracket.html', context)


@login_required(login_url='login')
def podium_view(request, pk):
    room = get_object_or_404(Room, id=pk)

    player_no_1 = None
    player_no_2 = None
    player_no_3 = None

    matches = room.matches

    semifinal_matches = matches.get('semifinals', [])
    final_match = matches.get('final', None)

    result_semi1 = get_game_results(semifinal_matches[0]['id'])
    result_semi2 = get_game_results(semifinal_matches[1]['id'])
    result_final = get_game_results(final_match['id'])

    player_no_1 = result_final['winner']
    player_no_2 = result_final['player1'] if result_final['winner'] == player_no_1 else result_final['player2']

    player3_scoring = result_semi1['score1'] if result_semi1['winner'] != result_semi1['player1'] else result_semi1['score2']
    player3_name = result_semi1['player1'] if result_semi1['winner'] != result_semi1['player1'] else result_semi1['player2']
    player4_scoring = result_semi2['score1'] if result_semi2['winner'] != result_semi2['player1'] else result_semi2['score2']
    player4_name = result_semi2['player1'] if result_semi2['winner'] != result_semi2['player1'] else result_semi2['player2']

    if player3_scoring == player4_scoring:
        player_no_3 = player3_name
    else:
        player_no_3 = player3_name if player3_scoring > player4_scoring else player4_name

    player_no_1 = get_object_or_404(User, username=player_no_1)
    player_no_2 = get_object_or_404(User, username=player_no_2)
    player_no_3 = get_object_or_404(User, username=player_no_3)

    
    context = {
        'player_no_1': player_no_1,
        'player_no_2': player_no_2,
        'player_no_3': player_no_3,
    }
    
    return render(request, 'tournament/podium.html', context)


# <!-- /*==============================
# =>  Notification Functions
# ================================*/ -->


def send_notification(user, sender, notification_type, title, message):
    Notification.objects.create(
        user=user,
        sender=sender,
        type=notification_type,
        title=title,
        message=message
    )


@login_required(login_url='login')
def notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required(login_url='login')
def friend_mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()

    # Redirect to the appropriate view after marking the notification as read
    if notification.type == 'friend_request':
        friend = get_object_or_404(User, id=notification.sender.id)
        if friend == request.user:
            messages.error(request, "You cannot add yourself as a friend.")
            return redirect('user-profile', pk=notification.sender.id)

        # Create or get the friendship relationship
        friendship, created = Friend.objects.get_or_create(
            user=request.user,
            friend=friend,
            defaults={'confirmed': False}
        )

        messages.info(request, f"You are now friends with {notification.sender.username}")
        return redirect('user-profile', pk=notification.sender.id)

    return redirect('notifications')


def noti_list(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    if request.headers.get('HX-Request'):
        return render(request, 'notification/partials/noti_list.html', {'notifications': notifications})
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# <!-- /*==============================
# =>  Friend Functions
# ================================*/ -->


@login_required(login_url='login')
def add_friend(request, user_id):
    friend = get_object_or_404(User, id=user_id)
    if friend == request.user:
        messages.error(request, "You cannot add yourself as a friend.")
        return redirect('user-profile', pk=user_id)

    friendship, created = Friend.objects.get_or_create(
        user=request.user,
        friend=friend,
        defaults={'confirmed': False}
    )

    if created:
        send_notification(
            friend,
            request.user,
            'friend_request',
            'Friend Request',
            f"{request.user.username} has sent you a friend request."
        )
        messages.success(request, "Friend request sent.")
    elif friendship.confirmed:
        messages.info(request, "You are already friends.")
    else:
        messages.info(request, "Friend request already sent.")

    return redirect('user-profile', pk=user_id)


def get_friends(user):
    # Get friends where user is the main user
    friends_as_user = User.objects.filter(friend_set__user=user)
    # Get friends where user is the related friend
    friends_as_friend = User.objects.filter(related_friend_set__friend=user)
    
    # Use Q objects to get all friends and eliminate duplicates
    friends = User.objects.filter(
        Q(id__in=friends_as_user.values('id')) |
        Q(id__in=friends_as_friend.values('id'))
    ).distinct()

    return friends


@login_required(login_url='login')
def remove_friend(request, user_id):
    friend = get_object_or_404(User, id=user_id)
    if friend == request.user:
        messages.error(request, "You cannot remove yourself as a friend.")
        return redirect('user-profile', pk=user_id)

    try:
        friendship = Friend.objects.get(user=request.user, friend=friend)
        friendship.delete()
        messages.success(request, f"You have removed {friend.username} from your friends.")
        reverse_friendship = Friend.objects.get(user=friend, friend=request.user)
        reverse_friendship.delete()
    except Friend.DoesNotExist:
        messages.error(request, "Friendship does not exist.")

    return redirect('user-profile', pk=user_id)


@login_required(login_url='login')
def cancel_friend_request(request, user_id):
    friend = get_object_or_404(User, id=user_id)
    try:
        friendship = Friend.objects.get(user=request.user, friend=friend, confirmed=False)
        friendship.delete()
        messages.success(request, "Friend request canceled.")
    except Friend.DoesNotExist:
        messages.error(request, "Friend request does not exist.")

    return redirect('user-profile', pk=user_id)

def pong_game_view(request):
    return render(request, 'pong/pong_game.html')