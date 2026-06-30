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
                row.innerHTML = `<td>${o.id}</td><td>${o.customer}</td><td>${o.product}</td><td>${o.amount}</td>
			            	<td>
           				 <button class="btn btn-sm btn-danger py-1 px-2 m-0 w-auto" onclick="deleteOrder(${o.id})">
               				 🗑 Delete
           				 </button>
        				</td>`;
                tbody.appendChild(row);
            });
        })
        .catch(err => console.error("Error loading API metrics data:", err));
});

// Global execution window scope for handling row drops asynchronously
window.deleteOrder = (orderId) => {
    if (confirm(`Are you sure you want to permanently delete Order #${orderId}?`)) {
        fetch(`/api/orders/${orderId}/delete`, { method: 'POST' })
            .then(resp => {
                if (resp.ok) {
                    // Instantly recalculate summary totals and slide remaining rows upwards
                    loadDashboardData(); 
                } else {
                    alert("Failed to process transaction deletion.");
                }
            })
            .catch(err => console.error("Deletion pipeline down:", err));
    }
};


