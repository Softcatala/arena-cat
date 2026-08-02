const apiBaseInput = document.querySelector("#apiBase");
const categoryInput = document.querySelector("#category");
const loadTaskButton = document.querySelector("#loadTask");
const promptOutput = document.querySelector("#prompt");
const responseAOutput = document.querySelector("#responseA");
const responseBOutput = document.querySelector("#responseB");
const statusOutput = document.querySelector("#status");
const voteButtons = [...document.querySelectorAll("[data-winner]")];

const authPanel = document.querySelector("#authPanel");
const sessionBar = document.querySelector("#sessionBar");
const sessionInfo = document.querySelector("#sessionInfo");

const registerEmail = document.querySelector("#registerEmail");
const registerPassword = document.querySelector("#registerPassword");
const registerConsent = document.querySelector("#registerConsent");
const registerButton = document.querySelector("#registerButton");
const registerResult = document.querySelector("#registerResult");

const loginEmail = document.querySelector("#loginEmail");
const loginPassword = document.querySelector("#loginPassword");
const loginButton = document.querySelector("#loginButton");
const loginResult = document.querySelector("#loginResult");

const logoutButton = document.querySelector("#logoutButton");
const exportButton = document.querySelector("#exportButton");
const deleteButton = document.querySelector("#deleteButton");
const deleteConfirm = document.querySelector("#deleteConfirm");
const deletePassword = document.querySelector("#deletePassword");
const deleteConfirmButton = document.querySelector("#deleteConfirmButton");
const deleteCancelButton = document.querySelector("#deleteCancelButton");

let currentToken = null;
let loggedIn = false;

if (apiBaseInput.value === "http://127.0.0.1:8000" && window.location.hostname === "localhost") {
  apiBaseInput.value = "http://localhost:8000";
}

function parseApiBase() {
  try {
    return new URL(apiBaseInput.value);
  } catch {
    return null;
  }
}

function hostFamily(hostname) {
  if (hostname === "localhost") {
    return "localhost";
  }
  if (hostname === "::1" || hostname === "[::1]") {
    return "::1";
  }
  if (hostname.startsWith("127.")) {
    return "127";
  }
  return hostname;
}

function cookieSetupHint() {
  const apiBase = parseApiBase();
  if (!apiBase) {
    return "L'URL de l'API no és vàlida.";
  }

  if (window.location.protocol === "file:") {
    return "Serveix el client amb `make http`; amb `file://` el navegador no envia la cookie de sessió.";
  }

  const pageHost = window.location.hostname;
  const apiHost = apiBase.hostname;
  if (hostFamily(pageHost) !== hostFamily(apiHost)) {
    return (
      `La pàgina s'ha obert amb ${pageHost}, però l'API apunta a ${apiHost}. ` +
      "Usa sempre 127.0.0.1 amb 127.0.0.1, o localhost amb localhost."
    );
  }

  if (
    apiBase.protocol === "http:" &&
    !["localhost", "::1"].includes(apiHost) &&
    !apiHost.startsWith("127.")
  ) {
    return "Si uses HTTP fora de localhost/127.0.0.1, posa COOKIE_SECURE=false al `.env` i reinicia el backend.";
  }

  return "Comprova que no hi hagi una cookie antiga bloquejada al navegador i que el backend s'hagi reiniciat després de canviar el `.env`.";
}

function apiUrl(path) {
  return `${apiBaseInput.value.replace(/\/$/, "")}${path}`;
}

function setStatus(message, isError = false) {
  statusOutput.textContent = message;
  statusOutput.classList.toggle("error", isError);
}

function setCallResult(output, message, isError = false) {
  output.textContent = message;
  output.classList.toggle("error", isError);
}

function words(text) {
  return text.match(/\S+/g) || [];
}

function correctionOriginalText(prompt) {
  const newline = prompt.indexOf("\n");
  if (newline >= 0) {
    return prompt.slice(newline + 1).trim();
  }
  const colon = prompt.indexOf(":");
  return colon >= 0 ? prompt.slice(colon + 1).trim() : prompt.trim();
}

