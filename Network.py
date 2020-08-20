import socket


class Network:

    def __init__(self, IP):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = IP 
        self.port = 5555
        self.addr = (self.host, self.port)
        self.id = self.connect()

    def connect(self):
        self.client.connect(self.addr)
        return self.client.recv(2048).decode()

    def send(self, data):
        try:
            self.client.send(str.encode(data))
            return self.client.recv(2048).decode()
        except socket.error as e:
            return str(e)
