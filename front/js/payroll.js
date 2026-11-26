const MODE_NAMES = {
  proportional: "пропорционально",
  all_or_nothing: "всё или ничего",
};

const monthInput = document.getElementById("month");
const employeePick = document.getElementById("employee-pick");
const employeeSelect = document.getElementById("employee");
const summaryBox = document.getElementById("summary");
const summaryTitle = document.getElementById("summary-title");
const overviewCard = document.getElementById("overview-card");
const overviewBody = document.getElementById("overview-body");
const financeTools = document.getElementById("finance-tools");
const penaltyCard = document.getElementById("penalty-card");

const salaryForm = document.getElementById("salary-form");
const entryForm = document.getElementById("entry-form");
const metricForm = document.getElementById("metric-form");
const resultForm = document.getElementById("result-form");
const penaltyForm = document.getElementById("penalty-form");
const metricsList = document.getElementById("metrics-list");

let currentUser = null;
let isFinance = false;
let canFine = false;
let selectedEmployeeId = null;
let directory = [];

document.getElementById("logout-button").addEventListener("click", logout);

function pad(number) {
  return String(number).padStart(2, "0");
}

function fmt(value) {
  return Number(value).toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDate(iso) {
  return iso.slice(8, 10) + "." + iso.slice(5, 7) + "." + iso.slice(0, 4);
}

function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function deleteButton(url, question) {
  const button = el("button", "button-secondary button-small", "Удалить");
  button.type = "button";
  button.addEventListener("click", async () => {
    if (!confirm(question)) return;
    try {
      await api(url, { method: "DELETE" });
      await loadAll();
    } catch (error) {
      alert(error.message);
    }
  });
  return button;
}

// ---------- Расчёт ----------
function payRow(label, value, className) {
  const row = el("div", "pay-row" + (className ? " " + className : ""));
  row.append(el("span", "", label), el("span", "pay-amount", value));
  return row;
}

function payBlock(label, value, content) {
  const block = el("details", "pay-block");
  const head = el("summary");
  head.append(el("span", "", label), el("span", "pay-amount", value));
  block.append(head, content);
  return block;
}

function projectsContent(data) {
  const box = el("div", "pay-detail");
  if (data.projects.length === 0) {
    box.append(el("p", "muted", "Записей в табеле за этот месяц нет"));
    return box;
  }
  for (const project of data.projects) {
    const title = el("div", "pay-project");
    title.append(
      el("strong", "", project.project_name),
      el("span", "muted", fmt(project.hours) + " ч · " + fmt(project.amount))
    );
    const list = el("ul", "history");
    for (const entry of project.entries) {
      const item = el("li");
      const text =
        formatDate(entry.work_date) + " · " + (entry.description || "без описания") +
        " · " + fmt(entry.hours) + " ч · " + fmt(entry.amount);
      item.append(el("span", "", text));
      if (isFinance) {
        item.append(deleteButton("/payroll/entries/" + entry.id, "Удалить запись из табеля?"));
      }
      list.append(item);
    }
    box.append(title, list);
  }
  return box;
}

function kpiContent(data) {
  const box = el("div", "pay-detail");
  if (data.kpi.length === 0) {
    box.append(el("p", "muted", "Результатов KPI за этот месяц нет"));
    return box;
  }
  const list = el("ul", "history");
  for (const line of data.kpi) {
    const item = el("li");
    item.append(
      el(
        "span",
        "",
        line.name + ": факт " + fmt(line.actual_value) + " из " + fmt(line.target_value) +
          " (" + MODE_NAMES[line.mode] + ", максимум " + fmt(line.max_bonus) + ") → премия " + fmt(line.bonus)
      )
    );
    list.append(item);
  }
  box.append(list);
  return box;
}

function penaltiesContent(data) {
  const box = el("div", "pay-detail");
  if (data.penalties.length === 0) {
    box.append(el("p", "muted", "Штрафов за этот месяц нет"));
    return box;
  }
  const list = el("ul", "history");
  for (const penalty of data.penalties) {
    const item = el("li");
    item.append(
      el(
        "span",
        "",
        formatDate(penalty.issued_at) + " · " + penalty.reason + " · " + fmt(penalty.amount) +
          " (назначил: " + penalty.issued_by + ")"
      )
    );
    if (penalty.can_delete) {
      item.append(deleteButton("/payroll/penalties/" + penalty.id, "Удалить штраф?"));
    }
    list.append(item);
  }
  box.append(list);
  return box;
}

function renderSummary(data) {
  summaryTitle.textContent = "Расчёт: " + data.employee.full_name;

  const total = payRow("Итого к выплате", fmt(data.total), "pay-total");
  summaryBox.replaceChildren(
    payRow("Оклад", fmt(data.base_salary)),
    payBlock("Заработано по проектам", fmt(data.projects_total), projectsContent(data)),
    payBlock("Премия KPI", fmt(data.kpi_total), kpiContent(data)),
    payBlock("Штрафы", "− " + fmt(data.penalties_total), penaltiesContent(data)),
    total
  );
}

// ---------- Сводная таблица ----------
function renderOverview(rows) {
  const trs = rows.map((row) => {
    const tr = el("tr", "row-click");
    for (const text of [
      row.employee.full_name,
      fmt(row.base_salary),
      fmt(row.projects_total),
      fmt(row.kpi_total),
      fmt(row.penalties_total),
      fmt(row.total),
    ]) {
      tr.append(el("td", "", text));
    }
    tr.addEventListener("click", () => {
      selectedEmployeeId = row.employee.id;
      employeeSelect.value = String(row.employee.id);
      loadAll();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    return tr;
  });
  overviewBody.replaceChildren(...trs);
}

// ---------- Загрузка ----------
function syncEntryDate() {
  const field = entryForm.elements.work_date;
  if (!field.value.startsWith(monthInput.value)) {
    field.value = monthInput.value + "-01";
  }
}

async function loadAll() {
  const month = monthInput.value;
  if (!month) return;

  try {
    const data = await api("/payroll/summary?month=" + month + "&employee_id=" + selectedEmployeeId);
    renderSummary(data);
    if (isFinance) {
      salaryForm.elements.base_salary.value = data.base_salary;
      syncEntryDate();
      renderOverview(await api("/payroll/overview?month=" + month));
    }
  } catch (error) {
    alert(error.message);
  }
}

async function loadMetrics() {
  const metrics = await api("/payroll/kpi/metrics");

  const select = resultForm.elements.metric_id;
  select.replaceChildren(...metrics.map((metric) => new Option(metric.name, metric.id)));

  const items = metrics.map((metric) => {
    const item = el("li");
    item.append(
      el(
        "span",
        "",
        metric.name + ": цель " + fmt(metric.target_value) + ", премия " + fmt(metric.bonus_amount) +
          " (" + MODE_NAMES[metric.mode] + ")"
      )
    );
    const archive = el("button", "button-secondary button-small", "В архив");
    archive.type = "button";
    archive.addEventListener("click", async () => {
      if (!confirm("Убрать метрику «" + metric.name + "»? Старые результаты сохранятся.")) return;
      try {
        await api("/payroll/kpi/metrics/" + metric.id, { method: "DELETE" });
        await loadMetrics();
      } catch (error) {
        alert(error.message);
      }
    });
    item.append(archive);
    return item;
  });
  metricsList.replaceChildren(...items);
}

// ---------- Формы ----------
function onSubmit(form, handler) {
  const errorBox = form.querySelector(".form-error");
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

onSubmit(salaryForm, async (f) => {
  await api("/payroll/salary/" + selectedEmployeeId, {
    method: "PUT",
    body: { base_salary: Number(f.base_salary.value || 0) },
  });
  await loadAll();
});

onSubmit(entryForm, async (f) => {
  if (!f.project_id.value) throw new Error("Выберите проект");
  if (!f.work_date.value) throw new Error("Укажите дату");
  await api("/payroll/entries", {
    method: "POST",
    body: {
      employee_id: selectedEmployeeId,
      project_id: Number(f.project_id.value),
      work_date: f.work_date.value,
      hours: Number(f.hours.value || 0),
      amount: Number(f.amount.value || 0),
      description: f.description.value.trim(),
    },
  });
  f.hours.value = "";
  f.amount.value = "";
  f.description.value = "";
  await loadAll();
});

onSubmit(metricForm, async (f) => {
  const name = f.metric_name.value.trim();
  if (!name) throw new Error("Введите название метрики");
  if (!(Number(f.target_value.value) > 0)) throw new Error("Цель должна быть больше нуля");
  await api("/payroll/kpi/metrics", {
    method: "POST",
    body: {
      name,
      target_value: Number(f.target_value.value),
      bonus_amount: Number(f.bonus_amount.value || 0),
      mode: f.mode.value,
    },
  });
  metricForm.reset();
  await loadMetrics();
});

onSubmit(resultForm, async (f) => {
  if (!f.metric_id.value) throw new Error("Сначала добавьте метрику");
  if (f.actual_value.value === "") throw new Error("Введите фактическое значение");
  await api("/payroll/kpi/results", {
    method: "PUT",
    body: {
      employee_id: selectedEmployeeId,
      metric_id: Number(f.metric_id.value),
      month: monthInput.value,
      actual_value: Number(f.actual_value.value),
    },
  });
  f.actual_value.value = "";
  await loadAll();
});

onSubmit(penaltyForm, async (f) => {
  const reason = f.reason.value.trim();
  if (!reason) throw new Error("Укажите причину");
  if (!(Number(f.amount.value) > 0)) throw new Error("Сумма штрафа должна быть больше нуля");
  await api("/payroll/penalties", {
    method: "POST",
    body: {
      employee_id: Number(f.employee_id.value),
      reason,
      amount: Number(f.amount.value),
      issued_at: f.issued_at.value || null,
    },
  });
  f.reason.value = "";
  f.amount.value = "";
  await loadAll();
});

monthInput.addEventListener("change", loadAll);
employeeSelect.addEventListener("change", () => {
  selectedEmployeeId = Number(employeeSelect.value);
  loadAll();
});

// ---------- Старт ----------
(async () => {
  currentUser = await requireUser();
  if (!currentUser) return;
  document.getElementById("user-name").textContent = currentUser.full_name;

  isFinance = ["admin", "accountant"].includes(currentUser.role);
  canFine = ["admin", "manager"].includes(currentUser.role);
  selectedEmployeeId = currentUser.id;

  const now = new Date();
  monthInput.value = now.getFullYear() + "-" + pad(now.getMonth() + 1);

  if (isFinance || canFine) {
    directory = await api("/employees/directory");
  }

  if (isFinance) {
    employeePick.hidden = false;
    overviewCard.hidden = false;
    financeTools.hidden = false;

    for (const employee of directory) {
      employeeSelect.append(new Option(employee.full_name, employee.id));
    }
    employeeSelect.value = String(currentUser.id);

    const projects = await api("/payroll/projects");
    entryForm.elements.project_id.replaceChildren(
      ...projects.map((project) => new Option(project.name, project.id))
    );
    await loadMetrics();
  }

  if (canFine) {
    penaltyCard.hidden = false;
    for (const employee of directory) {
      penaltyForm.elements.employee_id.append(new Option(employee.full_name, employee.id));
    }
    penaltyForm.elements.issued_at.value =
      now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
  }

  await loadAll();
})();