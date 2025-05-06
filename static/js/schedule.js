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

const savedTheme = localStorage.getItem("theme") || "light";
document.documentElement.setAttribute("data-theme", savedTheme);
window.addEventListener("DOMContentLoaded", updateThemeIcon);

let API_HOST;
const filters = [];
let scheduleData = {};
let currentSemcode = null;
let semesterDates = {};
let scheduleInfo = {};
let currentSortColumn = "date";
let sortDirection = "asc";
let minPair = 1;
let maxPair = 7;
let freeSlotsData = null;
let loadingModal;

const PAIR_TIMES = {
    1: "09:00 - 10:30",
    2: "10:40 - 12:10",
    3: "12:40 - 14:10",
    4: "14:20 - 15:50",
    5: "16:20 - 17:50",
    6: "18:00 - 19:30",
    7: "19:40 - 21:10",
};

const PAIR_START_TIMES = {
    1: "09:00",
    2: "10:40",
    3: "12:40",
    4: "14:20",
    5: "16:20",
    6: "18:00",
    7: "19:40",
};

const LESSON_TYPE_CLASSES = {
    ЛК: "lesson-type-lk",
    ПР: "lesson-type-pr",
    ЛАБ: "lesson-type-lab",
    ЭКЗ: "lesson-type-exam",
    ЗАЧ: "lesson-type-exam",
    КР: "lesson-type-exam",
};

function initializeApp(baseUrl) {
    API_HOST = baseUrl + "/api";
    loadingModal = document.getElementById("loading");

    const API_ENDPOINTS = {
        SCHEDULE_INFO: `${API_HOST}/schedule/info`,
        CURRENT_WEEK: `${API_HOST}/schedule/current-week`,
        SEMESTER_DATES: `${API_HOST}/schedule/semester-dates`,
        GET_SCHEDULE: `${API_HOST}/schedule/get`,
        FREE_SLOTS: `${API_HOST}/schedule/free-slots`,
        SEARCH_ITEMS: `${API_HOST}/schedule/search`,
        ADD_LESSON: `${API_HOST}/schedule/add-lesson`,
        DELETE_LESSON: `${API_HOST}/schedule/delete-lesson`,
        MOVE_LESSON: `${API_HOST}/schedule/move-lesson`,
        DOWNLOAD_SCHEDULES: `${API_HOST}/schedule/download-schedules`,
    };

    window.API_ENDPOINTS = API_ENDPOINTS;

    const minPairSlider = document.getElementById("minPairSlider");
    const maxPairSlider = document.getElementById("maxPairSlider");
    const minPairValue = document.getElementById("minPairValue");
    const maxPairValue = document.getElementById("maxPairValue");
    const applyRangeFilter = document.getElementById("applyRangeFilter");

    minPairSlider.addEventListener("input", function () {
        minPair = parseInt(this.value);
        if (minPair > maxPair) {
            maxPairSlider.value = minPair;
            maxPair = minPair;
            updateMaxPairValue();
        }
        updateMinPairValue();
    });

    maxPairSlider.addEventListener("input", function () {
        maxPair = parseInt(this.value);
        if (maxPair < minPair) {
            minPairSlider.value = maxPair;
            minPair = maxPair;
            updateMinPairValue();
        }
        updateMaxPairValue();
    });

    applyRangeFilter.addEventListener("click", function () {
        if (freeSlotsData) {
            renderFreeSlotsTable(freeSlotsData);
        }
    });

    window.addEventListener("DOMContentLoaded", async () => {
        await loadScheduleInfo();
        await loadCurrentWeekInfo();
        loadAvailableSchedules();

        document.getElementById("pairsRangeFilter").classList.add("is-hidden");
    });

    document.getElementById("semcodeSelect").addEventListener("change", async (e) => {
        currentSemcode = parseInt(e.target.value);
        await loadSemesterDates(currentSemcode);
        await loadCurrentWeekInfo();
        setFullSemester();
    });

    document.addEventListener("click", (e) => {
        if (!e.target.matches(".input")) {
            const dropdowns = document.querySelectorAll(".dropdown-content");
            dropdowns.forEach((dropdown) => {
                dropdown.classList.add("is-hidden");
            });
        }
    });

    document.getElementById("dateFrom").addEventListener("change", function () {
        freeSlotsData = null;
        document.getElementById("pairsRangeFilter").classList.add("is-hidden");
    });

    document.getElementById("dateTo").addEventListener("change", function () {
        freeSlotsData = null;
        document.getElementById("pairsRangeFilter").classList.add("is-hidden");
    });

    document.addEventListener("DOMContentLoaded", function () {
        const modalCloseButtons = document.querySelectorAll(
            "#addLessonModal .delete, #addLessonModal .modal-background"
        );
        modalCloseButtons.forEach((button) => {
            button.addEventListener("click", closeAddLessonModal);
        });

        document.getElementById("repeatForWeeks").addEventListener("change", function () {
            const weeksSelector = document.getElementById("weeksSelector");
            if (this.checked) {
                weeksSelector.classList.remove("is-hidden");
            } else {
                weeksSelector.classList.add("is-hidden");
            }
        });
    });

    document.addEventListener("click", function (e) {
        if (e.target.matches(".selected-item button")) {
            setTimeout(updateYearPresetsVisibility, 50);
        }
    });

    generateYearPresets();
}

