(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const img = (id, w = 1100) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${w}&q=80`;

  /* ---------- Nav ---------- */
  const nav = document.getElementById('nav');
  const toggle = document.getElementById('navToggle');
  const menu = document.getElementById('mobileMenu');

  const onScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 12);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  const setMenu = (open) => {
    menu.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    toggle.querySelector('use').setAttribute('href', open ? '#i-close' : '#i-menu');
    nav.classList.toggle('is-scrolled', open || window.scrollY > 12);
  };
  toggle.addEventListener('click', () => setMenu(menu.hidden));
  menu.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false); });
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !menu.hidden) setMenu(false); });

  /* ---------- Reveal on scroll ---------- */
  const reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduceMotion) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add('is-in'));
  }

  /* ---------- Hero: parallax + tilt leves ---------- */
  const heroVisual = document.querySelector('[data-parallax]');
  const heroPhone = document.querySelector('[data-tilt]');
  if (heroVisual && !reduceMotion) {
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = Math.min(window.scrollY, 900);
        heroVisual.style.transform = `translate3d(0, ${y * 0.08}px, 0)`;
        ticking = false;
      });
    }, { passive: true });

    if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
      heroVisual.addEventListener('pointermove', (e) => {
        const r = heroVisual.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        heroPhone.style.transform = `perspective(1200px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg)`;
      });
      heroVisual.addEventListener('pointerleave', () => { heroPhone.style.transform = ''; });
    }
  }

  /* ---------- Demo de identificação ---------- */
  const plants = [
    {
      img: 'photo-1755547721683-9b3d7c084083', alt: 'Vênus papa-moscas',
      tag: 'Planta carnívora', name: 'Dionaea muscipula', common: 'Dionéia · Vênus papa-moscas', conf: 97,
      about: 'Captura pequenos insetos com folhas modificadas que se fecham rapidamente quando estimuladas.',
      family: 'Droseraceae', origin: 'Carolinas, EUA',
      light: 'Sol direto ou meia-sombra', water: 'Substrato sempre úmido, com água sem cloro', level: 'Média',
    },
    {
      img: 'photo-1582893272956-e441d561b20a', alt: 'Folha de costela-de-adão',
      tag: 'Planta tropical', name: 'Monstera deliciosa', common: 'Costela-de-adão', conf: 98,
      about: 'Suas folhas grandes ganham os recortes característicos conforme a planta amadurece.',
      family: 'Araceae', origin: 'México e América Central',
      light: 'Indireta e abundante', water: 'Quando os primeiros centímetros do solo secarem', level: 'Fácil',
    },
    {
      img: 'photo-1686893043633-465fe4383769', alt: 'Zamioculca',
      tag: 'Planta de interior', name: 'Zamioculcas zamiifolia', common: 'Zamioculca · Planta ZZ', conf: 95,
      about: 'Armazena água nos rizomas, o que a torna muito resistente e tolerante à pouca luz.',
      family: 'Araceae', origin: 'Leste da África',
      light: 'Indireta, tolera pouca luz', water: 'Pouca — espere o solo secar por completo', level: 'Fácil',
    },
    {
      img: 'photo-1565626929866-e11c64e607cf', alt: 'Espada-de-são-jorge',
      tag: 'Planta de interior', name: 'Sansevieria trifasciata', common: 'Espada-de-são-jorge', conf: 94,
      about: 'Folhas rígidas e eretas, adaptadas a longos períodos sem água.',
      family: 'Asparagaceae', origin: 'África Ocidental',
      light: 'De meia-sombra a sol indireto', water: 'Pouca — deixe o solo secar entre regas', level: 'Fácil',
    },
  ];

  const demo = document.getElementById('idDemo');
  if (demo) {
    const $ = (id) => document.getElementById(id);
    const stage = demo.querySelector('.id-demo__stage');
    const pickers = demo.querySelectorAll('[data-plant]');
    const tabs = demo.querySelectorAll('[data-tab]');
    const panels = demo.querySelectorAll('[data-panel]');
    let current = 0;
    let timer;

    // pré-carrega as fotos para a troca ser instantânea
    plants.forEach((p) => { const i = new Image(); i.src = img(p.img); });

    const countUp = (el, to) => {
      if (reduceMotion || document.hidden) { el.textContent = `${to}%`; return; }
      const start = performance.now();
      const step = (t) => {
        const k = Math.min((t - start) / 900, 1);
        el.textContent = `${Math.round(to * (1 - Math.pow(1 - k, 3)))}%`;
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };

    const fill = (p) => {
      $('idTag').textContent = p.tag;
      $('idName').textContent = p.name;
      $('idCommon').textContent = p.common;
      $('idAbout').textContent = p.about;
      $('idFamily').textContent = p.family;
      $('idOrigin').textContent = p.origin;
      $('idLight').textContent = p.light;
      $('idWater').textContent = p.water;
      $('idLevel').textContent = p.level;
      $('idConfBar').style.setProperty('--v', `${p.conf}%`);
      countUp($('idConfNum'), p.conf);
    };

    const select = (index) => {
      if (index === current) return;
      current = index;
      const p = plants[index];
      pickers.forEach((b, i) => b.setAttribute('aria-selected', String(i === index)));
      clearTimeout(timer);

      const photo = $('idImg');
      photo.src = img(p.img);
      photo.alt = p.alt;
      stage.dataset.state = 'scanning';
      demo.classList.add('is-busy');
      $('idConfBar').style.setProperty('--v', '0%');

      timer = setTimeout(() => {
        fill(p);
        stage.dataset.state = 'done';
        demo.classList.remove('is-busy');
      }, reduceMotion ? 0 : 1500);
    };

    pickers.forEach((b) => b.addEventListener('click', () => select(Number(b.dataset.plant))));

    tabs.forEach((t) => t.addEventListener('click', () => {
      tabs.forEach((x) => x.setAttribute('aria-selected', String(x === t)));
      panels.forEach((panel) => { panel.hidden = panel.dataset.panel !== t.dataset.tab; });
    }));
  }

  /* ---------- Ano no rodapé ---------- */
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();
