const ROLE_NAMES = {
  admin: "Администратор",
  manager: "Руководитель",
  hr: "HR-специалист",
  accountant: "Бухгалтер",
  employee: "Сотрудник",
};

const TASK_STATUS_NAMES = {
  pending: "В ожидании",
  in_progress: "В работе",
  in_review: "На проверке",
  rework: "На доработке",
  done: "Завершена",
};

const KIND_NAMES = { task: "Срок задачи", meeting: "Встреча", assembly: "Собрание" };

document.getElementById("logout-button").addEventListener("click", logout);

function pad(number) {
  return String(number).padStart(2, "0");
}

// Дата для сервера без часового пояса: 2026-11-20T14:00:00
function localIso(date) {
  return (
    date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate()) +
    "T" + pad(date.getHours()) + ":" + pad(date.getMinutes()) + ":00"
  );
}

function shortDateTime(iso) {
  return iso.slice(8, 10) + "." + iso.slice(5, 7) + " " + iso.slice(11, 16);
}

function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

// Если один из запросов не удался, остальные блоки всё равно показываются
async function safe(promise) {
  try {
    return await promise;
  } catch (error) {
    return [];
  }
}

function fillList(box, rows, emptyText) {
  box.replaceChildren(...(rows.length > 0 ? rows : [el("p", "muted", emptyText)]));
}

function itemLink(href, title, metaText, overdue) {
  const link = el("a", "dash-item");
  link.href = href;
  link.append(el("strong", "", title), el("span", overdue ? "overdue" : "muted", metaText));
  return link;
}

function taskMeta(task, now) {
  let text = TASK_STATUS_NAMES[task.status];
  let overdue = false;
  if (task.deadline) {
    text += " · срок " + shortDateTime(task.deadline);
    if (task.status !== "done" && new Date(task.deadline) < now) {
      overdue = true;
      text += " (просрочено)";
    }
  }
  return { text, overdue };
}

(async () => {
  const user = await requireUser();
  if (!user) return;

  document.getElementById("user-name").textContent = user.full_name;
  document.getElementById("greeting").textContent = "Здравствуйте, " + user.full_name;
  document.getElementById("user-role").textContent = ROLE_NAMES[user.role] || user.role;

  const now = new Date();
  const weekLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

  const [assigned, created, approvals, upcoming, projects] = await Promise.all([
    safe(api("/tasks?view=assigned")),
    safe(api("/tasks?view=created")),
    safe(api("/documents?view=approval")),
    safe(
      api(
        "/calendar?start=" + encodeURIComponent(localIso(now)) +
          "&end=" + encodeURIComponent(localIso(weekLater))
      )
    ),
    safe(api("/projects")),
  ]);

  const activeTasks = assigned.filter((task) => task.status !== "done");
  const overdueTasks = activeTasks.filter((task) => task.deadline && new Date(task.deadline) < now);
  const reviewTasks = created.filter((task) => task.status === "in_review");
  const activeProjects = projects.filter((project) => !["done", "refused", "paused"].includes(project.stage));

  // Сводка
  document.getElementById("stat-tasks").textContent = activeTasks.length;
  document.getElementById("stat-overdue").textContent = overdueTasks.length;
  document.getElementById("stat-overdue-box").classList.toggle("warn", overdueTasks.length > 0);
  document.getElementById("stat-review").textContent = reviewTasks.length;
  document.getElementById("stat-docs").textContent = approvals.length;
  document.getElementById("stat-projects").textContent = activeProjects.length;

  // Мои задачи (первые 6, срочные по сроку уже отсортированы сервером)
  fillList(
    document.getElementById("my-tasks"),
    activeTasks.slice(0, 6).map((task) => {
      const meta = taskMeta(task, now);
      return itemLink("/tasks.html", task.title, meta.text, meta.overdue);
    }),
    "Активных задач нет"
  );

  // Ждут моей проверки
  fillList(
    document.getElementById("review-tasks"),
    reviewTasks.slice(0, 6).map((task) =>
      itemLink("/tasks.html", task.title, "Исполнитель: " + task.assignee.full_name, false)
    ),
    "Ничего не ждёт проверки"
  );

  // Ближайшие 7 дней
  fillList(
    document.getElementById("upcoming"),
    upcoming.slice(0, 8).map((item) =>
      itemLink(
        item.kind === "task" ? "/tasks.html" : "/calendar.html",
        item.title,
        shortDateTime(item.starts_at) + " · " + KIND_NAMES[item.kind],
        false
      )
    ),
    "На ближайшую неделю ничего нет"
  );

  // Документы на одобрении
  fillList(
    document.getElementById("approval-docs"),
    approvals.slice(0, 6).map((doc) =>
      itemLink("/document.html?id=" + doc.id, doc.title + " № " + doc.number, "От: " + doc.requester.full_name, false)
    ),
    "Документов на одобрении нет"
  );
})();