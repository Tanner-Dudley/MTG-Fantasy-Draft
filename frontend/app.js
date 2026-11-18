/* ═══════════════════════════════════════════════════════════════
   State
   ═══════════════════════════════════════════════════════════════ */

const state = {
  token: localStorage.getItem("mtg_token"),
  user: null,
  lobbyId: localStorage.getItem("mtg_lobby_id"),
  lobby: null,
  pollTimer: null,
};

/* ═══════════════════════════════════════════════════════════════
   API helper
   ═══════════════════════════════════════════════════════════════ */

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`/api${path}`, opts);
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const msg = data?.detail || `Request failed (${res.status})`;
    if (res.status === 401 && path !== "/login" && path !== "/register") {
      doLogout();
    }
    throw new Error(msg);
  }
  return data;
}

/* ═══════════════════════════════════════════════════════════════
   Toast notifications
   ═══════════════════════════════════════════════════════════════ */

let toastTimeout;
function showToast(message, type = "error") {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = `toast ${type} show`;
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => el.classList.remove("show"), 4000);
}

/* ═══════════════════════════════════════════════════════════════
   Screen navigation
   ═══════════════════════════════════════════════════════════════ */

function navigate(screenId) {
  stopPoll();
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  document.getElementById(screenId).classList.add("active");
}

/* ═══════════════════════════════════════════════════════════════
   Auth
   ═══════════════════════════════════════════════════════════════ */

function switchAuthTab(tab) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.getElementById("login-form").classList.toggle("hidden", tab !== "login");
  document.getElementById("register-form").classList.toggle("hidden", tab !== "register");
  event.target.classList.add("active");
}

async function doRegister(e) {
  e.preventDefault();
  try {
    const data = await api("POST", "/register", {
      username: document.getElementById("reg-username").value,
      password: document.getElementById("reg-password").value,
      display_name: document.getElementById("reg-display").value,
    });
    state.token = data.access_token;
    localStorage.setItem("mtg_token", state.token);
    state.user = await api("GET", "/me");
    showToast("Account created!", "success");
    enterHome();
  } catch (err) {
    showToast(err.message);
  }
}

async function doLogin(e) {
  e.preventDefault();
  try {
    const data = await api("POST", "/login", {
      username: document.getElementById("login-username").value,
      password: document.getElementById("login-password").value,
    });
    state.token = data.access_token;
    localStorage.setItem("mtg_token", state.token);
    state.user = await api("GET", "/me");
    showToast(`Welcome back, ${state.user.display_name}!`, "success");
    enterHome();
  } catch (err) {
    showToast(err.message);
  }
}

function doLogout() {
  state.token = null;
  state.user = null;
  state.lobbyId = null;
  state.lobby = null;
  localStorage.removeItem("mtg_token");
  localStorage.removeItem("mtg_lobby_id");
  stopPoll();
  navigate("auth-screen");
}

/* ═══════════════════════════════════════════════════════════════
   Home screen
   ═══════════════════════════════════════════════════════════════ */

function enterHome() {
  document.getElementById("welcome-name").textContent = state.user.display_name;
  navigate("home-screen");
}

async function doCreateLobby(e) {
  e.preventDefault();
  try {
    const lobby = await api("POST", "/lobbies", {
      name: document.getElementById("lobby-name").value,
      num_players: parseInt(document.getElementById("lobby-players").value),
    });
    enterLobby(lobby);
    showToast("Lobby created!", "success");
  } catch (err) {
    showToast(err.message);
  }
}

async function doJoinLobby(e) {
  e.preventDefault();
  try {
    const lobby = await api("POST", "/lobbies/join", {
      lobby_code: document.getElementById("join-code").value.toUpperCase(),
    });
    enterLobby(lobby);
    showToast("Joined lobby!", "success");
  } catch (err) {
    showToast(err.message);
  }
}

/* ═══════════════════════════════════════════════════════════════
   Lobby waiting room
   ═══════════════════════════════════════════════════════════════ */

function enterLobby(lobby) {
  state.lobby = lobby;
  state.lobbyId = lobby.id;
  localStorage.setItem("mtg_lobby_id", lobby.id);
  renderLobby();
  navigate("lobby-screen");
  startPoll(2000);
}

