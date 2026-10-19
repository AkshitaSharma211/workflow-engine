(function () {
  const links = [['/dashboard', 'Dashboard'], ['/search', 'Search'],
                 ['/my-jobs', 'My Jobs'], ['/activity', 'Activity']];
  const here = location.pathname;
  const bar = document.createElement('div');
  bar.className = 'bg-white border-b';
  bar.innerHTML = `
    <div class="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between text-sm">
      <a href="/" class="font-bold">Workflow Engine</a>
      <nav class="flex items-center gap-4">
        ${links.map(([h, l]) =>
          `<a href="${h}" class="${here === h ? 'font-semibold underline' : 'text-slate-500'}">${l}</a>`).join('')}
        <span id="nav-who" class="text-slate-400"></span>
        <button id="nav-out" class="underline">Log out</button>
      </nav>
    </div>`;
  document.body.prepend(bar);
  fetch('/me').then(r => r.json()).then(d => {
    document.getElementById('nav-who').textContent = d.email || '';
  });
  document.getElementById('nav-out').addEventListener('click', async () => {
    await fetch('/logout', {method: 'POST'});
    window.location = '/login';
  });
})();