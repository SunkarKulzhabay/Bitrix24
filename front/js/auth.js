// Вход, выход и проверка, что пользователь вошёл.

async function signIn(login, password) {
  const data = await api("/auth/login", { method: "POST", body: { login, password } });
  setToken(data.access_token);
}

function logout() {
  clearToken();
  window.location.href = "/index.html";
}

// Вызываем в начале каждой закрытой страницы.
// Возвращает данные текущего пользователя или отправляет на страницу входа.
async function requireUser() {
  if (!getToken()) {
    window.location.href = "/index.html";
    return null;
  }
  return api("/auth/me");
}
