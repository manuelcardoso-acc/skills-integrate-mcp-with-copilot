document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const emailGroup = document.getElementById("email-group");
  const emailInput = document.getElementById("email");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("login-form");
  const accountStatus = document.getElementById("account-status");
  const accountMessage = document.getElementById("account-message");
  const logoutButton = document.getElementById("logout-button");

  let accessToken = null;
  let currentUser = null;

  function apiFetch(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
    return fetch(url, { ...options, headers });
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return replacements[character];
    });
  }

  function showMessage(element, text, type) {
    element.textContent = text;
    element.className = type;
    element.classList.remove("hidden");
    setTimeout(() => element.classList.add("hidden"), 5000);
  }

  function updateAccountView() {
    loginForm.classList.toggle("hidden", Boolean(currentUser));
    accountStatus.classList.toggle("hidden", !currentUser);
    logoutButton.classList.toggle("hidden", !currentUser);
    signupContainer.classList.toggle("hidden", !currentUser);

    if (currentUser) {
      accountStatus.textContent = `Signed in as ${currentUser.username} (${currentUser.role})`;
      const canManageOthers =
        currentUser.role === "staff" || currentUser.role === "administrator";
      emailGroup.classList.toggle("hidden", !canManageOthers);
      emailInput.required = canManageOthers;
    } else {
      emailInput.required = false;
      emailInput.value = "";
    }
  }

  function canUnregister(activityName, email) {
    if (!currentUser) {
      return false;
    }
    if (currentUser.role === "administrator") {
      return true;
    }
    if (currentUser.role === "staff") {
      return currentUser.activities.includes(activityName);
    }
    return (
      currentUser.role === "student" &&
      currentUser.email.toLowerCase() === email.toLowerCase()
    );
  }

  async function fetchActivities() {
    try {
      const response = await apiFetch("/activities");
      const activities = await response.json();
      activitiesList.replaceChildren();

      while (activitySelect.options.length > 1) {
        activitySelect.remove(1);
      }

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const spotsLeft =
          details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
                <h5>Participants:</h5>
                <ul class="participants-list">
                  ${details.participants
                    .map((email) => {
                      const unregisterButton = canUnregister(name, email)
                        ? `<button class="delete-btn" data-activity="${escapeHtml(
                            name
                          )}" data-email="${escapeHtml(
                            email
                          )}" aria-label="Unregister ${escapeHtml(
                            email
                          )}">Unregister</button>`
                        : "";
                      return `<li><span class="participant-email">${escapeHtml(
                        email
                      )}</span>${unregisterButton}</li>`;
                    })
                    .join("")}
                </ul>
              </div>`
            : "<p><em>No participants yet</em></p>";

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">${participantsHTML}</div>
        `;
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.textContent =
        "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await apiFetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        await fetchActivities();
      } else {
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage(
        messageDiv,
        "Failed to unregister. Please try again.",
        "error"
      );
      console.error("Error unregistering:", error);
    }
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (!response.ok) {
        showMessage(
          accountMessage,
          result.detail || "Unable to log in",
          "error"
        );
        return;
      }

      accessToken = result.access_token;
      currentUser = result.user;
      loginForm.reset();
      updateAccountView();
      await fetchActivities();
      showMessage(accountMessage, "Logged in successfully", "success");
    } catch (error) {
      showMessage(accountMessage, "Failed to log in. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await apiFetch("/auth/logout", { method: "POST" });
      const result = await response.json();
      if (!response.ok) {
        showMessage(
          accountMessage,
          result.detail || "Unable to log out",
          "error"
        );
        return;
      }

      accessToken = null;
      currentUser = null;
      updateAccountView();
      await fetchActivities();
      showMessage(accountMessage, "Logged out successfully", "success");
    } catch (error) {
      showMessage(accountMessage, "Failed to log out. Please try again.", "error");
      console.error("Error logging out:", error);
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = emailInput.value;
    const activity = activitySelect.value;
    const query = email ? `?email=${encodeURIComponent(email)}` : "";

    try {
      const response = await apiFetch(
        `/activities/${encodeURIComponent(activity)}/signup${query}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage(
        messageDiv,
        "Failed to sign up. Please try again.",
        "error"
      );
      console.error("Error signing up:", error);
    }
  });

  updateAccountView();
  fetchActivities();
});
