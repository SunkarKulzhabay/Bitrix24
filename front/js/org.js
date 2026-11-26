const EVENT_NAMES = {
  hired: "Принят",
  rehired: "Принят повторно",
  fired: "Уволен",
  transferred: "Перевод",
  replaced: "Замена",
  moved_to_project: "Другой проект",
  note: "Заметка",
};

const treeBox = document.getElementById("tree");
const catalogs = document.getElementById("catalogs");
const assignCard = document.getElementById("assign-card");
const assignBody = document.getElementById("assign-body");
const historyPick = document.getElementById("history-pick");
const historySelect = document.getElementById("history-employee");
const historyList = document.getElementById("staff-history");
const historyForm = document.getElementById("history-form");
const historyTitle = document.getElementById("history-title");

let currentUser = null;
let isManager = false;
let chart = [];
let departments = [];
let positions = [];
let historyEmployeeId = null;

document.getElementById("logout-button").addEventListener("click", logout);

function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function pad(number) {
  return String(number).padStart(2, "0");
}

function todayIso() {
  const now = new Date();
  return now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
}

function formatDate(iso) {
  return iso.slice(8, 10) + "." + iso.slice(5, 7) + "." + iso.slice(0, 4);
}

function buildSelect(items, labelOf, selected, emptyLabel) {
  const select = document.createElement("select");
  select.append(new Option(emptyLabel, ""));
  for (const item of items) select.append(new Option(labelOf(item), item.id));
  select.value = selected ? String(selected) : "";
  return select;
}

// ---------- Дерево ----------
function renderTree() {
  const ids = new Set(chart.map((employee) => employee.id));
  const byManager = {};
  for (const employee of chart) {
    const key = employee.manager_id && ids.has(employee.manager_id) ? employee.manager_id : 0;
    (byManager[key] = byManager[key] || []).push(employee);
  }

  const visited = new Set();
  function branch(parentId) {
    const list = el("ul", "tree");
    for (const employee of byManager[parentId] || []) {
      if (visited.has(employee.id)) continue;
      visited.add(employee.id);

      const item = el("li");
      const meta = [employee.position, employee.department].filter(Boolean).join(", ");
      item.append(el("strong", "", employee.full_name), el("span", "muted", meta ? " — " + meta : ""));
      const sub = branch(employee.id);
      if (sub.children.length > 0) item.append(sub);
      list.append(item);
    }
    return list;
  }

  treeBox.replaceChildren(branch(0));
}

// ---------- Отделы и должности ----------
function renderCatalog(box, items, labelOf, urlBase, reload) {
  if (items.length === 0) {
    box.replaceChildren(el("p", "muted", "Пока пусто"));
    return;
  }
  const rows = items.map((item) => {
    const row = el("div", "catalog-item");
    row.append(el("span", "", labelOf(item)));
    const remove = el("button", "button-secondary button-small", "Удалить");
    remove.type = "button";
    remove.addEventListener("click", async () => {
      if (!confirm("Удалить «" + labelOf(item) + "»?")) return;
      try {
        await api(urlBase + "/" + item.id, { method: "DELETE" });
        await reload();
      } catch (error) {
        alert(error.message);
      }
    });
    row.append(remove);
    return row;
  });
  box.replaceChildren(...rows);
}

async function reloadDepartments() {
  departments = await api("/org/departments");
  renderCatalog(
    document.getElementById("departments-list"),
    departments,
    (item) => item.name,
    "/org/departments",
    reloadDepartments
  );
  renderAssignments();
}

async function reloadPositions() {
  positions = await api("/org/positions");
  renderCatalog(
    document.getElementById("positions-list"),
    positions,
    (item) => item.title,
    "/org/positions",
    reloadPositions
  );
  renderAssignments();
}

function onSubmit(form, handler) {
  const errorBox = form.nextElementSibling && form.nextElementSibling.classList.contains("form-error")
    ? form.nextElementSibling
    : form.querySelector(".form-error");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.textContent = "";
    try {
      await handler(form.elements);
    } catch (error) {
      errorBox.textContent = error.message;
    }
  });
}

onSubmit(document.getElementById("department-form"), async (f) => {
  const name = f.name.value.trim();
  if (!name) throw new Error("Введите название");
  await api("/org/departments", { method: "POST", body: { name } });
  f.name.value = "";
  await reloadDepartments();
});

