const apiBase = "http://127.0.0.1:8000/api";

document.getElementById("uploadBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("fileInput");
  const status = document.getElementById("status");

  if (!fileInput.files.length) {
    alert("Vui lòng chọn tệp CSV báo cáo tài chính!");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  status.innerText = "⏳ Đang tải và phân tích dữ liệu...";

  try {
    const res = await fetch(`${apiBase}/upload`, { method: "POST", body: formData });
    const data = await res.json();
    status.innerText = data.message || "Đã xử lý xong!";

    const recRes = await fetch(`${apiBase}/recommendations`);
    const recData = await recRes.json();
    renderTable(recData.recommendations);
    renderChart(recData.recommendations);
  } catch (error) {
    status.innerText = "❌ Lỗi khi xử lý dữ liệu!";
    console.error(error);
  }
});

function renderTable(data) {
  const table = document.getElementById("resultTable");
  table.innerHTML = `
    <tr class="bg-blue-100 font-semibold text-blue-700">
      <th class="p-2 border">Doanh nghiệp</th>
      <th class="p-2 border">Z-Score</th>
      <th class="p-2 border">Rủi ro</th>
      <th class="p-2 border">Khuyến nghị</th>
    </tr>
  `;
  data.forEach(d => {
    const color = d.Khuyen_nghi_vay.includes("Nên") ? "text-green-600" :
                  d.Khuyen_nghi_vay.includes("xem xét") ? "text-orange-600" : "text-red-600";
    table.innerHTML += `
      <tr class="hover:bg-gray-50 transition">
        <td class="p-2 border">${d.Ten_doanh_nghiep}</td>
        <td class="p-2 border text-center">${d.Z_score.toFixed(2)}</td>
        <td class="p-2 border text-center">${d.Danh_gia_rui_ro}</td>
        <td class="p-2 border text-center font-semibold ${color}">
          ${d.Khuyen_nghi_vay}
        </td>
      </tr>
    `;
  });
}

function renderChart(data) {
  const ctx = document.getElementById("zscoreChart");
  const labels = data.map(d => d.Ten_doanh_nghiep);
  const scores = data.map(d => d.Z_score);

  new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Z-Score (Altman)",
        data: scores,
        backgroundColor: scores.map(s => 
          s > 2.99 ? "rgba(34,197,94,0.6)" :
          s > 1.8 ? "rgba(249,115,22,0.6)" :
                     "rgba(239,68,68,0.6)"
        ),
        borderColor: "rgba(30,64,175,0.9)",
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      scales: { y: { beginAtZero: true, title: { display: true, text: "Z-Score" } } },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      }
    }
  });
}
