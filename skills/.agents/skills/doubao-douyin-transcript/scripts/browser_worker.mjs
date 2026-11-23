// Runs in the agent's cua_repl with an existing, authorized Chrome Tab.
// No Playwright import, browser launch, cookie extraction or raw network calls.
const INPUT = '[contenteditable="true"],textarea';

export async function prepare(tab, request) {
  if (new URL(await tab.url()).hostname !== 'www.doubao.com') throw Error('WRONG_SITE');
  const before = await tab.playwright.evaluate(() => ({
    sent: document.querySelectorAll('[data-testid="send_message"]').length,
    received: document.querySelectorAll('[data-testid="receive_message"]').length,
    inputs: Array.from(document.querySelectorAll('[contenteditable="true"],textarea'))
      .filter(e => e.getClientRects().length).map(e => e.tagName === 'TEXTAREA' ? e.value : e.innerText)
  }));
  if (before.sent || before.received) throw Error('NEW_CONVERSATION_REQUIRED');
  if (before.inputs.length !== 1) throw Error('INPUT_NOT_READY_OR_AMBIGUOUS');
  if (before.inputs[0].trim()) throw Error('EXISTING_DRAFT');
  await tab.playwright.locator(INPUT).fill(request.prompt);
  const actual = await tab.playwright.locator(INPUT).evaluate(e => e.tagName === 'TEXTAREA' ? e.value : e.innerText);
  if (actual.replace(/\s+/g, ' ').trim() !== request.prompt.replace(/\s+/g, ' ').trim()) throw Error('PROMPT_NOT_FILLED');
  return {request, prepared_at: new Date().toISOString(), phase: 'prepared'};
}

export async function submit(tab, job) {
  if (job.phase !== 'prepared') throw Error('ALREADY_SUBMITTED_OR_NOT_PREPARED');
  const actual = await tab.playwright.locator(INPUT).evaluate(e => e.tagName === 'TEXTAREA' ? e.value : e.innerText);
  if (actual.replace(/\s+/g, ' ').trim() !== job.request.prompt.replace(/\s+/g, ' ').trim()) throw Error('DRAFT_CHANGED');
  // Set state before dispatch: an uncertain outcome must never auto-resubmit.
  job.phase = 'submitted';
  job.submitted_at = new Date().toISOString();
  await tab.playwright.locator(INPUT).press('Enter');
  return await poll(tab, job);
}

export async function poll(tab, job) {
  const state = await tab.playwright.evaluate(() => {
    const sent = Array.from(document.querySelectorAll('[data-testid="send_message"]'));
    const received = Array.from(document.querySelectorAll('[data-testid="receive_message"]'));
    const answer = received.at(-1);
    const text = answer?.querySelector('[data-testid="message_text_content"]')?.innerText || '';
    const wholeTurn = answer?.closest('[data-testid="union_message"]');
    return {
      conversation_url: location.href,
      sent_count: sent.length,
      sent_text: sent.at(-1)?.innerText || '',
      received_count: received.length,
      raw_response: text,
      // A regenerate control belongs to a completed response, unlike copy which
      // can be present while tokens are streaming. Scope to this response only.
      completion_control: !!wholeTurn?.querySelector('[data-testid="message_action_regenerate"]'),
      sources: Array.from(answer?.querySelectorAll('a') || [])
        .map(e => ({text: e.innerText, url: e.href})),
      input: document.querySelector('[contenteditable="true"],textarea')?.innerText || ''
    };
  });
  if (state.sent_count > 1 || state.received_count > 1) throw Error('CONVERSATION_CHANGED');
  const promptMatches = state.sent_text.replace(/\s+/g, ' ').includes(job.request.prompt.replace(/\s+/g, ' '));
  if (state.sent_count && !promptMatches) throw Error('PROMPT_MISMATCH');
  const unchanged = job.last_text === state.raw_response;
  job.last_text = state.raw_response;
  const now = Date.now();
  if (!unchanged) job.last_change_ms = now;
  const stable = unchanged && now - (job.last_change_ms || now) >= 2000;
  const complete = state.sent_count === 1 && state.received_count === 1 &&
    state.completion_control && stable;
  job.phase = complete ? 'complete' : 'submitted';
  const capture = {
    ...state, request: job.request, submitted_at: job.submitted_at,
    captured_at: new Date().toISOString(),
    elapsed_upper_bound_seconds: (now - Date.parse(job.submitted_at)) / 1000,
    complete, prompt_matches: promptMatches
  };
  job.capture = capture;
  return {complete, phase: job.phase, received_characters: state.raw_response.length,
    sent_count: state.sent_count, completion_control: state.completion_control,
    elapsed_upper_bound_seconds: capture.elapsed_upper_bound_seconds,
    conversation_url: state.conversation_url};
}

export async function save(job, path) {
  if (!job.capture) throw Error('NO_CAPTURE');
  const fs = await import('node:fs/promises');
  // Preserve existing captures; each run needs a separate path.
  await fs.writeFile(path, JSON.stringify(job.capture, null, 2) + '\n', {flag: 'wx', mode: 0o600});
  return {path, complete: job.capture.complete};
}
