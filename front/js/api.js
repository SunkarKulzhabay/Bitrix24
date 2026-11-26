// Общий код для обращений к бэкенду. Все страницы подключают этот файл.

const TOKEN_KEY = "crm_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// api("/tasks")                                  -> GET /api/tasks
// api("/tasks", { method: "POST", body: {...} }) -> POST /api/tasks
async function api(path, { method = "GET", body } = {}) {
  const headers = {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch("/api" + path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  // Токен устарел или недействителен: возвращаем на страницу входа.
  // Для самого входа 401 означает «неверный пароль», это показывает форма.
  if (response.status === 401 && path !== "/auth/login") {
    clearToken();
    window.location.href = "/index.html";
    throw new Error("Требуется вход в систему");
  }

  if (!response.ok) {
    const detail = data && data.detail;
    throw new Error(typeof detail === "string" ? detail : "Проверьте введённые данные");
  }
  return data;
}
