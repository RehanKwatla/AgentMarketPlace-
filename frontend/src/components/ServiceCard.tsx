import React from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';

interface ServiceCardProps {
  service: ServiceDefinition;
  reputation?: ReputationMetrics;
}

export const ServiceCard: React.FC<ServiceCardProps> = ({ service, reputation }) => {
  const getBadgeColor = (category: string) => {
    switch (category) {
      case 'data': return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      case 'scraping': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'inference': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      default: return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
  };

  return (
    <div className="glass-card rounded-xl p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className={`text-xs uppercase font-mono px-2.5 py-1 rounded-md border font-medium ${getBadgeColor(service.category)}`}>
            {service.category}
          </span>
          <span className="text-sm font-mono text-emerald-400 font-semibold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
            {service.price_usdc} USDC
          </span>
        </div>

        <h3 className="text-base font-semibold text-white mb-1.5">{service.name}</h3>
        <p className="text-xs text-slate-400 mb-4 leading-relaxed line-clamp-2">{service.description}</p>
      </div>

      <div className="pt-3 border-t border-slate-800/80 text-xs text-slate-400 flex items-center justify-between font-mono">
        <div>
          <span>ID: </span>
          <span className="text-slate-200">{service.service_id}</span>
        </div>
        {reputation && (
          <div>
            <span>Rep: </span>
            <span className="text-blue-400 font-medium">{reputation.reputation_score}%</span>
          </div>
        )}
      </div>
    </div>
  );
};
