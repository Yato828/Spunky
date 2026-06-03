const canvas = document.getElementById("maze");
const ctx = canvas.getContext("2d");
const scoreEl = document.getElementById("score");
const bestEl = document.getElementById("best");
const pauseButton = document.getElementById("pause");
const restartButton = document.getElementById("restart");
const statusEl = document.getElementById("gameStatus");

const spunky = new Image();
spunky.src = "assets/spunky-king-contour.png";
const coinImg = new Image();
coinImg.src = "assets/solana-coin.png";

const tile = 40;
const map = [
  "##################",
  "#P.....#.........#",
  "#.###..#.#######.#",
  "#...#..#.....#...#",
  "###.#..#####.#.###",
  "#...#........#...#",
  "#.#####.##.#####.#",
  "#.......##.......#",
  "#.#####.##.#####.#",
  "#...#........#..G#",
  "###.#.######.#.###",
  "#.....#....#.....#",
  "##################",
];

const dirs = [
  { x: 1, y: 0 },
  { x: -1, y: 0 },
  { x: 0, y: 1 },
  { x: 0, y: -1 },
];

const walls = [];
const openTiles = [];
let player;
let enemy;
let coin;
let direction = { x: 1, y: 0 };
let nextDirection = { x: 1, y: 0 };
let enemyTarget = null;
let enemySpeedBoost = 0;
let score = 0;
let best = Number(sessionStorage.getItem("spunky-best") || 0);
let gameOver = false;
let paused = false;
let lastTime = 0;

bestEl.textContent = best;

function center(col, row) {
  return { x: col * tile + tile / 2, y: row * tile + tile / 2 };
}

function tileOf(obj) {
  return {
    x: Math.max(0, Math.min(map[0].length - 1, Math.floor(obj.x / tile))),
    y: Math.max(0, Math.min(map.length - 1, Math.floor(obj.y / tile))),
  };
}

function isOpen(x, y) {
  return map[y]?.[x] && map[y][x] !== "#";
}

function parseMap() {
  walls.length = 0;
  openTiles.length = 0;
  map.forEach((row, y) => {
    [...row].forEach((cell, x) => {
      if (cell === "#") {
        walls.push({ x: x * tile, y: y * tile, w: tile, h: tile });
      } else {
        openTiles.push({ x, y });
      }
      if (cell === "P") player = { ...center(x, y), r: 13, speed: 162 };
      if (cell === "G") enemy = { ...center(x, y), r: 13, speed: 142 };
    });
  });
}

function isWallAt(x, y, radius = 13) {
  const checks = [
    [x - radius, y - radius],
    [x + radius, y - radius],
    [x - radius, y + radius],
    [x + radius, y + radius],
  ];
  return checks.some(([px, py]) => map[Math.floor(py / tile)]?.[Math.floor(px / tile)] === "#");
}

function canMove(obj, dir, distance) {
  return !isWallAt(obj.x + dir.x * distance, obj.y + dir.y * distance, obj.r);
}

function snapToGrid(obj) {
  const col = Math.round((obj.x - tile / 2) / tile);
  const row = Math.round((obj.y - tile / 2) / tile);
  obj.x = col * tile + tile / 2;
  obj.y = row * tile + tile / 2;
}

function atCenter(obj, tolerance = 3) {
  const col = Math.round((obj.x - tile / 2) / tile);
  const row = Math.round((obj.y - tile / 2) / tile);
  return Math.abs(obj.x - (col * tile + tile / 2)) <= tolerance && Math.abs(obj.y - (row * tile + tile / 2)) <= tolerance;
}

