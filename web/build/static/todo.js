/**
 * Renders the todo widget UI inside ChatGPT (or the preview page).
 * The widget expects to receive the latest task list via a JSON blob embedded
 * in the MCP response. Interactions post messages back to the parent frame so
 * ChatGPT can invoke the appropriate tools.
 */
(() => {

  const dateFormatter = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  });

  const WIDGET_ACTION_TYPE = "widget-action";

  function sendToolCall(target, name, args) {
    if (!target || typeof target.postMessage !== "function") {
      console.warn("[todo-widget] No postMessage target available", name, args);
      return;
    }

    target.postMessage(
      {
        type: WIDGET_ACTION_TYPE,
        action: {
          type: "callTool",
          name,
          arguments: args,
        },
      },
      "*",
    );
  }

  function createSummaryItem(value, label) {
    const item = document.createElement("div");
    item.className = "todo-summary__item";

    const valueEl = document.createElement("div");
    valueEl.className = "todo-summary__value";
    valueEl.textContent = value;

    const labelEl = document.createElement("div");
    labelEl.className = "todo-summary__label";
    labelEl.textContent = label;

    item.append(valueEl, labelEl);
    return item;
  }

  function renderSummary(container, tasks) {
    container.innerHTML = "";

    if (!tasks.length) {
      return;
    }

    const total = tasks.length;
    const completed = tasks.filter((task) => !!task.done).length;
    const remaining = total - completed;

    container.append(
      createSummaryItem(total, "Total"),
      createSummaryItem(completed, "Completed"),
      createSummaryItem(remaining, "Remaining"),
    );
  }

  function renderEmptyState(root) {
    const empty = document.createElement("div");
    empty.className = "todo-empty";

    const title = document.createElement("span");
    title.className = "todo-empty__title";
    title.textContent = "All clear!";

    empty.append(
      title,
      document.createTextNode("Add a task to get started."),
    );

    root.append(empty);
    return empty;
  }

  function buildTaskItem(task, opts) {
    const { onToggle } = opts;
    const item = document.createElement("li");
    item.className = "todo-item";

    if (task.done) {
      item.classList.add("todo-item--completed");
    }

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "todo-item__checkbox";
    checkbox.checked = !!task.done;
    checkbox.setAttribute("aria-label", `Mark "${task.text}" done`);

    checkbox.addEventListener("change", () => {
      const checked = checkbox.checked;
      if (checked) {
        item.classList.add("todo-item--completed");
      } else {
        item.classList.remove("todo-item--completed");
      }
      onToggle?.(task, checked);
    });

    const main = document.createElement("div");
    main.className = "todo-item__main";

    const text = document.createElement("div");
    text.className = "todo-item__text";
    text.textContent = task.text;

    const meta = document.createElement("div");
    meta.className = "todo-item__meta";
    const metaParts = [];
    if (task.due_date) {
      metaParts.push(`Due ${task.due_date}`);
    }
    if (task.created_at) {
      try {
        const date = new Date(task.created_at);
        metaParts.push(`Added ${dateFormatter.format(date)}`);
      } catch (_err) {
        metaParts.push(`Added ${task.created_at}`);
      }
    }
    meta.textContent = metaParts.join(" • ");
    if (!metaParts.length) {
      meta.style.display = "none";
    }

    main.append(text, meta);
    item.append(checkbox, main);
    return item;
  }

  function buildAddTaskForm(opts) {
    const { onSubmit } = opts;
    const form = document.createElement("form");
    form.className = "todo-form";

    const textInput = document.createElement("input");
    textInput.type = "text";
    textInput.placeholder = "Add a task…";
    textInput.required = true;
    textInput.className = "todo-form__input";
    textInput.setAttribute("aria-label", "Task description");

    const dueInput = document.createElement("input");
    dueInput.type = "date";
    dueInput.className = "todo-form__date";
    dueInput.setAttribute("aria-label", "Due date");

    const button = document.createElement("button");
    button.type = "submit";
    button.className = "todo-form__button";
    button.textContent = "Add";

    form.append(textInput, dueInput, button);

    form.addEventListener("submit", (event) => {
      event.preventDefault();

      const text = textInput.value.trim();
      const due_date = dueInput.value ? dueInput.value : undefined;

      if (!text) {
        return;
      }

      onSubmit?.({ text, due_date });

      textInput.value = "";
      dueInput.value = "";
      textInput.focus();
    });

    return form;
  }

  function renderTodoWidget(options = {}) {
    const {
      root,
      tasks = [],
      postMessageTarget = null,
    } = options;

    if (!root) {
      console.error("[todo-widget] Missing root element");
      return;
    }

    const state = tasks.map((task) => ({ ...task }));

    root.innerHTML = "";

    const card = document.createElement("div");
    card.className = "todo-card";

    const header = document.createElement("div");
    header.className = "todo-card__header";

    const title = document.createElement("h1");
    title.className = "todo-card__title";
    title.textContent = "Han's To-Do List";

    const subtitle = document.createElement("p");
    subtitle.className = "todo-card__subtitle";
    subtitle.textContent = "Track your tasks and check them off.";

    header.append(title, subtitle);

    const content = document.createElement("div");
    content.className = "todo-content";

    const form = buildAddTaskForm({
      onSubmit: ({ text, due_date }) => {
        sendToolCall(postMessageTarget, "add_task", {
          text,
          due_date,
        });
      },
    });

    const summary = document.createElement("div");
    summary.className = "todo-summary";

    const list = document.createElement("ul");
    list.className = "todo-list";

    const emptyState = document.createElement("div");
    emptyState.className = "todo-empty";
    emptyState.append(
      (() => {
        const span = document.createElement("span");
        span.className = "todo-empty__title";
        span.textContent = "All clear!";
        return span;
      })(),
      document.createTextNode("Add a task to get started."),
    );

    function updateList() {
      list.innerHTML = "";
      const activeTasks = state.filter(Boolean);

      if (!activeTasks.length) {
        emptyState.style.display = "block";
        list.style.display = "none";
        summary.style.display = "none";
        return;
      }

      emptyState.style.display = "none";
      list.style.display = "flex";
      summary.style.display = "flex";

      activeTasks.forEach((task) => {
        const item = buildTaskItem(task, {
          onToggle: (t, done) => {
            t.done = done;
            renderSummary(summary, state);
            sendToolCall(postMessageTarget, "mark_done", {
              task_id: t.id,
              done,
            });
          },
        });
        list.append(item);
      });
    }

    updateList();
    renderSummary(summary, state);

    content.append(form, summary, list, emptyState);
    card.append(header, content);
    root.append(card);
  }

  const dataEl = document.getElementById("todo-data");
  const root = document.getElementById("todo-root");
  const data = JSON.parse(dataEl.textContent);

  renderTodoWidget({
    root,
    tasks: data.tasks,
    postMessageTarget: window.parent,
  });
})();
