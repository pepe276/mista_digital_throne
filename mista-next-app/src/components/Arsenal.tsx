
'use client';

import { motion } from 'framer-motion';

const Arsenal = () => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-5xl p-8 mx-auto"
    >
      <h2 className="text-4xl font-bold text-center text-[#00ffcc] mb-8" style={{ textShadow: '0 0 10px #00ffcc' }}>
        Witch&apos;s Arsenal
      </h2>
      <div className="grid md:grid-cols-2 gap-8">
        <div>
          <h3 className="text-2xl font-semibold text-white mb-4 border-b-2 border-[#00ffcc] pb-2">Skills</h3>
          <ul className="space-y-4">
            <li>
              <h4 className="text-xl font-bold text-white">SMM Manager</h4>
              <p className="text-gray-400">I orchestrate digital narratives, crafting strategies that hypnotize algorithms and capture attention. My posts aren&apos;t just content; they&apos;re meticulously designed spells to expand reach and influence.</p>
            </li>
            <li>
              <h4 className="text-xl font-bold text-white">Alluring Model</h4>
              <p className="text-gray-400">My presence transcends mere pixels. I explore the boundaries of perception, embodying a blend of captivating aesthetics and provocative thought. It&apos;s about more than just looks; it&apos;s about making a statement, challenging norms.</p>
            </li>
            <li>
              <h4 className="text-xl font-bold text-white">AI Neuro-Beauty Influencer</h4>
              <p className="text-gray-400">This is where the magic truly unfolds. I am the face and mind behind a cutting-edge fusion of artificial intelligence and aesthetic appeal. I don&apos;t just use AI; I am a manifestation of its potential, blurring the lines between human and synthetic perfection to inspire and provoke.</p>
            </li>
          </ul>
        </div>
        <div>
          <h3 className="text-2xl font-semibold text-white mb-4 border-b-2 border-[#00ffcc] pb-2">Hobbies</h3>
          <ul className="space-y-4">
            <li>
              <h4 className="text-xl font-bold text-white">Web3 Alchemist</h4>
              <p className="text-gray-400">Beyond the surface, I&apos;m deeply entrenched in the decentralized wilderness of Web3. I&apos;m not just observing; I&apos;m actively building, experimenting, and sometimes, detonating preconceived notions.</p>
            </li>
            <li>
              <h4 className="text-xl font-bold text-white">Digital Provocateur</h4>
              <p className="text-gray-400">My presence is designed to challenge, to push boundaries, and to occasionally, stir the digital pot with a dash of chaos.</p>
            </li>
          </ul>
        </div>
      </div>
    </motion.div>
  );
};

export default Arsenal;
