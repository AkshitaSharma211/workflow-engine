(function () {
  const links = [['/dashboard', 'Dashboard'], ['/search', 'Search'],
                 ['/my-jobs', 'My Jobs'], ['/activity', 'Activity']];
  const here = location.pathname;
  const active = 'bg-indigo-50 text-indigo-700';
  const idle = 'text-slate-600 transition hover:bg-slate-50 hover:text-slate-900';

  const bar = document.createElement('nav');
  bar.className = 'sticky top-0 z-50 border-b border-slate-200 bg-white';
  bar.setAttribute('aria-label', 'Primary navigation');
  bar.innerHTML = `
    <div class="mx-auto flex max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
      <a href="/dashboard" class="flex shrink-0 items-center gap-2 py-4 text-sm font-semibold text-slate-900">
        <span class="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-white" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 7h6M4 17h6m4-10h6m-6 10h6M10 7l4 10" />
          </svg>
        </span>
        <span>Workflow Engine</span>
      </a>
      <div class="min-w-0 flex-1 overflow-x-auto">
        <div class="flex min-w-max items-center gap-1 py-2">
          ${links.map(([href, label]) => `
            <a href="${href}" ${here === href ? 'aria-current="page"' : ''}
               class="rounded-md px-3 py-2 text-sm font-medium ${here === href ? active : idle}">${label}</a>`).join('')}
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-4">
        <span id="nav-who" class="hidden text-sm text-slate-500 sm:inline"></span>
        <button id="nav-out" type="button"
          class="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-400 hover:bg-slate-50 hover:text-slate-900">Log out</button>
      </div>
    </div>`;
  document.body.prepend(bar);

  fetch('/me').then(r => r.ok ? r.json() : {}).then(d => {
    document.getElementById('nav-who').textContent = d.email || '';
  });
  document.getElementById('nav-out').addEventListener('click', async () => {
    await fetch('/logout', {method: 'POST'});
    window.location = '/login';
  });
})();