---
name: tencent-smartsheet-location-fill-from-md
description: Use when the user wants to take a Markdown address list, usually `姓名-地址` lines, and fill a Tencent Docs Smart Sheet map/location column through the browser. Handles exported address Markdown, location-picker cells, candidate selection, per-row verification, and recovery from missed rows. NOT for ordinary text columns, direct API imports, Lark Base editing, or spreadsheet analysis.
---
# Tencent Smartsheet Location Fill From Markdown

Fill a Tencent Docs Smart Sheet location/map field from a Markdown list. This is an external write workflow: be slow, visible, and verify each batch.

## Fit Gate

Use this skill when all are true:

- The source is a local Markdown/text list with one record per line, commonly `name-address`.
- The destination is Tencent Docs Smart Sheet in a browser.
- The target column uses a location/map picker that requires typing a place, choosing a suggestion, and confirming.

Do not use this skill for:

- Plain text paste into a normal spreadsheet column.
- Lark Base or Feishu Base writeback; use the Lark Base skills instead.
- Bulk import through official APIs or CSV when the user has asked for browser-driven location picking.

## Inputs

Minimum inputs:

- Source Markdown file path.
- Destination Tencent Smart Sheet URL or an already-open Ego browser task space.
- Target table/view and the destination location column.
- Row matching rule, usually current visible order matching the Markdown order.

If row order is not explicitly confirmed, verify the first visible rows against names or stable adjacent fields before writing. If there is no reliable row match, stop and ask.

## Source Preparation

Parse only useful data lines:

- Ignore headings, blank lines, and comments.
- Split each line on the first ASCII hyphen `-`.
- Left side is the row label/name; right side is the address query.
- If an address came from a richer location value, keep only the positioning address before `,` or `，` unless the user asks to include the precise address.

Prefer adding city or nearby precise context to the map search query when the plain positioning address is ambiguous. Do not write that extra context into a normal text cell; it is only for map search.

## Browser Setup

Use `ego-browser` for Tencent Docs.

- Use one task space for the whole job.
- Reuse the current page if the user has already opened the sheet.
- For canvas-backed sheets, use screenshots and coordinates only to select cells and scroll.
- Use semantic selectors inside the map picker whenever they exist.

Before writing, take a screenshot and identify:

- The current visible row numbers.
- The x/y area of the location column cells.
- The vertical spacing between rows.
- Whether any target rows are already filled.

## Filling Strategy

Default strategy:

1. Work in small visible batches.
2. For each row, click the location cell or its dropdown affordance to open the map picker.
3. Fill `input[placeholder="输入地点"]` with the address query.
4. Wait for suggestions.
5. Click the first suggestion from the map-picker suggestion container.
6. Click the current map-picker `确定` button by semantic ref/text, never by a fixed screen coordinate.
7. Wait for the picker to close and the cell to show a value.
8. Screenshot after each batch.

Critical guardrails:

- Never use one fixed coordinate for `确定`; the map picker moves with the cell and fixed coordinates miss silently.
- Do not choose the first `menuitem` on the whole page. Tencent Docs also has view/table menus. Choose the first suggestion only from the address suggestion popup that appears after typing.
- If a row fails, inspect the current screenshot/snapshot before retrying. Do not continue assuming it wrote.
- Keep one overlapping row when scrolling so row order stays anchored.
- If a candidate list does not appear, retry with more context such as city, district, street, or original precise-address fragment.

Useful Ego selector patterns:

```js
await page.waitForSelector('loc=css:input[placeholder="输入地点"]', {
  state: "visible",
  timeout: 5000,
});
await page.fill('loc=css:input[placeholder="输入地点"]', query);
```

Find the current popup confirm button from the latest snapshot:

```js
const snap = await page.snapshot();
const confirmRefs = [...snap.matchAll(/button \[ref=(\d+)\]\n\s+text "确定"/g)].map((m) => m[1]);
if (!confirmRefs.length) throw new Error("no popup confirm");
await page.click("@" + confirmRefs[confirmRefs.length - 1], { label: "confirm popup" });
```

Find the first address suggestion from the popup, not page-level menus:

```js
const snap = await page.snapshot();
const match = snap.match(/container \[ref=\d+\]\n\s+menu(?: \[ref=\d+\])?\n\s+menuitem \[ref=(\d+)\]/);
if (!match) throw new Error("no address suggestion");
await page.click("@" + match[1], { label: "choose address suggestion" });
```

## Verification

Minimum verification:

- Screenshot each completed visible batch.
- Confirm every intended row in the batch shows a non-empty location cell.
- At the end, return control to the user for visual review.

When a user reports a missed row:

1. Navigate back to the row range.
2. Screenshot before changing anything.
3. Explain the root cause if observable.
4. Refill only the missed row(s) using semantic popup controls.
5. Screenshot after the fix.

## Stop Conditions

Stop and ask the user when:

- The destination row order cannot be matched to the Markdown list.
- A permission/login prompt appears.
- The map picker suggestions are missing or clearly wrong after adding context.
- The sheet changes under you or another collaborator edits the same rows.
- The user takes control of the Ego task space.

## Evaluation Cases

Positive triggers:

- "根据这个 `姓名-地址` md，把腾讯文档智能表格的通讯地址批量填入。"
- "打开这个 smart sheet，把导出的地址清单填到定位地址字段。"

Negative triggers:

- "把 Markdown 转成 CSV。"
- "把地址写回飞书 Base。"
- "分析这张表有多少城市。"

Hard negatives:

- A normal text column named address: paste values directly instead of opening map pickers.
- A Lark/Feishu Base location field: use Lark Base tooling, not Tencent Docs browser automation.
