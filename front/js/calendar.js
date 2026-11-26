const KIND_NAMES = { task: "Срок задачи", meeting: "Встреча", assembly: "Собрание" };
const MONTH_NAMES = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
];
const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

const grid = document.getElementById("calendar-grid");
const monthTitle = document.getElementById("month-title");
const dayTitle = document.getElementById("day-title");
const dayList = document.getElementById("day-list");
const form = document.getElementById("event-form");
const formError = document.getElementById("event-error");
const participantsSelect = document.getElementById("e-participants");

let currentUser = null;
let viewYear;
let viewMonth; // 0-11
let selectedDay = null; // "YYYY-MM-DD"
let itemsByDay = {};

document.getElementById("logout-button").addEventListener("click", logout);

function pad(number) {
  return String(number).padStart(2, "0");
}

function dayKey(year, month, day) {
  return year + "-" + pad(month + 1) + "-" + pad(day);
}

function todayKey() {
  const now = new Date();
  return dayKey(now.getFullYear(), now.getMonth(), now.getDate());
}

// Сервер отдаёт время без часового пояса: "2026-11-20T14:00:00"
function timeOf(iso) {
  return iso.slice(11, 16);
}

async function loadMonth() {
  const start = dayKey(viewYear, viewMonth, 1) + "T00:00:00";
  const next = new Date(viewYear, viewMonth + 1, 1);
  const end = dayKey(next.getFullYear(), next.getMonth(), 1) + "T00:00:00";

  const items = await api(
    "/calendar?start=" + encodeURIComponent(start) + "&end=" + encodeURIComponent(end)
  );

  itemsByDay = {};
  for (const item of items) {
    const key = item.starts_at.slice(0, 10);
    (itemsByDay[key] = itemsByDay[key] || []).push(item);
  }
  render();
}

function chip(item) {
  const element = document.createElement("div");
  element.className = "chip chip-" + item.kind;
  element.textContent = timeOf(item.starts_at) + " " + item.title;
  return element;
}

function dayCell(day) {
  const key = dayKey(viewYear, viewMonth, day);
  const cell = document.createElement("button");
  cell.type = "button";
  cell.className = "day";
  if (key === todayKey()) cell.classList.add("today");
  if (key === selectedDay) cell.classList.add("selected");

  const number = document.createElement("span");
  number.className = "day-number";
  number.textContent = day;
  cell.append(number);

  const items = itemsByDay[key] || [];
  items.slice(0, 3).forEach((item) => cell.append(chip(item)));
  if (items.length > 3) {
    const more = document.createElement("div");
    more.className = "chip-more";
    more.textContent = "ещё " + (items.length - 3);
    cell.append(more);
  }

  cell.addEventListener("click", () => selectDay(key));
  return cell;
}

function renderGrid() {
  monthTitle.textContent = MONTH_NAMES[viewMonth] + " " + viewYear;

  const headers = WEEKDAYS.map((name) => {
    const element = document.createElement("div");
    element.className = "weekday";
    element.textContent = name;
    return element;
  });

  // Неделя начинается с понедельника
  const offset = (new Date(viewYear, viewMonth, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

  const cells = [];
  for (let i = 0; i < offset; i++) {
    const empty = document.createElement("div");
    empty.className = "day-empty";
    cells.push(empty);
  }
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push(dayCell(day));
  }
  grid.replaceChildren(...headers, ...cells);
}

function addLine(box, text) {
  const line = document.createElement("div");
  line.className = "muted day-line";
  line.textContent = text;
  box.append(line);
}

function renderItem(item) {
  const box = document.createElement("div");
  box.className = "day-item";

  const title = document.createElement("strong");
  title.textContent = item.title;
  box.append(title);

  if (item.kind === "task") {
    addLine(box, KIND_NAMES.task + ": до " + timeOf(item.starts_at));
  } else {
    addLine(box, KIND_NAMES[item.kind] + ", " + timeOf(item.starts_at) + "–" + timeOf(item.ends_at));
    addLine(box, "Организатор: " + item.organizer);
    if (item.participants.length > 0) {
      addLine(box, "Участники: " + item.participants.join(", "));
    }
  }
  if (item.place) addLine(box, "Место: " + item.place);

  if (item.kind === "task") {
    const link = document.createElement("a");
    link.href = "/tasks.html";
    link.textContent = "Открыть задачи";
    box.append(link);
  }

  if (item.can_delete) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button-secondary button-small";
    button.textContent = "Удалить";
    button.addEventListener("click", async () => {
      if (!confirm("Удалить «" + item.title + "»?")) return;
      try {
        await api("/calendar/events/" + item.id, { method: "DELETE" });
        await loadMonth();
      } catch (error) {
        alert(error.message);
      }
    });
    box.append(button);
  }
  return box;
}

function renderDayList() {
  if (!selectedDay) {
    dayTitle.textContent = "Выберите день";
    dayList.replaceChildren();
    return;
  }

  const date = new Date(selectedDay + "T00:00:00");
  dayTitle.textContent = date.toLocaleDateString("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  const items = itemsByDay[selectedDay] || [];
  if (items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "На этот день ничего нет";
    dayList.replaceChildren(empty);
    return;
  }
  dayList.replaceChildren(...items.map(renderItem));
}

function render() {
  renderGrid();
  renderDayList();
}

function selectDay(key) {
  selectedDay = key;
  form.elements.date.value = key;
  render();
}

function shiftMonth(delta) {
  const date = new Date(viewYear, viewMonth + delta, 1);
  viewYear = date.getFullYear();
  viewMonth = date.getMonth();
  selectedDay = null;
  loadMonth();
}

document.getElementById("prev-month").addEventListener("click", () => shiftMonth(-1));
document.getElementById("next-month").addEventListener("click", () => shiftMonth(1));
document.getElementById("today-button").addEventListener("click", () => {
  const now = new Date();
  viewYear = now.getFullYear();
  viewMonth = now.getMonth();
  selectedDay = todayKey();
  form.elements.date.value = selectedDay;
  loadMonth();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.textContent = "";

  const fields = form.elements;
  const title = fields.title.value.trim();
  const date = fields.date.value;
  const start = fields.start.value;
  const end = fields.end.value;

  if (!title || !date || !start || !end) {
    formError.textContent = "Заполните название, дату и время";
    return;
  }
  if (end <= start) {
    formError.textContent = "Время окончания должно быть позже начала";
    return;
  }

  const body = {
    title,
    kind: fields.kind.value,
    place: fields.place.value.trim(),
    starts_at: date + "T" + start + ":00",
    ends_at: date + "T" + end + ":00",
    participant_ids: Array.from(participantsSelect.selectedOptions).map((option) => Number(option.value)),
  };

  try {
    await api("/calendar/events", { method: "POST", body });
    viewYear = Number(date.slice(0, 4));
    viewMonth = Number(date.slice(5, 7)) - 1;
    selectedDay = date;
    form.reset();
    fields.date.value = date;
    await loadMonth();
  } catch (error) {
    formError.textContent = error.message;
  }
});

(async () => {
  currentUser = await requireUser();
  if (!currentUser) return;
  document.getElementById("user-name").textContent = currentUser.full_name;

  const employees = await api("/employees/directory");
  for (const employee of employees) {
    if (employee.id !== currentUser.id) {
      participantsSelect.append(new Option(employee.full_name, employee.id));
    }
  }

  const now = new Date();
  viewYear = now.getFullYear();
  viewMonth = now.getMonth();
  selectedDay = todayKey();
  form.elements.date.value = selectedDay;
  await loadMonth();
})();