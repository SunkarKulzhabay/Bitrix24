const form = document.getElementById("login-form");
const errorBox = document.getElementById("login-error");
const submitButton = document.getElementById("login-button");

// Уже вошли: сразу на главную. Если токен устарел, api.js вернёт сюда.
if (getToken()) {
  window.location.href = "/dashboard.html";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.textContent = "";

  const login = form.elements.login.value.trim();
  const password = form.elements.password.value;
  if (!login || !password) {
    errorBox.textContent = "Введите логин и пароль";
    return;
  }

  submitButton.disabled = true;
  try {
    await signIn(login, password);
    window.location.href = "/dashboard.html";
  } catch (error) {
    errorBox.textContent = error.message;
    form.elements.password.value = "";
    form.elements.password.focus();
  } finally {
    submitButton.disabled = false;
  }
});
