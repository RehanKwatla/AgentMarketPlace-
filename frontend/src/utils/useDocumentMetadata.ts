import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

interface RouteMetadata {
  title: string;
  description: string;
}

const getRouteMetadata = (pathname: string): RouteMetadata => {
  const cleanPath = pathname.replace(/\/+$/, '') || '/';

  // 1. Dashboard
  if (cleanPath === '/' || cleanPath === '/dashboard') {
    return {
      title: 'Dashboard | Pay-per-Call Agent Economy',
      description: 'Real-time metrics, active AI service telemetry, and cryptographic micropayment settlements on Base Sepolia.',
    };
  }

  // 2. Marketplace
  if (cleanPath === '/marketplace') {
    return {
      title: 'Marketplace | Pay-per-Call Agent Economy',
      description: 'Discover registered AI services, filter by category and pricing, and inspect EIP-712 payment authorization specifications.',
    };
  }

  // 3. Buyer Console
  if (cleanPath === '/buyer') {
    return {
      title: 'Buyer Console | Pay-per-Call Agent Economy',
      description: 'Compose autonomous multi-hop tasks, define maximum USDC spending budgets, and orchestrate verified AI service workflows.',
    };
  }

  // 4. Agent Execution (with and without taskId)
  if (cleanPath.startsWith('/execution')) {
    const parts = cleanPath.split('/');
    const taskId = parts[2];
    if (taskId && taskId.trim().length > 0) {
      const shortId = taskId.length > 8 ? `${taskId.slice(0, 8)}...` : taskId;
      return {
        title: `Agent Execution: ${shortId} | Pay-per-Call Agent Economy`,
        description: `Real-time execution telemetry and step-by-step verification for task ${taskId}.`,
      };
    }
    return {
      title: 'Agent Execution | Pay-per-Call Agent Economy',
      description: 'Real-time telemetry and step-by-step verification of autonomous multi-hop service calls and x402 payment authorization.',
    };
  }

  // 5. Payment Processing
  if (cleanPath === '/payments') {
    return {
      title: 'Payment Processing | Pay-per-Call Agent Economy',
      description: 'Inspect x402 payment requirements, authoritatively verified settlements, and Base Sepolia on-chain transaction records.',
    };
  }

  // 6. Results (with and without taskId)
  if (cleanPath.startsWith('/results')) {
    const parts = cleanPath.split('/');
    const taskId = parts[2];
    if (taskId && taskId.trim().length > 0) {
      const shortId = taskId.length > 8 ? `${taskId.slice(0, 8)}...` : taskId;
      return {
        title: `Results: ${shortId} | Pay-per-Call Agent Economy`,
        description: `Cryptographic proof of work, output schema validation, and multi-agent synthesis provenance for task ${taskId}.`,
      };
    }
    return {
      title: 'Results | Pay-per-Call Agent Economy',
      description: 'Cryptographic proof of work, output schema validation, and multi-agent synthesis provenance for completed tasks.',
    };
  }

  // 7. Ledger
  if (cleanPath === '/ledger') {
    return {
      title: 'Ledger | Pay-per-Call Agent Economy',
      description: 'Immutable audit trail of recorded calls, verified transaction hashes, and atomic USDC payments on Base Sepolia.',
    };
  }

  // Secondary utility pages
  if (cleanPath === '/seller') {
    return {
      title: 'Seller Tools | Pay-per-Call Agent Economy',
      description: 'Service provider registration, pricing controls, and HTTP 402 challenge flow configuration.',
    };
  }
  if (cleanPath === '/analytics') {
    return {
      title: 'Analytics | Pay-per-Call Agent Economy',
      description: 'Network telemetry, latency benchmarks, and economic throughput distribution.',
    };
  }
  if (cleanPath === '/about') {
    return {
      title: 'About | Pay-per-Call Agent Economy',
      description: 'Decentralized autonomous agent microservice economy specification and architecture.',
    };
  }
  if (cleanPath === '/docs') {
    return {
      title: 'Documentation | Pay-per-Call Agent Economy',
      description: 'Developer integration guide and FastAPI specifications for autonomous buyer and seller agents.',
    };
  }

  // 404 Not Found
  return {
    title: 'Page Not Found | Pay-per-Call Agent Economy',
    description: 'The requested page could not be found on Agentica Pay-per-Call Agent Economy.',
  };
};

export const useDocumentMetadata = () => {
  const location = useLocation();

  useEffect(() => {
    const { title, description } = getRouteMetadata(location.pathname);
    document.title = title;

    let metaDesc = document.querySelector('meta[name="description"]');
    if (!metaDesc) {
      metaDesc = document.createElement('meta');
      metaDesc.setAttribute('name', 'description');
      document.head.appendChild(metaDesc);
    }
    metaDesc.setAttribute('content', description);
  }, [location.pathname]);
};
