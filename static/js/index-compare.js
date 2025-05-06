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
          <span class="version-groups-icon" data-groups="${version.group_names && version.group_names.length
                    ? version.group_names.join("\n")
                    : ""
                }">
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

            const deleteButton = box.querySelector('.version-delete');
            deleteButton.addEventListener('click', function () {
                deleteVersion(version.id);
            });
        });
}

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
    // Проверка наличия и корректности объекта summary
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

    // Проверяем, есть ли ненулевые значения в summary
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

    // Если в summary все нули, но есть изменения, генерируем бейджи на основе details
    if (!hasNonZeroValues && groupData && groupData.total > 0 && groupData.details) {
        const details = groupData.details;

        // Считаем количество изменений по типам
        const counts = {
            added: details.added.length,
            removed: details.removed.length,
            modified: details.modified.length
        };

        // Типы бейджей для разных изменений
        const typeLabels = {
            added: "добавлено",
            removed: "удалено",
            modified: "изменено"
        };

        // Добавляем бейджи для каждого типа изменений
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
            const subject = item.before.subject || "—";
            header.innerHTML += `<div class="subject-name">${subject}</div>`;

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
                const weekType = item.week % 2 === 1 ? "нечётные" : "чётные";
                weeksTable.innerHTML = `
          <h4 class="weeks-comparison-title">Изменения по ${weekType} неделям:</h4>
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
                                ? `<div><strong>Предмет:</strong> ${week.before.subject
                                }</div>
                   <div><strong>Преподаватель:</strong> ${week.before.teacher
                                }</div>
                   <div><strong>Аудитория:</strong> ${week.before.room} ${week.before.campus
                                    ? `(${week.before.campus})`
                                    : ""
                                }</div>`
                                : "<div>—</div>";

                            const afterInfo = week.after
                                ? `<div><strong>Предмет:</strong> ${week.after.subject
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
            const subject = item.details.subject || "—";
            header.innerHTML += `<div class="subject-name">${subject}</div>`;

            card.appendChild(header);

            if (item.weeks_comparison && item.weeks_comparison.length > 0) {
                const weeksTable = document.createElement("div");
                weeksTable.className = "weeks-comparison";
                const weekType = item.week % 2 === 1 ? "нечётные" : "чётные";
                weeksTable.innerHTML = `
          <h4 class="weeks-comparison-title">Информация по ${weekType} неделям:</h4>
          <table class="table is-fullwidth weeks-table">
            <thead>
              <tr>
                <th>Неделя</th>
                ${type === "removed"
                        ? "<th>Было</th><th></th>"
                        : "<th></th><th>Стало</th>"
                    }
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              ${item.weeks_comparison
                        .map((week) => {
                            const detailsInfo = (details) => {
                                if (!details) return "<div>—</div>";
                                return `<div><strong>Предмет:</strong> ${details.subject
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

                            if (type === "added") {
                                return `
                      <tr class="${week.change_type === type ? "week-changed" : ""
                                    }">
                        <td>
                          <strong>Неделя ${week.week}</strong>
                          <div class="week-date">${weekTypeLabel}</div>
                        </td>
                        <td></td>
                        <td class="after-cell">${detailsInfo(
                                        week.after
                                    )}</td>
                        <td class="${changeTypeClass} change-type-cell">${changeTypeText}</td>
                      </tr>
                    `;
                            } else {
                                return `
                      <tr class="${week.change_type === type ? "week-changed" : ""
                                    }">
                        <td>
                          <strong>Неделя ${week.week}</strong>
                          <div class="week-date">${weekTypeLabel}</div>
                        </td>
                        <td class="before-cell">${detailsInfo(
                                        week.before
                                    )}</td>
                        <td></td>
                        <td class="${changeTypeClass} change-type-cell">${changeTypeText}</td>
                      </tr>
                    `;
                            }
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
            <div><strong>Предмет:</strong> ${item.details.subject}</div>
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
    };
    return translations[field] || field;
}

window.renderVersions = renderVersions;
window.renderVersionOptions = renderVersionOptions;
window.renderComparisonResults = renderComparisonResults;
window.translateField = translateField;
window.deleteVersion = deleteVersion; 