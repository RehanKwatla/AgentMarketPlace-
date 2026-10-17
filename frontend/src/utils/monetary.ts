/**
 * Authoritative monetary utility functions for DI-06 USDC micro-settlements.
 * Prevents floating-point precision issues by using integer atomic units (6 decimals).
 */

/**
 * Converts a decimal USDC string to authoritative integer atomic base units (6 decimals).
 * Example: '0.002' -> 2000, '0.05' -> 50000, '1.5' -> 1500000
 */
export function toAtomicUnits(usdcString: string): number {
  const clean = usdcString.trim();
  if (!clean) return 0;
  
  // Verify numeric format with optional decimal
  if (!/^\d+(\.\d+)?$/.test(clean)) return 0;
  
  const [whole, frac = ''] = clean.split('.');
  const wholeInt = parseInt(whole, 10);
  if (isNaN(wholeInt)) return 0;
  
  // Pad or trim fraction to exactly 6 digits
  const paddedFrac = frac.padEnd(6, '0').slice(0, 6);
  const fracInt = parseInt(paddedFrac, 10);
  
  return wholeInt * 1_000_000 + fracInt;
}

/**
 * Converts integer atomic base units to decimal USDC string representation.
 * Example: 2000 -> '0.002000', 50000 -> '0.050000'
 */
export function fromAtomicUnits(atomicUnits: number): string {
  if (isNaN(atomicUnits) || atomicUnits < 0) return '0.000000';
  const whole = Math.floor(atomicUnits / 1_000_000);
  const frac = (atomicUnits % 1_000_000).toString().padStart(6, '0');
  return `${whole}.${frac}`;
}

/**
 * Validates natural-language task prompt against backend requirements.
 */
export function validateTaskPrompt(prompt: string): { isValid: boolean; error?: string } {
  const trimmed = prompt.trim();
  if (!trimmed) {
    return { isValid: false, error: 'Task objective cannot be empty.' };
  }
  if (trimmed.length < 3) {
    return { isValid: false, error: 'Task prompt must contain at least 3 characters.' };
  }
  return { isValid: true };
}

/**
 * Validates budget input against backend requirements and atomic units.
 */
export function validateBudget(budgetUsdc: string): { 
  isValid: boolean; 
  error?: string; 
  atomicUnits: number 
} {
  const trimmed = budgetUsdc.trim();
  if (!trimmed) {
    return { isValid: false, error: 'Budget allowance is required.', atomicUnits: 0 };
  }
  
  if (!/^\d+(\.\d+)?$/.test(trimmed)) {
    return { isValid: false, error: 'Budget must be a valid positive number.', atomicUnits: 0 };
  }
  
  const atomic = toAtomicUnits(trimmed);
  if (atomic <= 0) {
    return { isValid: false, error: 'Budget must be strictly positive (> 0 USDC).', atomicUnits: 0 };
  }
  
  return { isValid: true, atomicUnits: atomic };
}
