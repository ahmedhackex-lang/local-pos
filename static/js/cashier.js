/**
 * Cashier interface logic
 * Barcode scanning, cart management, checkout
 */

let cart = [];
let heldTransactions = [];
let nextHoldId = 1;

// ===== INITIALIZATION =====

document.addEventListener('DOMContentLoaded', () => {
    const barcodeInput = document.getElementById('barcode-input');
    
    // Auto-focus on load
    barcodeInput.focus();
    
    // Barcode input handler
    barcodeInput.addEventListener('keypress', handleBarcodeInput);
    
    // Refocus on blur (with delay for intentional clicks)
    let refocusTimeout;
    barcodeInput.addEventListener('blur', () => {
        refocusTimeout = setTimeout(() => {
            if (!document.activeElement.matches('input, textarea, button, select')) {
                barcodeInput.focus();
            }
        }, 1500);
    });
    
    document.addEventListener('focusin', (e) => {
        if (e.target !== barcodeInput) {
            clearTimeout(refocusTimeout);
        }
    });
    
    // Cash button handlers
    document.querySelectorAll('.cash-btn').forEach(btn => {
        btn.addEventListener('click', handleCashButton);
    });
    
    // Amount tendered input handler
    const tenderedInput = document.getElementById('amount-tendered');
    tenderedInput.addEventListener('input', calculateChange);
    
    // Payment method change
    document.getElementById('payment-method').addEventListener('change', handlePaymentMethodChange);
});

// ===== BARCODE SCANNING =====

async function handleBarcodeInput(e) {
    if (e.key !== 'Enter') return;
    
    e.preventDefault();
    
    const input = e.target.value.trim();
    if (!input) return;
    
    // Parse quantity multiplier (e.g., "5*1234567890")
    const multiplierMatch = input.match(/^(\d+)\*(.+)$/);
    const quantity = multiplierMatch ? parseInt(multiplierMatch[1]) : 1;
    const barcode = multiplierMatch ? multiplierMatch[2] : input;
    
    if (!validateBarcode(barcode)) {
        showToast('Invalid barcode', 'error');
        playSound('scan-error-sound');
        e.target.value = '';
        return;
    }
    
    // Lookup product
    try {
        showLoading(true);
        const product = await apiRequest(`/api/products/barcode/${barcode}`);
        
        // Add to cart
        addToCart(product, quantity);
        
        // Success feedback
        playSound('scan-success-sound');
        e.target.value = '';
        
    } catch (error) {
        showToast(error.message || 'Product not found', 'error');
        playSound('scan-error-sound');
        e.target.select();
    } finally {
        showLoading(false);
    }
}

// ===== CART MANAGEMENT =====

function addToCart(product, quantity = 1) {
    // Check if product already in cart
    const existingItem = cart.find(item => item.product_id === product.id);
    
    if (existingItem) {
        existingItem.quantity += quantity;
        existingItem.subtotal = existingItem.retail_price * existingItem.quantity;
    } else {
        cart.push({
            product_id: product.id,
            barcode: product.barcode,
            name: product.name,
            retail_price: product.retail_price,
            quantity: quantity,
            discount_percent: 0,
            subtotal: product.retail_price * quantity
        });
    }
    
    renderCart();
    updateTotals();
}

function removeFromCart(productId) {
    cart = cart.filter(item => item.product_id !== productId);
    renderCart();
    updateTotals();
}

function updateItemQuantity(productId, newQuantity) {
    const item = cart.find(item => item.product_id === productId);
    if (!item) return;
    
    if (newQuantity <= 0) {
        removeFromCart(productId);
        return;
    }
    
    item.quantity = newQuantity;
    item.subtotal = item.retail_price * newQuantity;
    
    renderCart();
    updateTotals();
}

function clearCart() {
    if (cart.length === 0) return;
    
    if (!confirm('Clear cart?')) return;
    
    cart = [];
    renderCart();
    updateTotals();
}

function renderCart() {
    const container = document.getElementById('cart-items');
    
    if (cart.length === 0) {
        container.innerHTML = '<p class="empty-cart">Cart is empty. Scan products to begin.</p>';
        return;
    }
    
    container.innerHTML = cart.map(item => `
        <div class="cart-item">
            <div class="item-details">
                <h4>${escapeHtml(item.name)}</h4>
                <p class="item-price">${formatCurrency(item.retail_price)} × ${item.quantity}</p>
            </div>
            <div class="item-actions">
                <button onclick="updateItemQuantity(${item.product_id}, ${item.quantity - 1})" class="btn-small">-</button>
                <input 
                    type="number" 
                    value="${item.quantity}" 
                    onchange="updateItemQuantity(${item.product_id}, parseFloat(this.value))"
                    class="qty-input">
                <button onclick="updateItemQuantity(${item.product_id}, ${item.quantity + 1})" class="btn-small">+</button>
                <button onclick="removeFromCart(${item.product_id})" class="btn-small btn-danger">×</button>
            </div>
            <div class="item-total">
                ${formatCurrency(item.subtotal)}
            </div>
        </div>
    `).join('');
}

