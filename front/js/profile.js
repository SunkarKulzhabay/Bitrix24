const ROLE_NAMES = {
  admin: "Администратор",
  manager: "Руководитель",
  hr: "HR-специалист",
  accountant: "Бухгалтер",
  employee: "Сотрудник",
};

const form = document.getElementById("password-form");
const errorBox = document.getElementById("password-error");
const okBox = document.getElementById("password-ok");

document.getElementById("logout-button").addEventListener("click", logout);

function addInfo(list, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = value;
  list.append(term, description);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.textContent = "";
  okBox.textContent = "";

  const current = form.elements.current.value;
  const next = form.elements.new.value;
  const repeat = form.elements.repeat.value;

  if (!current || !next) {
    errorBox.textContent = "Заполните все поля";
    return;
  }
  if (next.length < 8) {
    errorBox.textContent = "Новый пароль должен быть не короче 8 символов";
    return;
  }
  if (next !== repeat) {
    errorBox.textContent = "Новый пароль и повтор не совпадают";
    return;
  }

  try {
    await api("/auth/password", {
      method: "PUT",
      body: { current_password: current, new_password: next },
    });
    form.reset();
    okBox.textContent = "Пароль изменён";
  } catch (error) {
    errorBox.textContent = error.message;
  }
});

(async () => {
  const user = await requireUser();
  if (!user) return;

  document.getElementById("user-name").textContent = user.full_name;
  const list = document.getElementById("profile-info");
  addInfo(list, "ФИО", user.full_name);
  addInfo(list, "Логин", user.login);
  addInfo(list, "Роль", ROLE_NAMES[user.role] || user.role);
})();