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

const loginEmail = document.querySelector("#loginEmail");
const loginPassword = document.querySelector("#loginPassword");
const loginButton = document.querySelector("#loginButton");

const verifyToken = document.querySelector("#verifyToken");
const verifyButton = document.querySelector("#verifyButton");

const logoutButton = document.querySelector("#logoutButton");
const exportButton = document.querySelector("#exportButton");
const deleteButton = document.querySelector("#deleteButton");
const deleteConfirm = document.querySelector("#deleteConfirm");
const deletePassword = document.querySelector("#deletePassword");
const deleteConfirmButton = document.querySelector("#deleteConfirmButton");
const deleteCancelButton = document.querySelector("#deleteCancelButton");

let currentToken = null;
let loggedIn = false;

function apiUrl(path) {
  return `${apiBaseInput.value.replace(/\/$/, "")}${path}`;
}

function setStatus(message, isError = false) {
  statusOutput.textContent = message;
  statusOutput.classList.toggle("error", isError);
}

function setVoteButtons(enabled) {
  voteButtons.forEach((button) => {
    button.disabled = !enabled;
  });
}

// Reflecteix l'estat d'autenticació a la interfície.
function setLoggedIn(isLoggedIn) {
  loggedIn = isLoggedIn;
  authPanel.classList.toggle("hidden", isLoggedIn);
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

// Wrapper de fetch que sempre inclou la cookie de sessió i parseja el cos.
async function apiFetch(path, options = {}) {
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

  if (!response.ok) {
    const detail = (data && data.detail) || `HTTP ${response.status}`;
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  return data;
}

// Distingeix 401 (cal iniciar sessió) i 403 (cal verificar el correu).
function handleAuthError(error) {
  if (error.status === 401) {
    setLoggedIn(false);
    setStatus("Sessió invàlida o caducada. Torna a iniciar sessió.", true);
  } else if (error.status === 403) {
    setStatus("Cal verificar el correu abans de continuar.", true);
  } else {
    setStatus(error.message, true);
  }
}

async function register() {
  setStatus("Registrant...");
  try {
    const data = await apiFetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: registerEmail.value.trim(),
        password: registerPassword.value,
        consent: registerConsent.checked,
      }),
    });
    setStatus(
      `Registre correcte (${data.status}). Revisa el log del backend per obtenir el token de verificació.`,
    );
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function verify() {
  setStatus("Verificant correu...");
  try {
    const data = await apiFetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: verifyToken.value.trim() }),
    });
    setStatus(`Correu verificat (${data.status}). Ja pots iniciar sessió.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function login() {
  setStatus("Iniciant sessió...");
  try {
    await apiFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: loginEmail.value.trim(),
        password: loginPassword.value,
      }),
    });
    setLoggedIn(true);
    sessionInfo.textContent = `Sessió activa (${loginEmail.value.trim()}).`;
    setStatus("Sessió iniciada. Carrega una tasca per començar.");
  } catch (error) {
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
    responseAOutput.textContent = data.response_a;
    responseBOutput.textContent = data.response_b;
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
verifyButton.addEventListener("click", verify);
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
