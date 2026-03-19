/* app.js v5 */
document.addEventListener('DOMContentLoaded', () => {
    // Theme
    const themeBtn = document.getElementById('themeBtn');
    const iconMoon = document.getElementById('icon-moon');
    const iconSun = document.getElementById('icon-sun');
    function applyTheme(t) {
        if (t === 'light') { document.documentElement.setAttribute('data-theme','light'); iconMoon.style.display='none'; iconSun.style.display='block'; }
        else { document.documentElement.removeAttribute('data-theme'); iconMoon.style.display='block'; iconSun.style.display='none'; }
    }
    applyTheme(localStorage.getItem('theme') === 'light' ? 'light' : 'dark');
    themeBtn?.addEventListener('click', () => {
        const next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', next); applyTheme(next);
        if (window.replotCharts) window.replotCharts();
    });

    // Tabs
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
            setTimeout(() => { document.querySelectorAll('.tab-panel.active .reveal:not(.visible)').forEach(el => revealObserver.observe(el)); initScrollHints(); }, 150);
        });
    });
    const hash = window.location.hash.replace('#','');
    if (hash) { const t = document.querySelector(`.nav-tabs li[data-tab="${hash}"]`); if (t) t.click(); }

    // ML sub tabs
    document.querySelectorAll('.ml-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.ml-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.ml-panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('ml-' + tab.dataset.ml).classList.add('active');
        });
    });

    // Scroll reveal
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('visible'); revealObserver.unobserve(entry.target); } });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

    // Scroll hint arrows
    function initScrollHints() {
        document.querySelectorAll('.scroll-hint').forEach(el => {
            function checkEnd() {
                if (el.scrollLeft + el.clientWidth >= el.scrollWidth - 10) el.classList.add('scrolled-end');
                else el.classList.remove('scrolled-end');
            }
            el.removeEventListener('scroll', checkEnd);
            el.addEventListener('scroll', checkEnd);
            checkEnd();
        });
    }
    initScrollHints();

    // CodeSignal streak live fetch
    fetch('https://amjadkudsi.github.io/StatSync-Controller/stats.json')
        .then(r => r.json())
        .then(data => {
            if (data.streak) {
                const el = document.getElementById('codesignal-streak-count');
                if (el) el.textContent = data.streak;
            }
        })
        .catch(() => {}); // keep fallback value
});
