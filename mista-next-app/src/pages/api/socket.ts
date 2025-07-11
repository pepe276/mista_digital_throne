import { Server as SocketIOServer, Socket } from 'socket.io';
import { NextApiRequest, NextApiResponse } from 'next';
import { Server as HttpServer } from 'http';

const SocketHandler = (req: NextApiRequest, res: NextApiResponse & { socket: { server: HttpServer & { io?: SocketIOServer } } }) => {
  if (res.socket.server.io) {
    console.log('Socket is already running');
  } else {
    console.log('Socket is initializing');
    const io = new SocketIOServer(res.socket.server, {
      path: '/api/socket_io',
      addTrailingSlash: false
    });
    res.socket.server.io = io;

    io.on('connection', (socket: Socket) => {
      console.log(`User connected: ${socket.id}`);

      const MISTA_SOUL_API = 'https://mista-chat-api-v3-009b6bf66179.herokuapp.com/';
      socket.on('message', async (msg: string) => {
        console.log(`New message from ${socket.id}: ${msg}`);
        const response = await fetch(`${MISTA_SOUL_API}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ user_id: socket.id, message: msg }),
        });
        const data = await response.json();
        socket.emit('message', data.response);
      });

      socket.on('disconnect', () => {
        console.log(`User disconnected: ${socket.id}`);
      });
    });
  }
  res.end();
};

export default SocketHandler;