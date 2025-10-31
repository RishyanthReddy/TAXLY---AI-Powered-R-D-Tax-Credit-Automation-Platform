/**
 * Onboarding Page JavaScript
 * Handles onboarding flow and step navigation
 */

let currentStep = 1;
const totalSteps = 6;
let onboardingData = {
    companyName: '',
    taxYear: '',
    industry: '',
    employeeCount: '',
    hrPlatform: '',
    timePlatform: '',
    hrAuthenticated: false,
    timeAuthenticated: false
};

// Initialize onboarding
function initOnboarding() {
    setupEventListeners();
    loadSavedData();
}

// Setup event listeners
function setupEventListeners() {
    // Skip demo button
    const skipBtn = document.getElementById('skipDemoBtn');
    if (skipBtn) {
        skipBtn.addEventListener('click', skipToDemo);
    }
    
    // Platform selection
    document.querySelectorAll('.platform-card').forEach(card => {
        card.addEventListener('click', () => selectPlatform(card));
    });
    
    // Authentication buttons
    const authHRBtn = document.getElementById('authHRBtn');
    if (authHRBtn) {
        authHRBtn.addEventListener('click', () => authenticatePlatform('hr'));
    }
    
    const authTimeBtn = document.getElementById('authTimeBtn');
    if (authTimeBtn) {
        authTimeBtn.addEventListener('click', () => authenticatePlatform('time'));
    }
    
    // Form inputs
    document.querySelectorAll('.onboarding-form input, .onboarding-form select').forEach(input => {
        input.addEventListener('change', saveFormData);
    });
}

// Navigate to next step
function nextStep() {
    if (!validateCurrentStep()) {
        return;
    }
    
    if (currentStep < totalSteps) {
        // Hide current step
        document.getElementById(`step${currentStep}`).classList.remove('active');
        document.querySelector(`.progress-step[data-step="${currentStep}"]`).classList.remove('active');
        document.querySelector(`.progress-step[data-step="${currentStep}"]`).classList.add('completed');
        
        // Show next step
        currentStep++;
        document.getElementById(`step${currentStep}`).classList.add('active');
        document.querySelector(`.progress-step[data-step="${currentStep}"]`).classList.add('active');
        
        // Update step-specific content
        updateStepContent();
    }
}

// Navigate to previous step
function prevStep() {
    if (currentStep > 1) {
        // Hide current step
        document.getElementById(`step${currentStep}`).classList.remove('active');
        document.querySelector(`.progress-step[data-step="${currentStep}"]`).classList.remove('active');
        
        // Show previous step
        currentStep--;
        document.getElementById(`step${currentStep}`).classList.add('active');
        document.querySelector(`.progress-step[data-step="${currentStep}"]`).classList.remove('completed');
        document.querySelector(`.progress-step[data-step="${currentStep}"]`).classList.add('active');
    }
}

// Validate current step
function validateCurrentStep() {
    switch (currentStep) {
        case 2:
            const companyName = document.getElementById('companyName').value;
            const taxYear = document.getElementById('taxYear').value;
            const industry = document.getElementById('industry').value;
            if (!companyName || !taxYear || !industry) {
                alert('Please fill in all required fields');
                return false;
            }
            break;
        case 3:
            if (!onboardingData.hrPlatform) {
                alert('Please select an HR/Payroll platform');
                return false;
            }
            break;
        case 4:
            if (!onboardingData.timePlatform) {
                alert('Please select a Time Tracking platform');
                return false;
            }
            break;
        case 5:
            if (!onboardingData.hrAuthenticated || !onboardingData.timeAuthenticated) {
                alert('Please authenticate both platforms');
                return false;
            }
            break;
    }
    return true;
}

// Select platform
function selectPlatform(card) {
    const platform = card.dataset.platform;
    const step = currentStep;
    
    // Remove selection from siblings
    card.parentElement.querySelectorAll('.platform-card').forEach(c => {
        c.classList.remove('selected');
    });
    
    // Add selection to clicked card
    card.classList.add('selected');
    
    // Save selection
    if (step === 3) {
        onboardingData.hrPlatform = platform;
        document.getElementById('hrContinueBtn').disabled = false;
    } else if (step === 4) {
        onboardingData.timePlatform = platform;
        document.getElementById('timeContinueBtn').disabled = false;
    }
    
    saveOnboardingData();
}

