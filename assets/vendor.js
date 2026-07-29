(function () {
  "use strict";
  const E = window.CrewScoreEngine;
  if (!E) return;
  const answers = new Array(E.vendorQuestions.length).fill(null);
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value || "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[c]);
  const questions = $("vendor-questions");
  questions.innerHTML = E.vendorQuestions.map((question, index) => `<fieldset class="gap" style="margin-top:14px"><legend><strong>${index + 1}. ${esc(question)}</strong></legend><label><input type="radio" name="vendor-${index}" value="yes"> Yes</label><label><input type="radio" name="vendor-${index}" value="dk"> Don't know</label><label><input type="radio" name="vendor-${index}" value="no"> No</label></fieldset>`).join("");
  questions.querySelectorAll("input[type=radio]").forEach((input) => input.addEventListener("change", () => { answers[Number(input.name.replace("vendor-", ""))] = input.value; }));
  $("score-vendor").addEventListener("click", () => {
    const missing = answers.filter((answer) => !answer).length;
    if (missing) { $("vendor-result").innerHTML = `<p class="warning">Answer all ${answers.length} questions before summarizing.</p>`; return; }
    const positive = answers.filter((answer) => answer === "yes").length;
    const unknown = answers.filter((answer) => answer === "dk").length;
    const name = esc($("vendor-name").value.trim() || "This vendor");
    $("vendor-result").innerHTML = `<div class="coverage-disclosure"><strong>${name}:</strong> ${positive} of ${answers.length} answers are positive; ${unknown} need follow-up. This is a self-attested conversation summary, not a vendor grade or audit.</div>`;
    window.CrewScoreAnalytics?.capture("cs_vendor_open", { kind: "summary" });
  });
})();
