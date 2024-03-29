import socket
import threading
import enum

HOST = "0.0.0.0"
PORT = 12000
active_clients = {}
database = {}


class UserState(enum.Enum):
    Idle = 1
    Requesting = 2
    Requested = 3
    Chatting = 4

    def __str__(self):
        return '%s' % self.value


class User:
    def __init__(self, username, availability, connection, address, login_status, state):
        self.username = username
        self.availability = availability
        self.connection = connection
        self.address = address
        self.login_status = login_status
        self.state = state


def handle_client(connection, address):
    print("%s:%s has connected" % address)
    database[connection] = User("this", "available", connection, address, False, UserState.Idle)
    send_welcome(connection)
    try:
        while True:
            message = connection.recv(1024)
            message_router(message, connection)
    except:
        pass
    finally:
        connection.close()


def message_router(message, connection):
    # get user object associated with connection, always true
    user = database[connection]
    if user.state is UserState.Idle:
        if not user.login_status:
            user.username = message.decode()
            username_validation(user, connection)
        else:
            if message.decode() == '1':
                if len(active_clients) > 1:
                    send_user_list(connection)
                    send_menu(connection)
                else:
                    send_single_user_warning(connection)
                    send_menu(connection)
            elif message.decode() == '2':
                if len(database) > 1:
                    user.state = UserState.Requesting
                    send_user_list(connection)
                    send_chat_request(connection)
                else:
                    send_single_user_warning(connection)
                    send_menu(connection)
            elif message.decode() == '3':
                remove_connection(connection)
            else:
                # add error message here
                print("Error, invalid operation")
    elif user.state is UserState.Requesting:
        # current user in a state where they are requesting to chat with another user
        requested_user = get_user_from_name(message.decode())
        # turn off availability
        user.availability = "chatting with " + requested_user.username
        requested_user.availability = "chatting with " + user.username
        requested_user.state = UserState.Requested
        send_request_waiting(requested_user, connection)
        request_message = "\nUser " + user.username + " is requesting to chat with you. Y/N?"
        send_user_to_user_message(user, requested_user, request_message)
    elif user.state is UserState.Requested:
        temp_str_list = user.availability.split()
        request_user = get_user_from_name(temp_str_list[2])
        if message.decode().lower() == 'y':
            # formally begin chatting
            user.state = UserState.Chatting
            request_user.state = UserState.Chatting
            send_chat_header(user, connection)
            send_chat_header(request_user, request_user.connection)
            send_chat_prefix(user, connection)
            send_chat_prefix(request_user, request_user.connection)
        elif message.decode().lower() == 'n':
            # send rejection message to user
            user.state = UserState.Idle
            request_user.state = UserState.Idle
            send_rejection_message(user, request_user.connection)
            send_menu(request_user.connection)
            send_menu(connection)
        else:
            # error message
            print("user error...")
    elif user.state is UserState.Chatting:
        temp_str_list = user.availability.split()
        other_user = get_user_from_name(temp_str_list[2])
        if message.decode() == "Quit":
            send_chat_end_to_users(user.connection, other_user.connection)
            send_menu(other_user.connection)
            send_menu(user.connection)
            user.state = UserState.Idle
            other_user.state = UserState.Idle
        else:
            formatted_chat_message = other_user.username + ": " + message.decode() + "\n" + user.username + ": \n"
            send_user_to_user_message(user, other_user, formatted_chat_message)



def send_chat_end_to_users(connection, other_connection):
    end_message = "chat session ended"
    connection.send(end_message.encode())
    other_connection.send(end_message.encode())


def send_chat_prefix(user, connection):
    prefix = user.username + ": "
    connection.send(prefix.encode())


def send_rejection_message(user, connection):
    rejection_message = "\n " + user.username + " has denied the chat."
    connection.send(rejection_message.encode())


def send_chat_header(user, connection):
    header = '\n\n**** Private Chat with ' + user.username + " ****\n\n"
    connection.send(header.encode())


def send_welcome(connection):
    welcome = '\nWelcome to the chat server!\n\nEnter a username for yourself: '
    connection.send(welcome.encode())


def send_menu(connection):
    menu = "\n\n1. List users\n2. Chat\n3. Exit\n\nEnter your choice: "
    connection.send(menu.encode())


def send_single_user_warning(connection):
    warning = '\nYou are the only person in this server\n'
    connection.send(warning.encode())


def send_request_waiting(user, connection):
    wait_message = '\nWaiting for ' + user.username + ' to accept your invitation. Please wait.\n'
    connection.send(wait_message.encode())


def send_chat_request(connection):
    message = '\nEnter the name of the person you would like to chat with: '
    connection.send(message.encode())


def send_user_list(connection):
    send_user_list_header(connection)
    for key, value in active_clients.items():
        user_list = ""
        if value in database:
            temp_user = database[value]
            if key == temp_user.username:
                user_list += "\t" + temp_user.username + "\t\t" + str(temp_user.availability) \
                             + "\t" + str(temp_user.address) + "\t\t" + str(temp_user.login_status) + "\n"
                connection.send(user_list.encode())


def get_user_from_name(username):
    if username in active_clients:
        conn = active_clients[username]
        if conn in database:
            return database[conn]


def send_user_list_header(connection):
    user_list_header =  "\n\n------------------------------------------------------------------------------------\n"
    user_list_header += "\tusername\tavailability\t\taddress\t\tlogin status\t\n"
    user_list_header += "------------------------------------------------------------------------------------\n"
    connection.send(user_list_header.encode())


def send_user_to_user_message(current_user, requested_user, message):
    requested_user.connection.send(message.encode())


def username_validation(user, connection):
    if user.username == '':
        response = "Error: Username cannot be empty. Please choose another: "
        connection.send(response.encode())
    else:
        if user.username in active_clients:
            print("Error: Validation not successful")
            response = "Error: Username already taken. Please choose another: "
            connection.send(response.encode())
        else:
            print("Success, validated username")
            active_clients[user.username] = connection
            user.login_status = True
            user.availability = "Available"
            response = "Login successful."
            connection.send(response.encode())
            send_menu(connection)


def remove_connection(connection):
    for key, value in active_clients.items():
        if value in database:
            temp_user = database[value]
            if connection in database:
                print("deleting...")
                del database[connection]
                del active_clients[temp_user.username]
                message = "FORCE_EXIT"
                connection.send(message.encode())
                connection.close()


def Main():
    host = "0.0.0.0"
    port = 12000
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    print("socket binded to port", port)
    s.listen(100)
    print("socket is listening")

    # a forever loop until client wants to exit
    while True:
        client_connection, addr = s.accept()
        thread = threading.Thread(target=handle_client, args=(client_connection, addr))  # Start a thread & connect
        thread.start()

if __name__ == '__main__':
    Main()





