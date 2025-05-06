let API_HOST;
let versions = [];
let selectedGroups = [];
let loadingModal;

function toggleTheme() {
    const theme =
        document.documentElement.getAttribute("data-theme") === "dark"
            ? "light"
            : "dark";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
    updateThemeIcon();
}

function updateThemeIcon() {
    const icon = document.querySelector(".theme-toggle .icon i");
    if (document.documentElement.getAttribute("data-theme") === "dark") {
        icon.classList.remove("fa-moon");
        icon.classList.add("fa-sun");
    } else {
        icon.classList.remove("fa-sun");
        icon.classList.add("fa-moon");
    }
}

function initializeApp(baseUrl) {
    API_HOST = baseUrl + "/api";
    loadingModal = document.getElementById("loading");

    const API_ENDPOINTS = {
        SCHEDULE_INFO: `${API_HOST}/schedule/info`,
        CURRENT_WEEK: `${API_HOST}/schedule/current-week`,
        FILES_LIST: `${API_HOST}/files`,
        COMPARE_FILES: `${API_HOST}/compare-files`,
        ADD_FILE: `${API_HOST}/files/add-file`,
        SEARCH_GROUPS: `${API_HOST}/search-groups`,
        DOWNLOAD_SCHEDULES: `${API_HOST}/schedule/download-schedules`,
    };

    window.API_ENDPOINTS = API_ENDPOINTS;
    window.API_HOST = API_HOST;

    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcon();

    const selectedGroupsList = document.getElementById("selectedGroupsList");
    const groupSearchInput = document.getElementById("groupSearchInput");
    const groupSearchDropdown = document.getElementById("groupSearchDropdown");
    const groupSearchResults = document.getElementById("groupSearchResults");
    const addSelectedGroupButton = document.getElementById("addSelectedGroupButton");
    const downloadGroupsButton = document.getElementById("downloadGroupsButton");
    const compareVersionsButton = document.getElementById("compareVersionsButton");

    document.addEventListener("click", (e) => {
        if (
            !groupSearchDropdown.contains(e.target) &&
            e.target !== groupSearchInput
        ) {
            groupSearchDropdown.classList.remove("is-active");
        }
    });

    groupSearchInput.addEventListener("input", (e) => {
        debouncedSearchGroups(e.target.value);
    });

    addSelectedGroupButton.addEventListener("click", () => {
        if (
            selectedGroupToAdd &&
            !selectedGroups.find(
                (g) => g.fullTitle === selectedGroupToAdd.fullTitle
            )
        ) {
            selectedGroups.push(selectedGroupToAdd);
            renderSelectedGroups();
            groupSearchInput.value = "";
            groupSearchDropdown.classList.remove("is-active");
            clearSearchResults();
        }
    });

    downloadGroupsButton.addEventListener("click", async () => {
        if (selectedGroups.length === 0) {
            alert("Сначала выберите группы");
            return;
        }
        showLoading();
        try {
            const groupsArray = selectedGroups.map((group) => group.fullTitle);
            const response = await fetch(window.API_ENDPOINTS.DOWNLOAD_SCHEDULES, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ groups: groupsArray }),
            });
            if (!response.ok) throw new Error("Ошибка при загрузке групп");
            await response.json();
            await fetchVersions();
        } catch (error) {
            alert(error.message);
        } finally {
            hideLoading();
        }
    });

    compareVersionsButton.addEventListener("click", async () => {
        const leftVersionSelect = document.getElementById("leftVersionSelect");
        const rightVersionSelect = document.getElementById("rightVersionSelect");

        const leftVersionId = leftVersionSelect.value;
        const rightVersionId = rightVersionSelect.value;
        if (!leftVersionId || !rightVersionId) {
            alert("Выберите обе версии для сравнения");
            return;
        }
        if (leftVersionId === rightVersionId) {
            alert("Выберите разные версии для сравнения");
            return;
        }
        showLoading();
        try {
            const response = await fetch(
                `${window.API_ENDPOINTS.COMPARE_FILES}?file_id_1=${leftVersionId}&file_id_2=${rightVersionId}`,
                {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );
            if (!response.ok) throw new Error("Ошибка при сравнении версий");
            const result = await response.json();
            renderComparisonResults(result);
        } catch (error) {
            alert(error.message);
        } finally {
            hideLoading();
        }
    });

    fetchVersions();
}

function showLoading() {
    loadingModal.classList.add("is-active");
}

function hideLoading() {
    loadingModal.classList.remove("is-active");
}

let selectedGroupToAdd = null;

