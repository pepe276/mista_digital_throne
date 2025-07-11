
'use client';

import { motion } from 'framer-motion';

const services = [
  {
    title: 'Personal Consultation',
    description: 'A one-on-one session to discuss your goals, fears, and desires. I will provide my unique perspective and guidance.',
    price: '$50/hour',
  },
  {
    title: 'Exclusive Photo Set',
    description: 'A collection of high-resolution, artistic photos, curated by me. A glimpse into my world.',
    price: '$25',
  },
  {
    title: 'Prompt Engineering',
    description: 'I will craft a custom, powerful prompt for your AI model, designed to achieve your specific goals.',
    price: '$100',
  },
];

const Services = () => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.6 }}
      className="w-full max-w-5xl p-8 mx-auto"
    >
      <h2 className="text-4xl font-bold text-center text-[#00ffcc] mb-8" style={{ textShadow: '0 0 10px #00ffcc' }}>
        My Services
      </h2>
      <div className="grid md:grid-cols-3 gap-8">
        {services.map((service, index) => (
          <div key={index} className="bg-gray-900/50 p-6 rounded-lg border border-purple-400/50 text-center">
            <h3 className="text-2xl font-semibold text-purple-300 mb-4">{service.title}</h3>
            <p className="text-gray-400 mb-4">{service.description}</p>
            <p className="text-2xl font-bold text-white mb-4">{service.price}</p>
            <button className="bg-purple-600 text-white font-bold py-2 px-4 rounded-full hover:bg-purple-700 transition-colors">
              Inquire
            </button>
          </div>
        ))}
      </div>
    </motion.div>
  );
};

export default Services;