function shortestNextCell(start, goal) {
  if (start.x === goal.x && start.y === goal.y) return start;

  const queue = [start];
  const seen = new Set([`${start.x},${start.y}`]);
  const prev = new Map();

  for (let i = 0; i < queue.length; i += 1) {
    const cur = queue[i];
    if (cur.x === goal.x && cur.y === goal.y) break;

    for (const dir of dirs) {
      const next = { x: cur.x + dir.x, y: cur.y + dir.y };
      const key = `${next.x},${next.y}`;
      if (!isOpen(next.x, next.y) || seen.has(key)) continue;
      seen.add(key);
      prev.set(key, cur);
      queue.push(next);
    }
  }

  const goalKey = `${goal.x},${goal.y}`;
  if (!prev.has(goalKey)) {
    const fallback = dirs
      .map((dir) => ({ x: start.x + dir.x, y: start.y + dir.y }))
      .filter((cell) => isOpen(cell.x, cell.y))
      .sort((a, b) => Math.hypot(a.x - goal.x, a.y - goal.y) - Math.hypot(b.x - goal.x, b.y - goal.y));
    return fallback[0] || start;
  }

  let step = goal;
  let parent = prev.get(goalKey);
  while (parent && !(parent.x === start.x && parent.y === start.y)) {
    step = parent;
    parent = prev.get(`${step.x},${step.y}`);
  }
  return step;
}

function chooseEnemyTarget() {
  const enemyCell = tileOf(enemy);
  const playerCell = tileOf(player);
  const next = shortestNextCell(enemyCell, playerCell);
  enemyTarget = center(next.x, next.y);
}

function spawnCoin() {
  const safe = openTiles.filter((p) => {
    const c = center(p.x, p.y);
    return Math.hypot(c.x - player.x, c.y - player.y) > 130 && Math.hypot(c.x - enemy.x, c.y - enemy.y) > 120;
  });
  const pick = safe[Math.floor(Math.random() * safe.length)] || openTiles[0];
  coin = { ...center(pick.x, pick.y), r: 18 };
}

function resetGame() {
  parseMap();
  direction = { x: 1, y: 0 };
  nextDirection = { x: 1, y: 0 };
  enemyTarget = null;
  enemySpeedBoost = 0;
  score = 0;
  gameOver = false;
  paused = false;
  scoreEl.textContent = score;
  pauseButton.textContent = "Pause";
  statusEl.textContent = "Spunky is hunting.";
  spawnCoin();
  chooseEnemyTarget();
}

function togglePause() {
  if (gameOver) return;
  paused = !paused;
  pauseButton.textContent = paused ? "Resume" : "Pause";
  statusEl.textContent = paused ? "Paused." : "Spunky is hunting.";
}

function setDirection(key) {
  const controls = {
    ArrowUp: { x: 0, y: -1 },
    KeyW: { x: 0, y: -1 },
    ArrowDown: { x: 0, y: 1 },
    KeyS: { x: 0, y: 1 },
    ArrowLeft: { x: -1, y: 0 },
    KeyA: { x: -1, y: 0 },
    ArrowRight: { x: 1, y: 0 },
    KeyD: { x: 1, y: 0 },
  };
  if (controls[key]) nextDirection = controls[key];
}

function updatePlayer(dt) {
  const step = player.speed * dt;
  if (canMove(player, nextDirection, step + 2)) direction = nextDirection;
  if (canMove(player, direction, step)) {
    player.x += direction.x * step;
    player.y += direction.y * step;
  } else {
    snapToGrid(player);
  }
}

function updateEnemy(dt) {
  if (!enemyTarget || Math.hypot(enemy.x - enemyTarget.x, enemy.y - enemyTarget.y) < 3) {
    snapToGrid(enemy);
    chooseEnemyTarget();
  }

  const speed = enemy.speed + enemySpeedBoost;
  const dx = enemyTarget.x - enemy.x;
  const dy = enemyTarget.y - enemy.y;
  const dist = Math.hypot(dx, dy);
  if (dist <= 0) return;

  const step = Math.min(speed * dt, dist);
  enemy.x += (dx / dist) * step;
  enemy.y += (dy / dist) * step;

  if (atCenter(enemy, 2)) {
    chooseEnemyTarget();
  }
}

