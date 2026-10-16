import React, { useEffect, useRef } from 'react';

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
    let height = (canvas.height = 240);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = 240;
    };
    window.addEventListener('resize', handleResize);

    const particles: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      radius: number;
      alpha: number;
      color: string;
    }> = [];

    const totalParticles = 70;
    for (let i = 0; i < totalParticles; i++) {
      const isAgent = i < 35;
      particles.push({
        x: Math.random() * width,
        y: isAgent ? (height * 0.55) + (Math.random() * (height * 0.40)) : Math.random() * (height * 0.50),
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: isAgent ? Math.random() * 1.8 + 1 : Math.random() * 2 + 1,
        alpha: Math.random() * 0.5 + 0.3,
        color: isAgent ? '#36D6C8' : '#42C995',
      });
    }

    const render = () => {
      ctx.fillStyle = '#0F1313';
      ctx.fillRect(0, 0, width, height);

      // Subtle grid
      ctx.strokeStyle = 'rgba(120, 160, 153, 0.07)';
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

      // Divider line
      ctx.strokeStyle = 'rgba(120, 160, 153, 0.16)';
      ctx.beginPath();
      ctx.moveTo(0, height * 0.52);
      ctx.lineTo(width, height * 0.52);
      ctx.stroke();

      // Render particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.fill();
        ctx.globalAlpha = 1.0;
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [humanTxCount, agentTxCount]);

  return (
    <div className="wallet-card rounded-lg overflow-hidden border border-[rgba(120,160,153,0.18)]">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-[rgba(120,160,153,0.16)] flex items-center justify-between bg-[#0E1212] text-xs font-sans">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[#F4F7F6]">Payment Flow Visualizer</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#161B1A] text-[#9BA5A2] border border-[rgba(120,160,153,0.2)]">
            Telemetry
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#42C995]" />
            <span className="text-[#9BA5A2]">Human:</span>
            <span className="text-[#F4F7F6]">{humanTxCount}</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#36D6C8]" />
            <span className="text-[#9BA5A2]">Agent:</span>
            <span className="text-[#36D6C8] font-medium">{agentTxCount}</span>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="relative w-full h-[240px] bg-[#0F1313]">
        <canvas ref={canvasRef} className="w-full h-full block" />
        <div className="absolute left-3 top-2.5 text-[11px] font-sans text-[#6B7673]">
          Manual Human Flow
        </div>
        <div className="absolute left-3 bottom-2.5 text-[11px] font-sans text-[#36D6C8]">
          Autonomous x402 Flow
        </div>
      </div>
    </div>
  );
};
