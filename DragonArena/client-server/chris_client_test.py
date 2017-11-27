import chris_shit

client_sock = chris_shit.sock_client("127.0.0.1", 2002)
msg = chris_shit.Message((2,3,[3,4]))
chris_shit.write_to(client_sock, msg)
