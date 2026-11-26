// Общее меню для всех закрытых страниц.
// Подключается после api.js и auth.js и перед скриптом самой страницы.
(function buildHeader() {
  const header = document.querySelector("header.topbar");
  if (!header) return;

  const links = [
    ["/dashboard.html", "Главная"],
    ["/tasks.html", "Задачи"],
    ["/calendar.html", "Календарь"],
    ["/projects.html", "Проекты"],
    ["/documents.html", "Документы"],
    ["/payroll.html", "Зарплата"],
    ["/org.html", "Оргструктура"],
    ["/employees.html", "Сотрудники"],
  ];

  // Страницы одного объекта подсвечивают свой раздел
  const sections = { "/project.html": "/projects.html", "/document.html": "/documents.html" };
  const path = window.location.pathname;
  const currentSection = sections[path] || path;

  const nav = document.createElement("nav");
  nav.className = "main-nav";
  nav.setAttribute("aria-label", "Разделы");

  const brand = document.createElement("span");
  brand.className = "brand";
  brand.textContent = "Офис CRM";
  nav.append(brand);

  let employeesLink = null;
  for (const [href, name] of links) {
    const link = document.createElement("a");
    link.href = href;
    link.textContent = name;
    if (href === currentSection) link.setAttribute("aria-current", "page");
    if (href === "/employees.html") employeesLink = link;
    nav.append(link);
  }

  // Элементы с этими id используют скрипты страниц
  const userBox = document.createElement("div");
  userBox.className = "topbar-user";
  const userName = document.createElement("a");
  userName.id = "user-name";
  userName.href = "/profile.html";
  userName.title = "Профиль и смена пароля";
  const logoutButton = document.createElement("button");
  logoutButton.id = "logout-button";
  logoutButton.type = "button";
  logoutButton.className = "button-secondary";
  logoutButton.textContent = "Выйти";
  userBox.append(userName, logoutButton);

  header.replaceChildren(nav, userBox);

  // «Сотрудники» только для администратора и HR
  api("/auth/me")
    .then((me) => {
      if (!["admin", "hr"].includes(me.role)) employeesLink.hidden = true;
    })
    .catch(() => {});
})();