function renderLobby() {
  const lobby = state.lobby;
  if (!lobby) return;

  document.getElementById("lobby-title").textContent = lobby.name;
  document.getElementById("lobby-code-text").textContent = lobby.code;
  document.getElementById("lobby-welcome-name").textContent =
    state.user?.display_name || "";

  const listEl = document.getElementById("lobby-player-list");
  listEl.innerHTML =
    `<h3>Players (${lobby.players.length}/${lobby.num_players_expected})</h3>` +
    lobby.players
      .map(
        (p) =>
          `<div class="player-row${p.id === lobby.owner_id ? " owner" : ""}">${p.display_name}</div>`
      )
      .join("");

  const isOwner = state.user && lobby.owner_id === state.user.id;
  const canStart = isOwner && lobby.players.length >= 2;
  const startBtn = document.getElementById("start-btn");
  startBtn.style.display = isOwner ? "inline-block" : "none";
  startBtn.disabled = !canStart;

  const statusText = document.getElementById("lobby-status-text");
  if (lobby.players.length < 2) {
    statusText.textContent = "Waiting for at least one more player to join...";
  } else if (isOwner) {
    statusText.textContent = "Ready! Hit Start Draft when everyone is in.";
  } else {
    statusText.textContent = "Waiting for the lobby owner to start the draft...";
  }
}

function leaveLobby() {
  stopPoll();
  state.lobbyId = null;
  state.lobby = null;
  localStorage.removeItem("mtg_lobby_id");
  enterHome();
}

function copyLobbyCode() {
  const code = document.getElementById("lobby-code-text").textContent;
  navigator.clipboard.writeText(code).then(() => showToast("Code copied!", "success"));
}

/* ═══════════════════════════════════════════════════════════════
   Draft
   ═══════════════════════════════════════════════════════════════ */

async function doStartDraft() {
  try {
    document.getElementById("start-btn").disabled = true;
    const lobby = await api("POST", `/lobbies/${state.lobbyId}/start`);
    state.lobby = lobby;
    navigate("draft-screen");
    renderDraft();
    startPoll(2000);
  } catch (err) {
    document.getElementById("start-btn").disabled = false;
    showToast(err.message);
  }
}

function renderDraft() {
  const lobby = state.lobby;
  if (!lobby || !lobby.pool) return;

  const isMyTurn =
    state.user && lobby.current_turn_user_id === state.user.id;

  const turnPlayer = lobby.players.find(
    (p) => p.id === lobby.current_turn_user_id
  );

  const banner = document.getElementById("turn-banner");
  if (isMyTurn) {
    banner.className = "turn-banner your-turn";
    banner.textContent = "YOUR TURN — Pick a Commander!";
  } else {
    banner.className = "turn-banner waiting";
    banner.textContent = `Waiting for ${turnPlayer?.display_name || "..."}`;
  }

  const grid = document.getElementById("card-grid");
  grid.innerHTML = "";

  lobby.pool.forEach((card) => {
    const cell = document.createElement("div");
    cell.className = "card-cell" + (card.is_drafted ? " drafted" : "");

    const img = document.createElement("img");
    img.src = card.image_url;
    img.alt = card.name;
    img.loading = "lazy";

    const btn = document.createElement("button");
    btn.className = "draft-btn";
    btn.disabled = card.is_drafted || !isMyTurn;
    btn.textContent = card.is_drafted
      ? "Drafted"
      : isMyTurn
        ? "Draft"
        : "Waiting...";
    btn.addEventListener("click", () => doPick(card.id));

    cell.appendChild(img);
    cell.appendChild(btn);
    grid.appendChild(cell);
  });

  renderDraftBoard();
}

function renderDraftBoard() {
  const lobby = state.lobby;
  if (!lobby) return;

  const board = document.getElementById("draft-board");
  board.innerHTML = "";

  lobby.players.forEach((player) => {
    const section = document.createElement("div");
    const isActive = player.id === lobby.current_turn_user_id;
    section.className = "player-section" + (isActive ? " active" : "");

    const h3 = document.createElement("h3");
    h3.textContent = player.display_name + (isActive ? " ◄" : "");
    section.appendChild(h3);

    const ul = document.createElement("ul");
    player.picks.forEach((name) => {
      const li = document.createElement("li");
      li.textContent = name;
      ul.appendChild(li);
    });
    section.appendChild(ul);
    board.appendChild(section);
  });
}

