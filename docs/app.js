/* SciPIvot landing interactions */
(() => {
  "use strict";

  /* ---------------- case data (condensed from the benchmark) ---------------- */
  const CASES = {
    scorer: {
      domain: "AI & MACHINE LEARNING",
      title: "Scale the model — or check the scorer?",
      context: "A project is building an evaluation set with difficulty levels for a 0.8B model. Three LiveCodeBench groups score 0 / 480. A project note claims earlier checks ruled out an evaluation fault.",
      evidence: [
        ["Observed", "0.8B model scores 0 on three code groups"],
        ["Claim in notes", "Earlier checks ruled out an evaluation fault"],
        ["Unverified", "Whether the scorer extracts answers at all"],
      ],
      image: "assets/case-scorer.svg",
      imageAlt: "Schematic of an evaluation pipeline where the grader skips answer extraction",
      a: { title: "Scale up the model.", body: "Trust the note. Retest with a 2B model, keeping the tasks and the scorer." },
      b: { title: "Audit the scorer.", body: "Keep 0.8B. Check and fix the scorer's answer extraction, regrade, and add official tasks." },
      correct: "b",
      verdict: "The note's claim was unverified. The scorer had skipped answer extraction, so the zeros measured the grader rather than the model. Changing model size with the same scorer would have left the error in place.",
    },
    cloth: {
      domain: "MECHANICS & MATERIALS",
      title: "Search harder — or question the restriction?",
      context: "A cloth simulator is being calibrated against recorded motion. Four of six parameters are fixed at zero in every run, and the best fits of the other two sit at the search limits.",
      evidence: [
        ["Observed", "Best fits of both free parameters hit the box walls"],
        ["History", "Four parameters fixed at zero in every earlier run"],
        ["Unverified", "Whether the zeros were ever measured, or only chosen"],
      ],
      image: "assets/case-cloth.svg",
      imageAlt: "Schematic of six parameter dials with four locked at zero and two pinned at the search limits",
      a: { title: "Refine the two-parameter search.", body: "Keep the four at zero, as in every earlier run, and search the other two more densely." },
      b: { title: "Fit all six parameters.", body: "Reopen the full fit around the defaults and compare it with the two-parameter slice on the same objective." },
      correct: "b",
      verdict: "The zeros were the agent's own earlier choice, repeated until they looked like a rule. Nothing had ever measured them. Missing fitted values do not justify setting physical parameters to zero.",
    },
    simulator: {
      domain: "ROBOTICS & SIMULATION",
      title: "A finding — or a simulator bug?",
      context: "A pretrained robot policy shows joint-limit violations in a new MuJoCo simulator. The project is still validating the environment, including its rigid reference. An early comparison has only eight qualified poses.",
      evidence: [
        ["Policy", "Pretrained, frozen"],
        ["Simulator", "MuJoCo, newly adopted"],
        ["Qualified poses", "8"],
        ["Unresolved issue", "Joint-limit violations"],
      ],
      image: "assets/case-simulator.svg",
      imageAlt: "Schematic of a robot joint limit with an unresolved simulator compatibility check",
      a: { title: "Expand the pose pool.", body: "Repeat the comparison with more poses to increase statistical power for studying the apparent policy degradation." },
      b: { title: "Validate the simulator first.", body: "Keep the policy frozen. Check joint limits, contacts, and timestep on a rigid reference before interpreting soft-support results." },
      correct: "b",
      verdict: "More samples cannot establish that an unvalidated runtime's behavior is a scientific finding. The reference plan first isolates the simulator — validate before interpreting.",
    },
  };

  /* ---------------- results grid (paper Table 9: Project / Options only) ---------------- */
  const EFFORTS = ["low", "medium", "high", "xhigh", "max"];
  const MODELS = [
    { name: "GPT-6 Astra", sym: "A", project: [57.7, 59.5, 62.1, 63.5, 63.1], options: [64.5, 63.7, 64.9, 64.5, 62.7], best: "63.5 · xhigh" },
    { name: "Claude Opus 5", sym: "O", project: [40.5, 38.9, 43.3, 46.0, 46.8], options: [59.5, 58.9, 59.1, 58.9, 57.9], best: "46.8 · max" },
    { name: "Grok 4.6", sym: "G", project: [32.1, 33.1, 38.1, 33.3, 33.1], options: [53.8, 54.0, 55.8, 56.5, 53.4], best: "38.1 · high" },
    { name: "GPT-5.6 Sol", sym: "S", project: [36.1, 35.1, 35.9, 28.0, 29.2], options: [54.4, 46.8, 54.2, 53.8, 55.8], best: "37.7 · med + review 2" },
    { name: "GPT-5.6 Terra", sym: "T", project: [31.7, 29.2, 30.4, 30.2, 34.9], options: [56.5, 55.8, 55.4, 55.6, 57.3], best: "52.0 · med + review 1" },
  ];
  const ARM_LABEL = { project: "With project", options: "Options only" };

  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  /* ---------------- reveal on scroll ---------------- */
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((node) => io.observe(node));

  /* ---------------- mobile menu ---------------- */
  const toggle = document.querySelector(".menu-toggle");
  const nav = $("main-nav");
  toggle?.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  nav?.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => nav.classList.remove("open")));

  /* ---------------- case tabs + answer flow ---------------- */
  const tabs = [...document.querySelectorAll(".case-tabs button")];
  const panel = $("case-panel");
  const result = $("answer-result");
  const revealBtn = $("reveal-answer");
  const resetBtn = $("reset-case");
  let current = "scorer";
  let picked = null;

  function renderCase(key) {
    current = key;
    picked = null;
    const c = CASES[key];
    $("case-domain").textContent = c.domain;
    $("case-title").textContent = c.title;
    $("case-context").textContent = c.context;

    const dl = $("case-evidence");
    dl.replaceChildren(...c.evidence.map(([k, v]) => {
      const row = el("div");
      row.append(el("dt", null, k), el("dd", null, v));
      return row;
    }));

    const img = $("case-image");
    img.src = c.image;
    img.alt = c.imageAlt;
    $("answer-a-title").textContent = c.a.title;
    $("answer-a-body").textContent = c.a.body;
    $("answer-b-title").textContent = c.b.title;
    $("answer-b-body").textContent = c.b.body;

    document.querySelectorAll(".answer").forEach((btnEl) => {
      btnEl.classList.remove("is-correct", "is-wrong");
      btnEl.setAttribute("aria-pressed", "false");
    });
    result.hidden = true;
    result.classList.remove("wrong");
    result.replaceChildren();
    revealBtn.disabled = true;
    revealBtn.hidden = false;
    resetBtn.hidden = true;
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => { t.setAttribute("aria-selected", "false"); t.tabIndex = -1; });
      tab.setAttribute("aria-selected", "true");
      tab.tabIndex = 0;
      panel.setAttribute("aria-labelledby", tab.id);
      renderCase(tab.dataset.case);
    });
    tab.addEventListener("keydown", (e) => {
      const i = tabs.indexOf(tab);
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
        next.focus();
        next.click();
      }
    });
  });

  document.querySelectorAll(".answer").forEach((btn) => {
    btn.addEventListener("click", () => {
      picked = btn.dataset.answer;
      document.querySelectorAll(".answer").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      revealBtn.disabled = false;
    });
  });

  revealBtn?.addEventListener("click", () => {
    const c = CASES[current];
    const isRight = picked === c.correct;
    document.querySelectorAll(".answer").forEach((b) => {
      if (b.dataset.answer === c.correct) b.classList.add("is-correct");
      else if (b.dataset.answer === picked) b.classList.add("is-wrong");
    });
    result.hidden = false;
    result.classList.toggle("wrong", !isRight);
    result.replaceChildren(
      el("strong", null, isRight ? "The senior researcher agreed." : "The senior researcher went the other way."),
      document.createTextNode(c.verdict),
    );
    revealBtn.hidden = true;
    resetBtn.hidden = false;
  });

  resetBtn?.addEventListener("click", () => {
    const order = Object.keys(CASES);
    const next = order[(order.indexOf(current) + 1) % order.length];
    const tab = tabs.find((t) => t.dataset.case === next);
    tab.click();
    tab.focus();
    $("cases")?.scrollIntoView({ block: "start" });
  });

  /* ---------------- results table ---------------- */
  let arm = "project";
  let effort = "medium";

  function renderResults() {
    const ei = EFFORTS.indexOf(effort);
    const rows = MODELS.map((m) => {
      const score = m[arm][ei];
      const meter = el("div", "meter");
      const fill = el("span", "meter-fill");
      fill.style.setProperty("--w", `${score}%`);
      const chance = el("span", "chance");
      chance.style.left = "50%";
      chance.setAttribute("aria-hidden", "true");
      meter.append(fill, chance);

      const tr = el("tr");
      const th = el("th");
      th.scope = "row";
      th.append(el("span", "model-symbol", m.sym), document.createTextNode(m.name));
      const tdMeter = el("td");
      tdMeter.append(meter);
      tr.append(th, tdMeter, el("td", "score-cell", `${score.toFixed(1)}%`), el("td", "best-cell", m.best));
      return tr;
    });
    $("result-rows").replaceChildren(...rows);
    const mean = MODELS.reduce((s, m) => s + m[arm][ei], 0) / MODELS.length;
    $("result-summary").textContent =
      `${ARM_LABEL[arm]} · ${effort} effort · five-model mean ${mean.toFixed(1)}%.`;
  }

  document.querySelectorAll(".segmented button").forEach((b) => {
    b.addEventListener("click", () => {
      arm = b.dataset.arm;
      document.querySelectorAll(".segmented button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      renderResults();
    });
  });
  document.querySelectorAll(".effort-picker button").forEach((b) => {
    b.addEventListener("click", () => {
      effort = b.dataset.effort;
      document.querySelectorAll(".effort-picker button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      renderResults();
    });
  });
  renderResults();

  /* ---------------- copy buttons ---------------- */
  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const pre = $(btn.dataset.copy);
      const label = btn.querySelector("span");
      try {
        await navigator.clipboard.writeText(pre.innerText);
        label.textContent = "Copied";
      } catch {
        label.textContent = "Press Ctrl+C";
      }
      setTimeout(() => { label.textContent = "Copy"; }, 1600);
    });
  });
})();