function diffWords(original, revised) {
  const source = words(original);
  const target = words(revised);
  const dp = Array.from({ length: source.length + 1 }, () => Array(target.length + 1).fill(0));

  for (let i = source.length - 1; i >= 0; i -= 1) {
    for (let j = target.length - 1; j >= 0; j -= 1) {
      dp[i][j] =
        source[i] === target[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const changes = [];
  let i = 0;
  let j = 0;
  while (i < source.length || j < target.length) {
    if (i < source.length && j < target.length && source[i] === target[j]) {
      changes.push({ type: "same", text: target[j] });
      i += 1;
      j += 1;
    } else if (j < target.length && (i === source.length || dp[i][j + 1] > dp[i + 1][j])) {
      changes.push({ type: "added", text: target[j] });
      j += 1;
    } else {
      changes.push({ type: "removed", text: source[i] });
      i += 1;
    }
  }
  return changes;
}

function appendWord(output, text, className = "") {
  if (output.childNodes.length > 0) {
    output.append(" ");
  }
  const node = className ? document.createElement("span") : document.createTextNode(text);
  if (className) {
    node.className = className;
    node.textContent = text;
  }
  output.append(node);
}

function renderResponse(output, prompt, response) {
  output.replaceChildren();
  if (categoryInput.value !== "correccio") {
    output.textContent = response;
    return;
  }

  diffWords(correctionOriginalText(prompt), response).forEach((change) => {
    const className =
      change.type === "added" ? "diff-added" : change.type === "removed" ? "diff-removed" : "";
    appendWord(output, change.text, className);
  });
}

function setVoteButtons(enabled) {
  voteButtons.forEach((button) => {
    button.disabled = !enabled;
  });
}

// Reflecteix l'estat d'autenticació a la interfície.
function setLoggedIn(isLoggedIn, options = {}) {
  loggedIn = isLoggedIn;
  authPanel.classList.toggle("hidden", isLoggedIn && !options.keepAuthPanel);
  sessionBar.classList.toggle("hidden", !isLoggedIn);
  loadTaskButton.disabled = !isLoggedIn;
  if (!isLoggedIn) {
    currentToken = null;
    setVoteButtons(false);
    promptOutput.textContent = "Cap tasca carregada.";
    responseAOutput.textContent = "-";
    responseBOutput.textContent = "-";
    hideDeleteConfirm();
  }
}

function formatHttpResult(status, data) {
  const body = data === null ? "(sense cos)" : JSON.stringify(data, null, 2);
  return `HTTP ${status}\n${body}`;
}

// Wrapper de fetch que sempre inclou la cookie de sessió i parseja el cos.
async function apiFetch(path, options = {}, resultOutput = null) {
  const response = await fetch(apiUrl(path), {
    credentials: "include",
    ...options,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (resultOutput) {
    setCallResult(resultOutput, formatHttpResult(response.status, data), !response.ok);
  }

  if (!response.ok) {
    const detail = (data && data.detail) || `HTTP ${response.status}`;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail);
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

// Distingeix 401 (cal iniciar sessió) i 403 (cal verificar el correu).
function handleAuthError(error) {
  if (error.status === 401) {
    setLoggedIn(false);
    setStatus(`Sessió invàlida o caducada. ${cookieSetupHint()}`, true);
  } else if (error.status === 403) {
    setStatus("Cal verificar el correu abans de continuar.", true);
  } else {
    setStatus(error.message, true);
  }
}

async function register() {
  setStatus("Registrant...");
  setCallResult(registerResult, "");
  try {
    const data = await apiFetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: registerEmail.value.trim(),
        password: registerPassword.value,
        consent: registerConsent.checked,
      }),
    }, registerResult);
    if (data.status === "pending_verification") {
      setStatus(
        "Registre correcte (pending_verification). Cal verificar el correu fora d'aquest client abans d'iniciar sessió.",
      );
    } else {
      setStatus(`Registre correcte (${data.status}). Ja pots iniciar sessió.`);
    }
  } catch (error) {
    if (!error.status) {
      setCallResult(registerResult, `Error de xarxa/CORS\n${error.message}`, true);
    }
    setStatus(error.message, true);
  }
}

async function ensureSessionCookieWorks() {
  try {
    await apiFetch("/api/auth/session");
  } catch (error) {
    if (error.status === 401) {
      const cookieError = new Error(
        `El login ha anat bé, però el navegador no ha reenviat la cookie. ${cookieSetupHint()}`,
      );
      cookieError.status = 401;
      throw cookieError;
    }
    throw error;
  }
}

async function login() {
  setStatus("Iniciant sessió...");
  setCallResult(loginResult, "");
  try {
    await apiFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: loginEmail.value.trim(),
        password: loginPassword.value,
      }),
    }, loginResult);
    await ensureSessionCookieWorks();
    setLoggedIn(true, { keepAuthPanel: true });
    sessionInfo.textContent = `Sessió activa (${loginEmail.value.trim()}).`;
    setStatus("Sessió iniciada. Carrega una tasca per començar.");
  } catch (error) {
    if (!error.status) {
      setCallResult(loginResult, `Error de xarxa/CORS\n${error.message}`, true);
    }
    setLoggedIn(false);
    setStatus(error.message, true);
  }
}

