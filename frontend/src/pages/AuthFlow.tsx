import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, Eye, EyeOff, Fingerprint, ShieldCheck, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './AuthFlow.css';


type Step = 'account' | 'profile' | 'marketplace';

function AuthShell({ step, children }: { step: Step; children: React.ReactNode }) {
  const steps: { id: Step; label: string }[] = [
    { id: 'account', label: 'Account' },
    { id: 'profile', label: 'Profile' },
    { id: 'marketplace', label: 'Marketplace' },
  ];

  return (
    <main className="auth-page">
      <div className="auth-page-top">
        <Link to="/" className="auth-wordmark" aria-label="Agentica home">
          <span className="auth-brand-mark" aria-hidden="true"><i /><i /><i /></span>
          Agentica<span>.</span>
        </Link>
        <Link className="auth-return" to="/"><ArrowLeft size={15} /> Return to landing</Link>
      </div>

      <div className="auth-layout">
        <aside className="auth-story" aria-label="Onboarding steps">
          <div className="auth-story-orbit auth-story-orbit-one" />
          <div className="auth-story-orbit auth-story-orbit-two" />
          <div className="auth-story-content">
            <div className="auth-eyebrow"><span className="auth-eyebrow-dot" /> AGENTICA ACCESS</div>
            <div className="auth-story-icon"><Fingerprint size={27} strokeWidth={1.5} /></div>
            <p className="auth-story-kicker">A considered first step</p>
            <h1>Identity<br />before <em>access.</em></h1>
            <p className="auth-story-copy">A clear introduction helps shape a marketplace that works for people and their agents.</p>
            <ol className="auth-step-list">
              {steps.map((item, index) => {
                const activeIndex = steps.findIndex((entry) => entry.id === step);
                const complete = index < activeIndex;
                return (
                  <li className={item.id === step ? 'is-current' : complete ? 'is-complete' : ''} key={item.id}>
                    <span className="auth-step-number" aria-hidden="true">{complete ? <Check size={13} /> : `0${index + 1}`}</span>
                    <span>{item.label}</span>
                    {item.id === step && <span className="auth-step-current">CURRENT</span>}
                  </li>
                );
              })}
            </ol>
          </div>
          <div className="auth-story-foot"><span>PRIVATE BY DESIGN</span><span>01 — 03</span></div>
        </aside>

        <section className="auth-form-panel">
          <div className="auth-mobile-kicker"><span /> AGENTICA ACCESS</div>
          <div className="auth-step-mobile" aria-label={`Step ${steps.findIndex((item) => item.id === step) + 1} of 3`}>
            {steps.map((item) => (
              <span
                key={item.id}
                className={
                  item.id === step ||
                  steps.findIndex((s) => s.id === item.id) < steps.findIndex((s) => s.id === step)
                    ? 'active'
                    : ''
                }
              />
            ))}
          </div>
          {children}
          <div className="auth-form-foot">
            <ShieldCheck size={15} />
            <span>Secure Authentication · Salted bcrypt hashing · JWT revocation</span>
          </div>
        </section>
      </div>
      <footer className="auth-page-footer">
        <span>Agentica · Pay-per-call agent economy</span>
        <span>BASE SEPOLIA <i /> x402 V2</span>
      </footer>
    </main>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const emailError = !email.trim() ? 'Enter your email address.' : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? 'Enter a valid email address.' : '';
  const passwordError = password ? '' : 'Enter your password.';

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    setApiError(null);
    if (emailError || passwordError) return;

    try {
      setLoading(true);
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setApiError(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell step="account">
      <div className="auth-form-heading">
        <div className="auth-form-overline">01 / ACCOUNT</div>
        <h2>Welcome<br /><em>back.</em></h2>
        <p>Sign in to access your Agentica wallet, KYC, and agent workflows.</p>
      </div>

      {apiError && (
        <div className="p-3 mb-4 rounded-lg bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-xs flex items-center gap-2">
          <AlertCircle size={15} />
          <span>{apiError}</span>
        </div>
      )}

      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <label className="auth-label" htmlFor="login-email">Email address</label>
        <input
          id="login-email"
          className="auth-input"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          aria-invalid={submitted && Boolean(emailError)}
          aria-describedby={submitted && emailError ? 'login-email-error' : undefined}
        />
        {submitted && emailError && <p className="auth-field-error" id="login-email-error">{emailError}</p>}

        <div className="auth-label-row">
          <label className="auth-label" htmlFor="login-password">Password</label>
          <Link to="/forgot-password" className="auth-small-link">Forgot password?</Link>
        </div>
        <div className="auth-password-wrap">
          <input
            id="login-password"
            className="auth-input"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-invalid={submitted && Boolean(passwordError)}
            aria-describedby={submitted && passwordError ? 'login-password-error' : undefined}
          />
          <button
            className="auth-reveal"
            type="button"
            onClick={() => setShowPassword((value) => !value)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
          </button>
        </div>
        {submitted && passwordError && <p className="auth-field-error" id="login-password-error">{passwordError}</p>}

        <button className="auth-primary" type="submit" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign In'} <ArrowRight size={17} />
        </button>
      </form>
      <p className="auth-switch">
        New to Agentica? <Link to="/signup">Create an account <ArrowRight size={14} /></Link>
      </p>
    </AuthShell>
  );
}

export function SignupPage() {
  const { signup } = useAuth();
  const [email, setEmail] = useState('');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [successInfo, setSuccessInfo] = useState<{ token?: string } | null>(null);

  const emailError = !email.trim() ? 'Enter your email address.' : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? 'Enter a valid email address.' : '';
  const passwordError = password.length < 8 ? 'Password must be at least 8 characters.' : '';
  const confirmError = password !== confirmPassword ? 'Passwords do not match.' : '';

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    setApiError(null);
    if (emailError || passwordError || confirmError) return;

    try {
      setLoading(true);
      const res = await signup(email, password);
      setSuccessInfo({ token: res.verification_token });
    } catch (err: any) {
      setApiError(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell step="account">
      <div className="auth-form-heading">
        <div className="auth-form-overline">01 / SIGN UP</div>
        <h2>Create an<br /><em>account.</em></h2>
        <p>Register to manage wallets, verify identity, and access the agent marketplace.</p>
      </div>

      {apiError && (
        <div className="p-3 mb-4 rounded-lg bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-xs flex items-center gap-2">
          <AlertCircle size={15} />
          <span>{apiError}</span>
        </div>
      )}

      {successInfo ? (
        <div className="p-4 rounded-xl bg-[#38865B]/10 border border-[#38865B]/30 space-y-3 text-xs">
          <div className="flex items-center gap-2 text-[#38865B] font-bold">
            <Check size={16} />
            <span>Account created successfully!</span>
          </div>
          <p className="text-[#241B19]">
            A verification token has been generated. In this development environment, you can verify directly:
          </p>
          {successInfo.token && (
            <div className="p-2 font-mono bg-white rounded border border-[#CFC7BB] break-all select-all text-[11px]">
              {successInfo.token}
            </div>
          )}
          <div className="pt-2 flex gap-2">
            {successInfo.token ? (
              <Link
                to={`/verify-email?token=${encodeURIComponent(successInfo.token)}`}
                className="auth-primary py-2 text-center text-xs block"
              >
                Verify Email Now <ArrowRight size={14} className="inline ml-1" />
              </Link>
            ) : (
              <Link to="/login" className="auth-primary py-2 text-center text-xs block">
                Go to Sign In
              </Link>
            )}
          </div>
        </div>
      ) : (
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label className="auth-label" htmlFor="signup-email">Email address</label>
          <input
            id="signup-email"
            className="auth-input"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          {submitted && emailError && <p className="auth-field-error">{emailError}</p>}

          <label className="auth-label" htmlFor="signup-password">Password</label>
          <div className="auth-password-wrap">
            <input
              id="signup-password"
              className="auth-input"
              type={showPassword ? 'text' : 'password'}
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <button
              className="auth-reveal"
              type="button"
              onClick={() => setShowPassword((v) => !v)}
            >
              {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </div>
          {submitted && passwordError && <p className="auth-field-error">{passwordError}</p>}

          <label className="auth-label" htmlFor="confirm-password">Confirm password</label>
          <input
            id="confirm-password"
            className="auth-input"
            type={showPassword ? 'text' : 'password'}
            placeholder="Re-enter password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
          {submitted && confirmError && <p className="auth-field-error">{confirmError}</p>}

          <button className="auth-primary" type="submit" disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account'} <ArrowRight size={17} />
          </button>
        </form>
      )}

      <p className="auth-switch">
        Already have an account? <Link to="/login">Sign in <ArrowRight size={14} /></Link>
      </p>
    </AuthShell>
  );
}

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const { verifyEmail } = useAuth();
  const [tokenInput, setTokenInput] = useState(searchParams.get('token') || '');

  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    try {
      setLoading(true);
      setStatusMsg(null);
      await verifyEmail(tokenInput.trim());
      setStatusMsg({ type: 'success', text: 'Email successfully verified! You may now sign in or continue.' });
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Verification token invalid or expired.' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell step="profile">
      <div className="auth-form-heading">
        <div className="auth-form-overline">02 / VERIFY EMAIL</div>
        <h2>Verify your<br /><em>email address.</em></h2>
        <p>Confirm account ownership to access verified agent execution.</p>
      </div>

      {statusMsg && (
        <div
          className={`p-3 mb-4 rounded-lg text-xs flex items-center gap-2 ${
            statusMsg.type === 'success'
              ? 'bg-[#38865B]/10 border border-[#38865B]/30 text-[#38865B]'
              : 'bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040]'
          }`}
        >
          {statusMsg.type === 'success' ? <Check size={16} /> : <AlertCircle size={16} />}
          <span>{statusMsg.text}</span>
        </div>
      )}

      <form className="auth-form" onSubmit={handleVerify}>
        <label className="auth-label" htmlFor="verification-token">Verification Token</label>
        <input
          id="verification-token"
          className="auth-input font-mono text-xs"
          placeholder="Paste verification token"
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
        />

        <button className="auth-primary" type="submit" disabled={loading || !tokenInput.trim()}>
          {loading ? 'Verifying...' : 'Verify Email'} <ArrowRight size={17} />
        </button>
      </form>

      <p className="auth-switch">
        Ready to access the app? <Link to="/login">Sign in <ArrowRight size={14} /></Link>
      </p>
    </AuthShell>
  );
}

export function ForgotPasswordPage() {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    try {
      setLoading(true);
      const res = await forgotPassword(email.trim());
      setMessage('Password recovery initiated.');
      if (res.reset_token) {
        setResetToken(res.reset_token);
      }
    } catch (err: any) {
      setMessage('If this email is registered, recovery instructions have been prepared.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell step="account">
      <div className="auth-form-heading">
        <div className="auth-form-overline">01 / RECOVERY</div>
        <h2>Reset your<br /><em>password.</em></h2>
        <p>Enter your account email to receive a secure recovery token.</p>
      </div>

      {message && (
        <div className="p-3 mb-4 rounded-lg bg-[#38865B]/10 border border-[#38865B]/30 text-[#38865B] text-xs">
          {message}
        </div>
      )}

      {resetToken ? (
        <div className="p-4 rounded-xl bg-white border border-[#CFC7BB] space-y-3 text-xs">
          <p className="font-semibold text-[#241B19]">Recovery token (Local Dev):</p>
          <div className="p-2 font-mono bg-[#F7F4EE] rounded border border-[#CFC7BB] text-[11px] break-all select-all">
            {resetToken}
          </div>
          <Link
            to={`/reset-password?token=${encodeURIComponent(resetToken)}`}
            className="auth-primary py-2 text-center text-xs block"
          >
            Continue to Set New Password <ArrowRight size={14} className="inline ml-1" />
          </Link>
        </div>
      ) : (
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-label" htmlFor="forgot-email">Email address</label>
          <input
            id="forgot-email"
            className="auth-input"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <button className="auth-primary" type="submit" disabled={loading || !email.trim()}>
            {loading ? 'Submitting...' : 'Send Recovery Token'} <ArrowRight size={17} />
          </button>
        </form>
      )}

      <p className="auth-switch">
        Remembered your password? <Link to="/login">Sign in <ArrowRight size={14} /></Link>
      </p>
    </AuthShell>
  );
}

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { resetPassword } = useAuth();
  const [token, setToken] = useState(searchParams.get('token') || '');
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    if (!token.trim() || newPassword.length < 8) return;
    try {
      setLoading(true);
      setError(null);
      await resetPassword(token.trim(), newPassword);
      navigate('/login');
    } catch (err: any) {
      setError(err.message || 'Password reset failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell step="account">
      <div className="auth-form-heading">
        <div className="auth-form-overline">01 / PASSWORD RESET</div>
        <h2>Set a new<br /><em>password.</em></h2>
        <p>Enter the reset token and choose a secure replacement password.</p>
      </div>

      {error && (
        <div className="p-3 mb-4 rounded-lg bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-xs flex items-center gap-2">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      <form className="auth-form" onSubmit={handleReset}>
        <label className="auth-label" htmlFor="reset-token">Reset Token</label>
        <input
          id="reset-token"
          className="auth-input font-mono text-xs"
          placeholder="Paste reset token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />

        <label className="auth-label" htmlFor="new-password">New Password</label>
        <input
          id="new-password"
          className="auth-input"
          type="password"
          placeholder="Minimum 8 characters"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />

        <button className="auth-primary" type="submit" disabled={loading || !token.trim() || newPassword.length < 8}>
          {loading ? 'Updating...' : 'Update Password'} <ArrowRight size={17} />
        </button>
      </form>

      <p className="auth-switch">
        Back to <Link to="/login">Sign in <ArrowRight size={14} /></Link>
      </p>
    </AuthShell>
  );
}