function updateAddButtonState() {
    document.getElementById("addSelectedGroupButton").disabled = !selectedGroupToAdd;
}

function clearSearchResults() {
    selectedGroupToAdd = null;
    updateAddButtonState();
    const activeItems = document.querySelectorAll(".dropdown-item.is-active");
    activeItems.forEach((item) => item.classList.remove("is-active"));
}

async function fetchVersions() {
    try {
        const response = await fetch(window.API_ENDPOINTS.FILES_LIST);
        if (!response.ok)
            throw new Error("Ошибка при получении списка версий");
        const data = await response.json();
        versions = data.files;
        renderVersions();
        renderVersionOptions();

        if (versions.length > 0) {
            const sortedVersions = versions
                .slice()
                .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            const latestVersion = sortedVersions[0];
            await loadGroupsFromVersion(latestVersion.id);
        }
    } catch (error) {
        console.error(error);
        alert(error.message);
    }
}

async function loadGroupsFromVersion(versionId) {
    try {
        const response = await fetch(`${window.API_HOST}/files/${versionId}/groups`);
        if (!response.ok)
            throw new Error("Ошибка при получении списка групп из версии");
        const data = await response.json();

        if (data && data.groups && Array.isArray(data.groups)) {
            selectedGroups = data.groups.map((groupName) => ({
                id: null,
                fullTitle: groupName,
            }));
            renderSelectedGroups();
        }
    } catch (error) {
        console.error("Ошибка при загрузке групп из версии:", error);
    }
}

function renderSelectedGroups() {
    const selectedGroupsList = document.getElementById("selectedGroupsList");
    selectedGroupsList.innerHTML = "";

    if (selectedGroups.length === 0) {
        selectedGroupsList.innerHTML = '<p class="has-text-grey">Список групп пуст</p>';
        return;
    }

    selectedGroups.forEach((group, index) => {
        const tag = document.createElement("span");
        tag.className = "tag is-info is-medium";
        tag.textContent = group.fullTitle;
        tag.style.marginRight = "1rem";
        tag.style.marginTop = "1rem";

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "delete is-small";
        deleteBtn.style.marginLeft = "0.5rem";
        deleteBtn.addEventListener("click", () => {
            selectedGroups.splice(index, 1);
            renderSelectedGroups();
        });

        tag.appendChild(deleteBtn);
        selectedGroupsList.appendChild(tag);
    });
}

function debounce(func, delay) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}

const debouncedSearchGroups = debounce(searchGroups, 300);

async function searchGroups(query) {
    if (!query.trim()) {
        document.getElementById("groupSearchDropdown").classList.remove("is-active");
        clearSearchResults();
        return;
    }

    try {
        const response = await fetch(
            `${window.API_ENDPOINTS.SEARCH_GROUPS}?match=${encodeURIComponent(query)}`
        );

        if (!response.ok) throw new Error("Ошибка поиска групп");

        const data = await response.json();
        const groupSearchResults = document.getElementById("groupSearchResults");
        const groupSearchDropdown = document.getElementById("groupSearchDropdown");

        if (data.data && data.data.length > 0) {
            groupSearchResults.innerHTML = data.data
                .map((group) => {
                    const minGroup = {
                        id: group.id,
                        fullTitle: group.fullTitle,
                    };
                    return `<a class="dropdown-item" data-group='${JSON.stringify(
                        minGroup
                    )}'>${group.fullTitle}</a>`;
                })
                .join("");
            groupSearchDropdown.classList.add("is-active");

            document
                .querySelectorAll("#groupSearchResults .dropdown-item")
                .forEach((item) => {
                    item.addEventListener("click", (e) => {
                        e.preventDefault();
                        const group = JSON.parse(item.getAttribute("data-group"));
                        document.getElementById("groupSearchInput").value = group.fullTitle;
                        selectedGroupToAdd = group;
                        updateAddButtonState();
                        groupSearchDropdown.classList.remove("is-active");
                    });
                });
        } else {
            groupSearchResults.innerHTML =
                '<div class="dropdown-item">Группы не найдены</div>';
            groupSearchDropdown.classList.add("is-active");
            clearSearchResults();
        }
    } catch (error) {
        console.error("Ошибка при поиске групп:", error);
        clearSearchResults();
    }
}

window.toggleTheme = toggleTheme;
window.initializeApp = initializeApp;
window.fetchVersions = fetchVersions;
window.renderSelectedGroups = renderSelectedGroups;
window.searchGroups = searchGroups;
window.loadGroupsFromVersion = loadGroupsFromVersion; 