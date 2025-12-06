const statusEl = document.getElementById("status");
const timerEl = document.getElementById("timer");
const boostBtn = document.getElementById("boost");
const scoresEl = document.getElementById("scores");
const planeEl = document.getElementById("plane");

let ws;
let playerId = null;
let gameTimer = null;
let timeLeft = 30;
let isConnected = false;

function setStatus(text, ready = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("status-ready", ready);
  statusEl.classList.toggle("status-idle", !ready);
}

function updateScores(scores) {
  const entries = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  scoresEl.innerHTML = "";
  for (const [id, score] of entries) {
    const li = document.createElement("li");
    li.textContent = `${id}`;
    const span = document.createElement("span");
    span.textContent = `${score} 分`;
    li.appendChild(span);
    if (playerId === id) li.classList.add("self");
    scoresEl.appendChild(li);
  }
}

function startTimer() {
  clearInterval(gameTimer);
  timeLeft = 30;
  timerEl.textContent = timeLeft;
  gameTimer = setInterval(() => {
    timeLeft -= 1;
    timerEl.textContent = timeLeft;
    if (timeLeft <= 0) {
      clearInterval(gameTimer);
      boostBtn.disabled = true;
      setStatus("回合结束，请刷新重新开始", false);
    }
  }, 1000);
}

function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onopen = () => {
    isConnected = true;
    setStatus("已连接，准备起飞！", true);
    boostBtn.disabled = false;
    startTimer();
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "welcome") {
      playerId = data.playerId;
      updateScores(data.scores);
      planeEl.textContent = "✈️";
      setStatus(`欢迎 ${playerId}，点击按钮为喷气机加速！`, true);
    }
    if (data.type === "scores") {
      updateScores(data.scores);
    }
  };

  ws.onclose = () => {
    isConnected = false;
    setStatus("连接断开，请刷新页面重试", false);
    boostBtn.disabled = true;
  };

  ws.onerror = () => {
    setStatus("连接出现问题，正在重试...", false);
  };
}

boostBtn.addEventListener("click", () => {
  if (!isConnected || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ type: "boost" }));
  planeEl.textContent = "🚀";
  setTimeout(() => (planeEl.textContent = "✈️"), 200);
});

connect();
