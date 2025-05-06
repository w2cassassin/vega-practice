function formatDate(dateStr) {
    const date = new Date(dateStr);
    const days = [
        "Воскресенье",
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
    ];
    const months = [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ];

    return `${days[date.getDay()]}, ${date.getDate()} ${months[date.getMonth()]
        } ${date.getFullYear()}`;
}

function formatShortDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "numeric",
        weekday: "short",
    });
}

function renderSchedules() {
    const container = document.getElementById("scheduleContainer");
    container.innerHTML = "";

    const scheduleContainer = document.createElement("div");
    scheduleContainer.className = "schedule-container";

    const dateFrom = document.getElementById("dateFrom").value;
    const dateTo = document.getElementById("dateTo").value;

    if (!dateFrom || !dateTo) {
        container.innerHTML =
            '<div class="notification is-warning">Пожалуйста, выберите диапазон дат</div>';
        return;
    }

    const allDates = [];
    const startDate = new Date(dateFrom);
    const endDate = new Date(dateTo);

    let currentDate = new Date(startDate);
    while (currentDate <= endDate) {
        if (currentDate.getDay() !== 0) {
            const dateString = currentDate.toISOString().split("T")[0];
            allDates.push(dateString);
        }
        currentDate.setDate(currentDate.getDate() + 1);
    }

    if (allDates.length === 0) {
        container.innerHTML =
            '<div class="notification is-warning">Нет данных для выбранного периода</div>';
        return;
    }

    const entities = Object.keys(scheduleData);
    if (entities.length === 0) {
        container.innerHTML =
            '<div class="notification is-warning">Нет данных для выбранных фильтров</div>';
        return;
    }

    const table = document.createElement("table");
    table.className = "schedule-table";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    headerRow.innerHTML = `
    <th class="pair-header">Пара</th>
    ${entities.map((e) => `<th class="pair-cell">${e}</th>`).join("")}
  `;
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");

    for (const date of allDates) {
        const dateRow = document.createElement("tr");
        dateRow.className = "day-separator";
        dateRow.innerHTML = `<td colspan="${entities.length + 1
            }">${formatDate(date)}</td>`;
        tbody.appendChild(dateRow);

        for (const pair of ["1", "2", "3", "4", "5", "6", "7"]) {
            const row = document.createElement("tr");

            row.innerHTML = `
        <td>
          <strong>${pair}</strong>
          <div class="pair-time">${PAIR_TIMES[pair]}</div>
        </td>
      `;

            let busyCellsCount = 0;
            let totalCellsCount = 0;

            for (const entity of entities) {
                totalCellsCount++;
                const pairData = scheduleData[entity]?.[date]?.[pair];
                const cell = document.createElement("td");
                cell.dataset.date = date;
                cell.dataset.pair = pair;
                cell.dataset.entity = entity;
                cell.dataset.entityType = getEntityType(entity);
                cell.addEventListener("click", handleCellClick);

                if (pairData) {
                    busyCellsCount++;
                    let lessonTypeClass = "lesson-type-pr";

                    if (
                        pairData.lesson_type &&
                        LESSON_TYPE_CLASSES[pairData.lesson_type]
                    ) {
                        lessonTypeClass = LESSON_TYPE_CLASSES[pairData.lesson_type];
                    }

                    if (pairData.lessonId || pairData.id) {
                        cell.dataset.lessonId = pairData.lessonId || pairData.id;
                        cell.classList.add("busy-cell");
                    } else {
                        console.warn("У пары отсутствует ID:", pairData);
                        cell.classList.add("busy-cell");
                    }

                    cell.innerHTML = `
            <span class="lesson-type ${lessonTypeClass}">${pairData.lesson_type || "ПР"
                        }</span>
            <strong>${pairData.subject}</strong><br>
            ${pairData.teacher
                            ? `<span class="has-text-grey">${pairData.teacher}</span><br>`
                            : ""
                        }
            ${pairData.room
                            ? `<span class="has-text-info">${pairData.room}</span><br>`
                            : ""
                        }
            ${pairData.groups &&
                            (getEntityType(entity) === "prep" ||
                                getEntityType(entity) === "room")
                            ? `<span class="has-text-success">${pairData.groups.join(
                                ", "
                            )}</span><br>`
                            : ""
                        }
          `;
                } else {
                    cell.textContent = "Свободно";
                    cell.classList.add("free-cell");
                }
                row.appendChild(cell);
            }

            if (busyCellsCount === 0 && totalCellsCount > 0) {
                row.classList.add("all-free-slot");
            }

            tbody.appendChild(row);
        }
    }

    table.appendChild(tbody);
    scheduleContainer.appendChild(table);
    container.appendChild(scheduleContainer);
}

