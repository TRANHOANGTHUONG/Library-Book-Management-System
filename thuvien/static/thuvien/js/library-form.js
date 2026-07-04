function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function renderLibraryMessage(data) {
    const message = escapeHtml(data.message || "Thao tác đã hoàn tất.");
    const details = [];

    if (data.ma_sach !== undefined) {
        details.push(`Mã sách: ${escapeHtml(data.ma_sach)}`);
    }

    if (data.ma_the_loai !== undefined && data.ten_the_loai !== undefined) {
        details.push(`Thể loại: Mã ${escapeHtml(data.ma_the_loai)} - ${escapeHtml(data.ten_the_loai)}`);
    } else if (data.ma_the_loai !== undefined) {
        details.push(`Mã thể loại: ${escapeHtml(data.ma_the_loai)}`);
    } else if (data.ten_the_loai !== undefined) {
        details.push(`Tên thể loại: ${escapeHtml(data.ten_the_loai)}`);
    }

    const coHaiLanXacNhan =
        data.so_luong_xac_nhan_dau !== undefined && data.so_luong_xac_nhan_dau !== null &&
        data.so_luong_xac_nhan_sau !== undefined && data.so_luong_xac_nhan_sau !== null;

    if (coHaiLanXacNhan) {
        details.push(`Xác nhận lần 1: còn ${escapeHtml(data.so_luong_xac_nhan_dau)} cuốn`);
        details.push(`Xác nhận lần 2: còn ${escapeHtml(data.so_luong_xac_nhan_sau)} cuốn`);
    } else if (data.so_luong !== undefined && data.so_luong !== null) {
        details.push(`Số lượng ghi nhận: ${escapeHtml(data.so_luong)}`);
    }

    const coThongKeHaiLan =
        data.so_dau_sach_lan_1 !== undefined && data.so_dau_sach_lan_1 !== null &&
        data.so_dau_sach_lan_2 !== undefined && data.so_dau_sach_lan_2 !== null;

    if (coThongKeHaiLan) {
        details.push(`Số đầu sách lần 1: ${escapeHtml(data.so_dau_sach_lan_1)}`);
        details.push(`Số đầu sách lần 2: ${escapeHtml(data.so_dau_sach_lan_2)}`);
    } else if (data.so_dau_sach !== undefined && data.so_dau_sach !== null) {
        details.push(`Số đầu sách ghi nhận: ${escapeHtml(data.so_dau_sach)}`);
    }

    if (data.trang_thai) {
        details.push(`Trạng thái: ${escapeHtml(data.trang_thai)}`);
    }

    let html = `<strong>✓ ${message}</strong>`;

    if (details.length > 0) {
        html += `<div class="mt-2 small">${details.join("<br>")}</div>`;
    }

    return html;
}

function renderStockConfirmProgress(resultBox, stage) {
    const stages = {
        lan1: {
            title: "Đang xác nhận số lượng lần 1...",
            text: "Hệ thống đang ghi nhận số lượng ban đầu của đầu sách."
        },
        cho: {
            title: "Đã xác nhận lần 1, đang chờ rà soát lại...",
        },
        lan2: {
            title: "Đang xác nhận số lượng lần 2...",
            text: "Hệ thống đang đối chiếu lại số lượng trước khi hoàn tất."
        }
    };

    const current = stages[stage] || stages.lan1;

    resultBox.className = "alert alert-info mt-3";
    resultBox.innerHTML = `
        <strong>${escapeHtml(current.title)}</strong>
        <div class="mt-2 small">${escapeHtml(current.text)}</div>
        <div class="progress mt-3" role="progressbar" aria-label="Tiến trình xác nhận tồn kho">
            <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: ${stage === "lan1" ? "35" : stage === "cho" ? "65" : "90"}%"></div>
        </div>
    `;
}

function updateVisibleSections(form) {
    const taskInput = form.querySelector("[name='cong_viec']");
    if (!taskInput) return;

    const taskValue = taskInput.value;

    form.querySelectorAll("[data-section]").forEach(section => {
        const allowed = section.dataset.section.split(" ");
        section.hidden = !allowed.includes(taskValue);
    });
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form[data-library-form]").forEach(form => {
        const resultSelector = form.dataset.resultTarget || "#ketQuaXuLy";
        const resultBox = document.querySelector(resultSelector);
        const submitButton = form.querySelector("button[type='submit']");

        updateVisibleSections(form);

        form.querySelectorAll("[name='cong_viec']").forEach(input => {
            input.addEventListener("change", () => updateVisibleSections(form));
        });

        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            if (!resultBox) return;

            const formData = new FormData(form);
            const isStockConfirmFlow = form.dataset.stockConfirmFlow === "true";
            const isStockChecking = isStockConfirmFlow && formData.get("cong_viec") === "kiem_tra";
            const progressTimers = [];

            if (isStockChecking) {
                renderStockConfirmProgress(resultBox, "lan1");
                progressTimers.push(setTimeout(() => renderStockConfirmProgress(resultBox, "cho"), 800));
                progressTimers.push(setTimeout(() => renderStockConfirmProgress(resultBox, "lan2"), 9000));
            } else {
                resultBox.className = "alert alert-info mt-3";
                resultBox.textContent = "Đang xử lý, vui lòng chờ...";
            }

            if (submitButton) {
                submitButton.disabled = true;
            }

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: formData,
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });

                const data = await response.json();

                if (!response.ok || data.success === false || data.ok === false) {
                    throw new Error(data.message || "Không thể hoàn tất thao tác.");
                }

                progressTimers.forEach(timer => clearTimeout(timer));
                resultBox.className = "alert alert-success mt-3";
                resultBox.innerHTML = renderLibraryMessage(data);
            } catch (error) {
                progressTimers.forEach(timer => clearTimeout(timer));
                resultBox.className = "alert alert-danger mt-3";
                resultBox.textContent = error.message || "Có lỗi xảy ra trong quá trình xử lý.";
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                }
            }
        });
    });
});