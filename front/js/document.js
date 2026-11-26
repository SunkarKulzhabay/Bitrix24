const STATUS_NAMES = {
  draft: "Черновик",
  on_approval: "На одобрении",
  approved: "Одобрен",
  rejected: "Отклонён",
};

const APPROVAL_NAMES = {
  waiting: "ожидает решения",
  approved: "одобрил(а)",
  rejected: "отклонил(а)",
};

const documentId = Number(new URLSearchParams(window.location.search).get("id"));

const sendCard = document.getElementById("send-card");
const sendForm = document.getElementById("send-form");
const sendError = document.getElementById("send-error");
const approverSelect = document.getElementById("approver");
const decideCard = document.getElementById("decide-card");
const decideError = document.getElementById("decide-error");
const commentInput = document.getElementById("decision-comment");

let doc = null;
let currentUser = null;
let directory = [];

document.getElementById("logout-button").addEventListener("click", logout);
document.getElementById("print-button").addEventListener("click", () => window.print());

function renderApprovals() {
  if (doc.approvals.length === 0) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent = "Документ ещё не отправлялся на одобрение";
    document.getElementById("approvals").replaceChildren(empty);
    return;
  }

  const items = doc.approvals.map((approval) => {
    const item = document.createElement("li");
    let text = approval.approver.full_name + ": " + APPROVAL_NAMES[approval.status];
    if (approval.decided_at) {
      text += " (" + new Date(approval.decided_at).toLocaleString("ru-RU") + ")";
    }
    if (approval.comment) text += ". Комментарий: " + approval.comment;
    item.textContent = text;
    return item;
  });
  document.getElementById("approvals").replaceChildren(...items);
}

function render() {
  const heading = doc.title + " № " + doc.number;
  document.title = heading + " — Офис CRM";
  document.getElementById("doc-title").textContent = heading;

  const badge = document.getElementById("doc-status");
  badge.textContent = STATUS_NAMES[doc.status];
  badge.className = "badge status-" + doc.status;

  // Текст вставляется как текст, а не как HTML
  document.getElementById("doc-text").textContent = doc.content;
  const stamp = document.getElementById("stamp");
  stamp.hidden = !doc.with_stamp;
  stamp.textContent = doc.stamp_text;

  sendCard.hidden = !doc.can_send;
  decideCard.hidden = !doc.can_decide;
  renderApprovals();
}

sendForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  sendError.textContent = "";
  if (!approverSelect.value) {
    sendError.textContent = "Выберите сотрудника";
    return;
  }
  try {
    doc = await api("/documents/" + documentId + "/send", {
      method: "POST",
      body: { approver_id: Number(approverSelect.value) },
    });
    render();
  } catch (error) {
    sendError.textContent = error.message;
  }
});

async function decide(decision) {
  decideError.textContent = "";
  try {
    doc = await api("/documents/" + documentId + "/decision", {
      method: "POST",
      body: { decision, comment: commentInput.value.trim() },
    });
    commentInput.value = "";
    render();
  } catch (error) {
    decideError.textContent = error.message;
  }
}

document.getElementById("approve-button").addEventListener("click", () => decide("approved"));
document.getElementById("reject-button").addEventListener("click", () => decide("rejected"));

(async () => {
  currentUser = await requireUser();
  if (!currentUser) return;
  document.getElementById("user-name").textContent = currentUser.full_name;

  if (!documentId) {
    window.location.href = "/documents.html";
    return;
  }

  try {
    doc = await api("/documents/" + documentId);
  } catch (error) {
    alert(error.message);
    window.location.href = "/documents.html";
    return;
  }

  directory = await api("/employees/directory");
  for (const employee of directory) {
    if (employee.id !== currentUser.id) {
      approverSelect.append(new Option(employee.full_name, employee.id));
    }
  }
  render();
})();