function updateMinPairValue() {
    minPairValue.textContent = `${minPair} пара (${PAIR_START_TIMES[minPair]})`;
}

function updateMaxPairValue() {
    maxPairValue.textContent = `${maxPair} пара (${PAIR_START_TIMES[maxPair]})`;
}

async function loadScheduleInfo() {
    showLoading();

    try {
        const response = await fetch(window.API_ENDPOINTS.SCHEDULE_INFO);
        scheduleInfo = await response.json();

        const semcodeSelect = document.getElementById("semcodeSelect");
        semcodeSelect.innerHTML = "";

        if (scheduleInfo.semcodes && scheduleInfo.semcodes.length > 0) {
            for (const semcode of scheduleInfo.semcodes) {
                const option = document.createElement("option");
                option.value = semcode;

                const year = Math.floor(semcode / 10);
                const semester = semcode % 10;

                let semesterText = semester === 1 ? "Осенний" : "Весенний";

                let startDate = "";
                if (
                    scheduleInfo.semester_dates &&
                    scheduleInfo.semester_dates[semcode] &&
                    scheduleInfo.semester_dates[semcode].start_date
                ) {
                    const dateObj = new Date(
                        scheduleInfo.semester_dates[semcode].start_date
                    );
                    const day = dateObj.getDate();
                    const month = dateObj.getMonth() + 1;
                    startDate = ` (с ${day}.${month < 10 ? "0" + month : month})`;
                }

                option.textContent = `${semesterText} ${year}${startDate} (${semcode})`;

                if (semcode === scheduleInfo.current_semcode) {
                    option.selected = true;
                }

                semcodeSelect.appendChild(option);
            }
        } else {
            const option = document.createElement("option");
            option.value = scheduleInfo.current_semcode;

            const year = Math.floor(scheduleInfo.current_semcode / 10);
            const semester = scheduleInfo.current_semcode % 10;

            let semesterText = semester === 1 ? "Осенний" : "Весенний";
            option.textContent = `${semesterText} ${year} (${scheduleInfo.current_semcode})`;

            semcodeSelect.appendChild(option);
        }

        currentSemcode = scheduleInfo.current_semcode;

        await loadSemesterDates(currentSemcode);

        setCurrentWeek();
    } catch (error) {
        console.error("Error loading schedule info:", error);
    } finally {
        hideLoading();
    }
}

async function loadSemesterDates(semcode) {
    try {
        const response = await fetch(
            `${window.API_ENDPOINTS.SEMESTER_DATES}?semcode=${semcode}`
        );
        semesterDates = await response.json();
    } catch (error) {
        console.error("Error loading semester dates:", error);
    }
}

function setCurrentWeek() {
    const today = new Date();
    const dayOfWeek = today.getDay();

    const monday = new Date(today);
    monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    document.getElementById("dateFrom").value = formatDateForInput(monday);
    document.getElementById("dateTo").value = formatDateForInput(sunday);
}

