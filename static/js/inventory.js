/**
 * Inventory management logic
 * Product CRUD, Excel import, stock management
 */

let products = [];
let categories = [];
let currentPage = 1;
let totalPages = 1;
let editingProductId = null;

// ===== INITIALIZATION =====

document.addEventListener('DOMContentLoaded', async () => {
    await loadCategories();
    await loadProducts();
    await checkStockAlerts();
});

// ===== PRODUCT LOADING =====

async function loadProducts() {
    try {
        showLoading(true);
        
        const searchTerm = document.getElementById('search-input').value;
        const category = document.getElementById('category-filter').value;
        const lowStockOnly = document.getElementById('low-stock-filter').checked;
        const activeOnly = document.getElementById('active-only-filter').checked;
        
        let url = `/api/products/?skip=${(currentPage - 1) * 50}&limit=50`;
        
        if (searchTerm) url += `&search=${encodeURIComponent(searchTerm)}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;
        if (lowStockOnly) url += `&low_stock_only=true`;
        if (activeOnly) url += `&active_only=true`;
        
        products = await apiRequest(url);
        renderProducts();
        
    } catch (error) {
        showToast('Failed to load products', 'error');
    } finally {
        showLoading(false);
    }
}

function renderProducts() {
    const tbody = document.getElementById('products-tbody');
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-row">No products found</td></tr>';
        return;
    }
    
    tbody.innerHTML = products.map(p => `
        <tr class="${p.stock_quantity <= p.reorder_alert_level ? 'low-stock-row' : ''}">
            <td>${escapeHtml(p.barcode)}</td>
            <td>${escapeHtml(p.name)}</td>
            <td>${escapeHtml(p.category || '-')}</td>
            <td>${formatCurrency(p.cost_price)}</td>
            <td>${formatCurrency(p.retail_price)}</td>
            <td>
                <span class="stock-badge ${p.stock_quantity === 0 ? 'stock-out' : p.stock_quantity <= p.reorder_alert_level ? 'stock-low' : 'stock-ok'}">
                    ${p.stock_quantity}
                </span>
            </td>
            <td>
                <span class="status-badge ${p.is_active ? 'status-active' : 'status-inactive'}">
                    ${p.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <button onclick="editProduct(${p.id})" class="btn-small btn-secondary">Edit</button>
                <button onclick="toggleProductStatus(${p.id}, ${!p.is_active})" class="btn-small ${p.is_active ? 'btn-danger' : 'btn-success'}">
                    ${p.is_active ? 'Deactivate' : 'Activate'}
                </button>
            </td>
        </tr>
    `).join('');
}

// ===== SEARCH & FILTER =====

let searchTimeout;
function searchProducts() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentPage = 1;
        loadProducts();
    }, 500);
}

function filterProducts() {
    currentPage = 1;
    loadProducts();
}

// ===== CATEGORIES =====

async function loadCategories() {
    try {
        const response = await apiRequest('/api/products/categories/list');
        categories = response;
        
        const select = document.getElementById('category-filter');
        const datalist = document.getElementById('categories-list');
        
        const options = categories.map(cat => 
            `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`
        ).join('');
        
        select.innerHTML = '<option value="">All Categories</option>' + options;
        datalist.innerHTML = options;
        
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

// ===== STOCK ALERTS =====

async function checkStockAlerts() {
    try {
        const response = await apiRequest('/api/products/stock/alerts');
        
        if (response.count > 0) {
            const alertsDiv = document.getElementById('stock-alerts');
            alertsDiv.innerHTML = `
                <div class="alert alert-warning">
                    <strong>⚠️ ${response.count} products need attention:</strong>
                    <ul>
                        ${response.products.slice(0, 5).map(p => 
                            `<li>${escapeHtml(p.name)} - ${p.status} (${p.current_stock} units)</li>`
                        ).join('')}
                        ${response.count > 5 ? `<li><em>...and ${response.count - 5} more</em></li>` : ''}
                    </ul>
                </div>
            `;
            alertsDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Failed to load stock alerts:', error);
    }
}

// ===== PRODUCT MODAL =====

function showAddProductModal() {
    editingProductId = null;
    document.getElementById('modal-title').textContent = 'Add Product';
    document.getElementById('product-form').reset();
    document.getElementById('product-modal').style.display = 'flex';
    document.getElementById('product-barcode').focus();
}

function closeProductModal() {
    document.getElementById('product-modal').style.display = 'none';
}

async function editProduct(productId) {
    try {
        const product = await apiRequest(`/api/products/${productId}`);
        
        editingProductId = productId;
        document.getElementById('modal-title').textContent = 'Edit Product';
        
        document.getElementById('product-barcode').value = product.barcode;
        document.getElementById('product-name').value = product.name;
        document.getElementById('product-category').value = product.category || '';
        document.getElementById('product-brand').value = product.brand || '';
        document.getElementById('product-cost-price').value = product.cost_price;
        document.getElementById('product-retail-price').value = product.retail_price;
        document.getElementById('product-stock').value = product.stock_quantity;
        document.getElementById('product-alert-level').value = product.reorder_alert_level;
        document.getElementById('product-unit').value = product.unit_of_measure;
        document.getElementById('product-supplier').value = product.supplier_name || '';
        document.getElementById('product-notes').value = product.notes || '';
        
        document.getElementById('product-modal').style.display = 'flex';
        
    } catch (error) {
        showToast('Failed to load product', 'error');
    }
}

async function saveProduct() {
    const barcode = document.getElementById('product-barcode').value;
    const name = document.getElementById('product-name').value;
    const category = document.getElementById('product-category').value;
    const brand = document.getElementById('product-brand').value;
    const costPrice = parseFloat(document.getElementById('product-cost-price').value);
    const retailPrice = parseFloat(document.getElementById('product-retail-price').value);
    const stock = parseInt(document.getElementById('product-stock').value);
    const alertLevel = parseInt(document.getElementById('product-alert-level').value);
    const unit = document.getElementById('product-unit').value;
    const supplier = document.getElementById('product-supplier').value;
    const notes = document.getElementById('product-notes').value;
    
    // Validation
    if (!barcode || !name || !costPrice || !retailPrice) {
        showToast('Please fill all required fields', 'error');
        return;
    }
    
    if (costPrice < 0 || retailPrice <= 0) {
        showToast('Invalid prices', 'error');
        return;
    }
    
    const productData = {
        barcode,
        name,
        category: category || null,
        brand: brand || null,
        cost_price: costPrice,
        retail_price: retailPrice,
        stock_quantity: stock,
        reorder_alert_level: alertLevel,
        unit_of_measure: unit,
        supplier_name: supplier || null,
        notes: notes || null
    };
    
    try {
        showLoading(true);
        
        if (editingProductId) {
            await apiRequest(`/api/products/${editingProductId}`, 'PUT', productData);
            showToast('Product updated successfully', 'success');
        } else {
            await apiRequest('/api/products/', 'POST', productData);
            showToast('Product created successfully', 'success');
        }
        
        closeProductModal();
        await loadProducts();
        await loadCategories();
        await checkStockAlerts();
        
    } catch (error) {
        showToast(error.message || 'Failed to save product', 'error');
    } finally {
        showLoading(false);
    }
}

async function toggleProductStatus(productId, activate) {
    const action = activate ? 'activate' : 'deactivate';
    
    if (!confirm(`Are you sure you want to ${action} this product?`)) {
        return;
    }
    
    try {
        if (activate) {
            await apiRequest(`/api/products/${productId}`, 'PUT', { is_active: true });
        } else {
            await apiRequest(`/api/products/${productId}`, 'DELETE');
        }
        
        showToast(`Product ${activate ? 'activated' : 'deactivated'}`, 'success');
        await loadProducts();
        
    } catch (error) {
        showToast(error.message || 'Failed to update product', 'error');
    }
}

// ===== EXCEL IMPORT =====

function showImportModal() {
    document.getElementById('import-modal').style.display = 'flex';
    document.getElementById('import-results').style.display = 'none';
    document.getElementById('import-progress').style.display = 'none';
}

function closeImportModal() {
    document.getElementById('import-modal').style.display = 'none';
    document.getElementById('import-file').value = '';
}

async function uploadFile() {
    const fileInput = document.getElementById('import-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showToast('Please select a file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        document.getElementById('import-progress').style.display = 'block';
        
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/inventory/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const result = await response.json();
        
        // Display results
        const resultsDiv = document.getElementById('import-results');
        resultsDiv.innerHTML = `
            <div class="import-summary">
                <h3>Import Complete</h3>
                <p><strong>Total Records:</strong> ${result.results.total}</p>
                <p><strong>Inserted:</strong> ${result.results.inserted}</p>
                <p><strong>Updated:</strong> ${result.results.updated}</p>
                <p><strong>Errors:</strong> ${result.results.errors.length}</p>
                
                ${result.results.errors.length > 0 ? `
                    <div class="error-list">
                        <h4>Errors:</h4>
                        <ul>
                            ${result.results.errors.map(e => 
                                `<li>Row ${e.row}: ${e.barcode} - ${e.error}</li>`
                            ).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
        resultsDiv.style.display = 'block';
        
        showToast('Import completed', 'success');
        
        // Reload products
        await loadProducts();
        await loadCategories();
        await checkStockAlerts();
        
    } catch (error) {
        showToast(error.message || 'Import failed', 'error');
    } finally {
        document.getElementById('import-progress').style.display = 'none';
    }
}

// ===== EXPORT =====

async function exportInventory() {
    try {
        showLoading(true);
        
        const result = await apiRequest('/api/inventory/export');
        
        showToast(`Exported ${result.record_count} products to ${result.filename}`, 'success');
        
        // Optional: Trigger download
        window.open(`/data/exports/${result.filename}`, '_blank');
        
    } catch (error) {
        showToast('Export failed', 'error');
    } finally {
        showLoading(false);
    }
}