function renderFreeSlotsTable(freeSlotsData) {
    const container = document.getElementById("scheduleContainer");
    container.innerHTML = "";

    const allDates = Object.keys(freeSlotsData).sort();
    if (allDates.length === 0) {
        container.innerHTML =
            '<div class="notification is-warning">Нет данных для выбранного периода</div>';
        return;
    }

    const entities = new Set();
    Object.values(freeSlotsData).forEach((dateData) => {
        Object.keys(dateData).forEach((entity) => entities.add(entity));
    });

    const commonFreeSlots = [];

    for (const date of allDates) {
        if (new Date(date).getDay() === 0) continue;

        const pairCounts = {};
        const entitiesCount = entities.size;

        for (const entity of entities) {
            if (freeSlotsData[date] && freeSlotsData[date][entity]) {
                const availablePairs = freeSlotsData[date][entity].filter(
                    (pair) => pair >= minPair && pair <= maxPair
                );

                for (const pair of availablePairs) {
                    pairCounts[pair] = (pairCounts[pair] || 0) + 1;
                }
            }
        }

        for (const [pair, count] of Object.entries(pairCounts)) {
            if (count === entitiesCount) {
                commonFreeSlots.push({
                    date: date,
                    formattedDate: formatDate(date),
                    shortDate: formatShortDate(date),
                    pair: parseInt(pair),
                    pairTime: PAIR_TIMES[pair],
                    entityCount: entitiesCount,
                    entities: Array.from(entities).join(", "),
                });
            }
        }
    }

    if (commonFreeSlots.length === 0) {
        container.innerHTML =
            '<div class="notification is-warning">Нет общих свободных временных интервалов в выбранном диапазоне пар</div>';
        return;
    }

    sortFreeSlots(commonFreeSlots);

    const tableContainer = document.createElement("div");
    tableContainer.className = "box";

    const tableTitle = document.createElement("h3");
    tableTitle.className = "subtitle";
    tableTitle.innerHTML = `Свободные временные интервалы <span class="tag is-info is-light">Найдено: ${commonFreeSlots.length}</span>`;
    tableContainer.appendChild(tableTitle);

    const filterInfo = document.createElement("p");
    filterInfo.innerHTML = `Показаны интервалы для пар с ${minPair} по ${maxPair} <strong>(свободные у всех выбранных элементов, кроме воскресений)</strong>`;
    filterInfo.className = "mb-3 filter-info";
    tableContainer.appendChild(filterInfo);

    const table = document.createElement("table");
    table.className = "free-slots-table table is-fullwidth is-striped";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");

    const headers = [
        { id: "date", text: "Дата" },
        { id: "pair", text: "Пара" },
        { id: "entities", text: "Свободно для" },
    ];

    headers.forEach((header) => {
        const th = document.createElement("th");
        th.textContent = header.text;
        th.dataset.column = header.id;
        th.addEventListener("click", () => {
            sortTableByColumn(header.id, commonFreeSlots, table);
        });

        if (header.id === currentSortColumn) {
            th.classList.add(
                sortDirection === "asc" ? "sorted-asc" : "sorted-desc"
            );
        }

        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");

    commonFreeSlots.forEach((slot) => {
        const row = document.createElement("tr");

        row.innerHTML = `
      <td>${slot.shortDate}</td>
      <td>${slot.pair} (${slot.pairTime})</td>
      <td>${slot.entities}</td>
    `;

        tbody.appendChild(row);
    });

    table.appendChild(tbody);
    tableContainer.appendChild(table);
    container.appendChild(tableContainer);
}

function sortTableByColumn(column, data, table) {
    if (currentSortColumn === column) {
        sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
        currentSortColumn = column;
        sortDirection = "asc";
    }

    sortFreeSlots(data);

    const headers = table.querySelectorAll("th");
    headers.forEach((th) => {
        th.classList.remove("sorted-asc", "sorted-desc");
        if (th.dataset.column === currentSortColumn) {
            th.classList.add(
                sortDirection === "asc" ? "sorted-asc" : "sorted-desc"
            );
        }
    });

    const tbody = table.querySelector("tbody");
    tbody.innerHTML = "";

    data.forEach((slot) => {
        const row = document.createElement("tr");

        row.innerHTML = `
      <td>${slot.shortDate}</td>
      <td>${slot.pair} (${slot.pairTime})</td>
      <td>${slot.entities}</td>
    `;

        tbody.appendChild(row);
    });
}

function sortFreeSlots(slots) {
    slots.sort((a, b) => {
        let result = 0;

        if (currentSortColumn === "date") {
            result = new Date(a.date) - new Date(b.date);
        } else if (currentSortColumn === "entities") {
            result = a.entities.localeCompare(b.entities);
        } else if (currentSortColumn === "pair") {
            result = a.pair - b.pair;
        }

        return sortDirection === "asc" ? result : -result;
    });
}

function loadAvailableSchedules() { }

async function loadCurrentWeekInfo() {
    try {
        const response = await fetch(
            `${window.API_ENDPOINTS.CURRENT_WEEK}?semcode=${currentSemcode}`
        );
        const weekInfo = await response.json();

        if (weekInfo && weekInfo.week_number) {
            const weekType = weekInfo.is_odd_week ? "нечетная" : "четная";
            const weekStart = new Date(weekInfo.week_start).toLocaleDateString(
                "ru-RU"
            );
            const weekEnd = new Date(weekInfo.week_end).toLocaleDateString(
                "ru-RU"
            );

            const infoElem = document.getElementById("currentWeekInfo");
            infoElem.innerHTML = `
        <p><strong>Текущая неделя семестра:</strong> ${weekInfo.week_number} (${weekType})</p>
        <p><strong>Период:</strong> ${weekStart} - ${weekEnd}</p>
      `;

            window.currentWeekData = {
                number: weekInfo.week_number,
                type: weekType,
                start: weekStart,
                end: weekEnd,
                is_odd: weekInfo.is_odd_week,
            };
        }
    } catch (error) {
        console.error("Error loading current week info:", error);
    }
}

function getEntityType(entity) {
    const filterWithEntity = filters.find((filter) =>
        filter.values.includes(entity)
    );

    return filterWithEntity ? filterWithEntity.type : null;
}

function handleCellClick(event) {
    const cell = event.currentTarget;
    const isFreeCell =
        cell.classList.contains("free-cell") ||
        cell.textContent.trim() === "Свободно";
    const hasBusyContent =
        cell.textContent.trim() !== "Свободно" &&
        cell.textContent.trim() !== "";

    if (isFreeCell) {

        const date = cell.dataset.date;
        const pair = cell.dataset.pair;
        const entity = cell.dataset.entity;
        const entityType = cell.dataset.entityType;
        openAddLessonModal(date, pair, entity, entityType);
    } else if (hasBusyContent) {
        const pairData = extractPairDataFromCell(cell);
        showLessonActions(cell, pairData);
    } else {
        console.log("Ячейка неопределенного типа");
    }
}

function extractPairDataFromCell(cell) {
    if (cell.dataset.lessonId) {
        return {
            id: parseInt(cell.dataset.lessonId),
            subject:
                cell.querySelector("strong")?.textContent ||
                "Неизвестный предмет",
        };
    }

    const subject = cell.querySelector("strong")?.textContent || "";
    const tempId = Math.floor(Math.random() * 1000000) + 1;

    return {
        id: tempId,
        subject: subject,
        isTemporaryId: true,
    };
}

function showLessonActions(cell, pairData) {

    closeAllActionMenus();

    if (!pairData || !pairData.id) {
        console.error("ID пары не найден, меню не будет показано");
        return;
    }

    const warningMessage = pairData.isTemporaryId
        ? '<div class="lesson-action-warning">ID пары не найден. Действия могут работать некорректно.</div>'
        : "";

    const menu = document.createElement("div");
    menu.className = "lesson-actions-menu";
    menu.innerHTML = `
    ${warningMessage}
    <div class="lesson-action" onclick="moveLessonModal(${pairData.id})">
      <span class="icon"><i class="fas fa-exchange-alt"></i></span>
      <span>Перенести</span>
    </div>
    <div class="lesson-action delete-action" onclick="deleteLesson(${pairData.id})">
      <span class="icon"><i class="fas fa-trash"></i></span>
      <span>Удалить</span>
    </div>
  `;

    document.body.appendChild(menu);

    const rect = cell.getBoundingClientRect();
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const scrollLeft =
        window.scrollX || document.documentElement.scrollLeft;

    menu.style.position = "absolute";
    menu.style.top = rect.bottom + scrollTop + "px";
    menu.style.left = rect.left + scrollLeft + "px";

    setTimeout(() => {
        const menuRect = menu.getBoundingClientRect();
        if (menuRect.right > window.innerWidth) {
            menu.style.left = rect.right + scrollLeft - menuRect.width + "px";
        }
        if (menuRect.bottom > window.innerHeight) {
            menu.style.top = rect.top + scrollTop - menuRect.height + "px";
        }
    }, 0);

    const closeMenu = (e) => {
        if (!menu.contains(e.target) && !cell.contains(e.target)) {
            menu.remove();
            document.removeEventListener("click", closeMenu);
        }
    };

    setTimeout(() => document.addEventListener("click", closeMenu), 10);
}

function closeAllActionMenus() {
    document
        .querySelectorAll(".lesson-actions-menu")
        .forEach((menu) => menu.remove());
}

window.renderSchedules = renderSchedules;
window.renderFreeSlotsTable = renderFreeSlotsTable;
window.formatDate = formatDate;
window.formatShortDate = formatShortDate;
window.sortTableByColumn = sortTableByColumn;
window.sortFreeSlots = sortFreeSlots;
window.loadAvailableSchedules = loadAvailableSchedules;
window.loadCurrentWeekInfo = loadCurrentWeekInfo;
window.getEntityType = getEntityType;
window.handleCellClick = handleCellClick;
window.extractPairDataFromCell = extractPairDataFromCell;
window.showLessonActions = showLessonActions;
window.closeAllActionMenus = closeAllActionMenus;
