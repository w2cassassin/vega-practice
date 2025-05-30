async function deleteVersion(versionId) {
    if (!confirm("Вы уверены, что хотите удалить эту версию?")) {
        return;
    }

    showLoading();
    try {
        const response = await fetch(`${window.API_HOST}/files/${versionId}`, {
            method: "DELETE",
        });
        if (!response.ok) throw new Error("Ошибка при удалении версии");
        await fetchVersions();
    } catch (error) {
        alert(error.message);
    } finally {
        hideLoading();
    }
}

function renderVersions() {
    const versionsList = document.getElementById("versionsList");
    versionsList.innerHTML = "";

    if (versions.length === 0) {
        versionsList.innerHTML = '<p class="has-text-grey">Список версий пуст</p>';
        return;
    }

    versions
        .slice()
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .forEach((version) => {
            const box = document.createElement("div");
            box.className = "version-box box";
            const date = new Date(version.created_at).toLocaleString("ru-RU");
            box.innerHTML = `
        <div class="version-info">
          <span class="version-date">${date}</span>
          <span class="version-count">${version.group_count} групп</span>
          <span class="version-groups-icon" data-version-id="${version.id}">
            <i class="fas fa-info-circle"></i>
          </span>
        </div>
        <div class="version-actions">
          <button class="version-delete" title="Удалить версию" data-version-id="${version.id}">
            <i class="fas fa-times"></i>
          </button>
        </div>
      `;
            versionsList.appendChild(box);

            const groupsIcon = box.querySelector('.version-groups-icon');
            if (version.group_names && version.group_names.length) {
                groupsIcon.addEventListener('mouseenter', function (e) {
                    showGroupsTooltip(e.target, version.group_names.join("\n"));
                });
                groupsIcon.addEventListener('mouseleave', function () {
                    hideGroupsTooltip();
                });
            }

            const deleteButton = box.querySelector('.version-delete');
            deleteButton.addEventListener('click', function () {
                deleteVersion(version.id);
            });
        });
}

let activeTooltip = null;

