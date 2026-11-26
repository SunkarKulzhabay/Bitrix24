const STATUS_NAMES = {
  draft: "Черновик",
  on_approval: "На одобрении",
  approved: "Одобрен",
  rejected: "Отклонён",
};

const templateSelect = document.getElementById("d-template");
const fieldsBox = document.getElementById("d-fields");
const form = document.getElementById("document-form");
const formError = document.getElementById("document-error");
const listBox = document.getElementById("documents-list");
const tabs = document.querySelectorAll(".tab");
const approvalTab = document.querySelector('[data-view="approval"]');

let templates = [];
let currentView = "mine";

document.getElementById("logout-button").addEventListener("click", logout);

function renderFields() {
  fieldsBox.replaceChildren();
  const template = templates.find((item) => item.id === Number(templateSelect.value));
  if (!template) return;

  for (const field of template.fields) {
    const wrap = document.createElement("div");
    if (field.type === "textarea") wrap.className = "span-all";

    const label = document.createElement("label");
    label.htmlFor = "field-" + field.key;
    label.textContent = field.label;

    let input;
    if (field.type === "textarea") {
      input = document.createElement("textarea");
      input.rows = 5;
    } else {
      input = document.createElement("input");
      input.type = field.type === "date" ? "date" : field.type === "number" ? "number" : "text";
      if (field.type === "number") {
        input.min = "0";
        input.step = "1";
      }
    }
    input.id = "field-" + field.key;
    input.dataset.key = field.key;

    wrap.append(label, input);
    fieldsBox.append(wrap);
  }
}

function renderRow(doc) {
  const row = document.createElement("a");
  row.className = "doc-row";
  row.href = "/document.html?id=" + doc.id;

  const info = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = doc.title + " № " + doc.number;
  const meta = document.createElement("div");
  meta.className = "muted";
  meta.textContent =
    doc.requester.full_name + " · " + new Date(doc.created_at).toLocaleDateString("ru-RU");
  info.append(title, meta);

  const badge = document.createElement("span");
  badge.className = "badge status-" + doc.status;
  badge.textContent = STATUS_NAMES[doc.status];

  row.append(info, badge);
  return row;
}

async function loadLists() {
  const [mine, approval] = await Promise.all([
    api("/documents?view=mine"),
    api("/documents?view=approval"),
  ]);
  approvalTab.textContent = "На одобрении у меня (" + approval.length + ")";

  const items = currentView === "mine" ? mine : approval;
  if (items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Документов нет";
    listBox.replaceChildren(empty);
    return;
  }
  listBox.replaceChildren(...items.map(renderRow));
}

for (const tab of tabs) {
  tab.addEventListener("click", async () => {
    currentView = tab.dataset.view;
    tabs.forEach((item) => item.classList.toggle("active", item === tab));
    await loadLists();
  });
}

templateSelect.addEventListener("change", renderFields);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.textContent = "";

  const values = {};
  for (const input of fieldsBox.querySelectorAll("[data-key]")) {
    values[input.dataset.key] = input.value.trim();
  }

  try {
    const created = await api("/documents", {
      method: "POST",
      body: {
        template_id: Number(templateSelect.value),
        values,
        with_stamp: form.elements.with_stamp.checked,
      },
    });
    window.location.href = "/document.html?id=" + created.id;
  } catch (error) {
    formError.textContent = error.message;
  }
});

(async () => {
  const user = await requireUser();
  if (!user) return;
  document.getElementById("user-name").textContent = user.full_name;

  templates = await api("/documents/templates");
  for (const template of templates) {
    templateSelect.append(new Option(template.name, template.id));
  }
  renderFields();
  await loadLists();
})();