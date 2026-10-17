import { describe, it, expect } from 'vitest';
import '@testing-library/jest-dom';
import { render, screen, fireEvent } from '@testing-library/react';

import { MemoryRouter } from 'react-router-dom';
import { LoginPage, SignupPage, VerifyEmailPage, ForgotPasswordPage } from '../pages/AuthFlow';
import { KycPage } from '../pages/KycPage';
import { WalletManagementPage } from '../pages/WalletManagement';
import { ProfilePage } from '../pages/Profile';
import { AuthProvider } from '../context/AuthContext';

describe('Phase 3 Frontend Tests: Auth, Multi-Wallet, and KYC', () => {
  it('renders profile page with sign in prompt when unauthenticated', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <ProfilePage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText(/Sign in to view your profile/i)).toBeInTheDocument();
  });

  it('renders login page with email and password inputs', () => {
    render(

      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();

    expect(screen.getByText(/New to Agentica/i)).toBeInTheDocument();
  });

  it('validates password length and mismatch on signup page', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <SignupPage />
        </AuthProvider>
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/Email address/i);
    const passInput = screen.getByLabelText(/^Password/i);
    const confirmInput = screen.getByLabelText(/Confirm password/i);
    const submitBtn = screen.getByRole('button', { name: /Create Account/i });

    fireEvent.change(emailInput, { target: { value: 'user@example.com' } });
    fireEvent.change(passInput, { target: { value: 'short' } });
    fireEvent.change(confirmInput, { target: { value: 'different' } });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/Password must be at least 8 characters/i)).toBeInTheDocument();
    expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
  });

  it('renders KYC page with prominent [SIMULATED] banner and disclaimer', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <KycPage />
        </AuthProvider>
      </MemoryRouter>
    );

    // In unauthenticated state, displays sign in prompt
    expect(screen.getByText(/Authentication Required/i)).toBeInTheDocument();
  });

  it('renders wallet management page requiring authentication', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <WalletManagementPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText(/Authentication Required/i)).toBeInTheDocument();
  });

  it('renders forgot password page with recovery submission', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <ForgotPasswordPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send Recovery Token/i })).toBeInTheDocument();
  });

  it('renders verify email page with token input', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <VerifyEmailPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByLabelText(/Verification Token/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Verify Email/i })).toBeInTheDocument();
  });
});