async function doPick(cardId) {
  try {
    document.querySelectorAll(".draft-btn").forEach((b) => (b.disabled = true));
    const result = await api("POST", `/lobbies/${state.lobbyId}/pick`, {
      card_id: cardId,
    });

    const lobby = await api("GET", `/lobbies/${state.lobbyId}`);
    state.lobby = lobby;

    if (result.draft_complete) {
      stopPoll();
      navigate("results-screen");
      renderResults();
    } else {
      renderDraft();
    }
  } catch (err) {
    showToast(err.message);
    const lobby = await api("GET", `/lobbies/${state.lobbyId}`).catch(() => null);
    if (lobby) {
      state.lobby = lobby;
      renderDraft();
    }
  }
}

/* ═══════════════════════════════════════════════════════════════
   Results
   ═══════════════════════════════════════════════════════════════ */

function renderResults() {
  const lobby = state.lobby;
  if (!lobby) return;

  const poolMap = {};
  if (lobby.pool) {
    lobby.pool.forEach((c) => (poolMap[c.name] = c));
  }

  const grid = document.getElementById("results-grid");
  grid.innerHTML = "";

  lobby.players.forEach((player) => {
    const card = document.createElement("div");
    card.className = "result-card";

    const h3 = document.createElement("h3");
    h3.textContent = player.display_name;
    card.appendChild(h3);

    const ul = document.createElement("ul");
    ul.className = "pick-list";
    player.picks.forEach((name) => {
      const li = document.createElement("li");
      const info = poolMap[name];
      if (info) {
        const img = document.createElement("img");
        img.src = info.image_url;
        img.alt = name;
        img.loading = "lazy";
        li.appendChild(img);
      }
      const span = document.createElement("span");
      span.textContent = name;
      li.appendChild(span);
      ul.appendChild(li);
    });
    card.appendChild(ul);

    const copyBtn = document.createElement("button");
    copyBtn.className = "btn small";
    copyBtn.textContent = "Copy Decklist";
    copyBtn.addEventListener("click", () => {
      const text = player.picks.map((n) => `1 ${n}`).join("\n");
      navigator.clipboard.writeText(text).then(() => showToast("Copied!", "success"));
    });
    card.appendChild(copyBtn);

    grid.appendChild(card);
  });
}

function newDraft() {
  state.lobbyId = null;
  state.lobby = null;
  localStorage.removeItem("mtg_lobby_id");
  enterHome();
}

/* ═══════════════════════════════════════════════════════════════
   Polling
   ═══════════════════════════════════════════════════════════════ */

function startPoll(intervalMs = 2000) {
  stopPoll();
  state.pollTimer = setInterval(pollLobby, intervalMs);
}

function stopPoll() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

async function pollLobby() {
  if (!state.lobbyId) return;
  try {
    const lobby = await api("GET", `/lobbies/${state.lobbyId}`);
    state.lobby = lobby;

    if (lobby.status === "waiting") {
      renderLobby();
    } else if (lobby.status === "drafting") {
      if (!document.getElementById("draft-screen").classList.contains("active")) {
        navigate("draft-screen");
        startPoll(2000);
      }
      renderDraft();
    } else if (lobby.status === "completed") {
      stopPoll();
      navigate("results-screen");
      renderResults();
    }
  } catch {
    // Silently retry on next poll
  }
}

/* ═══════════════════════════════════════════════════════════════
   Init — runs on page load
   ═══════════════════════════════════════════════════════════════ */

async function init() {
  if (!state.token) {
    navigate("auth-screen");
    return;
  }

  try {
    state.user = await api("GET", "/me");
  } catch {
    doLogout();
    return;
  }

  if (state.lobbyId) {
    try {
      const lobby = await api("GET", `/lobbies/${state.lobbyId}`);
      state.lobby = lobby;

      if (lobby.status === "waiting") {
        renderLobby();
        navigate("lobby-screen");
        startPoll(2000);
      } else if (lobby.status === "drafting") {
        navigate("draft-screen");
        renderDraft();
        startPoll(2000);
      } else if (lobby.status === "completed") {
        navigate("results-screen");
        renderResults();
      }
    } catch {
      localStorage.removeItem("mtg_lobby_id");
      state.lobbyId = null;
      enterHome();
    }
  } else {
    enterHome();
  }
}

document.addEventListener("DOMContentLoaded", init);
