
import socket, select, time
import tkinter as tk
from tkinter import scrolledtext
from tkinter.constants import END, TRUE
import tkinter.font as tkFont
from packet import *
from _thread import *

class Client:
    def __init__(self, serverInfo, username, textBox, roomFrame):
        self.serverInfo = serverInfo
        self.username = username
        self.textBox = textBox
        self.roomFrame = roomFrame
        self.style = tkFont.Font(family='Arial', size=15)
        self.running = True

        # Connect to chat server 
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect(self.serverInfo)
        self.lastPacket = None
        self.roomList = []
        self.userList = []
        self.room = ''

    def getServerMsgs(self):
        """
        Watches the socket for packets from the server and processes them

        If there is an error in the packet produce that
        Otherwhise process the packet

        Detects if the server connection is closed and ends this thread
        """
        
        while self.running:
            read_sockets, write_socket, error_socket = select.select([self.server],[],[])
            for socks in read_sockets:
                if socks == self.server:
                    try:
                        packet = socks.recv(MAX_PACKET_SIZE)
                    # Packet retrieval failed close the connection  
                    except:
                        event = "DISCONNECTED FROM SERVER"
                        self.printEvent(event, True)
                        self.running = False
                    else:
                        # Decode the packet
                        decodedPkt = decodePacket(packet)

                        # Decode returned an error print the error for
                        # the server and sent it back to the client
                        if type(decodedPkt) == bytes:
                            opCode, length, errCode = decodePacket(decodedPkt)
                            event = "<SERVER> ERROR in server packet - " + list(ERRORCODES.keys())[int(errCode)]
                            self.printEvent(event,True)

                        else:
                            self.processMessage(decodedPkt)

                    
        
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
    
    def sendMsg(self,msg):
        # TODO errors from encoding
        print(msg)
        if self.running:
            packet = encodePacket(OPCODES["OPCODE_SEND_MSG"],msg)
            self.send(packet)
        else:
            self.printEvent("ERROR Cannot send message, no connection to server")

    def sendName(self):
        packet = encodePacket(OPCODES["OPCODE_HELLO"], self.username)
        self.send(packet)

    def processMessage(self, message):
        """
        message - (OPCODE, LENGTH, PAYLOAD)
        
        """
        opCode, length, payload = message
        error = False
        event = "<SERVER> "

        # Server sent error message
        if opCode == OPCODES["OPCODE_ERR"]:
            event += "Last packet returned error - "
            if type(payload) == int:
                errorMsg = getErrCode(payload)
                event += errorMsg 
                if payload == 2 or errorMsg == "ERR_UNKNOWN":
                    self.resend()
            else:
                event += payload
            error = True
        # Initial message from server
        elif opCode == OPCODES["OPCODE_HELLO"]:
            event += payload
            self.sendName()
        # TODO server should not send this
        elif opCode == OPCODES["OPCODE_GET_ROOMS"]:
            pass
        # Server sent list of chatrooms
        elif opCode == OPCODES["OPCODE_LIST_ROOMS"]:
            event, error = self.updateRooms(payload)
        # Server sent user list for the room
        elif opCode == OPCODES["OPCODE_LIST_USERS"]:
            event, error = self.updateUsers(payload)
        # TODO server should not send this
        elif opCode == OPCODES["OPCODE_CREATE_ROOM"]:
            pass
        # Assign user to a room
        elif opCode == OPCODES["OPCODE_JOIN_ROOM"]:
            event, error = self.assignRoom(payload)
        # Server removed client from room
        elif opCode == OPCODES["OPCODE_LEAVE_ROOM"]:
            self.room = ''
            self.userList.clear()
            event += f'you left room \"{payload}\"'
            self.clearText()
            self.buildRoomFrame()
        # TODO server should not send this
        elif opCode == OPCODES["OPCODE_SEND_MSG"]:
            pass
        # Server sent a message for my room
        elif opCode == OPCODES["OPCODE_BROADCAST_MSG"]:
            event = payload
        else:
            pass

        self.printEvent(event,error)

    def assignRoom(self, room):
        error = False
        self.room = room
        event = f'<SERVER> you joined room \"{self.room}\"'
        packet = encodePacket(OPCODES["OPCODE_LIST_USERS"],room)
        self.send(packet)
        self.clearText()
        self.buildRoomFrame()

        return event, error

    def updateRooms(self, roomStr):
        error = False
        event = "<SERVER> updated room list"
        if roomStr:
            self.roomList = roomStr.split(',')

        self.buildRoomFrame()
        return event,error

    def buildRoomFrame(self):
        """
        Builds either buttons to join or create rooms
        or Usernames for the people in the current room
        """
        # clear the room Frame
        for widget in self.roomFrame.winfo_children():
            widget.destroy()

        # Client not in a room list the rooms
        if self.room == '':
            tk.Label(self.roomFrame, text="Rooms", font=self.style).pack()
            for room in self.roomList:
                tk.Button(self.roomFrame, text=f'{room}', width=15, command=lambda index=f'{room}':self.joinRoom(index)).pack()
            tk.Label(self.roomFrame, text=' ').pack()
            newRoom = tk.Entry(self.roomFrame, width=18)
            newRoom.pack()
            tk.Button(self.roomFrame, text='Create New Room', width=15, command=lambda:self.createRoom(newRoom.get())).pack()
        
        # Print Usernames of users in room
        else:
            tk.Label(self.roomFrame, text=f"{self.room}", font=self.style).pack()
            users = scrolledtext.ScrolledText(self.roomFrame, width=12, height=22)
            users.pack()
            for user in self.userList:
                users.insert(tk.INSERT,user + '\n')
            users.configure(state='disabled')
            tk.Button(self.roomFrame, text='Leave Room', width=15, command=self.leaveRoom).pack()

    def joinRoom(self, room):
        packet = encodePacket(OPCODES["OPCODE_JOIN_ROOM"],room)
        self.send(packet)

    def createRoom(self, room):
        if not any(char.isspace() for char in room):
            packet = encodePacket(OPCODES["OPCODE_CREATE_ROOM"],room)
            self.send(packet)
        else:
            self.printEvent("<SERVER> room names cannot contain whitespace",True)

    def leaveRoom(self):
        if self.room != '':
            packet = encodePacket(OPCODES["OPCODE_LEAVE_ROOM"],)
            self.send(packet)

    def send(self,packet):
        """
        Store the last packet to resend on 
        certain errors
        """
        self.lastPacket = packet
        self.server.send(packet)

    def resend(self):
        """
        Resend most recent packet
        """
        self.printEvent("<CLIENT> Resent packet",True)
        self.server.send(self.lastPacket)

    def clearText(self):
        self.textBox.configure(state='normal')
        self.textBox.delete(1.0,END)
        for i in range(25):
            self.textBox.insert("end","\n")
        self.textBox.see("end")
        self.textBox.configure(state='disabled')

    def updateUsers(self, userStr):
        error = False
        
        # Client not in a room should not have recieved this
        if self.room == '':
            error = TRUE
            event = f"<CLIENT> Server sent user list update when not in a room" 

        else:
            event = f"<SERVER> updated user list for \"{self.room}\""
            print(userStr) 
            if userStr:
                self.userList = userStr.split(',')

        self.buildRoomFrame()
        return event,error
