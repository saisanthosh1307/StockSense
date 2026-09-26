import { useState, type FormEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  Eye,
  EyeOff,
  Info,
  KeyRound,
  LockKeyhole,
  Mail,
  PackageCheck,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import "./AuthPage.css";

export type AuthenticatedUser = {
  name: string;
  email: string;
  role: "Inventory Manager" | "Warehouse Staff";
};

type AuthStep = "login" | "register" | "forgot" | "otp" | "reset";
type OtpPurpose = "login" | "register" | "reset";

export default function AuthPage({
  onAuthenticated,
}: {
  onAuthenticated: (user: AuthenticatedUser) => void;
}) {
  const [step, setStep] = useState<AuthStep>("login");
  const [otpPurpose, setOtpPurpose] = useState<OtpPurpose>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] =
    useState<AuthenticatedUser["role"]>("Inventory Manager");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");

  const requestOtp = (
    event: FormEvent<HTMLFormElement>,
    purpose: OtpPurpose,
  ) => {
    event.preventDefault();
    setOtpPurpose(purpose);
    setOtp("");
    setError("");
    setFeedback("Enter any six-digit code to continue in this local preview.");
    setStep("otp");
  };

  const verifyOtp = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!/^\d{6}$/.test(otp)) {
      setError("Enter all six digits to continue.");
      return;
    }
    setError("");
    if (otpPurpose === "reset") {
      setFeedback("");
      setStep("reset");
      return;
    }
    const displayName =
      name.trim() || email.split("@")[0].replace(/[._-]/g, " ");
    onAuthenticated({ name: displayName, email, role });
  };

  const resetPassword = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (password.length < 8) {
      setError("Use at least 8 characters for your new password.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Those passwords do not match.");
      return;
    }
    setPassword("");
    setConfirmPassword("");
    setFeedback("Password reset complete in this local preview. Sign in to continue.");
    setStep("login");
  };

  const changeStep = (nextStep: AuthStep) => {
    setError("");
    setFeedback("");
    setPassword("");
    setConfirmPassword("");
    setStep(nextStep);
  };

  const heading = {
    login: ["Welcome back", "Sign in to your StockSense workspace."],
    register: ["Create your account", "Set up your access to StockSense."],
    forgot: ["Reset your password", "We’ll verify your email before you reset it."],
    otp: [
      otpPurpose === "reset" ? "Verify your email" : "Check your inbox",
      `Enter the 6-digit code for ${email}.`,
    ],
    reset: ["Choose a new password", "Make it at least 8 characters long."],
  }[step];

  return (
    <main className="auth-screen">
      <section className="auth-visual" aria-label="StockSense warehouse operations">
        <a className="auth-brand" href="#home" onClick={(event) => event.preventDefault()}>
          <span className="auth-brand-mark"><PackageCheck size={21} /></span>
          <span>stock<span>sense</span></span>
        </a>
        <div className="auth-visual-copy">
          <div className="auth-overline"><span /> INVENTORY, IN SYNC</div>
          <h1>Know what’s<br />where. Move<br />with confidence.</h1>
          <p>One clear view of every item, location, and movement across your operation.</p>
        </div>
        <div className="auth-visual-footer">
          <span className="auth-secure-mark"><ShieldCheck size={17} /></span>
          <span><strong>Built for accountable operations</strong><small>From receiving dock to dispatch</small></span>
          <span className="auth-visual-index">01 <i /> 03</span>
        </div>
        <span className="auth-photo-credit">WAREHOUSE OPERATIONS / STOCKSENSE</span>
      </section>

      <section className="auth-main">
        <div className="auth-topline"><span><ShieldCheck size={15} /> SECURE WORKSPACE</span><span>Need help? <a href="mailto:support@stocksense.local">Contact support</a></span></div>
        <div className="auth-content">
          <div className="auth-mobile-brand"><span className="auth-brand-mark"><PackageCheck size={20} /></span><span>stock<span>sense</span></span></div>
          {step === "login" && <div className="auth-switch" role="tablist" aria-label="Account access"><button className="active" type="button" role="tab" aria-selected="true">Log in</button><button type="button" role="tab" aria-selected="false" onClick={() => changeStep("register")}>Create account</button></div>}
          {step !== "login" && <button className="auth-back" type="button" onClick={() => changeStep(step === "reset" ? "forgot" : "login")}><ArrowLeft size={15} /> {step === "otp" ? "Back to sign in" : "Back"}</button>}

          <div className="auth-heading"><span className="auth-step-mark">{step === "otp" ? <KeyRound size={18} /> : step === "reset" ? <LockKeyhole size={18} /> : <UserRound size={18} />}</span><h2>{heading[0]}</h2><p>{heading[1]}</p></div>

          {step === "login" && <form className="auth-form" onSubmit={(event) => requestOtp(event, "login")}>
            <AuthInput label="Work email" icon={<Mail size={16} />} type="email" autoComplete="email" value={email} onChange={setEmail} placeholder="you@company.com" required />
            <AuthInput label="Password" icon={<LockKeyhole size={16} />} type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={setPassword} placeholder="Enter your password" required trailing={<button className="password-toggle" type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((shown) => !shown)}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button>} />
            <div className="auth-form-options"><label className="remember-option"><input type="checkbox" /> <span>Remember this device</span></label><button type="button" className="auth-inline-link" onClick={() => changeStep("forgot")}>Forgot password?</button></div>
            {feedback && <FeedbackMessage text={feedback} kind="success" />}
            {error && <FeedbackMessage text={error} kind="error" />}
            <button className="auth-submit" type="submit">Continue <ArrowRight size={16} /></button>
            <p className="auth-alternate">New to StockSense? <button type="button" onClick={() => changeStep("register")}>Create an account</button></p>
          </form>}

          {step === "register" && <form className="auth-form" onSubmit={(event) => requestOtp(event, "register")}>
            <AuthInput label="Full name" icon={<UserRound size={16} />} type="text" autoComplete="name" value={name} onChange={setName} placeholder="Your name" required />
            <AuthInput label="Work email" icon={<Mail size={16} />} type="email" autoComplete="email" value={email} onChange={setEmail} placeholder="you@company.com" required />
            <label className="auth-field"><span>Workspace role</span><span className="auth-select-wrap"><ShieldCheck size={16} /><select value={role} onChange={(event) => setRole(event.target.value as AuthenticatedUser["role"])}><option>Inventory Manager</option><option>Warehouse Staff</option></select><ChevronDown size={15} /></span></label>
            <AuthInput label="Password" icon={<LockKeyhole size={16} />} type="password" autoComplete="new-password" value={password} onChange={setPassword} placeholder="At least 8 characters" minLength={8} required />
            {error && <FeedbackMessage text={error} kind="error" />}
            <button className="auth-submit" type="submit">Create account <ArrowRight size={16} /></button>
            <p className="auth-alternate">Already have an account? <button type="button" onClick={() => changeStep("login")}>Log in</button></p>
          </form>}

          {step === "forgot" && <form className="auth-form" onSubmit={(event) => requestOtp(event, "reset")}>
            <AuthInput label="Work email" icon={<Mail size={16} />} type="email" autoComplete="email" value={email} onChange={setEmail} placeholder="you@company.com" required />
            {feedback && <FeedbackMessage text={feedback} kind="success" />}
            <button className="auth-submit" type="submit">Send verification code <ArrowRight size={16} /></button>
          </form>}

          {step === "otp" && <form className="auth-form otp-form" onSubmit={verifyOtp}>
            <label className="auth-field"><span>6-digit verification code</span><span className="otp-input-wrap"><KeyRound size={17} /><input aria-label="6-digit verification code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="000 000" required autoFocus /></span></label>
            <div className="otp-demo-note"><Info size={15} /><span>Local preview only: codes are not sent. Any six digits will work.</span></div>
            {feedback && <FeedbackMessage text={feedback} kind="success" />}
            {error && <FeedbackMessage text={error} kind="error" />}
            <button className="auth-submit" type="submit">Verify and continue <ArrowRight size={16} /></button>
            <p className="auth-alternate">Didn’t get a code? <button type="button" onClick={() => setFeedback("Demo code refreshed. Enter any six digits to continue.")}>Resend code</button></p>
          </form>}

          {step === "reset" && <form className="auth-form" onSubmit={resetPassword}>
            <AuthInput label="New password" icon={<LockKeyhole size={16} />} type="password" autoComplete="new-password" value={password} onChange={setPassword} placeholder="At least 8 characters" minLength={8} required />
            <AuthInput label="Confirm new password" icon={<LockKeyhole size={16} />} type="password" autoComplete="new-password" value={confirmPassword} onChange={setConfirmPassword} placeholder="Enter it once more" required />
            {error && <FeedbackMessage text={error} kind="error" />}
            <button className="auth-submit" type="submit">Reset password <Check size={16} /></button>
          </form>}
          <div className="auth-local-note"><Info size={14} /><span>Authentication is a local preview. Connect an identity provider before production use.</span></div>
        </div>
        <footer className="auth-footer"><span>© 2026 StockSense</span><span><LockKeyhole size={12} /> PRIVATE WORKSPACE</span></footer>
      </section>
    </main>
  );
}

function AuthInput({
  label,
  icon,
  trailing,
  onChange,
  ...inputProps
}: {
  label: string;
  icon: React.ReactNode;
  trailing?: React.ReactNode;
  value: string;
  onChange: (value: string) => void;
  type: string;
  autoComplete: string;
  placeholder: string;
  required?: boolean;
  minLength?: number;
}) {
  return <label className="auth-field"><span>{label}</span><span className="auth-input-wrap">{icon}<input {...inputProps} onChange={(event) => onChange(event.target.value)} />{trailing}</span></label>;
}

function FeedbackMessage({ text, kind }: { text: string; kind: "success" | "error" }) {
  return <div className={`auth-feedback ${kind}`} role={kind === "error" ? "alert" : "status"}>{kind === "error" ? <Info size={15} /> : <Check size={15} />}{text}</div>;
}