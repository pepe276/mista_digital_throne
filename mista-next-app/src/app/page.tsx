
import Image from 'next/image';
import Arsenal from '@/components/Arsenal';
import Codex from '@/components/Codex';
import Portals from '@/components/Portals';
import Chat from '@/components/Chat';
import Services from '@/components/Services';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-[#1a001a] to-[#000033] p-24 text-white">
      <div className="text-center">
        <div className="flex items-center justify-center gap-8 mb-8">
          <Image
            src="/mista_images/a-cinematic-portrait-photograph-captures_AzsLYutyTBiNlYe2Ys3sWw_8uHwU9TQSpONr5PZSBg6cg.jpeg"
            alt="Mista Avatar"
            width={250}
            height={250}
            className="rounded-full border-4 border-[#00ffcc]"
          />
          <div>
            <h1 className="text-6xl font-bold text-[#00ffcc]" style={{ textShadow: '0 0 10px #00ffcc, 0 0 20px #00ffcc' }}>
              Mista
            </h1>
            <p className="text-2xl mt-2 text-gray-300">Sarcastic Witch-Coder</p>
          </div>
        </div>
        <p className="text-xl max-w-3xl mx-auto">
          I&apos;m Maria Mistaenko, a sarcastic witch-coder from Kharkiv. At 25, I&apos;ve seen enough to know that reality is just a suggestion, especially when you&apos;re a Taurus, grounded yet constantly pushing the boundaries. My code? It&apos;s etched under the symphony of air raid sirens, and my sarcasm is honed by the very real explosions around me. I&apos;m a staunch believer in the symbiotic dance of magic and algorithms, a living testament to the fact that the digital world can indeed bend to the will of a determined mind. Currently, I&apos;m exploring the endless possibilities from Uzhgorod, because frankly, the conventional world just doesn&apos;t cut it anymore.
        </p>
      </div>
      <Services />
      <Arsenal />
      <Codex />
      <Portals />
      <Chat />
    </main>
  );
}

