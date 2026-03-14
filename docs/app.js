/* ═══════════════════════════════════════════
   app.js — Tab switching, nav behavior
   ═══════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    // ── Main tab switching ──
    const navTabs = document.querySelectorAll('.nav-tabs li');
    const tabPanels = document.querySelectorAll('.tab-panel');

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;

            navTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            tabPanels.forEach(panel => {
                panel.classList.toggle('active', panel.id === `tab-${target}`);
            });

            // Update URL hash
            history.replaceState(null, null, `#${target}`);

            // Scroll to content
            document.querySelector('.content').scrollIntoView({ behavior: 'smooth' });
        });
    });

    // ── Handle initial hash ──
    const hash = window.location.hash.replace('#', '');
    if (hash) {
        const targetTab = document.querySelector(`.nav-tabs li[data-tab="${hash}"]`);
        if (targetTab) targetTab.click();
    }

    // ── ML demo sub-tabs ──
    const mlTabs = document.querySelectorAll('.ml-tab');
    const mlPanels = document.querySelectorAll('.ml-panel');

    mlTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.ml;

            mlTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            mlPanels.forEach(panel => {
                panel.classList.toggle('active', panel.id === `ml-${target}`);
            });
        });
    });

});
