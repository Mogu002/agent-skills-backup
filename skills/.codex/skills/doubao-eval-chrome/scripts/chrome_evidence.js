/* Paste this file into cua_repl after browser setup. No imports or browser driver. */
var doubaoChrome = (() => {
  const version = '1.0.0';
  const kinds = ['inventory', 'fields', 'widgets', 'workflow_nodes', 'field_detail',
    'chart_detail', 'workflow_step', 'permission', 'form', 'form_settings'];
  const limitations = Object.freeze({
    inventory: ['full_inventory_virtualization'],
    fields: ['full_schema', 'all_records', 'formula_results'],
    widgets: ['all_widget_configs', 'chart_recalculation', 'visual_verification'],
    workflow_nodes: ['complex_workflow_topology', 'workflow_execution'],
    field_detail: ['all_records', 'formula_results'],
    chart_detail: ['chart_recalculation', 'visual_verification'],
    workflow_step: ['complex_workflow_topology', 'workflow_execution'],
    permission: ['permission_effective_access', 'permission_conditional_rules', 'all_roles'],
    form: ['form_conditional_logic', 'form_submission', 'source_field_types'],
    form_settings: ['form_conditional_logic', 'form_submission']
  });
  const selectors = {
    inventory: '[id^="bitable-ssr-sidebar-item-"]',
    fields: '.bitable-field-panel-list-item', widgets: '.layout-item[data-id]',
    workflow_nodes: '.bitable-workflow-builder-canvas-engine-step-node'
  };
  const capabilities = Object.freeze({inventory:'mounted_inventory', fields:'field_names_icons',
    widgets:'mounted_widgets', workflow_nodes:'visible_nodes', field_detail:'field_panel',
    chart_detail:'chart_panel', workflow_step:'node_panel', permission:'permission_panel',
    form:'visible_form', form_settings:'form_settings_panel'});
  function need(value, label) {
    if (typeof value !== 'string' || !value.trim()) throw new Error('Missing ' + label);
    return value;
  }
  function validUrl(value) {
    const u = new URL(need(value, 'expectedUrl'));
    if (u.protocol !== 'https:' || u.username || u.password ||
      !/(^|\.)(feishu\.cn|larkoffice\.com|larksuite\.com)$/.test(u.hostname) ||
      !/^\/(base|share\/base)\/[A-Za-z0-9]+\/?$/.test(u.pathname)) throw new Error('Not an HTTPS Base/Form URL');
    return u.href;
  }
  async function guard(tab, req) {
    if (req?.identityConfirmed !== true) throw new Error('Confirm test account and tenant first');
    if (await tab.url() !== validUrl(req.expectedUrl)) throw new Error('URL changed: inspect current page before continuing');
  }
  async function one(locator) {
    if (await locator.count() !== 1 || !await locator.isVisible()) throw new Error('Target missing, hidden, or ambiguous');
    return locator;
  }
  // Self-contained DOM callback: no runtime objects, networking, or mutations.
  function extract(elements, kind) {
    function visible(el) {
      if (!el.getClientRects().length) return false;
      for (let p = el; p; p = p.parentElement) {
        const s = getComputedStyle(p);
        if (s.display === 'none' || s.visibility === 'hidden' || p.getAttribute('aria-hidden') === 'true') return false;
      }
      return true;
    }
    function control(el) {
      const aria = el.getAttribute('aria-checked');
      const native = el.tagName === 'INPUT' && ['checkbox', 'radio'].includes(el.type);
      const universe = el.classList.contains('ud__switch');
      return {role: el.getAttribute('role') || el.type || el.tagName.toLowerCase(),
        label: el.getAttribute('aria-label') || el.closest('label')?.innerText ||
          el.closest('.bitable-perm-table-role-field-v2-item-checkbox-wrapper')
            ?.querySelector('.bitable-perm-table-role-field-v2-item-checkbox-title')?.textContent || null,
        value: 'value' in el ? el.value : null,
        checked: native ? (el.indeterminate ? 'mixed' : el.checked) :
          aria === 'mixed' ? 'mixed' : aria === 'true' ? true : aria === 'false' ? false :
          universe ? el.classList.contains('ud__switch-checked') : null,
        checkedSource: native ? 'native-property' : aria !== null ? 'aria-checked' : universe ? 'ud__switch-class' : null,
        disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true',
        context: el.parentElement?.innerText || '', className: el.getAttribute('class')};
    }
    return elements.filter(visible).map(el => {
      if (kind === 'inventory') return {id: el.id.slice('bitable-ssr-sidebar-item-'.length), name: el.textContent.trim()};
      if (kind === 'fields') return {name: el.querySelector('.bitable-field-name')?.textContent || null,
        typeIcon: el.querySelector('.bitable-field-icon svg')?.getAttribute('data-icon') || null};
      const r = el.getBoundingClientRect();
      const item = {id: el.getAttribute('data-id') || el.id || null, text: el.innerText,
        bounds: {x:r.x, y:r.y, width:r.width, height:r.height}, className: el.getAttribute('class')};
      if (kind !== 'widgets' && kind !== 'workflow_nodes') {
        item.controls = Array.from(el.querySelectorAll('input,textarea,select,[role="switch"],[role="checkbox"],[role="radio"]'))
          .filter(visible).map(control);
        // Keep row boundaries for exact field -> checkbox association. Never pair global arrays by index.
        item.permissionFields = Array.from(el.querySelectorAll('.bitable-perm-table-role-field-v2-item-desc-name')).map(name => {
          let row = name.parentElement;
          for (let n = 0; row && n < 4 && !row.querySelector('input,[role="checkbox"]'); n++) row = row.parentElement;
          const names = row?.querySelectorAll('.bitable-perm-table-role-field-v2-item-desc-name');
          return {name: name.textContent, rowText: names?.length === 1 ? row.innerText : null,
            controls: names?.length === 1 ? Array.from(row.querySelectorAll('input,[role="checkbox"]')).filter(visible).map(control) : [],
            association: names?.length === 1 ? 'single-field-row' : 'unresolved'};
        });
        if (kind === 'form') item.questions = Array.from(el.querySelectorAll('.base-form-container_card_item')).filter(visible).map(card => ({
          domId:card.id || null,
          title:card.querySelector('.base-form-container_title_wrapper')?.textContent?.trim() || null,
          titleClass:card.querySelector('.base-form-container_title_wrapper')?.getAttribute('class') || null,
          ordinal:card.querySelector('.base-form-container_number_content')?.textContent || null,
          requiredMarker:Array.from(card.querySelectorAll('.base-form-container_red_star')).some(visible),
          valueText:card.querySelector('.base-form-container_value_wrapper')?.innerText || '',
          evidenceMeaning:'rendered title/order/star/options only; not backend schema or validation'
        }));
      }
      return item;
    });
  }
  async function collect(tab, req) {
    if (!kinds.includes(req?.kind)) throw new Error('Unknown kind');
    await guard(tab, req);
    need(req.object, 'object description');
    need(req.expectedText, 'expectedText from fresh UI');
    // Even lists require a verified active container; inactive retained DOM must not leak into evidence.
    need(req.scopeSelector, 'scopeSelector from observed DOM');
    if (/(^|[\s,>+~])(body|html|\*)(?=$|[\s,.#:[>+~])/i.test(req.scopeSelector))
      throw new Error('Use an active component container, not a whole-page scope');
    const root = await one(tab.playwright.locator(req.scopeSelector));
    const rootText = await root.innerText();
    if (!rootText.includes(req.expectedText) || /加载中|Loading\.\.\./i.test(rootText))
      throw new Error('Scope is stale, mismatched, or still loading');
    // evaluateAll also covers a single root without evaluating source strings.
    const rows = await (selectors[req.kind] ? root.locator(selectors[req.kind]) : root).evaluateAll(extract, req.kind);
    await guard(tab, req);
    const gaps = limitations[req.kind].map(code => ({code, status:'unverified', reason:'Not established by this Chrome capture'}));
    if (!rows.length) gaps.push({code:'empty_scope', status:'missing', reason:'Empty DOM is not proof of absent product'});
    if (rows.some(r => r.permissionFields?.some(f => f.association !== 'single-field-row')))
      gaps.push({code:'permission_row_association', status:'missing', reason:'Field/control mapping unresolved'});
    if (rows.some(r => r.permissionFields?.some(f => !f.controls.length || f.controls.some(c => !c.label || c.checked === null))))
      gaps.push({code:'permission_control_semantics', status:'missing', reason:'Permission labels or states unresolved'});
    if (req.kind === 'form' && rows.some(r => !r.questions?.length || r.questions.some(q => !q.title || !q.ordinal)))
      gaps.push({code:'form_question_structure', status:'missing', reason:'Question structure incomplete; preserve raw text for inspection'});
    return {adapter:'doubao-eval-chrome', version, capturedAt:new Date().toISOString(), url:req.expectedUrl,
      object:req.object, kind:req.kind, scopeSelector:req.scopeSelector, expectedText:req.expectedText,
      identityCheck:'operator-confirmed; not independent authentication', status:'partial',
      captureStatus:rows.length ? 'captured' : 'empty', data:rows, evidenceGaps:gaps,
      scoring:'requires_query_requirement_review; never infer pass from capture',
      coverage:'current mounted scope only; not a transactional or whole-product snapshot'};
  }
  // One allowlisted UI action per invocation. Caller must inspect returned state before the next action.
  async function open(tab, req) {
    const actions = ['object','fields','field_menu','field_edit','field_cancel','chart_menu','chart_config',
      'workflow_step','share','permissions','permission_target','permission_close','form_editor','form_settings'];
    if (!actions.includes(req?.action)) throw new Error('Action not allowlisted');
    await guard(tab, req);
    const p = tab.playwright;
    let target;
    switch (req.action) {
      case 'object':
        if (!/^[A-Za-z0-9]+$/.test(req.id || '')) throw new Error('Invalid observed object ID');
        target = p.locator('#bitable-ssr-sidebar-item-' + req.id); break;
      case 'fields': target = p.getByText('字段配置',{exact:true}); break;
      case 'field_menu': target = p.locator('.bitable-field-panel-list-item')
        .filter({has:p.getByText(need(req.name,'field name'),{exact:true})}).locator('button.more-icon'); break;
      case 'field_edit': target = p.getByRole('menu').getByText('编辑',{exact:true}); break;
      case 'field_cancel': target = p.getByRole('button',{name:'取消',exact:true}); break;
      case 'chart_menu':
        if (!/^[A-Za-z0-9]+$/.test(req.id || '')) throw new Error('Invalid observed widget ID');
        target = p.locator('.layout-item[data-id="' + req.id + '"] .dashboard-grid-menu-button'); break;
      case 'chart_config': target = p.getByRole('menuitem',{name:'配置',exact:true}); break;
      case 'workflow_step': target = p.locator(selectors.workflow_nodes).getByText(need(req.name,'node name'),{exact:true}); break;
      case 'share': target = p.getByRole('button',{name:'分享',exact:true}); break;
      case 'permissions': target = p.locator('.base__share-permission-entry-action'); break;
      case 'permission_target': target = p.getByRole('dialog')
        .locator('.bitable-perm-v2-role-menu-text-name, .base-perm__block-menu-item__start__title')
        .and(p.getByText(need(req.name,'role or table'),{exact:true})); break;
      case 'permission_close': target = p.getByRole('dialog').getByRole('button')
        .filter({has:p.locator('svg[data-icon="CloseOutlined"]')}); break;
      case 'form_editor': target = p.getByRole('button',{name:'编辑问卷',exact:true}); break;
      case 'form_settings': target = p.locator('.base-form-header-setting-btn'); break;
    }
    await (await one(target)).click({timeoutMs:5000});
    return {action:req.action, url:await tab.url(), snapshot:await p.domSnapshot(),
      note:'Inspect resulting state; action success does not prove panel ready. No automatic retries.'};
  }
  function reviewCoverage(evidence, requirements) {
    if (!Array.isArray(requirements) || !requirements.length) throw new Error('Explicit Query evidence requirements needed');
    if (requirements.some(r => !r || !r.object || !r.kind || !r.capability)) throw new Error('Each requirement needs object, kind, capability');
    const missing = requirements.filter(r => !evidence.some(e => e.kind === r.kind && e.object === r.object &&
      capabilities[e.kind] === r.capability && e.captureStatus === 'captured' && !e.evidenceGaps.some(g => g.code === r.capability)));
    // This is a retrieval checklist, NOT an automatic scoring authorization.
    return {status:missing.length ? 'evidence_gaps' : 'needs_semantic_review', missing,
      mayAutoScore:false, reason:'Matching captures cannot establish Query compliance or full coverage'};
  }
  return {version, kinds, capabilities, limitations, collect, open, reviewCoverage};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = doubaoChrome;
