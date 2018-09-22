import socket

modhost_client = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
modhost_client.connect ( ("localhost", 5555) )

modhost_client.sendall (b'load /home/flappix/docs/code/raspberry-looper/mod-host/mod-host-config.txt')
