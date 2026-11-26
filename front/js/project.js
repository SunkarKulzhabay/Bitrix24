const STAGE_NAMES = {
  new: "Новая",
  pilot_prep: "Пилот: подготовка",
  pilot_running: "Пилот: в процессе",
  avr_report: "АВР и отчёт",
  contract_review: "Согласование контракта",
  presentation_payment: "Презентация и оплата",
  contract_talks: "Переговоры о контракте",
  done: "Успешно завершено",
  paused: "На паузе",
  refused: "Отказ",
};

const projectId = Number(new URLSearchParams(window.location.search).get("id"));

const stageCard = document.getElementById("stage-card");
const stageForm = document.getElementById("stage-form");
const stageSelect = document.getElementById("s-stage");
const reasonBox = document.getElementById("reason-box");
const reasonInput = document.getElementById("s-reason");
const stageError = document.getElementById("stage-error");

const membersBox = document.getElementById("members");
const memberForm = document.getElementById("member-form");
const memberEmployee = document.getElementById("m-employee");
const memberRole = document.getElementById("m-role");
const memberReports = document.getElementById("m-reports");
const memberError = document.getElementById("member-error");

let project = null;
let directory = [];

document.getElementById("logout-button").addEventListener("click", logout);

function addInfo(list, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = value || "—";
  list.append(term, description);
}

function renderInfo() {
  document.title = project.name + " — Офис CRM";
  document.getElementById("p-title").textContent = project.name;

  const badge = document.getElementById("p-stage");
  badge.textContent = STAGE_NAMES[project.stage];
  badge.className = "badge stage-" + project.stage;

  const list = document.getElementById("p-info");
  list.replaceChildren();
  addInfo(list, "Партнёр", project.partner.company_name);
  addInfo(list, "Контактное лицо", project.partner.contact_person);
  addInfo(list, "Телефон", project.partner.phone);
  addInfo(list, "Куратор", project.curator.full_name);
  addInfo(list, "Сумма сделки", Number(project.deal_amount).toLocaleString("ru-RU"));
  addInfo(list, "Услуги", project.services);
  if (project.stage === "refused") {
    addInfo(list, "Причина отказа", project.refusal_reason);
  }
}

function renderStageForm() {
  stageCard.hidden = !project.can_manage;
  stageSelect.replaceChildren();
  for (const [key, name] of Object.entries(STAGE_NAMES)) {
    if (key !== project.stage) stageSelect.append(new Option(name, key));
  }
  reasonBox.hidden = stageSelect.value !== "refused";
}

function renderMembers() {
  const children = {};
  for (const member of project.members) {
    const key = member.reports_to_id || 0;
    (children[key] = children[key] || []).push(member);
  }

  function branch(parentId) {
    const list = document.createElement("ul");
    list.className = "tree";
    for (const member of children[parentId] || []) {
      const item = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = member.employee.full_name + " — " + member.role;
      item.append(label);

      if (project.can_manage) {
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "button-secondary button-small";
        remove.textContent = "Убрать";
        remove.addEventListener("click", async () => {
          if (!confirm("Убрать из проекта: " + member.employee.full_name + "?")) return;
          try {
            project = await api("/projects/" + projectId + "/members/" + member.id, { method: "DELETE" });
            render();
          } catch (error) {
            alert(error.message);
          }
        });
        item.append(" ", remove);
      }

      const sub = branch(member.id);
      if (sub.children.length > 0) item.append(sub);
      list.append(item);
    }
    return list;
  }

  if (project.members.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Участников пока нет";
    membersBox.replaceChildren(empty);
  } else {
    membersBox.replaceChildren(branch(0));
  }

  memberForm.hidden = !project.can_manage;
  memberEmployee.replaceChildren();
  const taken = new Set(project.members.map((member) => member.employee.id));
  for (const employee of directory) {
    if (!taken.has(employee.id)) memberEmployee.append(new Option(employee.full_name, employee.id));
  }
  memberReports.replaceChildren(new Option("Ни кому (верхний уровень)", ""));
  for (const member of project.members) {
    memberReports.append(new Option(member.employee.full_name + " — " + member.role, member.id));
  }
}

function renderHistory() {
  const items = project.history.map((change) => {
    const item = document.createElement("li");
    const when = new Date(change.changed_at).toLocaleString("ru-RU");
    const step = change.from_stage
      ? STAGE_NAMES[change.from_stage] + " → " + STAGE_NAMES[change.to_stage]
      : "Проект создан";
    let text = when + ": " + step + " (" + change.changed_by.full_name + ")";
    if (change.comment) text += " — " + change.comment;
    item.textContent = text;
    return item;
  });
  document.getElementById("history").replaceChildren(...items);
}

function render() {
  renderInfo();
  renderStageForm();
  renderMembers();
  renderHistory();
}

stageSelect.addEventListener("change", () => {
  reasonBox.hidden = stageSelect.value !== "refused";
});

stageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  stageError.textContent = "";
  try {
    project = await api("/projects/" + projectId + "/stage", {
      method: "POST",
      body: { stage: stageSelect.value, reason: reasonInput.value.trim() },
    });
    reasonInput.value = "";
    render();
  } catch (error) {
    stageError.textContent = error.message;
  }
});

memberForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  memberError.textContent = "";

  const role = memberRole.value.trim();
  if (!memberEmployee.value || !role) {
    memberError.textContent = "Выберите сотрудника и укажите роль";
    return;
  }

  try {
    project = await api("/projects/" + projectId + "/members", {
      method: "POST",
      body: {
        employee_id: Number(memberEmployee.value),
        role,
        reports_to_id: memberReports.value ? Number(memberReports.value) : null,
      },
    });
    memberRole.value = "";
    render();
  } catch (error) {
    memberError.textContent = error.message;
  }
});

(async () => {
  const user = await requireUser();
  if (!user) return;
  document.getElementById("user-name").textContent = user.full_name;

  if (!projectId) {
    window.location.href = "/projects.html";
    return;
  }

  try {
    project = await api("/projects/" + projectId);
  } catch (error) {
    alert(error.message);
    window.location.href = "/projects.html";
    return;
  }
  directory = await api("/employees/directory");
  render();
})();