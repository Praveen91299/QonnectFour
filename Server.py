import socket
from _thread import *
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server = '' #replace with Server device IPv4
port = 5555

server_ip = socket.gethostbyname(server)
print("Server IP: " + server_ip)

try:
    s.bind((server, port))

except socket.error as e:
    print(str(e))

s.listen(2)
print("Waiting for a connection")

currentId = "0"
Data = ["0:0:h:0", "1:0:h:0"] #player:moveID:move:positions...
seed = 42
depth = 1
column = 7
StartPlayer = 0
def threaded_client(conn):
    global currentId, Data, seed, depth, column, StartPlayer
    conn.send(str.encode(currentId))
    currentId = "1"
    reply = ''
    while True:
        try:
            data = conn.recv(2048)
            reply = data.decode('utf-8')
            if not data:
                continue
            if reply == '2':
                conn.send(str.encode("Goodbye"))
                #break
            else:
                print("Recieved: " + reply)
                arr = reply.split(":")
                
                if arr[0] == "seed":
                    if arr[1] == "want":
                        send = str(seed) + ":" + str(depth) + ":" + str(column) + ":" + str(StartPlayer) #sends initial states
                        print(send)
                    else:
                        seed = int(arr[1])
                        depth = int(arr[2])
                        column = int(arr[3])
                        StartPlayer = int(arr[4])
                        send = str(1)
                elif len(arr) == 1: #get move
                    iden = int(arr[0])
                    send = Data[1-iden]
                elif len(arr) >= 4:
                    iden = int(arr[0])
                    Data[iden] = reply
                    print("Added move: " + reply)
                    send = reply
                print("Sending: " + send)
                conn.sendall(str.encode(send))
        except:
            print("Nothing received")
    
    print("Connection Closed")
    conn.close()

while True:
    conn, addr = s.accept()
    print("Connected to: ", addr)
    
    start_new_thread(threaded_client, (conn,))