const STAGES = [
  ["new", "Новая"],
  ["pilot_prep", "Пилот: подготовка"],
  ["pilot_running", "Пилот: в процессе"],
  ["avr_report", "АВР и отчёт"],
  ["contract_review", "Согласование контракта"],
  ["presentation_payment", "Презентация и оплата"],
  ["contract_talks", "Переговоры о контракте"],
  ["done", "Успешно завершено"],
  ["paused", "На паузе"],
  ["refused", "Отказ"],
];

const board = document.getElementById("board");
const createBox = document.getElementById("create-box");
const form = document.getElementById("project-form");
const formError = document.getElementById("project-error");
const curatorSelect = document.getElementById("p-curator");

let currentUser = null;

document.getElementById("logout-button").addEventListener("click", logout);

function formatAmount(value) {
  return Number(value).toLocaleString("ru-RU");
}

function line(text, className) {
  const element = document.createElement("span");
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

function renderCard(project) {
  const card = document.createElement("a");
  card.className = "kanban-card";
  card.href = "/project.html?id=" + project.id;

  const name = document.createElement("strong");
  name.textContent = project.name;

  card.append(
    name,
    line(project.partner.company_name, "muted"),
    line("Сумма: " + formatAmount(project.deal_amount), "muted"),
    line("Куратор: " + project.curator.full_name, "muted")
  );
  return card;
}

function renderBoard(projects) {
  const columns = STAGES.map(([key, name]) => {
    const items = projects.filter((project) => project.stage === key);

    const column = document.createElement("section");
    column.className = "kanban-column stage-" + key;

    const head = document.createElement("h3");
    head.textContent = name + " (" + items.length + ")";
    column.append(head, ...items.map(renderCard));
    return column;
  });
  board.replaceChildren(...columns);
}

async function loadProjects() {
  renderBoard(await api("/projects"));
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.textContent = "";

  const fields = form.elements;
  const body = {
    name: fields.name.value.trim(),
    partner_name: fields.partner_name.value.trim(),
    contact_person: fields.contact_person.value.trim(),
    phone: fields.phone.value.trim(),
    services: fields.services.value.trim(),
    deal_amount: Number(fields.deal_amount.value || 0),
    curator_id: Number(fields.curator_id.value),
  };
  if (!body.name || !body.partner_name) {
    formError.textContent = "Заполните название проекта и партнёра";
    return;
  }

  try {
    await api("/projects", { method: "POST", body });
    form.reset();
    curatorSelect.value = String(currentUser.id);
    createBox.open = false;
    await loadProjects();
  } catch (error) {
    formError.textContent = error.message;
  }
});

(async () => {
  currentUser = await requireUser();
  if (!currentUser) return;
  document.getElementById("user-name").textContent = currentUser.full_name;

  // Создавать проекты могут администратор и руководитель
  if (["admin", "manager"].includes(currentUser.role)) {
    createBox.hidden = false;
    const employees = await api("/employees/directory");
    for (const employee of employees) {
      curatorSelect.append(new Option(employee.full_name, employee.id));
    }
    curatorSelect.value = String(currentUser.id);
  }

  await loadProjects();
})();