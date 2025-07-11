

'use client';

import { motion } from 'framer-motion';

const Portals = () => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="w-full max-w-5xl p-8 mx-auto text-center"
    >
      <h2 className="text-4xl font-bold text-center text-[#00ffcc] mb-8" style={{ textShadow: '0 0 10px #00ffcc' }}>
        External Portals
      </h2>
      <div className="flex justify-center gap-6">
        <a href="https://www.instagram.com/mista101999/" target="_blank" rel="noopener noreferrer" className="text-white hover:text-[#00ffcc] transition-colors">
          <svg className="w-10 h-10" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path fillRule="evenodd" d="M12.315 2c-4.02.084-5.544.228-7.5 2.184S2.084 8.295 2 12.315c-.084 4.02.228 5.544 2.184 7.5s3.48 2.268 7.5 2.184c4.02-.084 5.544-.228 7.5-2.184s2.268-3.48 2.184-7.5c.084-4.02-.228-5.544-2.184-7.5S16.335 2.084 12.315 2zM8.44 5.832a.972.972 0 011.164 0l4.44 2.563a.972.972 0 010 1.69l-4.44 2.563a.972.972 0 01-1.164-1.69L11.5 9.972l-3.06-1.766a.972.972 0 010-1.69z" clipRule="evenodd" />
          </svg>
        </a>
        <a href="https://www.facebook.com/masha.mistarenko.mista?locale=uk_UA" target="_blank" rel="noopener noreferrer" className="text-white hover:text-[#00ffcc] transition-colors">
          <svg className="w-10 h-10" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path fillRule="evenodd" d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z" clipRule="evenodd" />
          </svg>
        </a>
        <a href="https://t.me" target="_blank" rel="noopener noreferrer" className="text-white hover:text-[#00ffcc] transition-colors">
          <svg className="w-10 h-10" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M11.944 0C5.338 0 0 4.862 0 10.836c0 3.544 1.932 6.633 4.857 8.542L3.44 24l5.39-3.234c1.03.242 2.11.378 3.214.378 6.606 0 11.944-4.862 11.944-10.836C23.888 4.862 18.55 0 11.944 0zm5.083 7.635c.224.472.26.99.112 1.524-.148.534-.448.99-.82 1.292l-5.826 4.37c-.48.36-.996.54-1.548.54-.552 0-1.032-.18-1.44-.54-.408-.36-.612-.816-.612-1.368 0-.552.204-1.01.612-1.374l3.852-2.888-2.448 2.184c-.288.252-.6.378-.936.378-.336 0-.636-.126-.89-.378-.252-.252-.378-.552-.378-.9 0-.348.126-.648.378-.9l5.826-4.37c.48-.36.996-.54 1.548-.54.552 0 1.032.18 1.44.54.408.36.612.816.612 1.368z" />
          </svg>
        </a>
      </div>
    </motion.div>
  );
};

export default Portals;

