// dock.js — the ONE panel. Every piece of content the map produces (cluster
// context, paper detail, cluster intelligence, reading list, library) lives
// here. One material, one position, animated content swaps. Kills the four
// competing floating-card languages.

let current = null; // { name }

export const dock = {
    show(name, html, { wide = false } = {}) {
        const el = document.getElementById('dock');
        current = { name };
        el.classList.toggle('wide', wide);
        document.body.classList.toggle('dock-wide', wide);
        document.body.classList.add('dock-open');
        // Content is set synchronously — callers wire events immediately after.
        const content = el.querySelector('.dock-content');
        content.innerHTML = html;
        content.scrollTop = 0;
        // Re-trigger the content fade on every swap.
        content.style.animation = 'none';
        void content.offsetWidth;
        content.style.animation = '';
        if (!el.classList.contains('visible')) {
            el.style.display = 'block';
            requestAnimationFrame(() => el.classList.add('visible'));
        }
    },

    update(html) {
        if (!current) return;
        document.getElementById('dock').querySelector('.dock-content').innerHTML = html;
    },

    hide() {
        current = null;
        const el = document.getElementById('dock');
        document.body.classList.remove('dock-open', 'dock-wide');
        el.classList.remove('visible');
        setTimeout(() => { el.style.display = 'none'; }, 350);
    },

    isOpen() { return !!current; },
    current() { return current && current.name; },
};