function setNextWeek() {
    const today = new Date();
    const dayOfWeek = today.getDay();

    const nextMonday = new Date(today);
    nextMonday.setDate(today.getDate() + (7 - dayOfWeek + 1));

    const nextSunday = new Date(nextMonday);
    nextSunday.setDate(nextMonday.getDate() + 6);

    document.getElementById("dateFrom").value = formatDateForInput(nextMonday);
    document.getElementById("dateTo").value = formatDateForInput(nextSunday);
}

function setFullSemester() {
    if (semesterDates && semesterDates.start_date && semesterDates.end_date) {
        document.getElementById("dateFrom").value = semesterDates.start_date.substring(0, 10);
        document.getElementById("dateTo").value = semesterDates.end_date.substring(0, 10);
    }
}

function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function addFilter(type) {
    const filterId = Date.now();
    const filterDiv = document.createElement("div");
    filterDiv.classList.add("field", "filter");
    filterDiv.dataset.filterId = filterId;

    filterDiv.innerHTML = `
    <label class="label">${type === "group"
            ? "Группа"
            : type === "prep"
                ? "Преподаватель"
                : "Аудитория"
        }</label>
    <div class="control">
      <input class="input" type="text" oninput="showSuggestions(event, '${type}', ${filterId})" placeholder="Начните вводить...">
      <div class="dropdown-content is-hidden" id="dropdown-${filterId}"></div>
      <div class="selected-items" id="selected-${filterId}"></div>
    </div>
  `;
    document.getElementById("filtersContainer").appendChild(filterDiv);

    filters.push({ id: filterId, type: type, values: [] });

    setTimeout(updateYearPresetsVisibility, 10);
}

function updateYearPresetsVisibility() {
    const presetsContainer = document.getElementById("yearPresetsContainer");
    if (!presetsContainer) {
        console.warn("Элемент контейнера пресетов не найден");
        return;
    }

    const hasGroupFilter = filters.some((filter) => filter.type === "group");

    if (hasGroupFilter) {
        presetsContainer.classList.remove("is-hidden");
    } else {
        presetsContainer.classList.add("is-hidden");
    }
}

async function showSuggestions(event, type, filterId) {
    const query = event.target.value.trim();
    if (query.length < 2) {
        document.getElementById(`dropdown-${filterId}`).classList.add("is-hidden");
        return;
    }
    const response = await fetch(
        `${window.API_ENDPOINTS.SEARCH_ITEMS}?search_type=${type}&q=${encodeURIComponent(query)}`
    );
    const suggestions = await response.json();

    const dropdown = document.getElementById(`dropdown-${filterId}`);
    dropdown.innerHTML = "";
    suggestions.forEach((item) => {
        const itemDiv = document.createElement("div");
        itemDiv.classList.add("dropdown-item");
        itemDiv.textContent = item;
        itemDiv.onclick = () => selectItem(filterId, item);
        dropdown.appendChild(itemDiv);
    });

    if (suggestions.length > 0) {
        dropdown.classList.remove("is-hidden");
    } else {
        dropdown.classList.add("is-hidden");
    }
}

function selectItem(filterId, item) {
    const filter = filters.find((f) => f.id === filterId);
    if (!filter.values.includes(item)) {
        filter.values.push(item);

        const selectedItemsDiv = document.getElementById(`selected-${filterId}`);
        const itemDiv = document.createElement("div");
        itemDiv.classList.add("selected-item");
        itemDiv.textContent = item;

        const removeButton = document.createElement("button");
        removeButton.innerHTML = "&times;";
        removeButton.onclick = () => {
            filter.values = filter.values.filter((v) => v !== item);
            itemDiv.remove();
        };
        itemDiv.appendChild(removeButton);
        selectedItemsDiv.appendChild(itemDiv);
    }

    document.getElementById(`dropdown-${filterId}`).classList.add("is-hidden");
    const inputField = document.querySelector(`[data-filter-id="${filterId}"] .input`);
    inputField.value = "";
}

// Остальной JavaScript код schedule.html
// ...

