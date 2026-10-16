import React from 'react';

interface WalletBackgroundProps {
  subtle?: boolean;
}

export const WalletBackground: React.FC<WalletBackgroundProps> = ({ subtle = false }) => {
  return (
    <div 
      className="absolute top-0 left-0 right-0 h-[480px] pointer-events-none overflow-hidden z-0" 
      aria-hidden="true"
    >
      {/* Subtle, restrained upper-center ambient glow */}
      <div 
        className="absolute top-[-100px] left-1/2 -translate-x-1/2 w-[720px] h-[320px] rounded-full blur-[120px] pointer-events-none"
        style={{
          background: subtle 
            ? 'radial-gradient(ellipse at center, rgba(255, 255, 255, 0.03) 0%, rgba(10, 10, 10, 0) 70%)' 
            : 'radial-gradient(ellipse at center, rgba(255, 255, 255, 0.05) 0%, rgba(38, 38, 38, 0.02) 40%, rgba(10, 10, 10, 0) 70%)'
        }}
      />
    </div>
  );
};
