export default function Hero() {
  return (
    <section className="hero">
      <div className="hero-subtitle">
        <svg className="icon small-beaker" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4.5 3h15"/><path d="M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3"/><path d="M6 14h12"/>
        </svg>
        <span>EVIDENCE-BASED SKINCARE</span>
      </div>
      <h1 className="hero-title">skinology<span className="dot">.</span></h1>
      <p className="hero-description">
        Every product. Every ingredient. Every claim — verified against peer-reviewed research. Build a routine grounded in science, not marketing.
      </p>
    </section>
  );
}
