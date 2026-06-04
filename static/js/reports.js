/**
 * Reports generation and display logic
 */

let currentReportType = 'daily';
let currentReportData = null;

// ===== REPORT TYPE SELECTION =====

function changeReportType() {
    const reportType = document.getElementById('report-type').value;
    currentReportType = reportType;
    
    // Show/hide date inputs based on report type
    const dateInput = document.getElementById('date-input');
    const startDateInput = document.getElementById('start-date-input');
    const endDateInput = document.getElementById('end-date-input');
    
    dateInput.style.display = 'none';
    startDateInput.style.display = 'none';
    endDateInput.style.display = 'none';
    
    if (reportType === 'daily') {
        dateInput.style.display = 'block';
    } else if (reportType === 'range' || reportType === 'top-products' || reportType === 'cashier') {
        startDateInput.style.display = 'block';
        endDateInput.style.display = 'block';
    }
}

// ===== REPORT GENERATION =====

async function generateReport() {
    const reportType = document.getElementById('report-type').value;
    
    try {
        showLoading(true);
        
        let reportData;
        
        switch (reportType) {
            case 'daily':
                reportData = await generateDailyReport();
                break;
            case 'range':
                reportData = await generateRangeReport();
                break;
            case 'top-products':
                reportData = await generateTopProductsReport();
                break;
            case 'cashier':
                reportData = await generateCashierReport();
                break;
            case 'inventory':
                reportData = await generateInventoryReport();
                break;
            default:
                throw new Error('Invalid report type');
        }
        
        currentReportData = reportData;
        displayReport(reportData, reportType);
        
    } catch (error) {
        showToast(error.message || 'Failed to generate report', 'error');
    } finally {
        showLoading(false);
    }
}

// ===== DAILY SALES REPORT =====

async function generateDailyReport() {
    const date = document.getElementById('report-date').value;
    const response = await apiRequest(`/api/reports/sales/daily?report_date=${date}`);
    return response;
}

function displayDailyReport(data) {
    return `
        <div class="report-header">
            <h2>Daily Sales Report</h2>
            <p class="report-date">${data.date}</p>
        </div>
        
        <div class="report-metrics">
            <div class="metric-card">
                <h3>Total Sales</h3>
                <p class="metric-value">${formatCurrency(data.total_sales)}</p>
            </div>
            
            <div class="metric-card">
                <h3>Transactions</h3>
                <p class="metric-value">${data.total_transactions}</p>
            </div>
            
            <div class="metric-card">
                <h3>Average Transaction</h3>
                <p class="metric-value">${formatCurrency(data.average_transaction)}</p>
            </div>
            
            <div class="metric-card">
                <h3>Total Profit</h3>
                <p class="metric-value">${formatCurrency(data.total_profit)}</p>
            </div>
        </div>
        
        <div class="report-section">
            <h3>Payment Method Breakdown</h3>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Payment Method</th>
                        <th>Amount</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Cash</td>
                        <td>${formatCurrency(data.payment_breakdown.cash)}</td>
                    </tr>
                    <tr>
                        <td>Card</td>
                        <td>${formatCurrency(data.payment_breakdown.card)}</td>
                    </tr>
                    <tr>
                        <td>Online</td>
                        <td>${formatCurrency(data.payment_breakdown.online)}</td>
                    </tr>
                    <tr>
                        <td>Credit</td>
                        <td>${formatCurrency(data.payment_breakdown.credit)}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    `;
}

// ===== DATE RANGE REPORT =====

async function generateRangeReport() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    if (!startDate || !endDate) {
        throw new Error('Please select start and end dates');
    }
    
    const response = await apiRequest(
        `/api/reports/sales/range?start_date=${startDate}&end_date=${endDate}`
    );
    return response;
}

