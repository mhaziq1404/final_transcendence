function scrollToBottom(time=0) {
    setTimeout(function() {
        const container = document.getElementById('chat_container');
        container.scrollTop = container.scrollHeight;
    }, time);
}
scrollToBottom()

document.addEventListener('DOMContentLoaded', function() {
    // Select all alert elements
    const alerts = document.querySelectorAll('.alert-dismissible');

    alerts.forEach(function(alert) {
        setTimeout(function() {
            let opacity = 1;
            const fadeDuration = 1000; // Duration in milliseconds
            const fadeStep = 50; // Step interval in milliseconds
            const fadeAmount = fadeStep / fadeDuration;

            const fadeOut = setInterval(function() {
                if (opacity <= 0) {
                    clearInterval(fadeOut);
                    alert.style.display = 'none';
                } else {
                    opacity -= fadeAmount;
                    alert.style.opacity = opacity;
                }
            }, fadeStep);
        }, 5000); // Start fade-out after 5 seconds
    });

    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';

    const onlineSocket = new WebSocket(wsProtocol + window.location.host + '/ws/online/');

    onlineSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const onlineUsersContainer = document.getElementById('online-users');
        onlineUsersContainer.innerHTML = ''; // Clear the list

        data.online_users.forEach(function(username) {
            const userElement = document.createElement('li');
            userElement.textContent = username;
            onlineUsersContainer.appendChild(userElement);
        });
    };

    onlineSocket.onclose = function(event) {
        console.error('WebSocket closed unexpectedly');
    };
});




