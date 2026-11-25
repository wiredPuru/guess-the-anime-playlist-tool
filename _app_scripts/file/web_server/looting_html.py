"""Embedded Looting Battle host controls and shared record shop."""

HTML = r"""
<style>
  #loot-dialog {
    --surface: #1a1a1a; --text: #eee; --muted: #aaa; --border: #333;
    --control: #222; --selected: #2a2a2a; --focus: #8894b7;
    position: fixed; inset: 0; margin: auto; width: min(96vw, 980px);
    max-height: 94dvh; padding: clamp(12px, 2.4vw, 24px);
    border: 1px solid var(--border); border-radius: 10px; overflow: auto;
    color: var(--text); background: var(--surface); color-scheme: dark;
  }
  #loot-dialog::backdrop { background: #000b; }
  #loot-dialog [hidden] { display: none !important; }
  #loot-dialog header, #loot-form, #loot-host-actions, #loot-inventory {
    display: flex; align-items: center; justify-content: space-between; gap: .65rem;
  }
  #loot-dialog h2 { font-size: 1.15rem; font-weight: 600; }
  #loot-dialog h3 { font-size: .9rem; font-weight: 600; }
  #loot-dialog button, #loot-dialog input {
    border: 1px solid var(--border); border-radius: 6px; color: inherit;
    background: var(--control); padding: .45rem .65rem; font: inherit; min-height: 44px;
  }
  #loot-dialog button { cursor: pointer; }
  #loot-dialog button:hover:not(:disabled) { border-color: #555; }
  #loot-dialog button:disabled { opacity: .6; cursor: default; }
  #loot-dialog button:focus-visible, #loot-dialog input:focus-visible {
    outline: 2px solid var(--focus); outline-offset: 2px;
  }
  #loot-dialog .loot-primary {
    border-color: #555; background: var(--selected); font-weight: 600;
  }
  #loot-clock {
    margin-left: auto; color: var(--muted); font-variant-numeric: tabular-nums;
  }
  #loot-clock:empty, #loot-status:empty, #loot-progress:empty { display: none; }
  #loot-progress, #loot-status { margin: .65rem 0 0; color: var(--muted); }
  #loot-form { justify-content: flex-start; flex-wrap: wrap; align-items: flex-end; margin-top: 1rem; }
  #loot-form label { display: grid; gap: .25rem; }
  #loot-form input { width: 8rem; }
  #loot-host-actions { justify-content: flex-start; margin-top: .8rem; }
  #loot-bins { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .7rem; margin: .9rem 0 .7rem; }
  #loot-bin-buttons { display: none; }
  .loot-bin {
    min-width: 0; padding: .65rem; border: 1px solid var(--border); border-radius: 6px;
  }
  .loot-bin header { margin-bottom: .55rem; }
  .loot-bin .loot-bin-count { color: var(--muted); font-size: .8rem; }
  .loot-sleeves {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .38rem;
    max-height: clamp(135px, 33dvh, 300px); overflow: auto; padding: 3px;
    scrollbar-color: #555 var(--surface);
  }
  #loot-dialog .loot-sleeve {
    position: relative; display: grid; place-items: center; width: 100%; padding: 0;
  }
  .loot-sleeve::before {
    content: ''; width: 14px; height: 14px; border: 1px solid #777; border-radius: 50%;
  }
  #loot-dialog .loot-sleeve[aria-pressed="true"], #loot-bin-buttons button[aria-pressed="true"] {
    border-color: #777; background: var(--selected);
  }
  .loot-sleeve[data-taken]::before { visibility: hidden; }
  .loot-stamp {
    position: absolute; inset: 0; place-self: center; width: max-content; height: max-content;
    color: var(--muted); font-size: .72rem;
  }
  #loot-preview {
    position: fixed; z-index: 2; max-width: min(280px, calc(100vw - 16px));
    padding: .3rem .5rem; border: 1px solid #555; border-radius: 6px;
    background: var(--surface); color: var(--text); font-size: .85rem;
    overflow-wrap: anywhere; pointer-events: none;
  }
  #loot-inventory {
    position: sticky; bottom: 0; align-items: flex-start; flex-direction: column; gap: .35rem;
    margin-top: .65rem; padding-block: .55rem .2rem; border-top: 1px solid var(--border); background: var(--surface);
  }
  #loot-pick-count, #loot-picks:empty::before { color: var(--muted); font-size: .85rem; }
  #loot-picks { display: flex; gap: .35rem; flex-wrap: wrap; }
  #loot-picks:empty::before { content: 'No records yet'; }
  #loot-dialog #loot-picks button { text-align: left; overflow-wrap: anywhere; min-height: 40px; }
  #loot-picks button span { color: var(--muted); margin-left: .45rem; }
  #loot-credit {
    margin: .35rem auto .7rem; color: #aaa;
    overflow-wrap: anywhere; text-align: center;
  }
  @media (max-width: 680px) {
    #loot-bin-buttons { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .35rem; margin-top: .8rem; }
    #loot-bin-buttons button { padding-inline: .25rem; }
    #loot-bins { grid-template-columns: 1fr; margin-top: .4rem; }
    .loot-bin:not([data-active]) { display: none; }
    .loot-sleeves { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  }
</style>
<dialog id="loot-dialog" aria-labelledby="loot-title">
  <header>
    <h2 id="loot-title" tabindex="-1" autofocus>Looting Battle</h2>
    <span id="loot-clock"></span>
    <button type="button" id="loot-close" hidden>Close</button>
  </header>
  <form id="loot-form" hidden>
    <label>Picks per player <input id="loot-limit" type="number" min="1" step="1" value="2" required></label>
    <label>Time in seconds <input id="loot-seconds" type="number" min="1" step="1" value="60" required></label>
    <button class="loot-primary">Start draft</button>
  </form>
  <p id="loot-progress"></p>
  <div id="loot-host-actions" hidden>
    <button type="button" id="loot-queue" hidden>Queue drafted set</button>
    <button type="button" id="loot-cancel">Cancel draft</button>
  </div>
  <section id="loot-player" aria-label="Shared record shop" hidden>
    <nav id="loot-bin-buttons" aria-label="Record bins"></nav>
    <div id="loot-bins"></div>
    <div id="loot-preview" role="status" hidden></div>
    <footer id="loot-inventory">
      <h3>Inventory <span id="loot-pick-count"></span></h3>
      <div id="loot-picks"></div>
    </footer>
  </section>
  <p id="loot-status" role="status"></p>
</dialog>
<script>
  (() => {
    const get = id => document.getElementById('loot-' + id);
    const dialog = get('dialog');
    const preview = get('preview');
    const sleeves = new Map();
    const bins = [];
    let draft = null, expires = 0, pending = false;
    let renderedDraft = null, renderedPicks = '', activeBin = 0;
    let previewTarget = null, touchTarget = null, inspectionTimer, inspectionInFlight = false, lastRequested = -1;

    function status(message) { get('status').textContent = message; }
    function makeButton(text, click) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = text;
      button.addEventListener('click', click);
      return button;
    }
    function act(action, target) {
      if (!draft || pending || !socket.connected || performance.now() >= expires) return;
      pending = true;
      status('');
      socket.emit('looting_pick', {id: draft.id, action, target});
    }
    function inspect() {
      const target = previewTarget ?? -1;
      if (!draft || draft.host || !socket.connected || performance.now() >= expires
          || inspectionInFlight || lastRequested === target) return;
      const id = draft.id;
      lastRequested = target;
      inspectionInFlight = true;
      socket.timeout(2500).emit('looting_pick', {id, action: 'inspect', target}, error => {
        if (draft?.id !== id) return;
        inspectionInFlight = false;
        if (error) lastRequested = null;
        else inspect();
      });
    }
    function setPreview(target, delay = 0) {
      if (previewTarget === target) return;
      previewTarget = target;
      positionPreview();
      clearTimeout(inspectionTimer);
      inspectionTimer = setTimeout(inspect, delay);
    }
    function positionPreview() {
      const sleeve = sleeves.get(previewTarget);
      const card = draft?.inspected === previewTarget && sleeve?.card;
      if (!card || sleeve.button.getClientRects().length === 0) {
        preview.hidden = true;
        return;
      }
      const anchor = sleeve.button.getBoundingClientRect();
      const rack = sleeve.button.parentElement.getBoundingClientRect();
      const bounds = dialog.getBoundingClientRect();
      if (anchor.bottom <= Math.max(rack.top, bounds.top) || anchor.top >= Math.min(rack.bottom, bounds.bottom)) {
        preview.hidden = true;
        return;
      }
      preview.textContent = card.title || 'Already taken';
      preview.hidden = false;
      const left = anchor.left + (anchor.width - preview.offsetWidth) / 2;
      preview.style.left = Math.max(8, Math.min(left, document.documentElement.clientWidth - preview.offsetWidth - 8)) + 'px';
      const above = anchor.top - preview.offsetHeight - 5;
      preview.style.top = (above >= 8 ? above : anchor.bottom + 5) + 'px';
    }
    function hostAction(action, extras = {}) {
      if (!_isHost || !socket.connected) {
        status('Connect as host to manage the draft.');
        return;
      }
      status('');
      socket.emit('host_action', {action, ...extras});
    }
    function selectBin(index) {
      activeBin = index;
      bins.forEach(({section, tab}, i) => {
        section.toggleAttribute('data-active', i === activeBin);
        tab.setAttribute('aria-pressed', String(i === activeBin));
      });
    }
    function buildShop() {
      renderedDraft = draft.id;
      sleeves.clear();
      bins.length = 0;
      get('bins').replaceChildren();
      get('bin-buttons').replaceChildren();
      draft.bins.forEach((cards, index) => {
        const name = 'Bin ' + (index + 1);
        const tab = makeButton(name, () => {
          selectBin(index);
          setPreview(null);
        });
        get('bin-buttons').append(tab);
        const section = document.createElement('section');
        section.className = 'loot-bin';
        section.setAttribute('aria-label', name);
        const header = document.createElement('header');
        const title = document.createElement('h3');
        title.textContent = name;
        const count = document.createElement('span');
        count.className = 'loot-bin-count';
        count.textContent = cards.length + (cards.length === 1 ? ' sleeve' : ' sleeves');
        header.append(title, count);
        const rack = document.createElement('div');
        rack.className = 'loot-sleeves';
        for (const [position, card] of cards.entries()) {
          let touch = false;
          const button = makeButton('', event => {
            selectBin(index);
            if ((event.pointerType === 'touch' || (event.detail !== 0 && touch))
                && (touchTarget !== card.id || previewTarget !== card.id || draft.inspected !== card.id)) {
              touchTarget = card.id;
              setPreview(card.id);
              return;
            }
            if (!sleeves.get(card.id).card.taken) act('claim', card.id);
          });
          button.className = 'loot-sleeve';
          button.addEventListener('pointerdown', event => { touch = event.pointerType === 'touch'; });
          button.addEventListener('pointerenter', event => {
            if (event.pointerType === 'mouse') setPreview(card.id, 45);
          });
          button.addEventListener('pointerleave', event => {
            if (event.pointerType === 'mouse' && previewTarget === card.id) setPreview(null, 45);
          });
          button.addEventListener('focus', () => { if (button.matches(':focus-visible')) setPreview(card.id); });
          button.addEventListener('blur', () => { if (previewTarget === card.id) setPreview(null); });
          const stamp = document.createElement('span');
          stamp.className = 'loot-stamp';
          stamp.textContent = 'Taken';
          stamp.setAttribute('aria-hidden', 'true');
          button.append(stamp);
          rack.append(button);
          sleeves.set(card.id, {button, stamp, bin: index, label: name + ', sleeve ' + (position + 1)});
        }
        section.append(header, rack);
        get('bins').append(section);
        bins.push({section, tab});
      });
      selectBin(sleeves.get(draft.inspected)?.bin ?? 0);
    }
    function renderPlayer() {
      if (renderedDraft !== draft.id) buildShop();
      for (const cards of draft.bins) {
        for (const card of cards) {
          const sleeve = sleeves.get(card.id);
          sleeve.card = card;
          sleeve.button.setAttribute('aria-pressed', String(previewTarget === card.id));
          sleeve.button.toggleAttribute('data-taken', card.taken);
          sleeve.button.setAttribute('aria-label', sleeve.label + (card.title ? ', ' + card.title : '') + (card.taken ? ', taken' : ''));
          sleeve.stamp.hidden = !card.taken;
        }
      }
      positionPreview();
      get('pick-count').textContent = draft.picks.length + '/' + draft.limit;
      const pickKey = draft.id + ':' + draft.picks.map(pick => pick.id).join(',');
      if (pickKey === renderedPicks) return;
      renderedPicks = pickKey;
      get('picks').replaceChildren(...draft.picks.map(pick => {
        const button = makeButton(pick.title, () => act('release', pick.id));
        button.setAttribute('aria-label', 'Release ' + pick.title);
        const release = document.createElement('span');
        release.textContent = 'Release';
        button.append(release);
        return button;
      }));
    }
    function render() {
      const host = draft?.host || _isHost;
      get('close').hidden = !host;
      get('form').hidden = !host || Boolean(draft);
      get('host-actions').hidden = !host || !draft;
      get('queue').hidden = !draft?.ready;
      get('player').hidden = !draft || host;
      get('progress').textContent = draft
        ? draft.ready
          ? draft.slots + ' songs ready · ' + draft.autoFilled + ' filled at random'
          : draft.claimed + ' of ' + draft.slots + ' picks claimed' + (host ? '' : ' · ' + draft.players + ' in the shop')
        : '';
      if (draft && !host) renderPlayer();
      tick();
    }
    function tick() {
      const seconds = Math.max(0, Math.ceil((expires - performance.now()) / 1000));
      get('clock').textContent = !draft || draft.ready ? '' : Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
    }
    window.openLootingBattle = () => {
      if (!_isHost) return;
      render();
      if (!dialog.open) dialog.showModal();
    };
    get('close').onclick = () => dialog.close();
    get('cancel').onclick = () => hostAction('cancel_looting', {id: draft?.id});
    get('queue').onclick = () => hostAction('queue_looting', {id: draft?.id});
    get('form').onsubmit = event => {
      event.preventDefault();
      hostAction('start_looting', {picks: get('limit').valueAsNumber, seconds: get('seconds').valueAsNumber});
    };
    dialog.addEventListener('cancel', event => {
      if (draft && !draft.host) event.preventDefault();
    });
    socket.on('looting_state', state => {
      const previous = draft;
      draft = state || null;
      expires = performance.now() + (draft?.remaining || 0);
      pending = false;
      if (draft?.id !== previous?.id) {
        clearTimeout(inspectionTimer);
        previewTarget = null;
        touchTarget = null;
        preview.hidden = true;
        inspectionInFlight = false;
        lastRequested = draft?.inspected ?? -1;
        status('');
      }
      if (!draft && previous && !previous.host && dialog.open) dialog.close();
      render();
      if (draft && !draft.host && !dialog.open) dialog.showModal();
    });
    socket.on('looting_error', data => {
      if (draft?.id !== data.id) return;
      pending = false;
      status(data.message);
    });
    socket.on('looting_notice', status);
    const credit = get('credit');
    socket.on('looting_credit', ({name}) => {
      credit.hidden = !name;
      credit.textContent = name ? 'Looted by ' + name : '';
    });
    socket.on('disconnect', () => {
      pending = false;
      inspectionInFlight = false;
      lastRequested = null;
      if (dialog.open) status('Disconnected. Reconnecting…');
    });
    socket.on('connect', () => { if (dialog.open) status(''); });
    dialog.addEventListener('scroll', positionPreview, true);
    window.addEventListener('resize', positionPreview);
    setInterval(tick, 250);
  })();
</script>
"""
