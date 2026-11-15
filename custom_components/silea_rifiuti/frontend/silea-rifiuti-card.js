// Silea Rifiuti Card: prossimo ritiro, prossimo passaggio per tipo, centro di raccolta e calendario di alcune settimane.
// Viene caricata in automatico dall'integrazione silea_rifiuti.
//
// type: custom:silea-rifiuti-card
// entity: calendar.raccolta_rifiuti_..._calendario   (obbligatorio)
// weeks: 5                                           (settimane nel calendario)
// names: {indifferenziato: Secco}                    (nomi personalizzati per tipo)
// centro: false                                      (nasconde il centro di raccolta; oppure l'entità binary_sensor da usare)
const VERSION = '0.3.1';
const TIPI = {
  umido: { n: 'Umido', i: 'mdi:food-apple-outline', c: '#c87734' },
  carta: { n: 'Carta', i: 'mdi:newspaper-variant-outline', c: '#2f9cc0' },
  vetro: { n: 'Vetro', i: 'mdi:bottle-wine-outline', c: '#3fa05c' },
  plastica: { n: 'Plastica', i: 'mdi:recycle', c: '#b8902a' },
  indifferenziato: { n: 'Indifferenziato', i: 'mdi:trash-can-outline', c: '#8b857c' },
  altro: { n: 'Altro', i: 'mdi:delete-variant', c: '#8e6bb8' },
};
const ORDINE = Object.keys(TIPI);
const WD = ['domenica', 'lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato'];
const MO = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
const MOL = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'];

