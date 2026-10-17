import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, Eye, EyeOff, Fingerprint, LockKeyhole, ShieldCheck } from 'lucide-react';
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
            {steps.map((item) => <span key={item.id} className={item.id === step || steps.findIndex((s) => s.id === item.id) < steps.findIndex((s) => s.id === step) ? 'active' : ''} />)}
          </div>
          {children}
          <div className="auth-form-foot"><ShieldCheck size={15} /><span>Demo onboarding · Your details stay in this browser session only</span></div>
        </section>
      </div>
      <footer className="auth-page-footer"><span>Agentica · Pay-per-call agent economy</span><span>BASE SEPOLIA <i /> x402 V2</span></footer>
    </main>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const emailError = !email.trim() ? 'Enter your email address.' : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? 'Enter a valid email address.' : '';
  const passwordError = password ? '' : 'Enter your password.';

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    if (!emailError && !passwordError) navigate('/kyc');
  }

  return (
    <AuthShell step="account">
      <div className="auth-form-heading">
        <div className="auth-form-overline">01 / ACCOUNT</div>
        <h2>Welcome<br /><em>back.</em></h2>
        <p>Sign in to continue to the Agentica marketplace.</p>
      </div>
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <label className="auth-label" htmlFor="login-email">Email address</label>
        <input id="login-email" className="auth-input" type="email" autoComplete="email" placeholder="you@company.com" value={email} onChange={(event) => setEmail(event.target.value)} aria-invalid={submitted && Boolean(emailError)} aria-describedby={submitted && emailError ? 'login-email-error' : undefined} />
        {submitted && emailError && <p className="auth-field-error" id="login-email-error">{emailError}</p>}

        <div className="auth-label-row"><label className="auth-label" htmlFor="login-password">Password</label><a href="#password" onClick={(event) => event.preventDefault()} className="auth-small-link">Forgot password?</a></div>
        <div className="auth-password-wrap">
          <input id="login-password" className="auth-input" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" value={password} onChange={(event) => setPassword(event.target.value)} aria-invalid={submitted && Boolean(passwordError)} aria-describedby={submitted && passwordError ? 'login-password-error' : undefined} />
          <button className="auth-reveal" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button>
        </div>
        {submitted && passwordError && <p className="auth-field-error" id="login-password-error">{passwordError}</p>}

        <div className="auth-demo-note"><LockKeyhole size={16} /><p><strong>Demo sign-in</strong><span>This form does not verify credentials. Any valid email and non-empty password will continue.</span></p></div>
        <button className="auth-primary" type="submit">Continue <ArrowRight size={17} /></button>
      </form>
      <p className="auth-switch">New to Agentica? <Link to="/kyc">Set up your account <ArrowRight size={14} /></Link></p>
    </AuthShell>
  );
}

export function KycPage() {
  const navigate = useNavigate();
  const [legalName, setLegalName] = useState('');
  const [country, setCountry] = useState('');
  const [accountType, setAccountType] = useState('individual');
  const [intendedUse, setIntendedUse] = useState('');
  const [consent, setConsent] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const errors = {
    legalName: legalName.trim() ? '' : 'Enter your legal name.',
    country: country ? '' : 'Select your country or region.',
    intendedUse: intendedUse.trim() ? '' : 'Tell us how you plan to use the marketplace.',
    consent: consent ? '' : 'Please confirm your consent to continue.',
  };

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    if (!Object.values(errors).some(Boolean)) navigate('/dashboard');
  }

  return (
    <AuthShell step="profile">
      <div className="auth-form-heading auth-form-heading-compact">
        <div className="auth-form-overline">02 / PROFILE</div>
        <h2>A little about<br /><em>you.</em></h2>
        <p>Help us tailor your marketplace experience. No documents or identity numbers needed.</p>
      </div>
      <form className="auth-form auth-kyc-form" onSubmit={handleSubmit} noValidate>
        <div className="auth-two-col">
          <div className="auth-field">
            <label className="auth-label" htmlFor="legal-name">Legal name</label>
            <input id="legal-name" className="auth-input" autoComplete="name" placeholder="Your full name" value={legalName} onChange={(event) => setLegalName(event.target.value)} aria-invalid={submitted && Boolean(errors.legalName)} aria-describedby={submitted && errors.legalName ? 'legal-name-error' : undefined} />
            {submitted && errors.legalName && <p className="auth-field-error" id="legal-name-error">{errors.legalName}</p>}
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="country">Country or region</label>
            <select id="country" className="auth-input auth-select" value={country} onChange={(event) => setCountry(event.target.value)} aria-invalid={submitted && Boolean(errors.country)} aria-describedby={submitted && errors.country ? 'country-error' : undefined}>
              <option value="">Select region</option><option>India</option><option>United States</option><option>United Kingdom</option><option>Canada</option><option>Singapore</option><option>Australia</option><option>Other</option>
            </select>
            {submitted && errors.country && <p className="auth-field-error" id="country-error">{errors.country}</p>}
          </div>
        </div>

        <fieldset className="auth-account-fieldset">
          <legend className="auth-label">Account type</legend>
          <div className="auth-choice-row">
            <label className={`auth-choice ${accountType === 'individual' ? 'selected' : ''}`}><input type="radio" name="account-type" value="individual" checked={accountType === 'individual'} onChange={(event) => setAccountType(event.target.value)} /><span className="auth-choice-mark" /><span><strong>Individual</strong><small>Personal workspace</small></span></label>
            <label className={`auth-choice ${accountType === 'business' ? 'selected' : ''}`}><input type="radio" name="account-type" value="business" checked={accountType === 'business'} onChange={(event) => setAccountType(event.target.value)} /><span className="auth-choice-mark" /><span><strong>Business</strong><small>Team or organization</small></span></label>
          </div>
        </fieldset>

        <div className="auth-field">
          <label className="auth-label" htmlFor="intended-use">How do you plan to use Agentica?</label>
          <textarea id="intended-use" className="auth-input auth-textarea" placeholder="For example, I’m exploring verified agents for market research…" maxLength={320} value={intendedUse} onChange={(event) => setIntendedUse(event.target.value)} aria-invalid={submitted && Boolean(errors.intendedUse)} aria-describedby={submitted && errors.intendedUse ? 'intended-use-error' : undefined} />
          {submitted && errors.intendedUse && <p className="auth-field-error" id="intended-use-error">{errors.intendedUse}</p>}
        </div>

        <div className="auth-consent-wrap">
          <label className="auth-consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} aria-invalid={submitted && Boolean(errors.consent)} aria-describedby={submitted && errors.consent ? 'consent-error' : undefined} /><span className="auth-checkbox" aria-hidden="true"><Check size={12} /></span><span>I agree to use this demo marketplace responsibly and understand that this form does not perform identity verification.</span></label>
          {submitted && errors.consent && <p className="auth-field-error" id="consent-error">{errors.consent}</p>}
        </div>

        <div className="auth-privacy-note"><ShieldCheck size={16} /><span>Demo only. Your information is not sent to a server or saved after you leave this page.</span></div>
        <button className="auth-primary" type="submit">Continue to marketplace <ArrowRight size={17} /></button>
      </form>
      <p className="auth-switch"><Link to="/login"><ArrowLeft size={14} /> Back to login</Link><span>Already have an account?</span></p>
    </AuthShell>
  );
}
