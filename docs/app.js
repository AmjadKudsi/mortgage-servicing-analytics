/* app.js v4 — Dark default, sun/moon toggle */
document.addEventListener('DOMContentLoaded', () => {
    // ── Theme: dark is default. Only 'light' is stored. ──
    const themeBtn = document.getElementById('themeBtn');
    const iconMoon = document.getElementById('icon-moon');
    const iconSun = document.getElementById('icon-sun');

    function applyTheme(theme) {
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
            iconMoon.style.display = 'none';
            iconSun.style.display = 'block';
        } else {
            document.documentElement.removeAttribute('data-theme');
            iconMoon.style.display = 'block';
            iconSun.style.display = 'none';
        }
    }

    const saved = localStorage.getItem('theme');
    applyTheme(saved === 'light' ? 'light' : 'dark');

    themeBtn?.addEventListener('click', () => {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        const next = isLight ? 'dark' : 'light';
        localStorage.setItem('theme', next);
        applyTheme(next);
        if (window.replotCharts) window.replotCharts();
    });

    // ── Tabs ──
    const navTabs = document.querySelectorAll('.nav-tabs li');
    const tabPanels = document.querySelectorAll('.tab-panel');
    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;
            navTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            tabPanels.forEach(p => p.classList.toggle('active', p.id === `tab-${target}`));
            history.replaceState(null, null, `#${target}`);
            document.querySelector('.content').scrollIntoView({ behavior: 'smooth' });
            setTimeout(() => {
                document.querySelectorAll('.tab-panel.active .reveal:not(.visible)').forEach(el => revealObserver.observe(el));
            }, 100);
        });
    });
    const hash = window.location.hash.replace('#', '');
    if (hash) { const t = document.querySelector(`.nav-tabs li[data-tab="${hash}"]`); if (t) t.click(); }

    // ── ML sub-tabs ──
    document.querySelectorAll('.ml-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.ml-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.ml-panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('ml-' + tab.dataset.ml).classList.add('active');
        });
    });

    // ── Scroll reveal ──
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('visible'); revealObserver.unobserve(entry.target); } });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));
});