function displayRangeReport(data) {
    return `
        <div class="report-header">
            <h2>Sales Range Report</h2>
            <p class="report-date">${data.start_date} - ${data.end_date}</p>
        </div>
        
        <div class="report-metrics">
            <div class="metric-card">
                <h3>Total Sales</h3>
                <p class="metric-value">${formatCurrency(data.total_sales)}</p>
            </div>
            
            <div class="metric-card">
                <h3>Total Transactions</h3>
                <p class="metric-value">${data.total_transactions}</p>
            </div>
            
            <div class="metric-card">
                <h3>Total Profit</h3>
                <p class="metric-value">${formatCurrency(data.total_profit)}</p>
            </div>
        </div>
        
        <div class="report-section">
            <h3>Daily Breakdown</h3>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Sales</th>
                        <th>Transactions</th>
                        <th>Profit</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.daily_breakdown.map(day => `
                        <tr>
                            <td>${day.date}</td>
                            <td>${formatCurrency(day.sales)}</td>
                            <td>${day.transactions}</td>
                            <td>${formatCurrency(day.profit)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// ===== TOP PRODUCTS REPORT =====

async function generateTopProductsReport() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    let url = '/api/reports/products/top-selling?limit=20';
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    
    const response = await apiRequest(url);
    return response;
}

function displayTopProductsReport(data) {
    return `
        <div class="report-header">
            <h2>Top Selling Products</h2>
        </div>
        
        <table class="report-table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Product Name</th>
                    <th>Quantity Sold</th>
                    <th>Revenue</th>
                    <th>Transactions</th>
                </tr>
            </thead>
            <tbody>
                ${data.map((product, index) => `
                    <tr>
                        <td>${index + 1}</td>
                        <td>${escapeHtml(product.product_name)}</td>
                        <td>${product.total_quantity}</td>
                        <td>${formatCurrency(product.total_revenue)}</td>
                        <td>${product.transaction_count}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// ===== CASHIER PERFORMANCE REPORT =====

async function generateCashierReport() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    let url = '/api/reports/cashier/performance';
    if (startDate) url += `?start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    
    const response = await apiRequest(url);
    return response;
}

function displayCashierReport(data) {
    return `
        <div class="report-header">
            <h2>Cashier Performance Report</h2>
        </div>
        
        <table class="report-table">
            <thead>
                <tr>
                    <th>Cashier</th>
                    <th>Transactions</th>
                    <th>Total Sales</th>
                    <th>Average Transaction</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(cashier => `
                    <tr>
                        <td>${escapeHtml(cashier.cashier_name)}</td>
                        <td>${cashier.transaction_count}</td>
                        <td>${formatCurrency(cashier.total_sales)}</td>
                        <td>${formatCurrency(cashier.average_transaction)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// ===== INVENTORY VALUATION REPORT =====

async function generateInventoryReport() {
    const response = await apiRequest('/api/reports/inventory/valuation');
    return response;
}

function displayInventoryReport(data) {
    return `
        <div class="report-header">
            <h2>Inventory Valuation Report</h2>
        </div>
        
        <div class="report-metrics">
            <div class="metric-card">
                <h3>Total Products</h3>
                <p class="metric-value">${data.total_products}</p>
            </div>
            
            <div class="metric-card">
                <h3>Cost Value</h3>
                <p class="metric-value">${formatCurrency(data.total_cost_value)}</p>
            </div>
            
            <div class="metric-card">
                <h3>Retail Value</h3>
                <p class="metric-value">${formatCurrency(data.total_retail_value)}</p>
            </div>
            
            <div class="metric-card">
                <h3>Potential Profit</h3>
                <p class="metric-value">${formatCurrency(data.total_potential_profit)}</p>
            </div>
        </div>
        
        <div class="report-section">
            <h3>Category Breakdown</h3>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Items</th>
                        <th>Cost Value</th>
                        <th>Retail Value</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.category_breakdown.map(cat => `
                        <tr>
                            <td>${escapeHtml(cat.category)}</td>
                            <td>${cat.items}</td>
                            <td>${formatCurrency(cat.cost_value)}</td>
                            <td>${formatCurrency(cat.retail_value)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// ===== REPORT DISPLAY =====

function displayReport(data, reportType) {
    const container = document.getElementById('report-content');
    
    let html;
    
    switch (reportType) {
        case 'daily':
            html = displayDailyReport(data);
            break;
        case 'range':
            html = displayRangeReport(data);
            break;
        case 'top-products':
            html = displayTopProductsReport(data);
            break;
        case 'cashier':
            html = displayCashierReport(data);
            break;
        case 'inventory':
            html = displayInventoryReport(data);
            break;
        default:
            html = '<p>Unknown report type</p>';
    }
    
    container.innerHTML = html;
}

// ===== EXPORT REPORT =====

function exportReport() {
    if (!currentReportData) {
        showToast('Generate a report first', 'error');
        return;
    }
    
    // Simple CSV export
    const csv = convertToCSV(currentReportData);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${currentReportType}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    
    showToast('Report exported', 'success');
}

function convertToCSV(data) {
    // Simple CSV conversion - enhance based on report type
    return JSON.stringify(data, null, 2);
}