function showGroupsTooltip(element, groupsText) {
    hideGroupsTooltip();

    const tooltip = document.createElement('div');
    tooltip.className = 'groups-tooltip';
    tooltip.textContent = groupsText;
    document.body.appendChild(tooltip);

    const rect = element.getBoundingClientRect();
    const isNearTop = rect.top < 150;

    if (isNearTop) {
        tooltip.style.top = (rect.bottom + window.scrollY + 5) + 'px';
    } else {
        tooltip.style.top = (rect.top + window.scrollY - tooltip.offsetHeight - 5) + 'px';
    }

    tooltip.style.left = (rect.left + window.scrollX + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
    activeTooltip = tooltip;
}

function hideGroupsTooltip() {
    if (activeTooltip) {
        document.body.removeChild(activeTooltip);
        activeTooltip = null;
    }
}

window.addEventListener('scroll', function () {
    hideGroupsTooltip();
});

function renderVersionOptions() {
    const leftVersionSelect = document.getElementById("leftVersionSelect");
    const rightVersionSelect = document.getElementById("rightVersionSelect");

    leftVersionSelect.innerHTML = "";
    rightVersionSelect.innerHTML = "";

    if (versions.length === 0) {
        leftVersionSelect.innerHTML = '<option value="">Нет версий</option>';
        rightVersionSelect.innerHTML = '<option value="">Нет версий</option>';
        return;
    }

    const sortedVersions = versions
        .slice()
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    sortedVersions.forEach((version) => {
        const date = new Date(version.created_at).toLocaleString("ru-RU");
        const option = document.createElement("option");
        option.value = version.id;
        option.textContent = `${date} (${version.group_count} групп)`;

        leftVersionSelect.appendChild(option.cloneNode(true));
        rightVersionSelect.appendChild(option.cloneNode(true));
    });

    if (sortedVersions.length >= 2) {
        rightVersionSelect.value = sortedVersions[0].id;
        leftVersionSelect.value = sortedVersions[1].id;
    } else if (sortedVersions.length === 1) {
        rightVersionSelect.value = sortedVersions[0].id;
    }
}

function renderComparisonResults(result) {
    const comparisonResultsBody = document.getElementById("comparisonResultsBody");
    const comparisonResults = document.getElementById("comparisonResults");

    comparisonResultsBody.innerHTML = "";

    const sortedGroups = Object.entries(result.groups).sort((a, b) => {
        if (b[1].total !== a[1].total) {
            return b[1].total - a[1].total;
        }
        return a[0].localeCompare(b[0]);
    });

    sortedGroups.forEach(([groupName, groupData], index) => {
        const tr = document.createElement("tr");
        tr.className = "group-row";
        tr.dataset.detailsId = `details-${index}`;

        tr.innerHTML = `
      <td>
          ${groupData.total
                ? `<span class="icon toggle-icon"><i class="fas fa-chevron-right"></i></span>`
                : ""
            }
          ${groupName}
      </td>
      <td class="${groupData.total ? "has-changes" : "no-changes"}">
          ${groupData.total
                ? `${groupData.total} изменений`
                : "Нет изменений"
            }
      </td>
      <td>${renderSummaryBadges(groupData.summary, groupData)}</td>
    `;

        comparisonResultsBody.appendChild(tr);

        if (groupData.total > 0) {
            const detailsRow = document.createElement("tr");
            detailsRow.className = "details-row";
            detailsRow.id = `details-${index}`;
            const detailsCell = document.createElement("td");
            detailsCell.colSpan = 3;

            const detailsContent = document.createElement("div");
            detailsContent.className = "change-details";

            if (groupData.details.added.length > 0) {
                detailsContent.appendChild(
                    renderChangeSection(
                        "Добавленные пары",
                        groupData.details.added,
                        "added"
                    )
                );
            }
            if (groupData.details.removed.length > 0) {
                detailsContent.appendChild(
                    renderChangeSection(
                        "Удаленные пары",
                        groupData.details.removed,
                        "removed"
                    )
                );
            }
            if (groupData.details.modified.length > 0) {
                detailsContent.appendChild(
                    renderChangeSection(
                        "Измененные пары",
                        groupData.details.modified,
                        "modified"
                    )
                );
            }

            detailsCell.appendChild(detailsContent);
            detailsRow.appendChild(detailsCell);
            comparisonResultsBody.appendChild(detailsRow);

            tr.addEventListener("click", function () {
                const detailsRow = document.getElementById(
                    this.dataset.detailsId
                );
                const isVisible = detailsRow.classList.contains("is-visible");

                document.querySelectorAll(".details-row").forEach((row) => {
                    row.classList.remove("is-visible");
                });
                document.querySelectorAll(".group-row").forEach((row) => {
                    row.classList.remove("is-expanded");
                });

                if (!isVisible) {
                    detailsRow.classList.add("is-visible");
                    this.classList.add("is-expanded");
                }
            });
        }
    });

    comparisonResults.style.display = "block";
}

function renderSummaryBadges(summary, groupData) {
    if (!summary || typeof summary !== 'object') {
        return '<span class="has-text-grey">Нет подробностей</span>';
    }

    const badges = [];
    const labels = {
        subject: "предметы",
        teacher: "преподаватели",
        room: "аудитории",
        campus: "кампусы",
    };

    let hasNonZeroValues = false;
    for (const [key, count] of Object.entries(summary)) {
        if (count > 0) {
            hasNonZeroValues = true;
            badges.push(`
        <span class="tag is-info is-light">
            ${labels[key] || key}: ${count}
        </span>
      `);
        }
    }

    if (!hasNonZeroValues && groupData && groupData.total > 0 && groupData.details) {
        const details = groupData.details;

        const counts = {
            added: details.added.length,
            removed: details.removed.length,
            modified: details.modified.length
        };

        const typeLabels = {
            added: "добавлено",
            removed: "удалено",
            modified: "изменено"
        };

        for (const [type, count] of Object.entries(counts)) {
            if (count > 0) {
                badges.push(`
          <span class="tag is-info is-light">
              ${typeLabels[type]}: ${count}
          </span>
        `);
            }
        }
    }

    return badges.length > 0 ? badges.join(" ") : '<span class="has-text-grey">Нет подробностей</span>';
}

function getWeekTypeLabel(type) {
    return type === "odd" ? "нечётная неделя" : "чётная неделя";
}

function renderChangeSection(title, items, type) {
    const section = document.createElement("div");
    section.className = "change-section";

    const heading = document.createElement("h3");
    heading.className = "subtitle is-5";
    heading.textContent = title;
    section.appendChild(heading);

    items.sort((a, b) => {
        if (a.day !== b.day) {
            return a.day.localeCompare(b.day);
        }
        const pairA = parseInt(a.lesson.match(/Пара (\d+)/)?.[1] || 0);
        const pairB = parseInt(b.lesson.match(/Пара (\d+)/)?.[1] || 0);
        return pairA - pairB;
    });

    items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "change-card";

        const header = document.createElement("div");
        header.className = "change-header";
        header.innerHTML = `
      <div>
        <strong>${item.day}</strong>
        <span class="lesson-info">
          ${item.lesson.replace(/\(неделя \d+\)/, "")}
          <span class="week-type">${item.week % 2 === 1 ? "нечётная неделя" : "чётная неделя"
            }</span>
        </span>
      </div>
    `;

        if (type === "modified") {
            card.appendChild(header);

            const datesInfo =
                item.before.dates && item.before.dates.dates_str
                    ? `<div class="dates-info"><strong>Даты проведения:</strong> ${item.before.dates.dates_str}</div>`
                    : "";

            if (datesInfo) {
                const datesDiv = document.createElement("div");
                datesDiv.className = "dates-section";
                datesDiv.innerHTML = datesInfo;
                card.appendChild(datesDiv);
            }

            if (item.weeks_comparison && item.weeks_comparison.length > 0) {
                const weeksTable = document.createElement("div");
                weeksTable.className = "weeks-comparison";
                weeksTable.innerHTML = `
          <table class="table is-fullwidth weeks-table">
            <thead>
              <tr>
                <th>Неделя</th>
                <th>Было</th>
                <th>Стало</th>
                <th>Изменения</th>
              </tr>
            </thead>
            <tbody>
              ${item.weeks_comparison
                        .map((week) => {
                            const beforeInfo = week.before
                                ? `<div><strong>Предмет:</strong> ${week.before.lesson_type ? `<span class="lesson-type ${getLessonTypeClass(week.before.lesson_type)}">${week.before.lesson_type}</span> ` : ''}${week.before.subject
                                }</div>
                   <div><strong>Преподаватель:</strong> ${week.before.teacher
                                }</div>
                   <div><strong>Аудитория:</strong> ${week.before.room} ${week.before.campus
                                    ? `(${week.before.campus})`
                                    : ""
                                }</div>`
                                : "<div>—</div>";

                            const afterInfo = week.after
                                ? `<div><strong>Предмет:</strong> ${week.after.lesson_type ? `<span class="lesson-type ${getLessonTypeClass(week.after.lesson_type)}">${week.after.lesson_type}</span> ` : ''}${week.after.subject
                                }</div>
                   <div><strong>Преподаватель:</strong> ${week.after.teacher
                                }</div>
                   <div><strong>Аудитория:</strong> ${week.after.room} ${week.after.campus ? `(${week.after.campus})` : ""
                                }</div>`
                                : "<div>—</div>";

                            let changeTypeClass = "";
                            let changeTypeText = "";

                            switch (week.change_type) {
                                case "added":
                                    changeTypeClass = "has-text-success";
                                    changeTypeText = "Добавлено";
                                    break;
                                case "removed":
                                    changeTypeClass = "has-text-danger";
                                    changeTypeText = "Удалено";
                                    break;
                                case "modified":
                                    changeTypeClass = "has-text-warning";
                                    changeTypeText =
                                        "Изменено: " +
                                        week.changed_fields
                                            .map((f) => translateField(f))
                                            .join(", ");
                                    break;
                                default:
                                    changeTypeClass = "has-text-grey";
                                    changeTypeText = "Без изменений";
                            }

                            const isOddWeek = week.week % 2 !== 0;
                            const weekTypeLabel = isOddWeek ? "нечётная" : "чётная";

                            return `
                  <tr class="${week.change_type !== "unchanged" ? "week-changed" : ""
                                }">
                    <td>
                      <strong>Неделя ${week.week}</strong>
                      <div class="week-date">${weekTypeLabel}</div>
                    </td>
                    <td class="before-cell">${beforeInfo}</td>
                    <td class="after-cell">${afterInfo}</td>
                    <td class="${changeTypeClass} change-type-cell">${changeTypeText}</td>
                  </tr>
                `;
                        })
                        .join("")}
            </tbody>
          </table>
        `;
                card.appendChild(weeksTable);
            } else {
                card.innerHTML += `
          <div class="changes-table">
            <table class="table is-fullwidth">
              <thead>
                <tr>
                  <th>Поле</th>
                  <th>Было</th>
                  <th>Стало</th>
                </tr>
              </thead>
              <tbody>
                ${item.changes
                        .map(
                            (change) => `
                  <tr>
                    <td>${translateField(change.field)}</td>
                    <td class="old-value">${typeof change.from_value === "object" &&
                                    change.from_value.dates_str
                                    ? change.from_value.dates_str
                                    : change.from_value
                                }</td>
                    <td class="new-value">${typeof change.to_value === "object" &&
                                    change.to_value.dates_str
                                    ? change.to_value.dates_str
                                    : change.to_value
                                }</td>
                  </tr>
                `
                        )
                        .join("")}
              </tbody>
            </table>
          </div>
        `;
            }
        } else {
            card.appendChild(header);

            if (item.weeks_comparison && item.weeks_comparison.length > 0) {
                const weeksTable = document.createElement("div");
                weeksTable.className = "weeks-comparison";
                weeksTable.innerHTML = `
          <table class="table is-fullwidth weeks-table">
            <thead>
              <tr>
                <th>Неделя</th>
                <th>Было</th>
                <th>Стало</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              ${item.weeks_comparison
                        .map((week) => {
                            const detailsInfo = (details) => {
                                if (!details) return "<div>—</div>";
                                return `<div><strong>Предмет:</strong> ${details.lesson_type ? `<span class="lesson-type ${getLessonTypeClass(details.lesson_type)}">${details.lesson_type}</span> ` : ''}${details.subject
                                    }</div>
                      <div><strong>Преподаватель:</strong> ${details.teacher
                                    }</div>
                      <div><strong>Аудитория:</strong> ${details.room} ${details.campus ? `(${details.campus})` : ""
                                    }</div>`;
                            };

                            let changeTypeClass = "";
                            let changeTypeText = "";

                            if (week.change_type === type) {
                                changeTypeClass =
                                    type === "added"
                                        ? "has-text-success"
                                        : "has-text-danger";
                                changeTypeText =
                                    type === "added" ? "Добавлено" : "Удалено";
                            } else {
                                changeTypeClass = "has-text-grey";
                                changeTypeText = "Без изменений";
                            }

                            const weekTypeLabel =
                                week.week % 2 !== 0 ? "нечётная" : "чётная";

                            let beforeCell = "<div>—</div>";
                            let afterCell = "<div>—</div>";

                            if (week.change_type === "unchanged") {
                                beforeCell = detailsInfo(week.before);
                                afterCell = detailsInfo(week.after);
                            } else if (week.change_type === "added") {
                                afterCell = detailsInfo(week.after);
                            } else if (week.change_type === "removed") {
                                beforeCell = detailsInfo(week.before);
                            }

                            return `
                      <tr class="${week.change_type === type ? "week-changed" : ""
                                }">
                        <td>
                          <strong>Неделя ${week.week}</strong>
                          <div class="week-date">${weekTypeLabel}</div>
                        </td>
                        <td class="before-cell">${beforeCell}</td>
                        <td class="after-cell">${afterCell}</td>
                        <td class="${changeTypeClass} change-type-cell">${changeTypeText}</td>
                      </tr>
                    `;
                        })
                        .join("")}
            </tbody>
          </table>
        `;
                card.appendChild(weeksTable);
            } else {
                const datesInfo =
                    item.dates && item.dates.dates_str
                        ? `<div><strong>Даты проведения:</strong> ${item.dates.dates_str}</div>`
                        : "";

                card.innerHTML += `
          <div class="schedule-item">
            <div><strong>Предмет:</strong> ${item.details.lesson_type ? `<span class="lesson-type ${getLessonTypeClass(item.details.lesson_type)}">${item.details.lesson_type}</span> ` : ''}${item.details.subject}</div>
            <div><strong>Преподаватель:</strong> ${item.details.teacher}</div>
            <div><strong>Аудитория:</strong> ${item.details.room}</div>
            <div><strong>Кампус:</strong> ${item.details.campus}</div>
            ${datesInfo}
          </div>
        `;
            }
        }

        section.appendChild(card);
    });

    return section;
}

