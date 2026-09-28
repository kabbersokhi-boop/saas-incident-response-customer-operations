(() => {
  'use strict';

  const $ = (selector) => document.querySelector(selector);
  const els = {
    services: $('#services-body'),
    events: $('#events-list'),
    deployments: $('#deployments-list'),
    incidents: $('#incidents-list'),
    cases: $('#cases-list'),
    logs: $('#logs-list'),
    error: $('#load-error'),
    status: $('#overall-status'),
    operation: $('#operation-message'),
    checkout: $('#checkout-result'),
    toast: $('#toast-region'),
    incident: $('#live-incident'),
  };
  let state = null;
  let pending = false;

  const first = (...values) => values.find((value) => value !== undefined && value !== null && value !== '');
  const asArray = (value) => Array.isArray(value) ? value : (value && typeof value === 'object' ? Object.values(value) : []);
  const field = (object, ...keys) => first(...keys.map((key) => object?.[key]));
  const display = (value, fallback = '—') => value === undefined || value === null || value === '' ? fallback : String(value);
  const escapeText = (value) => display(value);
  const normalized = (value) => String(value ?? '').toLowerCase();
  const isBad = (value) => /fail|error|down|unhealthy|incident|degraded|rollback|critical/.test(normalized(value));
  const isWarn = (value) => /warn|pending|unknown|partial|recover/.test(normalized(value));

  function node(tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (value !== undefined) element.textContent = escapeText(value);
    return element;
  }

  function setEmpty(container, message) {
    container.replaceChildren(node('div', 'empty-row', message));
  }

  function badgeClass(value) {
    return isBad(value) ? 'bad' : isWarn(value) ? 'warn' : '';
  }

  function serviceName(service) {
    return display(field(service, 'name', 'service', 'service_name', 'key', 'id'), 'Unnamed service');
  }

  function serviceStatus(service) {
    return display(field(service, 'status', 'health', 'state'), 'unknown');
  }

  function serviceVersion(service) {
    return display(field(service, 'version', 'release', 'image_tag'), '—');
  }

  function allServices(data) {
    const raw = field(data, 'services', 'service_health', 'health') ?? [];
    if (Array.isArray(raw)) return raw;
    if (raw && typeof raw === 'object') return Object.entries(raw).map(([name, value]) => typeof value === 'object' ? { name, ...value } : { name, status: value });
    return [];
  }

  function summaryOf(data) {
    return field(data, 'summary', 'counts', 'metrics') || {};
  }

  function setCount(id, value) {
    $(id).textContent = value === undefined || value === null ? '—' : display(value);
  }

  function showToast(message, error = false) {
    const toast = node('div', `toast${error ? ' error' : ''}`, message);
    els.toast.append(toast);
    window.setTimeout(() => toast.remove(), 4200);
  }

  function setOperation(message, kind = '') {
    els.operation.className = `operation-message${kind ? ` ${kind}` : ''}`;
    els.operation.textContent = message;
  }

  function extractMessage(payload, fallback) {
    return display(field(payload, 'message', 'detail', 'error', 'status', 'result'), fallback);
  }

  async function request(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) },
    });
    const bodyText = await response.text();
    let body = null;
    if (bodyText) {
      try { body = JSON.parse(bodyText); } catch { body = { detail: bodyText }; }
    }
    if (!response.ok) {
      const error = new Error(extractMessage(body, `${response.status} ${response.statusText}`));
      error.status = response.status;
      error.body = body;
      throw error;
    }
    return body;
  }

  function renderServiceHealth(services) {
    if (!services.length) {
      setEmpty(els.services, 'The API returned no service records.');
      $('#service-count').textContent = '0 services';
      $('#current-version').textContent = '—';
      $('#release-status').textContent = 'No service data';
      $('#release-status').className = 'release-status warn';
      return;
    }
    els.services.replaceChildren();
    services.forEach((service) => {
      const status = serviceStatus(service);
      const tr = document.createElement('tr');
      const name = node('td');
      const nameWrap = node('span', 'service-name');
      nameWrap.append(node('span', `service-health-dot ${badgeClass(status)}`), node('span', '', serviceName(service)));
      name.append(nameWrap);
      const statusCell = node('td');
      statusCell.append(node('span', `service-status ${badgeClass(status)}`, status));
      const versionCell = node('td');
      versionCell.append(node('span', 'service-version', serviceVersion(service)));
      tr.append(name, statusCell, versionCell);
      els.services.append(tr);
    });
    $('#service-count').textContent = `${services.length} ${services.length === 1 ? 'service' : 'services'}`;
    const checkoutService = services.find((service) => normalized(field(service, 'service_key', 'key')).replaceAll('_', '-').includes('checkout-api')) || services.find((service) => normalized(serviceName(service)).replaceAll(' ', '-').includes('checkout-api'));
    const versions = [...new Set(services.map(serviceVersion).filter((version) => version !== '—'))];
    const bad = services.filter((service) => isBad(serviceStatus(service)));
    const warn = services.filter((service) => isWarn(serviceStatus(service)));
    $('#current-version').textContent = checkoutService ? serviceVersion(checkoutService) : versions.length === 1 ? versions[0] : versions.length > 1 ? `${versions.length} versions` : '—';
    $('#current-release-caption').textContent = checkoutService ? 'Checkout API · reported service version' : versions.length > 1 ? 'Versions reported across services' : 'Reported by service health';
    $('#release-status').textContent = bad.length ? `${bad.length} unhealthy` : warn.length ? `${warn.length} need attention` : 'Services healthy';
    $('#release-status').className = `release-status ${bad.length ? 'bad' : warn.length ? 'warn' : ''}`;
  }

  function renderMetrics(data) {
    const summary = summaryOf(data);
    setCount('#count-customers', field(summary, 'customers', 'customer_count', 'total_customers'));
    setCount('#count-checkout', field(summary, 'checkout_customers', 'checkoutCustomers', 'checkout_customer_count'));
    setCount('#count-deployments', field(summary, 'deployments', 'deployment_count', 'total_deployments'));
    setCount('#count-incidents', field(summary, 'incidents', 'incident_count', 'total_incidents'));
  }

  function displayDate(value) {
    if (!value) return 'Time unavailable';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function renderDeployments(items) {
    const list = asArray(items);
    $('#deployment-count').textContent = `${list.length} ${list.length === 1 ? 'record' : 'records'}`;
    if (!list.length) return setEmpty(els.deployments, 'No deployment records returned.');
    els.deployments.replaceChildren();
    list.slice(0, 6).forEach((item) => {
      const version = field(item, 'version', 'release', 'image_tag', 'tag');
      const status = display(field(item, 'status', 'result', 'outcome'), 'recorded');
      const row = node('div', 'deployment-item');
      row.append(node('span', `deployment-glyph ${badgeClass(status)}`, isBad(status) ? '↶' : '⇧'));
      const detail = node('div', 'deployment-detail');
      detail.append(node('b', '', version ? String(version) : 'Deployment'), node('span', '', display(field(item, 'created_at', 'timestamp', 'deployed_at', 'time'), status)));
      row.append(detail, node('span', `deployment-outcome ${badgeClass(status)}`, status));
      els.deployments.append(row);
    });
  }

  function renderHistory(container, items, type) {
    const list = asArray(items);
    if (type === 'incident') $('#incident-count').textContent = String(list.length);
    else $('#case-count').textContent = String(list.length);
    if (!list.length) return setEmpty(container, `No historical ${type === 'incident' ? 'incidents' : 'service cases'} returned.`);
    container.replaceChildren();
    list.slice(0, 4).forEach((item) => {
      const title = field(item, 'title', 'name', 'incident', 'case', 'summary', 'subject', 'id', 'incident_id', 'case_id');
      const description = field(item, 'description', 'impact', 'details', 'customer_impact', 'resolution');
      const when = field(item, 'ended_at', 'resolved_at', 'created_at', 'started_at', 'timestamp');
      const row = node('div', 'history-item');
      row.append(node('span', `history-mark${type === 'case' ? ' case' : ''}`, type === 'case' ? '↗' : '!'));
      const info = node('div', 'history-info');
      info.append(node('b', '', title || (type === 'incident' ? 'Incident record' : 'Service case')));
      const affected = field(item, 'affected_customer_count', 'affected_customers', 'customer_count');
      if (description || affected !== undefined) {
        const details = [description, affected !== undefined ? `${display(affected)} affected customers` : ''].filter(Boolean).join(' · ');
        info.append(node('p', '', details));
      }
      row.append(info, node('span', 'history-meta', displayDate(when)));
      container.append(row);
    });
  }

  function eventTime(event) {
    return field(event, 'timestamp', 'created_at', 'time', 'occurred_at', 'at');
  }

  function renderEvents(events) {
    const list = asArray(events);
    if (!list.length) return setEmpty(els.events, 'No recent events returned.');
    els.events.replaceChildren();
    list.slice(0, 7).forEach((event) => {
      const row = node('div', 'event-item');
      const time = eventTime(event);
      row.append(node('span', 'event-time', time ? displayDate(time) : '—'));
      const copy = node('div', 'event-copy');
      copy.textContent = display(field(event, 'message', 'description', 'event', 'action', 'type', 'name'), 'Event');
      row.append(copy);
      els.events.append(row);
    });
  }

  function renderLastCheckout(checkout, events = []) {
    const checkoutEvents = asArray(events).filter((event) => /checkout\.(failed|created|succeeded|completed)/i.test(`${field(event, 'event_type', 'type', 'event', 'action', 'name') || ''} ${field(event, 'message', 'description') || ''}`));
    const latestAttempt = checkoutEvents[0];
    if (latestAttempt) {
      const details = field(latestAttempt, 'details') || {};
      const kind = `${field(latestAttempt, 'event_type', 'type', 'event', 'action', 'name') || ''} ${field(latestAttempt, 'message', 'description') || ''}`;
      const failed = /fail|error/i.test(kind);
      const orderId = field(details, 'order_id', 'orderId') || field(latestAttempt, 'order_id', 'orderId');
      const reason = field(details, 'reason');
      const label = failed ? `Checkout failed${reason ? `: ${display(reason)}` : ''}` : display(field(latestAttempt, 'message', 'description', 'event_type', 'type', 'event'), 'Checkout completed');
      els.checkout.className = `checkout-result${failed ? ' error' : ''}`;
      els.checkout.replaceChildren(document.createTextNode(`${label}${orderId ? ` · Order ${display(orderId)}` : ''}`));
      if (orderId && !failed) {
        const link = node('a', '', ' Read order ↗');
        link.href = `#order-${encodeURIComponent(String(orderId))}`;
        link.addEventListener('click', (event) => { event.preventDefault(); readOrder(String(orderId)); });
        els.checkout.append(link);
      }
      return;
    }
    if (!checkout || typeof checkout !== 'object') return;
    const orderId = field(checkout, 'order_id', 'id', 'orderId');
    const status = field(checkout, 'status', 'result');
    if (!orderId && !status) return;
    els.checkout.className = 'checkout-result';
    els.checkout.replaceChildren();
    els.checkout.append(document.createTextNode(`${status ? `${display(status)} · ` : ''}${orderId ? `Order ${display(orderId)}` : 'Latest checkout recorded'}`));
    if (orderId) {
      const link = node('a', '', ' Read order ↗');
      link.href = `#order-${encodeURIComponent(String(orderId))}`;
      link.addEventListener('click', (event) => { event.preventDefault(); readOrder(String(orderId)); });
      els.checkout.append(link);
    }
  }

  function updateOverall(services) {
    const bad = services.some((service) => isBad(serviceStatus(service)));
    const warn = services.some((service) => isWarn(serviceStatus(service)));
    const label = bad ? 'Degraded' : warn ? 'Attention' : services.length ? 'Operational' : 'No service data';
    els.status.className = `overall-status ${bad ? 'bad' : warn || !services.length ? 'warn' : 'ok'}`;
    els.status.lastElementChild.textContent = label;
  }

  function renderState(data) {
    state = data || {};
    const services = allServices(state);
    renderMetrics(state);
    renderServiceHealth(services);
    renderDeployments(field(state, 'recent_deployments', 'deployments', 'deployment_history'));
    renderHistory(els.incidents, field(state, 'historical_incidents', 'incidents'), 'incident');
    renderHistory(els.cases, field(state, 'historical_service_cases', 'service_cases', 'historical_cases'), 'case');
    renderEvents(field(state, 'recent_events', 'events', 'event_stream'));
    renderLastCheckout(field(state, 'last_checkout', 'latest_checkout'), field(state, 'recent_events', 'events', 'event_stream'));
    updateOverall(services);
    const timestamp = field(state, 'updated_at', 'generated_at', 'timestamp');
    $('#updated-at').textContent = timestamp ? `Updated ${displayDate(timestamp)}` : `Updated ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }

  async function loadHealth() {
    try {
      const health = await request('/health');
      $('#service-version').textContent = `API ${display(field(health, 'version'), 'version unavailable')}`;
    } catch (error) {
      $('#service-version').textContent = 'Health endpoint unavailable';
      console.warn('RelayCart health check failed:', error);
    }
  }

  async function loadState(showError = true) {
    try {
      const data = await request('/demo/state');
      renderState(data);
      els.error.classList.add('hidden');
      return data;
    } catch (error) {
      if (showError) {
        els.error.textContent = `Could not load live demo state: ${error.message}`;
        els.error.classList.remove('hidden');
        els.status.className = 'overall-status bad';
        els.status.lastElementChild.textContent = 'API unavailable';
      }
      return null;
    }
  }

  function normalizeLogs(payload) {
    if (Array.isArray(payload)) return payload;
    return asArray(field(payload, 'logs', 'items', 'entries', 'recent_logs', 'events'));
  }

  function renderLogs(payload) {
    const logs = normalizeLogs(payload);
    $('#logs-state').textContent = `${logs.length} ${logs.length === 1 ? 'entry' : 'entries'}`;
    if (!logs.length) return setEmpty(els.logs, 'No log entries returned by /logs.');
    els.logs.replaceChildren();
    logs.slice(0, 12).forEach((log) => {
      const time = field(log, 'timestamp', 'time', 'created_at', 'at');
      const level = display(field(log, 'level', 'severity'), 'INFO').toUpperCase();
      const message = typeof log === 'string' ? log : display(field(log, 'message', 'msg', 'event', 'detail', 'description'), JSON.stringify(log));
      const row = node('div', 'log-line');
      row.append(node('span', 'log-time', time ? displayDate(time) : ''), node('span', `log-level${isBad(level) ? ' error' : ''}`, level), node('span', 'log-content', message));
      els.logs.append(row);
    });
  }

  async function loadLogs() {
    $('#logs-state').textContent = 'Loading';
    try {
      const logs = await request('/logs');
      renderLogs(logs);
    } catch (error) {
      $('#logs-state').textContent = 'Unavailable';
      setEmpty(els.logs, `Could not load logs: ${error.message}`);
    }
  }

  function renderActiveIncident(payload) {
    $('#live-incident-state').textContent = payload && payload.available ? 'READ ONLY' : 'N8N SCHEMA NOT INSTALLED';
    if (!payload || !payload.available) return setEmpty(els.incident, 'Incident automation is not connected yet.');
    const incident = payload.incident;
    if (!incident) return setEmpty(els.incident, 'No technical incident has been recorded.');
    $('#live-incident-state').textContent = incident.is_active ? 'ACTIVE · READ ONLY' : 'LATEST · READ ONLY';

    els.incident.replaceChildren();
    const heading = node('div', 'live-incident-heading');
    const identity = node('div');
    identity.append(
      node('b', 'incident-id', incident.incident_id),
      node('span', '', display(incident.service) + ' · ' + display(incident.environment) + ' · ' + display(incident.current_version, 'release unknown')),
    );
    heading.append(identity, node('span', 'incident-severity ' + badgeClass(incident.severity), display(incident.severity) + ' · ' + display(incident.state)));
    els.incident.append(heading);
    if (incident.summary) els.incident.append(node('p', 'live-incident-summary', incident.summary));

    const body = node('div', 'live-incident-grid');
    const timeline = node('div', 'incident-readonly-section');
    timeline.append(node('h3', '', 'Signal timeline'));
    const signals = asArray(incident.timeline);
    if (!signals.length) {
      timeline.append(node('div', 'empty-row', 'No correlated signals yet.'));
    } else {
      signals.slice(-6).forEach((signal) => {
        const row = node('div', 'incident-signal');
        row.append(
          node('span', 'incident-signal-time', displayDate(signal.occurred_at)),
          node('span', 'incident-signal-type', signal.event_type),
          node('span', 'incident-signal-relation', signal.relationship),
        );
        timeline.append(row);
      });
    }
    body.append(timeline);

    const details = node('div', 'incident-readonly-section');
    details.append(node('h3', '', 'Investigation and recovery'));
    const assessment = incident.assessment;
    const proposal = incident.proposal;
    const checks = asArray(incident.remediation && incident.remediation.verification_checks);
    const facts = [
      ['Healthy release', incident.healthy_version],
      ['AI assessment', assessment ? assessment.status + ' · ' + assessment.provider + (assessment.model ? ' · ' + assessment.model : '') : 'Not available'],
      ['Remediation', proposal ? proposal.action_type + ' · ' + proposal.status + (proposal.source_version ? ' · ' + proposal.source_version + ' → ' + proposal.target_version : '') : 'No proposal'],
      ['Approval', proposal && proposal.approval ? proposal.approval.status : 'No approval'],
      ['Verification', checks.length ? checks.map((check) => check.check_name + ': ' + (check.passed ? 'passed' : 'failed')).join(' · ') : 'Not run'],
    ];
    facts.forEach(([label, value]) => {
      const fact = node('div', 'incident-fact');
      fact.append(node('span', '', label), node('b', '', value || '—'));
      details.append(fact);
    });
    const hypotheses = asArray(assessment && assessment.assessment && assessment.assessment.hypotheses);
    if (hypotheses[0] && hypotheses[0].summary) details.append(node('p', 'incident-assessment-summary', hypotheses[0].summary));
    const evidence = asArray(incident.evidence);
    if (evidence.length) {
      const evidenceList = node('div', 'incident-evidence-list');
      evidenceList.append(node('b', '', 'Evidence'));
      evidence.slice(0, 4).forEach((item) => evidenceList.append(node('span', '', item.evidence_key + ' · ' + item.summary)));
      details.append(evidenceList);
    }
    body.append(details);
    els.incident.append(body);
  }

  async function loadActiveIncident() {
    try {
      renderActiveIncident(await request('/incidents/latest'));
    } catch (error) {
      $('#live-incident-state').textContent = 'UNAVAILABLE';
      setEmpty(els.incident, 'Could not load incident state: ' + error.message);
    }
  }

  async function refreshAll() {
    $('#refresh-button').disabled = true;
    await Promise.all([loadHealth(), loadState(), loadLogs(), loadActiveIncident()]);
    $('#refresh-button').disabled = false;
  }

  async function readOrder(id) {
    els.checkout.className = 'checkout-result';
    els.checkout.textContent = `Reading order ${id}…`;
    try {
      const result = await request(`/orders/${encodeURIComponent(id)}`);
      const order = field(result, 'order') || result;
      els.checkout.replaceChildren();
      const orderId = field(order, 'id', 'order_id') || id;
      const status = field(order, 'status', 'state');
      const amount = field(order, 'amount', 'total');
      const currency = field(order, 'currency');
      els.checkout.append(document.createTextNode(`Order ${display(orderId)}${status ? ` · ${display(status)}` : ''}${amount !== undefined ? ` · ${display(currency, '')} ${display(amount)}` : ''}`));
      const details = node('div', 'order-details');
      details.textContent = JSON.stringify(order, null, 2);
      els.checkout.append(details);
    } catch (error) {
      els.checkout.className = 'checkout-result error';
      els.checkout.textContent = `Order read-back failed: ${error.message}`;
    }
  }

  function setBusy(buttons, busy) {
    pending = busy;
    buttons.forEach((button) => { button.disabled = busy; });
  }

  async function runAction(buttons, label, path, payload) {
    if (pending) return;
    setBusy(buttons, true);
    els.operation.className = 'operation-message';
    els.operation.textContent = `${label}…`;
    try {
      const options = { method: 'POST' };
      if (payload !== null) options.body = JSON.stringify(payload);
      const result = await request(path, options);
      const outcome = field(result, 'status', 'outcome');
      const degraded = isBad(outcome) || isBad(field(result, 'outcome'));
      const message = `${label} completed${outcome ? ` · ${display(outcome)}` : ''}`;
      setOperation(message, degraded ? 'error' : 'success');
      showToast(message, degraded);
      await Promise.all([loadState(false), loadLogs(), loadActiveIncident()]);
    } catch (error) {
      const message = `${label} failed: ${error.message}`;
      setOperation(message, 'error');
      showToast(message, true);
      await Promise.all([loadState(false), loadLogs(), loadActiveIncident()]);
    } finally {
      setBusy(buttons, false);
    }
  }

  async function runCheckout() {
    if (pending) return;
    const button = $('#checkout-button');
    setBusy([button], true);
    els.checkout.className = 'checkout-result';
    els.checkout.textContent = 'Sending checkout request…';
    try {
      const response = await request('/checkout', { method: 'POST', body: JSON.stringify({ customer_slug: 'acme-bikes', amount: '129.99', currency: 'USD' }) });
      const orderId = field(response, 'order_id', 'id', 'orderId');
      els.checkout.replaceChildren();
      els.checkout.className = 'checkout-result';
      const summary = field(response, 'message', 'status') || 'Checkout request accepted';
      els.checkout.append(document.createTextNode(`${display(summary)}${orderId ? ` · Order ${display(orderId)}` : ''}`));
      showToast('Checkout request completed.');
      await Promise.all([loadState(false), loadLogs(), loadActiveIncident()]);
      if (orderId) await readOrder(String(orderId));
    } catch (error) {
      els.checkout.className = 'checkout-result error';
      els.checkout.textContent = `Checkout failed: ${error.message}`;
      showToast(`Checkout failed: ${error.message}`, true);
      await Promise.all([loadState(false), loadLogs()]);
    } finally {
      setBusy([button], false);
    }
  }

  async function resetDemo() {
    if (pending) return;
    const buttons = [$('#reset-button'), $('#deploy-183'), $('#deploy-182'), $('#deploy-181'), $('#rollback-button'), $('#checkout-button')];
    setBusy(buttons, true);
    setOperation('Resetting demo state…');
    try {
      const result = await request('/demo/reset', { method: 'POST', body: '{}' });
      const message = extractMessage(result, 'Demo state reset.');
      setOperation(message, 'success');
      showToast(message);
      els.checkout.classList.add('hidden');
      await Promise.all([loadState(false), loadLogs()]);
    } catch (error) {
      setOperation(`Reset failed: ${error.message}`, 'error');
      showToast(`Reset failed: ${error.message}`, true);
    } finally {
      setBusy(buttons, false);
    }
  }

  $('#refresh-button').addEventListener('click', refreshAll);
  $('#logs-refresh').addEventListener('click', loadLogs);
  $('#checkout-button').addEventListener('click', runCheckout);
  $('#deploy-183').addEventListener('click', () => runAction([$('#deploy-183'), $('#deploy-182'), $('#deploy-181'), $('#rollback-button')], 'Deploy v1.8.3', '/deploy', { version: 'v1.8.3' }));
  $('#deploy-182').addEventListener('click', () => runAction([$('#deploy-183'), $('#deploy-182'), $('#deploy-181'), $('#rollback-button')], 'Deploy v1.8.2', '/deploy', { version: 'v1.8.2' }));
  $('#deploy-181').addEventListener('click', () => runAction([$('#deploy-183'), $('#deploy-182'), $('#deploy-181'), $('#rollback-button')], 'Deploy v1.8.1', '/deploy', { version: 'v1.8.1' }));
  $('#rollback-button').addEventListener('click', () => runAction([$('#deploy-183'), $('#deploy-182'), $('#deploy-181'), $('#rollback-button')], 'Rollback', '/rollback', null));
  $('#reset-button').addEventListener('click', resetDemo);

  refreshAll();
  window.setInterval(() => { loadState(false); loadLogs(); loadActiveIncident(); }, 30000);
})();
