const STATUS_NAMES = {
  pending: "В ожидании",
  in_progress: "В работе",
  in_review: "На проверке",
  rework: "На доработке",
  done: "Завершена",
};

const PRIORITY_NAMES = {
  urgent_important: "Срочно и важно",
  important_not_urgent: "Важно, не срочно",
  urgent_not_important: "Срочно, не важно",
  not_urgent_not_important: "Не срочно, не важно",
};

// Подпись кнопки для перехода в статус
const ACTION_LABELS = {
  in_progress: "Принять в работу",
  in_review: "Отправить на проверку",
  done: "Принять работу",
  rework: "Вернуть на доработку",
};

const listBox = document.getElementById("tasks-list");
const form = document.getElementById("task-form");
const formError = document.getElementById("task-error");
const assigneeSelect = document.getElementById("t-assignee");
const supervisorSelect = document.getElementById("t-supervisor");
const tabs = document.querySelectorAll(".tab");

let currentUser = null;
let currentView = "all";

document.getElementById("logout-button").addEventListener("click", logout);

function formatDate(iso) {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderTask(task) {
  const card = document.createElement("article");
  card.className = "task-card priority-" + task.priority;

  const head = document.createElement("div");
  head.className = "task-head";
  const title = document.createElement("h3");
  title.textContent = task.title;
  const badge = document.createElement("span");
  badge.className = "badge status-" + task.status;
  badge.textContent = STATUS_NAMES[task.status];
  head.append(title, badge);
  card.append(head);

  const meta = document.createElement("p");
  meta.className = "muted task-meta";
  meta.textContent =
    PRIORITY_NAMES[task.priority] +
    " · Исполнитель: " + task.assignee.full_name +
    " · Ответственный: " + task.responsible.full_name +
    " · Поставил: " + task.creator.full_name;
  card.append(meta);

  const deadline = document.createElement("p");
  deadline.className = "task-deadline";
  if (task.deadline) {
    deadline.textContent = "Срок: " + formatDate(task.deadline);
    if (task.status !== "done" && new Date(task.deadline) < new Date()) {
      deadline.classList.add("overdue");
      deadline.textContent += " (просрочено)";
    }
  } else {
    deadline.textContent = "Срок не указан";
  }
  card.append(deadline);

  if (task.description) {
    const description = document.createElement("p");
    description.className = "task-description";
    description.textContent = task.description;
    card.append(description);
  }

  if (task.available_statuses.length > 0) {
    const actions = document.createElement("div");
    actions.className = "actions";
    for (const nextStatus of task.available_statuses) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = nextStatus === "rework" ? "button-secondary button-small" : "button-small";
      button.textContent = ACTION_LABELS[nextStatus];
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await api("/tasks/" + task.id + "/status", { method: "POST", body: { status: nextStatus } });
          await loadTasks();
        } catch (error) {
          alert(error.message);
          button.disabled = false;
        }
      });
      actions.append(button);
    }
    card.append(actions);
  }

  return card;
}

async function loadTasks() {
  const tasks = await api("/tasks?view=" + currentView);
  if (tasks.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Задач нет";
    listBox.replaceChildren(empty);
    return;
  }
  listBox.replaceChildren(...tasks.map(renderTask));
}

function fillEmployees(employees) {
  const noSupervisor = new Option("Без руководителя", "");
  supervisorSelect.append(noSupervisor);
  for (const employee of employees) {
    assigneeSelect.append(new Option(employee.full_name, employee.id));
    supervisorSelect.append(new Option(employee.full_name, employee.id));
  }
  assigneeSelect.value = String(currentUser.id);
}

for (const tab of tabs) {
  tab.addEventListener("click", async () => {
    currentView = tab.dataset.view;
    tabs.forEach((item) => item.classList.toggle("active", item === tab));
    await loadTasks();
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.textContent = "";

  const body = {
    title: form.elements.title.value.trim(),
    description: form.elements.description.value.trim(),
    priority: form.elements.priority.value,
    deadline: form.elements.deadline.value || null,
    assignee_id: Number(form.elements.assignee_id.value),
    supervisor_id: form.elements.supervisor_id.value ? Number(form.elements.supervisor_id.value) : null,
  };
  if (!body.title) {
    formError.textContent = "Введите название задачи";
    return;
  }

  try {
    await api("/tasks", { method: "POST", body });
    form.reset();
    assigneeSelect.value = String(currentUser.id);
    await loadTasks();
  } catch (error) {
    formError.textContent = error.message;
  }
});

(async () => {
  currentUser = await requireUser();
  if (!currentUser) return;

  document.getElementById("user-name").textContent = currentUser.full_name;
  fillEmployees(await api("/employees/directory"));
  await loadTasks();
})();