function translateField(field) {
    const translations = {
        subject: "Предмет",
        teacher: "Преподаватель",
        room: "Аудитория",
        campus: "Кампус",
        dates: "Даты проведения",
        lesson_type: "Тип занятия",
    };
    return translations[field] || field;
}

function getLessonTypeClass(lessonType) {
    if (!lessonType || lessonType === "—") return "";

    const typeClasses = {
        "ПР": "lesson-type-pr",
        "ЛК": "lesson-type-lk",
        "ЛАБ": "lesson-type-lab",
        "ЭКЗ": "lesson-type-exam",
        "ЗАЧ": "lesson-type-exam",
        "ЗАЧ-Д": "lesson-type-exam",
        "КР": "lesson-type-exam",
        "КП": "lesson-type-pr",
        "СР": "lesson-type-pr",
        "КОНС": "lesson-type-lk"
    };

    if (typeClasses[lessonType.trim()]) {
        return typeClasses[lessonType.trim()];
    }

    const type = lessonType.toLowerCase();
    if (type.includes("лк") || type.includes("лекц") || type.includes("конс")) return "lesson-type-lk";
    if (type.includes("пр") || type.includes("практич") || type.includes("ср")) return "lesson-type-pr";
    if (type.includes("лаб") || type.includes("лабор")) return "lesson-type-lab";
    if (type.includes("экз") || type.includes("зач") || type.includes("контр") || type.includes("курс")) return "lesson-type-exam";

    return "";
}

window.renderVersions = renderVersions;
window.renderVersionOptions = renderVersionOptions;
window.renderComparisonResults = renderComparisonResults;
window.translateField = translateField;
window.deleteVersion = deleteVersion;
window.getLessonTypeClass = getLessonTypeClass; 