// Экспортируем функции, которые могут понадобиться в HTML
window.toggleTheme = toggleTheme;
window.setCurrentWeek = setCurrentWeek;
window.setNextWeek = setNextWeek;
window.setFullSemester = setFullSemester;
window.addFilter = addFilter;
window.showSuggestions = showSuggestions;
window.selectItem = selectItem;
window.loadSchedules = loadSchedules;
window.loadFreeSlots = loadFreeSlots;
window.handleCellClick = handleCellClick;
window.openAddLessonModal = openAddLessonModal;
window.closeAddLessonModal = closeAddLessonModal;
window.addManualTeacher = addManualTeacher;
window.addManualRoom = addManualRoom;
window.addManualGroup = addManualGroup;
window.saveLesson = saveLesson;
window.closeMoveLessonModal = closeMoveLessonModal;
window.saveMove = saveMove;
window.moveLessonModal = moveLessonModal;
window.deleteLesson = deleteLesson;
window.selectAllWeeks = selectAllWeeks;
window.selectOddWeeks = selectOddWeeks;
window.selectEvenWeeks = selectEvenWeeks;
window.deselectAllWeeks = deselectAllWeeks;
window.initializeApp = initializeApp;
window.updateYearPresetsVisibility = updateYearPresetsVisibility;

async function loadSchedules() {
    const dateFrom = document.getElementById("dateFrom").value;
    const dateTo = document.getElementById("dateTo").value;

    if (!dateFrom || !dateTo) {
        alert("Пожалуйста, выберите диапазон дат.");
        return;
    }

    if (filters.length === 0 || !filters.some((f) => f.values.length > 0)) {
        alert("Пожалуйста, добавьте хотя бы один фильтр.");
        return;
    }

    document.getElementById("pairsRangeFilter").classList.add("is-hidden");

    showLoading();

    try {
        for (const key in scheduleData) {
            delete scheduleData[key];
        }

        for (const filter of filters) {
            for (const value of filter.values) {
                const response = await fetch(
                    `${window.API_ENDPOINTS.GET_SCHEDULE}?semcode=${currentSemcode}&date_from=${dateFrom}&date_to=${dateTo}&filter_type=${filter.type
                    }&filter_value=${encodeURIComponent(value)}`
                );
                const data = await response.json();
                if (data && data[value]) {
                    scheduleData[value] = data[value];
                }
            }
        }

        renderSchedules();
    } catch (error) {
        console.error("Error loading schedules:", error);
        alert("Произошла ошибка при загрузке расписания");
    } finally {
        hideLoading();
    }
}

async function loadFreeSlots() {
    const dateFrom = document.getElementById("dateFrom").value;
    const dateTo = document.getElementById("dateTo").value;

    if (!dateFrom || !dateTo) {
        alert("Пожалуйста, выберите диапазон дат.");
        return;
    }

    if (filters.length === 0 || !filters.some((f) => f.values.length > 0)) {
        alert("Пожалуйста, добавьте хотя бы один фильтр.");
        return;
    }

    showLoading();

    try {
        const filter_types = [];
        const filter_values = [];

        for (const filter of filters) {
            for (const value of filter.values) {
                filter_types.push(filter.type);
                filter_values.push(value);
            }
        }

        let url = `${window.API_ENDPOINTS.FREE_SLOTS}?semcode=${currentSemcode}&date_from=${dateFrom}&date_to=${dateTo}`;

        filter_types.forEach((type) => {
            url += `&filter_types=${type}`;
        });

        filter_values.forEach((value) => {
            url += `&filter_values=${encodeURIComponent(value)}`;
        });

        const response = await fetch(url);
        const data = await response.json();

        freeSlotsData = data;

        document.getElementById("pairsRangeFilter").classList.remove("is-hidden");

        renderFreeSlotsTable(data);
    } catch (error) {
        console.error("Error loading free slots:", error);
        alert("Произошла ошибка при загрузке свободных временных интервалов");
    } finally {
        hideLoading();
    }
}

function showLoading() {
    loadingModal.classList.add("is-active");
}

function hideLoading() {
    loadingModal.classList.remove("is-active");
}

