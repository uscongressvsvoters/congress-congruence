// "Find your members by ZIP code", on any element with data-zip-finder.
//
// Privacy: the ZIP code never leaves the reader's browser. The page downloads one file that is the
// same for every visitor (members/zip-districts.json: each ZIP code area and its congressional
// districts, from the Census Bureau) and looks the ZIP code up in it. Only the state found is then
// asked for (the state's current members, as the state pages ask), never the ZIP code.
(() => {
  const boxes = document.querySelectorAll("[data-zip-finder]");
  if (!boxes.length) return;
  const API = "/api";
  const HOUSE_LOOKUP = "https://www.house.gov/representatives/find-your-representative";
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) if (v != null && v !== false) n.setAttribute(k, v);
    for (const k of kids.flat(Infinity)) if (k != null && k !== false) n.append(k instanceof Node ? k : String(k));
    return n;
  };
  const nameTag = n => (n || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const memberHref = m => `index.html#${m.state}/${m.bioguide_id}_${nameTag(m.name)}`;
  const seatName = (st, d) => `${st}-${d === 0 ? "AL" : d}`;
  const tel = p => { const d = p.replace(/\D/g, "").slice(-10); return d.length === 10 ? `tel:+1${d}` : null; };

  let zipFile;
  // About 600 KB as JSON; the gzip copy is about a quarter of that, unpacked here where browsers can.
  const zips = () => zipFile ||= ("DecompressionStream" in window
      ? fetch("members/zip-districts.json.gz").then(r => {
          if (!r.ok) throw new Error(r.status);
          return new Response(r.body.pipeThrough(new DecompressionStream("gzip"))).json();
        })
      : Promise.reject())
    .catch(() => fetch("members/zip-districts.json").then(r => r.ok ? r.json() : null))
    .catch(() => null);
  const stateMembers = {};
  const membersOf = st => stateMembers[st] ||= fetch(`${API}/v1/members?state=${st}&contact=true`)
    .then(r => r.ok ? r.json() : { members: [] }).then(d => d.members).catch(() => []);

  function contactLine(m) {
    const c = m.contact || {};
    const bits = [];
    if (c.phone) bits.push(tel(c.phone) ? el("a", { href: tel(c.phone) }, c.phone) : c.phone);
    if (c.contact_form) bits.push(el("a", { href: c.contact_form, rel: "noopener" }, "Email (contact form)"));
    if (c.website) bits.push(el("a", { href: c.website, rel: "noopener" }, "Website"));
    return bits.length ? el("span", { class: "zf-contact" }, bits.flatMap((b, i) => i ? [" · ", b] : [b])) : null;
  }
  function memberItem(m, note) {
    const role = m.chamber === "senate" ? `Senator, ${m.state}` : `Representative, ${m.seat}`;
    return el("li", {},
      el("a", { href: memberHref(m), class: "zf-name" }, m.name), " ",
      el("span", { class: "zf-role" }, role, note ? ` (${note})` : ""),
      el("br"), contactLine(m));
  }

  async function find(zip, out) {
    out.replaceChildren(el("p", { class: "zf-status" }, "Looking up…"));
    const data = await zips();
    if (!data || !data.zips) {
      out.replaceChildren(el("p", {}, "The ZIP code lookup isn't available right now. Pick your state below, or use ",
        el("a", { href: HOUSE_LOOKUP, rel: "noopener" }, "the House's lookup by address"), "."));
      return;
    }
    const parts = data.zips[zip];
    if (!parts) {
      out.replaceChildren(el("p", {}, `No match for ${zip}. Some ZIP codes, such as P.O. boxes and single buildings, `,
        "have no area of their own. Try the ZIP code where you live, pick your state, or use ",
        el("a", { href: HOUSE_LOOKUP, rel: "noopener" }, "the House's lookup by full address"), "."));
      return;
    }
    const states = [...new Set(parts.map(p => p[0]))];
    const lists = await Promise.all(states.map(membersOf));
    const kids = [];
    states.forEach((st, i) => {
      const members = lists[i];
      const senators = members.filter(m => m.chamber === "senate");
      const reps = parts.filter(p => p[0] === st).map(([, d, share]) =>
        [members.find(m => m.chamber === "house" && (m.district || 0) === d), d, share]);
      const items = [...senators.map(m => memberItem(m)),
                     ...reps.map(([m, d, share]) => m ? memberItem(m, reps.length > 1 ? `about ${share}% of this ZIP code` : "")
                       : el("li", {}, `${seatName(st, d)}: seat currently vacant`))];
      kids.push(el("ul", { class: "zf-members" }, items));
    });
    const split = parts.length > 1;
    kids.unshift(el("p", { class: "zf-head" }, split
      ? `ZIP code ${zip} crosses district lines (${parts.map(p => seatName(p[0], p[1])).join(", ")}). `
        + (states.length > 1 ? "It also crosses a state line, so your senators depend on your address too:"
                             : "Your senators are the same; your representative depends on your address:")
      : `ZIP code ${zip} is in ${seatName(parts[0][0], parts[0][1])}. Your members of Congress:`));
    kids.push(el("p", { class: "zf-note" },
      split ? "To be sure which district you're in, use " : "ZIP codes don't follow district lines exactly. To check by address, use ",
      el("a", { href: HOUSE_LOOKUP, rel: "noopener" }, "the House's lookup"), ". District lines as of the ",
      `${data.congress}th Congress.`));
    out.replaceChildren(...kids);
  }

  for (const box of boxes) {
    const id = `zf-${Math.random().toString(36).slice(2, 8)}`;
    const input = el("input", { id, type: "text", inputmode: "numeric", autocomplete: "postal-code", maxlength: "5",
                               pattern: "[0-9]{5}", placeholder: "e.g. 77378", "aria-describedby": `${id}-privacy` });
    const out = el("div", { class: "zf-out", "aria-live": "polite" });
    const form = el("form", { class: "zf-form" },
      el("label", { for: id }, "Your ZIP code"), input, el("button", { type: "submit" }, "Find my members"));
    form.addEventListener("submit", e => {
      e.preventDefault();
      const zip = input.value.replace(/\D/g, "");
      if (zip.length !== 5) { out.replaceChildren(el("p", {}, "Enter a 5-digit ZIP code.")); input.focus(); return; }
      find(zip, out);
    });
    box.replaceChildren(form,
      el("p", { class: "zf-privacy", id: `${id}-privacy` },
        "Your ZIP code stays on your device: it's looked up in a file every visitor gets, and never sent to this site."),
      out);
  }
})();