onSubmit(document.getElementById("position-form"), async (f) => {
  const name = f.name.value.trim();
  if (!name) throw new Error("Введите название");
  await api("/org/positions", { method: "POST", body: { name } });
  f.name.value = "";
  await reloadPositions();
});

// ---------- Назначения ----------
async function reloadChart() {
  chart = await api("/org/chart");
  renderTree();
  renderAssignments();
}

function renderAssignments() {
  if (!isManager) return;

  const rows = chart.map((employee) => {
    const row = el("tr");
    row.append(el("td", "", employee.full_name));

    const department = buildSelect(departments, (item) => item.name, employee.department_id, "—");
    const position = buildSelect(positions, (item) => item.title, employee.position_id, "—");
    const manager = buildSelect(
      chart.filter((other) => other.id !== employee.id),
      (item) => item.full_name,
      employee.manager_id,
      "Нет руководителя"
    );

    const save = el("button", "button-small", "Сохранить");
    save.type = "button";
    save.addEventListener("click", async () => {
      save.disabled = true;
      try {
        await api("/org/employees/" + employee.id + "/assignment", {
          method: "PUT",
          body: {
            department_id: department.value ? Number(department.value) : null,
            position_id: position.value ? Number(position.value) : null,
            manager_id: manager.value ? Number(manager.value) : null,
          },
        });
        await reloadChart();
        await loadHistory();
      } catch (error) {
        alert(error.message);
        save.disabled = false;
      }
    });

    for (const control of [department, position, manager, save]) {
      const cell = el("td");
      cell.append(control);
      row.append(cell);
    }
    return row;
  });
  assignBody.replaceChildren(...rows);
}

// ---------- История кадров ----------
async function loadHistory() {
  const items = await api("/org/history/" + historyEmployeeId);
  if (items.length === 0) {
    historyList.replaceChildren(el("li", "muted", "Записей пока нет"));
    return;
  }
  const lines = items.map((entry) => {
    let text = formatDate(entry.event_date) + " · " + (EVENT_NAMES[entry.event_type] || entry.event_type);
    if (entry.related_employee) text += " (" + entry.related_employee.full_name + ")";
    if (entry.comment) text += ": " + entry.comment;
    return el("li", "", text);
  });
  historyList.replaceChildren(...lines);
}

function fillRelated() {
  const select = historyForm.elements.related_employee_id;
  select.replaceChildren();
  for (const employee of chart) {
    if (employee.id !== historyEmployeeId) select.append(new Option(employee.full_name, employee.id));
  }
}

function syncHistoryForm() {
  document.getElementById("h-related-box").hidden = historyForm.elements.event_type.value !== "replaced";
}

historyForm.elements.event_type.addEventListener("change", syncHistoryForm);

onSubmit(historyForm, async (f) => {
  const type = f.event_type.value;
  await api("/org/history/" + historyEmployeeId, {
    method: "POST",
    body: {
      event_type: type,
      event_date: f.event_date.value || null,
      comment: f.comment.value.trim(),
      related_employee_id: type === "replaced" && f.related_employee_id.value
        ? Number(f.related_employee_id.value)
        : null,
    },
  });
  f.comment.value = "";
  await loadHistory();
});

historySelect.addEventListener("change", async () => {
  historyEmployeeId = Number(historySelect.value);
  fillRelated();
  await loadHistory();
});

// ---------- Старт ----------
(async () => {
  currentUser = await requireUser();
  if (!currentUser) return;
  document.getElementById("user-name").textContent = currentUser.full_name;
  isManager = ["admin", "hr"].includes(currentUser.role);

  chart = await api("/org/chart");
  renderTree();
  historyEmployeeId = currentUser.id;

  if (isManager) {
    catalogs.hidden = false;
    assignCard.hidden = false;
    historyPick.hidden = false;
    historyForm.hidden = false;
    historyForm.elements.event_date.value = todayIso();

    for (const employee of chart) {
      historySelect.append(new Option(employee.full_name, employee.id));
    }
    historySelect.value = String(currentUser.id);
    fillRelated();
    syncHistoryForm();

    await Promise.all([reloadDepartments(), reloadPositions()]);
  } else {
    historyTitle.textContent = "Моя история в компании";
  }

  await loadHistory();
})();