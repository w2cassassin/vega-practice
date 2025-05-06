// Функции для работы с модальным окном добавления пары
function openAddLessonModal(date, pair, entity, entityType) {
    document.getElementById("lessonDate").value = date;
    document.getElementById("lessonPair").value = pair;
    document.getElementById("lessonEntity").value = entity;
    document.getElementById("lessonEntityType").value = entityType;

    document.getElementById("selectedTeachers").innerHTML = "";
    document.getElementById("selectedRooms").innerHTML = "";
    document.getElementById("selectedGroups").innerHTML = "";

    if (entityType === "group") {
        addTagItem("selectedGroups", entity);
    } else if (entityType === "prep") {
        addTagItem("selectedTeachers", entity);
    } else if (entityType === "room") {
        addTagItem("selectedRooms", entity);
    }

    document.getElementById("lessonSubject").value = "";
    document.getElementById("lessonTeacherInput").value = "";
    document.getElementById("lessonRoomInput").value = "";
    document.getElementById("lessonGroupInput").value = "";

    document.getElementById("repeatForWeeks").checked = false;
    document.getElementById("weeksSelector").classList.add("is-hidden");

    if (semesterDates && semesterDates.weeks_count) {
        generateWeekCheckboxes(semesterDates.weeks_count);
    } else {
        generateWeekCheckboxes(18);
    }

    updateCurrentWeekInfo();

    document.getElementById("addLessonModal").classList.add("is-active");

    initializeAutocomplete();
}

function closeAddLessonModal() {
    document.getElementById("addLessonModal").classList.remove("is-active");

    document.querySelectorAll(".autocomplete-dropdown").forEach((dropdown) => {
        dropdown.classList.add("is-hidden");
    });
}

function addTagItem(containerId, value) {
    if (!value.trim()) return;

    const container = document.getElementById(containerId);

    if (
        Array.from(container.querySelectorAll(".tag")).some(
            (item) => item.dataset.value === value
        )
    ) {
        return;
    }

    const tag = document.createElement("span");
    tag.classList.add("tag", "is-medium", "is-info", "mb-2", "mr-2");
    tag.dataset.value = value;

    tag.innerHTML = `
    ${value}
    <button type="button" class="delete is-small" onclick="this.parentNode.remove()"></button>
  `;

    container.appendChild(tag);
}

function addManualTeacher() {
    const input = document.getElementById("lessonTeacherInput");
    if (input.value.trim()) {
        addTagItem("selectedTeachers", input.value.trim());
        input.value = "";
    }
}

function addManualRoom() {
    const input = document.getElementById("lessonRoomInput");
    if (input.value.trim()) {
        addTagItem("selectedRooms", input.value.trim());
        input.value = "";
    }
}

function addManualGroup() {
    const input = document.getElementById("lessonGroupInput");
    if (input.value.trim()) {
        addTagItem("selectedGroups", input.value.trim());
        input.value = "";
    }
}

function getSelectedValues(containerId) {
    const container = document.getElementById(containerId);
    return Array.from(container.querySelectorAll(".tag")).map(
        (item) => item.dataset.value
    );
}

function initializeAutocomplete() {
    initFieldAutocomplete(
        "lessonSubject",
        "subjectDropdown",
        "subject",
        (item) => {
            document.getElementById("lessonSubject").value = item;
        }
    );

    initFieldAutocomplete(
        "lessonTeacherInput",
        "teacherDropdown",
        "prep",
        (item) => {
            addTagItem("selectedTeachers", item);
            document.getElementById("lessonTeacherInput").value = "";
        }
    );

    initFieldAutocomplete(
        "lessonRoomInput",
        "roomDropdown",
        "room",
        (item) => {
            addTagItem("selectedRooms", item);
            document.getElementById("lessonRoomInput").value = "";
        }
    );

    initFieldAutocomplete(
        "lessonGroupInput",
        "groupDropdown",
        "group",
        (item) => {
            addTagItem("selectedGroups", item);
            document.getElementById("lessonGroupInput").value = "";
        }
    );

    document.addEventListener("click", function (e) {
        if (!e.target.matches(".input")) {
            document.querySelectorAll(".autocomplete-dropdown").forEach((dropdown) => {
                dropdown.classList.add("is-hidden");
            });
        }
    });
}

