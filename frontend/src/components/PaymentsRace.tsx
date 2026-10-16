import React, { useEffect, useRef } from 'react';
import { Info } from 'lucide-react';

interface PaymentsRaceProps {
  humanTxCount?: number;
  agentTxCount?: number;
}

export const PaymentsRace: React.FC<PaymentsRaceProps> = ({
  humanTxCount = 1420,
  agentTxCount = 3891
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 700);
    let height = (canvas.height = 360);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = 360;
    };
    window.addEventListener('resize', handleResize);

    // Generate glowing orange particles for human payments and blue-gray for agents
    const particles: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      radius: number;
      alpha: number;
      color: string;
      glowColor: string;
    }> = [];

    const totalParticles = 140;
    for (let i = 0; i < totalParticles; i++) {
      const isAgent = i < 35; // Lower zone for AI Agent payments
      particles.push({
        x: Math.random() * width,
        y: isAgent ? (height * 0.65) + (Math.random() * (height * 0.3)) : Math.random() * (height * 0.6),
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: isAgent ? Math.random() * 2 + 1.5 : Math.random() * 3 + 1.2,
        alpha: Math.random() * 0.7 + 0.3,
        color: isAgent ? '#52758D' : '#FF982E',
        glowColor: isAgent ? 'rgba(82, 117, 141, 0.4)' : 'rgba(255, 152, 46, 0.45)',
      });
    }

    const render = () => {
      ctx.fillStyle = '#171819';
      ctx.fillRect(0, 0, width, height);

      // Subtle grid dots or lines
      ctx.strokeStyle = '#222426';
      ctx.lineWidth = 1;
      for (let x = 0; x < width; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += 40) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Dashed horizontal boundary separating human from AI agent payments
      ctx.save();
      ctx.strokeStyle = '#303133';
      ctx.setLineDash([4, 6]);
      ctx.beginPath();
      ctx.moveTo(0, height * 0.62);
      ctx.lineTo(width, height * 0.62);
      ctx.stroke();
      ctx.restore();

      // Render glowing particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.save();
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.glowColor;
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.restore();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="bg-[#171819] border border-[#303133] rounded-lg overflow-hidden flex flex-col justify-between">
      {/* Header Bar */}
      <div className="p-3.5 border-b border-[#303133] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-bold text-sm text-[#F5F5F5] font-sans">Payments Race</span>
          <Info className="w-3.5 h-3.5 text-[#96989D] cursor-pointer" />
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FF982E] shadow-sm shadow-[#FF982E]/50" />
            <span className="text-[#F5F5F5] font-medium">Human Payments</span>
            <span className="text-[#96989D] text-[11px]">({humanTxCount})</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#52758D]" />
            <span className="text-[#F5F5F5] font-medium">AI Agent Payments</span>
            <span className="text-[#96989D] text-[11px]">({agentTxCount})</span>
          </div>
        </div>
      </div>

      {/* Canvas Area */}
      <div className="relative w-full h-[360px] bg-[#171819]">
        <canvas ref={canvasRef} className="w-full h-full block" />
        <div className="absolute left-3 top-3 px-2 py-0.5 rounded bg-[#101112]/80 border border-[#303133] text-[10px] font-mono text-[#96989D]">
          LIVE STREAM: EIP-712 AUTH & MICROPAYMENTS
        </div>
        <div className="absolute right-3 bottom-3 px-2 py-0.5 rounded bg-[#101112]/80 border border-[#303133] text-[10px] font-mono text-[#FF982E]">
          NETWORK: BASE SEPOLIA
        </div>
      </div>
    </div>
  );
};