function updateTotals() {
    const subtotal = cart.reduce((sum, item) => sum + parseFloat(item.subtotal), 0);
    const discount = 0; // TODO: Implement discount logic
    const total = subtotal - discount;
    
    document.getElementById('cart-subtotal').textContent = formatCurrency(subtotal);
    document.getElementById('cart-discount').textContent = formatCurrency(discount);
    document.getElementById('cart-total').textContent = formatCurrency(total);
}

// ===== HOLD/RESUME TRANSACTIONS =====

function holdTransaction() {
    if (cart.length === 0) {
        showToast('Cart is empty', 'error');
        return;
    }
    
    const holdId = nextHoldId++;
    const total = cart.reduce((sum, item) => sum + parseFloat(item.subtotal), 0);
    
    heldTransactions.push({
        id: holdId,
        cart: [...cart],
        total: total,
        timestamp: new Date()
    });
    
    cart = [];
    renderCart();
    updateTotals();
    renderHeldTransactions();
    
    showToast(`Transaction #${holdId} held`, 'success');
}

function resumeTransaction(holdId) {
    const heldIndex = heldTransactions.findIndex(t => t.id === holdId);
    if (heldIndex === -1) return;
    
    if (cart.length > 0 && !confirm('Current cart will be lost. Continue?')) {
        return;
    }
    
    const held = heldTransactions[heldIndex];
    cart = [...held.cart];
    
    heldTransactions.splice(heldIndex, 1);
    
    renderCart();
    updateTotals();
    renderHeldTransactions();
    
    showToast(`Transaction #${holdId} resumed`, 'success');
}

function renderHeldTransactions() {
    const container = document.getElementById('held-transactions');
    
    if (heldTransactions.length === 0) {
        container.innerHTML = '<p>No held transactions</p>';
        return;
    }
    
    container.innerHTML = heldTransactions.map(t => `
        <button class="held-btn" onclick="resumeTransaction(${t.id})">
            <strong>Hold #${t.id}</strong><br>
            Items: ${t.cart.length}<br>
            Total: ${formatCurrency(t.total)}<br>
            <small>${formatTime(t.timestamp)}</small>
        </button>
    `).join('');
}

// ===== PAYMENT =====

function handleCashButton(e) {
    const amount = parseFloat(e.target.dataset.amount);
    document.getElementById('amount-tendered').value = amount;
    calculateChange();
}

function calculateChange() {
    const tendered = parseFloat(document.getElementById('amount-tendered').value) || 0;
    const total = cart.reduce((sum, item) => sum + parseFloat(item.subtotal), 0);
    const change = tendered - total;
    
    const changeDisplay = document.getElementById('change-display');
    const changeValue = document.getElementById('change-value');
    
    if (change >= 0) {
        changeValue.textContent = change.toFixed(2);
        changeDisplay.style.display = 'block';
    } else {
        changeDisplay.style.display = 'none';
    }
}

function handlePaymentMethodChange() {
    const method = document.getElementById('payment-method').value;
    const tenderedInput = document.getElementById('amount-tendered');
    
    if (method === 'Cash') {
        tenderedInput.disabled = false;
    } else {
        tenderedInput.disabled = true;
        tenderedInput.value = '';
        document.getElementById('change-display').style.display = 'none';
    }
}

// ===== CHECKOUT =====

async function completeSale() {
    if (cart.length === 0) {
        showToast('Cart is empty', 'error');
        return;
    }
    
    const paymentMethod = document.getElementById('payment-method').value;
    const amountTendered = parseFloat(document.getElementById('amount-tendered').value) || 0;
    const total = cart.reduce((sum, item) => sum + parseFloat(item.subtotal), 0);
    
    // Validate payment
    if (paymentMethod === 'Cash') {
        if (amountTendered < total) {
            showToast('Insufficient payment amount', 'error');
            return;
        }
    }
    
    // Prepare sale data
    const saleData = {
        items: cart.map(item => ({
            product_id: item.product_id,
            quantity: item.quantity,
            discount_percent: item.discount_percent || 0
        })),
        payment_method: paymentMethod,
        amount_tendered: paymentMethod === 'Cash' ? amountTendered : null,
        discount: 0
    };
    
    try {
        showLoading(true);
        
        const result = await apiRequest('/api/sales/', 'POST', saleData);
        
        // Success
        playSound('checkout-sound');
        showToast(`Sale completed! Invoice: ${result.invoice_number}`, 'success');
        
        // Clear cart
        cart = [];
        renderCart();
        updateTotals();
        
        // Reset payment
        document.getElementById('amount-tendered').value = '';
        document.getElementById('change-display').style.display = 'none';
        
        // Refocus barcode input
        document.getElementById('barcode-input').focus();
        
    } catch (error) {
        showToast(error.message || 'Sale failed', 'error');
    } finally {
        showLoading(false);
    }
}