function initFieldAutocomplete(
    inputId,
    dropdownId,
    searchType,
    selectCallback
) {
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);

    input.addEventListener("input", async function (e) {
        const query = e.target.value.trim();
        if (query.length < 1) {
            dropdown.classList.add("is-hidden");
            return;
        }

        try {
            const response = await fetch(
                `${window.API_ENDPOINTS.SEARCH_ITEMS}?search_type=${searchType}&q=${encodeURIComponent(query)}`
            );
            const suggestions = await response.json();

            dropdown.innerHTML = "";

            if (suggestions.length === 0) {
                dropdown.classList.add("is-hidden");
                return;
            }

            suggestions.forEach((item) => {
                const itemDiv = document.createElement("div");
                itemDiv.classList.add("autocomplete-item");
                itemDiv.textContent = item;
                itemDiv.onclick = () => {
                    selectCallback(item);
                    dropdown.classList.add("is-hidden");
                };
                dropdown.appendChild(itemDiv);
            });

            dropdown.classList.remove("is-hidden");
        } catch (error) {
            console.error(`Ошибка при загрузке списка для ${searchType}:`, error);
        }
    });

    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && input.value.trim()) {
            const activeItem = dropdown.querySelector(".autocomplete-item.active");
            if (activeItem) {
                selectCallback(activeItem.textContent);
            } else if (inputId !== "lessonSubject") {
                selectCallback(input.value.trim());
            }
            dropdown.classList.add("is-hidden");
            e.preventDefault();
        } else if (e.key === "ArrowDown") {
            navigateDropdown(dropdown, "down");
            e.preventDefault();
        } else if (e.key === "ArrowUp") {
            navigateDropdown(dropdown, "up");
            e.preventDefault();
        }
    });
}

function navigateDropdown(dropdown, direction) {
    const items = dropdown.querySelectorAll(".autocomplete-item");
    if (items.length === 0) return;

    const activeItem = dropdown.querySelector(".autocomplete-item.active");

    if (!activeItem) {
        if (direction === "down") {
            items[0].classList.add("active");
        } else {
            items[items.length - 1].classList.add("active");
        }
        return;
    }

    activeItem.classList.remove("active");

    let currentIndex = Array.from(items).indexOf(activeItem);

    if (direction === "down") {
        currentIndex = (currentIndex + 1) % items.length;
    } else {
        currentIndex = (currentIndex - 1 + items.length) % items.length;
    }

    items[currentIndex].classList.add("active");

    if (
        items[currentIndex].offsetTop < dropdown.scrollTop ||
        items[currentIndex].offsetTop + items[currentIndex].offsetHeight >
        dropdown.scrollTop + dropdown.offsetHeight
    ) {
        dropdown.scrollTop = items[currentIndex].offsetTop - dropdown.offsetHeight / 2;
    }
}

