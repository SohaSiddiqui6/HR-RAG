const form = document.querySelector("#chat-form");
const input = document.querySelector("#question");
const messages = document.querySelector("#messages");

function addMessage(text, role) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;

  addMessage(question, "user");
  input.value = "";

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    addMessage(data.answer || data.error || "No response.", "bot");
  } catch (err) {
    addMessage("Request failed. Try again.", "bot");
  }
});
