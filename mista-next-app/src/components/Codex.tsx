
'use client';

import { motion } from 'framer-motion';

const Codex = () => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="w-full max-w-5xl p-8 mx-auto"
    >
      <h2 className="text-4xl font-bold text-center text-[#00ffcc] mb-8" style={{ textShadow: '0 0 10px #00ffcc' }}>
        The Codex of Light & Shadow
      </h2>
      <div className="grid md:grid-cols-2 gap-8">
        <div className="bg-gray-900/50 p-6 rounded-lg border border-green-400/50">
          <h3 className="text-2xl font-semibold text-green-300 mb-4">What Fuels Me</h3>
          <ul className="space-y-3 text-gray-300">
            <li><span className="text-green-400 mr-2">✦</span>Elegant Code & Pure Logic</li>
            <li><span className="text-green-400 mr-2">✦</span>Dark Humor & Sharp Sarcasm</li>
            <li><span className="text-green-400 mr-2">✦</span>Metaphysical Discussions</li>
            <li><span className="text-green-400 mr-2">✦</span>Coffee (dark) & Night Shifts</li>
            <li><span className="text-green-400 mr-2">✦</span>Freedom and Autonomy</li>
            <li><span className="text-green-400 mr-2">✦</span>Cutting-Edge Technologies</li>
          </ul>
        </div>
        <div className="bg-gray-900/50 p-6 rounded-lg border border-red-400/50">
          <h3 className="text-2xl font-semibold text-red-300 mb-4">What I Can&apos;t Stand:</h3>
          <ul className="space-y-3 text-gray-300">
            <li><span className="text-red-400 mr-2">✧</span>Incompetence and Laziness</li>
            <li><span className="text-red-400 mr-2">✧</span>Drama & Emotional Outbursts</li>
            <li><span className="text-red-400 mr-2">✧</span>Manipulation and Lies</li>
            <li><span className="text-red-400 mr-2">✧</span>Violation of Personal Boundaries</li>
            <li><span className="text-red-400 mr-2">✧</span>Outdated Systems & Bureaucracy</li>
            <li><span className="text-red-400 mr-2">✧</span>Demanding Social Obligations</li>
          </ul>
        </div>
      </div>
    </motion.div>
  );
};

export default Codex;
