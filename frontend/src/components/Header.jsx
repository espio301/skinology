export default function Header() {
  return (
    <header className="header">
      <div className="logo-container">
        <svg className="icon beaker-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4.5 3h15"/><path d="M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3"/><path d="M6 14h12"/>
        </svg>
        <span className="logo-text">skinology<span className="dot">.</span></span>
      </div>
      <div className="header-actions">
        <button className="btn btn-outline">my routine</button>
        <button className="btn btn-user">
          Alex
          <svg className="icon chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      </div>
    </header>
  );
}
