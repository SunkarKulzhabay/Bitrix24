const ROLE_NAMES = {
  employee: "Сотрудник",
  manager: "Руководитель",
  hr: "HR-специалист",
  accountant: "Бухгалтер",
  admin: "Администратор",
};

const tableBody = document.getElementById("employees-body");
const form = document.getElementById("employee-form");
const formError = document.getElementById("employee-error");
let currentUser = null;

document.getElementById("logout-button").addEventListener("click", logout);

function textCell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function smallButton(text, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button-secondary button-small";
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

function renderRow(employee) {
  const row = document.createElement("tr");
  if (!employee.is_active) row.classList.add("row-inactive");

  // Роль: выпадающий список
  const roleCell = document.createElement("td");
  const select = document.createElement("select");
  for (const [value, name] of Object.entries(ROLE_NAMES)) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = name;
    select.append(option);
  }
  select.value = employee.role;
  select.disabled = employee.id === currentUser.id;
  select.addEventListener("change", async () => {
    try {
      await api("/employees/" + employee.id, { method: "PATCH", body: { role: select.value } });
      employee.role = select.value;
    } catch (error) {
      alert(error.message);
      select.value = employee.role;
    }
  });
  roleCell.append(select);

  // Действия
  const actions = document.createElement("td");
  const actionsBox = document.createElement("div");
  actionsBox.className = "actions";

  if (employee.id !== currentUser.id) {
    actionsBox.append(
      smallButton(employee.is_active ? "Отключить" : "Включить", async () => {
        try {
          await api("/employees/" + employee.id, { method: "PATCH", body: { is_active: !employee.is_active } });
          await loadEmployees();
        } catch (error) {
          alert(error.message);
        }
      })
    );
  }
  actionsBox.append(
    smallButton("Новый пароль", async () => {
      const password = prompt("Новый пароль для " + employee.full_name + " (от 8 символов):");
      if (!password) return;
      try {
        await api("/employees/" + employee.id + "/password", { method: "PUT", body: { password } });
        alert("Пароль изменён");
      } catch (error) {
        alert(error.message);
      }
    })
  );
  actions.append(actionsBox);

  row.append(
    textCell(employee.full_name),
    textCell(employee.login),
    roleCell,
    textCell(employee.is_active ? "Работает" : "Отключён"),
    actions
  );
  return row;
}

async function loadEmployees() {
  const employees = await api("/employees");
  tableBody.replaceChildren(...employees.map(renderRow));
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.textContent = "";

  const body = {
    full_name: form.elements.full_name.value.trim(),
    login: form.elements.login.value.trim(),
    password: form.elements.password.value,
    role: form.elements.role.value,
  };
  if (!body.full_name || !body.login || !body.password) {
    formError.textContent = "Заполните ФИО, логин и пароль";
    return;
  }

  try {
    await api("/employees", { method: "POST", body });
    form.reset();
    await loadEmployees();
  } catch (error) {
    formError.textContent = error.message;
  }
});

(async () => {
  currentUser = await requireUser();
  if (!currentUser) return;

  // Страница только для администратора и HR
  if (!["admin", "hr"].includes(currentUser.role)) {
    window.location.href = "/dashboard.html";
    return;
  }

  document.getElementById("user-name").textContent = currentUser.full_name;
  await loadEmployees();
})();