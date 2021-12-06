import builtins
import socket, time
import tkinter as tk
from types import CellType
from packet import *
from _thread import *
    
class Server:
    def __init__(self,netInfo ,textBox, roomText, userText):
        self.netInfo = netInfo

        # GUI interfaces
        self.textBox = textBox
        self.roomText = roomText
        self.userText = userText

        # Create server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(self.netInfo)
        # Max allowable connections
        self.server.listen(100)

        self.lastPacket = {}

        # Client and room data
        self.clientList = []
        self.usernames = {}
        self.userRoom = {}
        self.roomList = ['room1','room2','room3','room4']

        self.running = True
    
    def clientThread(self,client):
        """
        Each client has their own thread on the server
        As long as their connection is active this thread
        will recieve and process any packets they send.
        If any packet is not recieved propery their connection
        is closed
        """
        
        # Connection establised send the client the hellow message
        hello = encodePacket(OPCODES["OPCODE_HELLO"],'Welcome to the Server') 
        client.send(hello)
    
        while True:
                try:
                    # Grab the packet from the client
                    packet = client.recv(MAX_PACKET_SIZE)
                except:
                    continue
                else:
                    if packet:
                        # Decode the packet
                        decodedPkt = decodePacket(packet)
                        
                        # Decode returned an error print the error for
                        # the server and sent it back to the client
                        if type(decodedPkt) == bytes:
                            opCode, length, errCode = decodePacket(decodedPkt)
                            event = self.buildTag(client) + " ERROR in client packet - " + getErrCode(errCode)
                            self.printEvent(event,True)
                            client.send(decodedPkt)

                        else:
                            self.processMessage(client, decodedPkt)

                    # Something is wrong with the packet close the connection
                    else:
                        self.remove(client)
    
                
        
    def remove(self, client):
        """
        Remove a client from the following:
        self.clientList
        self.usernames
        self.userRoom
        
        """
        clientIp = client.getpeername()

        if client in self.clientList:
            self.clientList.remove(client)
        
        if client in self.userRoom:
            self.userRoom.pop(client)

        if clientIp in self.usernames:
            self.usernames.pop(clientIp)

        
    
    def runServer(self):
        """
        This should be run in its own thread.

        While the server is running accepts new connections
        from clients and starts then in a new thread 
        """
        event = "Server running on " + self.netInfo[0] + ":" + str(self.netInfo[1])
        self.printEvent(event)

        while self.running:
            
            # Accept new client connection
            client, clientIp = self.server.accept()
        
            # Add client to the client list
            self.clientList.append(client)
        
            # prints the address of the user that just connected
            event = self.buildTag(client) + " connected"
            self.printEvent(event)
        
            # creates and individual thread for every user
            # that connects
            start_new_thread(self.clientThread,(client,))   
            
        client.close()
        self.server.close()

    def printEvent(self, event, error=False):
        """
        Print events to the server window at the time the event occurs.
        Prints the time the event is given.
        Errors print in red everything else in black
        """
        if error:
            config = 'error'
        else:
            config = 'normal' 
        currTime = time.strftime("%H:%M:%S",time.localtime())
        self.textBox.configure(state='normal')
        self.textBox.insert("end",currTime + " - " + event + "\n", f'{config}')
        self.textBox.tag_config('normal', foreground='black')
        self.textBox.tag_config('error', foreground='red')        
        self.textBox.see("end")
        self.textBox.configure(state='disabled')

    def buildTag(self, client):
        """
        Build the tag for printing events. Always contains IP:PORT
        appends Username if present.
        
        <ClientIP:PORT - Username>
        """
        clientIp = client.getpeername()
        tag = "<" + clientIp[0] + ":" + str(clientIp[1])

        if clientIp in self.usernames:
            tag += " - " + self.usernames[clientIp] + ">"
        else:
            tag += ">"

        return tag

    def updateInfo(self):
        # Clear old info

        self.roomText.configure(state='normal')
        self.roomText.delete(1.0,tk.END)
        for room in self.roomList:
            self.roomText.insert(tk.INSERT,room + '\n')
        self.roomText.configure(state='disabled')

        self.userText.configure(state='normal')
        self.userText.delete(1.0,tk.END)
        for user in self.usernames.values():
            self.userText.insert(tk.INSERT,user + '\n')
        self.userText.configure(state='disabled')

    def processMessage(self, client,  message):
        """
        message - (OPCODE, LENGTH, PAYLOAD)
        
        """
        opCode, length, payload = message
        event = self.buildTag(client)
        error = False

        # Client sent error message
        if opCode == OPCODES["OPCODE_ERR"]:
            event += " Client returned error - " + list(ERRORCODES.keys())[payload]
            error = True
        # TODO decide if this code is even necessary    
        elif opCode == OPCODES["OPCODE_KEEPALIVE"]:
            pass
        # Client just joined add their username
        elif opCode == OPCODES["OPCODE_HELLO"]:
            username = self.createUsername(client, payload)
            event += f" Updated username to \"{username}\" and sent room list"
            self.sendRoomlist(client)
        # Client request for current rooms
        elif opCode == OPCODES["OPCODE_GET_ROOMS"]:
            # Convert room list to string and send to client
            self.sendRoomlist(client)
            event += " Sent client room list"
        # TODO Client should not be sending this
        elif opCode == OPCODES["OPCODE_LIST_ROOMS"]:
            pass
        # Client requests users in their room
        elif opCode == OPCODES["OPCODE_LIST_USERS"]:
            event, error = self.sendUsers(client, payload)
        # Client requests creation of room
        elif opCode == OPCODES["OPCODE_CREATE_ROOM"]:
            event, error = self.createRoom(client, payload)
            self.sendRoomlist('all')
        # Assign user to a room
        elif opCode == OPCODES["OPCODE_JOIN_ROOM"]:
            event, error = self.assignRoom(client, payload)
        # Remove client from their current room
        elif opCode == OPCODES["OPCODE_LEAVE_ROOM"]:
            event, error = self.leaveRoom(client)
            self.sendRoomlist(client)
            event += " sent client room list"
        # Client sent a message to their chatroom
        elif opCode == OPCODES["OPCODE_SEND_MSG"]:
            event, error = self.broadcast(client, payload)
        # TODO Client should not be sending this
        elif opCode == OPCODES["OPCODE_BROADCAST_MSG"]:
            pass
        else:
            pass

        self.printEvent(event,error)
        self.updateInfo()

    def sendUsers(self, client, room):
        error = False
        clientIp = client.getpeername()
        event = self.buildTag(client)

        # Room does not exist tell user
        if room not in self.roomList:
            error = True
            packet = encodePacket(OPCODES["OPCODE_ERR"],str(ERRORCODES["ERR_ILLEGAL_NAME"]) + f":ERR_ILLEGAL_NAME - room \"{room}\" does not exists, no users to send")
            client.send(packet)
            event += f"ERR_NAME_EXISTS - room name \"{room}\" alread exsists"

        # Send client the user list
        else:
            # Get all the usernames
            # TODO This is awful and these data structures need
            # to be reworked 
            clientIpList = []
            for k,v in self.userRoom.items():
                if v == room:
                    clientIpList.append(k.getpeername())
            userList = []
            for k,v in self.usernames.items():
                if k in clientIpList:
                    userList.append(v)

            userStr = ','.join(userList)
            packet = encodePacket(OPCODES["OPCODE_LIST_USERS"],userStr)
            self.send(client, packet)

            event += f"sent \"{self.usernames[clientIp]}\" userlist for \"{room}\""

        return event, error

    def sendRoomlist(self, client):
        roomStr = ",".join(self.roomList)
        packet = encodePacket(OPCODES["OPCODE_LIST_ROOMS"],roomStr)
        if client == 'all':
            self.updateRoomless(packet)
        else:
            client.send(packet)


    def createUsername(self, client, wantName):
        """
        Adds the username in the username dictionary using their
        (IP,PORT) as the key.

        If the username exsists finds the first valid "(i)"
        appended username instead and sends the user an error
        with their updated name
        """
        clientIp = client.getpeername()
        username = wantName
        i = 1
        if username in self.usernames.values():
            tempName = username + f"({i})"
            while tempName in self.usernames.values():
                i += 1
                tempName = username + f"({i})"
            username = tempName
            packet = encodePacket(OPCODES["OPCODE_ERR"],str(ERRORCODES["ERR_NAME_EXISTS"]) + f":ERR_NAME_EXISTS - your username is now \"{username}\"")
            client.send(packet)

        self.usernames[clientIp] = username
        return username

    def createRoom(self, client, wantName):
        """
        Adds the room to the room list.

        If the requested name exists sends an error back to the user.
        Otherwise creates room, adds the user to it and sends them
        a message they have joined the room.
        """
        error = False
        event = self.buildTag(client)

        # Room already exists produce client and server error
        if wantName in self.roomList:
            error = True
            packet = encodePacket(OPCODES["OPCODE_ERR"],str(ERRORCODES["ERR_NAME_EXISTS"]) + f":ERR_NAME_EXISTS - room \"{wantName}\" already exists")
            client.send(packet)
            event += f"ERR_NAME_EXISTS - room name \"{wantName}\" alread exsists"

        # Create room, if user is in another room remove them,
        # add user to room
        else:
            self.roomList.append(wantName)
            if client in self.userRoom:
                packet = encodePacket(OPCODES["OPCODE_LEAVE_ROOM"],self.userRoom[client])
                client.send(packet)
                self.userRoom.pop(client)
            self.userRoom[client] = wantName
            event += f" Room \"{wantName}\" created"
            packet = encodePacket(OPCODES["OPCODE_JOIN_ROOM"],wantName)
            client.send(packet)

        return event, error

    def assignRoom(self, client, room):
        """
        Adds the client to the room they request.

        If the user is in another room they are removed first

        Sends the client an error if they attempt to join a 
        room that does not exsist
        """
        error = False
        event = self.buildTag(client)

        # Room exists remove user from current room if any
        # then add them to the room
        if room in self.roomList:
            if client in self.userRoom:
                packet = encodePacket(OPCODES["OPCODE_LEAVE_ROOM"],self.userRoom[client])
                client.send(packet)
                self.userRoom.pop(client)
            packet = encodePacket(OPCODES["OPCODE_JOIN_ROOM"],room)
            client.send(packet)
            self.userRoom[client] = room
            event += f" joined chatroom \"{room}\""

        # Room does not exists send error to user
        else:
            error = True
            packet = encodePacket(OPCODES["OPCODE_ERR"],str(ERRORCODES["ERR_ILLEGAL_NAME"]) + f":ERR_ILLEGAL_NAME - there is no chatroom named \"{room}\"")
            client.send(packet)
            event += str(ERRORCODES["ERR_ILLEGAL_NAME"]) + f":ERR_ILLEGAL_NAME - client cannot join \"{room}\" because it does not exist"

        return event, error

    def leaveRoom(self, client):
        """
        Remove the client from their current room
        
        If they are not in a room send them an error
        """
        error = False
        event = self.buildTag(client)

        # Remove client from their current room
        if client in self.userRoom:
            packet = encodePacket(OPCODES["OPCODE_LEAVE_ROOM"],self.userRoom[client])
            client.send(packet)
            event += f" left chatroom \"{self.userRoom[client]}\""
            self.userRoom.pop(client)

        # Client is not in a room
        else:
            error = True
            packet = encodePacket(OPCODES["OPCODE_ERR"],str(ERRORCODES["ERR_NOT_IN_ROOM"]) + f":ERR_NOT_IN_ROOM - leave room failed, you are not in a room")
            client.send(packet)
            event += str(ERRORCODES["ERR_NOT_IN_ROOM"]) + f":ERR_NOT_IN_ROOM - leave room failed, client not in a room"

        return event, error

    def broadcast(self, client, payload):
        """
        Send the message to all the clients in the same room as the client.

        If the client is not in a room produce an error
        Otherwise send the message to all clients in the room
        
        Copy the current client list to iterate.

        Try and send them the packet if their connection
        is no longer active remove them from original list 
        and close the connection.
        """
        error = False
        event = self.buildTag(client)

        # Send message to only clients in the same room
        if client in self.userRoom:

            # get username and attach it to append payload to it
            clientIp = client.getpeername()
            username = self.usernames[clientIp]
            newPayload = "<" + username +"> " + payload
            packet = encodePacket(OPCODES["OPCODE_BROADCAST_MSG"],newPayload)

            room = self.userRoom[client]
            currClients = self.clientList.copy()
            for otherClient in currClients:
                if otherClient in self.userRoom.keys():
                    if self.userRoom[otherClient] == room:
                        try:
                            otherClient.send(packet)
                        except:
                            self.remove(otherClient)
                            otherClient.close()
            event += f" sent a message in \"{room}\""

        # Client is not in a room cannot send
        else:
            error = True
            packet = encodePacket(OPCODES["OPCODE_ERR"],str(ERRORCODES["ERR_NOT_IN_ROOM"]) + f":ERR_NOT_IN_ROOM - send message failed, you are not in a room")
            client.send(packet)
            event += str(ERRORCODES["ERR_NOT_IN_ROOM"]) + f":ERR_NOT_IN_ROOM - client send message failed, client not in a room" 

        return event, error

    def updateRoomless(self, packet):
        """
        Send the roomlist to all users that are not currently in a room.
        
        Copy the current client list to iterate.

        Try and send them the packet if their connection
        is no longer active remove them from original list 
        and close the connection.
        """

        currClients = self.clientList.copy()
        for client in currClients:
            if client not in self.userRoom:
                try:
                    client.send(packet)
                except:
                    self.remove(client)
                    client.close()

    def send(self, client, packet):
        """
        Store the last packet for each client to resend on 
        certain errors
        """
        self.lastPacket[client] = packet
        client.send(packet)

    def resend(self, client):
        """
        Resend most recent packet
        """
        event = self.buildTag(client) + "Resending last packet"
        self.printEvent(event,True)
        client.send(self.lastPacket[client])
