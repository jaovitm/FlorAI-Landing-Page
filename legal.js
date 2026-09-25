(() => {
  const root = document.documentElement;
  const blocks = document.querySelectorAll('[data-lang]');
  const links = document.querySelectorAll('.lang-switch a');
  const titles = { pt: root.dataset.titlePt, en: root.dataset.titleEn };

  const stored = () => { try { return localStorage.getItem('florai-lang'); } catch { return null; } };
  const store = (l) => { try { localStorage.setItem('florai-lang', l); } catch {} };

  const initial = () => {
    const q = new URLSearchParams(location.search).get('lang');
    if (q === 'pt' || q === 'en') return q;
    const target = location.hash && document.getElementById(location.hash.slice(1));
    const owner = target && target.closest('[data-lang]');
    if (owner) return owner.dataset.lang;
    const s = stored();
    if (s === 'pt' || s === 'en') return s;
    return (navigator.language || 'pt').toLowerCase().startsWith('pt') ? 'pt' : 'en';
  };

  const apply = (lang) => {
    blocks.forEach((el) => el.classList.toggle('is-active', el.dataset.lang === lang));
    links.forEach((a) => a.setAttribute('aria-current', String(a.dataset.set === lang)));
    root.lang = lang === 'pt' ? 'pt-BR' : 'en';
    if (titles[lang]) document.title = titles[lang];
  };

  links.forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    const lang = a.dataset.set;
    store(lang);
    apply(lang);
    history.replaceState(null, '', `?lang=${lang}${location.hash}`);
    window.scrollTo({ top: 0 });
  }));

  root.classList.add('js');
  apply(initial());
  // A âncora pode estar num bloco que estava oculto: rola até ela após exibir
  const toHash = () => location.hash && document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'instant' });
  toHash();
  window.addEventListener('load', toHash, { once: true });

  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();
