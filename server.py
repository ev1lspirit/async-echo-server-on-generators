import collections
import socket
import enum
from select import select


class Phrases(str, enum.Enum):
    GREETINGS = "Hello, stranger! I'm an echo server."


class Mode(enum.Enum):
    READ = 0x1
    WRITE = 0x2


class AsyncSocket:
    def __init__(self, rsocket):
        self.socket = rsocket

    def send(self, *, message: str):
        yield Mode.WRITE, self.socket
        return self.socket.send(message.encode())

    def accept(self):
        yield Mode.READ, self.socket
        client_socket, address = self.socket.accept()
        return AsyncSocket(client_socket), address

    def recv(self, rbytes: int):
        yield Mode.READ, self.socket
        return self.socket.recv(rbytes)

    def __getattr__(self, item):
        return getattr(self.socket, item)


class Server:
    def __init__(self, *, address: str, port: int) -> None:
        self.address = address
        self.port = port
        self.socket = AsyncSocket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.wait_read = {}
        self.wait_write = {}
        self.tasks = collections.deque()
        self.messages = [Phrases.GREETINGS]
        self.socket.bind((self.address, self.port))
        self.socket.listen()
        self.tasks.append(self.accept_connection(self.socket))
        print(self.tasks)

    @property
    def server_socket(self):
        return self.socket

    def accept_connection(self, server_socket: AsyncSocket):
        while True:
            client_socket, address = yield from server_socket.accept()
            print(f"[+] Established connection with {address}")
            self.tasks.append(self.get_request_from_client(client_socket))

    def get_request_from_client(self, client: AsyncSocket):
        while True:
            message = yield from client.recv(4096)
            print(message)

            if message:
                if not self.messages:
                    self.messages.append(message.decode())
                phrase = self.messages.pop(0)
                try:
                    yield from client.send(message=phrase)
                except ConnectionResetError:
                    client.close()
            else:
                client.close()

    def run_event_loop(self):
        while any([self.wait_write, self.wait_read, self.tasks]):
            while not self.tasks:
                print('before select()')
                ready_to_read, ready_to_write, _ = select(self.wait_read, self.wait_write, [])
                for sock in ready_to_read:
                    self.tasks.append(self.wait_read.pop(sock))
                for sock in ready_to_write:
                    self.tasks.append(self.wait_write.pop(sock))

            task = self.tasks.popleft()
            next_val = next(task, (None, None))
            print(next_val)

            if all(next_val):
                why, what = next_val
                if why == Mode.READ:
                    self.wait_read[what] = task
                elif why == Mode.WRITE:
                    self.wait_write[what] = task
                else:
                    raise RuntimeError("Error")

            print(self.wait_read)


server = Server(address="192.168.196.199", port=9090)
server.run_event_loop()
