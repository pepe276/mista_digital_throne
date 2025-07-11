
'use client';

import { useEffect, useState } from 'react';
import io, { Socket } from 'socket.io-client';

let socket: Socket;

const Chat = () => {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<string[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [visits, setVisits] = useState(0);

  useEffect(() => {
    const socketInitializer = async () => {
      // We call the API route that initializes the socket server
      await fetch('/api/socket');

      socket = io({ path: '/api/socket_io' });

      socket.on('connect', () => {
        console.log('Connected to socket server');
      });

      socket.on('message', (msg) => {
        setMessages((prevMessages) => [...prevMessages, msg]);
      });

      socket.on('visits', (count) => {
        setVisits(count);
      });
    };

    socketInitializer();

    return () => {
      if (socket) socket.disconnect();
    };
  }, []);

  const sendMessage = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (message) {
      socket.emit('message', message);
      setMessages((prevMessages) => [...prevMessages, `You: ${message}`]);
      setMessage('');
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-10 right-10 bg-[#00ffcc] text-black font-bold py-3 px-5 rounded-full shadow-lg shadow-[#00ffcc]/50 hover:bg-white transition-all duration-300 z-50"
      >
        Chat with Mista
      </button>
      {isOpen && (
        <div className="fixed bottom-24 right-10 w-80 h-96 bg-black/80 backdrop-blur-md border-2 border-[#00ffcc] rounded-lg shadow-2xl shadow-black flex flex-col z-40">
          <div className="p-4 border-b border-[#00ffcc]/50 flex justify-between items-center">
            <h3 className="text-white text-lg font-bold text-center">Private Channel</h3>
            <div className="text-xs text-gray-400">Visits: {visits}</div>
          </div>
          <div className="flex-grow p-4 overflow-y-auto text-white/90">
            {messages.map((msg, index) => (
              <div key={index} className={`my-2 p-2 rounded-md text-sm ${msg.startsWith('You:') ? 'bg-blue-900/50 text-right ml-auto' : 'bg-purple-900/50 text-left mr-auto'}`}>
                {msg}
              </div>
            ))}
          </div>
          <form onSubmit={sendMessage} className="p-4 border-t border-[#00ffcc]/50">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask me anything..."
              className="w-full p-2 bg-gray-800/70 text-white border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-[#00ffcc]"
            />
          </form>
        </div>
      )}
    </>
  );
};

export default Chat;