// Stesso criterio di tipo_da_servizio() in const.py.
function tipo(summary) {
  const s = String(summary || '').toUpperCase();
  if (s.includes('UMIDO') || s.includes('ORGANIC')) return 'umido';
  if (s.includes('CARTA')) return 'carta';
  if (s.includes('VETRO')) return 'vetro';
  if (s.includes('PLASTICA') || s.includes('LATTINE')) return 'plastica';
  if (s.includes('INDIFF') || s.includes('SECCO')) return 'indifferenziato';
  return 'altro';
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const hhmm = (d) => `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;

class SileaRifiutiCard extends HTMLElement {
  static getStubConfig(hass) {
    const cal = Object.keys(hass.states).filter((e) => e.startsWith('calendar.'));
    return { entity: cal.find((e) => e.includes('raccolta_rifiuti')) || cal[0] || 'calendar.raccolta_rifiuti' };
  }

  setConfig(config) {
    if (!config.entity) throw new Error('Serve entity: il calendario creato da Silea Raccolta Rifiuti');
    this._cfg = { weeks: 5, ...config };
    this._tipi = {};
    ORDINE.forEach((k) => { this._tipi[k] = { ...TIPI[k], n: (config.names && config.names[k]) || TIPI[k].n }; });
    this._days = null;
    this._at = 0;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot) this._init();
    const now = Date.now();
    if (now - this._at > 30 * 60 * 1000) { this._at = now; this._load(); }
    const minute = Math.floor(now / 60000);
    if (minute !== this._minute) { this._minute = minute; this._render(); }
  }

  _init() {
    this.attachShadow({ mode: 'open' }).innerHTML = `<style>
      :host{display:block}
      .row{display:grid;grid-template-columns:1.1fr 1fr;gap:10px;margin-bottom:10px}
      @media (max-width:760px){.row{grid-template-columns:1fr}}
      .p{background:var(--ha-card-background,var(--card-background-color));border:1px solid var(--divider-color);border-radius:var(--ha-card-border-radius,14px);padding:16px 18px;color:var(--primary-text-color);min-width:0}
      .hero.hot{background:var(--carta-accent-soft,rgba(47,156,192,.12));border-color:var(--carta-accent-line,var(--divider-color))}
      .k{font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--secondary-text-color)}
      .hot .k{color:var(--carta-accent-ink,var(--primary-color))}
      .big{font-family:var(--ha-font-family-heading,inherit);font-size:30px;line-height:36px;font-weight:700;margin:6px 0 2px}
      .sub{font-size:13px;font-weight:600;color:var(--secondary-text-color)}
      .chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 10px}
      .chip{display:inline-flex;align-items:center;gap:8px;padding:5px 14px 5px 5px;border-radius:999px;font-size:15px;font-weight:700;white-space:nowrap}
      .dot{width:32px;height:32px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;flex:none}
      .dot ha-icon{--mdc-icon-size:18px;color:#fff;display:flex}
      .h{font-size:15px;font-weight:600;color:var(--secondary-text-color);margin-bottom:6px}
      .t{display:flex;align-items:center;gap:12px;padding:8px 0;border-top:1px solid var(--divider-color)}
      .t:first-of-type{border-top:none}
      .t .dot{width:28px;height:28px}.t .dot ha-icon{--mdc-icon-size:16px}
      .t b{font-size:14px}.t .w{margin-left:auto;text-align:right;font-size:13px;font-weight:700}
      .t .w.soon{color:var(--carta-accent-ink,var(--primary-color))}
      .t .w small{display:block;font-size:12px;font-weight:600;color:var(--secondary-text-color)}
      .cal{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}
      .cal .dn{font-size:11px;font-weight:700;color:var(--secondary-text-color);text-align:center;padding-bottom:4px;text-transform:uppercase}
      .d{min-height:62px;border-radius:10px;background:var(--secondary-background-color);padding:6px;display:flex;flex-direction:column;gap:4px}
      .d .num{font-size:12px;font-weight:700;color:var(--secondary-text-color)}
      .d.past{opacity:.38}
      .d.today{outline:2px solid var(--carta-accent-ink,var(--primary-color))}
      .d.today .num{color:var(--carta-accent-ink,var(--primary-color))}
      .d .ev{display:flex;flex-wrap:wrap;gap:3px}
      .d .e{width:22px;height:22px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center}
      .d .e ha-icon{--mdc-icon-size:13px;color:#fff;display:flex}
      .leg{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:10px;font-size:12px;font-weight:600;color:var(--secondary-text-color)}
      .leg i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
      .empty{font-size:14px;color:var(--secondary-text-color);padding:6px 0}
      .cr{margin-bottom:10px}
      .crh{display:flex;align-items:center;gap:12px}
      .st{font-size:16px;font-weight:700;margin-top:2px}
      .st.on{color:#3fa05c}
      .ore{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:10px;font-size:13px;color:var(--secondary-text-color)}
      .og b{text-transform:capitalize;color:var(--primary-text-color);margin-right:2px}
      .og.now{color:var(--primary-text-color);font-weight:600}
      @media (max-width:500px){.d{min-height:48px;padding:4px}.d .e{width:16px;height:16px}.d .e ha-icon{--mdc-icon-size:10px}}
    </style><div class="wrap"><div class="p empty">Carico il calendario…</div></div>`;
  }

  _key(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }

  async _load() {
    const t0 = new Date(); t0.setHours(0, 0, 0, 0);
    const start = new Date(t0); start.setDate(start.getDate() - ((start.getDay() + 6) % 7)); // lunedì di questa settimana
    const end = new Date(start); end.setDate(end.getDate() + 7 * this._cfg.weeks + 60); // oltre il calendario, per "prossimo per tipo"
    try {
      const ev = await this._hass.callApi('GET', `calendars/${this._cfg.entity}?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`);
      const days = {};
      ev.forEach((e) => {
        const s = (e.start && (e.start.dateTime || e.start.date)) || '';
        const k = s.slice(0, 10);
        if (!k) return;
        const d = (days[k] = days[k] || { tipi: [], fine: null, note: '' });
        const c = tipo(e.summary);
        if (!d.tipi.includes(c)) d.tipi.push(c);
        const f = e.end && e.end.dateTime ? new Date(e.end.dateTime) : null;
        if (f && (!d.fine || f > d.fine)) d.fine = f;
        if (!d.note && e.description) d.note = String(e.description);
      });
      Object.values(days).forEach((d) => d.tipi.sort((a, b) => ORDINE.indexOf(a) - ORDINE.indexOf(b)));
      this._days = days; this._start = start; this._err = null;
    } catch (e) { this._err = e && e.message ? e.message : String(e); }
    this._render();
  }

  _chip(c) { const t = this._tipi[c]; return `<span class="chip" style="background:${t.c}26"><span class="dot" style="background:${t.c}"><ha-icon icon="${t.i}"></ha-icon></span>${esc(t.n)}</span>`; }
  _ico(c, cls = 'dot') { const t = this._tipi[c]; return `<span class="${cls}" style="background:${t.c}" title="${esc(t.n)}"><ha-icon icon="${t.i}"></ha-icon></span>`; }

  // Il binary_sensor del centro di raccolta: dal config, oppure quello dello stesso dispositivo del calendario.
  _centroId() {
    if (this._cfg.centro === false) return null;
    if (typeof this._cfg.centro === 'string') return this._cfg.centro;
    const reg = this._hass.entities || {};
    const dev = reg[this._cfg.entity] && reg[this._cfg.entity].device_id;
    if (!dev) return null;
    const e = Object.values(reg).find((x) => x.device_id === dev && x.platform === 'silea_rifiuti' && x.entity_id.startsWith('binary_sensor.'));
    return e ? e.entity_id : null;
  }

  _centro(now, label) {
    const id = this._centroId();
    const st = id && this._hass.states[id];
    if (!st || st.state === 'unavailable' || st.state === 'unknown') return '';
    const a = st.attributes;
    const aperto = st.state === 'on';
    const quando = (iso) => {
      const d = new Date(iso), t0 = new Date(now); t0.setHours(0, 0, 0, 0);
      const k = this._key(d), n = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - t0) / 86400000);
      return `${n === 0 ? 'oggi' : n === 1 ? 'domani' : label(k).toLowerCase()} alle ${hhmm(d)}`;
    };
    const stato = aperto ? `Aperto · chiude alle ${hhmm(new Date(a.chiude_alle))}`
      : a.prossima_apertura ? `Chiuso · apre ${quando(a.prossima_apertura)}` : 'Chiuso';
    // "Utenze domestiche (famiglie)" → "orari famiglie"; niente se gli orari valgono per tutti.
    const chi = (String(a.utenza || '').match(/\(([^)]+)\)/) || [])[1];
    const oggi = WD[now.getDay()];
    const giorni = Object.entries(a.orario || {}).filter(([, h]) => h !== 'chiuso');
    const orario = giorni.length
      ? giorni.map(([g, h]) => `<span class="og ${g === oggi ? 'now' : ''}"><b>${esc(g.slice(0, 3))}</b> ${esc(h.replace(/-/g, '–'))}</span>`).join('')
      : `<span class="og">${esc(a.nota || 'Orario non disponibile')}</span>`;
    return `<div class="p cr"><div class="crh"><span class="dot" style="background:${aperto ? '#3fa05c' : '#8b857c'}"><ha-icon icon="mdi:store-outline"></ha-icon></span>
        <div><div class="h" style="margin:0">Centro di raccolta · ${esc(a.indirizzo || a.centro || '')}${chi ? ` · orari ${esc(chi)}` : ''}</div>
        <div class="st ${aperto ? 'on' : ''}">${esc(stato)}</div></div></div>
        <div class="ore">${orario}</div></div>`;
  }

  _render() {
    const wrap = this.shadowRoot && this.shadowRoot.querySelector('.wrap');
    if (!wrap) return;
    if (this._err) { wrap.innerHTML = `<div class="p empty">Calendario non leggibile: ${esc(this._err)}</div>`; return; }
    if (!this._days) return;
    const T = this._tipi;
    const now = new Date(), t0 = new Date(now); t0.setHours(0, 0, 0, 0);
    const todayK = this._key(t0);
    const diff = (k) => { const p = k.split('-'); return Math.round((new Date(+p[0], +p[1] - 1, +p[2]) - t0) / 86400000); };
    // Il ritiro di oggi conta come passato dopo l'orario di fine indicato da Silea.
    const done = (k) => { const n = diff(k); return n < 0 || (n === 0 && this._days[k] && this._days[k].fine && now >= this._days[k].fine); };
    const upcoming = Object.keys(this._days).sort().filter((k) => !done(k) && diff(k) >= 0);
    const label = (k) => { const n = diff(k), p = k.split('-'), d = new Date(+p[0], +p[1] - 1, +p[2]); return n === 0 ? 'Oggi' : n === 1 ? 'Domani' : `${WD[d.getDay()][0].toUpperCase()}${WD[d.getDay()].slice(1)} ${d.getDate()} ${MO[d.getMonth()]}`; };
    const presenti = ORDINE.filter((c) => c !== 'altro' || Object.values(this._days).some((d) => d.tipi.includes('altro')));

    let hero;
    if (!upcoming.length) hero = '<div class="p hero"><div class="k">Prossimo ritiro</div><div class="empty">Nessun ritiro in calendario.</div></div>';
    else {
      const k = upcoming[0], n = diff(k), day = this._days[k];
      const head = n === 0 ? 'Oggi passano' : n === 1 ? 'Stasera porta fuori' : 'Prossimo ritiro';
      const note = day.note ? ` · ${esc(day.note.charAt(0).toLowerCase() + day.note.slice(1))}` : '';
      const sub = n === 0 ? (day.fine ? `Ritiro fino alle ${hhmm(day.fine)}` : 'Ritiro in corso') : n === 1 ? `Da esporre stasera${note}` : `tra ${n} giorni`;
      const nxt = upcoming[1];
      hero = `<div class="p hero ${n <= 1 ? 'hot' : ''}"><div class="k">${head}</div>
        <div class="big">${label(k)}</div>
        <div class="chips">${day.tipi.map((c) => this._chip(c)).join('')}</div>
        <div class="sub">${sub}${nxt ? ` · poi ${label(nxt).toLowerCase()}: ${this._days[nxt].tipi.map((c) => esc(T[c].n.toLowerCase())).join(', ')}` : ''}</div></div>`;
    }

    const perTipo = presenti.map((c) => {
      const k = upcoming.find((x) => this._days[x].tipi.includes(c));
      if (!k) return `<div class="t">${this._ico(c)}<b>${esc(T[c].n)}</b><span class="w">—<small>non in calendario</small></span></div>`;
      const n = diff(k);
      const quando = n === 0 ? 'oggi' : n === 1 ? 'domani' : `tra ${n} giorni`;
      return `<div class="t">${this._ico(c)}<b>${esc(T[c].n)}</b><span class="w ${n <= 1 ? 'soon' : ''}">${label(k)}<small>${quando}</small></span></div>`;
    }).join('');

    const cells = [];
    const s = this._start;
    for (let i = 0; i < 7 * this._cfg.weeks; i++) {
      const d = new Date(s); d.setDate(s.getDate() + i);
      const k = this._key(d);
      const past = diff(k) < 0 || (k === todayK && (done(k) || !this._days[k]));
      const num = d.getDate() === 1 || i === 0 ? `${d.getDate()} ${MO[d.getMonth()]}` : d.getDate();
      cells.push(`<div class="d ${past ? 'past' : ''} ${k === todayK ? 'today' : ''}"><span class="num">${num}</span><span class="ev">${((this._days[k] || {}).tipi || []).map((c) => this._ico(c, 'e')).join('')}</span></div>`);
    }
    const last = new Date(s); last.setDate(s.getDate() + 7 * this._cfg.weeks - 1);
    const titolo = s.getMonth() === last.getMonth() ? MOL[s.getMonth()] : `${MOL[s.getMonth()]} – ${MOL[last.getMonth()]}`;
    wrap.innerHTML = `<div class="row">${hero}<div class="p"><div class="h">Prossimo passaggio per tipo</div>${perTipo}</div></div>
      ${this._centro(now, label)}
      <div class="p"><div class="h">Calendario · ${titolo}</div>
        <div class="cal">${['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'].map((x) => `<div class="dn">${x}</div>`).join('')}${cells.join('')}</div>
        <div class="leg">${presenti.map((c) => `<span><i style="background:${T[c].c}"></i>${esc(T[c].n)}</span>`).join('')}</div>
      </div>`;
  }

  getCardSize() { return 14; }
  getGridOptions() { return { columns: 'full', rows: 'auto' }; }
}

if (!customElements.get('silea-rifiuti-card')) customElements.define('silea-rifiuti-card', SileaRifiutiCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === 'silea-rifiuti-card')) {
  window.customCards.push({ type: 'silea-rifiuti-card', name: 'Silea Rifiuti', description: 'Prossimi ritiri e calendario della raccolta Silea', preview: false });
}
console.info(`%c SILEA-RIFIUTI-CARD %c ${VERSION} `, 'background:#3fa05c;color:#fff;font-weight:700', 'background:#eee;color:#333');