// Authenticate platform
function authenticatePlatform(type) {
    const btn = type === 'hr' ? document.getElementById('authHRBtn') : document.getElementById('authTimeBtn');
    const status = type === 'hr' ? document.getElementById('hrAuthStatus') : document.getElementById('timeAuthStatus');
    
    // Simulate OAuth flow
    btn.innerHTML = '<span class="spinner"></span> Authenticating...';
    btn.disabled = true;
    
    setTimeout(() => {
        if (type === 'hr') {
            onboardingData.hrAuthenticated = true;
            status.innerHTML = '<span class="status-icon">✅</span> Connected successfully';
            status.classList.add('success');
        } else {
            onboardingData.timeAuthenticated = true;
            status.innerHTML = '<span class="status-icon">✅</span> Connected successfully';
            status.classList.add('success');
        }
        
        btn.innerHTML = btn.innerHTML.replace('Authenticating...', 'Reconnect');
        btn.disabled = false;
        
        // Enable continue button if both authenticated
        if (onboardingData.hrAuthenticated && onboardingData.timeAuthenticated) {
            document.getElementById('authContinueBtn').disabled = false;
        }
        
        saveOnboardingData();
    }, 2000);
}

// Update step-specific content
function updateStepContent() {
    if (currentStep === 5) {
        // Update authentication step with selected platforms
        const hrName = capitalize(onboardingData.hrPlatform || 'BambooHR');
        const timeName = capitalize(onboardingData.timePlatform || 'Clockify');
        
        document.getElementById('hrPlatformName').textContent = hrName;
        document.getElementById('timePlatformName').textContent = timeName;
        document.getElementById('authHRBtn').innerHTML = `<span class="icon">🔐</span> Authorize ${hrName}`;
        document.getElementById('authTimeBtn').innerHTML = `<span class="icon">🔐</span> Authorize ${timeName}`;
    } else if (currentStep === 6) {
        // Update review step
        document.getElementById('reviewCompanyName').textContent = onboardingData.companyName || '-';
        document.getElementById('reviewTaxYear').textContent = onboardingData.taxYear || '-';
        document.getElementById('reviewIndustry').textContent = onboardingData.industry || '-';
        document.getElementById('reviewHRPlatform').textContent = capitalize(onboardingData.hrPlatform || '-');
        document.getElementById('reviewTimePlatform').textContent = capitalize(onboardingData.timePlatform || '-');
    }
}

// Save form data
function saveFormData() {
    onboardingData.companyName = document.getElementById('companyName')?.value || '';
    onboardingData.taxYear = document.getElementById('taxYear')?.value || '';
    onboardingData.industry = document.getElementById('industry')?.value || '';
    onboardingData.employeeCount = document.getElementById('employeeCount')?.value || '';
    saveOnboardingData();
}

// Save onboarding data to localStorage
function saveOnboardingData() {
    storage.set('onboardingData', onboardingData);
}

// Load saved data
function loadSavedData() {
    const saved = storage.get('onboardingData');
    if (saved) {
        onboardingData = saved;
        // Populate form fields if returning to onboarding
        if (document.getElementById('companyName')) {
            document.getElementById('companyName').value = onboardingData.companyName || '';
            document.getElementById('taxYear').value = onboardingData.taxYear || '';
            document.getElementById('industry').value = onboardingData.industry || '';
            document.getElementById('employeeCount').value = onboardingData.employeeCount || '';
        }
    }
}

// Skip to demo
function skipToDemo() {
    // Set demo data
    onboardingData = {
        companyName: 'Acme Corporation',
        taxYear: '2024',
        industry: 'software',
        employeeCount: '45',
        hrPlatform: 'bamboohr',
        timePlatform: 'clockify',
        hrAuthenticated: true,
        timeAuthenticated: true
    };
    saveOnboardingData();
    completeOnboarding();
}

// Complete onboarding
function completeOnboarding() {
    storage.set('onboardingComplete', true);
    window.location.href = 'index.html';
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOnboarding);
} else {
    initOnboarding();
}
