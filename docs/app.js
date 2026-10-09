'use strict';
const scenarios = {
  code: { command: 'ask -f app.py:40-90 "explain this function and flag edge cases"', description: 'Only lines 40–90 of app.py are attached to your question. Get a focused explanation without sending the whole file.', tags: ['Line ranges', 'Repeatable -f', 'Your model'], note: 'Replace app.py with a file in your project. Attached content is sent to your configured model provider.' },
  pipe: { command: 'cat error.log | ask "what caused this error and how can I fix it?"', description: 'Piped input becomes context for your question. Trace a failure, explain a stack trace, or summarize noisy output without copying it into another app.', tags: ['Standard input', 'Logs & stack traces', 'Focused context'], note: 'On PowerShell, use Get-Content error.log | ask "what caused this error?". Check logs for secrets before sending them.' },
  web: { command: 'ask --search-provider brave -w "What changed in the latest Python release? Cite sources."', description: 'Search first, then ask your model to use the retrieved sources. The answer includes numbered references and URLs you can open yourself.', tags: ['Search first', 'Numbered sources', 'One model call'], note: 'Requires a model key and BRAVE_API_KEY. Choose Brave or Tavily in the setup guide below.' },
  write: { command: 'git diff | ask --no-history --format md "review this diff for bugs" > review.md', description: 'Turn a diff into a review you can keep. The answer goes to review.md; progress and diagnostics stay in your terminal.', tags: ['Clean Markdown', 'No saved session', 'Works with pipes'], note: 'The model receives your diff. --no-history skips local conversation storage; it does not make a remote model local.' }
};
const providers = {
  brave: { name: 'Brave Search', env: 'BRAVE_API_KEY', placeholder: 'YOUR_BRAVE_KEY', link: 'https://api-dashboard.search.brave.com', description: 'Create a Brave Search API account, choose a plan, and create a key in ', linkLabel: 'your API dashboard ↗', note: 'A Brave browser installation does not provide an API key. Check the provider’s current pricing and request limits.' },
  tavily: { name: 'Tavily', env: 'TAVILY_API_KEY', placeholder: 'YOUR_TAVILY_KEY', link: 'https://app.tavily.com', description: 'Create a Tavily account and copy an API key from ', linkLabel: 'your Tavily dashboard ↗', note: 'Use a Tavily API key (typically starting with tvly-). Check your dashboard for current credits and limits.' },
  serper: { name: 'Serper', env: 'SERPER_API_KEY', placeholder: 'YOUR_SERPER_KEY', link: 'https://serper.dev', description: 'Create a Serper account and copy your API key from ', linkLabel: 'the Serper dashboard ↗', note: 'Your Serper search key is separate from your AI model key. Check your dashboard for current credits and limits.' },
  duckduckgo: { name: 'DuckDuckGo', env: '', description: 'No search account or API key required. Select DuckDuckGo and try a search.', note: 'The keyless HTML endpoint can rate-limit or return no results. Choose a keyed provider if this happens regularly.' }
};
let selectedShell = 'unix';
let selectedProvider = 'brave';
function markSelected(selector, selected, attr) {
  document.querySelectorAll(selector).forEach(button => {
    const isSelected = button.dataset[attr] === selected;
    button.classList.toggle(selector === '.scenario' ? 'active' : 'selected', isSelected);
    button.setAttribute('aria-pressed', String(isSelected));
  });
}
function renderSetup() {
  const p = providers[selectedProvider];
  const windows = selectedShell === 'windows';
  const envCommand = (name, value) => windows ? `$env:${name}="${value}"` : `export ${name}="${value}"`;
  document.getElementById('shell-note').textContent = windows ? 'Commands for Windows PowerShell.' : 'Commands for bash and zsh.';
  document.getElementById('model-command').textContent = envCommand('GROQ_API_KEY', 'YOUR_GROQ_KEY');
  document.getElementById('search-heading').textContent = `Give ask access to ${p.name}`;
  const description = document.getElementById('provider-description');
  description.textContent = p.description;
  if (p.link) {
    const link = document.createElement('a');
    link.href = p.link; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = p.linkLabel;
    description.append(link, '.');
  }
  document.getElementById('search-command').textContent = (p.env ? envCommand(p.env, p.placeholder) + '\n' : '') + `ask --setup-search ${selectedProvider}`;
  document.getElementById('key-note').textContent = p.note;
  document.getElementById('manual-config').textContent = JSON.stringify({search_provider: selectedProvider, search_api_key: '', search_api_key_env: p.env || 'SEARCH_API_KEY', web_fallback: true}, null, 2);
  document.getElementById('persist-note').textContent = windows
    ? 'For future terminals, add each key in Windows Settings → System → About → Advanced system settings → Environment Variables → User variables. Use the same variable names shown above, then reopen PowerShell. Do not commit keys to your project.'
    : 'Add the export lines to ~/.zshrc (zsh) or ~/.bashrc (bash), then open a new terminal. Treat that file as private: it contains your keys. Never commit keys to your project.';
  document.getElementById('success-description').textContent = `Doctor reports a live search result count from ${selectedProvider}. Your answer includes numbered source URLs.`;
}
document.querySelectorAll('[data-shell]').forEach(button => button.addEventListener('click', () => {
  selectedShell = button.dataset.shell; markSelected('[data-shell]', selectedShell, 'shell'); renderSetup();
}));
document.querySelectorAll('[data-provider]').forEach(button => button.addEventListener('click', () => {
  selectedProvider = button.dataset.provider; markSelected('[data-provider]', selectedProvider, 'provider'); renderSetup();
}));
document.querySelectorAll('.scenario').forEach(button => button.addEventListener('click', () => {
  const entry = scenarios[button.dataset.scenario];
  markSelected('.scenario', button.dataset.scenario, 'scenario');
  document.getElementById('example-command').textContent = entry.command;
  document.getElementById('copy-example').dataset.copy = entry.command;
  document.getElementById('example-description').textContent = entry.description;
  document.getElementById('example-footnote').textContent = entry.note;
  const tags = document.getElementById('example-tags'); tags.replaceChildren();
  entry.tags.forEach(text => { const tag = document.createElement('span'); tag.textContent = text; tags.append(tag); });
}));
let toastTimer;
function notifyCopy(message) {
  const toast = document.getElementById('toast');
  clearTimeout(toastTimer); toast.textContent = message; toast.classList.add('visible');
  toastTimer = setTimeout(() => toast.classList.remove('visible'), 3000);
}
async function copyCommand(button) {
  const text = button.dataset.copyTarget ? document.getElementById(button.dataset.copyTarget).textContent : button.dataset.copy;
  try {
    if (!navigator.clipboard || !window.isSecureContext) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(text);
    notifyCopy('Command copied. Replace any key placeholders before running.');
  } catch (_) {
    const field = document.createElement('textarea');
    field.value = text; field.setAttribute('readonly', '');
    field.style.cssText = 'position:fixed;top:0;left:0;opacity:0'; document.body.append(field); field.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch (_) { /* show manual selection below */ }
    field.remove(); button.focus();
    if (copied) notifyCopy('Command copied. Replace any key placeholders before running.');
    else {
      const code = button.dataset.copyTarget ? document.getElementById(button.dataset.copyTarget) : button.parentElement.querySelector('code');
      if (code) { const range = document.createRange(); range.selectNodeContents(code); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); }
      notifyCopy('Clipboard unavailable. Select the command and press Ctrl+C or ⌘C.');
    }
  }
}
document.querySelectorAll('[data-copy], [data-copy-target]').forEach(button => button.addEventListener('click', () => copyCommand(button)));
renderSetup();

// Keep Vercel analytics on the hosted site, without broken script requests in local previews.
if (location.hostname === 'ask.aolbeam.com' || location.hostname.endsWith('.vercel.app')) {
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  window.si = window.si || function () { (window.siq = window.siq || []).push(arguments); };
  ['/_vercel/insights/script.js', '/_vercel/speed-insights/script.js'].forEach(src => {
    const script = document.createElement('script'); script.src = src; script.defer = true; document.head.append(script);
  });
}
