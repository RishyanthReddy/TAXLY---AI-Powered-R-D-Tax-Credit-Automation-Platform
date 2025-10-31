/**
 * Utility Functions
 * Common helper functions used across the application
 */

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// Format date
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Format time duration
function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

// Get status color
function getStatusColor(status) {
    const colors = {
        'healthy': 'var(--status-healthy)',
        'warning': 'var(--status-warning)',
        'error': 'var(--status-error)',
        'info': 'var(--status-info)',
        'pending': 'var(--status-pending)'
    };
    return colors[status] || colors.pending;
}

// Local storage helpers
const storage = {
    get(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return null;
        }
    },
    
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Error writing to localStorage:', error);
            return false;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Error removing from localStorage:', error);
            return false;
        }
    },
    
    clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('Error clearing localStorage:', error);
            return false;
        }
    }
};

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Generate unique ID
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// Deep clone object
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

// Check if object is empty
function isEmpty(obj) {
    return Object.keys(obj).length === 0;
}

// Capitalize first letter
function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// Truncate text
function truncate(str, length) {
    return str.length > length ? str.substring(0, length) + '...' : str;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatCurrency,
        formatDate,
        formatFileSize,
        formatDuration,
        getStatusColor,
        storage,
        debounce,
        throttle,
        generateId,
        deepClone,
        isEmpty,
        capitalize,
        truncate
    };
}


// Safe navigation with error handling
function safeNavigate(url, fallbackUrl = 'home.html') {
    try {
        // Check if URL is valid
        if (!url || typeof url !== 'string') {
            console.error('Invalid URL provided:', url);
            window.location.href = fallbackUrl;
            return;
        }
        
        // Navigate to URL
        window.location.href = url;
    } catch (error) {
        console.error('Navigation error:', error);
        // Fallback to home page
        window.location.href = fallbackUrl;
    }
}

// Check if page exists before navigating
async function checkPageExists(url) {
    try {
        const response = await fetch(url, { method: 'HEAD' });
        return response.ok;
    } catch (error) {
        console.error('Error checking page:', error);
        return false;
    }
}

// Navigate with validation
async function navigateWithValidation(url, fallbackUrl = 'home.html') {
    const exists = await checkPageExists(url);
    if (exists) {
        window.location.href = url;
    } else {
        console.error('Page not found:', url);
        showNotification(`Page not found: ${url}. Redirecting to ${fallbackUrl}`, 'error');
        setTimeout(() => {
            window.location.href = fallbackUrl;
        }, 2000);
    }
}

// Show notification (toast message)
function showNotification(message, type = 'info', duration = 3000) {
    // Remove existing notifications
    const existing = document.querySelector('.notification-toast');
    if (existing) {
        existing.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification-toast notification-${type}`;
    notification.textContent = message;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background-color: ${type === 'success' ? 'var(--status-healthy)' : 
                           type === 'error' ? 'var(--status-error)' : 
                           type === 'warning' ? 'var(--status-warning)' : 
                           'var(--color-primary)'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
        font-size: 14px;
        line-height: 1.5;
    `;
    
    // Add animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after duration
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, duration);
}

// Handle onclick errors gracefully
function safeOnClick(handler, fallbackMessage = 'An error occurred') {
    return function(event) {
        try {
            handler(event);
        } catch (error) {
            console.error('Click handler error:', error);
            showNotification(fallbackMessage, 'error');
        }
    };
}

// Validate all navigation links on page load
function validateNavigationLinks() {
    const links = document.querySelectorAll('a[href]');
    const validPages = ['home.html', 'index.html', 'workflow.html', 'reports.html', 'onboarding.html'];
    
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (href && !href.startsWith('#') && !href.startsWith('http')) {
            if (!validPages.includes(href)) {
                console.warn('Invalid navigation link found:', href);
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    showNotification(`Page not found: ${href}`, 'error');
                });
            }
        }
    });
}

// Initialize navigation validation on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', validateNavigationLinks);
} else {
    validateNavigationLinks();
}