function update(dt) {
  if (gameOver || paused) return;

  updatePlayer(dt);
  updateEnemy(dt);

  if (Math.hypot(player.x - coin.x, player.y - coin.y) < player.r + coin.r) {
    score += 1;
    enemySpeedBoost = Math.min(46, enemySpeedBoost + 5);
    scoreEl.textContent = score;
    statusEl.textContent = score % 4 === 0 ? "Spunky got faster." : "Coin grabbed.";
    spawnCoin();
  }

  if (Math.hypot(player.x - enemy.x, player.y - enemy.y) < player.r + enemy.r + 4) {
    gameOver = true;
    best = Math.max(best, score);
    sessionStorage.setItem("spunky-best", String(best));
    bestEl.textContent = best;
    statusEl.textContent = "Caught. Restart and run it back.";
  }
}

function drawPlayer() {
  ctx.save();
  ctx.translate(player.x, player.y);
  ctx.rotate(Math.atan2(direction.y, direction.x));
  ctx.fillStyle = "#ffd84d";
  ctx.strokeStyle = "#ff9f1c";
  ctx.lineWidth = 3;
  ctx.shadowColor = "rgba(255, 216, 77, 0.6)";
  ctx.shadowBlur = 12;
  ctx.beginPath();
  ctx.arc(0, 0, 18, 0.35, Math.PI * 1.65);
  ctx.lineTo(0, 0);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#020817";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "#123a92";
  ctx.strokeStyle = "#2c74ff";
  ctx.lineWidth = 3;
  ctx.shadowColor = "rgba(44, 116, 255, 0.46)";
  ctx.shadowBlur = 9;
  walls.forEach((wall) => {
    ctx.fillRect(wall.x + 5, wall.y + 5, wall.w - 10, wall.h - 10);
    ctx.strokeRect(wall.x + 5, wall.y + 5, wall.w - 10, wall.h - 10);
  });
  ctx.shadowBlur = 0;

  openTiles.forEach((cell) => {
    const c = center(cell.x, cell.y);
    ctx.fillStyle = "rgba(255, 216, 77, 0.62)";
    ctx.beginPath();
    ctx.arc(c.x, c.y, 2, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.shadowColor = "rgba(255, 216, 77, 0.65)";
  ctx.shadowBlur = 12;
  ctx.drawImage(coinImg, coin.x - 21, coin.y - 21, 42, 42);
  ctx.shadowBlur = 0;
  drawPlayer();
  ctx.shadowColor = "rgba(255, 63, 143, 0.55)";
  ctx.shadowBlur = 12;
  ctx.drawImage(spunky, enemy.x - 30, enemy.y - 30, 60, 60);
  ctx.shadowBlur = 0;

  if (gameOver) {
    ctx.fillStyle = "rgba(2, 8, 23, 0.84)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffd84d";
    ctx.font = "900 42px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Caught!", canvas.width / 2, canvas.height / 2);
  }

  if (paused) {
    ctx.fillStyle = "rgba(2, 8, 23, 0.64)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffd84d";
    ctx.font = "900 42px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Paused", canvas.width / 2, canvas.height / 2);
  }
}

function loop(time) {
  const dt = Math.min(0.032, (time - lastTime) / 1000 || 0);
  lastTime = time;
  update(dt);
  draw();
  requestAnimationFrame(loop);
}

document.addEventListener("keydown", (event) => {
  if (event.code === "Space" || event.code === "KeyP") {
    togglePause();
    event.preventDefault();
    return;
  }
  setDirection(event.code);
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.code)) {
    event.preventDefault();
  }
});

let touchStart = null;
canvas.addEventListener("touchstart", (event) => {
  const t = event.changedTouches[0];
  touchStart = { x: t.clientX, y: t.clientY };
});

canvas.addEventListener("touchend", (event) => {
  if (!touchStart) return;
  const t = event.changedTouches[0];
  const dx = t.clientX - touchStart.x;
  const dy = t.clientY - touchStart.y;
  if (Math.abs(dx) > Math.abs(dy)) {
    nextDirection = dx > 0 ? { x: 1, y: 0 } : { x: -1, y: 0 };
  } else {
    nextDirection = dy > 0 ? { x: 0, y: 1 } : { x: 0, y: -1 };
  }
  touchStart = null;
});

pauseButton.addEventListener("click", togglePause);
restartButton.addEventListener("click", resetGame);

resetGame();
requestAnimationFrame(loop);
