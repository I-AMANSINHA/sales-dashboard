window.addEventListener('DOMContentLoaded', () => {
    fetch('/api/dashboard')
        .then(resp => resp.json())
        .then(data => {
            document.getElementById('sales').textContent = data.sales;
            document.getElementById('customers').textContent = data.customers;
            document.getElementById('orders').textContent = data.orders;

            const tbody = document.getElementById('order-list');
            tbody.innerHTML = ''; 
            data.recent.forEach(o => {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${o.id}</td><td>${o.customer}</td><td>${o.product}</td><td>${o.amount}</td>`;
                tbody.appendChild(row);
            });
        })
        .catch(err => console.error("Error loading API metrics data:", err));
});



