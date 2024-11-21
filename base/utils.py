from .models import Friend

def check_friend_request_sent(sender, receiver):
    """
    Checks if a friend request has been sent from sender to receiver.
    """
    return Friend.objects.filter(
        user=sender,
        friend=receiver,
        confirmed=False
    ).exists()

def check_if_friend(user1, user2):
    """
    Checks if user1 and user2 are friends.
    """
    return Friend.objects.filter(
        user=user1,
        friend=user2,
        confirmed=True
    ).exists() or Friend.objects.filter(
        user=user2,
        friend=user1,
        confirmed=True
    ).exists()