import re, queue, server, client, socket
import tkinter as tk
import tkinter.font as tkFont
from tkinter import Widget, scrolledtext
from _thread import *

class Gui:

    def __init__(self, root):
        # Window setup
        self.root = root
        self.root.resizable(False, False)
        self.root.title("Internet Relay Chat")
        self.frame = None
        self.style = tkFont.Font(family='Arial', size=15)
        self.queue = queue.Queue()
        
        # Network info should be a tuple (IP, PORT)
        self.netInfo = None

        # Show first menu 
        self.startUp()

        
    def startUp(self):
        """
        Setup the window for the user to choose either server
        or client mode
        """

        self.root.geometry("450x250")
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill='both', expand=True)
        tk.Label(self.frame, text='Select your user type with the buttons below', font=self.style).pack()
        tk.Button(self.frame, text='Server', font=self.style, command= lambda: self.getNetInfo(True)).place(x=100, y=100, width=100)
        tk.Button(self.frame, text='Client', font=self.style, command= lambda: self.getNetInfo(False)).place(x=250, y=100, width=100)
    
    def clearFrame(self):
        """
        Clears the all the contents of the  main frame
        """
        for widget in self.frame.winfo_children():
            widget.destroy()

    
    def getNetInfo(self, server):
        """
        Stores the IP address and port number for the server
        
        server: A boolean to give the menu context if this instance is
        a server or client. Changes the menu display to the user.
        """

        # Function to store info
        def storeNetinfo(server):
            # REGEX to test IP and port strings
            goodIp = re.compile('^(((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))|localhost$')
            goodPort = re.compile('^([0-9]{1,4}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$')
            ip = goodIp.match(tempIp.get())
            port = goodPort.match(tempPort.get())

            # If REGEX passes store IP and Port otherwise reprompt
            if ip and port:
                self.netInfo = (ip.group(0), int(port.group(0)))
                if server:
                    tempFrame.destroy()
                    self.startServer()
                else:
                    # Test server connection before proceeding
                    testServ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        testServ.connect(self.netInfo)
                        testServ.close()
                    except:
                        tempPrompt.config(text="Server could not be found! Try again.")
                    else:
                        tempFrame.destroy()
                        self.getUsername()
            else:
                tempPrompt.config(text="Invalid IP or Port! Try again.")
        
        # Clear old menu info
        self.clearFrame()

        tempFrame = tk.Frame(self.frame)
        if server:
            tempPrompt = tk.Label(tempFrame, text="Enter the IP address and port for this Server", font=self.style)
            tempPrompt.grid(row=0, columnspan=2)
        else:
            tempPrompt = tk.Label(tempFrame, text="Enter the Server info you wish to connect to", font=self.style)
            tempPrompt.grid(row=0, columnspan=2)

        tk.Label(tempFrame, text="Server IP", font=self.style).grid(row=1)
        tk.Label(tempFrame, text="Port", font = self.style).grid(row=2)
        tempIp = tk.Entry(tempFrame, font=self.style)
        tempIp.grid(row=1,column=1,)
        if server:
            tempIp.insert(0,socket.gethostbyname(socket.gethostname()))
        tempPort = tk.Entry(tempFrame, font=self.style)
        tempPort.grid(row=2,column=1)
        tk.Button(tempFrame, text='Start', font=self.style, command= lambda: storeNetinfo(server)).grid(row=3, columnspan=2)

        tempFrame.place(anchor='c', relx=.5, rely=.5)

    def getUsername(self):
        def storeUsername():
            name = tempName.get()
            # Check for whitespace or SERVER
            if not any(char.isspace() for char in name) and not name.upper() == 'SERVER':
                tempFrame.destroy()
                self.startClient(name)
            else:
                tempPrompt.config(text="Invalid Username! Try again.")

        # Clear old menu info
        self.clearFrame()
        tempFrame = tk.Frame(self.frame)

        tempPrompt = tk.Label(tempFrame, text="Enter your Username", font=self.style)
        tempPrompt.grid(row=0, columnspan=2)
        tk.Label(tempFrame, text="Username", font=self.style).grid(row=1)
        tempName = tk.Entry(tempFrame, font=self.style)
        tempName.grid(row=1,column=1,)
        tk.Button(tempFrame, text='Save', font=self.style, command=storeUsername).grid(row=3, columnspan=2)

        tempFrame.place(anchor='c', relx=.5, rely=.5)

    def startServer(self):
        self.clearFrame()
        self.root.geometry("")
        tk.Label(self.frame, text="Server Running - IP: " + self.netInfo[0] + " Port: " + str(self.netInfo[1]), font=self.style).grid(row=0,columnspan=2)
        serverText = scrolledtext.ScrolledText(self.frame, width=100)
        serverText.grid(row=1,column=0)
        tk.Label(self.frame, text="Rooms", font=self.style).grid(row=0,column=2)
        roomText = scrolledtext.ScrolledText(self.frame, width=15)
        roomText.grid(row=1,column=2)
        tk.Label(self.frame, text="Users", font=self.style).grid(row=0,column=3)
        userText = scrolledtext.ScrolledText(self.frame, width=15)
        userText.grid(row=1,column=3)
        for i in range(25):
            serverText.insert("end","\n")
        serverText.see("end")
        self.server = server.Server(self.netInfo, serverText, roomText, userText)
        start_new_thread(self.server.runServer,())

    def startClient(self, username):
        def sendMsg():
            msg = inputText.get("1.0","end").strip()
            inputText.delete("1.0","end")
            self.client.sendMsg(msg)

        self.clearFrame()
        self.root.geometry("")
        tk.Label(self.frame, text="Connected to Server - IP: " + self.netInfo[0] + " Port: " + str(self.netInfo[1]), font=self.style).grid(row=0,columnspan=2)
        clientText = scrolledtext.ScrolledText(self.frame)
        clientText.grid(row=1,columnspan=2)
        for i in range(25):
            clientText.insert("end","\n")
        clientText.see("end")
        inputText = tk.Text(self.frame,height=5,width=74)
        inputText.grid(row=2,column=0)
        tk.Button(self.frame, text='Send', height=3,font=self.style, command=sendMsg).grid(row=2, column=1)
        roomFrame = tk.Frame(self.frame)
        roomFrame.grid(row=0,column=3,rowspan=2, sticky='n')
        self.client = client.Client(self.netInfo, username, clientText, roomFrame)
        start_new_thread(self.client.getServerMsgs,())
    
    def update(self, textBox, message):
        textBox.configure(state='normal')
        textBox.insert('end',message)
        textBox.see('end')
        textBox.configure(state='normal')
    
if __name__ == "__main__":
    root = tk.Tk()
    window = Gui(root)

    tk.mainloop()