async function saveLesson() {
    const date = document.getElementById("lessonDate").value;
    const pair = document.getElementById("lessonPair").value;
    const subject = document.getElementById("lessonSubject").value;
    const lessonType = document.getElementById("lessonType").value;
    const kind = 0;

    const teachers = getSelectedValues("selectedTeachers");
    const rooms = getSelectedValues("selectedRooms");
    const groups = getSelectedValues("selectedGroups");

    if (
        !subject ||
        teachers.length === 0 ||
        rooms.length === 0 ||
        groups.length === 0
    ) {
        alert(
            "Пожалуйста, заполните все обязательные поля (предмет, преподаватель, аудитория, группа)"
        );
        return;
    }

    showLoading();

    try {
        const payload = {
            date: date,
            pair: parseInt(pair),
            subject: subject,
            worktype: parseInt(lessonType),
            teachers: teachers,
            rooms: rooms,
            kind: parseInt(kind),
            groups: groups,
            semcode: currentSemcode,
        };

        if (document.getElementById("repeatForWeeks").checked) {
            const selectedWeeks = getSelectedWeeks();
            if (selectedWeeks.length > 0) {
                payload.weeks = selectedWeeks;
            }
        }

        const response = await fetch(window.API_ENDPOINTS.ADD_LESSON, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Ошибка при добавлении пары");
        }

        const result = await response.json();

        if (result.errors && result.errors.length > 0) {
            const errorMessages = result.errors
                .map((err) => `Неделя ${err.week} (${err.date}): ${err.error}`)
                .join("\n");

            alert(`Пары созданы: ${result.total_created}\nОшибки:\n${errorMessages}`);
        }

        await loadSchedules();

        closeAddLessonModal();
    } catch (error) {
        console.error("Ошибка при сохранении пары:", error);
        alert(`Ошибка при сохранении: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function generateWeekCheckboxes(totalWeeks) {
    const container = document.getElementById("weekCheckboxes");
    container.innerHTML = "";
    container.classList.add("display-grid");

    for (let i = 1; i <= totalWeeks; i++) {
        const weekItem = document.createElement("div");
        weekItem.className = "week-item";

        const label = document.createElement("label");
        label.className = "week-checkbox-label";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = i;
        input.className = "week-checkbox";

        input.addEventListener("change", function () {
            if (this.checked) {
                label.classList.add("week-checkbox-active");
            } else {
                label.classList.remove("week-checkbox-active");
            }
        });

        label.textContent = i;

        label.appendChild(input);
        weekItem.appendChild(label);
        container.appendChild(weekItem);
    }
}

function selectAllWeeks() {
    document.querySelectorAll(".week-checkbox").forEach((checkbox) => {
        checkbox.checked = true;
        const label = checkbox.closest(".week-checkbox-label");
        if (label) {
            label.classList.add("week-checkbox-active");
        }
    });
}

function selectOddWeeks() {
    document.querySelectorAll(".week-checkbox").forEach((checkbox) => {
        const weekNumber = parseInt(checkbox.value);
        checkbox.checked = weekNumber % 2 === 1;
        const label = checkbox.closest(".week-checkbox-label");
        if (label) {
            if (checkbox.checked) {
                label.classList.add("week-checkbox-active");
            } else {
                label.classList.remove("week-checkbox-active");
            }
        }
    });
}

function selectEvenWeeks() {
    document.querySelectorAll(".week-checkbox").forEach((checkbox) => {
        const weekNumber = parseInt(checkbox.value);
        checkbox.checked = weekNumber % 2 === 0;
        const label = checkbox.closest(".week-checkbox-label");
        if (label) {
            if (checkbox.checked) {
                label.classList.add("week-checkbox-active");
            } else {
                label.classList.remove("week-checkbox-active");
            }
        }
    });
}

function deselectAllWeeks() {
    document.querySelectorAll(".week-checkbox").forEach((checkbox) => {
        checkbox.checked = false;
        const label = checkbox.closest(".week-checkbox-label");
        if (label) {
            label.classList.remove("week-checkbox-active");
        }
    });
}

function updateCurrentWeekInfo() {
    if (window.currentWeekData) {
        document.getElementById("currentWeekNumber").textContent = window.currentWeekData.number;
        document.getElementById("currentWeekType").textContent = window.currentWeekData.type;

        document.querySelectorAll(".week-checkbox").forEach((cb) => {
            if (parseInt(cb.value) === window.currentWeekData.number) {
                cb.checked = true;
            }
        });
    }
}

function getSelectedWeeks() {
    const selected = [];
    document.querySelectorAll(".week-checkbox:checked").forEach((cb) => {
        selected.push(parseInt(cb.value));
    });
    return selected;
}

async function deleteLesson(lessonId) {
    closeAllActionMenus();

    if (!confirm("Вы уверены, что хотите удалить пару?")) {
        return;
    }

    showLoading();

    try {
        const response = await fetch(
            `${window.API_ENDPOINTS.DELETE_LESSON}?lesson_id=${lessonId}`,
            {
                method: "DELETE",
            }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Ошибка при удалении пары");
        }

        await loadSchedules();
    } catch (error) {
        console.error("Ошибка при удалении пары:", error);
        alert(`Ошибка при удалении: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function moveLessonModal(lessonId) {
    closeAllActionMenus();

    document.getElementById("moveLessonId").value = lessonId;
    document.getElementById("moveTargetDate").value = "";
    document.getElementById("moveTargetPair").value = "1";
    document.getElementById("moveReason").value = "";
    document.getElementById("moveComment").value = "";
    document.getElementById("moveLessonModal").classList.add("is-active");
}

function closeMoveLessonModal() {
    document.getElementById("moveLessonModal").classList.remove("is-active");
}

async function saveMove() {
    const lessonId = parseInt(document.getElementById("moveLessonId").value);
    const targetDate = document.getElementById("moveTargetDate").value;
    const targetPair = parseInt(document.getElementById("moveTargetPair").value);
    const reason = document.getElementById("moveReason").value;
    const comment = document.getElementById("moveComment").value;

    if (!targetDate) {
        alert("Пожалуйста, выберите дату переноса");
        return;
    }

    showLoading();

    try {
        const response = await fetch(window.API_ENDPOINTS.MOVE_LESSON, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                lesson_id: lessonId,
                target_date: targetDate,
                target_pair: targetPair,
                reason: reason,
                comment: comment,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Ошибка при переносе пары");
        }

        closeMoveLessonModal();

        await loadSchedules();
    } catch (error) {
        console.error("Ошибка при переносе пары:", error);
        alert(`Ошибка при переносе: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function downloadGroupSchedules(groups) {
    if (!groups || groups.length === 0) {
        alert("Пожалуйста, выберите хотя бы одну группу для загрузки");
        return;
    }

    showLoading();

    try {
        const response = await fetch(window.API_ENDPOINTS.DOWNLOAD_SCHEDULES, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ groups }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Не удалось загрузить расписание групп");
        }

        const result = await response.json();
        alert(`Успешно загружено расписание для ${result.group_count} групп`);
        return result;
    } catch (error) {
        console.error("Ошибка при загрузке расписаний групп:", error);
        alert(`Ошибка: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function addGroupsByYear(year, hasAsterisk = false) {
    showLoading();

    try {
        let groupFilterId = null;
        let groupFilter = filters.find((filter) => filter.type === "group");

        if (!groupFilter) {
            groupFilterId = Date.now();
            const filterDiv = document.createElement("div");
            filterDiv.classList.add("field", "filter");
            filterDiv.dataset.filterId = groupFilterId;

            filterDiv.innerHTML = `
        <label class="label">Группа</label>
        <div class="control">
          <input class="input" type="text" oninput="showSuggestions(event, 'group', ${groupFilterId})" placeholder="Начните вводить...">
          <div class="dropdown-content" id="dropdown-${groupFilterId}"></div>
          <div class="selected-items" id="selected-${groupFilterId}"></div>
        </div>
      `;
            document.getElementById("filtersContainer").appendChild(filterDiv);

            filters.push({ id: groupFilterId, type: "group", values: [] });
            groupFilter = filters.find((filter) => filter.id === groupFilterId);
        } else {
            groupFilterId = groupFilter.id;
        }

        const response = await fetch(
            `${window.API_ENDPOINTS.SEARCH_ITEMS}?search_type=group&q=&limit=1000`
        );
        const allGroups = await response.json();

        const yearGroups = allGroups.filter((group) => {
            const parts = group.split("-");
            if (parts.length === 3) {
                const lastPart = parts[2];
                if (hasAsterisk) {
                    return lastPart.endsWith(year + "*");
                } else {
                    return lastPart.endsWith(year) && !lastPart.endsWith(year + "*");
                }
            }
            return false;
        });

        const selectedItemsDiv = document.getElementById(`selected-${groupFilterId}`);

        for (const group of yearGroups) {
            if (!groupFilter.values.includes(group)) {
                groupFilter.values.push(group);

                const itemDiv = document.createElement("div");
                itemDiv.classList.add("selected-item");
                itemDiv.textContent = group;

                const removeButton = document.createElement("button");
                removeButton.innerHTML = "&times;";
                removeButton.onclick = () => {
                    groupFilter.values = groupFilter.values.filter((v) => v !== group);
                    itemDiv.remove();
                };

                itemDiv.appendChild(removeButton);
                selectedItemsDiv.appendChild(itemDiv);
            }
        }

        updateYearPresetsVisibility();
    } catch (error) {
        console.error("Ошибка при добавлении групп по году:", error);
    } finally {
        hideLoading();
    }
}

function generateYearPresets() {
    const presetsContainer = document.getElementById("groupPresets");
    const presetsAsteriskContainer = document.getElementById("groupPresetsAsterisk");
    presetsContainer.innerHTML = "";
    presetsAsteriskContainer.innerHTML = "";

    const currentYear = new Date().getFullYear();

    for (let i = 0; i < 5; i++) {
        const year = currentYear - i;
        const shortYear = (year % 100).toString().padStart(2, "0");

        const button = document.createElement("button");
        button.className = "button is-primary is-light";
        button.textContent = year;
        button.onclick = () => addGroupsByYear(shortYear);
        presetsContainer.appendChild(button);

        const buttonAsterisk = document.createElement("button");
        buttonAsterisk.className = "button is-success is-light";
        buttonAsterisk.textContent = year + "*";
        buttonAsterisk.onclick = () => addGroupsByYear(shortYear, true);
        presetsAsteriskContainer.appendChild(buttonAsterisk);
    }

    // Используем setTimeout для гарантированного обновления видимости после создания пресетов
    setTimeout(updateYearPresetsVisibility, 20);
}

// Экспортируем функции в глобальный объект
window.openAddLessonModal = openAddLessonModal;
window.closeAddLessonModal = closeAddLessonModal;
window.addTagItem = addTagItem;
window.addManualTeacher = addManualTeacher;
window.addManualRoom = addManualRoom;
window.addManualGroup = addManualGroup;
window.getSelectedValues = getSelectedValues;
window.initializeAutocomplete = initializeAutocomplete;
window.initFieldAutocomplete = initFieldAutocomplete;
window.saveLesson = saveLesson;
window.generateWeekCheckboxes = generateWeekCheckboxes;
window.selectAllWeeks = selectAllWeeks;
window.selectOddWeeks = selectOddWeeks;
window.selectEvenWeeks = selectEvenWeeks;
window.deselectAllWeeks = deselectAllWeeks;
window.updateCurrentWeekInfo = updateCurrentWeekInfo;
window.getSelectedWeeks = getSelectedWeeks;
window.deleteLesson = deleteLesson;
window.moveLessonModal = moveLessonModal;
window.closeMoveLessonModal = closeMoveLessonModal;
window.saveMove = saveMove;
window.addGroupsByYear = addGroupsByYear;
window.generateYearPresets = generateYearPresets;
window.downloadGroupSchedules = downloadGroupSchedules; 