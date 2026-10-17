import React, { useEffect, useRef } from 'react';

interface PaymentsRaceProps {
  humanLatencyEstimateMs?: number;
  agentObservedLatencyMs?: number;
}

export const PaymentsRace: React.FC<PaymentsRaceProps> = ({
  humanLatencyEstimateMs = 45000,
  agentObservedLatencyMs = 380
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
        vx: isAgent ? (Math.random() * 1.5 + 0.8) : (Math.random() * 0.2 + 0.05),
        vy: (Math.random() - 0.5) * 0.3,
        radius: isAgent ? Math.random() * 2 + 1.2 : Math.random() * 2 + 1,
        alpha: Math.random() * 0.6 + 0.4,
        color: isAgent ? '#7D292D' : '#82786F',
      });
    }

    const render = () => {
      ctx.fillStyle = '#F7F4EE';
      ctx.fillRect(0, 0, width, height);

      // Subtle warm grid
      ctx.strokeStyle = 'rgba(207, 199, 187, 0.45)';
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
      ctx.strokeStyle = '#CFC7BB';
      ctx.beginPath();
      ctx.moveTo(0, height * 0.52);
      ctx.lineTo(width, height * 0.52);
      ctx.stroke();

      // Render particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x > width) p.x = 0;
        if (p.x < 0) p.x = width;
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
  }, []);

  return (
    <div className="rounded-xl overflow-hidden border border-[#CFC7BB] bg-[#F7F4EE] shadow-xs">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#CFC7BB] flex items-center justify-between bg-[#DED8CD]/30 text-xs font-sans">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-[#241B19]">Payment Flow Visualizer</span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB]">
            Telemetry
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#82786F]" />
            <span className="text-[#82786F]">Classical Human Flow:</span>
            <span className="text-[#241B19] font-medium">~{humanLatencyEstimateMs / 1000}s</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#7D292D]" />
            <span className="text-[#82786F]">Autonomous x402:</span>
            <span className="text-[#7D292D] font-bold">~{agentObservedLatencyMs}ms</span>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="relative w-full h-[220px] bg-[#F7F4EE]">
        <canvas ref={canvasRef} className="w-full h-full block" />
        <div className="absolute left-3 top-2.5 text-[11px] font-sans text-[#82786F] bg-[#FFFFFF]/90 px-2.5 py-1 rounded-md border border-[#CFC7BB] shadow-xs">
          Manual Human Flow (Cards / Auth / OTP)
        </div>
        <div className="absolute left-3 bottom-2.5 text-[11px] font-sans text-[#7D292D] font-medium bg-[#FFFFFF]/90 px-2.5 py-1 rounded-md border border-[#CFC7BB] shadow-xs">
          Autonomous x402 Flow (EIP-712 / Instant Settlement)
        </div>
      </div>
    </div>
  );
};