async function logout() {
  setStatus("Tancant sessió...");
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
  } catch {
    // Encara que falli, tractem la sessió com a tancada al client.
  }
  setLoggedIn(false);
  setStatus("Sessió tancada.");
}

// Descarrega un objecte com a fitxer JSON al navegador.
function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function exportData() {
  setStatus("Exportant les teves dades...");
  try {
    const data = await apiFetch("/api/auth/export");
    downloadJson(data, "arena-cat-dades.json");
    setStatus("Dades exportades: s'ha descarregat arena-cat-dades.json.");
  } catch (error) {
    handleAuthError(error);
  }
}

function showDeleteConfirm() {
  deleteConfirm.classList.remove("hidden");
  deletePassword.focus();
}

function hideDeleteConfirm() {
  deleteConfirm.classList.add("hidden");
  deletePassword.value = "";
}

async function deleteAccount() {
  if (!deletePassword.value) {
    setStatus("Introdueix la contrasenya actual per confirmar la baixa.", true);
    return;
  }

  setStatus("Donant de baixa el compte...");
  try {
    const data = await apiFetch("/api/auth/delete-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: deletePassword.value }),
    });
    setLoggedIn(false);
    setStatus(`Compte donat de baixa (${data.status}).`);
  } catch (error) {
    // El backend retorna 401 tant per contrasenya incorrecta com per sessió
    // caducada; mostrem el missatge real i deixem reintentar sense tancar sessió.
    setStatus(error.message, true);
  }
}

async function loadTask() {
  currentToken = null;
  setVoteButtons(false);
  setStatus("Carregant...");

  const params = new URLSearchParams({
    category_code: categoryInput.value,
  });

  try {
    const data = await apiFetch(`/api/task?${params}`);
    currentToken = data.token;
    promptOutput.textContent = data.prompt;
    renderResponse(responseAOutput, data.prompt, data.response_a);
    renderResponse(responseBOutput, data.prompt, data.response_b);
    setVoteButtons(true);
    setStatus("Tasca carregada.");
  } catch (error) {
    promptOutput.textContent = "Cap tasca carregada.";
    responseAOutput.textContent = "-";
    responseBOutput.textContent = "-";
    handleAuthError(error);
  }
}

async function vote(winner) {
  if (!currentToken) {
    return;
  }

  setVoteButtons(false);
  setStatus("Enviant vot...");

  try {
    const data = await apiFetch("/api/vote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ winner, token: currentToken }),
    });
    setStatus(`Vot desat: ${data.status}.`);
    await loadTask();
  } catch (error) {
    setVoteButtons(true);
    handleAuthError(error);
  }
}

registerButton.addEventListener("click", register);
loginButton.addEventListener("click", login);
logoutButton.addEventListener("click", logout);
exportButton.addEventListener("click", exportData);
deleteButton.addEventListener("click", showDeleteConfirm);
deleteCancelButton.addEventListener("click", hideDeleteConfirm);
deleteConfirmButton.addEventListener("click", deleteAccount);
loadTaskButton.addEventListener("click", loadTask);
voteButtons.forEach((button) => {
  button.addEventListener("click", () => vote(button.dataset.winner));
});

setLoggedIn(false);
