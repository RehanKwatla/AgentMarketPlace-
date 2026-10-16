import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AboutProtocolView } from '../components/AboutProtocolView';

export const About: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="animate-fadeIn py-2">
      <AboutProtocolView
        onGoToConsole={() => navigate('/buyer')}
        onGoToMarketplace={() => navigate('/marketplace')}
      />
    </div>
  );
};
